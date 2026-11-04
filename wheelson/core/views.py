from django.shortcuts import render, redirect
from django.contrib import messages
from core.forms import UsuarioForm, EmpresaForm, HabilidadForm, ProyectoForm, OfertaForm
from core.services import (
    UsuarioService,
    EmpresaService,
    HabilidadService,
    ProyectoService,
    OfertaService,
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
    return render(request, "usuarios/detalle.html", {"usuario": usuario})


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
    return render(request, "empresas/detalle.html", {"empresa": empresa})


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
    return render(request, "proyectos/detalle.html", {"proyecto": proyecto})


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
    return render(request, "ofertas/detalle.html", {"oferta": oferta})


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
