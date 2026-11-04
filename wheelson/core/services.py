import uuid
import socket
import time
from datetime import date
from django.contrib.auth.hashers import make_password
from core.models import Usuario, Empresa, Habilidad, Proyecto, Oferta

_last_neo4j_check = 0
_neo4j_is_live = False


def is_neo4j_available():
    global _last_neo4j_check, _neo4j_is_live
    now = time.time()
    if now - _last_neo4j_check < 5.0:
        return _neo4j_is_live
    _last_neo4j_check = now
    try:
        with socket.create_connection(("localhost", 7687), timeout=0.08):
            _neo4j_is_live = True
            return True
    except (OSError, socket.timeout):
        _neo4j_is_live = False
        return False


class BaseMemoryStore:
    def __init__(self):
        self._store = {}

    def add(self, key, item):
        self._store[str(key)] = item
        return item

    def get(self, key):
        return self._store.get(str(key))

    def all(self):
        return list(self._store.values())

    def remove(self, key):
        if str(key) in self._store:
            del self._store[str(key)]
            return True
        return False


_memory_usuarios = BaseMemoryStore()
_memory_empresas = BaseMemoryStore()
_memory_habilidades = BaseMemoryStore()
_memory_proyectos = BaseMemoryStore()
_memory_ofertas = BaseMemoryStore()


class UsuarioService:
    @staticmethod
    def create(nombre, apellido, email, password=None, titulo_profesional="Profesional",
               ubicacion="No especificada", biografia="", foto_url="/static/img/default-avatar.svg"):
        password_hash = make_password(password or "WheelsOn2026*")
        if is_neo4j_available():
            try:
                return Usuario(
                    nombre=nombre.strip(),
                    apellido=apellido.strip(),
                    email=email.strip().lower(),
                    password_hash=password_hash,
                    titulo_profesional=titulo_profesional.strip() if titulo_profesional else "Profesional",
                    ubicacion=ubicacion.strip() if ubicacion else "No especificada",
                    biografia=biografia.strip() if biografia else "",
                    foto_url=foto_url,
                ).save()
            except Exception:
                pass

        user = Usuario(
            uid=f"usr_{uuid.uuid4().hex[:12]}",
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            titulo_profesional=titulo_profesional.strip() if titulo_profesional else "Profesional",
            ubicacion=ubicacion.strip() if ubicacion else "No especificada",
            biografia=biografia.strip() if biografia else "",
            foto_url=foto_url,
            fecha_registro=date.today(),
        )
        return _memory_usuarios.add(user.uid, user)

    @staticmethod
    def get(uid):
        if is_neo4j_available():
            try:
                return Usuario.nodes.get(uid=uid)
            except Exception:
                pass
        return _memory_usuarios.get(uid)

    @staticmethod
    def all(limit=100):
        if is_neo4j_available():
            try:
                nodes = list(Usuario.nodes.all()[:limit])
                if nodes:
                    return nodes
            except Exception:
                pass
        return _memory_usuarios.all()[:limit]

    @staticmethod
    def update(uid, **kwargs):
        user = UsuarioService.get(uid)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                if key == "password" and value:
                    setattr(user, "password_hash", make_password(value))
                else:
                    setattr(user, key, value)
        if is_neo4j_available():
            try:
                user.save()
            except Exception:
                pass
        _memory_usuarios.add(user.uid, user)
        return user

    @staticmethod
    def delete(uid):
        user = UsuarioService.get(uid)
        if not user:
            return False
        if is_neo4j_available():
            try:
                user.delete()
            except Exception:
                pass
        return _memory_usuarios.remove(uid)


