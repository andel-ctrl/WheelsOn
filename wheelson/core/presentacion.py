"""
Datos que solo existen para presentar la interfaz: las imágenes del feed y el panel
de notificaciones. Nada de esto se guarda en Neo4j.
"""

import hashlib

from django.urls import reverse
from django.utils.formats import date_format, number_format

from core.recommendations import RecommendationEngine
from core.services import ConexionService, EmpleoService, InvitacionService, NotificacionService, PostulacionService, a_fecha

# Ilustraciones del feed. Para cambiarlas, reemplaza los archivos y ajusta esta lista.
IMAGENES_FEED = tuple(f"img/feed/feed-{numero}.webp" for numero in range(1, 7))
MAX_AVISOS = 12


def imagen_para(identificador):
    """Asigna una ilustración según el identificador: siempre la misma para cada elemento."""
    resumen = hashlib.md5(str(identificador).encode("utf-8")).digest()
    return IMAGENES_FEED[resumen[0] % len(IMAGENES_FEED)]


def imagen_de_publicacion(identificador):
    """
    No todas las publicaciones llevan imagen, como en una red real. La decisión depende del
    identificador para que cada publicación se vea siempre igual.
    """
    resumen = hashlib.md5(str(identificador).encode("utf-8")).digest()
    return imagen_para(identificador) if resumen[1] % 2 else None


def tejer_feed(elementos):
    """Intercala los tipos de publicación para que el feed no agrupe todo lo igual."""
    por_tipo = {}
    for elemento in elementos:
        por_tipo.setdefault(elemento["tipo"], []).append(elemento)
    colas = [por_tipo.get(tipo, []) for tipo in ("publicacion", "proyecto", "oferta", "avance", "conexion")]
    feed = []
    while any(colas):
        for cola in colas:
            if cola:
                feed.append(cola.pop(0))
    return feed


