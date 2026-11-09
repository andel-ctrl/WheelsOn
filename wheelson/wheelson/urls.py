"""
WheelsOn - URL Configuration
"""

from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
]

handler404 = "core.views.no_encontrado"
handler500 = "core.views.error_del_servidor"
