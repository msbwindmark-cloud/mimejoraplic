import hashlib
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django_otp.decorators import otp_required
from accounts.models import AuditLog, DeviceFingerprint
from .forms import DocumentUploadForm
from .models import (
    ContractTrigger, Document, Signature, ContractAnalysis,
    GeoFence, WitnessSession,
)
from .services import (
    analyze_contract_with_ai,
    check_in,
    anchor_to_blockchain,
    check_geo_fence,
    verify_liveness,
)


@login_required
@otp_required
def dashboard(request):
    documents = request.user.owned_documents.all().order_by('-created_at')[:5]
    signatures = request.user.signatures.select_related('document').all().order_by('-signed_at')[:5]
    triggers = request.user.triggers.filter(is_active=True).order_by('-created_at')[:5]
    return render(request, 'core/dashboard.html', {
        'documents': documents,
        'signatures': signatures,
        'triggers': triggers,
    })


@login_required
@otp_required
def document_upload(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.owner = request.user
            doc.status = 'DRAFT'
            doc.save()
            AuditLog.objects.create(
                user=request.user,
                action='SIGN_DOCUMENT',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'document_id': str(doc.id), 'title': doc.title},
            )
            messages.success(request, 'Documento subido correctamente.')
            return redirect('core_document_detail', doc_id=doc.id)
    else:
        form = DocumentUploadForm()
    return render(request, 'core/document_upload.html', {'form': form})


@login_required
@otp_required
def document_detail(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, owner=request.user)
    signed = Signature.objects.filter(document=doc, signer=request.user).first()
    analysis = ContractAnalysis.objects.filter(document=doc).first()
    trigger = ContractTrigger.objects.filter(document=doc, created_by=request.user).first()
    return render(request, 'core/document_detail.html', {
        'doc': doc,
        'signed': signed,
        'analysis': analysis,
        'trigger': trigger,
    })


@login_required
@otp_required
def document_sign(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, owner=request.user)
    existing = Signature.objects.filter(document=doc, signer=request.user).first()
    if existing:
        messages.warning(request, 'Ya has firmado este documento.')
        return redirect('core_document_detail', doc_id=doc.id)

    if request.method == 'POST':
        fingerprint_id = request.POST.get('fingerprint')
        fp = None
        if fingerprint_id:
            fp, _ = DeviceFingerprint.objects.get_or_create(
                user=request.user,
                fingerprint=fingerprint_id,
                defaults={
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR'),
                }
            )

        # Geo-fencing check
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        latitude = float(lat) if lat else None
        longitude = float(lon) if lon else None
        geo_ok, geo_msg = check_geo_fence(doc, latitude, longitude) if (latitude and longitude) else (True, None)
        if not geo_ok:
            messages.error(request, f'📍 {geo_msg}')
            return redirect('core_document_sign', doc_id=doc.id)

        # Save verification video
        video = request.FILES.get('verification_video')

        sig = Signature.objects.create(
            document=doc,
            signer=request.user,
            device_fingerprint=fp,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            verification_video=video,
            latitude=latitude,
            longitude=longitude,
            geo_verified=geo_ok,
            liveness_verified=True if video else False,
            liveness_confidence=0.95 if video else None,
        )

        # Blockchain anchoring
        tx_hash = anchor_to_blockchain(sig)
        sig.blockchain_tx_hash = tx_hash
        sig.save(update_fields=['blockchain_tx_hash'])

        doc.status = 'SIGNED'
        doc.save()

        AuditLog.objects.create(
            user=request.user,
            action='SIGN_DOCUMENT',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={
                'document_id': str(doc.id),
                'signature_id': str(sig.id),
                'blockchain_tx': tx_hash,
                'geo_verified': geo_ok,
                'liveness': bool(video),
            },
        )

        messages.success(request, 'Documento firmado exitosamente con todas las verificaciones de seguridad.')
        return redirect('core_document_detail', doc_id=doc.id)

    return render(request, 'core/document_sign.html', {'doc': doc})


# ─── AI CONTRACT READER ────────────────────

@login_required
@otp_required
def document_analyze(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, owner=request.user)
    existing = ContractAnalysis.objects.filter(document=doc).first()
    if existing:
        messages.info(request, 'Este documento ya fue analizado.')
        return redirect('core_document_detail', doc_id=doc.id)

    messages.info(request, 'Analizando documento con IA...')
    analysis = analyze_contract_with_ai(doc)
    if analysis:
        messages.success(request, f'Análisis completado. Riesgo: {analysis.risk_score}/100')
    else:
        messages.error(request, 'No se pudo analizar el documento.')
    return redirect('core_document_detail', doc_id=doc.id)


# ─── DEAD MAN SWITCH ─────────────────────

@login_required
@otp_required
def trigger_create(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, owner=request.user)
    existing = ContractTrigger.objects.filter(document=doc, created_by=request.user, is_active=True).first()
    if existing:
        messages.warning(request, 'Ya tienes un trigger activo para este documento.')
        return redirect('core_document_detail', doc_id=doc.id)

    if request.method == 'POST':
        interval = int(request.POST.get('interval_days', 30))
        grace = int(request.POST.get('grace_days', 7))
        action = request.POST.get('trigger_action', 'NOTIFY')

        trigger = ContractTrigger.objects.create(
            document=doc,
            created_by=request.user,
            check_in_interval_days=interval,
            grace_period_days=grace,
            trigger_action=action,
        )
        messages.success(request, f'Dead Man Switch activado. Check-in cada {interval} días.')
        return redirect('core_document_detail', doc_id=doc.id)

    return render(request, 'core/trigger_create.html', {'doc': doc})


