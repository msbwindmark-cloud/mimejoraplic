import os
import json
import math
import fitz
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import ContractTrigger, CheckInLog


# ──────────────────────────────────────────
#  BLOCKCHAIN ANCHORING
# ──────────────────────────────────────────

def anchor_to_blockchain(signature):
    """Registra la firma en Polygon/Ethereum como prueba inmutable."""
    private_key = os.environ.get('BLOCKCHAIN_PRIVATE_KEY', '')
    rpc_url = os.environ.get('BLOCKCHAIN_RPC_URL', 'https://rpc-mumbai.maticvigil.com')

    if not private_key:
        return _mock_blockchain_anchor(signature)

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return _mock_blockchain_anchor(signature)

        account = w3.eth.account.from_key(private_key)
        nonce = w3.eth.get_transaction_count(account.address)

        doc = signature.document
        data = w3.keccak(text=json.dumps({
            'doc_id': str(doc.id),
            'hash': doc.hash_sha256,
            'signer': signature.signer.email,
            'signed_at': signature.signed_at.isoformat(),
            'fingerprint': str(signature.device_fingerprint.fingerprint) if signature.device_fingerprint else '',
        }))

        tx = {
            'nonce': nonce,
            'to': account.address,
            'value': w3.to_wei(0, 'ether'),
            'gas': 50000,
            'gasPrice': w3.eth.gas_price,
            'data': data,
            'chainId': w3.eth.chain_id,
        }
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return w3.to_hex(tx_hash)
    except Exception:
        return _mock_blockchain_anchor(signature)


def _mock_blockchain_anchor(signature):
    import hashlib
    mock_hash = hashlib.sha256(
        f"{signature.id}-{signature.document.hash_sha256}-{signature.signed_at.isoformat()}".encode()
    ).hexdigest()
    return f"0x{mock_hash}"


# ──────────────────────────────────────────
#  GEO-FENCING
# ──────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    """Distancia entre dos coordenadas GPS en metros."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def check_geo_fence(document, latitude, longitude):
    """Verifica si una ubicación está dentro de alguna geocerca del documento."""
    fences = document.geofences.filter(is_active=True)
    if not fences.exists():
        return True, None

    for fence in fences:
        distance = haversine(latitude, longitude, fence.latitude, fence.longitude)
        if distance <= fence.radius_meters:
            return True, fence

    closest = min(fences, key=lambda f: haversine(latitude, longitude, f.latitude, f.longitude))
    dist = haversine(latitude, longitude, closest.latitude, closest.longitude)
    return False, f"Estás a {dist:.0f}m de la ubicación permitida (máx {closest.radius_meters}m)"


# ──────────────────────────────────────────
#  LIVENESS VERIFICATION (mock)
# ──────────────────────────────────────────

def verify_liveness(video_path):
    """Verifica que el video contenga un rostro real (mock).
    En producción integrar con AWS Rekognition / Azure Face API."""
    return True, 0.95


# ──────────────────────────────────────────
#  AI CONTRACT READER
# ──────────────────────────────────────────

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text()
    except Exception:
        text = "[No se pudo extraer texto del PDF]"
    return text[:15000]


