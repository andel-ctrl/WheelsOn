from core.services import (
    UsuarioService,
    ConexionService,
    HabilidadUsuarioService,
    ParticipacionProyectoService,
)


def social_context(request):
    """
    Context processor para proveer la sesion social activa,
    el usuario actual y su red de contactos a todas las plantillas.
    """
    all_users = UsuarioService.all()
    if not all_users:
        return {
            "current_user": None,
            "current_user_handle": "@usuario",
            "current_user_connections_count": 0,
            "current_user_skills_count": 0,
            "all_users_for_switch": [],
            "dev_mode": request.session.get("dev_mode", False),
        }

    # Permitir alternar de usuario mediante ?as_user=uid
    req_user_uid = request.GET.get("as_user")
    if req_user_uid and UsuarioService.get(req_user_uid):
        request.session["active_user_uid"] = req_user_uid

    active_uid = request.session.get("active_user_uid")
    current_user = UsuarioService.get(active_uid) if active_uid else None

    # Si la ruta es login o registro y no hay sesión activa, no forzar login automático
    if not current_user and request.path in ["/login/", "/registro/"]:
        return {
            "current_user": None,
            "current_user_handle": "@invitado",
            "current_user_connections_count": 0,
            "current_user_skills_count": 0,
            "current_user_projects_count": 0,
            "all_users_for_switch": all_users,
            "dev_mode": request.session.get("dev_mode", False),
        }

    # Si no hay usuario en sesion, fijar usr_carlos001 o el primero de la lista
    if not current_user:
        current_user = UsuarioService.get("usr_carlos001") or all_users[0]
        request.session["active_user_uid"] = current_user.uid

    # Toggle de modo dev (inspector Cypher)
    if "toggle_dev" in request.GET:
        request.session["dev_mode"] = not request.session.get("dev_mode", False)

    handle = f"@{current_user.nombre.lower()}.{current_user.apellido.lower()}"
    connections = ConexionService.listar(current_user.uid)
    skills = HabilidadUsuarioService.listar_por_usuario(current_user.uid)
    projects = ParticipacionProyectoService.listar_por_usuario(current_user.uid)

    return {
        "current_user": current_user,
        "current_user_handle": handle,
        "current_user_connections_count": len(connections),
        "current_user_skills_count": len(skills),
        "current_user_projects_count": len(projects),
        "all_users_for_switch": all_users[:10],
        "dev_mode": request.session.get("dev_mode", False),
    }
