from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DeviceFingerprint, AuditLog

admin.site.register(User, UserAdmin)
admin.site.register(DeviceFingerprint)
admin.site.register(AuditLog)