def avisos_para(uid, limite=MAX_AVISOS):
    """
    Avisos del panel de notificaciones, derivados de lo que ya hay en el grafo. No hay
    eventos ni modelo propio: cada aviso es un hecho consultable en este momento.
    """
    if not uid:
        return []

    avisos = []
    # Lo que espera tu respuesta va primero
    for solicitud in InvitacionService.solicitudes_recibidas(uid):
        otro = solicitud["usuario"]
        avisos.append({
            "id": f"solicitud:{otro.uid}",
            "tipo": "conexion",
            "icono": "users",
            "titulo": f"{otro.nombre_completo} quiere conectar contigo",
            "detalle": solicitud["mensaje"] or (otro.titulo_profesional or ""),
            "fecha": solicitud["fecha"],
            "url_nombre": "core:conexiones_red",
            "url_clave": {},
            "pendiente": True,
        })
    TITULOS_INVITACION = {
        "colaborar": "Te invitaron a colaborar en {}",
        "liderar": "Te proponen liderar {}",
        "administrar": "Te proponen administrar {}",
    }
    for invitacion in InvitacionService.invitaciones_de(uid):
        avisos.append({
            "id": f"invitacion:{invitacion['tipo']}:{invitacion.get('pid') or invitacion.get('eid')}",
            "tipo": "conexion",
            "icono": "briefcase",
            "titulo": TITULOS_INVITACION[invitacion["tipo"]].format(invitacion["nombre"]),
            "detalle": invitacion["rol"],
            "fecha": invitacion["fecha"],
            "url_nombre": "core:conexiones_red",
            "url_clave": {},
            "pendiente": True,
        })
    for solicitud in InvitacionService.solicitudes_union_para_lider(uid):
        avisos.append({
            "id": f"union:{solicitud['proyecto'].pid}:{solicitud['usuario'].uid}",
            "tipo": "conexion",
            "icono": "users",
            "titulo": f"{solicitud['usuario'].nombre_completo} quiere unirse a {solicitud['proyecto'].nombre}",
            "detalle": solicitud["usuario"].titulo_profesional or "",
            "fecha": solicitud["fecha"],
            "url_nombre": "core:proyecto_detalle",
            "url_clave": {"pid": solicitud["proyecto"].pid},
            "pendiente": True,
        })
    for solicitud in EmpleoService.solicitudes_para_administrador(uid):
        avisos.append({
            "id": f"empleo-pendiente:{solicitud['empresa'].eid}:{solicitud['usuario'].uid}",
            "tipo": "conexion",
            "icono": "briefcase",
            "titulo": f"{solicitud['usuario'].nombre_completo} pide confirmar su empleo en {solicitud['empresa'].nombre}",
            "detalle": solicitud["cargo"] or "",
            "fecha": solicitud["fecha"],
            "url_nombre": "core:empresa_detalle",
            "url_clave": {"eid": solicitud["empresa"].eid},
            "url_sufijo": "?tab=gestion",
            "pendiente": True,
        })
    for invitacion in EmpleoService.invitaciones_de_usuario(uid):
        avisos.append({
            "id": f"invitacion_equipo:{invitacion['empresa'].eid}",
            "tipo": "empleo",
            "icono": "briefcase",
            "titulo": f"{invitacion['empresa'].nombre} te invita a su equipo",
            "detalle": invitacion["cargo"] or "",
            "fecha": invitacion["fecha"],
            "url_nombre": "core:conexiones_red",
            "url_clave": {},
            "pendiente": True,
        })
    for nueva in PostulacionService.nuevas_para_administrador(uid):
        avisos.append({
            "id": f"candidato:{nueva['oferta'].oid}:{nueva['usuario'].uid}",
            "tipo": "postulacion",
            "icono": "paper-plane-tilt",
            "titulo": f"Nueva postulación a {nueva['oferta'].titulo}",
            "detalle": nueva["usuario"].nombre_completo,
            "fecha": nueva["fecha"],
            "url_nombre": "core:oferta_detalle",
            "url_clave": {"oid": nueva["oferta"].oid},
            "pendiente": True,
        })

    # Lo que ya pasó y te afecta: respuestas, cambios y eliminaciones
    for notificacion in NotificacionService.de_usuario(uid):
        avisos.append({
            "id": f"notificacion:{notificacion['nid']}",
            "tipo": "conexion",
            "icono": notificacion["icono"],
            "titulo": notificacion["titulo"],
            "detalle": notificacion["detalle"],
            "fecha": notificacion["fecha"],
            "url": notificacion["url"] or reverse("core:dashboard"),
            "orden": notificacion["creada"],
        })

    for conexion in ConexionService.listar(uid):
        otro = conexion["usuario"]
        avisos.append({
            "id": f"conexion:{otro.uid}",
            "tipo": "conexion",
            "icono": "users",
            "titulo": f"Conexión con {otro.nombre_completo}",
            "detalle": otro.titulo_profesional or "",
            "fecha": conexion["fecha"],
            "url_nombre": "core:usuario_detalle",
            "url_clave": {"uid": otro.uid},
        })
    for postulacion in PostulacionService.listar_por_usuario(uid):
        oferta = postulacion["oferta"]
        avisos.append({
            # Con el estado en el identificador, cada cambio vuelve a marcarse como nuevo
            "id": f"postulacion:{oferta.oid}:{postulacion['estado']}",
            "tipo": "postulacion",
            "icono": "paper-plane-tilt",
            "titulo": f"Te postulaste a {oferta.titulo}",
            "detalle": f"Estado: {postulacion['estado_texto']}",
            "fecha": postulacion["fecha_estado"],
            "url_nombre": "core:oferta_detalle",
            "url_clave": {"oid": oferta.oid},
        })
    for empleo in RecommendationEngine.recomendar_empleos(uid, limit=3):
        oferta = empleo["oferta"]
        empresa = empleo["empresa"].nombre if empleo["empresa"] else "Empresa sin asignar"
        avisos.append({
            "id": f"empleo:{oferta.oid}",
            "tipo": "empleo",
            "icono": "briefcase",
            "titulo": f"Empleo compatible: {oferta.titulo}",
            "detalle": f"{number_format(empleo['match_porcentaje'], 1)} % de compatibilidad · {empresa}",
            "fecha": str(oferta.fecha_publicacion or ""),
            "url_nombre": "core:oferta_detalle",
            "url_clave": {"oid": oferta.oid},
        })

    avisos.sort(key=lambda aviso: (aviso.get("pendiente", False), aviso["fecha"], aviso.get("orden", 0), aviso["id"]), reverse=True)
    avisos = avisos[:limite]
    for aviso in avisos:
        fecha = a_fecha(aviso["fecha"])
        aviso["fecha_texto"] = date_format(fecha, "j M Y") if fecha else ""
    return avisos
