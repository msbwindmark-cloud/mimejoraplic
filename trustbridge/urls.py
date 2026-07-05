"""
URL configuration for trustbridge project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from two_factor.urls import urlpatterns as tf_urls
from core.views import landing

FAVICON_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#2c3e50"/><path d="M50 20 L75 35 V60 L50 80 L25 60 V35 Z" fill="#18bc9c"/><path d="M42 50 L48 56 L58 44" stroke="#ffffff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>'''

urlpatterns = [
    path('', landing, name='landing'),
    path('favicon.ico', lambda r: HttpResponse(FAVICON_SVG, content_type='image/svg+xml')),
    path('static/favicon.ico', lambda r: HttpResponse(FAVICON_SVG, content_type='image/svg+xml')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    path('', include(tf_urls)),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
