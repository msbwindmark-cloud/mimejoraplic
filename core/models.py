import uuid
from django.db import models
from django.conf import settings


class Document(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador'),
        ('PENDING', 'Pendiente de Firma'),
        ('SIGNED', 'Firmado'),
        ('VERIFIED', 'Verificado'),
        ('REJECTED', 'Rechazado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    hash_sha256 = models.CharField(max_length=64, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_documents'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Signature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    device_fingerprint = models.ForeignKey(
        'accounts.DeviceFingerprint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)
    blockchain_tx_hash = models.CharField(max_length=255, blank=True)
    verification_video = models.FileField(
        upload_to='verification_videos/',
        null=True, blank=True
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geo_verified = models.BooleanField(default=False)
    liveness_verified = models.BooleanField(default=False)
    liveness_confidence = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('document', 'signer')

    def __str__(self):
        return f"{self.signer.email} - {self.document.title}"


class ContractTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='triggers')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='triggers')
    check_in_interval_days = models.PositiveIntegerField(
        default=30,
        help_text='Días máximos sin check-in antes de activar el trigger'
    )
    last_check_in = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    trigger_action = models.CharField(
        max_length=50,
        choices=[
            ('NOTIFY', 'Notificar por correo'),
            ('TRANSFER', 'Transferir documento'),
            ('PUBLISH', 'Publicar documento'),
        ],
        default='NOTIFY',
    )
    trigger_data = models.JSONField(default=dict, blank=True)
    grace_period_days = models.PositiveIntegerField(
        default=7,
        help_text='Días de gracia después del vencimiento antes de ejecutar'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trigger {self.document.title} - {self.created_by.email}"

    class Meta:
        ordering = ['-created_at']


class CheckInLog(models.Model):
    trigger = models.ForeignKey(ContractTrigger, on_delete=models.CASCADE, related_name='checkins')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_in_at']


class ContractAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='analyses')
    analyzed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    raw_response = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    risk_score = models.IntegerField(
        default=0,
        help_text='0 = sin riesgo, 100 = máximo riesgo'
    )
    risky_clauses = models.JSONField(default=list, blank=True)
    recommendations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Analysis: {self.document.title} ({self.risk_score}/100)"


class GeoFence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='geofences')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default='Ubicación permitida')
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_meters = models.FloatField(default=100, help_text='Radio de tolerancia en metros')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"


class WitnessSession(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('ACTIVE', 'En curso'),
        ('COMPLETED', 'Completada'),
        ('CANCELLED', 'Cancelada'),
        ('REJECTED', 'Rechazada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='witness_sessions')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='witness_sessions_as_owner'
    )
    witness = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='witness_sessions_as_witness'
    )
    witness_email = models.EmailField(help_text='Email del testigo')
    witness_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    witness_notes = models.TextField(blank=True, help_text='Notas del testigo sobre la verificación')
    identity_confirmed = models.BooleanField(default=False)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    room_id = models.CharField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Testigo: {self.witness_email} - {self.document.title}"

    def save(self, *args, **kwargs):
        if not self.room_id:
            self.room_id = f"witness-{self.id}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)
