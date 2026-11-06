from django.utils.text import slugify
from django.conf import settings
from django.urls import reverse

from core.permisos import Permisos
from core.presentacion import avisos_para
from core.services import (
    UsuarioService,
    ConexionService,
    HabilidadUsuarioService,
    ParticipacionProyectoService,
)


def social_context(request):
    """Usuario actual, sus permisos y su resumen, disponibles en todas las plantillas."""
    current_user = getattr(request, "usuario", None)
    contexto = {
        "current_user": current_user,
        "permisos": getattr(request, "permisos", Permisos(None)),
        "modo_demo": settings.WHEELSON_MODO_DEMO,
    }
    if not current_user:
        return contexto

    avisos = avisos_para(current_user.uid)
    for aviso in avisos:
        if "url" not in aviso:
            aviso["url"] = reverse(aviso["url_nombre"], kwargs=aviso["url_clave"]) + aviso.get("url_sufijo", "")

    contexto.update({
        "avisos": avisos,
        "current_user_handle": f"@{slugify(current_user.nombre)}.{slugify(current_user.apellido)}",
        "current_user_connections_count": len(ConexionService.listar(current_user.uid)),
        "current_user_skills_count": len(HabilidadUsuarioService.listar_por_usuario(current_user.uid)),
        "current_user_projects_count": len(ParticipacionProyectoService.listar_por_usuario(current_user.uid)),
        "all_users_for_switch": UsuarioService.all() if settings.WHEELSON_MODO_DEMO else [],
    })
    return contexto
