import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    face_register_date = models.DateTimeField(null=True, blank=True)
    is_device_trusted = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class DeviceFingerprint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    fingerprint = models.CharField(max_length=255, db_index=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    is_trusted = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'fingerprint')


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGIN_FAILED', 'Login Fallido'),
        ('LOGOUT', 'Logout'),
        ('SIGN_DOCUMENT', 'Firma de Documento'),
        ('VERIFY_IDENTITY', 'Verificación de Identidad'),
        ('2FA_ENABLED', '2FA Activado'),
        ('2FA_DISABLED', '2FA Desactivado'),
        ('DEVICE_TRUSTED', 'Dispositivo Confiado'),
        ('PASSWORD_CHANGE', 'Cambio de Contraseña'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
        ]
