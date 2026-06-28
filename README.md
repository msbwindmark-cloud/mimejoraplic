# TrustBridge — Firma Digital Segura con Validez Judicial

Plataforma SaaS de firma de contratos con verificación biométrica, blockchain, geocercas, testigos en vivo y Dead Man Switch.

## 🚀 Stack

| Capa         | Tecnología                              |
|-------------|-----------------------------------------|
| Backend     | Python 3.13 + Django 6.0               |
| Frontend    | Bootstrap 5 + Bootswatch Flatly        |
| Auth        | django-allauth + django-two-factor-auth |
| Seguridad   | 2FA TOTP, FingerprintJS, WebAuthn      |
| IA          | OpenAI GPT-4o-mini (análisis contratos) |
| Blockchain  | Web3.py (Polygon/Ethereum)             |
| Video       | WebRTC (testigos en vivo)              |
| DB demo     | SQLite3                                |

---

## 📋 Funcionalidades

### 🔐 Seguridad nivel Facebook
- Login con email + contraseña
- 2FA obligatorio (Google Authenticator)
- Huella digital del dispositivo (FingerprintJS)
- Rate limiting por IP
- Geolocalización del firmante

### 📄 Gestión de documentos
- Subida de PDF/DOC/PNG con hash SHA-256 automático
- Firma digital con captura de:
  - IP + User-Agent
  - Huella digital del dispositivo
  - Coordenadas GPS
  - Video de verificación en vivo

### 🤖 AI Contract Reader
- Analiza contratos con GPT-4o-mini
- Detecta cláusulas riesgosas
- Puntúa el riesgo (0-100)
- Recomendaciones legales

### 🧪 Dead Man Switch
- Si no haces check-in en X días, se activa una acción
- Ideal para testamentos digitales y herencias
- Comando: `python manage.py check_triggers`

### 📍 Geocercas
- Restringe la firma a ubicaciones GPS específicas
- Ej: solo se puede firmar estando en la oficina

### 👥 Modo Testigo
- Un tercero verifica tu identidad en vivo vía WebRTC
- Sin necesidad de cuenta
- Queda registro del testigo y sus notas

### ⛓️ Blockchain
- Cada firma se ancla a Polygon/Ethereum
- Hash de transacción visible en el detalle
- Verificable por cualquier juez

### ⚖️ Panel Judicial
- Público, sin autenticación
- Buscar documentos por hash SHA-256
- Reporte imprimible con todos los datos de la firma

---

## 🛠️ Instalación para desarrollo

```powershell
# 1. Clonar
git clone <repo> trustbridge
cd trustbridge

# 2. Entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Migrar base de datos
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser

# 6. Correr servidor
python manage.py runserver
```

## 🌐 PythonAnywhere (demo)

```powershell
# 1. Subir archivos (sin venv)
# 2. En PythonAnywhere consola:
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# 3. En Web tab:
#   Source code: /home/tuusuario/trustbridge
#   Working directory: /home/tuusuario/trustbridge
#   WSGI config file: /var/www/tuusuario_pythonanywhere_com_wsgi.py
#      -> apuntar a trustbridge.wsgi.application

# 4. Static files:
#   URL: /static/
#   Path: /home/tuusuario/trustbridge/staticfiles
python manage.py collectstatic
```

## 🔧 Variables de entorno

| Variable                  | Obligatoria | Descripción                                  |
|--------------------------|-------------|----------------------------------------------|
| `DJANGO_SECRET_KEY`       | No*         | Clave secreta Django                         |
| `DJANGO_DEBUG`            | No          | `True`/`False`                               |
| `DJANGO_ALLOWED_HOSTS`    | No          | Hosts permitidos separados por coma          |
| `OPENAI_API_KEY`          | No**        | API key de OpenAI para AI Contract Reader    |
| `BLOCKCHAIN_PRIVATE_KEY`  | No**        | Private key de wallet Polygon                |
| `BLOCKCHAIN_RPC_URL`      | No**        | RPC URL de Polygon/Ethereum                  |
| `EMAIL_HOST_USER`         | No          | Correo SMTP                                  |
| `EMAIL_HOST_PASSWORD`     | No          | Password SMTP                                |

*Obligatoria en producción. En desarrollo usa una por defecto.
**Sin estas keys, las features funcionan en modo mock/demo.

## 📁 Estructura del proyecto

```
trustbridge/
├── accounts/                 # App de usuarios
│   ├── models.py             # User, DeviceFingerprint, AuditLog
│   ├── views.py              # Perfil de usuario
│   └── urls.py
├── core/                     # App principal
│   ├── models.py             # Document, Signature, ContractAnalysis,
│   │                         # ContractTrigger, GeoFence, WitnessSession
│   ├── views.py              # Dashboard, upload, sign, analyze,
│   │                         # triggers, geofence, witness, verify
│   ├── services.py           # Blockchain, geocerca, AI, liveness
│   ├── forms.py              # DocumentUploadForm
│   ├── management/commands/  # check_triggers
│   └── urls.py
├── templates/                # Todos los templates HTML
│   ├── base.html
│   ├── account/              # Login, signup
│   ├── two_factor/           # 2FA
│   ├── accounts/             # Profile
│   └── core/                 # Dashboard, upload, detail, sign,
│                             # triggers, geofence, witness, verify
├── trustbridge/              # Configuración Django
│   ├── settings.py
│   └── urls.py
├── media/                    # Archivos subidos
└── manage.py
```

## 🧪 Comandos útiles

```powershell
# Dead Man Switch (programar en cron/Task Scheduler)
python manage.py check_triggers              # ejecutar triggers vencidos
python manage.py check_triggers --dry-run     # solo vista previa

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Recolectar estáticos
python manage.py collectstatic

# Consola Django
python manage.py shell
```

## 📸 Flujo completo (usuario)

1. **Registro** → email + contraseña
2. **Verificar email** → enlace en bandeja de entrada
3. **Configurar 2FA** → escanear QR con Google Authenticator
4. **Dashboard** → vista general
5. **Subir documento** → PDF con hash SHA-256
6. **Analizar con IA** → detecta cláusulas de riesgo
7. **(Opcional) Crear Geocerca** → restringir firma a ubicación GPS
8. **(Opcional) Invitar Testigo** → envía enlace a notario
9. **Firmar** → cámara + GPS + fingerprint + blockchain
10. **Verificar** → cualquiera puede buscar por hash en el panel judicial

## 📄 Licencia

Uso interno / SaaS. Todos los derechos reservados.

---

> Hecho con ❤️ por TrustBridge — 2026