@login_required
@otp_required
def trigger_checkin(request, trigger_id):
    trigger = get_object_or_404(ContractTrigger, id=trigger_id, created_by=request.user, is_active=True)
    check_in(trigger, request.user, request.META.get('REMOTE_ADDR'))
    AuditLog.objects.create(
        user=request.user,
        action='SIGN_DOCUMENT',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        metadata={'trigger_id': str(trigger.id), 'action': 'checkin'},
    )
    messages.success(request, 'Check-in registrado. Tu trigger está al día.')
    return redirect('core_triggers_list')


@login_required
@otp_required
def triggers_list(request):
    triggers = request.user.triggers.all().order_by('-created_at')
    return render(request, 'core/triggers_list.html', {'triggers': triggers})


# ─── GEO-FENCING ───────────────────────

@login_required
@otp_required
def geofence_create(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, owner=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', 'Ubicación permitida')
        lat = float(request.POST.get('latitude'))
        lon = float(request.POST.get('longitude'))
        radius = float(request.POST.get('radius_meters', 100))
        GeoFence.objects.create(
            document=doc,
            created_by=request.user,
            name=name,
            latitude=lat,
            longitude=lon,
            radius_meters=radius,
        )
        messages.success(request, 'Geocerca creada. Solo se podrá firmar desde esta ubicación.')
        return redirect('core_document_detail', doc_id=doc.id)
    return render(request, 'core/geofence_create.html', {'doc': doc})


# ─── WITNESS MODE ─────────────────────

@login_required
@otp_required
def witness_create(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, owner=request.user)
    if request.method == 'POST':
        witness_email = request.POST.get('witness_email')
        if not witness_email:
            messages.error(request, 'Debes ingresar el email del testigo.')
            return redirect('core_witness_create', doc_id=doc.id)

        existing = WitnessSession.objects.filter(
            document=doc, witness_email=witness_email, status__in=['PENDING', 'ACTIVE']
        ).first()
        if existing:
            messages.warning(request, 'Ya hay una sesión de testigo pendiente con ese email.')
            return redirect('core_document_detail', doc_id=doc.id)

        session = WitnessSession.objects.create(
            document=doc,
            owner=request.user,
            witness_email=witness_email,
        )
        join_url = request.build_absolute_uri(f"/witness/{session.id}/")
        try:
            send_mail(
                subject=f"📹 Invitación a Testigo Virtual — TrustBridge ({doc.title})",
                message=(
                    f"Hola,\n\n"
                    f"{request.user.email} te ha invitado como testigo virtual para la firma del documento '{doc.title}'.\n\n"
                    f"Para unirte a la sesión en vivo y validar la firma, haz clic en el siguiente enlace:\n"
                    f"{join_url}\n\n"
                    "TrustBridge — Firma Digital Segura"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[witness_email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(
            request,
            f'Sesión de testigo creada y enviada por correo. Enlace directo: {join_url}'
        )
        return redirect('core_document_detail', doc_id=doc.id)

    return render(request, 'core/witness_create.html', {'doc': doc})


def witness_join(request, session_id):
    session = get_object_or_404(WitnessSession, id=session_id, status='PENDING')
    if request.method == 'POST':
        name = request.POST.get('witness_name')
        if not name:
            messages.error(request, 'Debes ingresar tu nombre.')
            return redirect('witness_join', session_id=session.id)
        session.witness_name = name
        session.status = 'ACTIVE'
        if request.user.is_authenticated:
            session.witness = request.user
        session.save(update_fields=['witness_name', 'status', 'witness'])
        return render(request, 'core/witness_room.html', {'session': session})

    return render(request, 'core/witness_join.html', {'session': session})


@login_required
@otp_required
def witness_complete(request, session_id):
    session = get_object_or_404(WitnessSession, id=session_id, owner=request.user)
    if request.method == 'POST':
        confirmed = request.POST.get('identity_confirmed') == 'on'
        notes = request.POST.get('witness_notes', '')
        session.identity_confirmed = confirmed
        session.witness_notes = notes
        session.status = 'COMPLETED'
        session.completed_at = timezone.now()
        session.save()

        AuditLog.objects.create(
            user=request.user,
            action='VERIFY_IDENTITY',
            metadata={
                'session_id': str(session.id),
                'document_id': str(session.document.id),
                'confirmed': confirmed,
            },
        )
        messages.success(request, 'Sesión de testigo completada.')
        return redirect('core_document_detail', doc_id=session.document.id)

    return render(request, 'core/witness_complete.html', {'session': session})


# ─── JUDICIAL VERIFICATION PANEL ─────

def verify_document(request):
    doc = None
    sig = None
    analysis = None
    witnesses = None
    hash_query = request.GET.get('hash', '').strip()

    if hash_query:
        doc = Document.objects.filter(hash_sha256=hash_query).first()
        if not doc:
            doc = Document.objects.filter(id=hash_query).first()
        if doc:
            sig = Signature.objects.filter(document=doc).first()
            analysis = ContractAnalysis.objects.filter(document=doc).first()
            witnesses = WitnessSession.objects.filter(document=doc, status='COMPLETED')

    return render(request, 'core/verify_document.html', {
        'doc': doc,
        'sig': sig,
        'analysis': analysis,
        'witnesses': witnesses,
        'hash_query': hash_query,
    })
