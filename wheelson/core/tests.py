from datetime import date
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from neo4j.exceptions import AuthError, ServiceUnavailable
from neomodel import UniqueProperty, db

from core.test_utils import Neo4jTestCase as TestCase, ejecutar_script_cypher
from core.models import (
    Usuario,
    Empresa,
    Habilidad,
    Proyecto,
    Oferta,
    ConectaConRel,
    TrabajaEnRel,
    TieneHabilidadRel,
    ParticipaEnRel,
    PublicaRel,
    RequiereRel,
    PostulaARel,
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
from core.graph_queries import GraphAnalyticsService
from core.recommendations import RecommendationEngine
from core.analytics import NetworkAnalyticsService
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
    CaminoCortoForm,
    ContactosComunForm,
    HabilidadesSimilaresForm,
    RutaEmpresaForm,
    CandidatosOfertaForm,
)


class WheelsOnSetupTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WheelsOn")


class GraphModelsDefinitionTest(TestCase):
    def test_usuario_model_definition(self):
        u = Usuario(
            nombre="Carlos",
            apellido="Santana",
            email="carlos@example.com",
            password_hash="pbkdf2_sha256$hashed",
            titulo_profesional="Backend Developer",
            ubicacion="Bogota",
        )
        self.assertEqual(u.nombre_completo, "Carlos Santana")
        data = u.to_dict()
        self.assertEqual(data["email"], "carlos@example.com")
        self.assertIn("conexiones", Usuario.__dict__)

    def test_empresa_model_definition(self):
        e = Empresa(
            nombre="Tech Innovators",
            industria="Software",
            ubicacion="Medellin",
            tamano="mediana",
        )
        data = e.to_dict()
        self.assertEqual(data["nombre"], "Tech Innovators")

    def test_habilidad_model_definition(self):
        h = Habilidad(nombre="Neo4j Cypher", categoria="tecnica")
        data = h.to_dict()
        self.assertEqual(data["nombre"], "Neo4j Cypher")

    def test_proyecto_model_definition(self):
        p = Proyecto(nombre="Sistema Recom", tecnologias=["Python", "Neo4j"])
        data = p.to_dict()
        self.assertEqual(data["nombre"], "Sistema Recom")

    def test_oferta_model_definition(self):
        o = Oferta(titulo="Ingeniero de Grafos", salario_min=4000000.0)
        data = o.to_dict()
        self.assertEqual(data["titulo"], "Ingeniero de Grafos")

    def test_relationships_classes(self):
        self.assertTrue(issubclass(ConectaConRel, object))
        self.assertTrue(issubclass(TrabajaEnRel, object))
        self.assertTrue(issubclass(TieneHabilidadRel, object))
        self.assertTrue(issubclass(ParticipaEnRel, object))
        self.assertTrue(issubclass(PublicaRel, object))
        self.assertTrue(issubclass(RequiereRel, object))
        self.assertTrue(issubclass(PostulaARel, object))


class ServicesCrudTest(TestCase):
    def test_usuario_service_crud(self):
        user = UsuarioService.create(
            nombre="Ana",
            apellido="Gomez",
            email="ana@example.com",
            titulo_profesional="Data Scientist",
            ubicacion="Cali",
        )
        self.assertIsNotNone(user.uid)
        self.assertEqual(user.nombre, "Ana")

        fetched = UsuarioService.get(user.uid)
        self.assertEqual(fetched.email, "ana@example.com")

        updated = UsuarioService.update(user.uid, titulo_profesional="Senior Data Scientist")
        self.assertEqual(updated.titulo_profesional, "Senior Data Scientist")

        deleted = UsuarioService.delete(user.uid)
        self.assertTrue(deleted)

    def test_empresa_service_crud(self):
        emp = EmpresaService.create(
            nombre="Global Logistics",
            industria="Logistica",
            ubicacion="Barranquilla",
            tamano="grande",
        )
        self.assertIsNotNone(emp.eid)
        self.assertEqual(emp.nombre, "Global Logistics")

        fetched = EmpresaService.get(emp.eid)
        self.assertEqual(fetched.tamano, "grande")

        updated = EmpresaService.update(emp.eid, ubicacion="Cartagena")
        self.assertEqual(updated.ubicacion, "Cartagena")

        deleted = EmpresaService.delete(emp.eid)
        self.assertTrue(deleted)

    def test_habilidad_service_crud(self):
        hab = HabilidadService.create(
            nombre="Machine Learning",
            categoria="tecnica",
            descripcion="Modelos predictivos",
        )
        self.assertIsNotNone(hab.hid)
        self.assertEqual(hab.nombre, "Machine Learning")

        fetched = HabilidadService.get(hab.hid)
        self.assertEqual(fetched.categoria, "tecnica")

        deleted = HabilidadService.delete(hab.hid)
        self.assertTrue(deleted)

    def test_proyecto_service_crud(self):
        proy = ProyectoService.create(
            nombre="Plataforma E-Commerce",
            descripcion="Tienda virtual escalable",
            estado="activo",
            tecnologias="Django, Vue, Postgres",
        )
        self.assertIsNotNone(proy.pid)
        self.assertEqual(len(proy.tecnologias), 3)

        updated = ProyectoService.update(proy.pid, estado="completado")
        self.assertEqual(updated.estado, "completado")

        deleted = ProyectoService.delete(proy.pid)
        self.assertTrue(deleted)

    def test_oferta_service_crud(self):
        ofr = OfertaService.create(
            titulo="Desarrollador Django",
            descripcion="Backend con grafos",
            salario_min=5000000,
            salario_max=7000000,
            modalidad="remoto",
        )
        self.assertIsNotNone(ofr.oid)
        self.assertEqual(ofr.titulo, "Desarrollador Django")

        updated = OfertaService.update(ofr.oid, estado="cerrada")
        self.assertEqual(updated.estado, "cerrada")

        deleted = OfertaService.delete(ofr.oid)
        self.assertTrue(deleted)