class EmpresaService:
    @staticmethod
    def create(nombre, industria, ubicacion="No especificada", descripcion="",
               sitio_web="", tamano="mediana", logo_url="/static/img/default-company.svg"):
        if is_neo4j_available():
            try:
                return Empresa(
                    nombre=nombre.strip(),
                    industria=industria.strip(),
                    ubicacion=ubicacion.strip() if ubicacion else "No especificada",
                    descripcion=descripcion.strip() if descripcion else "",
                    sitio_web=sitio_web.strip() if sitio_web else "",
                    tamano=tamano,
                    logo_url=logo_url,
                ).save()
            except Exception:
                pass

        empresa = Empresa(
            eid=f"emp_{uuid.uuid4().hex[:12]}",
            nombre=nombre.strip(),
            industria=industria.strip(),
            ubicacion=ubicacion.strip() if ubicacion else "No especificada",
            descripcion=descripcion.strip() if descripcion else "",
            sitio_web=sitio_web.strip() if sitio_web else "",
            tamano=tamano,
            logo_url=logo_url,
        )
        return _memory_empresas.add(empresa.eid, empresa)

    @staticmethod
    def get(eid):
        if is_neo4j_available():
            try:
                return Empresa.nodes.get(eid=eid)
            except Exception:
                pass
        return _memory_empresas.get(eid)

    @staticmethod
    def all(limit=100):
        if is_neo4j_available():
            try:
                nodes = list(Empresa.nodes.all()[:limit])
                if nodes:
                    return nodes
            except Exception:
                pass
        return _memory_empresas.all()[:limit]

    @staticmethod
    def update(eid, **kwargs):
        empresa = EmpresaService.get(eid)
        if not empresa:
            return None
        for key, value in kwargs.items():
            if hasattr(empresa, key) and value is not None:
                setattr(empresa, key, value)
        if is_neo4j_available():
            try:
                empresa.save()
            except Exception:
                pass
        _memory_empresas.add(empresa.eid, empresa)
        return empresa

    @staticmethod
    def delete(eid):
        empresa = EmpresaService.get(eid)
        if not empresa:
            return False
        if is_neo4j_available():
            try:
                empresa.delete()
            except Exception:
                pass
        return _memory_empresas.remove(eid)


class HabilidadService:
    @staticmethod
    def create(nombre, categoria="tecnica", descripcion=""):
        if is_neo4j_available():
            try:
                return Habilidad(
                    nombre=nombre.strip(),
                    categoria=categoria,
                    descripcion=descripcion.strip() if descripcion else "",
                ).save()
            except Exception:
                pass

        habilidad = Habilidad(
            hid=f"hab_{uuid.uuid4().hex[:12]}",
            nombre=nombre.strip(),
            categoria=categoria,
            descripcion=descripcion.strip() if descripcion else "",
        )
        return _memory_habilidades.add(habilidad.hid, habilidad)

    @staticmethod
    def get(hid):
        if is_neo4j_available():
            try:
                return Habilidad.nodes.get(hid=hid)
            except Exception:
                pass
        return _memory_habilidades.get(hid)

    @staticmethod
    def all(limit=100):
        if is_neo4j_available():
            try:
                nodes = list(Habilidad.nodes.all()[:limit])
                if nodes:
                    return nodes
            except Exception:
                pass
        return _memory_habilidades.all()[:limit]

    @staticmethod
    def update(hid, **kwargs):
        habilidad = HabilidadService.get(hid)
        if not habilidad:
            return None
        for key, value in kwargs.items():
            if hasattr(habilidad, key) and value is not None:
                setattr(habilidad, key, value)
        if is_neo4j_available():
            try:
                habilidad.save()
            except Exception:
                pass
        _memory_habilidades.add(habilidad.hid, habilidad)
        return habilidad

    @staticmethod
    def delete(hid):
        habilidad = HabilidadService.get(hid)
        if not habilidad:
            return False
        if is_neo4j_available():
            try:
                habilidad.delete()
            except Exception:
                pass
        return _memory_habilidades.remove(hid)


