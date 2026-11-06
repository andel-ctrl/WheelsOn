"""
Soporte para probar la app contra un Neo4j real y separado del de desarrollo.

Los tests borran toda la base antes de cada prueba, así que el ejecutor se niega
a correr si la dirección de pruebas es la misma de la base de desarrollo.

Base de pruebas:
    docker run -d --name wheelson-neo4j-test -p 7688:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.test.runner import DiscoverRunner
from neomodel import db

SCRIPTS = Path(settings.BASE_DIR).parent / "scripts"
_base_de_pruebas_activa = False


def ejecutar_script_cypher(nombre):
    """Ejecuta un archivo de scripts/, sentencia por sentencia."""
    lineas = (
        linea for linea in (SCRIPTS / nombre).read_text(encoding="utf-8").splitlines()
        if not linea.strip().startswith("//")
    )
    for sentencia in "\n".join(lineas).split(";\n"):
        sentencia = sentencia.strip().rstrip(";")
        if sentencia:
            db.cypher_query(sentencia)


class Neo4jTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        global _base_de_pruebas_activa
        super().setup_test_environment(**kwargs)

        url = os.getenv("NEO4J_TEST_BOLT_URL", "bolt://neo4j:password@localhost:7688")
        if url == settings.NEOMODEL_NEO4J_BOLT_URL:
            raise ImproperlyConfigured(
                "NEO4J_TEST_BOLT_URL debe apuntar a una base distinta: los tests borran todos sus datos."
            )

        # Los tests corren sin DEBUG; así no hace falta ejecutar collectstatic antes.
        self._estaticos = override_settings(STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        })
        self._estaticos.enable()

        db.close_connection()
        db.set_connection(url=url)
        ejecutar_script_cypher("init_db.cypher")
        _base_de_pruebas_activa = True

    def teardown_test_environment(self, **kwargs):
        global _base_de_pruebas_activa
        _base_de_pruebas_activa = False
        db.close_connection()
        self._estaticos.disable()
        super().teardown_test_environment(**kwargs)


class Neo4jTestCase(TestCase):
    """Cada prueba empieza con la base de pruebas vacía."""

    def run(self, result=None):
        # Se limpia aquí y no en setUp para que aplique aunque la prueba defina el suyo.
        if not _base_de_pruebas_activa:
            raise ImproperlyConfigured("Ejecuta los tests con Neo4jTestRunner (python manage.py test).")
        db.cypher_query("MATCH (n) DETACH DELETE n")
        return super().run(result)
