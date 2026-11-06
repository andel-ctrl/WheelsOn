"""
Muestra un error claro cuando la app no puede usar Neo4j, en lugar de un error
genérico de Django.
"""

from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable, SessionExpired


def _motivo_del_fallo(error):
    """Devuelve 'credenciales' o 'conexion', o None si el error no es de disponibilidad."""
    if isinstance(error, AuthError):
        return "credenciales"
    if isinstance(error, Neo4jError) and str(error.code or "").startswith("Neo.ClientError.Security"):
        return "credenciales"
    if isinstance(error, (ServiceUnavailable, SessionExpired)):
        return "conexion"
    return None


class Neo4jNoDisponibleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        motivo = _motivo_del_fallo(exception)
        if motivo is None:
            return None

        if request.path.startswith("/grafo/api/"):
            return JsonResponse({"error": "Neo4j no está disponible.", "motivo": motivo}, status=503)

        # Sin request: la página no debe consultar Neo4j para dibujarse.
        html = render_to_string("errores/neo4j_no_disponible.html", {"motivo": motivo})
        return HttpResponse(html, status=503)