class ProyectoService:
    @staticmethod
    def create(nombre, descripcion="", fecha_inicio=None, fecha_fin=None,
               estado="activo", tecnologias=None):
        if tecnologias is None:
            tecnologias = []
        elif isinstance(tecnologias, str):
            tecnologias = [t.strip() for t in tecnologias.split(",") if t.strip()]

        if is_neo4j_available():
            try:
                return Proyecto(
                    nombre=nombre.strip(),
                    descripcion=descripcion.strip() if descripcion else "",
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    estado=estado,
                    tecnologias=tecnologias,
                ).save()
            except Exception:
                pass

        proyecto = Proyecto(
            pid=f"pro_{uuid.uuid4().hex[:12]}",
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else "",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
            tecnologias=tecnologias,
        )
        return _memory_proyectos.add(proyecto.pid, proyecto)

    @staticmethod
    def get(pid):
        if is_neo4j_available():
            try:
                return Proyecto.nodes.get(pid=pid)
            except Exception:
                pass
        return _memory_proyectos.get(pid)

    @staticmethod
    def all(limit=100):
        if is_neo4j_available():
            try:
                nodes = list(Proyecto.nodes.all()[:limit])
                if nodes:
                    return nodes
            except Exception:
                pass
        return _memory_proyectos.all()[:limit]

    @staticmethod
    def update(pid, **kwargs):
        proyecto = ProyectoService.get(pid)
        if not proyecto:
            return None
        for key, value in kwargs.items():
            if hasattr(proyecto, key) and value is not None:
                if key == "tecnologias" and isinstance(value, str):
                    value = [t.strip() for t in value.split(",") if t.strip()]
                setattr(proyecto, key, value)
        if is_neo4j_available():
            try:
                proyecto.save()
            except Exception:
                pass
        _memory_proyectos.add(proyecto.pid, proyecto)
        return proyecto

    @staticmethod
    def delete(pid):
        proyecto = ProyectoService.get(pid)
        if not proyecto:
            return False
        if is_neo4j_available():
            try:
                proyecto.delete()
            except Exception:
                pass
        return _memory_proyectos.remove(pid)


class OfertaService:
    @staticmethod
    def create(titulo, descripcion="", salario_min=0.0, salario_max=0.0,
               modalidad="remoto", ubicacion="No especificada", estado="abierta"):
        s_min = float(salario_min or 0.0)
        s_max = float(salario_max or 0.0)
        if is_neo4j_available():
            try:
                return Oferta(
                    titulo=titulo.strip(),
                    descripcion=descripcion.strip() if descripcion else "",
                    salario_min=s_min,
                    salario_max=s_max,
                    modalidad=modalidad,
                    ubicacion=ubicacion.strip() if ubicacion else "No especificada",
                    estado=estado,
                ).save()
            except Exception:
                pass

        oferta = Oferta(
            oid=f"ofr_{uuid.uuid4().hex[:12]}",
            titulo=titulo.strip(),
            descripcion=descripcion.strip() if descripcion else "",
            salario_min=s_min,
            salario_max=s_max,
            modalidad=modalidad,
            ubicacion=ubicacion.strip() if ubicacion else "No especificada",
            estado=estado,
            fecha_publicacion=date.today(),
        )
        return _memory_ofertas.add(oferta.oid, oferta)

    @staticmethod
    def get(oid):
        if is_neo4j_available():
            try:
                return Oferta.nodes.get(oid=oid)
            except Exception:
                pass
        return _memory_ofertas.get(oid)

    @staticmethod
    def all(limit=100):
        if is_neo4j_available():
            try:
                nodes = list(Oferta.nodes.all()[:limit])
                if nodes:
                    return nodes
            except Exception:
                pass
        return _memory_ofertas.all()[:limit]

    @staticmethod
    def update(oid, **kwargs):
        oferta = OfertaService.get(oid)
        if not oferta:
            return None
        for key, value in kwargs.items():
            if hasattr(oferta, key) and value is not None:
                if key in ("salario_min", "salario_max"):
                    value = float(value or 0.0)
                setattr(oferta, key, value)
        if is_neo4j_available():
            try:
                oferta.save()
            except Exception:
                pass
        _memory_ofertas.add(oferta.oid, oferta)
        return oferta

    @staticmethod
    def delete(oid):
        oferta = OfertaService.get(oid)
        if not oferta:
            return False
        if is_neo4j_available():
            try:
                oferta.delete()
            except Exception:
                pass
        return _memory_ofertas.remove(oid)
