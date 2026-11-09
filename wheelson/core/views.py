from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from neomodel import UniqueProperty
from core.forms import (
    UsuarioForm,
    EmpresaForm,
    HabilidadForm,
    ProyectoForm,
    OfertaForm,
    AvanceForm,
    ConectarUsuarioForm,
    PublicacionForm,
    VincularHabilidadUsuarioForm,
    ExperienciaLaboralForm,
    ParticipacionProyectoForm,
    PublicarOfertaEmpresaForm,
    RequisitoOfertaForm,
    PostulacionForm,
    LoginForm,
    RegistroForm,
)
from datetime import date

from core.models import ESTADOS_EN_PROCESO, ESTADOS_FINALES, ESTADOS_POSTULACION, ESTADOS_PROYECTO
from django.urls import reverse
from core.services import (
    a_fecha,
    AvanceService,
    InvitacionService,
    NotificacionService,
    PublicacionService,
    PropiedadService,
    UsuarioService,
    EmpresaService,
    HabilidadService,
    ProyectoService,
    OfertaService,
    ConexionService,
    EmpleoService,
    HabilidadUsuarioService,
    ParticipacionProyectoService,
    PublicacionOfertaService,
    RequisitoOfertaService,
    PostulacionService,
)
from core.graph_queries import GraphAnalyticsService
from core.recommendations import RecommendationEngine
from core.analytics import NetworkAnalyticsService
from core.graph_viz import GrafoVisualizacionService
from core.permisos import exigir
from core.presentacion import imagen_de_publicacion, tejer_feed