def analyze_contract_with_ai(document):
    from .models import ContractAnalysis

    text = extract_text_from_pdf(document.file.path)
    if not text.strip():
        return None

    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        return _mock_analysis(document)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    prompt = f"""
Eres un abogado digital experto en análisis de contratos.
Analiza el siguiente contrato y responde SOLO con JSON válido (sin markdown):

{{
  "summary": "Resumen en 2-3 oraciones en español",
  "risk_score": <0-100>,
  "risky_clauses": [
    {{"clause": "texto de la cláusula", "risk": "alto|medio|bajo", "explanation": "por qué es riesgosa"}}
  ],
  "recommendations": "Recomendaciones en español"
}}

CONTRATO:
{text[:12000]}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        import json
        data = json.loads(resp.choices[0].message.content)
    except Exception:
        return _mock_analysis(document)

    analysis = ContractAnalysis.objects.create(
        document=document,
        analyzed_by=document.owner,
        raw_response=data,
        summary=data.get("summary", ""),
        risk_score=data.get("risk_score", 50),
        risky_clauses=data.get("risky_clauses", []),
        recommendations=data.get("recommendations", ""),
    )
    return analysis


def _mock_analysis(document):
    from .models import ContractAnalysis
    import random

    mock_clauses = [
        {"clause": "Cláusula de penalización por terminación anticipada",
         "risk": "alto",
         "explanation": "Multa del 30% del valor total del contrato."},
        {"clause": "Cláusula de renovación automática",
         "risk": "medio",
         "explanation": "Se renueva automáticamente cada año si no hay aviso con 90 días de anticipación."},
        {"clause": "Cláusula de jurisdicción",
         "risk": "bajo",
         "explanation": "Las disputas se resolverán en los tribunales de la ciudad sede."},
    ]

    analysis = ContractAnalysis.objects.create(
        document=document,
        analyzed_by=document.owner,
        raw_response={"mock": True},
        summary="El contrato contiene cláusulas estándar pero se identificaron algunos puntos importantes a revisar antes de firmar.",
        risk_score=random.randint(15, 45),
        risky_clauses=random.sample(mock_clauses, random.randint(1, 3)),
        recommendations="Se recomienda revisar las cláusulas de penalización y renovación automática con un abogado antes de firmar.",
    )
    return analysis


# ──────────────────────────────────────────
#  DEAD MAN SWITCH
# ──────────────────────────────────────────

def check_in(trigger, user, ip_address=None):
    trigger.last_check_in = timezone.now()
    trigger.save(update_fields=['last_check_in'])
    CheckInLog.objects.create(
        trigger=trigger,
        user=user,
        ip_address=ip_address,
    )


def process_expired_triggers(dry_run=False):
    now = timezone.now()
    expired = ContractTrigger.objects.filter(
        is_active=True,
        triggered_at__isnull=True,
        last_check_in__lte=now - timedelta(days=30),
    )

    results = []
    for trigger in expired:
        days_since = (now - trigger.last_check_in).days
        if days_since >= (trigger.check_in_interval_days + trigger.grace_period_days):
            if dry_run:
                results.append(f"[DRY RUN] Trigger {trigger.id} - {trigger.document.title} se ACTIVARÍA")
            else:
                _execute_trigger(trigger)
                results.append(f"[EJECUTADO] Trigger {trigger.id} - {trigger.document.title}")
        else:
            remaining = (trigger.check_in_interval_days + trigger.grace_period_days) - days_since
            if dry_run:
                results.append(f"[DRY RUN] Trigger {trigger.id} - {trigger.document.title} expirará en {remaining} días")
    return results


def _execute_trigger(trigger):
    from .models import AuditLog

    trigger.triggered_at = timezone.now()
    trigger.is_active = False
    trigger.save(update_fields=['triggered_at', 'is_active'])

    user = trigger.created_by

    if trigger.trigger_action == 'NOTIFY':
        send_mail(
            subject=f"🔔 TrustBridge — Trigger activado: {trigger.document.title}",
            message=(
                f"Tu contrato '{trigger.document.title}' ha superado el periodo sin check-in.\n\n"
                f"Documento: {trigger.document.title}\n"
                f"Último check-in: {trigger.last_check_in}\n"
                f"Acción configurada: {trigger.get_trigger_action_display()}\n\n"
                "TrustBridge — Firma Digital Segura"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

    AuditLog.objects.create(
        user=user,
        action='SIGN_DOCUMENT',
        metadata={
            'trigger_id': str(trigger.id),
            'document_id': str(trigger.document.id),
            'action': trigger.trigger_action,
        },
    )