class FormsValidationTest(TestCase):
    def test_usuario_form_valid(self):
        form = UsuarioForm(data={
            "nombre": "Pedro",
            "apellido": "Perez",
            "email": "pedro@example.com",
            "titulo_profesional": "Frontend Dev",
            "ubicacion": "Bogota",
        })
        self.assertTrue(form.is_valid())

    def test_empresa_form_valid(self):
        form = EmpresaForm(data={
            "nombre": "CloudTech",
            "industria": "Cloud Computing",
            "ubicacion": "Medellin",
            "tamano": "mediana",
        })
        self.assertTrue(form.is_valid())

    def test_habilidad_form_valid(self):
        form = HabilidadForm(data={
            "nombre": "Docker",
            "categoria": "tecnica",
        })
        self.assertTrue(form.is_valid())

    def test_proyecto_form_valid(self):
        form = ProyectoForm(data={
            "nombre": "App Movil",
            "estado": "activo",
            "tecnologias": "Flutter, Firebase",
        })
        self.assertTrue(form.is_valid())

    def test_oferta_form_valid(self):
        form = OfertaForm(data={
            "titulo": "Tech Lead",
            "modalidad": "hibrido",
            "salario_min": 8000000,
            "salario_max": 12000000,
            "estado": "abierta",
        })
        self.assertTrue(form.is_valid())


class ViewsEndpointsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_usuarios_views_flow(self):
        # 1. Crear
        post_res = self.client.post(reverse("core:usuario_crear"), {
            "nombre": "Laura",
            "apellido": "Rios",
            "email": "laura@example.com",
            "titulo_profesional": "UX Designer",
            "ubicacion": "Pereira",
        })
        self.assertEqual(post_res.status_code, 302)

        # 2. Listar
        list_res = self.client.get(reverse("core:usuarios_lista"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Laura")

    def test_empresas_views_flow(self):
        post_res = self.client.post(reverse("core:empresa_crear"), {
            "nombre": "Nexus Corp",
            "industria": "Fintech",
            "ubicacion": "Bogota",
            "tamano": "grande",
        })
        self.assertEqual(post_res.status_code, 302)

        list_res = self.client.get(reverse("core:empresas_lista"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Nexus Corp")

    def test_habilidades_views_flow(self):
        post_res = self.client.post(reverse("core:habilidad_crear"), {
            "nombre": "GraphQL",
            "categoria": "tecnica",
        })
        self.assertEqual(post_res.status_code, 302)

        list_res = self.client.get(reverse("core:habilidades_lista"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "GraphQL")

    def test_proyectos_views_flow(self):
        post_res = self.client.post(reverse("core:proyecto_crear"), {
            "nombre": "Chatbot AI",
            "estado": "activo",
            "tecnologias": "Python, OpenAI",
        })
        self.assertEqual(post_res.status_code, 302)

        list_res = self.client.get(reverse("core:proyectos_lista"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Chatbot AI")

    def test_ofertas_views_flow(self):
        post_res = self.client.post(reverse("core:oferta_crear"), {
            "titulo": "Data Engineer",
            "modalidad": "remoto",
            "salario_min": 6000000,
            "salario_max": 9000000,
            "estado": "abierta",
        })
        self.assertEqual(post_res.status_code, 302)

        list_res = self.client.get(reverse("core:ofertas_lista"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Data Engineer")


class TemplateUiEnhancementsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_base_layout_and_theme(self):
        res = self.client.get(reverse("core:dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "themeManager()")
        self.assertContains(res, "data-theme")
        self.assertContains(res, "htmx-indicator")

    def test_usuario_detalle_template(self):
        u = UsuarioService.create(
            nombre="Laura",
            apellido="Gomez",
            email="laura@example.com",
            titulo_profesional="Tech Lead",
            ubicacion="Medellin",
        )
        res = self.client.get(reverse("core:usuario_detalle", kwargs={"uid": u.uid}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Tech Lead")
        self.assertContains(res, "activeTab")

    def test_empresa_detalle_template(self):
        e = EmpresaService.create(
            nombre="Globant Latam",
            industria="Software",
            ubicacion="Bogota",
            tamano="grande",
        )
        res = self.client.get(reverse("core:empresa_detalle", kwargs={"eid": e.eid}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Globant Latam")
        self.assertContains(res, "Ofertas Publicadas")

    def test_oferta_detalle_template(self):
        o = OfertaService.create(
            titulo="Fullstack Python Architect",
            modalidad="remoto",
            salario_min=12000000,
            salario_max=16000000,
            estado="abierta",
        )
        res = self.client.get(reverse("core:oferta_detalle", kwargs={"oid": o.oid}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Fullstack Python Architect")
        self.assertContains(res, "Postularme Ahora")

    def test_proyecto_detalle_template(self):
        p = ProyectoService.create(
            nombre="AI Graph Engine",
            estado="activo",
            tecnologias="Python, Neo4j, Cypher",
        )
        res = self.client.get(reverse("core:proyecto_detalle", kwargs={"pid": p.pid}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "AI Graph Engine")
        self.assertContains(res, "Stack Tecnológico")

    def test_habilidades_cloud_template(self):
        HabilidadService.create(nombre="Kubernetes", categoria="tecnica")
        res = self.client.get(reverse("core:habilidades_lista"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Skills Cloud")
        self.assertContains(res, "Kubernetes")


class RelationshipsManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = UsuarioService.create(nombre="Ana", apellido="Perez", email="ana@example.com")
        self.u2 = UsuarioService.create(nombre="Beto", apellido="Lopez", email="beto@example.com")
        self.emp = EmpresaService.create(nombre="DevCorp", industria="IT", tamano="grande")
        self.hab = HabilidadService.create(nombre="Docker", categoria="tecnica")
        self.proy = ProyectoService.create(nombre="Microservices Migration", estado="activo")
        self.ofr = OfertaService.create(titulo="DevOps Specialist", modalidad="remoto")

    def test_conexion_service_lifecycle(self):
        self.assertFalse(ConexionService.estan_conectados(self.u1.uid, self.u2.uid))
        ConexionService.conectar(self.u1.uid, self.u2.uid, mensaje="Hola Beto!")
        self.assertTrue(ConexionService.estan_conectados(self.u1.uid, self.u2.uid))
        conexiones = ConexionService.listar(self.u1.uid)
        self.assertEqual(len(conexiones), 1)
        self.assertEqual(conexiones[0]["usuario"].uid, self.u2.uid)
        self.assertEqual(conexiones[0]["mensaje"], "Hola Beto!")

        ConexionService.desconectar(self.u1.uid, self.u2.uid)
        self.assertFalse(ConexionService.estan_conectados(self.u1.uid, self.u2.uid))

    def test_empleo_service_lifecycle(self):
        EmpleoService.vincular(self.u1.uid, self.emp.eid, cargo="Backend Dev", actual=True)
        empleos = EmpleoService.listar_por_usuario(self.u1.uid)
        self.assertEqual(len(empleos), 1)
        self.assertEqual(empleos[0]["cargo"], "Backend Dev")
        self.assertEqual(empleos[0]["empresa"].eid, self.emp.eid)

        empleados = EmpleoService.listar_por_empresa(self.emp.eid)
        self.assertEqual(len(empleados), 1)
        self.assertEqual(empleados[0]["usuario"].uid, self.u1.uid)

        EmpleoService.desvincular(self.u1.uid, self.emp.eid)
        self.assertEqual(len(EmpleoService.listar_por_usuario(self.u1.uid)), 0)

    def test_habilidad_usuario_service_lifecycle(self):
        HabilidadUsuarioService.vincular(self.u1.uid, self.hab.hid, nivel="avanzado", anios_experiencia=3)
        habilidades = HabilidadUsuarioService.listar_por_usuario(self.u1.uid)
        self.assertEqual(len(habilidades), 1)
        self.assertEqual(habilidades[0]["habilidad"].hid, self.hab.hid)
        self.assertEqual(habilidades[0]["nivel"], "avanzado")
        self.assertEqual(habilidades[0]["anios_experiencia"], 3)

        HabilidadUsuarioService.desvincular(self.u1.uid, self.hab.hid)
        self.assertEqual(len(HabilidadUsuarioService.listar_por_usuario(self.u1.uid)), 0)

    def test_participacion_proyecto_service_lifecycle(self):
        ParticipacionProyectoService.vincular(self.u1.uid, self.proy.pid, rol="Tech Lead")
        proyectos = ParticipacionProyectoService.listar_por_usuario(self.u1.uid)
        self.assertEqual(len(proyectos), 1)
        self.assertEqual(proyectos[0]["rol"], "Tech Lead")

        miembros = ParticipacionProyectoService.listar_por_proyecto(self.proy.pid)
        self.assertEqual(len(miembros), 1)
        self.assertEqual(miembros[0]["usuario"].uid, self.u1.uid)

        ParticipacionProyectoService.desvincular(self.u1.uid, self.proy.pid)
        self.assertEqual(len(ParticipacionProyectoService.listar_por_proyecto(self.proy.pid)), 0)

    def test_publicacion_oferta_service_lifecycle(self):
        PublicacionOfertaService.vincular(self.emp.eid, self.ofr.oid)
        empresa = PublicacionOfertaService.obtener_empresa(self.ofr.oid)
        self.assertIsNotNone(empresa)
        self.assertEqual(empresa.eid, self.emp.eid)

        ofertas = PublicacionOfertaService.listar_por_empresa(self.emp.eid)
        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0].oid, self.ofr.oid)

    def test_requisito_oferta_service_lifecycle(self):
        RequisitoOfertaService.vincular(self.ofr.oid, self.hab.hid, nivel_minimo="intermedio", prioridad="obligatoria")
        requisitos = RequisitoOfertaService.listar_por_oferta(self.ofr.oid)
        self.assertEqual(len(requisitos), 1)
        self.assertEqual(requisitos[0]["habilidad"].hid, self.hab.hid)
        self.assertEqual(requisitos[0]["prioridad"], "obligatoria")

        RequisitoOfertaService.desvincular(self.ofr.oid, self.hab.hid)
        self.assertEqual(len(RequisitoOfertaService.listar_por_oferta(self.ofr.oid)), 0)

    def test_postulacion_service_lifecycle(self):
        self.assertFalse(PostulacionService.ha_postulado(self.u1.uid, self.ofr.oid))
        PostulacionService.postular(self.u1.uid, self.ofr.oid, carta_presentacion="Mi postulacion")
        self.assertTrue(PostulacionService.ha_postulado(self.u1.uid, self.ofr.oid))

        candidatos = PostulacionService.listar_por_oferta(self.ofr.oid)
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["usuario"].uid, self.u1.uid)

        PostulacionService.desvincular(self.u1.uid, self.ofr.oid)
        self.assertFalse(PostulacionService.ha_postulado(self.u1.uid, self.ofr.oid))

    def test_relaciones_views_and_flow(self):
        res_conectar = self.client.post(reverse("core:conexion_conectar"), {
            "uid_origen": self.u1.uid,
            "uid_destino": self.u2.uid,
            "mensaje": "Conectemos por favor",
        })
        self.assertEqual(res_conectar.status_code, 302)
        self.assertTrue(ConexionService.estan_conectados(self.u1.uid, self.u2.uid))

        res_hab = self.client.post(reverse("core:usuario_habilidad_agregar", kwargs={"uid": self.u1.uid}), {
            "hid": self.hab.hid,
            "nivel": "experto",
            "anios_experiencia": 5,
        })
        self.assertEqual(res_hab.status_code, 302)
        self.assertEqual(len(HabilidadUsuarioService.listar_por_usuario(self.u1.uid)), 1)

        res_emp = self.client.post(reverse("core:usuario_experiencia_agregar", kwargs={"uid": self.u1.uid}), {
            "eid": self.emp.eid,
            "cargo": "Tech Director",
            "actual": "on",
        })
        self.assertEqual(res_emp.status_code, 302)
        self.assertEqual(len(EmpleoService.listar_por_usuario(self.u1.uid)), 1)

        res_postular = self.client.post(reverse("core:oferta_postular", kwargs={"oid": self.ofr.oid}), {
            "uid": self.u1.uid,
            "carta_presentacion": "Carta motivacional",
        })
        self.assertEqual(res_postular.status_code, 302)
        self.assertTrue(PostulacionService.ha_postulado(self.u1.uid, self.ofr.oid))

        res_red = self.client.get(reverse("core:conexiones_red") + f"?uid={self.u1.uid}")
        self.assertEqual(res_red.status_code, 200)
        self.assertContains(res_red, "Red de Conexiones")
        self.assertContains(res_red, self.u2.nombre)


class AdvancedGraphQueriesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = UsuarioService.create(nombre="Carlos", apellido="Mendoza", email="carlos@test.com", titulo_profesional="Backend Lead")
        self.u2 = UsuarioService.create(nombre="Diana", apellido="Rios", email="diana@test.com", titulo_profesional="Fullstack Dev")
        self.u3 = UsuarioService.create(nombre="Esteban", apellido="Gomez", email="esteban@test.com", titulo_profesional="Cloud Architect")
        self.emp = EmpresaService.create(nombre="CloudSys", industria="Cloud", tamano="mediana")
        self.h1 = HabilidadService.create(nombre="FastAPI", categoria="tecnica")
        self.h2 = HabilidadService.create(nombre="Neo4j", categoria="tecnica")
        self.ofr = OfertaService.create(titulo="Python Architect", modalidad="remoto", estado="abierta")

    def test_shortest_path_analytics(self):
        res_disconn = GraphAnalyticsService.shortest_path_usuarios(self.u1.uid, self.u3.uid)
        self.assertFalse(res_disconn["encontrado"])

        ConexionService.conectar(self.u1.uid, self.u2.uid)
        ConexionService.conectar(self.u2.uid, self.u3.uid)

        res_conn = GraphAnalyticsService.shortest_path_usuarios(self.u1.uid, self.u3.uid)
        self.assertTrue(res_conn["encontrado"])
        self.assertEqual(res_conn["grados"], 2)
        self.assertEqual(len(res_conn["camino"]), 3)

    def test_contactos_en_comun_analytics(self):
        ConexionService.conectar(self.u1.uid, self.u2.uid)
        ConexionService.conectar(self.u3.uid, self.u2.uid)

        comunes = GraphAnalyticsService.contactos_en_comun(self.u1.uid, self.u3.uid)
        self.assertEqual(len(comunes), 1)
        self.assertEqual(comunes[0].uid, self.u2.uid)

    def test_usuarios_con_habilidades_similares_analytics(self):
        HabilidadUsuarioService.vincular(self.u1.uid, self.h1.hid, nivel="avanzado")
        HabilidadUsuarioService.vincular(self.u2.uid, self.h1.hid, nivel="intermedio")
        HabilidadUsuarioService.vincular(self.u1.uid, self.h2.hid, nivel="experto")

        similares = GraphAnalyticsService.usuarios_con_habilidades_similares(self.u1.uid)
        self.assertEqual(len(similares), 1)
        self.assertEqual(similares[0]["usuario"].uid, self.u2.uid)
        self.assertEqual(similares[0]["total_compartidas"], 1)
        self.assertIn("FastAPI", similares[0]["habilidades_comunes"])

    def test_ruta_usuario_empresa_analytics(self):
        ConexionService.conectar(self.u1.uid, self.u2.uid)
        EmpleoService.vincular(self.u2.uid, self.emp.eid, cargo="Cloud Architect", actual=True)

        ruta = GraphAnalyticsService.ruta_usuario_empresa(self.u1.uid, self.emp.eid)
        self.assertTrue(ruta["encontrado"])
        self.assertGreaterEqual(ruta["longitud"], 2)

    def test_habilidades_mas_demandadas_analytics(self):
        RequisitoOfertaService.vincular(self.ofr.oid, self.h1.hid, nivel_minimo="avanzado", prioridad="obligatoria")
        RequisitoOfertaService.vincular(self.ofr.oid, self.h2.hid, nivel_minimo="basico", prioridad="deseable")

        demandadas = GraphAnalyticsService.habilidades_mas_demandadas()
        self.assertGreaterEqual(len(demandadas), 2)
        nombres = [d["habilidad"] for d in demandadas]
        self.assertIn("FastAPI", nombres)
        self.assertIn("Neo4j", nombres)

    def test_candidatos_para_oferta_analytics(self):
        RequisitoOfertaService.vincular(self.ofr.oid, self.h1.hid, prioridad="obligatoria")
        HabilidadUsuarioService.vincular(self.u1.uid, self.h1.hid)

        candidatos = GraphAnalyticsService.candidatos_para_oferta(self.ofr.oid)
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["usuario"].uid, self.u1.uid)
        self.assertEqual(candidatos[0]["total_coincidencias"], 1)

    def test_consultas_view_endpoints(self):
        res = self.client.get(reverse("core:consultas_index"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Consultas Avanzadas de Grafo")

        res_cc = self.client.get(reverse("core:consultas_index") + f"?query_type=camino_corto&uid_origen={self.u1.uid}&uid_destino={self.u2.uid}")
        self.assertEqual(res_cc.status_code, 200)

        res_comun = self.client.get(reverse("core:consultas_index") + f"?query_type=contactos_comun&uid1={self.u1.uid}&uid2={self.u2.uid}")
        self.assertEqual(res_comun.status_code, 200)

        res_hab = self.client.get(reverse("core:consultas_index") + f"?query_type=habilidades_similares&uid={self.u1.uid}")
        self.assertEqual(res_hab.status_code, 200)

        res_ruta = self.client.get(reverse("core:consultas_index") + f"?query_type=ruta_empresa&uid={self.u1.uid}&eid={self.emp.eid}")
        self.assertEqual(res_ruta.status_code, 200)

        res_dem = self.client.get(reverse("core:consultas_index") + "?query_type=demanda_habilidades")
        self.assertEqual(res_dem.status_code, 200)

        res_cand = self.client.get(reverse("core:consultas_index") + f"?query_type=candidatos_oferta&oid={self.ofr.oid}")
        self.assertEqual(res_cand.status_code, 200)


class RecommendationEngineTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = UsuarioService.create(nombre="Alvaro", apellido="Vega", email="alvaro@test.com", titulo_profesional="Senior Backend")
        self.u2 = UsuarioService.create(nombre="Beatriz", apellido="Paz", email="beatriz@test.com", titulo_profesional="Data Scientist")
        self.u3 = UsuarioService.create(nombre="Camilo", apellido="Torres", email="camilo@test.com", titulo_profesional="DevOps Lead")
        self.emp = EmpresaService.create(nombre="DataWave", industria="Big Data", tamano="grande")
        self.h_py = HabilidadService.create(nombre="Python", categoria="tecnica")
        self.h_sql = HabilidadService.create(nombre="SQL", categoria="tecnica")
        self.h_gcp = HabilidadService.create(nombre="GCP", categoria="tecnica")
        self.proy = ProyectoService.create(nombre="Lakehouse Migration", estado="activo", tecnologias="Python, GCP")
        self.ofr = OfertaService.create(titulo="Data Engineer", modalidad="remoto", estado="abierta")
        PublicacionOfertaService.vincular(self.emp.eid, self.ofr.oid)

    def test_recomendar_contactos_amigos_de_amigos(self):
        ConexionService.conectar(self.u1.uid, self.u2.uid)
        ConexionService.conectar(self.u2.uid, self.u3.uid)

        recs = RecommendationEngine.recomendar_contactos(self.u1.uid)
        self.assertGreaterEqual(len(recs), 1)
        uids_recomendados = [r["usuario"].uid for r in recs]
        self.assertIn(self.u3.uid, uids_recomendados)
        self.assertNotIn(self.u2.uid, uids_recomendados)
        self.assertNotIn(self.u1.uid, uids_recomendados)

    def test_recomendar_empleos_por_habilidades(self):
        RequisitoOfertaService.vincular(self.ofr.oid, self.h_py.hid, nivel_minimo="intermedio", prioridad="obligatoria")
        RequisitoOfertaService.vincular(self.ofr.oid, self.h_sql.hid, nivel_minimo="basico", prioridad="deseable")

        HabilidadUsuarioService.vincular(self.u1.uid, self.h_py.hid, nivel="avanzado")

        recs = RecommendationEngine.recomendar_empleos(self.u1.uid)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["oferta"].oid, self.ofr.oid)
        self.assertEqual(recs[0]["match_porcentaje"], 50.0)
        self.assertIn("Python", recs[0]["habilidades_match"])
        self.assertIn("SQL", recs[0]["habilidades_faltantes"])

        PostulacionService.postular(self.u1.uid, self.ofr.oid)
        recs_post = RecommendationEngine.recomendar_empleos(self.u1.uid)
        self.assertEqual(len(recs_post), 0)

    def test_recomendar_colaboradores_proyecto(self):
        ParticipacionProyectoService.vincular(self.u1.uid, self.proy.pid, rol="Tech Lead")
        HabilidadUsuarioService.vincular(self.u2.uid, self.h_gcp.hid)
        ConexionService.conectar(self.u2.uid, self.u1.uid)

        recs = RecommendationEngine.recomendar_colaboradores_proyecto(self.proy.pid)
        self.assertGreaterEqual(len(recs), 1)
        self.assertEqual(recs[0]["usuario"].uid, self.u2.uid)
        self.assertIn("GCP", recs[0]["habilidades_match"])
        self.assertGreaterEqual(recs[0]["conexiones_equipo"], 1)

    def test_recomendar_candidatos_para_empresa(self):
        RequisitoOfertaService.vincular(self.ofr.oid, self.h_py.hid)
        HabilidadUsuarioService.vincular(self.u1.uid, self.h_py.hid)

        recs = RecommendationEngine.recomendar_candidatos_para_empresa(self.emp.eid)
        self.assertGreaterEqual(len(recs), 1)
        self.assertEqual(recs[0]["usuario"].uid, self.u1.uid)

    def test_recomendaciones_views(self):
        res = self.client.get(reverse("core:recomendaciones_index"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Recomendaciones Inteligentes")

        res_cont = self.client.get(reverse("core:recomendaciones_index") + f"?tab=contactos&uid={self.u1.uid}")
        self.assertEqual(res_cont.status_code, 200)

        res_emp = self.client.get(reverse("core:recomendaciones_index") + f"?tab=empleos&uid={self.u1.uid}")
        self.assertEqual(res_emp.status_code, 200)

        res_colab = self.client.get(reverse("core:recomendaciones_index") + f"?tab=colaboradores&pid={self.proy.pid}")
        self.assertEqual(res_colab.status_code, 200)

        res_tal = self.client.get(reverse("core:recomendaciones_index") + f"?tab=talento&eid={self.emp.eid}")
        self.assertEqual(res_tal.status_code, 200)

    def test_analytics_metricas_globales(self):
        ConexionService.conectar(self.u1.uid, self.u2.uid)
        metricas = NetworkAnalyticsService.metricas_red_globales()
        self.assertGreaterEqual(metricas["total_usuarios"], 2)
        self.assertGreaterEqual(metricas["total_conexiones"], 1)
        self.assertGreaterEqual(metricas["densidad_raw"], 0.0)
        self.assertGreaterEqual(metricas["grado_promedio"], 0.0)
        self.assertIn("clustering_coef", metricas)
        self.assertIn("diametro", metricas)

    def test_analytics_centralidad_y_pagerank(self):
        ConexionService.conectar(self.u1.uid, self.u2.uid)
        centralidad = NetworkAnalyticsService.ranking_centralidad_grado(limit=5)
        self.assertGreaterEqual(len(centralidad), 2)
        self.assertEqual(centralidad[0]["ranking"], 1)
        self.assertGreaterEqual(centralidad[0]["grado"], 1)

        pagerank = NetworkAnalyticsService.ranking_pagerank(limit=5)
        self.assertGreaterEqual(len(pagerank), 2)
        self.assertGreaterEqual(pagerank[0]["score"], 0.0)
        self.assertEqual(pagerank[0]["ranking"], 1)

    def test_analytics_comunidades_y_mercado(self):
        HabilidadUsuarioService.vincular(self.u1.uid, self.h_py.hid)
        RequisitoOfertaService.vincular(self.ofr.oid, self.h_py.hid, prioridad="obligatoria")
        
        comunidades = NetworkAnalyticsService.deteccion_comunidades()
        self.assertGreaterEqual(len(comunidades), 1)
        self.assertIn("nombre", comunidades[0])
        self.assertGreaterEqual(comunidades[0]["tamano"], 1)

        balance = NetworkAnalyticsService.analisis_oferta_demanda_habilidades()
        self.assertGreaterEqual(balance["total_habilidades"], 1)
        self.assertGreaterEqual(len(balance["habilidades"]), 1)

        graficos = NetworkAnalyticsService.preparar_datos_graficos()
        self.assertIn("influencia", graficos)
        self.assertIn("comunidades", graficos)
        self.assertIn("habilidades", graficos)

    def test_analytics_view_endpoint(self):
        res = self.client.get(reverse("core:analitica_dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Panel de Analítica de Grafos")
        self.assertIn("metricas", res.context)
        self.assertIn("centralidad", res.context)
        self.assertIn("pagerank", res.context)
        self.assertIn("comunidades", res.context)
        self.assertIn("habilidades_balance", res.context)
        self.assertIn("chart_data_json", res.context)

    def test_auth_login_views_and_quick_demo(self):
        # 1. GET Login Page
        res_get = self.client.get(reverse("core:login") + "?force=1")
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Iniciar Sesión")

        # 2. Quick Demo Login (1-click)
        res_quick = self.client.get(reverse("core:login") + f"?quick_login={self.u1.uid}")
        self.assertEqual(res_quick.status_code, 302)
        self.assertEqual(self.client.session.get("active_user_uid"), self.u1.uid)

        # 3. Normal POST Login
        res_post = self.client.post(reverse("core:login"), {
            "email": self.u1.email,
            "password": "WheelsOn2026*",
        })
        self.assertEqual(res_post.status_code, 302)
        self.assertEqual(self.client.session.get("active_user_uid"), self.u1.uid)

    def test_auth_registro_workflow(self):
        # 1. GET Registro Page
        res_get = self.client.get(reverse("core:registro") + "?force=1")
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Únete a WheelsOn")

        # 2. POST Registro
        nuevo_email = "nuevo.dev@wheelson.com"
        res_post = self.client.post(reverse("core:registro"), {
            "nombre": "Estudiante",
            "apellido": "Universitario",
            "email": nuevo_email,
            "titulo_profesional": "Graph Researcher",
            "ubicacion": "Bogotá, Colombia",
            "biografia": "Interesado en redes complejas",
            "password": "Password123*",
            "password_confirm": "Password123*",
        })
        self.assertEqual(res_post.status_code, 302)

        # Verificar que el usuario fue creado y logueado
        nuevo_user = UsuarioService.get_by_email(nuevo_email)
        self.assertIsNotNone(nuevo_user)
        self.assertEqual(self.client.session.get("active_user_uid"), nuevo_user.uid)

    def test_auth_logout_workflow(self):
        # Establecer sesión
        session = self.client.session
        session["active_user_uid"] = self.u1.uid
        session.save()

        # Logout
        res_logout = self.client.get(reverse("core:logout"))
        self.assertEqual(res_logout.status_code, 302)
        self.assertNotIn("active_user_uid", self.client.session)


class Fase9VisualizacionGrafoTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")
        self.client = Client()

    def test_grafo_interactivo_view_renders(self):
        res = self.client.get(reverse("core:grafo_interactivo"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Explorador de Grafo Interactivo")
        self.assertContains(res, "vis-graph-canvas")
        self.assertContains(res, "Vis.js Network")

    def test_grafo_data_api_returns_valid_structure(self):
        res = self.client.get(reverse("core:grafo_data_api"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["content-type"], "application/json")
        data = res.json()
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("stats", data)
        self.assertGreater(data["stats"]["total_nodos"], 0)
        self.assertGreater(data["stats"]["total_aristas"], 0)

    def test_grafo_data_api_filter_types(self):
        res = self.client.get(reverse("core:grafo_data_api") + "?tipos=Usuario,Empresa")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for node in data["nodes"]:
            self.assertIn(node["group"], ["Usuario", "Empresa"])

    def test_grafo_data_api_subgraph(self):
        res = self.client.get(reverse("core:grafo_data_api") + "?subgrafo=usr_carlos001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        node_ids = [n["id"] for n in data["nodes"]]
        self.assertIn("usr_carlos001", node_ids)

    def test_grafo_data_api_search(self):
        res = self.client.get(reverse("core:grafo_data_api") + "?q=Carlos")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        carlos_nodes = [n for n in data["nodes"] if "Carlos" in n["label"]]
        self.assertGreater(len(carlos_nodes), 0)


def contar_relaciones(tipo):
    return db.cypher_query(f"MATCH ()-[r:{tipo}]->() RETURN count(r)")[0][0][0]


class ScriptDeDatosTest(TestCase):
    """El script de datos debe cargar sin errores y crear todo el grafo."""

    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_crea_todos_los_nodos_y_relaciones(self):
        nodos = dict(db.cypher_query("MATCH (n) RETURN labels(n)[0], count(*)")[0])
        self.assertEqual(nodos, {"Usuario": 15, "Empresa": 3, "Habilidad": 12, "Proyecto": 2, "Oferta": 2})
        relaciones = dict(db.cypher_query("MATCH ()-[r]->() RETURN type(r), count(*)")[0])
        self.assertEqual(relaciones, {
            "CONECTA_CON": 30, "TRABAJA_EN": 15, "TIENE_HABILIDAD": 42,
            "PARTICIPA_EN": 8, "PUBLICA": 2, "REQUIERE": 6, "POSTULA_A": 2,
        })

    def test_usuario_de_ejemplo_puede_iniciar_sesion(self):
        cliente = Client()
        res = cliente.post(reverse("core:login") + "?force=1", {
            "email": "dubal@wheelson.com",
            "password": "WheelsOn2026*",
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(cliente.session.get("active_user_uid"), "usr_dubal003")

    def test_todas_las_pantallas_responden(self):
        cliente = Client()
        rutas = [
            "/", "/usuarios/", "/usuarios/usr_carlos001/", "/empresas/", "/empresas/emp_nexus01/",
            "/habilidades/", "/proyectos/", "/proyectos/proy_graph01/", "/ofertas/",
            "/ofertas/ofr_dataeng01/", "/conexiones/", "/analitica/", "/grafo/", "/grafo/api/data/",
            "/consultas/?tab=camino&uid1=usr_andres015&uid2=usr_miguel010",
            "/consultas/?tab=comun&uid1=usr_carlos001&uid2=usr_dubal003",
            "/consultas/?tab=similares&uid1=usr_carlos001",
            "/consultas/?tab=ruta_empresa&uid1=usr_andres015&eid=emp_techin02",
            "/consultas/?tab=candidatos&oid=ofr_dataeng01",
            "/recomendaciones/?tab=contactos&uid=usr_carlos001",
            "/recomendaciones/?tab=empleos&uid=usr_carlos001",
            "/recomendaciones/?tab=colaboradores&pid=proy_graph01",
            "/recomendaciones/?tab=talento&eid=emp_nexus01",
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)


class SoloNeo4jTest(TestCase):
    """La app no debe mostrar datos que no estén en Neo4j."""

    def test_base_vacia_no_inventa_datos(self):
        self.assertEqual(UsuarioService.all(), [])
        self.assertEqual(EmpresaService.all(), [])
        self.assertEqual(OfertaService.all(), [])
        self.assertIsNone(UsuarioService.get("usr_carlos001"))
        self.assertEqual(GraphAnalyticsService.habilidades_mas_demandadas(), [])

    def test_pantallas_funcionan_con_base_vacia(self):
        cliente = Client()
        for ruta in ["/", "/usuarios/", "/consultas/", "/recomendaciones/", "/analitica/", "/grafo/", "/conexiones/"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)

    def test_neo4j_caido_muestra_error_claro(self):
        cliente = Client()
        with patch("neomodel.sync_.database.Database.cypher_query", side_effect=ServiceUnavailable("caido")):
            res = cliente.get("/usuarios/")
        self.assertEqual(res.status_code, 503)
        self.assertContains(res, "No se pudo conectar con Neo4j", status_code=503)

    def test_credenciales_incorrectas_muestran_error_claro(self):
        cliente = Client()
        with patch("neomodel.sync_.database.Database.cypher_query", side_effect=AuthError("clave")):
            res = cliente.get("/analitica/")
        self.assertEqual(res.status_code, 503)
        self.assertContains(res, "rechazó el usuario o la contraseña", status_code=503)

    def test_api_del_grafo_responde_json_si_neo4j_esta_caido(self):
        cliente = Client()
        with patch("neomodel.sync_.database.Database.cypher_query", side_effect=ServiceUnavailable("caido")):
            res = cliente.get(reverse("core:grafo_data_api"))
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res["content-type"], "application/json")

    def test_correo_repetido_avisa_en_el_formulario(self):
        UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com")
        res = Client().post(reverse("core:usuario_crear"), {
            "nombre": "Otra", "apellido": "Ana", "email": "ana@test.com",
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Ya existe un usuario con este correo")
        self.assertEqual(len(UsuarioService.all()), 1)

    def test_nombre_de_empresa_repetido_lanza_error_de_unicidad(self):
        EmpresaService.create(nombre="Acme", industria="X")
        with self.assertRaises(UniqueProperty):
            EmpresaService.create(nombre="Acme", industria="Y")

    def test_cambiar_contrasena_desde_el_servicio(self):
        u = UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com", password="ClaveVieja1*")
        UsuarioService.update(u.uid, password="ClaveNueva1*")
        self.assertEqual(UsuarioService.autenticar("ana@test.com", "ClaveNueva1*").uid, u.uid)
        self.assertIsNone(UsuarioService.autenticar("ana@test.com", "ClaveVieja1*"))


class FechasEnRelacionesTest(TestCase):
    def setUp(self):
        super().setUp()
        self.cliente = Client()
        self.u = UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com")
        self.emp = EmpresaService.create(nombre="Acme", industria="Software")
        self.proy = ProyectoService.create(nombre="Motor", estado="activo")

    def test_experiencia_con_fecha_se_guarda_en_neo4j(self):
        self.cliente.post(reverse("core:usuario_experiencia_agregar", kwargs={"uid": self.u.uid}), {
            "eid": self.emp.eid, "cargo": "QA", "fecha_inicio": "2026-01-15", "actual": "on",
        })
        self.assertEqual(contar_relaciones("TRABAJA_EN"), 1)
        self.assertEqual(EmpleoService.listar_por_usuario(self.u.uid)[0]["fecha_inicio"], "2026-01-15")

    def test_colaborador_con_fecha_se_guarda_en_neo4j(self):
        self.cliente.post(reverse("core:proyecto_colaborador_agregar", kwargs={"pid": self.proy.pid}), {
            "uid": self.u.uid, "rol": "QA", "fecha_inicio": "2026-02-20",
        })
        self.assertEqual(contar_relaciones("PARTICIPA_EN"), 1)
        self.assertEqual(ParticipacionProyectoService.listar_por_proyecto(self.proy.pid)[0]["fecha_inicio"], "2026-02-20")

    def test_fecha_invalida_avisa_y_no_guarda(self):
        res = self.cliente.post(reverse("core:usuario_experiencia_agregar", kwargs={"uid": self.u.uid}), {
            "eid": self.emp.eid, "cargo": "QA", "fecha_inicio": "ayer", "actual": "on",
        }, follow=True)
        self.assertEqual(contar_relaciones("TRABAJA_EN"), 0)
        self.assertContains(res, "La fecha no es valida")

    def test_objeto_date_tambien_funciona(self):
        EmpleoService.vincular(self.u.uid, self.emp.eid, cargo="QA", fecha_inicio=date(2025, 3, 1))
        self.assertEqual(EmpleoService.listar_por_usuario(self.u.uid)[0]["fecha_inicio"], "2025-03-01")


class RelacionesSinDuplicadosTest(TestCase):
    def test_repetir_un_vinculo_reemplaza_sus_datos(self):
        u = UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com")
        e = EmpresaService.create(nombre="Acme", industria="X")
        h = HabilidadService.create(nombre="Python")
        EmpleoService.vincular(u.uid, e.eid, cargo="Junior")
        EmpleoService.vincular(u.uid, e.eid, cargo="Senior")
        HabilidadUsuarioService.vincular(u.uid, h.hid, nivel="basico")
        HabilidadUsuarioService.vincular(u.uid, h.hid, nivel="experto")

        self.assertEqual(contar_relaciones("TRABAJA_EN"), 1)
        self.assertEqual(EmpleoService.listar_por_usuario(u.uid)[0]["cargo"], "Senior")
        self.assertEqual(contar_relaciones("TIENE_HABILIDAD"), 1)
        self.assertEqual(HabilidadUsuarioService.listar_por_usuario(u.uid)[0]["nivel"], "experto")


class ConexionesMutuasTest(TestCase):
    def setUp(self):
        super().setUp()
        self.a = UsuarioService.create(nombre="Ana", apellido="Paz", email="a@test.com")
        self.b = UsuarioService.create(nombre="Beto", apellido="Rey", email="b@test.com")

    def test_la_conexion_se_ve_desde_ambos_lados(self):
        ConexionService.conectar(self.a.uid, self.b.uid, mensaje="Hola")
        self.assertEqual(ConexionService.listar(self.a.uid)[0]["usuario"].uid, self.b.uid)
        self.assertEqual(ConexionService.listar(self.b.uid)[0]["usuario"].uid, self.a.uid)
        self.assertTrue(ConexionService.estan_conectados(self.b.uid, self.a.uid))

    def test_conectar_en_sentido_contrario_no_duplica(self):
        ConexionService.conectar(self.a.uid, self.b.uid)
        ConexionService.conectar(self.b.uid, self.a.uid)
        self.assertEqual(contar_relaciones("CONECTA_CON"), 1)

    def test_desconectar_funciona_desde_cualquier_lado(self):
        ConexionService.conectar(self.a.uid, self.b.uid)
        self.assertTrue(ConexionService.desconectar(self.b.uid, self.a.uid))
        self.assertEqual(contar_relaciones("CONECTA_CON"), 0)

    def test_conteo_de_conexiones_en_datos_de_ejemplo(self):
        ejecutar_script_cypher("seed_data.cypher")
        self.assertEqual(len(ConexionService.listar("usr_dubal003")), 5)


class RecomendacionesEnGrafoTest(TestCase):
    def setUp(self):
        super().setUp()
        self.yo = UsuarioService.create(nombre="Yo", apellido="Mismo", email="yo@test.com")
        self.x = UsuarioService.create(nombre="Xavi", apellido="Luz", email="x@test.com")
        self.z = UsuarioService.create(nombre="Zoe", apellido="Mar", email="z@test.com")
        self.py = HabilidadService.create(nombre="Python")
        self.react = HabilidadService.create(nombre="React")

    def test_contactos_solo_cuenta_habilidades_compartidas_conmigo(self):
        # Xavi y Zoe comparten React entre ellos, pero yo solo tengo Python.
        HabilidadUsuarioService.vincular(self.yo.uid, self.py.hid)
        HabilidadUsuarioService.vincular(self.x.uid, self.py.hid)
        HabilidadUsuarioService.vincular(self.x.uid, self.react.hid)
        HabilidadUsuarioService.vincular(self.z.uid, self.react.hid)

        recomendados = RecommendationEngine.recomendar_contactos(self.yo.uid)
        self.assertEqual([r["usuario"].uid for r in recomendados], [self.x.uid])
        self.assertEqual(recomendados[0]["nombres_habs"], ["Python"])

    def test_empleos_indica_las_habilidades_que_faltan(self):
        oferta = OfertaService.create(titulo="Dev", estado="abierta")
        RequisitoOfertaService.vincular(oferta.oid, self.py.hid)
        RequisitoOfertaService.vincular(oferta.oid, self.react.hid, prioridad="deseable")
        HabilidadUsuarioService.vincular(self.yo.uid, self.py.hid)

        recomendacion = RecommendationEngine.recomendar_empleos(self.yo.uid)[0]
        self.assertEqual(recomendacion["habilidades_faltantes"], ["React"])
        self.assertEqual(recomendacion["obligatorias_cubiertas"], 1)
        self.assertEqual(recomendacion["total_obligatorias"], 1)

    def test_ruta_a_empresa_no_pasa_por_habilidades(self):
        empresa = EmpresaService.create(nombre="Acme", industria="X")
        HabilidadUsuarioService.vincular(self.yo.uid, self.py.hid)
        HabilidadUsuarioService.vincular(self.x.uid, self.py.hid)
        EmpleoService.vincular(self.x.uid, empresa.eid, cargo="Dev")
        self.assertFalse(GraphAnalyticsService.ruta_usuario_empresa(self.yo.uid, empresa.eid)["encontrado"])


class GrafoInteractivoDesdeNeo4jTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_cada_arista_coincide_con_neo4j(self):
        datos = Client().get(reverse("core:grafo_data_api")).json()
        en_pantalla = {}
        for arista in datos["edges"]:
            en_pantalla[arista["label"]] = en_pantalla.get(arista["label"], 0) + 1
        en_neo4j = dict(db.cypher_query("MATCH ()-[r]->() RETURN type(r), count(*)")[0])
        self.assertEqual(en_pantalla, en_neo4j)

    def test_relacion_creada_directo_en_neo4j_aparece(self):
        db.cypher_query(
            "MATCH (a:Usuario {uid: 'usr_miguel010'}), (b:Usuario {uid: 'usr_andres015'}) "
            "CREATE (a)-[:CONECTA_CON]->(b)"
        )
        datos = Client().get(reverse("core:grafo_data_api")).json()
        self.assertTrue(any(
            {arista["from"], arista["to"]} == {"usr_miguel010", "usr_andres015"}
            for arista in datos["edges"]
        ))


class ComunidadesTest(TestCase):
    def _grupo(self, prefijo, cantidad):
        usuarios = [
            UsuarioService.create(nombre=f"{prefijo}{i}", apellido="T", email=f"{prefijo}{i}@test.com")
            for i in range(cantidad)
        ]
        for i, a in enumerate(usuarios):
            for b in usuarios[i + 1:]:
                ConexionService.conectar(a.uid, b.uid)
        return usuarios

    def test_separa_dos_grupos_unidos_por_un_solo_puente(self):
        grupo_a = self._grupo("a", 4)
        grupo_b = self._grupo("b", 4)
        ConexionService.conectar(grupo_a[0].uid, grupo_b[0].uid)

        comunidades = NetworkAnalyticsService.deteccion_comunidades()
        self.assertEqual(len(comunidades), 2)
        conjuntos = [{m.uid for m in c["miembros"]} for c in comunidades]
        self.assertIn({u.uid for u in grupo_a}, conjuntos)
        self.assertIn({u.uid for u in grupo_b}, conjuntos)

    def test_datos_de_ejemplo_tienen_varias_comunidades_y_resultado_estable(self):
        ejecutar_script_cypher("seed_data.cypher")
        primera = NetworkAnalyticsService.deteccion_comunidades()
        segunda = NetworkAnalyticsService.deteccion_comunidades()
        self.assertGreater(len(primera), 1)
        self.assertEqual(sum(c["tamano"] for c in primera), 15)
        self.assertEqual(
            [sorted(m.uid for m in c["miembros"]) for c in primera],
            [sorted(m.uid for m in c["miembros"]) for c in segunda],
        )


class PanelDeAnaliticaTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_grafico_de_influencia_no_pone_pagerank_en_cero(self):
        datos = NetworkAnalyticsService.preparar_datos_graficos()["influencia"]
        self.assertTrue(all(valor > 0 for valor in datos["pagerank"]))

    def test_oferta_cerrada_no_cuenta_como_demanda(self):
        OfertaService.update("ofr_arch02", estado="cerrada")
        balance = NetworkAnalyticsService.analisis_oferta_demanda_habilidades()
        en_panel = {item["habilidad"].nombre: item["demanda"] for item in balance["top_demandadas"]}
        en_consulta = {
            item["habilidad"]: item["total_ofertas"]
            for item in GraphAnalyticsService.habilidades_mas_demandadas()
        }
        self.assertEqual(en_panel, en_consulta)
        self.assertNotIn("Liderazgo", en_panel)

    def test_mas_demandadas_excluye_habilidades_sin_demanda(self):
        balance = NetworkAnalyticsService.analisis_oferta_demanda_habilidades()
        self.assertTrue(balance["top_demandadas"])
        self.assertTrue(all(item["demanda"] > 0 for item in balance["top_demandadas"]))
