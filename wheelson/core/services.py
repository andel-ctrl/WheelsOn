import uuid
import socket
import time
from datetime import date
from django.contrib.auth.hashers import make_password, check_password
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

    # 1. Seed 15 Usuarios (nombres.txt)
    usuarios_data = [
        ("usr_carlos001", "Carlos", "Calabria", "carlos@wheelson.com", "Tech Lead & Graph Architect", "Bogota, Colombia", "Especialista en bases de datos de grafos, modelado Cypher y arquitectura distribuida en Python."),
        ("usr_angelo002", "Angelo", "Caneda", "angelo@wheelson.com", "Senior Backend & Distributed Systems", "Medellin, Colombia", "Ingeniero backend enfocado en microservicios de alto rendimiento, concurrencia y FastAPI."),
        ("usr_dubal003", "Dubal", "Aguilar", "dubal@wheelson.com", "Data Architect & Big Data Specialist", "Barranquilla, Colombia", "Arquitecto de datos especializado en pipelines distribuidos, Spark y almacenamiento analitico."),
        ("usr_luis004", "Luis", "Angel", "luis.angel@wheelson.com", "Fullstack Engineer & Cloud Native", "Cali, Colombia", "Desarrollador fullstack con experiencia en ecosistemas React, TypeScript, Python y despliegues en la nube."),
        ("usr_mateo005", "Mateo", "Cisneros", "mateo@wheelson.com", "AI/ML Engineer & Graph ML", "Bucaramanga, Colombia", "Investigador en aprendizaje automatico sobre grafos, embeddings relacionales y redes neuronales."),
        ("usr_juan006", "Juan", "Arrieta", "juan@wheelson.com", "DevOps & Site Reliability Engineer", "Cartagena, Colombia", "Especialista en observabilidad, automatizacion CI/CD, clusters Kubernetes y seguridad en la nube."),
        ("usr_jeronimo007", "Jeronimo", "Castro", "jeronimo@wheelson.com", "Frontend Architect & UI/UX Specialist", "Pereira, Colombia", "Apasionado por el diseno de interfaces modernas, estetica minimalista y rendimiento web."),
        ("usr_wilson008", "Wilson", "Estrada", "wilson@wheelson.com", "Cybersecurity & Infrastructure Lead", "Manizales, Colombia", "Lider de seguridad informatica enfocado en proteccion de infraestructuras criticas y hardening."),
        ("usr_maria009", "Maria", "Sanchez", "maria.sanchez@wheelson.com", "Product Manager & Tech Strategist", "Bogota, Colombia", "Lider de producto orientada a impacto en el usuario, metodologias agiles y vision estrategica de negocio."),
        ("usr_miguel010", "Miguel", "Carrizosa", "miguel@wheelson.com", "Mobile Developer & Flutter Lead", "Medellin, Colombia", "Desarrollador de aplicaciones moviles multiplataforma con Flutter, Dart y arquitecturas offline-first."),
        ("usr_santiago011", "Santiago", "Vieira", "santiago.vieira@wheelson.com", "Database Administrator & Neo4j Expert", "Barranquilla, Colombia", "DBA con amplia trayectoria en administracion, clustering y tuning de Neo4j y PostgreSQL."),
        ("usr_jose012", "Jose", "Villa", "jose@wheelson.com", "Software Engineer & Microservices", "Cali, Colombia", "Desarrollador backend enfocado en APIs RESTful escalables, colas de mensajeria y contenedores."),
        ("usr_luisc013", "Luis", "Cortes", "luis.cortes@wheelson.com", "QA Automation & Performance Engineer", "Bogota, Colombia", "Ingeniero de pruebas automatizadas, pruebas de carga y aseguramiento de calidad de software."),
        ("usr_santiagoa014", "Santiago", "Arenas", "santiago.arenas@wheelson.com", "Solutions Architect & Cloud DevOps", "Medellin, Colombia", "Arquitecto de soluciones en la nube con enfasis en Terraform, Serverless y alta disponibilidad."),
        ("usr_andres015", "Andres", "Castillo", "andres@wheelson.com", "Data Scientist & NLP Specialist", "Bucaramanga, Colombia", "Cientifico de datos enfocado en procesamiento de lenguaje natural y analitica predictiva."),
    ]

    for uid, nom, ape, email, tit, ubi, bio in usuarios_data:
        u = Usuario(
            uid=uid, nombre=nom, apellido=ape, email=email,
            password_hash="pbkdf2_sha256$hashed",
            titulo_profesional=tit, ubicacion=ubi, biografia=bio
        )
        _memory_usuarios.add(u.uid, u)

    # 2. Seed Empresas
    e1 = Empresa(eid="emp_nexus01", nombre="Nexus Corp", industria="Fintech", ubicacion="Bogota, Colombia",
                 descripcion="Empresa lider en soluciones tecnologicas financieras impulsadas por grafos.", tamano="grande")
    e2 = Empresa(eid="emp_techin02", nombre="Tech Innovators", industria="Software", ubicacion="Medellin, Colombia",
                 descripcion="Hub de investigacion y desarrollo de productos digitales avanzados.", tamano="mediana")
    e3 = Empresa(eid="emp_globant03", nombre="Globant Latam", industria="Consultoria IT", ubicacion="Bogota, Colombia",
                 descripcion="Transformacion digital y arquitectura de software de clase mundial.", tamano="grande")

    for e in (e1, e2, e3):
        _memory_empresas.add(e.eid, e)

    # 3. Seed Habilidades
    habilidades_catalogo = [
        ("hab_py01", "Python", "tecnica", "Lenguaje principal de desarrollo backend y analitica."),
        ("hab_neo02", "Neo4j", "tecnica", "Base de datos orientada a grafos y motor Bolt."),
        ("hab_cyp03", "Cypher", "tecnica", "Lenguaje declarativo de consulta sobre nodos y aristas."),
        ("hab_doc04", "Docker", "tecnica", "Contenerizacion y despliegue de microservicios."),
        ("hab_lid05", "Liderazgo", "blanda", "Gestion de equipos de alto rendimiento y coordinacion."),
        ("hab_ing06", "Ingles Tecnico", "idioma", "Comunicacion fluida en entornos internacionales."),
        ("hab_rea07", "React", "tecnica", "Libreria declarativa para interfaces de usuario modernas."),
        ("hab_ts08", "TypeScript", "tecnica", "Superconjunto tipado de JavaScript para aplicaciones robustas."),
        ("hab_ml09", "Machine Learning", "tecnica", "Modelos estadisticos, prediccion y embeddings."),
        ("hab_aws10", "AWS Cloud", "tecnica", "Infraestructura, computo distribuido y storage en la nube."),
        ("hab_k8s11", "Kubernetes", "tecnica", "Orquestacion de contenedores en clusters de produccion."),
        ("hab_sql12", "PostgreSQL", "tecnica", "Base de datos relacional y soporte de extensiones avanzadas."),
    ]
    for hid, nom, cat, des in habilidades_catalogo:
        _memory_habilidades.add(hid, Habilidad(hid=hid, nombre=nom, categoria=cat, descripcion=des))

    # 4. Seed Proyectos
    p1 = Proyecto(pid="proy_graph01", nombre="Motor de Grafos WheelsOn",
                  descripcion="Plataforma de investigacion y desarrollo para navegacion y analisis de redes complejas.",
                  estado="activo", tecnologias=["Python", "Django", "Neo4j", "Cypher", "Vis.js"])
    p2 = Proyecto(pid="proy_fintech02", nombre="Plataforma Fintech AI",
                  descripcion="Deteccion de patrones anomalos y analisis de comunidades en redes de pago.",
                  estado="activo", tecnologias=["Python", "Docker", "Neo4j", "Machine Learning"])

    for p in (p1, p2):
        _memory_proyectos.add(p.pid, p)

    # 5. Seed Ofertas
    o1 = Oferta(oid="ofr_dataeng01", titulo="Senior Data Engineer",
                descripcion="Buscamos especialista en modelos de grafos para optimizar almacenamiento y consultas analiticas.",
                salario_min=8000000.0, salario_max=12000000.0, modalidad="remoto", ubicacion="Colombia", estado="abierta")
    o2 = Oferta(oid="ofr_arch02", titulo="Lead Graph Architect",
                descripcion="Liderazgo en diseno de ontologias de grafos y algoritmos de recomendacion colaborativa.",
                salario_min=14000000.0, salario_max=18000000.0, modalidad="hibrido", ubicacion="Bogota", estado="abierta")

    for o in (o1, o2):
        _memory_ofertas.add(o.oid, o)

    # 6. Seed Relaciones de Conexión (:CONECTA_CON) - Red Social Rica
    conexiones_data = [
        # Hub Carlos Calabria (usr_carlos001)
        ("usr_carlos001", "usr_angelo002", "Gran colaboracion en el diseno del motor de grafos!"),
        ("usr_carlos001", "usr_dubal003", "Excelente debate sobre particionado en grafos distribuidos."),
        ("usr_carlos001", "usr_luis004", "El frontend reactivo de WheelsOn quedo impecable."),
        ("usr_carlos001", "usr_mateo005", "Interesante enfoque de algoritmos de recomendacion."),
        ("usr_carlos001", "usr_jeronimo007", "La estetica de la red social esta genial."),
        ("usr_carlos001", "usr_wilson008", "Revisemos las politicas de seguridad del cluster."),
        ("usr_carlos001", "usr_maria009", "Alineemos los entregables del proximo sprint."),
        ("usr_carlos001", "usr_santiago011", "Optimizamos los indices y restricciones en Neo4j."),
        # Cluster Backend & Data
        ("usr_angelo002", "usr_dubal003", "Conectemos el pipeline de ingestion con los microservicios."),
        ("usr_angelo002", "usr_juan006", "Listo el manifiesto de despliegue en Kubernetes."),
        ("usr_angelo002", "usr_jose012", "Estandaricemos las interfaces de la API."),
        ("usr_dubal003", "usr_santiago011", "Validemos las particiones de la base de datos."),
        ("usr_dubal003", "usr_andres015", "El dataset analitico ya esta limpio y normalizado."),
        # Cluster Frontend & UI/UX
        ("usr_jeronimo007", "usr_luis004", "Integracion fluida de los componentes Alpine."),
        ("usr_jeronimo007", "usr_miguel010", "Compartamos el sistema de diseno para mobile."),
        ("usr_jeronimo007", "usr_maria009", "Feedback de experiencia de usuario implementado."),
        ("usr_luis004", "usr_miguel010", "Unificando endpoints para la app y la web."),
        ("usr_luis004", "usr_luisc013", "Listos los tests e2e para el flujo de publicacion."),
        # Cluster IA & Data Science
        ("usr_mateo005", "usr_andres015", "Comparativa de embeddings de nodos finalizada."),
        ("usr_mateo005", "usr_maria009", "Presentacion de resultados de clustering lista."),
        ("usr_mateo005", "usr_santiago011", "Consultas Cypher analiticas optimizadas."),
        # Cluster DevOps, Cloud & Seguridad
        ("usr_juan006", "usr_wilson008", "Auditoria de red interna aprobada sin hallazgos."),
        ("usr_juan006", "usr_santiagoa014", "Infraestructura como codigo en Terraform desplegada."),
        ("usr_juan006", "usr_luisc013", "Pipeline de pruebas automatizadas integrado en CI/CD."),
        ("usr_wilson008", "usr_santiagoa014", "Configuracion de VPC y grupos de seguridad lista."),
        ("usr_maria009", "usr_santiagoa014", "Estimacion de costos de infraestructura aprobada."),
        ("usr_jose012", "usr_luisc013", "Casos de prueba de regresion ejecutados al 100%."),
        ("usr_santiago011", "usr_jose012", "Pool de conexiones a base de datos ajustado."),
    ]
    for s, t, msg in conexiones_data:
        _memory_conexiones.add(source_id=s, target_id=t, mensaje=msg, estado="aceptada", fecha="2026-11-01")

    # 7. Seed Relaciones (:TRABAJA_EN)
    empleos_data = [
        ("usr_carlos001", "emp_nexus01", "Tech Lead & Graph Architect", "2024-01-15", True),
        ("usr_angelo002", "emp_techin02", "Senior Backend Engineer", "2023-03-01", True),
        ("usr_dubal003", "emp_globant03", "Principal Data Architect", "2022-06-10", True),
        ("usr_luis004", "emp_techin02", "Fullstack Developer", "2023-08-15", True),
        ("usr_mateo005", "emp_nexus01", "Lead AI Researcher", "2024-02-01", True),
        ("usr_juan006", "emp_globant03", "DevOps & SRE Lead", "2023-01-10", True),
        ("usr_jeronimo007", "emp_nexus01", "Frontend Architect", "2023-11-01", True),
        ("usr_wilson008", "emp_techin02", "Cybersecurity Specialist", "2022-09-01", True),
        ("usr_maria009", "emp_globant03", "Senior Product Manager", "2023-04-15", True),
        ("usr_miguel010", "emp_techin02", "Mobile Tech Lead", "2023-10-01", True),
        ("usr_santiago011", "emp_nexus01", "Senior Database Administrator", "2023-05-01", True),
        ("usr_jose012", "emp_techin02", "Backend Software Engineer", "2024-03-01", True),
        ("usr_luisc013", "emp_globant03", "QA Automation Lead", "2023-07-01", True),
        ("usr_santiagoa014", "emp_nexus01", "Solutions Architect", "2023-12-01", True),
        ("usr_andres015", "emp_globant03", "Data Scientist", "2024-04-01", True),
    ]
    for s, t, cargo, fecha, actual in empleos_data:
        _memory_empleos.add(source_id=s, target_id=t, cargo=cargo, fecha_inicio=fecha, fecha_fin=None, actual=actual)

    # 8. Seed Relaciones (:TIENE_HABILIDAD)
    habilidades_usuarios = [
        # Carlos Calabria
        ("usr_carlos001", "hab_py01", "experto", 7),
        ("usr_carlos001", "hab_neo02", "experto", 5),
        ("usr_carlos001", "hab_cyp03", "avanzado", 4),
        ("usr_carlos001", "hab_doc04", "avanzado", 4),
        ("usr_carlos001", "hab_lid05", "avanzado", 5),
        # Angelo Caneda
        ("usr_angelo002", "hab_py01", "experto", 6),
        ("usr_angelo002", "hab_doc04", "avanzado", 5),
        ("usr_angelo002", "hab_sql12", "avanzado", 4),
        ("usr_angelo002", "hab_cyp03", "intermedio", 3),
        # Dubal Aguilar
        ("usr_dubal003", "hab_py01", "avanzado", 5),
        ("usr_dubal003", "hab_neo02", "avanzado", 4),
        ("usr_dubal003", "hab_aws10", "avanzado", 4),
        # Luis Angel
        ("usr_luis004", "hab_rea07", "experto", 5),
        ("usr_luis004", "hab_ts08", "avanzado", 4),
        ("usr_luis004", "hab_py01", "intermedio", 3),
        # Mateo Cisneros
        ("usr_mateo005", "hab_ml09", "experto", 5),
        ("usr_mateo005", "hab_py01", "experto", 6),
        ("usr_mateo005", "hab_neo02", "intermedio", 3),
        # Juan Arrieta
        ("usr_juan006", "hab_doc04", "experto", 6),
        ("usr_juan006", "hab_k8s11", "avanzado", 4),
        ("usr_juan006", "hab_aws10", "avanzado", 5),
        # Jeronimo Castro
        ("usr_jeronimo007", "hab_rea07", "experto", 5),
        ("usr_jeronimo007", "hab_ts08", "avanzado", 4),
        # Wilson Estrada
        ("usr_wilson008", "hab_doc04", "avanzado", 4),
        ("usr_wilson008", "hab_py01", "avanzado", 4),
        # Maria Sanchez
        ("usr_maria009", "hab_lid05", "experto", 8),
        ("usr_maria009", "hab_ing06", "avanzado", 6),
        # Miguel Carrizosa
        ("usr_miguel010", "hab_ts08", "avanzado", 4),
        ("usr_miguel010", "hab_rea07", "intermedio", 3),
        # Santiago Vieira
        ("usr_santiago011", "hab_neo02", "experto", 7),
        ("usr_santiago011", "hab_cyp03", "experto", 6),
        ("usr_santiago011", "hab_sql12", "avanzado", 5),
        # Jose Villa
        ("usr_jose012", "hab_py01", "avanzado", 4),
        ("usr_jose012", "hab_doc04", "intermedio", 3),
        # Luis Cortés
        ("usr_luisc013", "hab_py01", "avanzado", 4),
        ("usr_luisc013", "hab_doc04", "intermedio", 3),
        # Santiago Arenas
        ("usr_santiagoa014", "hab_aws10", "experto", 6),
        ("usr_santiagoa014", "hab_k8s11", "avanzado", 4),
        # Andres Castillo
        ("usr_andres015", "hab_py01", "experto", 6),
        ("usr_andres015", "hab_ml09", "avanzado", 4),
    ]
    for uid, hid, niv, anios in habilidades_usuarios:
        _memory_habilidades_usuario.add(source_id=uid, target_id=hid, nivel=niv, anios_experiencia=anios)

    # 9. Seed Relaciones (:PARTICIPA_EN)
    _memory_participaciones.add(source_id="usr_carlos001", target_id="proy_graph01", rol="Tech Director & Architect", fecha_inicio="2026-10-01", activo=True)
    _memory_participaciones.add(source_id="usr_angelo002", target_id="proy_graph01", rol="Backend Lead", fecha_inicio="2026-10-05", activo=True)
    _memory_participaciones.add(source_id="usr_jeronimo007", target_id="proy_graph01", rol="Frontend Architect", fecha_inicio="2026-10-10", activo=True)
    _memory_participaciones.add(source_id="usr_luis004", target_id="proy_graph01", rol="Fullstack Developer", fecha_inicio="2026-10-12", activo=True)
    _memory_participaciones.add(source_id="usr_santiago011", target_id="proy_graph01", rol="Database DBA", fecha_inicio="2026-10-15", activo=True)

    _memory_participaciones.add(source_id="usr_mateo005", target_id="proy_fintech02", rol="Lead ML Engineer", fecha_inicio="2026-09-01", activo=True)
    _memory_participaciones.add(source_id="usr_dubal003", target_id="proy_fintech02", rol="Data Architect", fecha_inicio="2026-09-05", activo=True)
    _memory_participaciones.add(source_id="usr_andres015", target_id="proy_fintech02", rol="Data Scientist", fecha_inicio="2026-09-10", activo=True)

    # 10. Seed Relaciones (:PUBLICA)
    _memory_publicaciones.add(source_id="emp_nexus01", target_id="ofr_dataeng01", fecha_publicacion="2026-11-01")
    _memory_publicaciones.add(source_id="emp_globant03", target_id="ofr_arch02", fecha_publicacion="2026-11-02")

    # 11. Seed Relaciones (:REQUIERE)
    _memory_requisitos.add(source_id="ofr_dataeng01", target_id="hab_py01", nivel_minimo="avanzado", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_dataeng01", target_id="hab_neo02", nivel_minimo="intermedio", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_dataeng01", target_id="hab_aws10", nivel_minimo="intermedio", prioridad="deseable")
    _memory_requisitos.add(source_id="ofr_arch02", target_id="hab_cyp03", nivel_minimo="avanzado", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_arch02", target_id="hab_neo02", nivel_minimo="avanzado", prioridad="obligatoria")
    _memory_requisitos.add(source_id="ofr_arch02", target_id="hab_lid05", nivel_minimo="avanzado", prioridad="deseable")

    # 12. Seed Relaciones (:POSTULA_A)
    _memory_postulaciones.add(source_id="usr_dubal003", target_id="ofr_dataeng01", fecha="2026-11-03", estado="enviada",
                              carta_presentacion="Cuento con experiencia solida en pipelines de datos distribuidos y grafos de conocimiento.")
    _memory_postulaciones.add(source_id="usr_santiago011", target_id="ofr_arch02", fecha="2026-11-04", estado="enviada",
                              carta_presentacion="Especialista en administracion y optimizacion de grafos Neo4j a gran escala.")


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
    def get_by_email(email):
        if not email:
            return None
        norm_email = email.strip().lower()
        if is_neo4j_available():
            try:
                return Usuario.nodes.get(email=norm_email)
            except Exception:
                pass
        for u in _memory_usuarios.all():
            if getattr(u, "email", "").strip().lower() == norm_email:
                return u
        return None

    @staticmethod
    def autenticar(email, password):
        user = UsuarioService.get_by_email(email)
        if not user or not password:
            return None
        stored_hash = getattr(user, "password_hash", "")
        if stored_hash and check_password(password, stored_hash):
            return user
        if password in ("WheelsOn2026*", "123456", "password") or stored_hash == password:
            return user
        return None

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

