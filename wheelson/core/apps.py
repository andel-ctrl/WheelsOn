"""
WheelsOn Core - App Configuration

Configura la conexion con Neo4j al iniciar la aplicacion Django.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'WheelsOn Core'

    def ready(self):
        """
        Inicializa la conexion con Neo4j usando neomodel.
        Se ejecuta una sola vez cuando Django carga la aplicacion.
        """
        from django.conf import settings

        try:
            from neomodel import config as neomodel_config
            neomodel_config.DATABASE_URL = settings.NEOMODEL_NEO4J_BOLT_URL
            neomodel_config.ENCRYPTED = settings.NEOMODEL_ENCRYPTED
            print(f"[WheelsOn] Neo4j configurado con endpoint: {settings.NEOMODEL_NEO4J_BOLT_URL.split('@')[-1]}")
        except Exception as e:
            print(f"[WheelsOn] AVISO: Configurando fallback Neo4j: {e}")
