from django.shortcuts import render, redirect
from django.contrib import messages
from core.forms import (
    UsuarioForm,
    EmpresaForm,
    HabilidadForm,
    ProyectoForm,
    OfertaForm,
    ConectarUsuarioForm,
    VincularHabilidadUsuarioForm,
    ExperienciaLaboralForm,
    ParticipacionProyectoForm,
    PublicarOfertaEmpresaForm,
    RequisitoOfertaForm,
    PostulacionForm,
)
from core.services import (
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


def dashboard(request):
    total_usuarios = len(UsuarioService.all())
    total_empresas = len(EmpresaService.all())
    total_ofertas = len(OfertaService.all())
    total_proyectos = len(ProyectoService.all())
    total_habilidades = len(HabilidadService.all())

    context = {
        "app_name": "WheelsOn",
        "page_title": "Dashboard",
        "total_usuarios": total_usuarios,
        "total_empresas": total_empresas,
        "total_ofertas": total_ofertas,
        "total_proyectos": total_proyectos,
        "total_habilidades": total_habilidades,
        "usuarios_recientes": UsuarioService.all(limit=5),
        "ofertas_recientes": OfertaService.all(limit=5),
    }
    return render(request, "dashboard.html", context)


# ==============================================================================
# CRUD USUARIOS
# ==============================================================================

def usuarios_lista(request):
    query = request.GET.get("q", "").strip().lower()
    usuarios = UsuarioService.all()
    if query:
        usuarios = [
            u for u in usuarios
            if query in u.nombre.lower()
            or query in u.apellido.lower()
            or query in (u.titulo_profesional or "").lower()
            or query in (u.ubicacion or "").lower()
        ]
    return render(request, "usuarios/lista.html", {"usuarios": usuarios, "query": query})


def usuario_crear(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            u = UsuarioService.create(**form.cleaned_data)
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

    context = {
        "usuario": usuario,
        "habilidades_rel": HabilidadUsuarioService.listar_por_usuario(uid),
        "empleos_rel": EmpleoService.listar_por_usuario(uid),
        "proyectos_rel": ParticipacionProyectoService.listar_por_usuario(uid),
        "conexiones_rel": ConexionService.listar(uid),
        "postulaciones_rel": PostulacionService.listar_por_usuario(uid),
        "todas_habilidades": HabilidadService.all(),
        "todas_empresas": EmpresaService.all(),
        "todos_proyectos": ProyectoService.all(),
        "todos_usuarios": [u for u in UsuarioService.all() if u.uid != uid],
    }
    return render(request, "usuarios/detalle.html", context)


def usuario_editar(request, uid):
    usuario = UsuarioService.get(uid)
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:usuarios_lista")

    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if not data.get("password"):
                data.pop("password", None)
            UsuarioService.update(uid, **data)
            messages.success(request, f"Perfil de '{usuario.nombre_completo}' actualizado.")
            return redirect("core:usuario_detalle", uid=uid)
    else:
        form = UsuarioForm(initial={
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

    if request.method == "POST":
        nombre = usuario.nombre_completo
        UsuarioService.delete(uid)
        messages.success(request, f"Usuario '{nombre}' eliminado.")
        return redirect("core:usuarios_lista")

    return render(request, "usuarios/confirmar_eliminar.html", {"objeto": usuario, "tipo": "Usuario"})


# ==============================================================================
# CRUD EMPRESAS
# ==============================================================================

def empresas_lista(request):
    query = request.GET.get("q", "").strip().lower()
    empresas = EmpresaService.all()
    if query:
        empresas = [
            e for e in empresas
            if query in e.nombre.lower()
            or query in (e.industria or "").lower()
            or query in (e.ubicacion or "").lower()
        ]
    return render(request, "empresas/lista.html", {"empresas": empresas, "query": query})


def empresa_crear(request):
    if request.method == "POST":
        form = EmpresaForm(request.POST)
        if form.is_valid():
            e = EmpresaService.create(**form.cleaned_data)
            messages.success(request, f"Empresa '{e.nombre}' creada con exito.")
            return redirect("core:empresa_detalle", eid=e.eid)
    else:
        form = EmpresaForm()
    return render(request, "empresas/formulario.html", {"form": form, "accion": "Crear"})


def empresa_detalle(request, eid):
    empresa = EmpresaService.get(eid)
    if not empresa:
        messages.error(request, "Empresa no encontrada.")
        return redirect("core:empresas_lista")

    context = {
        "empresa": empresa,
        "ofertas_rel": PublicacionOfertaService.listar_por_empresa(eid),
        "empleados_rel": EmpleoService.listar_por_empresa(eid),
        "todos_usuarios": UsuarioService.all(),
    }
    return render(request, "empresas/detalle.html", context)


def empresa_editar(request, eid):
    empresa = EmpresaService.get(eid)
    if not empresa:
        messages.error(request, "Empresa no encontrada.")
        return redirect("core:empresas_lista")

    if request.method == "POST":
        form = EmpresaForm(request.POST)
        if form.is_valid():
            EmpresaService.update(eid, **form.cleaned_data)
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

    if request.method == "POST":
        nombre = empresa.nombre
        EmpresaService.delete(eid)
        messages.success(request, f"Empresa '{nombre}' eliminada.")
        return redirect("core:empresas_lista")

    return render(request, "empresas/confirmar_eliminar.html", {"objeto": empresa, "tipo": "Empresa"})


# ==============================================================================
# CRUD HABILIDADES
# ==============================================================================

def habilidades_lista(request):
    query = request.GET.get("q", "").strip().lower()
    habilidades = HabilidadService.all()
    if query:
        habilidades = [
            h for h in habilidades
            if query in h.nombre.lower() or query in (h.categoria or "").lower()
        ]
    form = HabilidadForm()
    return render(request, "habilidades/lista.html", {"habilidades": habilidades, "form": form, "query": query})


def habilidad_crear(request):
    if request.method == "POST":
        form = HabilidadForm(request.POST)
        if form.is_valid():
            h = HabilidadService.create(**form.cleaned_data)
            messages.success(request, f"Habilidad '{h.nombre}' registrada.")
        else:
            messages.error(request, "Error al registrar la habilidad.")
    return redirect("core:habilidades_lista")


def habilidad_eliminar(request, hid):
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
    proyectos = ProyectoService.all()
    if query:
        proyectos = [
            p for p in proyectos
            if query in p.nombre.lower()
            or query in (p.descripcion or "").lower()
            or any(query in t.lower() for t in (p.tecnologias or []))
        ]
    return render(request, "proyectos/lista.html", {"proyectos": proyectos, "query": query})


def proyecto_crear(request):
    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            p = ProyectoService.create(**form.cleaned_data)
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

    context = {
        "proyecto": proyecto,
        "miembros_rel": ParticipacionProyectoService.listar_por_proyecto(pid),
        "todos_usuarios": UsuarioService.all(),
    }
    return render(request, "proyectos/detalle.html", context)


def proyecto_editar(request, pid):
    proyecto = ProyectoService.get(pid)
    if not proyecto:
        messages.error(request, "Proyecto no encontrado.")
        return redirect("core:proyectos_lista")

    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            ProyectoService.update(pid, **form.cleaned_data)
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
    return render(request, "proyectos/formulario.html", {"form": form, "proyecto": proyecto, "accion": "Editar"})


def proyecto_eliminar(request, pid):
    proyecto = ProyectoService.get(pid)
    if not proyecto:
        messages.error(request, "Proyecto no encontrado.")
        return redirect("core:proyectos_lista")

    if request.method == "POST":
        nombre = proyecto.nombre
        ProyectoService.delete(pid)
        messages.success(request, f"Proyecto '{nombre}' eliminado.")
        return redirect("core:proyectos_lista")

    return render(request, "proyectos/confirmar_eliminar.html", {"objeto": proyecto, "tipo": "Proyecto"})


# ==============================================================================
# CRUD OFERTAS
# ==============================================================================

def ofertas_lista(request):
    query = request.GET.get("q", "").strip().lower()
    modalidad = request.GET.get("modalidad", "").strip().lower()
    ofertas = OfertaService.all()

    if query:
        ofertas = [
            o for o in ofertas
            if query in o.titulo.lower()
            or query in (o.descripcion or "").lower()
            or query in (o.ubicacion or "").lower()
        ]
    if modalidad:
        ofertas = [o for o in ofertas if (o.modalidad or "").lower() == modalidad]

    return render(request, "ofertas/lista.html", {"ofertas": ofertas, "query": query, "modalidad_filtro": modalidad})


def oferta_crear(request):
    if request.method == "POST":
        form = OfertaForm(request.POST)
        if form.is_valid():
            o = OfertaService.create(**form.cleaned_data)
            messages.success(request, f"Vacante '{o.titulo}' publicada con exito.")
            return redirect("core:oferta_detalle", oid=o.oid)
    else:
        form = OfertaForm()
    return render(request, "ofertas/formulario.html", {"form": form, "accion": "Crear"})


def oferta_detalle(request, oid):
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Oferta no encontrada.")
        return redirect("core:ofertas_lista")

    context = {
        "oferta": oferta,
        "empresa_rel": PublicacionOfertaService.obtener_empresa(oid),
        "requisitos_rel": RequisitoOfertaService.listar_por_oferta(oid),
        "candidatos_rel": PostulacionService.listar_por_oferta(oid),
        "todas_habilidades": HabilidadService.all(),
        "todas_empresas": EmpresaService.all(),
        "todos_usuarios": UsuarioService.all(),
    }
    return render(request, "ofertas/detalle.html", context)


def oferta_editar(request, oid):
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Oferta no encontrada.")
        return redirect("core:ofertas_lista")

    if request.method == "POST":
        form = OfertaForm(request.POST)
        if form.is_valid():
            OfertaService.update(oid, **form.cleaned_data)
            messages.success(request, f"Vacante '{oferta.titulo}' actualizada.")
            return redirect("core:oferta_detalle", oid=oid)
    else:
        form = OfertaForm(initial={
            "titulo": oferta.titulo,
            "descripcion": oferta.descripcion,
            "salario_min": oferta.salario_min,
            "salario_max": oferta.salario_max,
            "modalidad": oferta.modalidad,
            "ubicacion": oferta.ubicacion,
            "estado": oferta.estado,
        })
    return render(request, "ofertas/formulario.html", {"form": form, "oferta": oferta, "accion": "Editar"})


def oferta_eliminar(request, oid):
    oferta = OfertaService.get(oid)
    if not oferta:
        messages.error(request, "Oferta no encontrada.")
        return redirect("core:ofertas_lista")

    if request.method == "POST":
        titulo = oferta.titulo
        OfertaService.delete(oid)
        messages.success(request, f"Oferta '{titulo}' eliminada.")
        return redirect("core:ofertas_lista")

    return render(request, "ofertas/confirmar_eliminar.html", {"objeto": oferta, "tipo": "Oferta"})


# ==============================================================================
# VISTAS DE GESTION DE RELACIONES (FASE 5)
# ==============================================================================

def conexiones_red(request):
    usuarios = UsuarioService.all()
    uid_seleccionado = request.GET.get("uid") or (usuarios[0].uid if usuarios else None)
    usuario_activo = UsuarioService.get(uid_seleccionado) if uid_seleccionado else None

    conexiones = ConexionService.listar(usuario_activo.uid) if usuario_activo else []
    uids_conectados = {c["usuario"].uid for c in conexiones} | ({usuario_activo.uid} if usuario_activo else set())
    sugerencias = [u for u in usuarios if u.uid not in uids_conectados]

    context = {
        "usuarios": usuarios,
        "usuario_activo": usuario_activo,
        "conexiones": conexiones,
        "sugerencias": sugerencias,
    }
    return render(request, "conexiones/red.html", context)


def conexion_conectar(request):
    if request.method == "POST":
        uid_origen = request.POST.get("uid_origen")
        uid_destino = request.POST.get("uid_destino")
        mensaje = request.POST.get("mensaje", "")
        if uid_origen and uid_destino:
            ConexionService.conectar(uid_origen, uid_destino, mensaje=mensaje)
            messages.success(request, "Conexion establecida exitosamente en el grafo.")
        else:
            messages.error(request, "Parametros invalidos para la conexion.")
    return redirect(request.META.get("HTTP_REFERER", "core:conexiones_red"))


def conexion_desconectar(request, uid_origen, uid_destino):
    if request.method == "POST":
        ConexionService.desconectar(uid_origen, uid_destino)
        messages.success(request, "Conexion eliminada del grafo.")
    return redirect(request.META.get("HTTP_REFERER", "core:conexiones_red"))


def usuario_habilidad_agregar(request, uid):
    if request.method == "POST":
        hid = request.POST.get("hid")
        nivel = request.POST.get("nivel", "intermedio")
        anios = request.POST.get("anios_experiencia", 1)
        if hid:
            HabilidadUsuarioService.vincular(uid, hid, nivel=nivel, anios_experiencia=anios)
            messages.success(request, "Habilidad vinculada al perfil.")
        else:
            messages.error(request, "Debe seleccionar una habilidad valida.")
    return redirect("core:usuario_detalle", uid=uid)


def usuario_habilidad_eliminar(request, uid, hid):
    if request.method == "POST":
        HabilidadUsuarioService.desvincular(uid, hid)
        messages.success(request, "Habilidad desvinculada del perfil.")
    return redirect("core:usuario_detalle", uid=uid)


def usuario_experiencia_agregar(request, uid):
    if request.method == "POST":
        eid = request.POST.get("eid")
        cargo = request.POST.get("cargo", "").strip()
        fecha_inicio = request.POST.get("fecha_inicio") or None
        fecha_fin = request.POST.get("fecha_fin") or None
        actual = request.POST.get("actual") == "on" or request.POST.get("actual") == "true"
        if eid and cargo:
            EmpleoService.vincular(uid, eid, cargo=cargo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, actual=actual)
            messages.success(request, "Experiencia laboral anadida al perfil.")
        else:
            messages.error(request, "Debe indicar empresa y cargo obligatoriamente.")
    return redirect("core:usuario_detalle", uid=uid)


def usuario_experiencia_eliminar(request, uid, eid):
    if request.method == "POST":
        EmpleoService.desvincular(uid, eid)
        messages.success(request, "Experiencia laboral eliminada del perfil.")
    return redirect("core:usuario_detalle", uid=uid)


def proyecto_colaborador_agregar(request, pid):
    if request.method == "POST":
        uid = request.POST.get("uid")
        rol = request.POST.get("rol", "Colaborador").strip()
        fecha_inicio = request.POST.get("fecha_inicio") or None
        if uid:
            ParticipacionProyectoService.vincular(uid, pid, rol=rol, fecha_inicio=fecha_inicio)
            messages.success(request, "Colaborador incorporado al proyecto.")
        else:
            messages.error(request, "Debe seleccionar un usuario para vincularlo.")
    return redirect("core:proyecto_detalle", pid=pid)


def proyecto_colaborador_eliminar(request, pid, uid):
    if request.method == "POST":
        ParticipacionProyectoService.desvincular(uid, pid)
        messages.success(request, "Colaborador desvinculado del proyecto.")
    return redirect("core:proyecto_detalle", pid=pid)


def oferta_requisito_agregar(request, oid):
    if request.method == "POST":
        hid = request.POST.get("hid")
        nivel_minimo = request.POST.get("nivel_minimo", "basico")
        prioridad = request.POST.get("prioridad", "obligatoria")
        if hid:
            RequisitoOfertaService.vincular(oid, hid, nivel_minimo=nivel_minimo, prioridad=prioridad)
            messages.success(request, "Requisito de habilidad agregado a la oferta.")
        else:
            messages.error(request, "Debe seleccionar una habilidad.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_requisito_eliminar(request, oid, hid):
    if request.method == "POST":
        RequisitoOfertaService.desvincular(oid, hid)
        messages.success(request, "Requisito eliminado de la oferta.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_empresa_asignar(request, oid):
    if request.method == "POST":
        eid = request.POST.get("eid")
        if eid:
            PublicacionOfertaService.vincular(eid, oid)
            messages.success(request, "Empresa emisora vinculada a la vacante.")
        else:
            messages.error(request, "Debe seleccionar una empresa.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_postular(request, oid):
    if request.method == "POST":
        uid = request.POST.get("uid")
        carta = request.POST.get("carta_presentacion", "").strip()
        if uid:
            PostulacionService.postular(uid, oid, carta_presentacion=carta)
            messages.success(request, "Postulacion registrada con exito en el grafo.")
        else:
            messages.error(request, "Debe seleccionar un usuario para postularse.")
    return redirect("core:oferta_detalle", oid=oid)


def oferta_postulacion_eliminar(request, oid, uid):
    if request.method == "POST":
        PostulacionService.desvincular(uid, oid)
        messages.success(request, "Postulacion cancelada.")
    return redirect("core:oferta_detalle", oid=oid)

