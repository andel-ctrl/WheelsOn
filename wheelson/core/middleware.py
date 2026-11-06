"""
Muestra un error claro cuando la app no puede usar Neo4j, en lugar de un error
genérico de Django.
"""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable, SessionExpired, TransientError


def _motivo_del_fallo(error):
    """Devuelve 'credenciales' o 'conexion', o None si el error no es de disponibilidad."""
    if isinstance(error, AuthError):
        return "credenciales"
    if isinstance(error, Neo4jError) and str(error.code or "").startswith("Neo.ClientError.Security"):
        return "credenciales"
    if isinstance(error, (ServiceUnavailable, SessionExpired)):
        return "conexion"
    return None


def _respuesta_sin_neo4j(request, motivo):
    if request.path.startswith("/grafo/api/"):
        return JsonResponse({"error": "Neo4j no está disponible.", "motivo": motivo}, status=503)
    # Sin request: la página no debe consultar Neo4j para dibujarse.
    html = render_to_string("errores/neo4j_no_disponible.html", {"motivo": motivo})
    return HttpResponse(html, status=503)


class SesionRequeridaMiddleware:
    """Exige sesión en toda la app, salvo iniciar sesión y registrarse, y carga al usuario actual."""

    RUTAS_PUBLICAS = ("/login/", "/registro/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        from core.permisos import Permisos
        from core.services import UsuarioService

        request.usuario = None
        request.permisos = Permisos(None)
        if request.path.startswith(settings.STATIC_URL):
            return None

        uid = request.session.get("active_user_uid")
        try:
            if uid and settings.WHEELSON_MODO_DEMO and request.GET.get("as_user"):
                # Cambiar de perspectiva: atajo para probar la demo, desactivado fuera de ella
                destino = UsuarioService.get(request.GET["as_user"])
                if destino:
                    uid = destino.uid
                    request.session["active_user_uid"] = uid
            usuario = UsuarioService.get(uid) if uid else None
        except Exception as error:
            motivo = _motivo_del_fallo(error)
            if motivo is None:
                raise
            return _respuesta_sin_neo4j(request, motivo)

        if usuario:
            request.usuario = usuario
            request.permisos = Permisos(usuario)
            return None

        if uid:  # la cuenta de esta sesión ya no existe
            request.session.flush()
        if request.path in self.RUTAS_PUBLICAS:
            return None
        if request.path.startswith("/grafo/api/"):
            return JsonResponse({"error": "Inicia sesión para continuar."}, status=401)
        return redirect_to_login(request.get_full_path(), login_url="/login/")


class Neo4jNoDisponibleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, TransientError):
            messages.error(request, "Hubo mucha actividad al mismo tiempo y no se guardó. Intenta de nuevo.")
            anterior = request.META.get("HTTP_REFERER", "")
            if anterior and url_has_allowed_host_and_scheme(anterior, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(anterior)
            return redirect("/")
        motivo = _motivo_del_fallo(exception)
        if motivo is None:
            return None

        return _respuesta_sin_neo4j(request, motivo)