def _volver(request, respaldo, ancla=""):
    """Regresa a la página anterior solo si pertenece a esta misma app."""
    anterior = request.META.get("HTTP_REFERER", "")
    if anterior and url_has_allowed_host_and_scheme(anterior, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(anterior + ancla)
    return redirect(reverse(respaldo) + ancla)


def _texto(request, campo, maximo):
    """Texto libre de un formulario: sin espacios sobrantes, sin caracteres de control y con tope."""
    valor = "".join(c for c in request.POST.get(campo, "") if c in "\n\t" or c.isprintable())
    return valor.strip()[:maximo]


def _url(nombre, **claves):
    return reverse(f"core:{nombre}", kwargs=claves)


def _avisar(request, uid, titulo, detalle="", url="", icono="bell"):
    """Notifica a otra persona. Nadie recibe aviso de lo que hizo él mismo."""
    if uid and uid != request.permisos.uid:
        NotificacionService.crear(uid, titulo, detalle, url, icono)


def _respondio(aceptar):
    return ("aceptó", "check-circle") if aceptar else ("rechazó", "x")


def _primer_error(formulario):
    return next(iter(formulario.errors.values()))[0]


def _con_permisos(publicaciones, permisos):
    for publicacion in publicaciones:
        autor = {"uid": publicacion["autor"].uid if publicacion["autor"] else None, "eid": publicacion["empresa"].eid if publicacion["empresa"] else None}
        publicacion["puede_eliminar"] = permisos.gestionar_publicacion(autor)
    return publicaciones


def _administra_empresa(uid, eid):
    administrador = PropiedadService.administrador_de(eid)
    return bool(administrador) and administrador.uid == uid


def _es_lider(uid, pid):
    lider = PropiedadService.lider_de(pid)
    return bool(lider) and lider.uid == uid


def _respuesta(request):
    """True si acepta, False si rechaza, None si la petición no trae una respuesta válida."""
    return {"aceptar": True, "rechazar": False}.get(request.POST.get("accion"))


def dashboard(request):
    all_users = UsuarioService.all()
    current_user = request.usuario
    uid_ref = current_user.uid

    if request.method == "POST":
        form = PublicacionForm(request.POST)
        if form.is_valid():
            como = request.POST.get("como") or None
            if como:
                exigir(request.permisos.gestionar_empresa(como), "Solo puedes publicar a nombre de empresas que administras.")
            if PublicacionService.crear(current_user.uid, form.cleaned_data["texto"], eid=como):
                messages.success(request, "La publicación ya está en el feed.")
            else:
                messages.error(request, "No se pudo publicar.")
        else:
            messages.error(request, _primer_error(form))
        return redirect("core:dashboard")

    # Construccion del Muro de Novedades (Feed Social Dinamico de Eventos del Grafo)
    feed_items = []

    # Publicaciones de las personas
    for publicacion in _con_permisos(PublicacionService.recientes(uid_ref), request.permisos):
        feed_items.append({"tipo": "publicacion", "fecha": publicacion["publicacion"].fecha, **publicacion})

    # Avances de los proyectos
    for avance in AvanceService.recientes():
        feed_items.append({"tipo": "avance", "fecha": avance["avance"].fecha, **avance})

    # 1. Novedades de Proyectos (Proof of Work)
    proyectos = ProyectoService.all()
    for p in proyectos:
        feed_items.append({
            "tipo": "proyecto",
            "proyecto": p,
            "fecha": getattr(p, "fecha_inicio", "") or "Reciente",
            "imagen": imagen_de_publicacion(p.pid),
            "orden": 1,
        })

    # 2. Oportunidades Laborales con Match de Habilidades
    mis_habilidades = set()
    if uid_ref:
        mis_habilidades = {
            str(h["habilidad"].hid)
            for h in HabilidadUsuarioService.listar_por_usuario(uid_ref)
        }

    ofertas = OfertaService.all()
    # Empresa, requisitos y postulaciones de todos los empleos de una vez, no uno por uno
    detalle_abiertas = RequisitoOfertaService.de_ofertas_abiertas()
    postuladas = PostulacionService.ofertas_postuladas(uid_ref)
    for o in ofertas:
        if o.estado == "abierta":
            empresa, reqs = detalle_abiertas.get(o.oid, (None, []))
            for r in reqs:
                r["tengo"] = str(r["habilidad"].hid) in mis_habilidades
            match_count = sum(1 for r in reqs if r["tengo"])
            match_pct = round((match_count / len(reqs)) * 100, 1) if reqs else 0
            feed_items.append({
                "tipo": "oferta",
                "oferta": o,
                "empresa": empresa,
                "requisitos": reqs,
                "match_count": match_count,
                "match_pct": match_pct,
                "ya_postulado": o.oid in postuladas,
                "es_propia": o.oid in request.permisos.ofertas_administradas,
                "fecha": getattr(o, "fecha_publicacion", "") or "Reciente",
                "orden": 2 if match_pct > 0 else 4,
            })

    # 3. Hitos de Conexion en la Red
    for u in all_users[:4]:
        conns = ConexionService.listar(u.uid)
        for c in conns[:1]:
            if str(u.uid) < str(c["usuario"].uid):  # Evitar duplicar arista bidireccional
                feed_items.append({
                    "tipo": "conexion",
                    "u1": u,
                    "u2": c["usuario"],
                    "mensaje": c.get("mensaje", ""),
                    "fecha": a_fecha(c.get("fecha")) or "Reciente",
                    "orden": 3,
                })

    # Las ofertas más compatibles van primero; después se intercalan los tipos
    feed_items.sort(key=lambda x: -x.get("match_pct", 0))
    feed_items = tejer_feed(feed_items)
    tipos_feed = [("", "Todo"), ("publicacion", "Publicaciones"), ("proyecto", "Proyectos"), ("oferta", "Empleos"), ("avance", "Avances"), ("conexion", "Conexiones")]
    ver = request.GET.get("ver", "")
    if ver in {tipo for tipo, _ in tipos_feed[1:]}:
        feed_items = [item for item in feed_items if item["tipo"] == ver]
    else:
        ver = ""
    total_feed = len(feed_items)
    pag = _paginacion(request, 8)
    feed_items = _recortar(feed_items, pag)

    # El equipo y el líder de cada proyecto se consultan solo para los que se van a mostrar
    for item in feed_items:
        if item["tipo"] == "proyecto":
            proyecto = item["proyecto"]
            item["autor"] = PropiedadService.lider_de(proyecto.pid)
            item["colaboradores"] = [c["usuario"] for c in ParticipacionProyectoService.listar_por_proyecto(proyecto.pid)]
            item["tecnologias"] = [str(t).strip() for t in (proyecto.tecnologias or []) if str(t).strip()]

    context = {
        "feed_items": feed_items,
        "tipos_feed": tipos_feed,
        "ver": ver,
    }
    if not pag["fragmento"]:
        context.update({
            "app_name": "WheelsOn",
            "page_title": "Feed Social | WheelsOn",
            "mis_contactos": ConexionService.listar(uid_ref) if uid_ref else [],
            "empleos_sugeridos": RecommendationEngine.recomendar_empleos(uid_ref, limit=3) if uid_ref else [],
            "empresas_para_publicar": [EmpresaService.get(eid) for eid in sorted(request.permisos.empresas_administradas)],
        })
    return _responder_lista(request, "dashboard.html", "componentes/feed_items.html", "lista-feed", context, pag, total_feed)



# ==============================================================================
# PUBLICACIONES
# ==============================================================================

def publicacion_percibir(request, pubid):
    if request.method == "POST" and not PublicacionService.percibir(request.permisos.uid, pubid, request.POST.get("tipo")):
        messages.error(request, "No se pudo registrar tu percepción.")
    return _volver(request, "core:dashboard", ancla=f"#pub-{pubid}")


def publicacion_eliminar(request, pubid):
    autor = PublicacionService.autor_de(pubid)
    if not autor:
        messages.error(request, "Publicación no encontrada.")
        return redirect("core:dashboard")
    exigir(request.permisos.gestionar_publicacion(autor), "Solo quien la publicó puede eliminarla.")
    if request.method == "POST":
        PublicacionService.delete(pubid)
        _avisar(request, autor["uid"], "Un administrador eliminó una de tus publicaciones", icono="x")
        messages.success(request, "Publicación eliminada.")
    return _volver(request, "core:dashboard")


# ==============================================================================
# CRUD USUARIOS
# ==============================================================================

def usuarios_lista(request):
    query = request.GET.get("q", "").strip().lower()
    pag = _paginacion(request, 8)
    usuarios, total = UsuarioService.pagina(query, pag["skip"], pag["limit"])
    contexto = {"usuarios": _con_grado(usuarios), "query": query}
    return _responder_lista(request, "usuarios/lista.html", "usuarios/_items.html", "lista-personas", contexto, pag, total)


def usuario_crear(request):
    exigir(request.permisos.crear_usuario(), "Solo un administrador puede crear cuentas. Cada persona puede registrarse por su cuenta.")
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if not request.POST.get("password"):
            form.add_error("password", "Define una contraseña para la cuenta.")
        if form.is_valid():
            try:
                u = UsuarioService.create(**form.cleaned_data)
            except UniqueProperty:
                form.add_error("email", "Ya existe un usuario con este correo.")
            else:
                messages.success(request, f"Usuario '{u.nombre_completo}' registrado exitosamente.")
                return redirect("core:usuario_detalle", uid=u.uid)
    else:
        form = UsuarioForm()
    return render(request, "usuarios/formulario.html", {"form": form, "accion": "Crear"})


def usuario_detalle(request, uid):
    usuario = UsuarioService.get(uid)
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:usuarios_lista")

    permisos = request.permisos
    empleos = EmpleoService.listar_por_usuario(uid)
    for empleo in empleos:
        # Quien administra la empresa no se ofrece como quitable: primero debe transferirla
        empleo["puede_quitar"] = permisos.quitar_empleo(uid, empleo["empresa"].eid) and not _administra_empresa(uid, empleo["empresa"].eid)
    proyectos = ParticipacionProyectoService.listar_por_usuario(uid)
    for participacion in proyectos:
        pid_proyecto = participacion["proyecto"].pid
        participacion["puede_quitar"] = permisos.quitar_colaborador(uid, pid_proyecto) and not _es_lider(uid, pid_proyecto)

    es_propio = permisos.uid == uid
    estado_conexion = None if es_propio else InvitacionService.estado_conexion(permisos.uid, uid)
    pids_propios = {participacion["proyecto"].pid for participacion in proyectos}
    context = {
        "usuario": usuario,
        "es_propio": es_propio,
        "puede_editar": permisos.editar_usuario(uid),
        "puede_conectar": not es_propio and estado_conexion is None,
        "solicitud_enviada": estado_conexion == "enviada",
        "solicitud_recibida": estado_conexion == "recibida",
        "publicaciones_rel": _con_permisos(PublicacionService.de_usuario(uid, permisos.uid), permisos),
        # Lo que la empresa aún no confirma solo lo ve la persona
        "empleos_pendientes": EmpleoService.solicitudes_de_usuario(uid) if permisos.editar_usuario(uid) else [],
        "empresas_que_administra": list(usuario.empresas_administradas.all()),
        "habilidades_rel": HabilidadUsuarioService.listar_por_usuario(uid),
        "empleos_rel": empleos,
        "proyectos_rel": proyectos,
        "conexiones_rel": ConexionService.listar(uid),
        # Las postulaciones son privadas: solo las ve la persona o un administrador
        "postulaciones_rel": PostulacionService.listar_por_usuario(uid) if permisos.editar_usuario(uid) else [],
        "todas_habilidades": HabilidadService.all(),
        "todas_empresas": EmpresaService.all(),
        "proyectos_vinculables": [p for p in ProyectoService.all() if permisos.gestionar_proyecto(p.pid) and p.pid not in pids_propios],
    }
    return render(request, "usuarios/detalle.html", context)


def usuario_editar(request, uid):
    usuario = UsuarioService.get(uid)
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:usuarios_lista")
    exigir(request.permisos.editar_usuario(uid), "Solo puedes editar tu propio perfil.")
    verificar = usuario if uid == request.permisos.uid else None

    if request.method == "POST":
        form = UsuarioForm(request.POST, verificar_clave_de=verificar)
        if form.is_valid():
            data = form.cleaned_data
            if not data.get("password"):
                data.pop("password", None)
            try:
                UsuarioService.update(uid, **data)
            except UniqueProperty:
                form.add_error("email", "Ya existe un usuario con este correo.")
            else:
                _avisar(request, uid, "Un administrador actualizó tu perfil", url=_url("usuario_detalle", uid=uid))
                messages.success(request, f"Perfil de '{usuario.nombre_completo}' actualizado.")
                return redirect("core:usuario_detalle", uid=uid)
    else:
        form = UsuarioForm(verificar_clave_de=verificar, initial={
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "email": usuario.email,
            "titulo_profesional": usuario.titulo_profesional,
            "ubicacion": usuario.ubicacion,
            "biografia": usuario.biografia,
        })
    return render(request, "usuarios/formulario.html", {"form": form, "usuario": usuario, "accion": "Editar"})


def usuario_eliminar(request, uid):
    usuario = UsuarioService.get(uid)
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:usuarios_lista")
    exigir(request.permisos.editar_usuario(uid), "Solo puedes eliminar tu propia cuenta.")

    pendientes = PropiedadService.pendientes_de_transferir(uid)
    ultimo_admin = UsuarioService.es_ultimo_admin(uid)
    if request.method == "POST":
        if ultimo_admin:
            messages.error(request, "No se puede eliminar al único administrador de la plataforma.")
            return redirect("core:usuario_detalle", uid=uid)
        if pendientes:
            messages.error(request, f"Antes de eliminar la cuenta, transfiere o elimina: {', '.join(pendientes)}.")
            return redirect("core:usuario_detalle", uid=uid)
        nombre = usuario.nombre_completo
        era_propia = uid == request.permisos.uid
        PropiedadService.eliminar_cuenta(uid)
        if era_propia:
            request.session.flush()
            messages.success(request, "Tu cuenta fue eliminada.")
            return redirect("core:login")
        messages.success(request, f"Usuario '{nombre}' eliminado.")
        return redirect("core:usuarios_lista")

    return render(request, "usuarios/confirmar_eliminar.html", {
        "objeto": usuario,
        "tipo": "Usuario",
        "pendientes": pendientes,
        "ultimo_admin": ultimo_admin,
        "proyectos_individuales": PropiedadService.proyectos_individuales(uid),
        "total_publicaciones": PublicacionService.contar_de(uid),
    })


# ==============================================================================
# CRUD EMPRESAS
# ==============================================================================

def empresas_lista(request):
    query = request.GET.get("q", "").strip().lower()
    pag = _paginacion(request, 6)
    empresas, total = EmpresaService.pagina(query, pag["skip"], pag["limit"], uid=request.permisos.uid)
    resumen = EmpresaService.resumen_edificios(ids=[e.eid for e in empresas])
    relaciones = EmpresaService.relacion_de(request.permisos.uid, [e.eid for e in empresas])
    for empresa in empresas:
        empresa.relacion = relaciones.get(empresa.eid)
        empresa.resumen = resumen.get(empresa.eid, {"empleados": 0, "ofertas": 0})
    return _responder_lista(request, "empresas/lista.html", "empresas/_items.html", "lista-empresas", {"empresas": empresas, "query": query}, pag, total)


def empresa_crear(request):
    if request.method == "POST":
        form = EmpresaForm(request.POST)
        if form.is_valid():
            try:
                e = PropiedadService.crear_empresa(request.permisos.uid, **form.cleaned_data)
            except UniqueProperty:
                form.add_error("nombre", "Ya existe una empresa con este nombre.")
            else:
                messages.success(request, f"Empresa '{e.nombre}' creada.")
                return redirect("core:empresa_detalle", eid=e.eid)
    else:
        form = EmpresaForm()
    return render(request, "empresas/formulario.html", {"form": form, "accion": "Crear"})


def empresa_detalle(request, eid):
    empresa = EmpresaService.get(eid)
    if not empresa:
        messages.error(request, "Empresa no encontrada.")
        return redirect("core:empresas_lista")

    permisos = request.permisos
    puede_gestionar = permisos.gestionar_empresa(eid)
    administrador = PropiedadService.administrador_de(eid)
    empleos = EmpleoService.listar_por_empresa(eid)
    equipo = [e for e in empleos if e["actual"] is not False]
    for miembro in equipo:
        miembro["es_administrador"] = bool(administrador) and miembro["usuario"].uid == administrador.uid
    uid = permisos.uid
    if EmpleoService.es_empleado(uid, eid):
        estado_equipo = "miembro"
    elif EmpleoService.invitacion_de(uid, eid):
        estado_equipo = "invitado"
    elif EmpleoService.tiene_solicitud(uid, eid):
        estado_equipo = "solicitada"
    else:
        estado_equipo = None
    context = {
        "empresa": empresa,
        "administrador": administrador,
        "puede_gestionar": puede_gestionar,
        "ofertas_rel": PublicacionOfertaService.listar_por_empresa(eid),
        "equipo": equipo,
        "antiguos": [e for e in empleos if e["actual"] is False],
        "publicaciones_rel": _con_permisos(PublicacionService.de_empresa(eid, permisos.uid), permisos),
        "tab_inicial": request.GET.get("tab") if request.GET.get("tab") in ("publicaciones", "vacantes", "empleados", "gestion") else "info",
        "estado_equipo": estado_equipo,
        "invitacion_equipo": EmpleoService.invitacion_de(uid, eid),
        "es_administrador_empresa": bool(administrador) and administrador.uid == uid,
    }
    if puede_gestionar:
        solicitudes_empleo = EmpleoService.solicitudes_de_empresa(eid)
        invitaciones_equipo = EmpleoService.invitaciones_de_empresa(eid)
        ocupados = {e["usuario"].uid for e in equipo} | {i["usuario"].uid for i in invitaciones_equipo} | {s["usuario"].uid for s in solicitudes_empleo}
        context.update({
            "solicitudes_empleo": solicitudes_empleo,
            "invitaciones_equipo": invitaciones_equipo,
            "personas_para_invitar": [u for u in UsuarioService.all() if u.uid not in ocupados],
            "invitar_uid": request.GET.get("invitar", ""),
            "transferencia_pendiente": InvitacionService.pendiente_de_empresa(eid),
            "candidatos_transferencia": _candidatos_transferencia([e["usuario"] for e in equipo], administrador.uid if administrador else None, permisos),
            "pendientes_gestion": len(solicitudes_empleo),
        })
    return render(request, "empresas/detalle.html", context)


def empresa_editar(request, eid):
    empresa = EmpresaService.get(eid)
    if not empresa:
        messages.error(request, "Empresa no encontrada.")
        return redirect("core:empresas_lista")
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede editarla.")

    if request.method == "POST":
        form = EmpresaForm(request.POST)
        if form.is_valid():
            try:
                EmpresaService.update(eid, **form.cleaned_data)
            except UniqueProperty:
                form.add_error("nombre", "Ya existe una empresa con este nombre.")
            else:
                messages.success(request, f"Empresa '{empresa.nombre}' actualizada.")
                return redirect("core:empresa_detalle", eid=eid)
    else:
        form = EmpresaForm(initial={
            "nombre": empresa.nombre,
            "industria": empresa.industria,
            "ubicacion": empresa.ubicacion,
            "descripcion": empresa.descripcion,
            "sitio_web": empresa.sitio_web,
            "tamano": empresa.tamano,
        })
    return render(request, "empresas/formulario.html", {"form": form, "empresa": empresa, "accion": "Editar"})


def empresa_eliminar(request, eid):
    empresa = EmpresaService.get(eid)
    if not empresa:
        messages.error(request, "Empresa no encontrada.")
        return redirect("core:empresas_lista")
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede eliminarla.")

    if request.method == "POST":
        nombre = empresa.nombre
        afectados = {e["usuario"].uid for e in EmpleoService.listar_por_empresa(eid)}
        for oferta in PublicacionOfertaService.listar_por_empresa(eid):
            afectados |= {c["usuario"].uid for c in PostulacionService.listar_por_oferta(oferta.oid)}
        EmpresaService.delete(eid)
        for uid in afectados:
            _avisar(request, uid, f"La empresa {nombre} fue eliminada", "Se quitaron tu empleo o tus postulaciones relacionados.", icono="x")
        messages.success(request, f"Empresa '{nombre}' eliminada.")
        return redirect("core:empresas_lista")

    return render(request, "empresas/confirmar_eliminar.html", {
        "objeto": empresa,
        "tipo": "Empresa",
        "impacto": EmpresaService.impacto_de_eliminar(eid),
    })


def _con_grado(personas):
    """Agrega a cada persona su grado en el grafo y las 5 marcas de su barra, según el máximo de la red."""
    grados = UsuarioService.grados()
    maximo = max(grados.values(), default=0) or 1
    for persona in personas:
        grado = grados.get(persona.uid, 0)
        llenas = round(grado * 5 / maximo) if grado else 0
        persona.grado = grado
        persona.marcas = [i < max(llenas, 1 if grado else 0) for i in range(5)]
    return personas


def _paginacion(request, por_pagina):
    """
    Qué parte de una lista pide esta petición. Con fragmento=1 son solo los elementos nuevos,
    para sumarlos a la página sin recargarla. Sin él son todos hasta esa página, así un enlace
    o una recarga con ?pagina=3 muestra lo mismo que se veía.
    """
    try:
        pagina = min(max(int(request.GET.get("pagina", 1)), 1), 1000)
    except ValueError:
        pagina = 1
    fragmento = request.GET.get("fragmento") == "1"
    return {
        "pagina": pagina,
        "por_pagina": por_pagina,
        "fragmento": fragmento,
        "skip": (pagina - 1) * por_pagina if fragmento else 0,
        "limit": por_pagina if fragmento else pagina * por_pagina,
    }


def _recortar(lista, pag):
    """Para listas que ya están en memoria: la misma parte que pediría _paginacion a Neo4j."""
    return lista[pag["skip"]:pag["skip"] + pag["limit"]]


def _responder_lista(request, plantilla, parcial, destino, contexto, pag, total):
    """La página completa, o solo los elementos nuevos si los pidió el botón Ver más."""
    mostrados = min(pag["pagina"] * pag["por_pagina"], total)
    contexto.update({"total": total, "destino": destino, "ver_mas": None})
    if mostrados < total:
        parametros = request.GET.copy()
        parametros.pop("fragmento", None)
        parametros["pagina"] = pag["pagina"] + 1
        contexto["ver_mas"] = {
            "url": "?" + parametros.urlencode(),
            "cuantos": min(pag["por_pagina"], total - mostrados),
            "mostrados": mostrados,
        }
    if pag["fragmento"]:
        contexto["parcial"] = parcial
        return render(request, "componentes/fragmento.html", contexto)
    return render(request, plantilla, contexto)


def _preparar_boletos(ofertas, uid):
    """Agrega a cada oferta lo que su pasaje muestra: empresa, compatibilidad y ruta desde esta persona."""
    resumen = OfertaService.resumen_boletos(uid, ids=[o.oid for o in ofertas])
    saltos = ConexionService.saltos_a_empresas(uid)
    for oferta in ofertas:
        datos = resumen.get(oferta.oid, {})
        oferta.b_empresa = datos.get("empresa")
        oferta.b_pct = datos.get("pct")
        oferta.b_postulado = datos.get("postulado", False)
        oferta.b_propia = datos.get("propia", False)
        distancia = saltos.get(oferta.b_empresa.eid) if oferta.b_empresa else None
        if oferta.b_propia:
            oferta.b_ruta = "Es tu empresa"
        elif distancia == 0:
            oferta.b_ruta = "Ya trabajas aquí"
        elif distancia is None:
            oferta.b_ruta = "Sin ruta todavía"
        else:
            oferta.b_ruta = f"{distancia} salto{'s' if distancia != 1 else ''}"
    return ofertas


def _a_gestion(eid):
    return redirect(reverse("core:empresa_detalle", kwargs={"eid": eid}) + "?tab=gestion")


def _candidatos_transferencia(miembros, actual_uid, permisos):
    """Solo se transfiere a un miembro. Un administrador de plataforma también puede asumirlo él mismo."""
    candidatos = [u for u in miembros if u.uid != actual_uid]
    if permisos.es_admin and permisos.uid != actual_uid and all(u.uid != permisos.uid for u in candidatos):
        candidatos.append(permisos.usuario)
    return candidatos


def empresa_transferir(request, eid):
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede transferirla.")
    if request.method == "POST":
        uid = request.POST.get("uid")
        actual = PropiedadService.administrador_de(eid)
        empresa = EmpresaService.get(eid)
        if actual and actual.uid == uid:
            messages.error(request, "Esa persona ya administra la empresa.")
        elif uid == request.permisos.uid:  # un administrador de plataforma la asume él mismo
            PropiedadService.asignar_administrador(uid, eid)
            if actual:
                _avisar(request, actual.uid, f"Ya no administras {empresa.nombre}", "Un administrador de la plataforma la asumió.", _url("empresa_detalle", eid=eid), "buildings")
            messages.success(request, "Ahora administras esta empresa.")
        elif not EmpleoService.es_empleado(uid, eid):
            messages.error(request, "Solo puedes transferirla a un miembro de la empresa.")
        elif InvitacionService.proponer_administrador(uid, eid):
            messages.success(request, "Invitación enviada. La administración cambia cuando la persona la acepte.")
        else:
            messages.error(request, "Selecciona una persona válida.")
    return _a_gestion(eid)


def empresa_invitacion_cancelar(request, eid):
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede cancelar la invitación.")
    if request.method == "POST":
        invitado = InvitacionService.cancelar_de_empresa(eid)
        if invitado:
            _avisar(request, invitado, f"Se canceló la transferencia de {EmpresaService.get(eid).nombre}", url=_url("empresa_detalle", eid=eid), icono="x")
        messages.info(request, "Invitación cancelada.")
    return _a_gestion(eid)


def empresa_invitacion_responder(request, eid):
    # Siempre responde quien tiene la sesión: nadie puede aceptar por otra persona
    if request.method == "POST":
        aceptar = _respuesta(request)
        anterior = PropiedadService.administrador_de(eid)
        if aceptar is None or not InvitacionService.responder_empresa(request.permisos.uid, eid, aceptar):
            messages.error(request, "Esta invitación ya no está disponible.")
        else:
            if anterior:
                verbo, icono = _respondio(aceptar)
                _avisar(request, anterior.uid, f"{request.usuario.nombre_completo} {verbo} administrar {EmpresaService.get(eid).nombre}", url=_url("empresa_detalle", eid=eid), icono=icono)
            messages.success(request, "Ahora administras esta empresa." if aceptar else "Invitación rechazada.")
    return _volver(request, "core:conexiones_red")


def empresa_empleo_responder(request, eid, uid):
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede confirmar sus empleos.")
    if request.method == "POST":
        aceptar = _respuesta(request)
        if aceptar is None or not EmpleoService.responder(uid, eid, aceptar):
            messages.error(request, "Esta solicitud ya no está disponible.")
        else:
            verbo, icono = ("confirmó", "check-circle") if aceptar else ("rechazó", "x")
            _avisar(request, uid, f"{EmpresaService.get(eid).nombre} {verbo} tu empleo", url=_url("usuario_detalle", uid=uid), icono=icono)
            messages.success(request, "Empleo confirmado." if aceptar else "Solicitud rechazada.")
    return _volver(request, "core:conexiones_red")


def empresa_trabajo_aqui(request, eid):
    """Siempre pide quien tiene la sesión; la empresa lo confirma."""
    empresa = EmpresaService.get(eid)
    if not empresa:
        messages.error(request, "Empresa no encontrada.")
        return redirect("core:empresas_lista")
    if request.method == "POST":
        uid = request.permisos.uid
        cargo = _texto(request, "cargo", 121)
        administrador = PropiedadService.administrador_de(eid)
        if EmpleoService.es_empleado(uid, eid):
            messages.info(request, "Ya haces parte de este equipo.")
        elif EmpleoService.invitacion_de(uid, eid):
            EmpleoService.responder_invitacion(uid, eid, aceptar=True)
            if administrador:
                _avisar(request, administrador.uid, f"{request.usuario.nombre_completo} se unió a {empresa.nombre}", url=_url("empresa_detalle", eid=eid), icono="check-circle")
            messages.success(request, "Ya te habían invitado: ahora haces parte del equipo.")
        elif not cargo or len(cargo) > 120:
            messages.error(request, "Indica tu cargo.")
        else:
            EmpleoService.solicitar(uid, eid, cargo=cargo, fecha_inicio=date.today(), actual=True)
            messages.success(request, "Solicitud enviada. Entras al equipo cuando la empresa lo confirme.")
    return _volver(request, "core:empresas_lista")


def empresa_equipo_invitar(request, eid):
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede invitar a su equipo.")
    if request.method == "POST":
        uid = request.POST.get("uid", "")
        cargo = _texto(request, "cargo", 121)
        empresa = EmpresaService.get(eid)
        if not cargo or len(cargo) > 120:
            messages.error(request, "Indica el cargo de la persona.")
            return _volver(request, "core:empresas_lista")
        resultado = EmpleoService.invitar(uid, eid, cargo)
        if resultado == "enviada":
            _avisar(request, uid, f"{empresa.nombre} te invita a su equipo", cargo, url=_url("empresa_detalle", eid=eid), icono="briefcase")
            messages.success(request, "Invitación enviada. La persona entra al equipo cuando acepte.")
        elif resultado == "aceptada":
            _avisar(request, uid, f"{empresa.nombre} confirmó tu empleo", url=_url("empresa_detalle", eid=eid), icono="check-circle")
            messages.success(request, "Esa persona ya lo había pedido: ahora hace parte del equipo.")
        elif resultado == "empleado":
            messages.info(request, "Esa persona ya hace parte del equipo.")
        elif resultado == "ya_enviada":
            messages.info(request, "Ya invitaste a esa persona.")
        else:
            messages.error(request, "Selecciona a una persona.")
    return _volver(request, "core:empresas_lista")


def empresa_equipo_invitacion_responder(request, eid):
    # Responde quien tiene la sesión: nadie puede aceptar por otro
    if request.method == "POST":
        aceptar = _respuesta(request)
        empresa = EmpresaService.get(eid)
        if aceptar is None or not empresa or not EmpleoService.responder_invitacion(request.permisos.uid, eid, aceptar):
            messages.error(request, "Esta invitación ya no está disponible.")
        else:
            administrador = PropiedadService.administrador_de(eid)
            if administrador:
                verbo, icono = _respondio(aceptar)
                _avisar(request, administrador.uid, f"{request.usuario.nombre_completo} {verbo} la invitación a {empresa.nombre}", url=_url("empresa_detalle", eid=eid), icono=icono)
            messages.success(request, "Ahora haces parte del equipo." if aceptar else "Invitación rechazada.")
    return _volver(request, "core:conexiones_red")


def empresa_equipo_invitacion_cancelar(request, eid, uid):
    exigir(request.permisos.gestionar_empresa(eid), "Solo quien administra esta empresa puede cancelar sus invitaciones.")
    if request.method == "POST" and EmpleoService.responder_invitacion(uid, eid, aceptar=False):
        _avisar(request, uid, f"Se canceló tu invitación al equipo de {EmpresaService.get(eid).nombre}", url=_url("empresa_detalle", eid=eid), icono="x")
        messages.info(request, "Invitación cancelada.")
    return _volver(request, "core:empresas_lista")


def empresa_equipo_terminar(request, eid, uid):
    """Salir del equipo o quitar a alguien: el empleo queda en su trayectoria como anterior."""
    exigir(request.permisos.quitar_empleo(uid, eid), "Solo la persona o quien administra la empresa puede hacerlo.")
    if request.method == "POST":
        empresa = EmpresaService.get(eid)
        if _administra_empresa(uid, eid):
            messages.error(request, "Quien administra la empresa no puede dejarla. Transfiérela primero a otra persona.")
        elif empresa and EmpleoService.terminar(uid, eid):
            administrador = PropiedadService.administrador_de(eid)
            if uid == request.permisos.uid:
                if administrador:
                    _avisar(request, administrador.uid, f"{request.usuario.nombre_completo} dejó {empresa.nombre}", url=_url("empresa_detalle", eid=eid), icono="x")
                messages.success(request, "Listo. El empleo queda en tu trayectoria como anterior.")
            else:
                _avisar(request, uid, f"{empresa.nombre} te quitó de su equipo", "El empleo queda en tu trayectoria como anterior.", url=_url("usuario_detalle", uid=uid), icono="x")
                messages.success(request, "La persona ya no hace parte del equipo.")
        else:
            messages.error(request, "Esa persona no hace parte del equipo.")
    return _volver(request, "core:empresas_lista")

# ==============================================================================
# CRUD HABILIDADES
# ==============================================================================

def habilidades_lista(request):
    query = request.GET.get("q", "").strip().lower()
    categoria = request.GET.get("categoria", "").strip().lower()
    pag = _paginacion(request, 12)
    habilidades, total = HabilidadService.pagina(query, categoria, pag["skip"], pag["limit"])
    resumen = HabilidadService.resumen_catalogo([h.hid for h in habilidades])
    for habilidad in habilidades:
        habilidad.uso = resumen.get(habilidad.hid, {"personas": 0, "empleos": 0})
    conteo = HabilidadService.conteo_por_categoria()
    contexto = {
        "habilidades": habilidades,
        "form": HabilidadForm(),
        "query": query,
        "categoria": categoria,
        "categorias": [("", "Todas", sum(conteo.values())), ("tecnica", "Técnicas", conteo.get("tecnica", 0)), ("blanda", "Blandas", conteo.get("blanda", 0)), ("idioma", "Idiomas", conteo.get("idioma", 0))],
    }
    return _responder_lista(request, "habilidades/lista.html", "habilidades/_items.html", "lista-habilidades", contexto, pag, total)


def habilidad_crear(request):
    exigir(request.permisos.crear_habilidad(), "Solo un administrador puede agregar habilidades al catálogo.")
    if request.method == "POST":
        form = HabilidadForm(request.POST)
        if form.is_valid():
            try:
                h = HabilidadService.create(**form.cleaned_data)
            except UniqueProperty:
                messages.error(request, "Ya existe una habilidad con ese nombre.")
            else:
                messages.success(request, f"Habilidad '{h.nombre}' registrada.")
        else:
            messages.error(request, "Error al registrar la habilidad.")
    return redirect("core:habilidades_lista")


def habilidad_eliminar(request, hid):
    exigir(request.permisos.eliminar_habilidad(), "Solo un administrador puede eliminar habilidades del catálogo.")
    if request.method == "POST":
        h = HabilidadService.get(hid)
        nombre = h.nombre if h else "Habilidad"
        HabilidadService.delete(hid)
        messages.success(request, f"Habilidad '{nombre}' eliminada.")
    return redirect("core:habilidades_lista")


# ==============================================================================
# CRUD PROYECTOS
# ==============================================================================

def proyectos_lista(request):
    query = request.GET.get("q", "").strip().lower()
    estado = request.GET.get("estado", "").strip().lower()
    pag = _paginacion(request, 6)
    proyectos, total = ProyectoService.pagina(query, estado, pag["skip"], pag["limit"], uid=request.permisos.uid)
    miembros, avances = ProyectoService.resumen_carpetas(ids=[p.pid for p in proyectos])
    relaciones = ProyectoService.relacion_de(request.permisos.uid, [p.pid for p in proyectos])
    for proyecto in proyectos:
        proyecto.relacion = relaciones.get(proyecto.pid)
        iniciales = miembros.get(proyecto.pid, [])
        proyecto.iniciales = iniciales[:4]
        proyecto.mas_miembros = max(len(iniciales) - 4, 0)
        proyecto.total_miembros = len(iniciales)
        proyecto.total_avances, proyecto.ultimo_avance = avances.get(proyecto.pid, (0, ""))
    contexto = {
        "proyectos": proyectos,
        "query": query,
        "estado": estado,
        "estados_filtro": [("", "Todos"), ("activo", "En desarrollo"), ("pausado", "Pausados"), ("completado", "Completados")],
    }
    return _responder_lista(request, "proyectos/lista.html", "proyectos/_items.html", "lista-proyectos", contexto, pag, total)


def proyecto_crear(request):
    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            p = PropiedadService.crear_proyecto(request.permisos.uid, **form.cleaned_data)
            _cerrar_pendientes_si_termino(request, p.pid)
            messages.success(request, f"Proyecto '{p.nombre}' creado exitosamente.")
            return redirect("core:proyecto_detalle", pid=p.pid)
    else:
        form = ProyectoForm()
    return render(request, "proyectos/formulario.html", {"form": form, "accion": "Crear"})


def proyecto_detalle(request, pid):
    proyecto = ProyectoService.get(pid)
    if not proyecto:
        messages.error(request, "Proyecto no encontrado.")
        return redirect("core:proyectos_lista")

    miembros = ParticipacionProyectoService.listar_por_proyecto(pid)
    for miembro in miembros:
        # El líder no se ofrece como quitable: primero debe transferir el proyecto
        miembro["puede_quitar"] = request.permisos.quitar_colaborador(miembro["usuario"].uid, pid) and not _es_lider(miembro["usuario"].uid, pid)
    lider = PropiedadService.lider_de(pid)
    puede_gestionar = request.permisos.gestionar_proyecto(pid)
    pendientes = InvitacionService.pendientes_de_proyecto(pid) if puede_gestionar else []
    estado_union = InvitacionService.estado_union(request.permisos.uid, pid)
    context = {
        "avances_rel": AvanceService.de_proyecto(pid),
        "estados_proyecto": ESTADOS_PROYECTO.items(),
        "estado_union": estado_union,
        "puede_solicitar_union": estado_union is None and proyecto.estado != "completado",
        "solicitudes_union": InvitacionService.solicitudes_union_de_proyecto(pid) if puede_gestionar else [],
        "proyecto": proyecto,
        "lider": lider,
        "puede_gestionar": request.permisos.gestionar_proyecto(pid),
        "invitaciones_pendientes": [i for i in pendientes if i["tipo"] == "colaborar"],
        "transferencia_pendiente": next((i["usuario"] for i in pendientes if i["tipo"] == "liderar"), None),
        "candidatos_transferencia": _candidatos_transferencia(
            [m["usuario"] for m in miembros], lider.uid if lider else None, request.permisos,
        ) if puede_gestionar else [],
        "miembros_rel": miembros,
        "todos_usuarios": UsuarioService.all(),
    }
    return render(request, "proyectos/detalle.html", context)


def _cerrar_pendientes_si_termino(request, pid):
    """Un proyecto terminado no recibe a nadie más: quien esperaba respuesta se entera."""
    proyecto = ProyectoService.get(pid)
    if proyecto and proyecto.estado == "completado":
        # Terminarlo desde el formulario también deja el avance que cuenta cómo y cuándo terminó
        if not any(a["avance"].estado == "completado" for a in AvanceService.de_proyecto(pid)):
            AvanceService.crear(request.permisos.uid, pid, "Proyecto completado.", "completado")
        for uid in InvitacionService.cerrar_pendientes_de_proyecto(pid):
            _avisar(request, uid, f"{proyecto.nombre} terminó", "Tu solicitud o invitación ya no está vigente.", url=_url("proyecto_detalle", pid=pid), icono="x")


def proyecto_editar(request, pid):
    proyecto = ProyectoService.get(pid)
    if not proyecto:
        messages.error(request, "Proyecto no encontrado.")
        return redirect("core:proyectos_lista")
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera este proyecto puede editarlo.")

    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            ProyectoService.update(pid, **form.cleaned_data)
            _cerrar_pendientes_si_termino(request, pid)
            messages.success(request, f"Proyecto '{proyecto.nombre}' actualizado.")
            return redirect("core:proyecto_detalle", pid=pid)
    else:
        form = ProyectoForm(initial={
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "fecha_inicio": proyecto.fecha_inicio,
            "fecha_fin": proyecto.fecha_fin,
            "estado": proyecto.estado,
            "tecnologias": ", ".join(proyecto.tecnologias or []),
        })
    return render(request, "proyectos/formulario.html", {
        "form": form,
        "proyecto": proyecto,
        "accion": "Editar",
        "estados_proyecto": ESTADOS_PROYECTO.items(),
    })


def proyecto_eliminar(request, pid):
    proyecto = ProyectoService.get(pid)
    if not proyecto:
        messages.error(request, "Proyecto no encontrado.")
        return redirect("core:proyectos_lista")
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera este proyecto puede eliminarlo.")

    if request.method == "POST":
        nombre = proyecto.nombre
        miembros = [m["usuario"].uid for m in ParticipacionProyectoService.listar_por_proyecto(pid)]
        ProyectoService.delete(pid)
        for uid in miembros:
            _avisar(request, uid, f"El proyecto {nombre} fue eliminado", icono="x")
        messages.success(request, f"Proyecto '{nombre}' eliminado.")
        return redirect("core:proyectos_lista")

    return render(request, "proyectos/confirmar_eliminar.html", {"objeto": proyecto, "tipo": "Proyecto"})


def proyecto_transferir(request, pid):
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera este proyecto puede transferirlo.")
    if request.method == "POST":
        uid = request.POST.get("uid")
        actual = PropiedadService.lider_de(pid)
        if actual and actual.uid == uid:
            messages.error(request, "Esa persona ya lidera el proyecto.")
        elif uid == request.permisos.uid:  # un administrador de plataforma lo asume él mismo
            PropiedadService.asignar_lider(uid, pid)
            if actual:
                _avisar(request, actual.uid, f"Ya no lideras {ProyectoService.get(pid).nombre}", "Un administrador de la plataforma lo asumió.", _url("proyecto_detalle", pid=pid), "rocket-launch")
            messages.success(request, "Ahora lideras este proyecto.")
        elif not ParticipacionProyectoService.es_miembro(uid, pid):
            messages.error(request, "Solo puedes transferirlo a un miembro del proyecto.")
        elif InvitacionService.proponer_lider(uid, pid):
            messages.success(request, "Invitación enviada. El liderazgo cambia cuando la persona la acepte.")
        else:
            messages.error(request, "Selecciona una persona válida.")
    return redirect("core:proyecto_detalle", pid=pid)


def proyecto_avance_agregar(request, pid):
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera el proyecto puede registrar avances.")
    if request.method == "POST":
        form = AvanceForm(request.POST)
        if form.is_valid() and AvanceService.crear(request.permisos.uid, pid, form.cleaned_data["texto"], form.cleaned_data["estado"]):
            nombre = ProyectoService.get(pid).nombre
            for miembro in ParticipacionProyectoService.listar_por_proyecto(pid):
                _avisar(request, miembro["usuario"].uid, f"Nuevo avance en {nombre}", form.cleaned_data["texto"][:120], _url("proyecto_detalle", pid=pid), "rocket-launch")
            _cerrar_pendientes_si_termino(request, pid)
            messages.success(request, "Avance registrado.")
        else:
            messages.error(request, _primer_error(form) if form.errors else "No se pudo registrar el avance.")
    return redirect("core:proyecto_detalle", pid=pid)


def proyecto_avance_eliminar(request, pid, aid):
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera el proyecto puede eliminar avances.")
    if request.method == "POST":
        if AvanceService.proyecto_de(aid) == pid:
            if AvanceService.delete(aid) == "cierre":
                messages.error(request, "Este avance es el que cerró el proyecto. Para quitarlo, primero cambia el estado del proyecto.")
            else:
                messages.success(request, "Avance eliminado.")
        else:
            messages.error(request, "Este avance no existe en el proyecto.")
    return redirect("core:proyecto_detalle", pid=pid)


def proyecto_unirse(request, pid):
    # Siempre se une quien tiene la sesión
    if request.method == "POST":
        resultado = InvitacionService.solicitar_unirse(request.permisos.uid, pid)
        if resultado == "enviada":
            messages.success(request, "Solicitud enviada. Te sumas cuando quien lidera el proyecto la acepte.")
        elif resultado == "aceptada":
            lider = PropiedadService.lider_de(pid)
            if lider:
                _avisar(request, lider.uid, f"{request.usuario.nombre_completo} se unió a {ProyectoService.get(pid).nombre}", url=_url("proyecto_detalle", pid=pid), icono="check-circle")
            messages.success(request, "Ya te habían invitado: ahora participas en el proyecto.")
        elif resultado == "ya_enviada":
            messages.info(request, "Ya pediste unirte a este proyecto.")
        elif resultado == "miembro":
            messages.info(request, "Ya participas en este proyecto.")
        elif resultado == "cerrado":
            messages.error(request, "Este proyecto ya terminó y no recibe solicitudes.")
        else:
            messages.error(request, "No se pudo enviar la solicitud.")
    return _volver(request, "core:proyectos_lista")


def proyecto_unirse_cancelar(request, pid):
    if request.method == "POST":
        InvitacionService.responder_union(request.permisos.uid, pid, aceptar=False)
        messages.info(request, "Solicitud cancelada.")
    return _volver(request, "core:proyectos_lista")


def proyecto_union_responder(request, pid, uid):
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera el proyecto puede responder estas solicitudes.")
    if request.method == "POST":
        aceptar = _respuesta(request)
        if aceptar is None or not InvitacionService.responder_union(uid, pid, aceptar):
            messages.error(request, "Esta solicitud ya no está disponible.")
        else:
            verbo, icono = _respondio(aceptar)
            _avisar(request, uid, f"Se {verbo} tu solicitud para unirte a {ProyectoService.get(pid).nombre}", url=_url("proyecto_detalle", pid=pid), icono=icono)
            messages.success(request, "La persona ya participa en el proyecto." if aceptar else "Solicitud rechazada.")
    return _volver(request, "core:proyectos_lista")


def proyecto_invitacion_cancelar(request, pid, uid):
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera el proyecto puede cancelar sus invitaciones.")
    if request.method == "POST":
        if InvitacionService.responder_proyecto(uid, pid, aceptar=False):
            _avisar(request, uid, f"Se canceló tu invitación a {ProyectoService.get(pid).nombre}", url=_url("proyecto_detalle", pid=pid), icono="x")
        messages.info(request, "Invitación cancelada.")
    return redirect("core:proyecto_detalle", pid=pid)


def proyecto_invitacion_responder(request, pid):
    # Siempre responde quien tiene la sesión: nadie puede aceptar por otra persona
    if request.method == "POST":
        aceptar = _respuesta(request)
        tipo = InvitacionService.tipo_invitacion_proyecto(request.permisos.uid, pid)
        lider = PropiedadService.lider_de(pid)
        if aceptar is None or not InvitacionService.responder_proyecto(request.permisos.uid, pid, aceptar):
            messages.error(request, "Esta invitación ya no está disponible.")
        else:
            if lider:
                verbo, icono = _respondio(aceptar)
                accion = "liderar" if tipo == "liderar" else "colaborar en"
                _avisar(request, lider.uid, f"{request.usuario.nombre_completo} {verbo} {accion} {ProyectoService.get(pid).nombre}", url=_url("proyecto_detalle", pid=pid), icono=icono)
            messages.success(request, "Invitación aceptada." if aceptar else "Invitación rechazada.")
    return _volver(request, "core:conexiones_red")


# ==============================================================================
# CRUD OFERTAS
# ==============================================================================

def ofertas_lista(request):
    query = request.GET.get("q", "").strip().lower()
    modalidad = request.GET.get("modalidad", "").strip().lower()
    pag = _paginacion(request, 6)
    ofertas, total = OfertaService.pagina(query, modalidad, pag["skip"], pag["limit"])
    _preparar_boletos(ofertas, request.permisos.uid)
    contexto = {"ofertas": ofertas, "query": query, "modalidad_filtro": modalidad}
    return _responder_lista(request, "ofertas/lista.html", "ofertas/_items.html", "lista-empleos", contexto, pag, total)


def oferta_crear(request):
    permisos = request.permisos
    empresas = [e for e in EmpresaService.all() if permisos.gestionar_empresa(e.eid)]
    if not empresas:
        messages.info(request, "Para publicar un empleo, primero registra una empresa.")
        return redirect("core:empresa_crear")

    if request.method == "POST":
        form = OfertaForm(request.POST, empresas=empresas)
        if form.is_valid():
            datos = form.cleaned_data
            eid = datos.pop("eid")
            exigir(permisos.gestionar_empresa(eid), "Solo puedes publicar empleos de empresas que administras.")
            o = PropiedadService.crear_oferta(eid, **datos)
            messages.success(request, f"Empleo '{o.titulo}' publicado.")
            return redirect("core:oferta_detalle", oid=o.oid)
    else:
        form = OfertaForm(empresas=empresas, initial={"eid": request.GET.get("empresa")})
    return render(request, "ofertas/formulario.html", {"form": form, "accion": "Crear"})


def oferta_detalle(request, oid):
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Empleo no encontrado.")
        return redirect("core:ofertas_lista")

    permisos = request.permisos
    _preparar_boletos([oferta], permisos.uid)
    puede_gestionar = permisos.gestionar_oferta(oid)
    ya_postulado = PostulacionService.ha_postulado(permisos.uid, oid)
    candidatos = PostulacionService.listar_por_oferta(oid)
    # Las postulaciones son privadas: la empresa ve todas; cada persona, solo la suya
    if not puede_gestionar:
        candidatos = [c for c in candidatos if c["usuario"].uid == permisos.uid]
    total_postulaciones, cupos_ocupados = PostulacionService.contar(oid)
    for candidato in candidatos:
        candidato["puede_retirar"] = permisos.retirar_postulacion(candidato["usuario"].uid) and not candidato["decidida"]

    context = {
        "oferta": oferta,
        "empresa_rel": PublicacionOfertaService.obtener_empresa(oid),
        "requisitos_rel": RequisitoOfertaService.listar_por_oferta(oid),
        "candidatos_rel": candidatos,
        "puede_gestionar": puede_gestionar,
        "estados_en_proceso": [(e, ESTADOS_POSTULACION[e]) for e in ESTADOS_EN_PROCESO],
        "total_postulaciones": total_postulaciones,
        "cupos_ocupados": cupos_ocupados,
        "cupos_libres": max((oferta.cupos or 1) - cupos_ocupados, 0),
        "ya_postulado": ya_postulado,
        "puede_postular": permisos.postularse(oid) and not ya_postulado and oferta.estado == "abierta",
        "todas_habilidades": HabilidadService.all(),
        "todas_empresas": EmpresaService.all(),
    }
    return render(request, "ofertas/detalle.html", context)


def oferta_editar(request, oid):
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Empleo no encontrado.")
        return redirect("core:ofertas_lista")
    exigir(request.permisos.gestionar_oferta(oid), "Solo la empresa que publica este empleo puede editarlo.")

    if request.method == "POST":
        form = OfertaForm(request.POST)
        if form.is_valid():
            _, aceptadas = PostulacionService.contar(oid)
            if form.cleaned_data["cupos"] < aceptadas:
                form.add_error("cupos", f"Ya contrataste a {aceptadas}: los cupos no pueden ser menos.")
            elif form.cleaned_data["estado"] == "abierta" and aceptadas >= form.cleaned_data["cupos"]:
                form.add_error("cupos", "Los cupos ya están ocupados. Auméntalos para volver a abrir el empleo.")
        if form.is_valid():
            if oferta.estado == "abierta" and form.cleaned_data["estado"] == "cerrada":
                for candidato_uid in PostulacionService.cerrar_oferta(oid):
                    _avisar(request, candidato_uid, f"El empleo {oferta.titulo} se cerró", "Tu postulación quedó como no seleccionada.", url=_url("oferta_detalle", oid=oid), icono="briefcase")
            OfertaService.update(oid, **form.cleaned_data)
            if oferta.estado == "cerrada" and form.cleaned_data["estado"] == "abierta":
                for candidato_uid in PostulacionService.reabrir_oferta(oid):
                    _avisar(request, candidato_uid, f"El empleo {oferta.titulo} volvió a abrirse", "Tu postulación sigue en curso.", url=_url("oferta_detalle", oid=oid), icono="briefcase")
            messages.success(request, f"Empleo '{oferta.titulo}' actualizado.")
            return redirect("core:oferta_detalle", oid=oid)
    else:
        form = OfertaForm(initial={
            "titulo": oferta.titulo,
            "descripcion": oferta.descripcion,
            "salario_min": oferta.salario_min,
            "salario_max": oferta.salario_max,
            "modalidad": oferta.modalidad,
            "ubicacion": oferta.ubicacion,
            "cupos": oferta.cupos or 1,
            "estado": oferta.estado,
        })
    return render(request, "ofertas/formulario.html", {"form": form, "oferta": oferta, "accion": "Editar"})


def oferta_eliminar(request, oid):
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Empleo no encontrado.")
        return redirect("core:ofertas_lista")
    exigir(request.permisos.gestionar_oferta(oid), "Solo la empresa que publica este empleo puede eliminarlo.")

    if request.method == "POST":
        titulo = oferta.titulo
        candidatos = [c["usuario"].uid for c in PostulacionService.listar_por_oferta(oid)]
        OfertaService.delete(oid)
        for uid in candidatos:
            _avisar(request, uid, f"El empleo {titulo} fue eliminado", "Tu postulación ya no está vigente.", icono="x")
        messages.success(request, f"Empleo '{titulo}' eliminado.")
        return redirect("core:ofertas_lista")

    return render(request, "ofertas/confirmar_eliminar.html", {
        "objeto": oferta,
        "tipo": "Oferta",
        "total_postulaciones": len(PostulacionService.listar_por_oferta(oid)),
    })


# ==============================================================================
# VISTAS DE GESTION DE RELACIONES (FASE 5)
# ==============================================================================

def conexiones_red(request):
    usuario_activo = UsuarioService.get(request.GET.get("uid")) or request.usuario
    query = request.GET.get("q", "").strip().lower()
    pag = _paginacion(request, 6)

    conexiones = ConexionService.listar(usuario_activo.uid)
    total_conexiones = len(conexiones)
    es_mi_red = usuario_activo.uid == request.permisos.uid
    solicitudes_recibidas = InvitacionService.solicitudes_recibidas(usuario_activo.uid) if es_mi_red else []
    solicitudes_enviadas = InvitacionService.solicitudes_enviadas(usuario_activo.uid) if es_mi_red else []
    # Las sugerencias son privadas: solo se ven en la red propia, y nunca alguien con quien
    # ya hay una solicitud en curso.
    sugerencias = []
    if es_mi_red:
        en_curso = {s["usuario"].uid for s in solicitudes_recibidas + solicitudes_enviadas}
        recomendadas = RecommendationEngine.recomendar_contactos(usuario_activo.uid, limit=4 + len(en_curso))
        sugerencias = [r for r in recomendadas if r["usuario"].uid not in en_curso][:4]
    if query:
        conexiones = [
            c for c in conexiones
            if query in c["usuario"].nombre_completo.lower()
            or query in (c["usuario"].titulo_profesional or "").lower()
            or query in (c["usuario"].ubicacion or "").lower()
        ]
    total_filtrados = len(conexiones)
    conexiones = _recortar(conexiones, pag)

    context = {
        "usuario_activo": usuario_activo,
        "conexiones": conexiones,
        "total_conexiones": total_conexiones,
        "query": query,
        "sugerencias": sugerencias,
        "es_mi_red": es_mi_red,
        "solicitudes_recibidas": solicitudes_recibidas,
        "solicitudes_enviadas": solicitudes_enviadas,
        "invitaciones": InvitacionService.invitaciones_de(usuario_activo.uid) if es_mi_red else [],
        "uniones_recibidas": InvitacionService.solicitudes_union_para_lider(usuario_activo.uid) if es_mi_red else [],
        "uniones_enviadas": InvitacionService.solicitudes_union_enviadas(usuario_activo.uid) if es_mi_red else [],
        "empleos_recibidos": EmpleoService.solicitudes_para_administrador(usuario_activo.uid) if es_mi_red else [],
        "invitaciones_equipo": EmpleoService.invitaciones_de_usuario(usuario_activo.uid) if es_mi_red else [],
        "puede_desconectar": request.permisos.editar_usuario(usuario_activo.uid),
    }
    return _responder_lista(request, "conexiones/red.html", "conexiones/_contactos.html", "lista-contactos", context, pag, total_filtrados)


def conexion_conectar(request):
    # La solicitud siempre sale de quien tiene la sesión, nunca de un dato del formulario
    if request.method == "POST":
        resultado = InvitacionService.solicitar_conexion(
            request.permisos.uid, request.POST.get("uid_destino"), mensaje=_texto(request, "mensaje", 250),
        )
        if resultado == "enviada":
            messages.success(request, "Solicitud enviada. La conexión se crea cuando la otra persona la acepte.")
        elif resultado == "aceptada":
            _avisar(request, request.POST.get("uid_destino"), f"{request.usuario.nombre_completo} aceptó tu solicitud de conexión", url=_url("usuario_detalle", uid=request.permisos.uid), icono="check-circle")
            messages.success(request, "Esa persona ya te lo había pedido: ahora están conectados.")
        elif resultado == "ya_enviada":
            messages.info(request, "Ya le enviaste una solicitud a esta persona.")
        elif resultado == "conectados":
            messages.info(request, "Ya están conectados.")
        else:
            messages.error(request, "No se pudo enviar la solicitud.")
    return _volver(request, "core:conexiones_red")


def conexion_solicitud_responder(request, uid_origen):
    # Siempre responde quien tiene la sesión: nadie puede aceptar por otra persona
    if request.method == "POST":
        aceptar = _respuesta(request)
        if aceptar is None or not InvitacionService.responder_conexion(uid_origen, request.permisos.uid, aceptar):
            messages.error(request, "Esta solicitud ya no está disponible.")
        else:
            verbo, icono = _respondio(aceptar)
            _avisar(request, uid_origen, f"{request.usuario.nombre_completo} {verbo} tu solicitud de conexión", url=_url("usuario_detalle", uid=request.permisos.uid), icono=icono)
            messages.success(request, "Ahora están conectados." if aceptar else "Solicitud rechazada.")
    return _volver(request, "core:conexiones_red")


def conexion_solicitud_cancelar(request, uid_destino):
    if request.method == "POST":
        InvitacionService.responder_conexion(request.permisos.uid, uid_destino, aceptar=False)
        messages.info(request, "Solicitud cancelada.")
    return _volver(request, "core:conexiones_red")


def conexion_desconectar(request, uid_origen, uid_destino):
    exigir(request.permisos.desconectar(uid_origen, uid_destino), "Solo puedes eliminar tus propias conexiones.")
    if request.method == "POST":
        if ConexionService.desconectar(uid_origen, uid_destino):
            for uid, otro in ((uid_origen, uid_destino), (uid_destino, uid_origen)):
                persona = UsuarioService.get(otro)
                if persona:
                    _avisar(request, uid, f"Tu conexión con {persona.nombre_completo} terminó", url=_url("usuario_detalle", uid=otro), icono="x")
        messages.success(request, "Conexión eliminada.")
    return _volver(request, "core:conexiones_red")


def usuario_habilidad_agregar(request, uid):
    exigir(request.permisos.editar_usuario(uid), "Solo puedes modificar tu propio perfil.")
    if request.method == "POST":
        form = VincularHabilidadUsuarioForm({"nivel": "intermedio", "anios_experiencia": 1, **request.POST.dict()})
        if not request.POST.get("hid"):
            messages.error(request, "Debe seleccionar una habilidad válida.")
        elif not form.is_valid():
            messages.error(request, _primer_error(form))
        elif HabilidadUsuarioService.vincular(uid, form.cleaned_data["hid"], nivel=form.cleaned_data["nivel"], anios_experiencia=form.cleaned_data["anios_experiencia"]):
            _avisar(request, uid, "Un administrador cambió tus habilidades", url=_url("usuario_detalle", uid=uid))
            messages.success(request, "Habilidad vinculada al perfil.")
        else:
            messages.error(request, "Debe seleccionar una habilidad válida.")
    return redirect("core:usuario_detalle", uid=uid)


def usuario_habilidad_eliminar(request, uid, hid):
    exigir(request.permisos.editar_usuario(uid), "Solo puedes modificar tu propio perfil.")
    if request.method == "POST":
        HabilidadUsuarioService.desvincular(uid, hid)
        _avisar(request, uid, "Un administrador cambió tus habilidades", url=_url("usuario_detalle", uid=uid))
        messages.success(request, "Habilidad desvinculada del perfil.")
    return redirect("core:usuario_detalle", uid=uid)


def usuario_experiencia_agregar(request, uid):
    exigir(request.permisos.editar_usuario(uid), "Solo puedes modificar tu propio perfil.")
    if request.method == "POST":
        form = ExperienciaLaboralForm(request.POST)
        if not request.POST.get("eid") or not request.POST.get("cargo", "").strip():
            messages.error(request, "Debe indicar empresa y cargo obligatoriamente.")
        elif not form.is_valid():
            messages.error(request, _primer_error(form))
        else:
            datos = form.cleaned_data
            eid = datos["eid"]
            campos = {"cargo": datos["cargo"], "fecha_inicio": datos["fecha_inicio"], "fecha_fin": datos["fecha_fin"], "actual": datos["actual"]}
            if request.permisos.gestionar_empresa(eid):
                # Quien gestiona la empresa puede confirmar el empleo: no hace falta pedírselo a sí mismo
                if EmpleoService.vincular(uid, eid, **campos):
                    _avisar(request, uid, f"{EmpresaService.get(eid).nombre} agregó un empleo a tu perfil", datos["cargo"], _url("usuario_detalle", uid=uid), "briefcase")
                    messages.success(request, "Experiencia laboral anadida al perfil.")
                else:
                    messages.error(request, "La empresa seleccionada no existe.")
            elif EmpleoService.solicitar(uid, eid, **campos):
                messages.success(request, "Solicitud enviada. El empleo aparecerá en el perfil cuando la empresa lo confirme.")
            else:
                messages.error(request, "La empresa seleccionada no existe.")
    return redirect("core:usuario_detalle", uid=uid)


def usuario_experiencia_cancelar(request, uid, eid):
    exigir(request.permisos.editar_usuario(uid), "Solo puedes modificar tu propio perfil.")
    if request.method == "POST":
        EmpleoService.responder(uid, eid, aceptar=False)
        messages.info(request, "Solicitud cancelada.")
    return _volver(request, "core:usuarios_lista")


def usuario_experiencia_eliminar(request, uid, eid):
    exigir(request.permisos.quitar_empleo(uid, eid), "Solo la persona o quien administra la empresa puede quitar este empleo.")
    if request.method == "POST":
        if _administra_empresa(uid, eid):
            messages.error(request, "Quien administra la empresa no puede dejarla. Transfiérela primero a otra persona.")
            return redirect("core:usuario_detalle", uid=uid)
        era_empleado = EmpleoService.es_empleado(uid, eid)
        tenia_registro = era_empleado or any(e["empresa"].eid == eid for e in EmpleoService.listar_por_usuario(uid))
        resultado = EmpleoService.desvincular(uid, eid)
        if tenia_registro and (resultado != "anterior" or era_empleado):
            empresa = EmpresaService.get(eid)
            administrador = PropiedadService.administrador_de(eid)
            _avisar(request, uid, f"{empresa.nombre} " + ("te quitó de su equipo" if resultado == "anterior" else "quitó tu empleo de tu perfil"), url=_url("usuario_detalle", uid=uid), icono="x")
            if administrador and uid == request.permisos.uid:
                _avisar(request, administrador.uid, f"{request.usuario.nombre_completo} dejó {empresa.nombre}", url=_url("empresa_detalle", eid=eid), icono="briefcase")
        if resultado == "anterior":
            messages.info(request, "Este empleo viene de una contratación en WheelsOn, así que queda en la trayectoria como empleo anterior.")
        else:
            messages.success(request, "Experiencia laboral eliminada del perfil.")
    return redirect("core:usuario_detalle", uid=uid)


def proyecto_colaborador_agregar(request, pid):
    exigir(request.permisos.gestionar_proyecto(pid), "Solo quien lidera el proyecto puede sumar colaboradores.")
    if request.method == "POST":
        uid = request.POST.get("uid")
        rol = _texto(request, "rol", 100) or "Colaborador"
        fecha_inicio = request.POST.get("fecha_inicio") or None
        if uid:
            try:
                es_miembro = ParticipacionProyectoService.es_miembro(uid, pid)
                if not es_miembro and uid != request.permisos.uid and ProyectoService.get(pid).estado == "completado":
                    messages.error(request, "Este proyecto ya terminó y no recibe a nadie más.")
                    return redirect("core:proyecto_detalle", pid=pid)
                if uid == request.permisos.uid or es_miembro:
                    # Tu propia participación, o cambiar el rol de quien ya aceptó, no requiere invitación
                    guardado = ParticipacionProyectoService.vincular(uid, pid, rol=rol, fecha_inicio=fecha_inicio)
                    exito = "Participación actualizada."
                    _avisar(request, uid, f"Tu rol en {ProyectoService.get(pid).nombre} ahora es {rol}", url=_url("proyecto_detalle", pid=pid), icono="rocket-launch")
                else:
                    guardado = InvitacionService.invitar_a_proyecto(uid, pid, rol=rol, fecha_inicio=fecha_inicio)
                    exito = "Ya había pedido unirse: ahora participa." if guardado == "unido" else "Invitación enviada. Se suma al proyecto cuando la acepte."
                    if guardado == "unido":
                        _avisar(request, uid, f"Se aceptó tu solicitud para unirte a {ProyectoService.get(pid).nombre}", url=_url("proyecto_detalle", pid=pid), icono="check-circle")
            except ValueError:
                messages.error(request, "La fecha no es válida. Usa el formato AAAA-MM-DD.")
            else:
                if guardado:
                    messages.success(request, exito)
                else:
                    messages.error(request, "La persona seleccionada no existe.")
        else:
            messages.error(request, "Debe seleccionar un usuario para vincularlo.")
    return redirect("core:proyecto_detalle", pid=pid)


def proyecto_colaborador_eliminar(request, pid, uid):
    exigir(request.permisos.quitar_colaborador(uid, pid), "Solo la persona o quien lidera el proyecto puede quitarla.")
    if request.method == "POST":
        if _es_lider(uid, pid):
            messages.error(request, "El líder no puede salir del proyecto. Transfiérelo primero a otra persona.")
            return redirect("core:proyecto_detalle", pid=pid)
        proyecto = ProyectoService.get(pid)
        if not proyecto:
            messages.error(request, "Proyecto no encontrado.")
            return redirect("core:proyectos_lista")
        ParticipacionProyectoService.desvincular(uid, pid)
        lider = PropiedadService.lider_de(pid)
        if uid == request.permisos.uid:
            if lider:
                _avisar(request, lider.uid, f"{request.usuario.nombre_completo} salió de {proyecto.nombre}", url=_url("proyecto_detalle", pid=pid), icono="users")
        else:
            _avisar(request, uid, f"Ya no participas en {proyecto.nombre}", url=_url("proyecto_detalle", pid=pid), icono="x")
        messages.success(request, "Colaborador desvinculado del proyecto.")
    return redirect("core:proyecto_detalle", pid=pid)


def oferta_requisito_agregar(request, oid):
    exigir(request.permisos.gestionar_oferta(oid), "Solo la empresa que publica el empleo puede cambiar sus requisitos.")
    if request.method == "POST":
        form = RequisitoOfertaForm({"nivel_minimo": "basico", "prioridad": "obligatoria", **request.POST.dict()})
        if not request.POST.get("hid"):
            messages.error(request, "Debe seleccionar una habilidad.")
        elif not form.is_valid():
            messages.error(request, _primer_error(form))
        elif RequisitoOfertaService.vincular(oid, form.cleaned_data["hid"], nivel_minimo=form.cleaned_data["nivel_minimo"], prioridad=form.cleaned_data["prioridad"]):
            messages.success(request, "Requisito agregado al empleo.")
        else:
            messages.error(request, "Debe seleccionar una habilidad.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_requisito_eliminar(request, oid, hid):
    exigir(request.permisos.gestionar_oferta(oid), "Solo la empresa que publica el empleo puede cambiar sus requisitos.")
    if request.method == "POST":
        RequisitoOfertaService.desvincular(oid, hid)
        messages.success(request, "Requisito eliminado del empleo.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_empresa_asignar(request, oid):
    # Toda oferta nace con empresa; esto solo repara ofertas sin dueño
    exigir(request.permisos.es_admin, "Solo un administrador puede asignar la empresa de un empleo.")
    if request.method == "POST":
        eid = request.POST.get("eid")
        if PublicacionOfertaService.obtener_empresa(oid):
            messages.error(request, "Este empleo ya tiene una empresa.")
        elif eid and PublicacionOfertaService.vincular(eid, oid):
            messages.success(request, "Empresa vinculada al empleo.")
        else:
            messages.error(request, "Debe seleccionar una empresa.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_postular(request, oid):
    # Cada persona se postula a sí misma: el candidato nunca viene del formulario
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Empleo no encontrado.")
        return redirect("core:ofertas_lista")
    if request.method == "POST":
        permisos = request.permisos
        if not permisos.postularse(oid):
            messages.error(request, "No puedes postularte a un empleo que administras.")
        else:
            carta = _texto(request, "carta_presentacion", 2000)
            resultado = PostulacionService.postular_si_abierta(permisos.uid, oid, carta_presentacion=carta)
            if resultado == "enviada":
                messages.success(request, "Tu postulación fue enviada.")
            elif resultado == "ya_postulado":
                messages.info(request, "Ya te postulaste a este empleo.")
            else:
                messages.error(request, "Este empleo ya está cerrado.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_postulacion_eliminar(request, oid, uid):
    exigir(request.permisos.retirar_postulacion(uid), "Solo la persona que se postuló puede retirar su postulación.")
    if request.method == "POST":
        if not PostulacionService.retirar(uid, oid):
            messages.error(request, "Esta postulación ya tiene una decisión y no se puede retirar.")
        else:
            empresa = PublicacionOfertaService.obtener_empresa(oid)
            administrador = PropiedadService.administrador_de(empresa.eid) if empresa else None
            if administrador:
                _avisar(request, administrador.uid, f"{UsuarioService.get(uid).nombre_completo} retiró su postulación", OfertaService.get(oid).titulo, _url("oferta_detalle", oid=oid), "paper-plane-tilt")
            messages.success(request, "Postulación retirada.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_postulacion_estado(request, oid, uid):
    exigir(request.permisos.gestionar_oferta(oid), "Solo la empresa que publica el empleo puede responder a las postulaciones.")
    if request.method == "POST":
        estado = request.POST.get("estado")
        oferta = OfertaService.get(oid)
        if estado == "aceptada":
            resultado = PostulacionService.contratar(uid, oid)
            if not resultado:
                messages.error(request, "Ya no se puede aceptar: la postulación ya tiene una decisión, el empleo está cerrado o no tiene empresa.")
            else:
                empresa = resultado["empresa"]
                _avisar(request, uid, f"{empresa.nombre} te contrató", f"Ya haces parte de su equipo como {oferta.titulo}.", url=_url("empresa_detalle", eid=empresa.eid), icono="check-circle")
                for otro in resultado["no_seleccionados"]:
                    _avisar(request, otro, f"El empleo {oferta.titulo} ya se cubrió", "Tu postulación quedó como no seleccionada.", url=_url("oferta_detalle", oid=oid), icono="x")
                if resultado["cubierta"]:
                    messages.success(request, "Contratación lista: la persona ya está en el equipo. Los cupos se llenaron y el empleo se cerró.")
                else:
                    messages.success(request, "Contratación lista: la persona ya está en el equipo.")
        elif estado not in (*ESTADOS_EN_PROCESO, "rechazada"):
            messages.error(request, "Selecciona un estado válido.")
        elif PostulacionService.cambiar_estado(uid, oid, estado):
            messages.success(request, f"Postulación marcada como: {ESTADOS_POSTULACION[estado]}.")
        else:
            messages.error(request, "Esta postulación ya tiene una decisión.")
    return redirect("core:oferta_detalle", oid=oid)


# ==============================================================================
# VISTAS DE CONSULTAS AVANZADAS DE GRAFOS (FASE 6)
# ==============================================================================

def consultas_index(request):
    tab = request.GET.get("tab", "camino")
    usuarios = UsuarioService.all()
    empresas = EmpresaService.all()
    ofertas = OfertaService.all()
    proyectos = ProyectoService.all()

    uid1 = request.GET.get("uid1") or request.permisos.uid
    uid2 = request.GET.get("uid2") or (usuarios[1].uid if len(usuarios) > 1 else (usuarios[0].uid if usuarios else ""))
    eid = request.GET.get("eid") or (empresas[0].eid if len(empresas) > 0 else "")
    oid = request.GET.get("oid") or (ofertas[0].oid if len(ofertas) > 0 else "")
    pid = request.GET.get("pid") or (proyectos[0].pid if len(proyectos) > 0 else "")

    # Los candidatos sugeridos son información de la empresa: solo los ve quien gestiona la oferta
    ofertas_gestionadas = [o for o in ofertas if request.permisos.gestionar_oferta(o.oid)]
    if tab == "candidatos":
        if request.GET.get("oid"):
            exigir(request.permisos.gestionar_oferta(oid), "Solo la empresa que publica el empleo puede ver sus candidatos sugeridos.")
        else:
            oid = ofertas_gestionadas[0].oid if ofertas_gestionadas else ""

    res_ruta_oferta = None
    res_proyectos = None
    res_camino = None
    res_comun = None
    res_similares = None
    res_empresa = None
    res_demandadas = GraphAnalyticsService.habilidades_mas_demandadas(limit=10)
    res_candidatos = None

    if tab == "camino" and uid1 and uid2:
        res_camino = GraphAnalyticsService.shortest_path_usuarios(uid1, uid2)
    elif tab == "comun" and uid1 and uid2:
        res_comun = GraphAnalyticsService.contactos_en_comun(uid1, uid2)
    elif tab == "similares" and uid1:
        res_similares = GraphAnalyticsService.usuarios_con_habilidades_similares(uid1, limit=10)
    elif tab == "ruta_empresa" and uid1 and eid:
        res_empresa = GraphAnalyticsService.ruta_usuario_empresa(uid1, eid)
    elif tab == "candidatos" and oid:
        res_candidatos = GraphAnalyticsService.candidatos_para_oferta(oid, limit=10)
    elif tab == "ruta_oferta" and uid1 and oid:
        res_ruta_oferta = GraphAnalyticsService.ruta_usuario_oferta(uid1, oid)
    elif tab == "proyectos" and pid:
        res_proyectos = GraphAnalyticsService.proyectos_relacionados(pid, limit=10)

    # Las postulaciones son privadas: solo se informan a la persona y a la empresa
    if res_ruta_oferta and not request.permisos.ver_postulacion(uid1, oid):
        res_ruta_oferta["ya_postulado"] = False

    context = {
        "tab": tab,
        "usuarios": usuarios,
        "empresas": empresas,
        "ofertas": ofertas,
        "ofertas_gestionadas": ofertas_gestionadas,
        "proyectos": proyectos,
        "uid1": uid1,
        "uid2": uid2,
        "eid": eid,
        "oid": oid,
        "pid": pid,
        "res_ruta_oferta": res_ruta_oferta,
        "res_proyectos": res_proyectos,
        "usuario1": UsuarioService.get(uid1) if uid1 else None,
        "usuario2": UsuarioService.get(uid2) if uid2 else None,
        "empresa_obj": EmpresaService.get(eid) if eid else None,
        "oferta_obj": OfertaService.get(oid) if oid else None,
        "res_camino": res_camino,
        "res_comun": res_comun,
        "res_similares": res_similares,
        "res_empresa": res_empresa,
        "res_demandadas": res_demandadas,
        "res_candidatos": res_candidatos,
    }
    return render(request, "grafo/consultas.html", context)


def recomendaciones_index(request):
    tab = request.GET.get("tab", "contactos")
    permisos = request.permisos

    # Las sugerencias son personales: cada quien ve las suyas, y las de un proyecto
    # o una empresa solo quien los gestiona.
    uid = permisos.uid
    proyectos = [p for p in ProyectoService.all() if permisos.gestionar_proyecto(p.pid)]
    empresas = [e for e in EmpresaService.all() if permisos.gestionar_empresa(e.eid)]
    pid = request.GET.get("pid", "")
    eid = request.GET.get("eid", "")
    if pid:
        exigir(permisos.gestionar_proyecto(pid), "Solo quien lidera el proyecto puede ver sus colaboradores sugeridos.")
    if eid:
        exigir(permisos.gestionar_empresa(eid), "Solo quien administra la empresa puede ver su talento sugerido.")
    pid = pid or (proyectos[0].pid if proyectos else "")
    eid = eid or (empresas[0].eid if empresas else "")

    usuario_sel = UsuarioService.get(uid) if uid else None
    proyecto_sel = ProyectoService.get(pid) if pid else None
    empresa_sel = EmpresaService.get(eid) if eid else None

    rec_contactos = []
    rec_empleos = []
    rec_colaboradores = []
    rec_talento = []

    if tab == "contactos" and uid:
        rec_contactos = RecommendationEngine.recomendar_contactos(uid, limit=12)
    elif tab == "empleos" and uid:
        rec_empleos = RecommendationEngine.recomendar_empleos(uid, limit=12)
    elif tab == "colaboradores" and pid:
        rec_colaboradores = RecommendationEngine.recomendar_colaboradores_proyecto(pid, limit=12)
    elif tab == "talento" and eid:
        # Quien ya tiene una invitación o una solicitud en curso no necesita otra sugerencia
        en_curso = {i["usuario"].uid for i in EmpleoService.invitaciones_de_empresa(eid)} | {s["usuario"].uid for s in EmpleoService.solicitudes_de_empresa(eid)}
        rec_talento = [r for r in RecommendationEngine.recomendar_candidatos_para_empresa(eid, limit=12 + len(en_curso)) if r["usuario"].uid not in en_curso][:12]

    _con_grado([item["usuario"] for item in rec_contactos + rec_colaboradores + rec_talento])
    _preparar_boletos([item["oferta"] for item in rec_empleos], uid)
    for item in rec_colaboradores:
        partes = []
        if item["habilidades_match"]:
            partes.append("Domina " + ", ".join(item["habilidades_match"]))
        if item["nombres_conexiones"]:
            partes.append("Conoce a " + ", ".join(item["nombres_conexiones"][:3]))
        item["nota"] = ". ".join(partes) + "."
    for item in rec_talento:
        partes = []
        if item["habilidades_match"]:
            partes.append("Domina " + ", ".join(item["habilidades_match"]))
        if item["conexiones_internas"]:
            partes.append(f"{item['conexiones_internas']} contacto{'s' if item['conexiones_internas'] != 1 else ''} en la empresa")
        item["nota"] = ". ".join(partes) + "."

    context = {
        "tab": tab,
        "proyectos": proyectos,
        "empresas": empresas,
        "uid": uid,
        "pid": pid,
        "eid": eid,
        "usuario_sel": usuario_sel,
        "proyecto_sel": proyecto_sel,
        "empresa_sel": empresa_sel,
        "rec_contactos": rec_contactos,
        "rec_empleos": rec_empleos,
        "rec_colaboradores": rec_colaboradores,
        "rec_talento": rec_talento,
        "total_sugerencias": len(rec_contactos) + len(rec_empleos) + len(rec_colaboradores) + len(rec_talento),
    }
    return render(request, "recomendaciones/index.html", context)


def analitica_dashboard(request):
    metricas = NetworkAnalyticsService.metricas_red_globales()
    centralidad = NetworkAnalyticsService.ranking_centralidad_grado(limit=10)
    pagerank = NetworkAnalyticsService.ranking_pagerank(limit=10)
    intermediacion = NetworkAnalyticsService.ranking_intermediacion(limit=10)
    comunidades = NetworkAnalyticsService.deteccion_comunidades()
    habilidades_balance = NetworkAnalyticsService.analisis_oferta_demanda_habilidades()
    chart_data = NetworkAnalyticsService.preparar_datos_graficos(comunidades, habilidades_balance)

    context = {
        "metricas": metricas,
        "centralidad": centralidad,
        "pagerank": pagerank,
        "intermediacion": intermediacion,
        "comunidades": comunidades,
        "habilidades_balance": habilidades_balance,
        "chart_data": chart_data,
    }
    return render(request, "analitica/dashboard.html", context)


def _iniciar_sesion(request, usuario):
    request.session.cycle_key()  # identificador de sesión nuevo al entrar
    request.session["active_user_uid"] = usuario.uid


def login_view(request):
    # Acceso rápido: atajo para probar la demo, desactivado fuera de ella
    quick_uid = request.GET.get("quick_login")
    if quick_uid and settings.WHEELSON_MODO_DEMO:
        user = UsuarioService.get(quick_uid)
        if user:
            _iniciar_sesion(request, user)
            messages.success(request, f"Sesión iniciada como {user.nombre_completo}.")
            return redirect("core:dashboard")

    if request.usuario and not request.GET.get("force"):
        return redirect("core:dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = UsuarioService.autenticar(form.cleaned_data["email"], form.cleaned_data["password"])
            if user:
                _iniciar_sesion(request, user)
                messages.success(request, f"¡Bienvenido de nuevo, {user.nombre}!")
                destino = request.GET.get("next", "")
                if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(destino)
                return redirect("core:dashboard")
            messages.error(request, "Credenciales incorrectas. Verifica tu correo y contraseña.")
    else:
        form = LoginForm()

    context = {
        "form": form,
        "usuarios_demo": UsuarioService.all() if settings.WHEELSON_MODO_DEMO else [],
        "total_personas": len(UsuarioService.all(limit=1000)),
        "total_empresas": len(EmpresaService.all(limit=1000)),
        "total_proyectos": len(ProyectoService.all(limit=1000)),
    }
    return render(request, "auth/login.html", context)


def registro_view(request):
    if request.usuario and not request.GET.get("force"):
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            if UsuarioService.get_by_email(email):
                form.add_error("email", "Ya existe una cuenta registrada con este correo.")
            else:
                data = form.cleaned_data.copy()
                data.pop("password_confirm", None)
                try:
                    nuevo_usuario = UsuarioService.create(**data)
                except UniqueProperty:
                    form.add_error("email", "Ya existe una cuenta registrada con este correo.")
                    return render(request, "auth/registro.html", {"form": form})
                _iniciar_sesion(request, nuevo_usuario)
                messages.success(request, f"¡Cuenta creada con éxito! Bienvenido a WheelsOn, {nuevo_usuario.nombre}.")
                return redirect("core:dashboard")
    else:
        form = RegistroForm()

    return render(request, "auth/registro.html", {"form": form})


def logout_view(request):
    # Solo por POST: un enlace externo no puede cerrar la sesión de nadie
    if request.method != "POST":
        return redirect("core:dashboard")
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente. ¡Hasta pronto!")
    return redirect("core:login")


# ==============================================================================
# FASE 9: VISUALIZACIÓN INTERACTIVA DE GRAFOS CON VIS.JS
# ==============================================================================

def grafo_interactivo(request):
    """
    Vista principal del explorador interactivo de grafos con Vis.js Network.
    Permite visualizar la red completa o subgrafos egocéntricos con controles de física y filtros.
    """
    subgrafo_uid = request.GET.get("subgrafo", "").strip() or None
    busqueda = request.GET.get("q", "").strip() or None
    
    # Obtener datos iniciales
    datos_grafo = GrafoVisualizacionService.obtener_datos_grafo(
        subgrafo_uid=subgrafo_uid,
        busqueda=busqueda,
        permisos=request.permisos,
    )

    context = {
        "subgrafo_uid": subgrafo_uid,
        "busqueda": busqueda or "",
        "usuarios_para_filtro": UsuarioService.all(),
        "stats": datos_grafo["stats"],
        "datos_grafo": datos_grafo,
    }
    return render(request, "grafo/interactivo.html", context)


def grafo_data_api(request):
    """
    Endpoint JSON que provee nodos y aristas filtradas dinámicamente para Vis.js Network.
    Soporta filtros por tipo de nodo, búsqueda por texto y subgrafos por UID.
    """
    subgrafo_uid = request.GET.get("subgrafo", "").strip() or None
    busqueda = request.GET.get("q", "").strip() or None
    tipos_str = request.GET.get("tipos", "").strip()
    
    tipos_nodo = [t.strip() for t in tipos_str.split(",") if t.strip()] if tipos_str else None

    datos = GrafoVisualizacionService.obtener_datos_grafo(
        subgrafo_uid=subgrafo_uid,
        tipos_nodo=tipos_nodo,
        busqueda=busqueda,
        permisos=request.permisos,
    )
    return JsonResponse(datos)


# ==============================================================================
# PÁGINAS DE ERROR
# ==============================================================================

def no_encontrado(request, exception=None):
    # Una dirección que no existe no pasa por las vistas: se carga la sesión para mostrar el menú
    if getattr(request, "usuario", None) is None:
        from core.permisos import Permisos
        try:
            usuario = UsuarioService.get(request.session.get("active_user_uid"))
        except Exception:
            usuario = None
        request.usuario = usuario
        request.permisos = Permisos(usuario)
    return render(request, "404.html", status=404)


def error_del_servidor(request):
    # Página sin consultas ni contexto: si algo falló, dibujarla no puede volver a fallar.
    return HttpResponse(render_to_string("500.html"), status=500)


def csrf_vencido(request, reason=""):
    """El formulario venía de una página desactualizada: se vuelve a ella con un aviso."""
    messages.warning(request, "La página estaba desactualizada y no se guardó nada. Inténtalo de nuevo.")
    return _volver(request, "core:dashboard")
