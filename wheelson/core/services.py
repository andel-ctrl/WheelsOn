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


class BaseEdgeStore:
    def __init__(self):
        self._edges = []

    def add(self, **kwargs):
        self._edges = [e for e in self._edges if not (
            e.get("source_id") == kwargs.get("source_id") and
            e.get("target_id") == kwargs.get("target_id")
        )]
        self._edges.append(kwargs)
        return kwargs

    def remove(self, source_id, target_id):
        before = len(self._edges)
        self._edges = [
            e for e in self._edges
            if not (e.get("source_id") == str(source_id) and e.get("target_id") == str(target_id))
        ]
        return len(self._edges) < before

    def find_by_source(self, source_id):
        return [e for e in self._edges if e.get("source_id") == str(source_id)]

    def find_by_target(self, target_id):
        return [e for e in self._edges if e.get("target_id") == str(target_id)]

    def exists(self, source_id, target_id):
        return any(
            e.get("source_id") == str(source_id) and e.get("target_id") == str(target_id)
            for e in self._edges
        )


_memory_usuarios = BaseMemoryStore()
_memory_empresas = BaseMemoryStore()
_memory_habilidades = BaseMemoryStore()
_memory_proyectos = BaseMemoryStore()
_memory_ofertas = BaseMemoryStore()

_memory_conexiones = BaseEdgeStore()
_memory_empleos = BaseEdgeStore()
_memory_habilidades_usuario = BaseEdgeStore()
_memory_participaciones = BaseEdgeStore()
_memory_publicaciones = BaseEdgeStore()
_memory_requisitos = BaseEdgeStore()
_memory_postulaciones = BaseEdgeStore()


def _init_memory_seed():
    if _memory_usuarios.all():
        return

    # Seed Usuarios
    u1 = Usuario(uid="usr_carlos001", nombre="Carlos", apellido="Santana", email="carlos@wheelson.com",
                 password_hash="pbkdf2_sha256$hashed", titulo_profesional="Senior Backend & Graph Architect",
                 ubicacion="Bogota, Colombia", biografia="Especialista en bases de datos de grafos, modelado Cypher y sistemas distribuidos en Python.")
    u2 = Usuario(uid="usr_laura002", nombre="Laura", apellido="Gomez", email="laura@wheelson.com",
                 password_hash="pbkdf2_sha256$hashed", titulo_profesional="Tech Lead & Cloud Specialist",
                 ubicacion="Medellin, Colombia", biografia="Lider tecnica con 8 anos de experiencia en arquitecturas de datos en la nube y DevOps.")
    u3 = Usuario(uid="usr_diego003", nombre="Diego", apellido="Morales", email="diego@wheelson.com",
                 password_hash="pbkdf2_sha256$hashed", titulo_profesional="Data Engineer & ETL Developer",
                 ubicacion="Cali, Colombia", biografia="Ingeniero de datos enfocado en pipelines de alto volumen y optimizacion de grafos de conocimiento.")
    u4 = Usuario(uid="usr_sofia004", nombre="Sofia", apellido="Castro", email="sofia@wheelson.com",
                 password_hash="pbkdf2_sha256$hashed", titulo_profesional="UX/UI & Frontend Engineer",
                 ubicacion="Pereira, Colombia", biografia="Disenadora de experiencias interactivas y desarrollo frontend con Tailwind, Alpine y visualizacion.")

    for u in (u1, u2, u3, u4):
        _memory_usuarios.add(u.uid, u)

    # Seed Empresas
    e1 = Empresa(eid="emp_nexus01", nombre="Nexus Corp", industria="Fintech", ubicacion="Bogota, Colombia",
                 descripcion="Empresa lider en soluciones tecnologicas financieras impulsadas por grafos.", tamano="grande")
    e2 = Empresa(eid="emp_techin02", nombre="Tech Innovators", industria="Software", ubicacion="Medellin, Colombia",
                 descripcion="Hub de investigacion y desarrollo de productos digitales avanzados.", tamano="mediana")
    e3 = Empresa(eid="emp_globant03", nombre="Globant Latam", industria="Consultoria IT", ubicacion="Bogota, Colombia",
                 descripcion="Transformacion digital y arquitectura de software de clase mundial.", tamano="grande")

    for e in (e1, e2, e3):
        _memory_empresas.add(e.eid, e)

    # Seed Habilidades
    h1 = Habilidad(hid="hab_py01", nombre="Python", categoria="tecnica", descripcion="Lenguaje principal de desarrollo backend y analitica.")
    h2 = Habilidad(hid="hab_neo02", nombre="Neo4j", categoria="tecnica", descripcion="Base de datos orientada a grafos y motor Bolt.")
    h3 = Habilidad(hid="hab_cyp03", nombre="Cypher", categoria="tecnica", descripcion="Lenguaje declarativo de consulta sobre nodos y aristas.")
    h4 = Habilidad(hid="hab_doc04", nombre="Docker", categoria="tecnica", descripcion="Contenerizacion y despliegue de microservicios.")
    h5 = Habilidad(hid="hab_lid05", nombre="Liderazgo", categoria="blanda", descripcion="Gestion de equipos de alto rendimiento y coordinacion.")
    h6 = Habilidad(hid="hab_ing06", nombre="Ingles Tecnico", categoria="idioma", descripcion="Comunicacion fluida en entornos internacionales.")

    for h in (h1, h2, h3, h4, h5, h6):
        _memory_habilidades.add(h.hid, h)

    # Seed Proyectos
    p1 = Proyecto(pid="proy_graph01", nombre="Motor de Grafos WheelsOn",
                  descripcion="Plataforma de investigacion y desarrollo para navegacion y analisis de redes complejas.",
                  estado="activo", tecnologias=["Python", "Django", "Neo4j", "Cypher", "Vis.js"])
    p2 = Proyecto(pid="proy_fintech02", nombre="Plataforma Fintech AI",
                  descripcion="Deteccion de patrones anomalos y analisis de comunidades en redes de pago.",
                  estado="activo", tecnologias=["Python", "Docker", "Neo4j"])

    for p in (p1, p2):
        _memory_proyectos.add(p.pid, p)

    # Seed Ofertas
    o1 = Oferta(oid="ofr_dataeng01", titulo="Senior Data Engineer",
                descripcion="Buscamos especialista en modelos de grafos para optimizar almacenamiento y consultas analiticas.",
                salario_min=8000000.0, salario_max=12000000.0, modalidad="remoto", ubicacion="Colombia", estado="abierta")
    o2 = Oferta(oid="ofr_arch02", titulo="Lead Graph Architect",
                descripcion="Liderazgo en diseno de ontologias de grafos y algoritmos de recomendacion colaborativa.",
                salario_min=14000000.0, salario_max=18000000.0, modalidad="hibrido", ubicacion="Bogota", estado="abierta")

    for o in (o1, o2):
        _memory_ofertas.add(o.oid, o)

    # Seed Relaciones (:CONECTA_CON)
    _memory_conexiones.add(source_id="usr_carlos001", target_id="usr_laura002", mensaje="Gran trabajo en la arquitectura de grafos!", estado="aceptada", fecha="2026-11-01")
    _memory_conexiones.add(source_id="usr_carlos001", target_id="usr_diego003", mensaje="Un gusto colaborar en WheelsOn", estado="aceptada", fecha="2026-11-02")
    _memory_conexiones.add(source_id="usr_laura002", target_id="usr_sofia004", mensaje="Coordinemos los nuevos componentes de interfaz", estado="aceptada", fecha="2026-11-03")

    # Seed Relaciones (:TRABAJA_EN)
    _memory_empleos.add(source_id="usr_carlos001", target_id="emp_techin02", cargo="Principal Graph Architect", fecha_inicio="2024-01-15", fecha_fin=None, actual=True)
    _memory_empleos.add(source_id="usr_laura002", target_id="emp_globant03", cargo="Senior Cloud Lead", fecha_inicio="2023-05-01", fecha_fin=None, actual=True)
    _memory_empleos.add(source_id="usr_diego003", target_id="emp_nexus01", cargo="Data Engineer", fecha_inicio="2022-03-10", fecha_fin="2024-06-30", actual=False)

    # Seed Relaciones (:TIENE_HABILIDAD)
    _memory_habilidades_usuario.add(source_id="usr_carlos001", target_id="hab_py01", nivel="experto", anios_experiencia=7)
    _memory_habilidades_usuario.add(source_id="usr_carlos001", target_id="hab_neo02", nivel="experto", anios_experiencia=5)
    _memory_habilidades_usuario.add(source_id="usr_carlos001", target_id="hab_cyp03", nivel="avanzado", anios_experiencia=4)
    _memory_habilidades_usuario.add(source_id="usr_laura002", target_id="hab_py01", nivel="experto", anios_experiencia=8)
    _memory_habilidades_usuario.add(source_id="usr_laura002", target_id="hab_doc04", nivel="avanzado", anios_experiencia=5)
    _memory_habilidades_usuario.add(source_id="usr_laura002", target_id="hab_lid05", nivel="avanzado", anios_experiencia=4)
    _memory_habilidades_usuario.add(source_id="usr_diego003", target_id="hab_py01", nivel="avanzado", anios_experiencia=4)
    _memory_habilidades_usuario.add(source_id="usr_diego003", target_id="hab_neo02", nivel="intermedio", anios_experiencia=2)

    # Seed Relaciones (:PARTICIPA_EN)
    _memory_participaciones.add(source_id="usr_carlos001", target_id="proy_graph01", rol="Tech Director & Architect", fecha_inicio="2026-10-01", activo=True)
    _memory_participaciones.add(source_id="usr_laura002", target_id="proy_graph01", rol="Cloud Specialist", fecha_inicio="2026-10-15", activo=True)
    _memory_participaciones.add(source_id="usr_sofia004", target_id="proy_graph01", rol="UI/UX Lead", fecha_inicio="2026-10-20", activo=True)

    # Seed Relaciones (:PUBLICA)
    _memory_publicaciones.add(source_id="emp_nexus01", target_id="ofr_dataeng01", fecha_publicacion="2026-11-01")
    _memory_publicaciones.add(source_id="emp_globant03", target_id="ofr_arch02", fecha_publicacion="2026-11-02")

    # Seed Relaciones (:REQUIERE)
    _memory_requisitos.add(source_id="ofr_dataeng01", target_id="hab_py01", nivel_minimo="avanzado", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_dataeng01", target_id="hab_neo02", nivel_minimo="intermedio", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_arch02", target_id="hab_cyp03", nivel_minimo="avanzado", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_arch02", target_id="hab_lid05", nivel_minimo="avanzado", prioridad="deseable")

    # Seed Relaciones (:POSTULA_A)
    _memory_postulaciones.add(source_id="usr_diego003", target_id="ofr_dataeng01", fecha="2026-11-03", estado="enviada",
                              carta_presentacion="Cuento con experiencia solida en pipelines de datos y modelado relacional y de grafos.")


_init_memory_seed()


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


# ==============================================================================
# SERVICIOS DE GESTION DE RELACIONES (FASE 5)
# ==============================================================================

class ConexionService:
    @staticmethod
    def conectar(uid_origen, uid_destino, mensaje="", estado="aceptada"):
        if uid_origen == uid_destino:
            return None
        u1 = UsuarioService.get(uid_origen)
        u2 = UsuarioService.get(uid_destino)
        if not u1 or not u2:
            return None

        if is_neo4j_available():
            try:
                u1.conexiones.connect(u2, {"mensaje": mensaje, "estado": estado, "fecha": date.today()})
            except Exception:
                pass

        return _memory_conexiones.add(
            source_id=str(uid_origen),
            target_id=str(uid_destino),
            mensaje=mensaje,
            estado=estado,
            fecha=str(date.today()),
        )

    @staticmethod
    def desconectar(uid_origen, uid_destino):
        u1 = UsuarioService.get(uid_origen)
        u2 = UsuarioService.get(uid_destino)
        if is_neo4j_available() and u1 and u2:
            try:
                u1.conexiones.disconnect(u2)
            except Exception:
                pass
        removed1 = _memory_conexiones.remove(uid_origen, uid_destino)
        removed2 = _memory_conexiones.remove(uid_destino, uid_origen)
        return removed1 or removed2

    @staticmethod
    def estan_conectados(uid_origen, uid_destino):
        u1 = UsuarioService.get(uid_origen)
        u2 = UsuarioService.get(uid_destino)
        if is_neo4j_available() and u1 and u2:
            try:
                return u1.conexiones.is_connected(u2)
            except Exception:
                pass
        return _memory_conexiones.exists(uid_origen, uid_destino) or _memory_conexiones.exists(uid_destino, uid_origen)

    @staticmethod
    def listar(uid):
        resultado = []
        if is_neo4j_available():
            try:
                u = Usuario.nodes.get(uid=uid)
                for c in u.conexiones.all():
                    rel = u.conexiones.relationship(c)
                    resultado.append({
                        "usuario": c,
                        "mensaje": getattr(rel, "mensaje", ""),
                        "estado": getattr(rel, "estado", "aceptada"),
                        "fecha": str(getattr(rel, "fecha", date.today())),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        edges = _memory_conexiones.find_by_source(uid) + _memory_conexiones.find_by_target(uid)
        seen = set()
        for e in edges:
            other_id = e["target_id"] if e["source_id"] == str(uid) else e["source_id"]
            if other_id not in seen:
                seen.add(other_id)
                target_user = UsuarioService.get(other_id)
                if target_user:
                    resultado.append({
                        "usuario": target_user,
                        "mensaje": e.get("mensaje", ""),
                        "estado": e.get("estado", "aceptada"),
                        "fecha": e.get("fecha", str(date.today())),
                    })
        return resultado


class EmpleoService:
    @staticmethod
    def vincular(uid, eid, cargo, fecha_inicio=None, fecha_fin=None, actual=True):
        u = UsuarioService.get(uid)
        e = EmpresaService.get(eid)
        if not u or not e:
            return None

        if is_neo4j_available():
            try:
                u.empleos.connect(e, {
                    "cargo": cargo.strip(),
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "actual": bool(actual),
                })
            except Exception:
                pass

        return _memory_empleos.add(
            source_id=str(uid),
            target_id=str(eid),
            cargo=cargo.strip(),
            fecha_inicio=str(fecha_inicio) if fecha_inicio else None,
            fecha_fin=str(fecha_fin) if fecha_fin else None,
            actual=bool(actual),
        )

    @staticmethod
    def desvincular(uid, eid):
        u = UsuarioService.get(uid)
        e = EmpresaService.get(eid)
        if is_neo4j_available() and u and e:
            try:
                u.empleos.disconnect(e)
            except Exception:
                pass
        return _memory_empleos.remove(uid, eid)

    @staticmethod
    def listar_por_usuario(uid):
        resultado = []
        if is_neo4j_available():
            try:
                u = Usuario.nodes.get(uid=uid)
                for emp in u.empleos.all():
                    rel = u.empleos.relationship(emp)
                    resultado.append({
                        "empresa": emp,
                        "cargo": getattr(rel, "cargo", "Colaborador"),
                        "fecha_inicio": str(getattr(rel, "fecha_inicio", "") or ""),
                        "fecha_fin": str(getattr(rel, "fecha_fin", "") or ""),
                        "actual": getattr(rel, "actual", True),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_empleos.find_by_source(uid):
            empresa = EmpresaService.get(edge["target_id"])
            if empresa:
                resultado.append({
                    "empresa": empresa,
                    "cargo": edge.get("cargo", "Colaborador"),
                    "fecha_inicio": edge.get("fecha_inicio"),
                    "fecha_fin": edge.get("fecha_fin"),
                    "actual": edge.get("actual", True),
                })
        return resultado

    @staticmethod
    def listar_por_empresa(eid):
        resultado = []
        if is_neo4j_available():
            try:
                emp = Empresa.nodes.get(eid=eid)
                for u in emp.empleados.all():
                    rel = emp.empleados.relationship(u)
                    resultado.append({
                        "usuario": u,
                        "cargo": getattr(rel, "cargo", "Colaborador"),
                        "fecha_inicio": str(getattr(rel, "fecha_inicio", "") or ""),
                        "fecha_fin": str(getattr(rel, "fecha_fin", "") or ""),
                        "actual": getattr(rel, "actual", True),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_empleos.find_by_target(eid):
            usuario = UsuarioService.get(edge["source_id"])
            if usuario:
                resultado.append({
                    "usuario": usuario,
                    "cargo": edge.get("cargo", "Colaborador"),
                    "fecha_inicio": edge.get("fecha_inicio"),
                    "fecha_fin": edge.get("fecha_fin"),
                    "actual": edge.get("actual", True),
                })
        return resultado


class HabilidadUsuarioService:
    @staticmethod
    def vincular(uid, hid, nivel="intermedio", anios_experiencia=0):
        u = UsuarioService.get(uid)
        h = HabilidadService.get(hid)
        if not u or not h:
            return None

        if is_neo4j_available():
            try:
                u.habilidades.connect(h, {
                    "nivel": nivel,
                    "anios_experiencia": int(anios_experiencia or 0),
                })
            except Exception:
                pass

        return _memory_habilidades_usuario.add(
            source_id=str(uid),
            target_id=str(hid),
            nivel=nivel,
            anios_experiencia=int(anios_experiencia or 0),
        )

    @staticmethod
    def desvincular(uid, hid):
        u = UsuarioService.get(uid)
        h = HabilidadService.get(hid)
        if is_neo4j_available() and u and h:
            try:
                u.habilidades.disconnect(h)
            except Exception:
                pass
        return _memory_habilidades_usuario.remove(uid, hid)

    @staticmethod
    def listar_por_usuario(uid):
        resultado = []
        if is_neo4j_available():
            try:
                u = Usuario.nodes.get(uid=uid)
                for h in u.habilidades.all():
                    rel = u.habilidades.relationship(h)
                    resultado.append({
                        "habilidad": h,
                        "nivel": getattr(rel, "nivel", "intermedio"),
                        "anios_experiencia": getattr(rel, "anios_experiencia", 0),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_habilidades_usuario.find_by_source(uid):
            hab = HabilidadService.get(edge["target_id"])
            if hab:
                resultado.append({
                    "habilidad": hab,
                    "nivel": edge.get("nivel", "intermedio"),
                    "anios_experiencia": edge.get("anios_experiencia", 0),
                })
        return resultado


class ParticipacionProyectoService:
    @staticmethod
    def vincular(uid, pid, rol="Colaborador", fecha_inicio=None, activo=True):
        u = UsuarioService.get(uid)
        p = ProyectoService.get(pid)
        if not u or not p:
            return None

        if is_neo4j_available():
            try:
                u.proyectos.connect(p, {
                    "rol": rol.strip(),
                    "fecha_inicio": fecha_inicio,
                    "activo": bool(activo),
                })
            except Exception:
                pass

        return _memory_participaciones.add(
            source_id=str(uid),
            target_id=str(pid),
            rol=rol.strip(),
            fecha_inicio=str(fecha_inicio) if fecha_inicio else None,
            activo=bool(activo),
        )

    @staticmethod
    def desvincular(uid, pid):
        u = UsuarioService.get(uid)
        p = ProyectoService.get(pid)
        if is_neo4j_available() and u and p:
            try:
                u.proyectos.disconnect(p)
            except Exception:
                pass
        return _memory_participaciones.remove(uid, pid)

    @staticmethod
    def listar_por_usuario(uid):
        resultado = []
        if is_neo4j_available():
            try:
                u = Usuario.nodes.get(uid=uid)
                for p in u.proyectos.all():
                    rel = u.proyectos.relationship(p)
                    resultado.append({
                        "proyecto": p,
                        "rol": getattr(rel, "rol", "Colaborador"),
                        "fecha_inicio": str(getattr(rel, "fecha_inicio", "") or ""),
                        "activo": getattr(rel, "activo", True),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_participaciones.find_by_source(uid):
            proy = ProyectoService.get(edge["target_id"])
            if proy:
                resultado.append({
                    "proyecto": proy,
                    "rol": edge.get("rol", "Colaborador"),
                    "fecha_inicio": edge.get("fecha_inicio"),
                    "activo": edge.get("activo", True),
                })
        return resultado

    @staticmethod
    def listar_por_proyecto(pid):
        resultado = []
        if is_neo4j_available():
            try:
                p = Proyecto.nodes.get(pid=pid)
                for u in p.miembros.all():
                    rel = p.miembros.relationship(u)
                    resultado.append({
                        "usuario": u,
                        "rol": getattr(rel, "rol", "Colaborador"),
                        "fecha_inicio": str(getattr(rel, "fecha_inicio", "") or ""),
                        "activo": getattr(rel, "activo", True),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_participaciones.find_by_target(pid):
            usuario = UsuarioService.get(edge["source_id"])
            if usuario:
                resultado.append({
                    "usuario": usuario,
                    "rol": edge.get("rol", "Colaborador"),
                    "fecha_inicio": edge.get("fecha_inicio"),
                    "activo": edge.get("activo", True),
                })
        return resultado


class PublicacionOfertaService:
    @staticmethod
    def vincular(eid, oid, fecha_publicacion=None):
        e = EmpresaService.get(eid)
        o = OfertaService.get(oid)
        if not e or not o:
            return None

        if is_neo4j_available():
            try:
                e.ofertas.connect(o, {"fecha_publicacion": fecha_publicacion or date.today()})
            except Exception:
                pass

        return _memory_publicaciones.add(
            source_id=str(eid),
            target_id=str(oid),
            fecha_publicacion=str(fecha_publicacion or date.today()),
        )

    @staticmethod
    def desvincular(eid, oid):
        e = EmpresaService.get(eid)
        o = OfertaService.get(oid)
        if is_neo4j_available() and e and o:
            try:
                e.ofertas.disconnect(o)
            except Exception:
                pass
        return _memory_publicaciones.remove(eid, oid)

    @staticmethod
    def obtener_empresa(oid):
        if is_neo4j_available():
            try:
                o = Oferta.nodes.get(oid=oid)
                empresas = o.empresa.all()
                if empresas:
                    return empresas[0]
            except Exception:
                pass

        edges = _memory_publicaciones.find_by_target(oid)
        if edges:
            return EmpresaService.get(edges[0]["source_id"])
        return None

    @staticmethod
    def listar_por_empresa(eid):
        resultado = []
        if is_neo4j_available():
            try:
                e = Empresa.nodes.get(eid=eid)
                return list(e.ofertas.all())
            except Exception:
                pass

        for edge in _memory_publicaciones.find_by_source(eid):
            oferta = OfertaService.get(edge["target_id"])
            if oferta:
                resultado.append(oferta)
        return resultado


class RequisitoOfertaService:
    @staticmethod
    def vincular(oid, hid, nivel_minimo="basico", prioridad="obligatoria"):
        o = OfertaService.get(oid)
        h = HabilidadService.get(hid)
        if not o or not h:
            return None

        if is_neo4j_available():
            try:
                o.habilidades.connect(h, {
                    "nivel_minimo": nivel_minimo,
                    "prioridad": prioridad,
                })
            except Exception:
                pass

        return _memory_requisitos.add(
            source_id=str(oid),
            target_id=str(hid),
            nivel_minimo=nivel_minimo,
            prioridad=prioridad,
        )

    @staticmethod
    def desvincular(oid, hid):
        o = OfertaService.get(oid)
        h = HabilidadService.get(hid)
        if is_neo4j_available() and o and h:
            try:
                o.habilidades.disconnect(h)
            except Exception:
                pass
        return _memory_requisitos.remove(oid, hid)

    @staticmethod
    def listar_por_oferta(oid):
        resultado = []
        if is_neo4j_available():
            try:
                o = Oferta.nodes.get(oid=oid)
                for h in o.habilidades.all():
                    rel = o.habilidades.relationship(h)
                    resultado.append({
                        "habilidad": h,
                        "nivel_minimo": getattr(rel, "nivel_minimo", "basico"),
                        "prioridad": getattr(rel, "prioridad", "obligatoria"),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_requisitos.find_by_source(oid):
            hab = HabilidadService.get(edge["target_id"])
            if hab:
                resultado.append({
                    "habilidad": hab,
                    "nivel_minimo": edge.get("nivel_minimo", "basico"),
                    "prioridad": edge.get("prioridad", "obligatoria"),
                })
        return resultado


class PostulacionService:
    @staticmethod
    def postular(uid, oid, carta_presentacion="", estado="enviada"):
        u = UsuarioService.get(uid)
        o = OfertaService.get(oid)
        if not u or not o:
            return None

        if is_neo4j_available():
            try:
                u.postulaciones.connect(o, {
                    "fecha": date.today(),
                    "estado": estado,
                    "carta_presentacion": carta_presentacion.strip(),
                })
            except Exception:
                pass

        return _memory_postulaciones.add(
            source_id=str(uid),
            target_id=str(oid),
            fecha=str(date.today()),
            estado=estado,
            carta_presentacion=carta_presentacion.strip(),
        )

    @staticmethod
    def desvincular(uid, oid):
        u = UsuarioService.get(uid)
        o = OfertaService.get(oid)
        if is_neo4j_available() and u and o:
            try:
                u.postulaciones.disconnect(o)
            except Exception:
                pass
        return _memory_postulaciones.remove(uid, oid)

    @staticmethod
    def ha_postulado(uid, oid):
        u = UsuarioService.get(uid)
        o = OfertaService.get(oid)
        if is_neo4j_available() and u and o:
            try:
                return u.postulaciones.is_connected(o)
            except Exception:
                pass
        return _memory_postulaciones.exists(uid, oid)

    @staticmethod
    def listar_por_usuario(uid):
        resultado = []
        if is_neo4j_available():
            try:
                u = Usuario.nodes.get(uid=uid)
                for o in u.postulaciones.all():
                    rel = u.postulaciones.relationship(o)
                    resultado.append({
                        "oferta": o,
                        "fecha": str(getattr(rel, "fecha", "") or ""),
                        "estado": getattr(rel, "estado", "enviada"),
                        "carta_presentacion": getattr(rel, "carta_presentacion", ""),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_postulaciones.find_by_source(uid):
            oferta = OfertaService.get(edge["target_id"])
            if oferta:
                resultado.append({
                    "oferta": oferta,
                    "fecha": edge.get("fecha", str(date.today())),
                    "estado": edge.get("estado", "enviada"),
                    "carta_presentacion": edge.get("carta_presentacion", ""),
                })
        return resultado

    @staticmethod
    def listar_por_oferta(oid):
        resultado = []
        if is_neo4j_available():
            try:
                o = Oferta.nodes.get(oid=oid)
                for u in o.candidatos.all():
                    rel = o.candidatos.relationship(u)
                    resultado.append({
                        "usuario": u,
                        "fecha": str(getattr(rel, "fecha", "") or ""),
                        "estado": getattr(rel, "estado", "enviada"),
                        "carta_presentacion": getattr(rel, "carta_presentacion", ""),
                    })
                if resultado:
                    return resultado
            except Exception:
                pass

        for edge in _memory_postulaciones.find_by_target(oid):
            usuario = UsuarioService.get(edge["source_id"])
            if usuario:
                resultado.append({
                    "usuario": usuario,
                    "fecha": edge.get("fecha", str(date.today())),
                    "estado": edge.get("estado", "enviada"),
                    "carta_presentacion": edge.get("carta_presentacion", ""),
                })
        return resultado

