import os
import re
from html.parser import HTMLParser
from urllib.parse import urljoin
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client as ClienteAnonimo, override_settings
from django.utils.functional import empty
from django.utils.html import escape
from django.urls import reverse
from neo4j.exceptions import AuthError, ServiceUnavailable
from neomodel import UniqueProperty, db

from core.test_utils import Neo4jTestCase as TestCase, SCRIPTS, ejecutar_script_cypher
from core.templatetags.wheelson_ui import cifra_porcentaje, skyline
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
    NotificacionService,
    AvanceService,
    PublicacionService,
    InvitacionService,
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
from core.presentacion import IMAGENES_FEED, MAX_AVISOS, avisos_para, imagen_de_publicacion, imagen_para, tejer_feed
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


class Client(ClienteAnonimo):
    """Cliente con sesión de administrador, para las pruebas que no tratan sobre permisos."""

    ADMIN = "admin.pruebas@test.com"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sesion_lista = False

    def preparar_sesion(self):
        if self._sesion_lista:
            return
        self._sesion_lista = True
        admin = UsuarioService.get_by_email(self.ADMIN) or UsuarioService.create(nombre="Admin", apellido="Pruebas", email=self.ADMIN)
        admin.rol = "admin"
        admin.save()
        sesion = self.session
        sesion["active_user_uid"] = admin.uid
        sesion.save()

    def request(self, **peticion):
        self.preparar_sesion()
        return super().request(**peticion)


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
            "password": "ClaveDePrueba7*",
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
        empresa = EmpresaService.create(nombre="Acme Datos", industria="Datos")
        post_res = self.client.post(reverse("core:oferta_crear"), {
            "eid": empresa.eid,
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
        self.assertContains(res, "ws-sidebar")
        self.assertContains(res, "data-theme")
        self.assertNotContains(res, "themeManager")
        self.assertNotContains(res, "htmx")

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
        self.assertContains(res, 'id="user-constellation-network"')

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
        self.assertContains(res, "Empleos publicados")

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
        self.assertContains(res, "Postularme")

    def test_proyecto_detalle_template(self):
        p = ProyectoService.create(
            nombre="AI Graph Engine",
            estado="activo",
            tecnologias="Python, Neo4j, Cypher",
        )
        res = self.client.get(reverse("core:proyecto_detalle", kwargs={"pid": p.pid}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "AI Graph Engine")
        self.assertContains(res, "Tecnologías")

    def test_habilidades_cloud_template(self):
        HabilidadService.create(nombre="Kubernetes", categoria="tecnica")
        res = self.client.get(reverse("core:habilidades_lista"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "ws-catalogo__item")
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
        res_conectar = entrar_como(self.u1.uid).post(reverse("core:conexion_conectar"), {
            "uid_destino": self.u2.uid,
            "mensaje": "Conectemos por favor",
        })
        self.assertEqual(res_conectar.status_code, 302)
        self.assertFalse(ConexionService.estan_conectados(self.u1.uid, self.u2.uid))
        entrar_como(self.u2.uid).post(reverse("core:conexion_solicitud_responder", kwargs={"uid_origen": self.u1.uid}), {"accion": "aceptar"})
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

        res_postular = entrar_como(self.u1.uid).post(reverse("core:oferta_postular", kwargs={"oid": self.ofr.oid}), {
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
        self.assertContains(res, "Sugerencias")

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
        self.assertContains(res, "Analítica")
        self.assertIn("metricas", res.context)
        self.assertIn("centralidad", res.context)
        self.assertIn("pagerank", res.context)
        self.assertIn("comunidades", res.context)
        self.assertIn("habilidades_balance", res.context)
        self.assertIn("chart_data", res.context)

    def test_auth_login_views_and_quick_demo(self):
        # 1. GET Login Page
        self.client = ClienteAnonimo()
        res_get = self.client.get(reverse("core:login") + "?force=1")
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Iniciar Sesión")

        # 2. Quick Demo Login (1-click)
        self.client = ClienteAnonimo()
        res_quick = self.client.get(reverse("core:login") + f"?quick_login={self.u1.uid}")
        self.assertEqual(res_quick.status_code, 302)
        self.assertEqual(self.client.session.get("active_user_uid"), self.u1.uid)

        # 3. Normal POST Login
        UsuarioService.update(self.u1.uid, password="ClaveDePrueba7*")
        self.client = ClienteAnonimo()
        res_post = self.client.post(reverse("core:login"), {
            "email": self.u1.email,
            "password": "ClaveDePrueba7*",
        })
        self.assertEqual(res_post.status_code, 302)
        self.assertEqual(self.client.session.get("active_user_uid"), self.u1.uid)

    def test_auth_registro_workflow(self):
        # 1. GET Registro Page
        self.client = ClienteAnonimo()
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
        self.client = ClienteAnonimo()
        session = self.client.session
        session["active_user_uid"] = self.u1.uid
        session.save()

        # Logout
        res_logout = self.client.post(reverse("core:logout"))
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
        self.assertContains(res, "Grafo Interactivo")
        self.assertContains(res, "vis-graph-canvas")
        self.assertContains(res, "vendor/vis-network-9.1.9.min.js")

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
        self.assertEqual(nodos, {"Usuario": 15, "Empresa": 3, "Habilidad": 12, "Proyecto": 3, "Oferta": 2, "Publicacion": 4, "Avance": 3})
        relaciones = dict(db.cypher_query("MATCH ()-[r]->() RETURN type(r), count(*)")[0])
        self.assertEqual(relaciones, {
            "CONECTA_CON": 30, "TRABAJA_EN": 15, "TIENE_HABILIDAD": 42,
            "PARTICIPA_EN": 11, "PUBLICA": 2, "REQUIERE": 6, "POSTULA_A": 2,
            "ADMINISTRA": 3, "LIDERA": 3, "SOLICITA_CONEXION": 2, "INVITADO_A": 1, "SOLICITA_UNIRSE": 1,
            "AUTOR_DE": 4, "REDACTA": 1, "PERCIBE": 7, "TIENE_AVANCE": 3, "REGISTRA": 3,
            "SOLICITA_EMPLEO": 1,
        })

    def test_usuario_de_ejemplo_puede_iniciar_sesion(self):
        cliente = ClienteAnonimo()
        res = cliente.post(reverse("core:login") + "?force=1", {
            "email": "dubal@wheelson.com",
            "password": clave_demo("dubal@wheelson.com"),
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
            "/consultas/?tab=ruta_oferta&uid1=usr_andres015&oid=ofr_dataeng01",
            "/consultas/?tab=proyectos&pid=proy_graph01",
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
        for ruta in [
            "/", "/usuarios/", "/consultas/", "/recomendaciones/", "/analitica/", "/grafo/", "/conexiones/",
            "/consultas/?tab=ruta_oferta", "/consultas/?tab=proyectos", "/consultas/?tab=candidatos",
        ]:
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)

    def test_neo4j_caido_muestra_error_claro(self):
        cliente = Client()
        cliente.preparar_sesion()
        with patch("neomodel.sync_.database.Database.cypher_query", side_effect=ServiceUnavailable("caido")):
            res = cliente.get("/usuarios/")
        self.assertEqual(res.status_code, 503)
        self.assertContains(res, "No se pudo conectar con Neo4j", status_code=503)

    def test_credenciales_incorrectas_muestran_error_claro(self):
        cliente = Client()
        cliente.preparar_sesion()
        with patch("neomodel.sync_.database.Database.cypher_query", side_effect=AuthError("clave")):
            res = cliente.get("/analitica/")
        self.assertEqual(res.status_code, 503)
        self.assertContains(res, "rechazó el usuario o la contraseña", status_code=503)

    def test_api_del_grafo_responde_json_si_neo4j_esta_caido(self):
        cliente = Client()
        cliente.preparar_sesion()
        with patch("neomodel.sync_.database.Database.cypher_query", side_effect=ServiceUnavailable("caido")):
            res = cliente.get(reverse("core:grafo_data_api"))
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res["content-type"], "application/json")

    def test_correo_repetido_avisa_en_el_formulario(self):
        UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com")
        res = Client().post(reverse("core:usuario_crear"), {
            "nombre": "Otra", "apellido": "Ana", "email": "ana@test.com", "password": "ClaveDePrueba7*",
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Ya existe un usuario con este correo")
        self.assertEqual(sum(u.email == "ana@test.com" for u in UsuarioService.all()), 1)

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
        self.assertEqual(contar_relaciones("PARTICIPA_EN"), 0)
        entrar_como(self.u.uid).post(reverse("core:proyecto_invitacion_responder", kwargs={"pid": self.proy.pid}), {"accion": "aceptar"})
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
        # El grafo muestra la red profesional: ni lo pendiente ni el contenido del feed
        en_neo4j = dict(db.cypher_query(
            "MATCH ()-[r]->() WHERE NOT type(r) IN ['SOLICITA_CONEXION', 'SOLICITA_UNIRSE', 'INVITADO_A', 'INVITADO_A_ADMINISTRAR', "
            "'SOLICITA_EMPLEO', 'SOLICITA_ALIANZA', 'AUTOR_DE', 'REDACTA', 'PERCIBE', 'TIENE_AVANCE', 'REGISTRA'] "
            "RETURN type(r), count(*)"
        )[0])
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


class ProyectosRelacionadosTest(TestCase):
    def setUp(self):
        super().setUp()
        self.base = ProyectoService.create(nombre="Base", tecnologias="Python, Neo4j")
        self.ana = UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com")
        self.beto = UsuarioService.create(nombre="Beto", apellido="Rey", email="beto@test.com")

    def test_tecnologias_comunes_sin_distinguir_mayusculas(self):
        otro = ProyectoService.create(nombre="Otro", tecnologias="python, Django")
        resultado = GraphAnalyticsService.proyectos_relacionados(self.base.pid)
        self.assertEqual([r["proyecto"].pid for r in resultado], [otro.pid])
        self.assertEqual(resultado[0]["tecnologias_comunes"], ["Python"])
        self.assertEqual(resultado[0]["miembros_comunes"], [])
        self.assertEqual(resultado[0]["miembros_conectados"], [])

    def test_miembros_comunes_sin_tecnologias_comunes(self):
        otro = ProyectoService.create(nombre="Otro", tecnologias="Go")
        ParticipacionProyectoService.vincular(self.ana.uid, self.base.pid)
        ParticipacionProyectoService.vincular(self.ana.uid, otro.pid)
        resultado = GraphAnalyticsService.proyectos_relacionados(self.base.pid)
        self.assertEqual(resultado[0]["miembros_comunes"], ["Ana Paz"])
        self.assertEqual(resultado[0]["tecnologias_comunes"], [])

    def test_miembros_conectados_entre_equipos(self):
        otro = ProyectoService.create(nombre="Otro", tecnologias="Go")
        ParticipacionProyectoService.vincular(self.ana.uid, self.base.pid)
        ParticipacionProyectoService.vincular(self.beto.uid, otro.pid)
        ConexionService.conectar(self.beto.uid, self.ana.uid)
        resultado = GraphAnalyticsService.proyectos_relacionados(self.base.pid)
        self.assertEqual(resultado[0]["miembros_conectados"], ["Ana Paz - Beto Rey"])

    def test_miembro_comun_no_se_repite_como_conectado(self):
        otro = ProyectoService.create(nombre="Otro", tecnologias="Go")
        for proyecto in (self.base, otro):
            ParticipacionProyectoService.vincular(self.ana.uid, proyecto.pid)
        ParticipacionProyectoService.vincular(self.beto.uid, otro.pid)
        ConexionService.conectar(self.ana.uid, self.beto.uid)
        resultado = GraphAnalyticsService.proyectos_relacionados(self.base.pid)
        self.assertEqual(resultado[0]["miembros_comunes"], ["Ana Paz"])
        self.assertEqual(resultado[0]["miembros_conectados"], [])

    def test_proyecto_sin_relacion_no_aparece(self):
        ProyectoService.create(nombre="Aislado", tecnologias="Cobol")
        self.assertEqual(GraphAnalyticsService.proyectos_relacionados(self.base.pid), [])

    def test_proyecto_sin_tecnologias_no_falla(self):
        vacio = ProyectoService.create(nombre="Vacio")
        self.assertEqual(GraphAnalyticsService.proyectos_relacionados(vacio.pid), [])

    def test_ordena_por_puntaje_y_respeta_el_limite(self):
        uno = ProyectoService.create(nombre="Uno", tecnologias="Python")
        dos = ProyectoService.create(nombre="Dos", tecnologias="Python, Neo4j")
        resultado = GraphAnalyticsService.proyectos_relacionados(self.base.pid)
        self.assertEqual([r["proyecto"].pid for r in resultado], [dos.pid, uno.pid])
        self.assertEqual(len(GraphAnalyticsService.proyectos_relacionados(self.base.pid, limit=1)), 1)

    def test_identificador_vacio_o_inexistente(self):
        self.assertEqual(GraphAnalyticsService.proyectos_relacionados(""), [])
        self.assertEqual(GraphAnalyticsService.proyectos_relacionados("no_existe"), [])

    def test_datos_de_ejemplo_y_pantalla(self):
        db.cypher_query("MATCH (n) DETACH DELETE n")
        ejecutar_script_cypher("seed_data.cypher")
        resultado = {
            r["proyecto"].pid: r for r in GraphAnalyticsService.proyectos_relacionados("proy_graph01")
        }
        self.assertCountEqual(resultado, ["proy_fintech02", "proy_talento03"])
        fintech = resultado["proy_fintech02"]
        self.assertCountEqual(fintech["tecnologias_comunes"], ["Python", "Neo4j"])
        self.assertEqual(fintech["miembros_comunes"], [])
        self.assertIn("Santiago Vieira - Dubal Aguilar", fintech["miembros_conectados"])
        self.assertEqual(resultado["proy_talento03"]["miembros_comunes"], ["Carlos Calabria"])

        res = Client().get(reverse("core:consultas_index") + "?tab=proyectos&pid=proy_graph01")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Plataforma Fintech AI")
        self.assertContains(res, "Recomendador de Talento")
        self.assertContains(res, "Miembros conectados entre equipos")


class CandidatosConConexionesTest(TestCase):
    def setUp(self):
        super().setUp()
        self.empresa = EmpresaService.create(nombre="Acme", industria="X")
        self.oferta = OfertaService.create(titulo="Dev", estado="abierta")
        PublicacionOfertaService.vincular(self.empresa.eid, self.oferta.oid)
        self.py = HabilidadService.create(nombre="Python")
        self.sql = HabilidadService.create(nombre="SQL")
        RequisitoOfertaService.vincular(self.oferta.oid, self.py.hid, prioridad="obligatoria")
        RequisitoOfertaService.vincular(self.oferta.oid, self.sql.hid, prioridad="deseable")
        self.interno = UsuarioService.create(nombre="Ines", apellido="Dentro", email="ines@test.com")
        EmpleoService.vincular(self.interno.uid, self.empresa.eid, cargo="Lider")
        self.con_contacto = UsuarioService.create(nombre="Zoe", apellido="Red", email="zoe@test.com")
        self.sin_contacto = UsuarioService.create(nombre="Ana", apellido="Sola", email="ana@test.com")
        for usuario in (self.con_contacto, self.sin_contacto):
            HabilidadUsuarioService.vincular(usuario.uid, self.py.hid)

    def _uids(self):
        return [c["usuario"].uid for c in GraphAnalyticsService.candidatos_para_oferta(self.oferta.oid)]

    def test_contacto_en_la_empresa_sube_el_puesto(self):
        self.assertEqual(self._uids(), [self.sin_contacto.uid, self.con_contacto.uid])
        ConexionService.conectar(self.con_contacto.uid, self.interno.uid)
        self.assertEqual(self._uids(), [self.con_contacto.uid, self.sin_contacto.uid])
        primero = GraphAnalyticsService.candidatos_para_oferta(self.oferta.oid)[0]
        self.assertEqual(primero["contactos_en_empresa"], ["Ines Dentro"])

    def test_competencias_pesan_mas_que_un_contacto(self):
        ConexionService.conectar(self.con_contacto.uid, self.interno.uid)
        HabilidadUsuarioService.vincular(self.sin_contacto.uid, self.sql.hid)
        self.assertEqual(self._uids(), [self.sin_contacto.uid, self.con_contacto.uid])

    def test_solo_conexion_sin_competencias_no_es_candidato(self):
        sin_habilidad = UsuarioService.create(nombre="Beto", apellido="Rey", email="beto@test.com")
        ConexionService.conectar(sin_habilidad.uid, self.interno.uid)
        self.assertNotIn(sin_habilidad.uid, self._uids())

    def test_empleado_actual_no_es_candidato_y_ex_empleado_si(self):
        HabilidadUsuarioService.vincular(self.interno.uid, self.py.hid)
        self.assertNotIn(self.interno.uid, self._uids())
        EmpleoService.vincular(self.interno.uid, self.empresa.eid, cargo="Lider", actual=False)
        self.assertIn(self.interno.uid, self._uids())

    def test_ex_empleado_no_cuenta_como_contacto(self):
        EmpleoService.vincular(self.interno.uid, self.empresa.eid, cargo="Lider", actual=False)
        ConexionService.conectar(self.con_contacto.uid, self.interno.uid)
        resultado = GraphAnalyticsService.candidatos_para_oferta(self.oferta.oid)
        contactos = {c["usuario"].uid: c["contactos_en_empresa"] for c in resultado}
        self.assertEqual(contactos[self.con_contacto.uid], [])

    def test_conteos_no_se_inflan_con_varias_habilidades_y_contactos(self):
        otro = UsuarioService.create(nombre="Oto", apellido="Dentro", email="oto@test.com")
        EmpleoService.vincular(otro.uid, self.empresa.eid, cargo="Dev")
        ConexionService.conectar(self.con_contacto.uid, self.interno.uid)
        ConexionService.conectar(self.con_contacto.uid, otro.uid)
        HabilidadUsuarioService.vincular(self.con_contacto.uid, self.sql.hid)
        c = GraphAnalyticsService.candidatos_para_oferta(self.oferta.oid)[0]
        self.assertEqual(c["total_coincidencias"], 2)
        self.assertEqual(c["obligatorias_cubiertas"], 1)
        self.assertCountEqual(c["contactos_en_empresa"], ["Ines Dentro", "Oto Dentro"])
        self.assertEqual(c["score"], 2 * 3 + 1 * 2 + 2 * 2)

    def test_indica_si_ya_se_postulo(self):
        PostulacionService.postular(self.sin_contacto.uid, self.oferta.oid)
        estados = {
            c["usuario"].uid: c["ya_postulado"]
            for c in GraphAnalyticsService.candidatos_para_oferta(self.oferta.oid)
        }
        self.assertTrue(estados[self.sin_contacto.uid])
        self.assertFalse(estados[self.con_contacto.uid])

    def test_oferta_sin_empresa_sigue_funcionando(self):
        suelta = OfertaService.create(titulo="Suelta", estado="abierta")
        RequisitoOfertaService.vincular(suelta.oid, self.py.hid)
        self.assertEqual(len(GraphAnalyticsService.candidatos_para_oferta(suelta.oid)), 2)

    def test_identificador_vacio_o_inexistente(self):
        self.assertEqual(GraphAnalyticsService.candidatos_para_oferta(""), [])
        self.assertEqual(GraphAnalyticsService.candidatos_para_oferta("no_existe"), [])

    def test_datos_de_ejemplo_y_pantalla(self):
        db.cypher_query("MATCH (n) DETACH DELETE n")
        ejecutar_script_cypher("seed_data.cypher")
        resultado = GraphAnalyticsService.candidatos_para_oferta("ofr_dataeng01")
        uids = [c["usuario"].uid for c in resultado]
        # Mateo y Carlos trabajan en Nexus Corp, la empresa que publica esta oferta.
        self.assertNotIn("usr_mateo005", uids)
        self.assertNotIn("usr_carlos001", uids)
        self.assertEqual(uids[0], "usr_dubal003")
        self.assertTrue(resultado[0]["ya_postulado"])
        self.assertIn("Mateo Cisneros", resultado[0]["contactos_en_empresa"])

        res = Client().get(reverse("core:consultas_index") + "?tab=candidatos&oid=ofr_dataeng01")
        self.assertContains(res, "Contactos en la empresa")
        self.assertContains(res, "Ya se postuló")


class RutaUsuarioOfertaTest(TestCase):
    def setUp(self):
        super().setUp()
        self.empresa = EmpresaService.create(nombre="Acme", industria="X")
        self.oferta = OfertaService.create(titulo="Dev", estado="abierta")
        PublicacionOfertaService.vincular(self.empresa.eid, self.oferta.oid)
        self.ana = UsuarioService.create(nombre="Ana", apellido="Paz", email="ana@test.com")
        self.beto = UsuarioService.create(nombre="Beto", apellido="Rey", email="beto@test.com")

    def _ruta(self, uid=None, oid=None):
        return GraphAnalyticsService.ruta_usuario_oferta(uid or self.ana.uid, oid or self.oferta.oid)

    def test_empleado_llega_por_su_empresa(self):
        EmpleoService.vincular(self.ana.uid, self.empresa.eid, cargo="Dev")
        ruta = self._ruta()
        self.assertTrue(ruta["encontrado"])
        self.assertEqual(ruta["longitud"], 2)
        self.assertEqual([p["tipo"] for p in ruta["camino"]], ["Usuario", "Empresa", "Oferta"])
        self.assertEqual(
            [p["relacion_siguiente"] for p in ruta["camino"]],
            ["TRABAJA_EN", "PUBLICA", None],
        )

    def test_llega_a_traves_de_un_contacto(self):
        EmpleoService.vincular(self.beto.uid, self.empresa.eid, cargo="Dev")
        ConexionService.conectar(self.beto.uid, self.ana.uid)
        ruta = self._ruta()
        self.assertEqual(ruta["longitud"], 3)
        self.assertEqual([p["nombre"] for p in ruta["camino"]], ["Ana Paz", "Beto Rey", "Acme", "Dev"])

    def test_sin_contactos_no_hay_camino(self):
        EmpleoService.vincular(self.beto.uid, self.empresa.eid, cargo="Dev")
        self.assertFalse(self._ruta()["encontrado"])

    def test_oferta_sin_empresa_no_tiene_camino(self):
        suelta = OfertaService.create(titulo="Suelta", estado="abierta")
        self.assertFalse(self._ruta(oid=suelta.oid)["encontrado"])

    def test_habilidad_compartida_no_cuenta_como_camino(self):
        habilidad = HabilidadService.create(nombre="Python")
        HabilidadUsuarioService.vincular(self.ana.uid, habilidad.hid)
        HabilidadUsuarioService.vincular(self.beto.uid, habilidad.hid)
        EmpleoService.vincular(self.beto.uid, self.empresa.eid, cargo="Dev")
        self.assertFalse(self._ruta()["encontrado"])

    def test_postularse_no_crea_camino_pero_se_informa(self):
        PostulacionService.postular(self.ana.uid, self.oferta.oid)
        ruta = self._ruta()
        self.assertFalse(ruta["encontrado"])
        self.assertTrue(ruta["ya_postulado"])

    def test_postulacion_de_otro_no_sirve_de_puente(self):
        ConexionService.conectar(self.ana.uid, self.beto.uid)
        PostulacionService.postular(self.beto.uid, self.oferta.oid)
        ruta = self._ruta()
        self.assertFalse(ruta["encontrado"])
        self.assertFalse(ruta["ya_postulado"])

    def test_identificadores_vacios_o_inexistentes(self):
        self.assertFalse(GraphAnalyticsService.ruta_usuario_oferta("", self.oferta.oid)["encontrado"])
        self.assertFalse(GraphAnalyticsService.ruta_usuario_oferta(self.ana.uid, "")["encontrado"])
        self.assertFalse(GraphAnalyticsService.ruta_usuario_oferta("no", "existe")["encontrado"])

    def test_datos_de_ejemplo_y_pantalla(self):
        ejecutar_script_cypher("seed_data.cypher")
        ruta = GraphAnalyticsService.ruta_usuario_oferta("usr_andres015", "ofr_dataeng01")
        self.assertTrue(ruta["encontrado"])
        self.assertEqual(ruta["camino"][0]["id"], "usr_andres015")
        self.assertEqual(ruta["camino"][-2]["id"], "emp_nexus01")
        self.assertEqual(ruta["camino"][-1]["id"], "ofr_dataeng01")

        res = Client().get(reverse("core:consultas_index") + "?tab=ruta_oferta&uid1=usr_andres015&oid=ofr_dataeng01")
        self.assertContains(res, "Camino Encontrado")
        self.assertContains(res, ":PUBLICA")

    def test_pantalla_sin_camino_explica_el_motivo(self):
        res = Client().get(
            reverse("core:consultas_index") + f"?tab=ruta_oferta&uid1={self.ana.uid}&oid={self.oferta.oid}"
        )
        self.assertContains(res, "No se encontró un camino hacia esta oferta")


class ScriptDeConsultasTest(TestCase):
    """Todas las consultas del entregable deben ejecutarse sin errores en Neo4j."""

    def test_todas_las_consultas_son_validas(self):
        ejecutar_script_cypher("seed_data.cypher")
        lineas = [
            linea for linea in (SCRIPTS / "queries.cypher").read_text(encoding="utf-8").splitlines()
            if not linea.strip().startswith("//")
        ]
        sentencias = [s.strip() for s in "\n".join(lineas).split(";\n") if s.strip()]
        self.assertEqual(len(sentencias), 17)
        parametros = {
            "uid": "usr_dubal003", "uid1": "usr_carlos001", "uid2": "usr_dubal003",
            "eid": "emp_nexus01", "oid": "ofr_dataeng01", "pid": "proy_graph01", "limit": 10,
        }
        for numero, sentencia in enumerate(sentencias, 1):
            with self.subTest(consulta=numero):
                filas, _ = db.cypher_query(sentencia.rstrip(";"), parametros)
                self.assertGreater(len(filas), 0)


class SistemaVisualTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")
        self.cliente = Client()
        self.cliente.get(reverse("core:login") + "?quick_login=usr_dubal003")

    def test_navegacion_conserva_sus_opciones_en_orden(self):
        html = self.cliente.get(reverse("core:dashboard")).content.decode()
        inicio = html.index('aria-label="Principal"')
        fin = html.index("</nav>", inicio)
        nombres = re.findall(r"</svg><span>([^<]+)</span>", html[inicio:fin])
        self.assertEqual(nombres, [
            "Inicio", "Proyectos", "Empleos", "Empresas", "Mi Red",
            "Sugerencias", "Explorar", "Analítica", "Grafo Interactivo", "Consultas Cypher",
        ])

    def test_bienvenida_personalizada_y_sin_elementos_sin_respaldo(self):
        res = self.cliente.get(reverse("core:dashboard"))
        self.assertContains(res, "Hola, <span>Dubal</span>.")
        self.assertContains(res, "Exploremos la red hoy")
        self.assertNotContains(res, "wheelson.io")
        self.assertNotContains(res, "colegas colaboraron")

    def test_feed_usa_imagen_estable_por_elemento(self):
        self.assertEqual(imagen_para("proy_graph01"), imagen_para("proy_graph01"))
        self.assertIn(imagen_para("cualquiera"), IMAGENES_FEED)
        for imagen in IMAGENES_FEED:
            self.assertTrue(finders.find(imagen), imagen)

    def test_no_todas_las_publicaciones_llevan_imagen(self):
        imagenes = [imagen_de_publicacion(p) for p in ("proy_graph01", "proy_fintech02", "proy_talento03")]
        self.assertIn(None, imagenes)
        self.assertTrue(any(imagenes))
        html = self.cliente.get(reverse("core:dashboard") + "?ver=proyecto").content.decode()
        self.assertIn("ws-expediente__foto", html)
        self.assertIn("ws-expediente__hoja", html)
        self.assertEqual(imagen_de_publicacion("proy_graph01"), imagen_de_publicacion("proy_graph01"))

    def test_feed_intercala_los_tipos_y_conserva_todo(self):
        elementos = [{"tipo": t, "n": i} for i, t in enumerate(["proyecto", "proyecto", "oferta", "conexion", "proyecto"])]
        tejido = tejer_feed(elementos)
        self.assertEqual([e["tipo"] for e in tejido], ["proyecto", "oferta", "conexion", "proyecto", "proyecto"])
        self.assertEqual(len(tejido), len(elementos))
        res = self.cliente.get(reverse("core:dashboard"))
        tipos = [item["tipo"] for item in res.context["feed_items"]]
        self.assertEqual(tipos[:3], ["publicacion", "proyecto", "oferta"])

    def test_oferta_marca_las_habilidades_que_ya_tienes(self):
        res = self.cliente.get(reverse("core:dashboard"))
        oferta = next(i for i in res.context["feed_items"] if i["tipo"] == "oferta")
        self.assertEqual(oferta["match_count"], sum(1 for r in oferta["requisitos"] if r["tengo"]))
        self.assertContains(res, "es-tuya")
        self.assertContains(res, "--pct:33.3")

    def test_division_de_inicio_conserva_acciones_y_contactos(self):
        html = self.cliente.get(reverse("core:dashboard")).content.decode()
        # Saludo, publicar y feed comparten la columna que se desplaza; acciones y contactos están fuera
        principal = html.index("ws-inicio__principal")
        self.assertLess(principal, html.index("ws-bienvenida__titulo"))
        self.assertLess(html.index("ws-bienvenida__titulo"), html.index("ws-compositor"))
        self.assertLess(html.index("ws-compositor"), html.index('class="ws-feed"'))
        self.assertLess(html.index('class="ws-feed"'), html.index("ws-inicio__derecha"))
        self.assertLess(html.index("ws-inicio__derecha"), html.index("ws-panel--contactos"))
        self.assertLess(html.index("ws-compositor"), html.index("/proyectos/nuevo/"))

    def test_porcentaje_de_empleos_es_cifra_suelta(self):
        self.assertEqual(cifra_porcentaje(33.3), '<span class="ws-cifra"><b>33</b><small>,3 %</small></span>')
        self.assertEqual(cifra_porcentaje(100.0), '<span class="ws-cifra"><b>100</b><small> %</small></span>')
        html = self.cliente.get(reverse("core:dashboard")).content.decode()
        self.assertIn("ws-cifra", html)
        self.assertNotIn("ws-pastilla--marca", html)

    def test_sin_pestanas_de_color_en_menu_ni_ofertas(self):
        css = open(finders.find("css/wheelson.css"), encoding="utf-8").read()
        self.assertNotIn("border-left: 3px", css)
        self.assertNotIn("inset 3px 0 0", css)

    def test_todos_los_iconos_usados_existen_en_el_sprite(self):
        sprite = open(finders.find("icons/phosphor-sprite.svg"), encoding="utf-8").read()
        for ruta in ["core:dashboard", "core:usuarios_lista"]:
            html = self.cliente.get(reverse(ruta)).content.decode()
            usados = set(re.findall(r'phosphor-sprite\.svg#([a-z-]+)"', html))
            self.assertTrue(usados)
            for icono in usados:
                self.assertIn(f'id="{icono}"', sprite)

    def test_recursos_son_locales(self):
        rutas = ["/", "/analitica/", "/grafo/", "/usuarios/usr_carlos001/", "/proyectos/nuevo/", "/consultas/"]
        for ruta in rutas:
            html = self.cliente.get(ruta).content.decode()
            for externo in ("cdn.jsdelivr.net", "unpkg.com", "dicebear.com", "fonts.googleapis.com"):
                with self.subTest(ruta=ruta, externo=externo):
                    self.assertNotIn(externo, html)
            for recurso in re.findall(r'(?:href|src)="/static/([^"#]+)"', html):
                self.assertTrue(finders.find(recurso), recurso)

    def test_empaquetado_de_estaticos_funciona(self):
        # El almacenamiento de producción falla si un archivo referencia otro que no existe
        with tempfile.TemporaryDirectory() as carpeta, override_settings(
            STATIC_ROOT=carpeta,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
            },
        ):
            staticfiles_storage._wrapped = empty
            try:
                call_command("collectstatic", interactive=False, verbosity=0)
                self.assertTrue(os.path.exists(os.path.join(carpeta, "staticfiles.json")))
            finally:
                staticfiles_storage._wrapped = empty

    def test_acceso_rapido_y_panel_de_cuenta_siguen_funcionando(self):
        res = self.cliente.get(reverse("core:dashboard") + "?as_user=usr_carlos001")
        self.assertEqual(self.cliente.session.get("active_user_uid"), "usr_carlos001")
        self.assertContains(res, "Ver la app como")
        self.assertContains(res, reverse("core:logout"))
        self.assertContains(res, "Ver mi perfil")

    def test_login_no_muestra_barra_ni_campana(self):
        res = ClienteAnonimo().get(reverse("core:login") + "?force=1")
        self.assertNotContains(res, "ws-sidebar\"")
        self.assertNotContains(res, "ws-campana")


class AvisosTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_avisos_salen_de_datos_reales_del_grafo(self):
        avisos = avisos_para("usr_dubal003")
        ids = {a["id"] for a in avisos}
        self.assertIn("postulacion:ofr_dataeng01:enviada", ids)
        self.assertIn("empleo:ofr_arch02", ids)
        self.assertTrue(any(a["tipo"] == "conexion" for a in avisos))
        self.assertLessEqual(len(avisos), MAX_AVISOS)
        # Primero lo que espera una respuesta; dentro de cada grupo, lo más reciente
        self.assertTrue(avisos[0].get("pendiente"))
        fechas = [a["fecha"] for a in avisos if not a.get("pendiente")]
        self.assertEqual(fechas, sorted(fechas, reverse=True))
        self.assertTrue(all(a["fecha_texto"] for a in avisos))

    def test_sin_datos_no_inventa_avisos(self):
        nuevo = UsuarioService.create(nombre="Sin", apellido="Red", email="sinred@test.com")
        self.assertEqual(avisos_para(nuevo.uid), [])
        self.assertEqual(avisos_para(""), [])

    def test_panel_se_dibuja_con_enlaces_validos(self):
        cliente = Client()
        cliente.get(reverse("core:login") + "?quick_login=usr_dubal003")
        res = cliente.get(reverse("core:dashboard"))
        self.assertContains(res, "ws-campana")
        self.assertContains(res, 'data-aviso="postulacion:ofr_dataeng01:enviada"')
        self.assertContains(res, reverse("core:oferta_detalle", kwargs={"oid": "ofr_dataeng01"}))

    def test_usuario_nuevo_ve_estado_vacio(self):
        nuevo = UsuarioService.create(nombre="Sin", apellido="Red", email="sinred@test.com")
        cliente = Client()
        cliente.get(reverse("core:login") + f"?quick_login={nuevo.uid}")
        self.assertContains(cliente.get(reverse("core:usuarios_lista")), "Todavía no hay actividad")


class PaletaCiruelaCoralTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")
        self.cliente = Client()

    def test_paleta_ciruela_y_coral_aplicada(self):
        css = open(finders.find("css/wheelson.css"), encoding="utf-8").read()
        self.assertIn("--primary: #6D1F6B;", css)
        self.assertIn("--accent: #D9483B;", css)
        html = self.cliente.get(reverse("core:dashboard")).content.decode()
        self.assertIn('data-theme="wheelson"', html)
        self.assertIn("css/wheelson-compat.css", html)
        self.assertNotIn("ws-avatar--verde", html)
        self.assertFalse(re.search(r"#00b84c|#2FC774|#00C058", css))

    def test_morado_reservado_para_acciones(self):
        css = open(finders.find("css/wheelson.css"), encoding="utf-8").read()
        for selector in (".ws-avatar--marca", ".ws-nav__item.is-activo", ".ws-cuenta", ".ws-bienvenida__titulo span"):
            regla = re.search(re.escape(selector) + r" \{(.*?)\}", css, re.S).group(1)
            self.assertNotIn("--primary", regla, selector)
            self.assertNotIn("#6D1F6B", regla, selector)

    def test_fotos_del_feed_son_locales_y_tienen_creditos(self):
        for imagen in IMAGENES_FEED:
            self.assertTrue(imagen.endswith(".webp"))
            self.assertTrue(finders.find(imagen), imagen)
        self.assertTrue(finders.find("img/feed/CREDITOS.txt"))
        html = self.cliente.get("/").content.decode()
        self.assertNotIn("images.unsplash.com", html)

    def test_grafo_tiene_color_y_forma_por_tipo_de_nodo(self):
        datos = self.cliente.get(reverse("core:grafo_data_api")).json()
        formas = {nodo["group"]: nodo["shape"] for nodo in datos["nodes"]}
        self.assertEqual(formas, {
            "Usuario": "dot", "Empresa": "square", "Habilidad": "diamond", "Proyecto": "hexagon", "Oferta": "triangle",
        })


def clave_demo(correo):
    """Contraseña de una cuenta de ejemplo, según la lista de scripts/usuarios_demo.md."""
    texto = (SCRIPTS / "usuarios_demo.md").read_text(encoding="utf-8")
    return re.search(re.escape(correo) + r" \| `([^`]+)`", texto).group(1)


class CredencialesTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def _entrar(self, correo, clave):
        cliente = ClienteAnonimo()
        cliente.post(reverse("core:login"), {"email": correo, "password": clave})
        return cliente.session.get("active_user_uid")

    def test_cada_usuario_tiene_su_propia_contrasena(self):
        texto = (SCRIPTS / "usuarios_demo.md").read_text(encoding="utf-8").split("## Red de demostración")[0]
        filas = re.findall(r"\| ([\w.]+@wheelson\.com) \| `([^`]+)`", texto)
        self.assertEqual(len(filas), 15)
        self.assertEqual(len({clave for _, clave in filas}), 15)
        for correo, clave in filas:
            with self.subTest(correo=correo):
                self.assertIsNotNone(self._entrar(correo, clave))

    def test_contrasena_de_otro_no_sirve(self):
        self.assertIsNone(self._entrar("dubal@wheelson.com", clave_demo("carlos@wheelson.com")))

    def test_claves_universales_ya_no_funcionan(self):
        for clave in ("123456", "password", "WheelsOn2026*", "pbkdf2_sha256$hashed"):
            with self.subTest(clave=clave):
                self.assertIsNone(self._entrar("dubal@wheelson.com", clave))

    def test_contrasenas_no_se_guardan_en_texto_plano(self):
        guardadas = [fila[0] for fila in db.cypher_query("MATCH (u:Usuario) RETURN u.password_hash")[0]]
        self.assertTrue(all(h.startswith("pbkdf2_sha256$") for h in guardadas))
        self.assertEqual(len(set(guardadas)), 15)

    def test_hash_invalido_niega_el_acceso_sin_error(self):
        db.cypher_query("MATCH (u:Usuario {uid: 'usr_dubal003'}) SET u.password_hash = 'dañado'")
        self.assertIsNone(self._entrar("dubal@wheelson.com", "dañado"))

    def test_cuenta_nueva_sin_contrasena_no_puede_entrar(self):
        UsuarioService.create(nombre="Sin", apellido="Clave", email="sinclave@test.com")
        self.assertIsNone(self._entrar("sinclave@test.com", "WheelsOn2026*"))

    def test_registro_rechaza_contrasena_debil(self):
        res = ClienteAnonimo().post(reverse("core:registro"), {
            "nombre": "A", "apellido": "B", "email": "debil@test.com",
            "password": "123456", "password_confirm": "123456",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(UsuarioService.get_by_email("debil@test.com"))


class SesionTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_sin_sesion_todo_lleva_al_login(self):
        for ruta in ["/", "/usuarios/", "/usuarios/usr_carlos001/", "/empresas/", "/ofertas/", "/proyectos/", "/analitica/", "/grafo/", "/consultas/", "/conexiones/", "/habilidades/", "/recomendaciones/"]:
            with self.subTest(ruta=ruta):
                res = ClienteAnonimo().get(ruta)
                self.assertEqual(res.status_code, 302)
                self.assertTrue(res["Location"].startswith("/login/"))

    def test_api_del_grafo_sin_sesion_responde_401(self):
        self.assertEqual(ClienteAnonimo().get(reverse("core:grafo_data_api")).status_code, 401)

    def test_sin_sesion_no_se_puede_escribir(self):
        antes = UsuarioService.get("usr_carlos001")
        res = ClienteAnonimo().post("/usuarios/usr_carlos001/eliminar/")
        self.assertEqual(res.status_code, 302)
        self.assertIsNotNone(UsuarioService.get(antes.uid))

    def test_cerrar_sesion_solo_por_post(self):
        cliente = entrar_como("usr_dubal003")
        cliente.get(reverse("core:logout"))
        self.assertEqual(cliente.session.get("active_user_uid"), "usr_dubal003")
        cliente.post(reverse("core:logout"))
        self.assertIsNone(cliente.session.get("active_user_uid"))

    def test_next_no_redirige_a_otros_sitios(self):
        res = ClienteAnonimo().post("/login/?next=https://sitio-malicioso.example/", {
            "email": "dubal@wheelson.com", "password": clave_demo("dubal@wheelson.com"),
        })
        self.assertEqual(res["Location"], "/")

    def test_next_interno_si_funciona(self):
        res = ClienteAnonimo().post("/login/?next=/analitica/", {
            "email": "dubal@wheelson.com", "password": clave_demo("dubal@wheelson.com"),
        })
        self.assertEqual(res["Location"], "/analitica/")

    def test_sesion_de_cuenta_borrada_vuelve_al_login(self):
        cliente = entrar_como("usr_miguel010")
        UsuarioService.delete("usr_miguel010")
        self.assertTrue(cliente.get("/").get("Location", "").startswith("/login/"))

    @override_settings(WHEELSON_MODO_DEMO=False)
    def test_fuera_de_la_demo_no_hay_atajos(self):
        anonimo = ClienteAnonimo()
        anonimo.get("/login/?quick_login=usr_carlos001")
        self.assertIsNone(anonimo.session.get("active_user_uid"))
        self.assertNotContains(ClienteAnonimo().get("/login/"), "Acceso Rápido")

        cliente = entrar_como("usr_dubal003")
        res = cliente.get("/?as_user=usr_wilson008")
        self.assertEqual(cliente.session.get("active_user_uid"), "usr_dubal003")
        self.assertNotContains(res, "Ver la app como")

    def test_en_la_demo_se_conservan_los_atajos(self):
        anonimo = ClienteAnonimo()
        anonimo.get("/login/?quick_login=usr_carlos001")
        self.assertEqual(anonimo.session.get("active_user_uid"), "usr_carlos001")
        res = entrar_como("usr_dubal003").get("/?as_user=usr_carlos001")
        self.assertContains(res, "Hola, <span>Carlos</span>.")


def entrar_como(uid):
    cliente = ClienteAnonimo()
    sesion = cliente.session
    sesion["active_user_uid"] = uid
    sesion.save()
    return cliente


# Datos de ejemplo: Dubal lidera Fintech; Mateo administra Nexus y lidera Motor de Grafos;
# María administra Globant; Luis no administra nada; Wilson es administrador de plataforma.
DUBAL, MATEO, MARIA, LUIS, WILSON = "usr_dubal003", "usr_mateo005", "usr_maria009", "usr_luis004", "usr_wilson008"


class MatrizDePermisosTest(TestCase):
    """Cada fila: quién, qué acción y si el servidor debe permitirla."""

    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def _codigo(self, uid, metodo, ruta, datos=None):
        cliente = entrar_como(uid)
        return getattr(cliente, metodo)(ruta, datos or {}).status_code

    def _comprobar(self, filas):
        for uid, metodo, ruta, datos, permitido in filas:
            with self.subTest(uid=uid, ruta=ruta, metodo=metodo):
                codigo = self._codigo(uid, metodo, ruta, datos)
                if permitido:
                    self.assertNotEqual(codigo, 403)
                else:
                    self.assertEqual(codigo, 403)

    def test_usuarios(self):
        datos = {"nombre": "X", "apellido": "Y", "email": "cambiado@test.com"}
        self._comprobar([
            (LUIS, "get", f"/usuarios/{DUBAL}/editar/", None, False),
            (LUIS, "post", f"/usuarios/{DUBAL}/editar/", datos, False),
            (LUIS, "get", f"/usuarios/{DUBAL}/eliminar/", None, False),
            (LUIS, "post", f"/usuarios/{DUBAL}/eliminar/", None, False),
            (LUIS, "get", "/usuarios/nuevo/", None, False),
            (LUIS, "get", f"/usuarios/{LUIS}/editar/", None, True),
            (LUIS, "get", f"/usuarios/{DUBAL}/", None, True),
            (WILSON, "get", f"/usuarios/{DUBAL}/editar/", None, True),
            (WILSON, "get", "/usuarios/nuevo/", None, True),
        ])
        self.assertEqual(UsuarioService.get(DUBAL).email, "dubal@wheelson.com")

    def test_vinculos_del_perfil(self):
        self._comprobar([
            (LUIS, "post", f"/usuarios/{DUBAL}/habilidades/agregar/", {"hid": "hab_py01"}, False),
            (LUIS, "post", f"/usuarios/{DUBAL}/habilidades/hab_py01/eliminar/", None, False),
            (LUIS, "post", f"/usuarios/{DUBAL}/experiencia/agregar/", {"eid": "emp_nexus01", "cargo": "X"}, False),
            (LUIS, "post", f"/usuarios/{DUBAL}/experiencia/emp_globant03/eliminar/", None, False),
            (DUBAL, "post", f"/usuarios/{DUBAL}/habilidades/agregar/", {"hid": "hab_k8s11"}, True),
            (MARIA, "post", f"/usuarios/{DUBAL}/experiencia/emp_globant03/eliminar/", None, True),
        ])

    def test_empresas(self):
        self._comprobar([
            (DUBAL, "get", "/empresas/emp_nexus01/editar/", None, False),
            (DUBAL, "post", "/empresas/emp_nexus01/eliminar/", None, False),
            (DUBAL, "post", "/empresas/emp_nexus01/transferir/", {"uid": DUBAL}, False),
            (DUBAL, "post", f"/empresas/emp_nexus01/empleos/usr_jose012/responder/", {"accion": "aceptar"}, False),
            (MARIA, "get", "/empresas/emp_nexus01/editar/", None, False),
            (MATEO, "get", "/empresas/emp_nexus01/editar/", None, True),
            (WILSON, "get", "/empresas/emp_nexus01/editar/", None, True),
            (DUBAL, "get", "/empresas/emp_nexus01/", None, True),
        ])
        self.assertEqual([PropiedadService.administrador_de("emp_nexus01").uid], [MATEO])

    def test_proyectos(self):
        self._comprobar([
            (LUIS, "get", "/proyectos/proy_fintech02/editar/", None, False),
            (LUIS, "post", "/proyectos/proy_fintech02/eliminar/", None, False),
            (LUIS, "post", "/proyectos/proy_fintech02/colaboradores/agregar/", {"uid": LUIS}, False),
            (LUIS, "post", f"/proyectos/proy_fintech02/colaboradores/{DUBAL}/eliminar/", None, False),
            (LUIS, "post", "/proyectos/proy_fintech02/transferir/", {"uid": LUIS}, False),
            (DUBAL, "get", "/proyectos/proy_fintech02/editar/", None, True),
            (MATEO, "get", "/proyectos/proy_fintech02/editar/", None, False),
        ])
        self.assertEqual(PropiedadService.lider_de("proy_fintech02").uid, DUBAL)

    def test_ofertas_las_gestiona_su_empresa(self):
        self._comprobar([
            (DUBAL, "get", "/ofertas/ofr_dataeng01/editar/", None, False),
            (DUBAL, "post", "/ofertas/ofr_dataeng01/eliminar/", None, False),
            (DUBAL, "post", "/ofertas/ofr_dataeng01/requisitos/agregar/", {"hid": "hab_k8s11"}, False),
            (DUBAL, "post", "/ofertas/ofr_dataeng01/requisitos/hab_py01/eliminar/", None, False),
            (MARIA, "get", "/ofertas/ofr_dataeng01/editar/", None, False),
            (MATEO, "get", "/ofertas/ofr_dataeng01/editar/", None, True),
            (MATEO, "post", "/ofertas/ofr_dataeng01/empresa/asignar/", {"eid": "emp_globant03"}, False),
            (WILSON, "get", "/ofertas/ofr_dataeng01/editar/", None, True),
        ])
        self.assertEqual(len(RequisitoOfertaService.listar_por_oferta("ofr_dataeng01")), 3)

    def test_habilidades(self):
        self._comprobar([
            (LUIS, "post", "/habilidades/hab_py01/eliminar/", None, False),
            (LUIS, "post", "/habilidades/nueva/", {"nombre": "Rust", "categoria": "tecnica"}, False),
            (MATEO, "post", "/habilidades/nueva/", {"nombre": "Rust", "categoria": "tecnica"}, False),
            (WILSON, "post", "/habilidades/nueva/", {"nombre": "Rust", "categoria": "tecnica"}, True),
        ])
        self.assertIsNotNone(HabilidadService.get("hab_py01"))


class AccionesANombrePropioTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_postularse_ignora_el_candidato_del_formulario(self):
        entrar_como(LUIS).post("/ofertas/ofr_arch02/postular/", {"uid": DUBAL, "carta_presentacion": "Hola"})
        self.assertTrue(PostulacionService.ha_postulado(LUIS, "ofr_arch02"))
        self.assertFalse(PostulacionService.ha_postulado(DUBAL, "ofr_arch02"))

    def test_conectar_ignora_el_origen_del_formulario(self):
        entrar_como(LUIS).post("/conexiones/conectar/", {"uid_origen": "usr_jose012", "uid_destino": "usr_andres015"})
        self.assertEqual(InvitacionService.estado_conexion(LUIS, "usr_andres015"), "enviada")
        self.assertIsNone(InvitacionService.estado_conexion("usr_jose012", "usr_andres015"))

    def test_no_se_puede_desconectar_a_terceros(self):
        res = entrar_como(LUIS).post(f"/conexiones/desconectar/{DUBAL}/usr_carlos001/")
        self.assertEqual(res.status_code, 403)
        self.assertTrue(ConexionService.estan_conectados(DUBAL, "usr_carlos001"))

    def test_quien_administra_la_oferta_no_puede_postularse(self):
        entrar_como(MATEO).post("/ofertas/ofr_dataeng01/postular/")
        self.assertFalse(PostulacionService.ha_postulado(MATEO, "ofr_dataeng01"))

    def test_no_se_puede_postular_a_oferta_cerrada(self):
        OfertaService.update("ofr_arch02", estado="cerrada")
        entrar_como(LUIS).post("/ofertas/ofr_arch02/postular/")
        self.assertFalse(PostulacionService.ha_postulado(LUIS, "ofr_arch02"))

    def test_admin_de_plataforma_tambien_puede_postularse(self):
        entrar_como(WILSON).post("/ofertas/ofr_arch02/postular/")
        self.assertTrue(PostulacionService.ha_postulado(WILSON, "ofr_arch02"))

    def test_retirar_postulacion(self):
        self.assertEqual(entrar_como(LUIS).post(f"/ofertas/ofr_dataeng01/postulaciones/{DUBAL}/eliminar/").status_code, 403)
        entrar_como(DUBAL).post(f"/ofertas/ofr_dataeng01/postulaciones/{DUBAL}/eliminar/")
        self.assertFalse(PostulacionService.ha_postulado(DUBAL, "ofr_dataeng01"))

    def test_candidatos_son_privados(self):
        self.assertNotContains(entrar_como(LUIS).get("/ofertas/ofr_dataeng01/"), "Cuento con experiencia sólida")
        self.assertContains(entrar_como(MATEO).get("/ofertas/ofr_dataeng01/"), "Cuento con experiencia sólida")
        self.assertContains(entrar_como(DUBAL).get("/ofertas/ofr_dataeng01/"), "Cuento con experiencia sólida")

    def test_feed_indica_si_ya_te_postulaste(self):
        self.assertContains(entrar_como(DUBAL).get("/"), "Ya te postulaste")
        self.assertContains(entrar_como(MATEO).get("/"), "Gestionar empleo")


class DuenosTest(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_quien_crea_una_empresa_la_administra(self):
        entrar_como(LUIS).post("/empresas/nueva/", {"nombre": "Luis SAS", "industria": "IT", "tamano": "pequena", "ubicacion": "Cali"})
        empresa = next(e for e in EmpresaService.all() if e.nombre == "Luis SAS")
        self.assertEqual([PropiedadService.administrador_de(empresa.eid).uid], [LUIS])

    def test_quien_crea_un_proyecto_lo_lidera_y_participa(self):
        entrar_como(LUIS).post("/proyectos/nuevo/", {"nombre": "Proyecto Luis", "estado": "activo"})
        proyecto = next(p for p in ProyectoService.all() if p.nombre == "Proyecto Luis")
        self.assertEqual(PropiedadService.lider_de(proyecto.pid).uid, LUIS)
        miembros = [m["usuario"].uid for m in ParticipacionProyectoService.listar_por_proyecto(proyecto.pid)]
        self.assertEqual(miembros, [LUIS])

    def test_publicar_desde_el_inicio_no_crea_un_proyecto(self):
        antes = len(ProyectoService.all())
        entrar_como(LUIS).post("/", {"texto": "Trabajo en algo"})
        self.assertEqual(len(ProyectoService.all()), antes)
        self.assertEqual(PublicacionService.de_usuario(LUIS, LUIS)[0]["publicacion"].texto, "Trabajo en algo")

    def test_oferta_nace_con_su_empresa(self):
        datos = {"titulo": "Oferta M", "modalidad": "remoto", "estado": "abierta", "eid": "emp_nexus01"}
        entrar_como(MATEO).post("/ofertas/nueva/", datos)
        oferta = next(o for o in OfertaService.all() if o.titulo == "Oferta M")
        self.assertEqual(PublicacionOfertaService.obtener_empresa(oferta.oid).eid, "emp_nexus01")

    def test_no_se_puede_publicar_a_nombre_de_empresa_ajena(self):
        datos = {"titulo": "Falsa", "modalidad": "remoto", "estado": "abierta", "eid": "emp_globant03"}
        entrar_como(MATEO).post("/ofertas/nueva/", datos)
        self.assertFalse(any(o.titulo == "Falsa" for o in OfertaService.all()))

    def test_sin_empresa_propia_primero_debe_registrar_una(self):
        res = entrar_como(LUIS).get("/ofertas/nueva/")
        self.assertEqual(res["Location"], reverse("core:empresa_crear"))

    def test_eliminar_empresa_elimina_sus_ofertas(self):
        entrar_como(MATEO).post("/empresas/emp_nexus01/eliminar/")
        self.assertIsNone(EmpresaService.get("emp_nexus01"))
        self.assertIsNone(OfertaService.get("ofr_dataeng01"))
        self.assertIsNotNone(OfertaService.get("ofr_arch02"))

    def test_transferir_empresa_cambia_el_permiso(self):
        carlos = "usr_carlos001"
        entrar_como(MATEO).post("/empresas/emp_nexus01/transferir/", {"uid": carlos})
        self.assertEqual(PropiedadService.administrador_de("emp_nexus01").uid, MATEO)
        entrar_como(carlos).post("/empresas/emp_nexus01/invitacion/responder/", {"accion": "aceptar"})
        self.assertEqual(PropiedadService.administrador_de("emp_nexus01").uid, carlos)
        self.assertEqual(entrar_como(MATEO).get("/empresas/emp_nexus01/editar/").status_code, 403)
        self.assertEqual(entrar_como(carlos).get("/empresas/emp_nexus01/editar/").status_code, 200)

    def test_transferir_proyecto_cambia_el_lider(self):
        andres = "usr_andres015"
        entrar_como(DUBAL).post("/proyectos/proy_fintech02/transferir/", {"uid": andres})
        self.assertEqual(PropiedadService.lider_de("proy_fintech02").uid, DUBAL)
        entrar_como(andres).post("/proyectos/proy_fintech02/invitacion/responder/", {"accion": "aceptar"})
        self.assertEqual(PropiedadService.lider_de("proy_fintech02").uid, andres)

    def test_cuenta_con_recursos_no_se_elimina_sin_transferir(self):
        cliente = entrar_como(MATEO)
        cliente.post(f"/usuarios/{MATEO}/eliminar/")
        self.assertIsNotNone(UsuarioService.get(MATEO))
        self.assertContains(cliente.get(f"/usuarios/{MATEO}/eliminar/"), "Nexus Corp")

    def test_cuenta_sin_recursos_se_elimina_y_cierra_sesion(self):
        cliente = entrar_como(LUIS)
        res = cliente.post(f"/usuarios/{LUIS}/eliminar/")
        self.assertEqual(res["Location"], reverse("core:login"))
        self.assertIsNone(UsuarioService.get(LUIS))
        self.assertIsNone(cliente.session.get("active_user_uid"))

    def test_lider_no_puede_salir_dejando_el_proyecto_sin_dueno(self):
        entrar_como(DUBAL).post(f"/proyectos/proy_fintech02/colaboradores/{DUBAL}/eliminar/")
        miembros = [m["usuario"].uid for m in ParticipacionProyectoService.listar_por_proyecto("proy_fintech02")]
        self.assertIn(DUBAL, miembros)

    def test_colaborador_puede_salir_por_su_cuenta(self):
        entrar_como("usr_andres015").post("/proyectos/proy_fintech02/colaboradores/usr_andres015/eliminar/")
        miembros = [m["usuario"].uid for m in ParticipacionProyectoService.listar_por_proyecto("proy_fintech02")]
        self.assertNotIn("usr_andres015", miembros)

    def test_autor_del_feed_es_el_lider(self):
        res = entrar_como(LUIS).get("/")
        proyecto = next(i for i in res.context["feed_items"] if i["tipo"] == "proyecto" and i["proyecto"].pid == "proy_graph01")
        self.assertEqual(proyecto["autor"].uid, MATEO)


class BotonesCoherentesTest(TestCase):
    """Las pantallas no ofrecen acciones que el servidor rechazaría."""

    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")

    def test_perfil_ajeno_sin_acciones_de_gestion(self):
        html = entrar_como(LUIS).get(f"/usuarios/{DUBAL}/").content.decode()
        for ruta in ("/editar/", "/eliminar/", "habilidades/hab_py01/eliminar", "experiencia/emp_globant03/eliminar"):
            self.assertNotIn(f"/usuarios/{DUBAL}/{ruta}".replace("//", "/"), html)

    def test_perfil_propio_con_acciones(self):
        html = entrar_como(DUBAL).get(f"/usuarios/{DUBAL}/").content.decode()
        self.assertIn(f"/usuarios/{DUBAL}/editar/", html)
        self.assertIn(f"/usuarios/{DUBAL}/eliminar/", html)

    def test_empresa_ajena_y_propia(self):
        ajena = entrar_como(DUBAL).get("/empresas/emp_nexus01/").content.decode()
        self.assertNotIn("/empresas/emp_nexus01/editar/", ajena)
        self.assertNotIn("/empresas/emp_nexus01/transferir/", ajena)
        propia = entrar_como(MATEO).get("/empresas/emp_nexus01/").content.decode()
        self.assertIn("/empresas/emp_nexus01/editar/", propia)
        self.assertIn("/empresas/emp_nexus01/transferir/", propia)

    def test_oferta_ajena_y_propia(self):
        ajena = entrar_como(LUIS).get("/ofertas/ofr_dataeng01/").content.decode()
        self.assertNotIn("/ofertas/ofr_dataeng01/editar/", ajena)
        self.assertIn("Postularme", ajena)
        propia = entrar_como(MATEO).get("/ofertas/ofr_dataeng01/").content.decode()
        self.assertIn("/ofertas/ofr_dataeng01/editar/", propia)
        self.assertNotIn("Postularme", propia)

    def test_listas_solo_muestran_editar_en_lo_propio(self):
        html = entrar_como(LUIS).get("/usuarios/").content.decode()
        self.assertEqual(re.findall(r"/usuarios/([^/]+)/editar/", html), [LUIS])
        html = entrar_como(MATEO).get("/empresas/").content.decode()
        self.assertEqual(re.findall(r"/empresas/([^/]+)/editar/", html), ["emp_nexus01"])

    def test_formularios_no_envian_identidad(self):
        for ruta in (f"/usuarios/{DUBAL}/", "/conexiones/", "/recomendaciones/?tab=contactos", "/recomendaciones/?tab=empleos"):
            with self.subTest(ruta=ruta):
                self.assertNotIn('name="uid_origen"', entrar_como(LUIS).get(ruta).content.decode())
        self.assertNotIn('<select name="uid"', entrar_como(LUIS).get("/ofertas/ofr_arch02/").content.decode().split("Carta de Presentación")[0].split("oferta_postular")[-1])

    def test_vista_de_otro_no_permite_actuar_por_el(self):
        # Las sugerencias son siempre de quien las pide, aunque la dirección diga otra cosa
        self.assertEqual(entrar_como(LUIS).get(f"/recomendaciones/?tab=contactos&uid={DUBAL}").context["uid"], LUIS)
        html = entrar_como(LUIS).get(f"/conexiones/?uid={DUBAL}").content.decode()
        self.assertNotIn("/conexiones/desconectar/", html)

    def test_confirmaciones_de_eliminar_abren_para_su_dueno(self):
        for uid, ruta, texto in [
            (LUIS, f"/usuarios/{LUIS}/eliminar/", "Luis"),
            (MATEO, f"/usuarios/{MATEO}/eliminar/", "Motor de Grafos"),
            (MATEO, "/empresas/emp_nexus01/eliminar/", "Nexus Corp"),
            (DUBAL, "/proyectos/proy_fintech02/eliminar/", "Plataforma Fintech"),
            (MATEO, "/ofertas/ofr_dataeng01/eliminar/", "Data Engineer"),
        ]:
            with self.subTest(ruta=ruta):
                self.assertContains(entrar_como(uid).get(ruta), texto)

    def test_403_tiene_pagina_propia(self):
        res = entrar_como(LUIS).get(f"/usuarios/{DUBAL}/editar/")
        self.assertEqual(res.status_code, 403)
        self.assertContains(res, "No puedes hacer esto", status_code=403)


class _LectorDePagina(HTMLParser):
    """Reúne los enlaces y los formularios POST que una pantalla le ofrece al usuario."""

    def __init__(self, ruta_actual):
        super().__init__()
        self.ruta_actual = ruta_actual
        self.enlaces = set()
        self.formularios = {}  # acción -> datos, o None si la persona debe llenar algún campo
        self._form = None

    def handle_starttag(self, tag, attrs):
        datos = dict(attrs)
        if tag == "a" and datos.get("href"):
            self.enlaces.add(urljoin(self.ruta_actual, datos["href"]).split("#")[0])
        elif tag == "form" and (datos.get("method") or "").lower() == "post":
            self._form = {"accion": urljoin(self.ruta_actual, datos.get("action") or self.ruta_actual), "datos": {}, "completo": True}
        elif self._form is not None:
            if tag in ("select", "textarea") or (tag == "input" and (datos.get("type") != "hidden" or datos.get("value") is None)):
                self._form["completo"] = False
            elif datos.get("name") and tag in ("input", "button") and datos["name"] != "csrfmiddlewaretoken":
                self._form["datos"].setdefault(datos["name"], datos.get("value") or "")

    def handle_endtag(self, tag):
        if tag == "form" and self._form is not None:
            self.formularios.setdefault(self._form["accion"], self._form["datos"] if self._form["completo"] else None)
            self._form = None


class RecorridoCoherenteTest(TestCase):
    """Entra como cada papel y usa todo lo que ve: nada visible puede terminar en 403 ni en error."""

    PAPELES = {"sin recursos": LUIS, "líder": DUBAL, "administra empresa": MATEO, "plataforma": WILSON}
    # Salir o cambiar de identidad cortaría el recorrido; se prueban aparte en SesionTest.
    OMITIR = ("as_user=", "quick_login=", "/static/", "/login/", "/registro/")

    def _recargar(self):
        db.cypher_query("MATCH (n) DETACH DELETE n")
        ejecutar_script_cypher("seed_data.cypher")

    def _recorrer(self, uid):
        cliente = entrar_como(uid)
        pendientes, vistas, formularios, prohibidos = ["/"], set(), {}, []
        while pendientes:
            ruta = pendientes.pop()
            if ruta in vistas:
                continue
            vistas.add(ruta)
            res = cliente.get(ruta, follow=True)
            if res.status_code == 403:
                prohibidos.append(ruta)
                continue
            self.assertEqual(res.status_code, 200, ruta)
            ruta_final = res.request["PATH_INFO"]
            lector = _LectorDePagina(ruta)
            lector.feed(res.content.decode())
            formularios = {**lector.formularios, **formularios}
            for enlace in lector.enlaces:
                if enlace.startswith("/") and not any(o in enlace for o in self.OMITIR) and enlace not in vistas:
                    pendientes.append(enlace)
            self.assertTrue(ruta_final.startswith("/"))
        return vistas, formularios, prohibidos

    def test_nada_visible_termina_en_prohibido(self):
        for papel, uid in self.PAPELES.items():
            with self.subTest(papel=papel):
                self._recargar()
                vistas, formularios, prohibidos = self._recorrer(uid)
                self.assertGreater(len(vistas), 30)
                self.assertEqual(prohibidos, [])
                rechazados, con_error = [], []
                for accion, datos in sorted(formularios.items()):
                    if any(o in accion for o in self.OMITIR):
                        continue
                    self._recargar()
                    res = entrar_como(uid).post(accion, datos or {}, follow=True)
                    if res.status_code == 403:
                        rechazados.append(accion)
                    # Un botón que no pide ningún dato tiene que funcionar a la primera
                    elif datos is not None and res.context and any(m.level_tag == "error" for m in res.context["messages"]):
                        con_error.append(accion)
                self.assertEqual(rechazados, [], f"{len(formularios)} formularios revisados")
                self.assertEqual(con_error, [])


class _ConDatosDeEjemplo(TestCase):
    def setUp(self):
        super().setUp()
        ejecutar_script_cypher("seed_data.cypher")


class CodigoInyectadoTest(_ConDatosDeEjemplo):
    CARGA = "</script><script>window.x=1</script>"

    def test_grafo_y_analitica_no_cierran_su_script(self):
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/editar/", {"nombre": self.CARGA, "apellido": "A", "email": "luis.angel@wheelson.com", "biografia": self.CARGA})
        self.assertEqual(UsuarioService.get(LUIS).biografia, self.CARGA)
        for ruta in ("/grafo/", "/analitica/", f"/usuarios/{LUIS}/"):
            with self.subTest(ruta=ruta):
                self.assertNotIn(self.CARGA, entrar_como(DUBAL).get(ruta).content.decode())

    def test_los_datos_del_grafo_siguen_llegando_completos(self):
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/editar/", {"nombre": "Luis", "apellido": "A", "email": "luis.angel@wheelson.com", "biografia": self.CARGA})
        res = entrar_como(DUBAL).get("/grafo/")
        nodo = next(n for n in res.context["datos_grafo"]["nodes"] if n["id"] == LUIS)
        self.assertEqual(nodo["properties"]["bio"], self.CARGA)

    def test_nombres_nunca_se_escriben_dentro_de_javascript(self):
        nombre = "');window.x=1;//"
        db.cypher_query("MATCH (u:Usuario) WHERE u.uid IN $uids SET u.nombre = $n", {"uids": ["usr_andres015", "usr_carlos001", "usr_jose012"], "n": nombre})
        for uid, ruta in [(DUBAL, "/conexiones/"), (LUIS, "/conexiones/"), (DUBAL, "/proyectos/proy_fintech02/"), (MATEO, "/ofertas/ofr_dataeng01/"), (WILSON, "/habilidades/")]:
            with self.subTest(ruta=ruta):
                html = entrar_como(uid).get(ruta).content.decode()
                self.assertNotIn("confirm(\'", html)
                self.assertNotIn("confirm('", html)
                self.assertNotIn("targetNombre = &#x27;", html)
                self.assertNotIn("targetNombre = '", html)


class PrivacidadDePostulacionesTest(_ConDatosDeEjemplo):
    def _postulaciones_en_grafo(self, uid):
        aristas = entrar_como(uid).get("/grafo/api/data/").json()["edges"]
        return {(a["from"], a["to"]) for a in aristas if a["label"] == "POSTULA_A"}

    def test_cada_quien_ve_solo_lo_que_le_corresponde(self):
        dubal, santiago = (DUBAL, "ofr_dataeng01"), ("usr_santiago011", "ofr_arch02")
        self.assertEqual(self._postulaciones_en_grafo(LUIS), set())
        self.assertEqual(self._postulaciones_en_grafo(DUBAL), {dubal})
        self.assertEqual(self._postulaciones_en_grafo(MATEO), {dubal})
        self.assertEqual(self._postulaciones_en_grafo(MARIA), {santiago})
        self.assertEqual(self._postulaciones_en_grafo(WILSON), {dubal, santiago})

    def test_la_carta_no_llega_a_terceros(self):
        for ruta in ("/grafo/", "/grafo/api/data/"):
            html = entrar_como(LUIS).get(ruta).content.decode()
            self.assertNotIn("carta_presentacion", html)
            self.assertNotIn("Cuento con experiencia sólida", html)

    def test_consultas_no_revelan_postulaciones_ajenas(self):
        candidatos = "/consultas/?tab=candidatos&oid=ofr_dataeng01"
        ruta = f"/consultas/?tab=ruta_oferta&uid1={DUBAL}&oid=ofr_dataeng01"
        self.assertEqual(entrar_como(LUIS).get(candidatos).status_code, 403)
        self.assertContains(entrar_como(MATEO).get(candidatos), "Ya se postuló")
        self.assertNotContains(entrar_como(LUIS).get(ruta), "Ya se postuló")
        self.assertContains(entrar_como(MATEO).get(ruta), "Ya se postuló")

    def test_el_perfil_solo_muestra_postulaciones_a_su_dueno(self):
        self.assertContains(entrar_como(DUBAL).get(f"/usuarios/{DUBAL}/"), "Senior Data Engineer")
        self.assertNotContains(entrar_como(LUIS).get(f"/usuarios/{DUBAL}/"), 'aria-label="Postulaciones"')

    def test_el_grafo_resalta_a_quien_lo_mira(self):
        nodos = {n["id"]: n["size"] for n in entrar_como(LUIS).get("/grafo/api/data/").json()["nodes"]}
        self.assertEqual(nodos[LUIS], 28)
        self.assertLess(nodos[MATEO], 28)


class CuentasTest(_ConDatosDeEjemplo):
    def _editar(self, uid, sesion=None, **datos):
        base = {"nombre": "Luis", "apellido": "A", "email": "luis.angel@wheelson.com"}
        return entrar_como(sesion or uid).post(f"/usuarios/{uid}/editar/", {**base, **datos})

    def test_correo_con_mayusculas_no_deja_a_nadie_afuera(self):
        self._editar(LUIS, email="Luis.Nuevo@Wheelson.com")
        self.assertEqual(UsuarioService.get(LUIS).email, "luis.nuevo@wheelson.com")
        self.assertIsNotNone(UsuarioService.get_by_email("LUIS.NUEVO@wheelson.com"))

    def test_correo_ajeno_en_mayusculas_se_rechaza(self):
        res = self._editar(LUIS, email="DUBAL@wheelson.com")
        self.assertContains(res, "Ya existe un usuario con este correo")
        self.assertEqual(UsuarioService.get(LUIS).email, "luis.angel@wheelson.com")

    def test_registro_guarda_el_correo_en_minusculas(self):
        ClienteAnonimo().post("/registro/", {"nombre": "A", "apellido": "B", "email": "Nueva@Test.com", "password": "ClaveLarga#2026", "password_confirm": "ClaveLarga#2026"})
        self.assertIsNotNone(UsuarioService.get_by_email("nueva@test.com"))

    def test_contrasena_debil_se_rechaza_al_editar_y_al_crear(self):
        clave = clave_demo("luis.angel@wheelson.com")
        self._editar(LUIS, password="1", password_actual=clave)
        self.assertIsNone(UsuarioService.autenticar("luis.angel@wheelson.com", "1"))
        res = entrar_como(WILSON).post("/usuarios/nuevo/", {"nombre": "A", "apellido": "B", "email": "debil@test.com", "password": "123"})
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(UsuarioService.get_by_email("debil@test.com"))

    def test_cambiar_tu_contrasena_exige_la_actual(self):
        clave = clave_demo("luis.angel@wheelson.com")
        for actual in ("", "equivocada"):
            with self.subTest(actual=actual):
                res = self._editar(LUIS, password="ClaveNueva#2026", password_actual=actual)
                self.assertContains(res, "Escribe tu contraseña actual")
                self.assertIsNone(UsuarioService.autenticar("luis.angel@wheelson.com", "ClaveNueva#2026"))
        self._editar(LUIS, password="ClaveNueva#2026", password_actual=clave)
        self.assertIsNotNone(UsuarioService.autenticar("luis.angel@wheelson.com", "ClaveNueva#2026"))

    def test_editar_sin_cambiar_contrasena_no_pide_la_actual(self):
        self.assertEqual(self._editar(LUIS, titulo_profesional="QA").status_code, 302)
        self.assertEqual(UsuarioService.get(LUIS).titulo_profesional, "QA")

    def test_administrador_puede_restablecer_sin_conocer_la_clave(self):
        self._editar(LUIS, sesion=WILSON, password="ClaveNueva#2026")
        self.assertIsNotNone(UsuarioService.autenticar("luis.angel@wheelson.com", "ClaveNueva#2026"))

    def test_el_ultimo_administrador_no_puede_eliminarse(self):
        self.assertNotContains(entrar_como(WILSON).get(f"/usuarios/{WILSON}/eliminar/"), "Confirmar Eliminacion")
        entrar_como(WILSON).post(f"/usuarios/{WILSON}/eliminar/")
        self.assertIsNotNone(UsuarioService.get(WILSON))

    def test_con_otro_administrador_si_puede(self):
        db.cypher_query("MATCH (u:Usuario {uid: $uid}) SET u.rol = 'admin'", {"uid": LUIS})
        entrar_como(WILSON).post(f"/usuarios/{WILSON}/eliminar/")
        self.assertIsNone(UsuarioService.get(WILSON))

    def test_una_publicacion_no_bloquea_eliminar_la_cuenta(self):
        cliente = entrar_como("usr_jose012")
        cliente.post("/", {"texto": "Hola a todos"})
        self.assertContains(cliente.get("/usuarios/usr_jose012/eliminar/"), "sus publicaciones (1)")
        cliente.post("/usuarios/usr_jose012/eliminar/")
        self.assertIsNone(UsuarioService.get("usr_jose012"))
        self.assertEqual(db.cypher_query("MATCH (p:Publicacion {texto: 'Hola a todos'}) RETURN count(p)")[0][0][0], 0)

    def test_proyecto_individual_se_elimina_con_la_cuenta(self):
        cliente = entrar_como("usr_jose012")
        cliente.post("/proyectos/nuevo/", {"nombre": "Solo de Jose", "estado": "activo"})
        self.assertContains(cliente.get("/usuarios/usr_jose012/eliminar/"), "Solo de Jose")
        cliente.post("/usuarios/usr_jose012/eliminar/")
        self.assertIsNone(UsuarioService.get("usr_jose012"))
        self.assertFalse(any(p.nombre == "Solo de Jose" for p in ProyectoService.all()))

    def test_proyecto_con_mas_gente_si_exige_transferir(self):
        entrar_como(DUBAL).post(f"/usuarios/{DUBAL}/eliminar/")
        self.assertIsNotNone(UsuarioService.get(DUBAL))
        self.assertIsNotNone(ProyectoService.get("proy_fintech02"))


class SolicitudesDeConexionTest(_ConDatosDeEjemplo):
    # En los datos de ejemplo, Luis ya le pidió conexión a Dubal
    def _responder(self, sesion, origen, accion):
        return entrar_como(sesion).post(f"/conexiones/solicitudes/{origen}/responder/", {"accion": accion})

    def test_pendiente_no_es_una_conexion(self):
        self.assertFalse(ConexionService.estan_conectados(LUIS, DUBAL))
        self.assertFalse(any(c["usuario"].uid == LUIS for c in ConexionService.listar(DUBAL)))
        aristas = entrar_como(LUIS).get("/grafo/api/data/").json()["edges"]
        self.assertFalse(any(a["label"] == "SOLICITA_CONEXION" for a in aristas))

    def test_aceptar_crea_la_conexion_con_su_mensaje(self):
        self._responder(DUBAL, LUIS, "aceptar")
        self.assertTrue(ConexionService.estan_conectados(LUIS, DUBAL))
        self.assertEqual(next(c for c in ConexionService.listar(DUBAL) if c["usuario"].uid == LUIS)["mensaje"], "Hola Dubal, me gustaria conectar contigo.")
        self.assertIsNone(next((s for s in InvitacionService.solicitudes_recibidas(DUBAL) if s["usuario"].uid == LUIS), None))

    def test_rechazar_no_conecta_y_permite_volver_a_pedir(self):
        self._responder(DUBAL, LUIS, "rechazar")
        self.assertIsNone(InvitacionService.estado_conexion(LUIS, DUBAL))
        self.assertContains(entrar_como(LUIS).get(f"/usuarios/{DUBAL}/"), "Conectar")

    def test_nadie_puede_aceptar_por_otra_persona(self):
        self._responder("usr_jose012", LUIS, "aceptar")
        self._responder(WILSON, LUIS, "aceptar")
        self._responder(LUIS, LUIS, "aceptar")
        self.assertEqual(InvitacionService.estado_conexion(LUIS, DUBAL), "enviada")

    def test_respuesta_invalida_no_cambia_nada(self):
        self._responder(DUBAL, LUIS, "otra")
        self.assertEqual(InvitacionService.estado_conexion(LUIS, DUBAL), "enviada")

    def test_quien_la_envio_puede_cancelarla(self):
        entrar_como(LUIS).post(f"/conexiones/solicitudes/{DUBAL}/cancelar/")
        self.assertIsNone(InvitacionService.estado_conexion(LUIS, DUBAL))

    def test_un_tercero_no_puede_cancelarla(self):
        entrar_como("usr_jose012").post(f"/conexiones/solicitudes/{DUBAL}/cancelar/")
        self.assertEqual(InvitacionService.estado_conexion(LUIS, DUBAL), "enviada")

    def test_si_ambos_lo_piden_quedan_conectados(self):
        entrar_como(DUBAL).post("/conexiones/conectar/", {"uid_destino": LUIS})
        self.assertTrue(ConexionService.estan_conectados(LUIS, DUBAL))

    def test_no_se_duplica(self):
        entrar_como(LUIS).post("/conexiones/conectar/", {"uid_destino": DUBAL})
        self.assertEqual(len([s for s in InvitacionService.solicitudes_recibidas(DUBAL) if s["usuario"].uid == LUIS]), 1)

    def test_el_perfil_muestra_el_estado_correcto(self):
        de_luis = entrar_como(LUIS).get(f"/usuarios/{DUBAL}/").content.decode()
        self.assertIn(f"/conexiones/solicitudes/{DUBAL}/cancelar/", de_luis)
        self.assertNotIn("showConnectModal = true", de_luis)
        de_dubal = entrar_como(DUBAL).get(f"/usuarios/{LUIS}/").content.decode()
        self.assertIn(f"/conexiones/solicitudes/{LUIS}/responder/", de_dubal)
        self.assertNotIn(f"/conexiones/solicitudes/{LUIS}/responder/", entrar_como("usr_jose012").get(f"/usuarios/{LUIS}/").content.decode())

    def test_la_bandeja_y_el_aviso_llegan_a_quien_responde(self):
        self.assertContains(entrar_como(DUBAL).get("/conexiones/"), "quiere conectar contigo")
        self.assertTrue(any(a["id"] == f"solicitud:{LUIS}" for a in avisos_para(DUBAL)))
        self.assertNotContains(entrar_como(LUIS).get(f"/conexiones/?uid={DUBAL}"), "quiere conectar contigo")

    def test_lo_pendiente_no_se_sugiere_otra_vez(self):
        self.assertFalse(any(r["usuario"].uid == LUIS for r in RecommendationEngine.recomendar_contactos(DUBAL, limit=30)))
        self.assertFalse(any(s["usuario"].uid == LUIS for s in entrar_como(DUBAL).get("/conexiones/").context["sugerencias"]))


class InvitacionesATest(_ConDatosDeEjemplo):
    # En los datos de ejemplo, Dubal ya invitó a Luis a Fintech
    FINTECH = "proy_fintech02"

    def _miembros(self):
        return {m["usuario"].uid for m in ParticipacionProyectoService.listar_por_proyecto(self.FINTECH)}

    def test_invitar_no_suma_hasta_aceptar(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/colaboradores/agregar/", {"uid": "usr_jose012", "rol": "QA"})
        self.assertNotIn("usr_jose012", self._miembros())
        entrar_como("usr_jose012").post(f"/proyectos/{self.FINTECH}/invitacion/responder/", {"accion": "aceptar"})
        self.assertIn("usr_jose012", self._miembros())
        rol = next(m["rol"] for m in ParticipacionProyectoService.listar_por_proyecto(self.FINTECH) if m["usuario"].uid == "usr_jose012")
        self.assertEqual(rol, "QA")

    def test_rechazar_no_suma(self):
        entrar_como(LUIS).post(f"/proyectos/{self.FINTECH}/invitacion/responder/", {"accion": "rechazar"})
        self.assertNotIn(LUIS, self._miembros())
        self.assertEqual(InvitacionService.invitaciones_de(LUIS), [])

    def test_sin_invitacion_no_se_puede_entrar_solo(self):
        entrar_como("usr_jose012").post(f"/proyectos/{self.FINTECH}/invitacion/responder/", {"accion": "aceptar"})
        self.assertNotIn("usr_jose012", self._miembros())

    def test_solo_el_lider_cancela(self):
        ruta = f"/proyectos/{self.FINTECH}/invitaciones/{LUIS}/cancelar/"
        self.assertEqual(entrar_como("usr_jose012").post(ruta).status_code, 403)
        self.assertEqual(len(InvitacionService.invitaciones_de(LUIS)), 1)
        entrar_como(DUBAL).post(ruta)
        self.assertEqual(InvitacionService.invitaciones_de(LUIS), [])

    def test_cambiar_rol_de_un_miembro_no_pide_invitacion(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/colaboradores/agregar/", {"uid": "usr_andres015", "rol": "Arquitecto"})
        rol = next(m["rol"] for m in ParticipacionProyectoService.listar_por_proyecto(self.FINTECH) if m["usuario"].uid == "usr_andres015")
        self.assertEqual(rol, "Arquitecto")

    def test_transferencia_no_quita_permisos_hasta_aceptar(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/transferir/", {"uid": "usr_andres015"})
        self.assertEqual(PropiedadService.lider_de(self.FINTECH).uid, DUBAL)
        self.assertEqual(entrar_como("usr_andres015").get(f"/proyectos/{self.FINTECH}/editar/").status_code, 403)
        self.assertEqual(entrar_como(DUBAL).get(f"/proyectos/{self.FINTECH}/editar/").status_code, 200)
        self.assertContains(entrar_como(DUBAL).get(f"/proyectos/{self.FINTECH}/"), "Esperando que")

    def test_transferencia_no_bloquea_la_cuenta_de_quien_no_acepto(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/transferir/", {"uid": "usr_andres015"})
        cliente = entrar_como("usr_andres015")
        cliente.post("/usuarios/usr_andres015/eliminar/")
        self.assertIsNone(UsuarioService.get("usr_andres015"))
        self.assertEqual(PropiedadService.lider_de(self.FINTECH).uid, DUBAL)

    def test_la_bandeja_ofrece_responder(self):
        html = entrar_como(LUIS).get("/conexiones/").content.decode()
        self.assertIn("Te invitaron a colaborar en", html)
        self.assertIn(f"/proyectos/{self.FINTECH}/invitacion/responder/", html)
        self.assertTrue(any(a["id"].startswith("invitacion:colaborar") for a in avisos_para(LUIS)))


class EstadosDePostulacionTest(_ConDatosDeEjemplo):
    RUTA = f"/ofertas/ofr_dataeng01/postulaciones/{DUBAL}/estado/"

    def test_la_empresa_cambia_el_estado(self):
        entrar_como(MATEO).post(self.RUTA, {"estado": "entrevista"})
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, "ofr_dataeng01"), "entrevista")
        self.assertContains(entrar_como(DUBAL).get("/ofertas/ofr_dataeng01/"), "Entrevista")

    def test_nadie_mas_puede_cambiarlo(self):
        for uid in (DUBAL, LUIS, MARIA):
            with self.subTest(uid=uid):
                self.assertEqual(entrar_como(uid).post(self.RUTA, {"estado": "aceptada"}).status_code, 403)
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, "ofr_dataeng01"), "enviada")

    def test_estado_invalido_o_sin_postulacion(self):
        entrar_como(MATEO).post(self.RUTA, {"estado": "hackeado"})
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, "ofr_dataeng01"), "enviada")
        self.assertEqual(entrar_como(MATEO).post(f"/ofertas/ofr_dataeng01/postulaciones/{LUIS}/estado/", {"estado": "aceptada"}).status_code, 302)
        self.assertFalse(PostulacionService.ha_postulado(LUIS, "ofr_dataeng01"))

    def test_el_selector_solo_lo_ve_la_empresa(self):
        self.assertIn(self.RUTA, entrar_como(MATEO).get("/ofertas/ofr_dataeng01/").content.decode())
        self.assertNotIn(self.RUTA, entrar_como(DUBAL).get("/ofertas/ofr_dataeng01/").content.decode())

    def test_la_empresa_ya_no_borra_candidatos(self):
        ruta = f"/ofertas/ofr_dataeng01/postulaciones/{DUBAL}/eliminar/"
        self.assertEqual(entrar_como(MATEO).post(ruta).status_code, 403)
        self.assertNotIn(ruta, entrar_como(MATEO).get("/ofertas/ofr_dataeng01/").content.decode())

    def test_con_decision_ya_no_se_puede_retirar(self):
        ruta = f"/ofertas/ofr_dataeng01/postulaciones/{DUBAL}/eliminar/"
        self.assertIn(ruta, entrar_como(DUBAL).get("/ofertas/ofr_dataeng01/").content.decode())
        entrar_como(MATEO).post(self.RUTA, {"estado": "rechazada"})
        self.assertNotIn(ruta, entrar_como(DUBAL).get("/ofertas/ofr_dataeng01/").content.decode())
        entrar_como(DUBAL).post(ruta)
        self.assertTrue(PostulacionService.ha_postulado(DUBAL, "ofr_dataeng01"))

    def test_cada_cambio_llega_como_aviso_nuevo(self):
        entrar_como(MATEO).post(self.RUTA, {"estado": "aceptada"})
        aviso = next(a for a in avisos_para(DUBAL, limite=50) if a["id"] == "postulacion:ofr_dataeng01:aceptada")
        self.assertIn("Aceptada", aviso["detalle"])

    def test_la_empresa_recibe_aviso_de_postulaciones_nuevas(self):
        titulos = [a["titulo"] for a in avisos_para(MATEO, limite=50)]
        self.assertIn("Nueva postulación a Senior Data Engineer", titulos)
        entrar_como(MATEO).post(self.RUTA, {"estado": "revision"})
        titulos = [a["titulo"] for a in avisos_para(MATEO, limite=50)]
        self.assertNotIn("Nueva postulación a Senior Data Engineer", titulos)


class CoherenciaTest(_ConDatosDeEjemplo):
    def test_una_oferta_nunca_tiene_dos_empresas(self):
        entrar_como(WILSON).post("/ofertas/ofr_dataeng01/empresa/asignar/", {"eid": "emp_globant03"})
        filas = db.cypher_query("MATCH (e:Empresa)-[:PUBLICA]->(:Oferta {oid: 'ofr_dataeng01'}) RETURN e.eid")[0]
        self.assertEqual(filas, [["emp_nexus01"]])
        self.assertEqual(entrar_como(MARIA).get("/ofertas/ofr_dataeng01/editar/").status_code, 403)
        self.assertNotIn("empresa/asignar", entrar_como(WILSON).get("/ofertas/ofr_dataeng01/").content.decode())

    def test_oferta_sin_empresa_si_se_puede_reparar(self):
        db.cypher_query("MATCH (:Empresa)-[r:PUBLICA]->(:Oferta {oid: 'ofr_dataeng01'}) DELETE r")
        self.assertIn("empresa/asignar", entrar_como(WILSON).get("/ofertas/ofr_dataeng01/").content.decode())
        entrar_como(WILSON).post("/ofertas/ofr_dataeng01/empresa/asignar/", {"eid": "emp_globant03"})
        self.assertEqual(PublicacionOfertaService.obtener_empresa("ofr_dataeng01").eid, "emp_globant03")

    def test_confirmar_eliminar_empresa_avisa_todo_lo_que_se_pierde(self):
        html = entrar_como(MATEO).get("/empresas/emp_nexus01/eliminar/").content.decode()
        self.assertIn("1 empleo y 1 postulación", html)
        self.assertIn("5 personas perderán esta experiencia", html)

    def test_confirmar_eliminar_oferta_avisa_las_postulaciones(self):
        self.assertContains(entrar_como(MATEO).get("/ofertas/ofr_dataeng01/eliminar/"), "sus postulaciones (1)")

    def test_no_te_recomienda_tus_propias_ofertas(self):
        for uid, oferta in ((MATEO, "ofr_dataeng01"), (MARIA, "ofr_arch02")):
            with self.subTest(uid=uid):
                self.assertNotIn(oferta, [r["oferta"].oid for r in RecommendationEngine.recomendar_empleos(uid, limit=20)])
                self.assertNotIn(f"/ofertas/{oferta}/postular/", entrar_como(uid).get("/recomendaciones/?tab=empleos").content.decode())
                self.assertNotIn(f"empleo:{oferta}", [a["id"] for a in avisos_para(uid, limite=50)])

    def test_referir_no_aparece_en_tu_propia_empresa(self):
        de_mateo = [i for i in entrar_como(MATEO).get("/").context["feed_items"] if i["tipo"] == "oferta" and i["oferta"].oid == "ofr_dataeng01"][0]
        self.assertTrue(de_mateo["es_propia"])
        self.assertNotIn("tab=ruta_empresa&uid1=" + MATEO + "&eid=emp_nexus01", entrar_como(MATEO).get("/").content.decode().replace("&amp;", "&"))
        self.assertIn("tab=ruta_empresa&uid1=" + LUIS + "&eid=emp_nexus01", entrar_como(LUIS).get("/").content.decode().replace("&amp;", "&"))

    def test_datos_manipulados_no_rompen_la_pagina(self):
        for uid, ruta, datos in [
            (DUBAL, f"/usuarios/{DUBAL}/habilidades/agregar/", {"hid": "hab_k8s11", "anios_experiencia": "abc"}),
            (DUBAL, f"/usuarios/{DUBAL}/habilidades/agregar/", {"hid": "hab_k8s11", "nivel": "hacker"}),
            (DUBAL, f"/usuarios/{DUBAL}/habilidades/agregar/", {"hid": "no-existe"}),
            (DUBAL, f"/usuarios/{DUBAL}/experiencia/agregar/", {"eid": "no-existe", "cargo": "x"}),
            (MATEO, "/ofertas/ofr_dataeng01/requisitos/agregar/", {"hid": "hab_k8s11", "prioridad": "xx"}),
            (MATEO, "/ofertas/ofr_dataeng01/requisitos/agregar/", {"hid": "hab_k8s11", "nivel_minimo": "yy"}),
            (DUBAL, "/proyectos/proy_fintech02/colaboradores/agregar/", {"uid": "no-existe"}),
        ]:
            with self.subTest(ruta=ruta, datos=datos):
                res = entrar_como(uid).post(ruta, datos, follow=True)
                self.assertEqual(res.status_code, 200)
                self.assertTrue(any(m.level_tag == "error" for m in res.context["messages"]))
        self.assertFalse(any(h["habilidad"].hid == "hab_k8s11" for h in HabilidadUsuarioService.listar_por_usuario(DUBAL)))
        self.assertFalse(any(r["habilidad"].hid == "hab_k8s11" for r in RequisitoOfertaService.listar_por_oferta("ofr_dataeng01")))

    def test_rangos_invertidos_se_rechazan(self):
        res = entrar_como(MATEO).post("/ofertas/nueva/", {"titulo": "Mal", "modalidad": "remoto", "estado": "abierta", "eid": "emp_nexus01", "salario_min": 9000, "salario_max": 10})
        self.assertContains(res, "El salario máximo no puede ser menor")
        self.assertFalse(any(o.titulo == "Mal" for o in OfertaService.all()))

        res = entrar_como(DUBAL).post("/proyectos/proy_fintech02/editar/", {"nombre": "F", "estado": "activo", "fecha_inicio": "2026-05-01", "fecha_fin": "2020-01-01"})
        self.assertContains(res, "La fecha de fin no puede ser anterior")
        self.assertNotEqual(ProyectoService.get("proy_fintech02").nombre, "F")

        res = entrar_como(DUBAL).post(f"/usuarios/{DUBAL}/experiencia/agregar/", {"eid": "emp_techin02", "cargo": "x", "fecha_inicio": "2026-05-01", "fecha_fin": "2020-01-01"}, follow=True)
        self.assertContains(res, "La fecha de fin no puede ser anterior")

    def test_salario_solo_con_un_extremo_sigue_valiendo(self):
        entrar_como(MATEO).post("/ofertas/nueva/", {"titulo": "Solo minimo", "modalidad": "remoto", "estado": "abierta", "eid": "emp_nexus01", "salario_min": 9000})
        self.assertTrue(any(o.titulo == "Solo minimo" for o in OfertaService.all()))

    def test_acceso_rapido_muestra_a_todas_las_personas(self):
        res = ClienteAnonimo().get("/login/")
        self.assertEqual(len(res.context["usuarios_demo"]), 15)
        self.assertEqual(len(entrar_como(LUIS).get("/").context["all_users_for_switch"]), 15)


class PublicacionesTest(_ConDatosDeEjemplo):
    PUB = "pub_dubal01"  # de Dubal; Luis, Mateo y Carlos ya la percibieron bien

    def _de(self, uid, pubid=None):
        pubid = pubid or self.PUB
        return next(p for p in PublicacionService.recientes(uid) if p["publicacion"].pubid == pubid)

    def _percibir(self, uid, tipo, pubid=None):
        return entrar_como(uid).post(f"/publicaciones/{pubid or self.PUB}/percibir/", {"tipo": tipo})

    def test_publicar_aparece_primero_en_el_feed(self):
        entrar_como(LUIS).post("/", {"texto": "Novedad de hoy"})
        res = entrar_como(MATEO).get("/")
        publicaciones = [i for i in res.context["feed_items"] if i["tipo"] == "publicacion"]
        self.assertEqual(publicaciones[0]["publicacion"].texto, "Novedad de hoy")
        self.assertEqual(publicaciones[0]["autor"].uid, LUIS)
        self.assertContains(res, "Novedad de hoy")

    def test_publicar_vacio_o_muy_largo_se_rechaza(self):
        for texto in ("   ", "x" * 2001):
            with self.subTest(largo=len(texto)):
                res = entrar_como(LUIS).post("/", {"texto": texto}, follow=True)
                self.assertTrue(any(m.level_tag == "error" for m in res.context["messages"]))
        self.assertEqual(PublicacionService.de_usuario(LUIS, LUIS), [])

    def test_la_publicacion_no_es_un_proyecto(self):
        entrar_como(LUIS).post("/", {"texto": "Solo una idea"})
        self.assertNotContains(entrar_como(LUIS).get("/proyectos/"), "Solo una idea")

    def test_conteos_y_porcentaje(self):
        self._percibir("usr_jose012", "mala")
        p = self._de(LUIS)
        self.assertEqual((p["buenas"], p["malas"], p["total"], p["pct_buena"]), (3, 1, 4, 75))
        self.assertEqual(p["mi_percepcion"], "buena")

    def test_una_sola_opinion_por_persona(self):
        self._percibir("usr_jose012", "buena")
        self._percibir("usr_jose012", "mala")
        p = self._de("usr_jose012")
        self.assertEqual((p["buenas"], p["malas"], p["mi_percepcion"]), (3, 1, "mala"))

    def test_elegir_lo_mismo_retira_la_opinion(self):
        self._percibir(LUIS, "buena")
        p = self._de(LUIS)
        self.assertEqual((p["buenas"], p["mi_percepcion"]), (2, None))

    def test_nadie_opina_sobre_lo_propio(self):
        self._percibir(DUBAL, "buena")
        self.assertEqual(self._de(DUBAL)["buenas"], 3)
        html = entrar_como(DUBAL).get("/").content.decode()
        self.assertNotIn(f"/publicaciones/{self.PUB}/percibir/", html)

    def test_percepcion_invalida_se_rechaza(self):
        res = entrar_como("usr_jose012").post(f"/publicaciones/{self.PUB}/percibir/", {"tipo": "regular"}, follow=True)
        self.assertTrue(any(m.level_tag == "error" for m in res.context["messages"]))
        self.assertEqual(self._de(LUIS)["total"], 3)

    def test_vuelve_al_mismo_lugar_del_feed(self):
        res = entrar_como(LUIS).post(f"/publicaciones/{self.PUB}/percibir/", {"tipo": "mala"}, HTTP_REFERER="http://testserver/")
        self.assertEqual(res["Location"], f"http://testserver/#pub-{self.PUB}")

    def test_solo_el_autor_y_el_administrador_eliminan(self):
        ruta = f"/publicaciones/{self.PUB}/eliminar/"
        self.assertEqual(entrar_como(LUIS).post(ruta).status_code, 403)
        self.assertNotIn(ruta, entrar_como(LUIS).get("/").content.decode())
        self.assertIn(ruta, entrar_como(DUBAL).get("/").content.decode())
        entrar_como(WILSON).post(ruta)
        self.assertFalse(any(p["publicacion"].pubid == self.PUB for p in PublicacionService.recientes(LUIS)))

    def test_el_perfil_muestra_sus_publicaciones(self):
        self.assertContains(entrar_como(LUIS).get(f"/usuarios/{DUBAL}/"), "rutas de referidos")
        self.assertNotContains(entrar_como(LUIS).get(f"/usuarios/{MATEO}/"), 'aria-label="Publicaciones"')

    def test_el_texto_no_se_ejecuta(self):
        entrar_como(LUIS).post("/", {"texto": "<script>window.x=1</script>"})
        html = entrar_como(MATEO).get("/").content.decode()
        self.assertNotIn("<script>window.x=1</script>", html)
        self.assertIn("&lt;script&gt;window.x=1", html)

    def test_las_publicaciones_no_entran_al_grafo_de_la_red(self):
        datos = entrar_como(LUIS).get("/grafo/api/data/").json()
        self.assertFalse(any(n["id"] == self.PUB for n in datos["nodes"]))


class AvancesTest(_ConDatosDeEjemplo):
    FINTECH = "proy_fintech02"

    def test_el_lider_agrega_avance_y_cambia_el_estado(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/avances/agregar/", {"texto": "Entregamos la primera versión", "estado": "pausado"})
        self.assertEqual(ProyectoService.get(self.FINTECH).estado, "pausado")
        avance = AvanceService.de_proyecto(self.FINTECH)[0]
        self.assertEqual((avance["avance"].texto, avance["estado_texto"], avance["autor"].uid), ("Entregamos la primera versión", "Pausado", DUBAL))
        self.assertContains(entrar_como(LUIS).get(f"/proyectos/{self.FINTECH}/"), "Entregamos la primera versión")

    def test_solo_quien_lidera_registra_o_elimina(self):
        agregar = f"/proyectos/{self.FINTECH}/avances/agregar/"
        eliminar = f"/proyectos/{self.FINTECH}/avances/av_fintech01/eliminar/"
        for uid in (LUIS, "usr_andres015"):
            with self.subTest(uid=uid):
                self.assertEqual(entrar_como(uid).post(agregar, {"texto": "x", "estado": "activo"}).status_code, 403)
                self.assertEqual(entrar_como(uid).post(eliminar).status_code, 403)
                html = entrar_como(uid).get(f"/proyectos/{self.FINTECH}/").content.decode()
                self.assertNotIn(agregar, html)
                self.assertNotIn(eliminar, html)
        self.assertEqual(entrar_como(WILSON).post(agregar, {"texto": "Revisado", "estado": "activo"}).status_code, 302)

    def test_la_edicion_ofrece_agregar_avance(self):
        res = entrar_como(DUBAL).get(f"/proyectos/{self.FINTECH}/editar/")
        self.assertContains(res, "Agregar avance")
        self.assertContains(res, f"/proyectos/{self.FINTECH}/avances/agregar/")
        self.assertNotContains(entrar_como(DUBAL).get("/proyectos/nuevo/"), "Agregar avance")

    def test_datos_invalidos_no_guardan_nada(self):
        antes = len(AvanceService.de_proyecto(self.FINTECH))
        for datos in ({"texto": "", "estado": "activo"}, {"texto": "x", "estado": "inventado"}, {"texto": "x" * 1001, "estado": "activo"}):
            with self.subTest(datos=str(datos)[:30]):
                res = entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/avances/agregar/", datos, follow=True)
                self.assertTrue(any(m.level_tag == "error" for m in res.context["messages"]))
        self.assertEqual(len(AvanceService.de_proyecto(self.FINTECH)), antes)
        self.assertEqual(ProyectoService.get(self.FINTECH).estado, "activo")

    def test_no_se_elimina_un_avance_de_otro_proyecto(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/avances/av_graph01/eliminar/")
        self.assertEqual(AvanceService.proyecto_de("av_graph01"), "proy_graph01")

    def test_aparece_en_el_feed(self):
        self.assertContains(entrar_como(LUIS).get("/"), "ws-hito--avance")

    def test_eliminar_el_proyecto_elimina_sus_avances(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/eliminar/")
        self.assertEqual(db.cypher_query("MATCH (a:Avance {aid: 'av_fintech01'}) RETURN count(a)")[0][0][0], 0)

    def test_el_avance_sobrevive_si_su_autor_se_va(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/avances/agregar/", {"texto": "Hecho por Dubal", "estado": "activo"})
        db.cypher_query("MATCH (:Usuario {uid: $uid})-[r:REGISTRA]->() DELETE r", {"uid": DUBAL})
        self.assertIsNone(AvanceService.de_proyecto(self.FINTECH)[0]["autor"])
        self.assertEqual(entrar_como(LUIS).get("/").status_code, 200)
        self.assertEqual(entrar_como(LUIS).get(f"/proyectos/{self.FINTECH}/").status_code, 200)


class UnirseAProyectoTest(_ConDatosDeEjemplo):
    # En los datos de ejemplo, José ya pidió unirse a Recomendador (lo lidera Carlos)
    TALENTO, CARLOS = "proy_talento03", "usr_carlos001"

    def _miembros(self, pid=None):
        return {m["usuario"].uid for m in ParticipacionProyectoService.listar_por_proyecto(pid or self.TALENTO)}

    def test_pedir_no_suma_hasta_que_acepten(self):
        html = entrar_como(MARIA).get("/proyectos/proy_fintech02/").content.decode()
        self.assertIn("/proyectos/proy_fintech02/unirse/", html)
        entrar_como(MARIA).post("/proyectos/proy_fintech02/unirse/")
        self.assertNotIn(MARIA, self._miembros("proy_fintech02"))
        self.assertEqual(InvitacionService.estado_union(MARIA, "proy_fintech02"), "solicitada")
        self.assertContains(entrar_como(MARIA).get("/proyectos/proy_fintech02/"), "Pediste unirte")

    def test_el_lider_acepta(self):
        entrar_como(self.CARLOS).post(f"/proyectos/{self.TALENTO}/solicitudes/usr_jose012/responder/", {"accion": "aceptar"})
        self.assertIn("usr_jose012", self._miembros())
        self.assertIsNone(next((s for s in InvitacionService.solicitudes_union_de_proyecto(self.TALENTO)), None))

    def test_el_lider_rechaza(self):
        entrar_como(self.CARLOS).post(f"/proyectos/{self.TALENTO}/solicitudes/usr_jose012/responder/", {"accion": "rechazar"})
        self.assertNotIn("usr_jose012", self._miembros())
        self.assertIsNone(InvitacionService.estado_union("usr_jose012", self.TALENTO))

    def test_nadie_mas_puede_aceptar_ni_el_mismo(self):
        ruta = f"/proyectos/{self.TALENTO}/solicitudes/usr_jose012/responder/"
        for uid in ("usr_jose012", LUIS, DUBAL):
            with self.subTest(uid=uid):
                self.assertEqual(entrar_como(uid).post(ruta, {"accion": "aceptar"}).status_code, 403)
        self.assertNotIn("usr_jose012", self._miembros())

    def test_el_solicitante_puede_cancelar(self):
        entrar_como("usr_jose012").post(f"/proyectos/{self.TALENTO}/unirse/cancelar/")
        self.assertIsNone(InvitacionService.estado_union("usr_jose012", self.TALENTO))

    def test_miembros_no_ven_el_boton(self):
        self.assertNotIn(f"/proyectos/{self.TALENTO}/unirse/", entrar_como(self.CARLOS).get(f"/proyectos/{self.TALENTO}/").content.decode())

    def test_proyecto_terminado_no_recibe_solicitudes(self):
        ProyectoService.update("proy_fintech02", estado="completado")
        self.assertNotIn("/proyectos/proy_fintech02/unirse/", entrar_como(MARIA).get("/proyectos/proy_fintech02/").content.decode())
        entrar_como(MARIA).post("/proyectos/proy_fintech02/unirse/")
        self.assertIsNone(InvitacionService.estado_union(MARIA, "proy_fintech02"))

    def test_si_ya_estaba_invitado_entra_directo(self):
        entrar_como(LUIS).post("/proyectos/proy_fintech02/unirse/")
        self.assertIn(LUIS, self._miembros("proy_fintech02"))

    def test_si_ya_lo_habia_pedido_invitarlo_lo_suma(self):
        entrar_como(self.CARLOS).post(f"/proyectos/{self.TALENTO}/colaboradores/agregar/", {"uid": "usr_jose012", "rol": "QA"})
        self.assertIn("usr_jose012", self._miembros())
        self.assertEqual(InvitacionService.invitaciones_de("usr_jose012"), [])

    def test_quien_lidera_recibe_el_aviso_y_lo_ve_en_su_bandeja(self):
        self.assertTrue(any(a["id"] == f"union:{self.TALENTO}:usr_jose012" for a in avisos_para(self.CARLOS)))
        self.assertContains(entrar_como(self.CARLOS).get("/conexiones/"), "quiere unirse a")
        self.assertContains(entrar_como(self.CARLOS).get(f"/proyectos/{self.TALENTO}/"), "Quieren unirse al proyecto")
        self.assertContains(entrar_como("usr_jose012").get("/conexiones/"), "Pediste unirte a")

    def test_la_invitacion_tambien_se_responde_en_el_proyecto(self):
        res = entrar_como(LUIS).get("/proyectos/proy_fintech02/")
        self.assertContains(res, "/proyectos/proy_fintech02/invitacion/responder/")


class SugerenciasPrivadasTest(_ConDatosDeEjemplo):
    def test_empleos_y_contactos_siempre_son_tuyos(self):
        for tab in ("empleos", "contactos"):
            with self.subTest(tab=tab):
                res = entrar_como(LUIS).get(f"/recomendaciones/?tab={tab}&uid={DUBAL}")
                self.assertEqual(res.context["uid"], LUIS)
                self.assertNotContains(res, 'name="uid"')

    def test_ni_el_administrador_ve_las_de_otro(self):
        self.assertEqual(entrar_como(WILSON).get(f"/recomendaciones/?tab=empleos&uid={DUBAL}").context["uid"], WILSON)

    def test_talento_solo_para_quien_administra_la_empresa(self):
        self.assertEqual(entrar_como(LUIS).get("/recomendaciones/?tab=talento&eid=emp_nexus01").status_code, 403)
        self.assertEqual(entrar_como(MARIA).get("/recomendaciones/?tab=talento&eid=emp_nexus01").status_code, 403)
        self.assertEqual(entrar_como(MATEO).get("/recomendaciones/?tab=talento&eid=emp_nexus01").status_code, 200)
        self.assertEqual(entrar_como(WILSON).get("/recomendaciones/?tab=talento&eid=emp_nexus01").status_code, 200)

    def test_colaboradores_solo_para_quien_lidera(self):
        self.assertEqual(entrar_como(LUIS).get("/recomendaciones/?tab=colaboradores&pid=proy_fintech02").status_code, 403)
        self.assertEqual(entrar_como(DUBAL).get("/recomendaciones/?tab=colaboradores&pid=proy_fintech02").status_code, 200)

    def test_los_selectores_solo_ofrecen_lo_tuyo(self):
        res = entrar_como(MATEO).get("/recomendaciones/?tab=talento")
        self.assertEqual([e.eid for e in res.context["empresas"]], ["emp_nexus01"])
        self.assertEqual(res.context["eid"], "emp_nexus01")

    def test_sin_empresa_ni_proyecto_no_se_ofrecen_esas_pestanas(self):
        html = entrar_como("usr_jose012").get("/recomendaciones/").content.decode()
        self.assertNotIn("tab=talento", html)
        self.assertNotIn("tab=colaboradores", html)
        self.assertContains(entrar_como("usr_jose012").get("/recomendaciones/?tab=talento"), "quien administra una empresa")
        self.assertContains(entrar_como("usr_jose012").get("/recomendaciones/?tab=colaboradores"), "quien lidera un proyecto")

    def test_candidatos_de_consultas_solo_para_la_empresa(self):
        self.assertEqual(entrar_como(LUIS).get("/consultas/?tab=candidatos&oid=ofr_dataeng01").status_code, 403)
        self.assertEqual(entrar_como(MARIA).get("/consultas/?tab=candidatos&oid=ofr_dataeng01").status_code, 403)
        self.assertEqual(entrar_como(MATEO).get("/consultas/?tab=candidatos&oid=ofr_dataeng01").status_code, 200)
        self.assertEqual([o.oid for o in entrar_como(MATEO).get("/consultas/?tab=candidatos").context["ofertas_gestionadas"]], ["ofr_dataeng01"])
        self.assertNotIn("tab=candidatos", entrar_como(LUIS).get("/consultas/").content.decode())
        self.assertContains(entrar_como(LUIS).get("/consultas/?tab=candidatos"), "la empresa que publica la oferta")

    def test_el_correo_sigue_siendo_visible(self):
        self.assertContains(entrar_como(LUIS).get(f"/usuarios/{DUBAL}/"), "dubal@wheelson.com")


class FechasDeProyectoTest(_ConDatosDeEjemplo):
    def test_editar_muestra_las_fechas_que_ya_tiene(self):
        html = entrar_como(DUBAL).get("/proyectos/proy_fintech02/editar/").content.decode()
        self.assertRegex(html, r'name="fecha_inicio" value="2026-09-01"|value="2026-09-01"[^>]*name="fecha_inicio"')

    def test_proyecto_pausado_no_dice_que_sigue_en_desarrollo(self):
        self.assertContains(entrar_como(LUIS).get("/proyectos/proy_fintech02/"), "En desarrollo activo")
        ProyectoService.update("proy_fintech02", estado="pausado")
        res = entrar_como(LUIS).get("/proyectos/proy_fintech02/")
        self.assertNotContains(res, "En desarrollo activo")
        self.assertContains(res, "Sin fecha definida")


class EmpleosConAprobacionTest(_ConDatosDeEjemplo):
    # En los datos de ejemplo, José pidió confirmar un empleo en Nexus (la administra Mateo)
    NEXUS = "emp_nexus01"
    JOSE = "usr_jose012"

    def _en_empresa(self, uid, eid=None):
        return any(e["usuario"].uid == uid for e in EmpleoService.listar_por_empresa(eid or self.NEXUS))

    def _responder(self, sesion, accion, uid=None):
        return entrar_como(sesion).post(f"/empresas/{self.NEXUS}/empleos/{uid or self.JOSE}/responder/", {"accion": accion})

    def test_declararse_ceo_no_aparece_en_la_empresa(self):
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/experiencia/agregar/", {"eid": self.NEXUS, "cargo": "CEO", "actual": "on"})
        self.assertFalse(self._en_empresa(LUIS))
        self.assertNotContains(entrar_como(DUBAL).get(f"/empresas/{self.NEXUS}/"), "CEO")
        self.assertFalse(any(e["empresa"].eid == self.NEXUS for e in EmpleoService.listar_por_usuario(LUIS)))
        self.assertEqual(db.cypher_query("MATCH (:Usuario {uid: $u})-[r:TRABAJA_EN]->(:Empresa {eid: $e}) RETURN count(r)", {"u": LUIS, "e": self.NEXUS})[0][0][0], 0)

    def test_pendiente_no_influye_en_referidos(self):
        # José tiene pendiente Nexus: no debe contar como contacto dentro de la empresa
        rutas = GraphAnalyticsService.ruta_usuario_empresa(self.JOSE, self.NEXUS)
        self.assertNotEqual(rutas.get("longitud"), 1)

    def test_la_empresa_confirma_y_entonces_aparece(self):
        self._responder(MATEO, "aceptar")
        self.assertTrue(self._en_empresa(self.JOSE))
        cargo = next(e["cargo"] for e in EmpleoService.listar_por_usuario(self.JOSE) if e["empresa"].eid == self.NEXUS)
        self.assertEqual(cargo, "QA Engineer")
        self.assertEqual(EmpleoService.solicitudes_de_usuario(self.JOSE), [])

    def test_la_empresa_rechaza(self):
        self._responder(MATEO, "rechazar")
        self.assertFalse(self._en_empresa(self.JOSE))
        self.assertEqual(EmpleoService.solicitudes_de_empresa(self.NEXUS), [])

    def test_nadie_mas_confirma_ni_el_interesado(self):
        for uid in (self.JOSE, LUIS, MARIA):
            with self.subTest(uid=uid):
                self.assertEqual(self._responder(uid, "aceptar").status_code, 403)
        self.assertFalse(self._en_empresa(self.JOSE))

    def test_el_administrador_de_plataforma_tambien_puede(self):
        self._responder(WILSON, "aceptar")
        self.assertTrue(self._en_empresa(self.JOSE))

    def test_respuesta_invalida_no_cambia_nada(self):
        self._responder(MATEO, "otra")
        self.assertFalse(self._en_empresa(self.JOSE))
        self.assertEqual(len(EmpleoService.solicitudes_de_empresa(self.NEXUS)), 1)

    def test_cancelar_la_propia_solicitud(self):
        ruta = f"/usuarios/{self.JOSE}/experiencia/{self.NEXUS}/cancelar/"
        self.assertEqual(entrar_como(LUIS).post(ruta).status_code, 403)
        entrar_como(self.JOSE).post(ruta)
        self.assertEqual(EmpleoService.solicitudes_de_usuario(self.JOSE), [])

    def test_solo_la_persona_ve_lo_pendiente_en_su_perfil(self):
        self.assertContains(entrar_como(self.JOSE).get(f"/usuarios/{self.JOSE}/"), "Empleos por confirmar")
        self.assertNotContains(entrar_como(LUIS).get(f"/usuarios/{self.JOSE}/"), "Empleos por confirmar")

    def test_la_empresa_lo_recibe_en_gestion_avisos_y_mi_red(self):
        self.assertContains(entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/"), "dice que trabaja aquí como")
        self.assertNotContains(entrar_como(DUBAL).get(f"/empresas/{self.NEXUS}/"), "dice que trabaja aquí como")
        self.assertTrue(any(a["id"].startswith("empleo-pendiente:") for a in avisos_para(MATEO)))
        self.assertContains(entrar_como(MATEO).get("/conexiones/"), "dice que trabaja como")
        self.assertContains(entrar_como(MATEO).get("/"), f"/empresas/{self.NEXUS}/?tab=gestion")

    def test_quien_administra_no_se_lo_pide_a_si_mismo(self):
        entrar_como(MATEO).post(f"/usuarios/{MATEO}/experiencia/agregar/", {"eid": self.NEXUS, "cargo": "Director", "actual": "on"})
        self.assertEqual(next(e["cargo"] for e in EmpleoService.listar_por_usuario(MATEO) if e["empresa"].eid == self.NEXUS), "Director")

    def test_pedir_otro_cargo_no_borra_el_confirmado(self):
        actual = next(e["cargo"] for e in EmpleoService.listar_por_usuario("usr_carlos001") if e["empresa"].eid == self.NEXUS)
        entrar_como("usr_carlos001").post("/usuarios/usr_carlos001/experiencia/agregar/", {"eid": self.NEXUS, "cargo": "CEO"})
        self.assertEqual(next(e["cargo"] for e in EmpleoService.listar_por_usuario("usr_carlos001") if e["empresa"].eid == self.NEXUS), actual)

    def test_la_empresa_sigue_pudiendo_quitar_un_empleo(self):
        entrar_como(MATEO).post(f"/usuarios/usr_carlos001/experiencia/{self.NEXUS}/eliminar/")
        self.assertFalse(self._en_empresa("usr_carlos001"))


class PublicarComoEmpresaTest(_ConDatosDeEjemplo):
    NEXUS = "emp_nexus01"
    PUB = "pub_nexus04"

    def _de_empresa(self, uid=LUIS):
        return PublicacionService.de_empresa(self.NEXUS, uid)

    def test_el_administrador_publica_a_nombre_de_la_empresa(self):
        entrar_como(MATEO).post("/", {"texto": "Nueva sede", "como": self.NEXUS})
        p = self._de_empresa()[0]
        self.assertEqual((p["publicacion"].texto, p["empresa"].eid, p["autor"]), ("Nueva sede", self.NEXUS, None))
        self.assertEqual(db.cypher_query("MATCH (u:Usuario)-[:REDACTA]->(:Publicacion {texto: 'Nueva sede'}) RETURN u.uid")[0][0][0], MATEO)

    def test_nadie_mas_publica_a_su_nombre(self):
        res = entrar_como(LUIS).post("/", {"texto": "Falsa", "como": self.NEXUS})
        self.assertEqual(res.status_code, 403)
        self.assertEqual(entrar_como(MARIA).post("/", {"texto": "Falsa", "como": self.NEXUS}).status_code, 403)
        self.assertFalse(any(p["publicacion"].texto == "Falsa" for p in self._de_empresa()))

    def test_el_compositor_solo_ofrece_tus_empresas(self):
        html = entrar_como(MATEO).get("/").content.decode()
        self.assertIn('name="como"', html)
        self.assertIn(f'value="{self.NEXUS}"', html)
        self.assertNotIn('name="como"', entrar_como(LUIS).get("/").content.decode())

    def test_el_feed_y_la_empresa_la_muestran(self):
        res = entrar_como(LUIS).get("/?ver=publicacion&pagina=10")
        item = next(i for i in res.context["feed_items"] if i["tipo"] == "publicacion" and i["publicacion"].pubid == self.PUB)
        self.assertEqual(item["empresa"].eid, self.NEXUS)
        self.assertContains(entrar_como(LUIS).get(f"/empresas/{self.NEXUS}/"), "ampliando el equipo de datos")
        self.assertNotContains(entrar_como(LUIS).get(f"/usuarios/{MATEO}/"), "ampliando el equipo de datos")

    def test_la_empresa_no_opina_sobre_lo_suyo(self):
        entrar_como(MATEO).post(f"/publicaciones/{self.PUB}/percibir/", {"tipo": "buena"})
        self.assertEqual(self._de_empresa()[0]["buenas"], 1)
        self.assertTrue(self._de_empresa(MATEO)[0]["es_mia"])
        self.assertFalse(self._de_empresa(DUBAL)[0]["es_mia"])
        entrar_como(DUBAL).post(f"/publicaciones/{self.PUB}/percibir/", {"tipo": "buena"})
        self.assertEqual(self._de_empresa()[0]["buenas"], 2)

    def test_solo_sus_administradores_la_eliminan(self):
        ruta = f"/publicaciones/{self.PUB}/eliminar/"
        self.assertEqual(entrar_como(LUIS).post(ruta).status_code, 403)
        entrar_como(MATEO).post(ruta)
        self.assertEqual(self._de_empresa(), [])

    def test_si_quien_la_escribio_se_va_la_publicacion_queda(self):
        db.cypher_query("MATCH (:Usuario {uid: $u})-[r:REDACTA]->() DELETE r", {"u": MATEO})
        self.assertEqual(len(self._de_empresa()), 1)
        self.assertEqual(entrar_como(LUIS).get("/").status_code, 200)

    def test_eliminar_la_empresa_elimina_sus_publicaciones(self):
        self.assertContains(entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/eliminar/"), "sus publicaciones (1)")
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/eliminar/")
        self.assertEqual(db.cypher_query("MATCH (p:Publicacion {pubid: 'pub_nexus04'}) RETURN count(p)")[0][0][0], 0)


class TransferirSoloAMiembrosTest(_ConDatosDeEjemplo):
    NEXUS, FINTECH = "emp_nexus01", "proy_fintech02"
    CARLOS, ANDRES = "usr_carlos001", "usr_andres015"

    def _proponer_empresa(self, uid, sesion=MATEO):
        return entrar_como(sesion).post(f"/empresas/{self.NEXUS}/transferir/", {"uid": uid}, follow=True)

    def test_empresa_solo_a_sus_empleados(self):
        res = self._proponer_empresa(DUBAL)
        self.assertContains(res, "Solo puedes transferirla a un miembro")
        self.assertIsNone(InvitacionService.pendiente_de_empresa(self.NEXUS))
        self._proponer_empresa(self.CARLOS)
        self.assertEqual(InvitacionService.pendiente_de_empresa(self.NEXUS).uid, self.CARLOS)

    def test_proyecto_solo_a_sus_miembros(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/transferir/", {"uid": MATEO})
        self.assertEqual(InvitacionService.tipo_invitacion_proyecto(MATEO, self.FINTECH), None)
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/transferir/", {"uid": self.ANDRES})
        self.assertEqual(InvitacionService.tipo_invitacion_proyecto(self.ANDRES, self.FINTECH), "liderar")

    def test_la_lista_solo_ofrece_miembros(self):
        empresa = entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/").context["candidatos_transferencia"]
        self.assertIn(self.CARLOS, {u.uid for u in empresa})
        self.assertNotIn(MATEO, {u.uid for u in empresa})
        self.assertNotIn(DUBAL, {u.uid for u in empresa})
        proyecto = entrar_como(DUBAL).get(f"/proyectos/{self.FINTECH}/").context["candidatos_transferencia"]
        self.assertEqual([u.uid for u in proyecto], [self.ANDRES])

    def test_empleo_historico_no_cuenta_como_miembro(self):
        EmpleoService.vincular(self.CARLOS, self.NEXUS, cargo="Ex", actual=False)
        self.assertContains(self._proponer_empresa(self.CARLOS), "Solo puedes transferirla a un miembro")

    def test_sin_miembros_lo_explica(self):
        cliente = entrar_como("usr_jose012")
        cliente.post("/empresas/nueva/", {"nombre": "Sola", "industria": "IT", "tamano": "pequena"})
        empresa = next(e for e in EmpresaService.all() if e.nombre == "Sola")
        self.assertContains(cliente.get(f"/empresas/{empresa.eid}/"), "primero debe haber otros empleados")

    def test_rechazar_deja_todo_igual(self):
        self._proponer_empresa(self.CARLOS)
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/invitacion/responder/", {"accion": "rechazar"})
        self.assertEqual(PropiedadService.administrador_de(self.NEXUS).uid, MATEO)
        self.assertIsNone(InvitacionService.pendiente_de_empresa(self.NEXUS))

    def test_cancelar_solo_quien_administra(self):
        self._proponer_empresa(self.CARLOS)
        self.assertEqual(entrar_como(DUBAL).post(f"/empresas/{self.NEXUS}/invitacion/cancelar/").status_code, 403)
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/invitacion/cancelar/")
        self.assertIsNone(InvitacionService.pendiente_de_empresa(self.NEXUS))

    def test_solo_queda_la_ultima_propuesta(self):
        self._proponer_empresa(self.CARLOS)
        self._proponer_empresa("usr_santiago011")
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/invitacion/responder/", {"accion": "aceptar"})
        self.assertEqual(PropiedadService.administrador_de(self.NEXUS).uid, MATEO)
        self.assertEqual(InvitacionService.pendiente_de_empresa(self.NEXUS).uid, "usr_santiago011")

    def test_nunca_hay_dos_administradores(self):
        self._proponer_empresa(self.CARLOS)
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/invitacion/responder/", {"accion": "aceptar"})
        filas = db.cypher_query("MATCH (u:Usuario)-[:ADMINISTRA]->(:Empresa {eid: 'emp_nexus01'}) RETURN count(u)")[0][0][0]
        self.assertEqual(filas, 1)

    def test_si_deja_de_ser_miembro_la_propuesta_se_cae(self):
        self._proponer_empresa(self.CARLOS)
        entrar_como(self.CARLOS).post(f"/usuarios/{self.CARLOS}/experiencia/{self.NEXUS}/eliminar/")
        self.assertIsNone(InvitacionService.pendiente_de_empresa(self.NEXUS))
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/transferir/", {"uid": self.ANDRES})
        entrar_como(self.ANDRES).post(f"/proyectos/{self.FINTECH}/colaboradores/{self.ANDRES}/eliminar/")
        self.assertIsNone(InvitacionService.tipo_invitacion_proyecto(self.ANDRES, self.FINTECH))

    def test_plataforma_puede_asumirla_pero_no_imponerla(self):
        self._proponer_empresa(self.CARLOS, sesion=WILSON)
        self.assertEqual(PropiedadService.administrador_de(self.NEXUS).uid, MATEO)
        self.assertIn(WILSON, {u.uid for u in entrar_como(WILSON).get(f"/empresas/{self.NEXUS}/").context["candidatos_transferencia"]})
        self._proponer_empresa(WILSON, sesion=WILSON)
        self.assertEqual(PropiedadService.administrador_de(self.NEXUS).uid, WILSON)

    def test_la_cuenta_del_administrador_sigue_bloqueada(self):
        entrar_como(MATEO).post(f"/usuarios/{MATEO}/eliminar/")
        self.assertIsNotNone(UsuarioService.get(MATEO))


class NotificacionesTest(_ConDatosDeEjemplo):
    NEXUS, FINTECH, TALENTO = "emp_nexus01", "proy_fintech02", "proy_talento03"
    JOSE, CARLOS, ANDRES, ANGELO, GLOBANT, TECH = "usr_jose012", "usr_carlos001", "usr_andres015", "usr_angelo002", "emp_globant03", "emp_techin02"

    def _titulos(self, uid):
        return [n["titulo"] for n in NotificacionService.de_usuario(uid)]

    def _avisado(self, uid, texto):
        titulos = self._titulos(uid)
        self.assertTrue(any(texto in t for t in titulos), f"{texto!r} no está en {titulos}")

    def test_solicitud_de_conexion_aceptada_y_rechazada(self):
        entrar_como(DUBAL).post(f"/conexiones/solicitudes/{LUIS}/responder/", {"accion": "aceptar"})
        self._avisado(LUIS, "Dubal Aguilar aceptó tu solicitud de conexión")
        entrar_como(MATEO).post(f"/conexiones/solicitudes/{self.JOSE}/responder/", {"accion": "rechazar"})
        self._avisado(self.JOSE, "Mateo Cisneros rechazó tu solicitud de conexión")

    def test_empleo_confirmado_y_rechazado(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/empleos/{self.JOSE}/responder/", {"accion": "rechazar"})
        self._avisado(self.JOSE, "Nexus Corp rechazó tu empleo")
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/experiencia/agregar/", {"eid": self.NEXUS, "cargo": "QA"})
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/empleos/{LUIS}/responder/", {"accion": "aceptar"})
        self._avisado(LUIS, "Nexus Corp confirmó tu empleo")

    def test_invitacion_a_proyecto_avisa_al_lider(self):
        entrar_como(LUIS).post(f"/proyectos/{self.FINTECH}/invitacion/responder/", {"accion": "rechazar"})
        self._avisado(DUBAL, "Luis Angel rechazó colaborar en Plataforma Fintech AI")

    def test_solicitud_para_unirse_avisa_a_quien_la_pidio(self):
        entrar_como(self.CARLOS).post(f"/proyectos/{self.TALENTO}/solicitudes/{self.JOSE}/responder/", {"accion": "rechazar"})
        self._avisado(self.JOSE, "Se rechazó tu solicitud para unirte a Recomendador de Talento")

    def test_transferencia_avisa_al_responsable(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/transferir/", {"uid": self.ANDRES})
        entrar_como(self.ANDRES).post(f"/proyectos/{self.FINTECH}/invitacion/responder/", {"accion": "rechazar"})
        self._avisado(DUBAL, "Andres Castillo rechazó liderar Plataforma Fintech AI")
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/transferir/", {"uid": self.CARLOS})
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/invitacion/responder/", {"accion": "aceptar"})
        self._avisado(MATEO, "Carlos Calabria aceptó administrar Nexus Corp")

    def test_cancelar_invitaciones_avisa_al_invitado(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/invitaciones/{LUIS}/cancelar/")
        self._avisado(LUIS, "Se canceló tu invitación a Plataforma Fintech AI")
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/transferir/", {"uid": self.CARLOS})
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/invitacion/cancelar/")
        self._avisado(self.CARLOS, "Se canceló la transferencia de Nexus Corp")

    def test_conexion_terminada(self):
        entrar_como(DUBAL).post(f"/conexiones/desconectar/{DUBAL}/{self.CARLOS}/")
        self._avisado(self.CARLOS, "Tu conexión con Dubal Aguilar terminó")
        self.assertEqual(self._titulos(DUBAL), [])

    def test_quitar_de_un_proyecto_y_salir(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/colaboradores/{self.ANDRES}/eliminar/")
        self._avisado(self.ANDRES, "Ya no participas en Plataforma Fintech AI")
        entrar_como("usr_miguel010").post(f"/proyectos/{self.TALENTO}/colaboradores/usr_miguel010/eliminar/")
        self._avisado(self.CARLOS, "salió de Recomendador de Talento")

    def test_cambio_de_rol(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/colaboradores/agregar/", {"uid": self.ANDRES, "rol": "Arquitecto"})
        self._avisado(self.ANDRES, "Tu rol en Plataforma Fintech AI ahora es Arquitecto")

    def test_quitar_empleo_y_renunciar(self):
        entrar_como(MATEO).post(f"/usuarios/{self.CARLOS}/experiencia/{self.NEXUS}/eliminar/")
        self._avisado(self.CARLOS, "Nexus Corp quitó tu empleo de tu perfil")
        entrar_como("usr_santiago011").post(f"/usuarios/usr_santiago011/experiencia/{self.NEXUS}/eliminar/")
        self._avisado(MATEO, "dejó Nexus Corp")
        self.assertFalse(any("quitó tu empleo" in t for t in self._titulos("usr_santiago011")))

    def test_eliminar_empresa_oferta_y_proyecto(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/eliminar/")
        self._avisado(self.CARLOS, "La empresa Nexus Corp fue eliminada")
        self._avisado(DUBAL, "La empresa Nexus Corp fue eliminada")
        entrar_como(MARIA).post("/ofertas/ofr_arch02/eliminar/")
        self._avisado("usr_santiago011", "El empleo Lead Graph Architect fue eliminado")
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/eliminar/")
        self._avisado(self.ANDRES, "El proyecto Plataforma Fintech AI fue eliminado")

    def test_oferta_cerrada_avisa_a_candidatos(self):
        entrar_como(MATEO).post("/ofertas/ofr_dataeng01/editar/", {"titulo": "Senior Data Engineer", "modalidad": "remoto", "estado": "cerrada"})
        self._avisado(DUBAL, "El empleo Senior Data Engineer se cerró")
        entrar_como(MATEO).post("/ofertas/ofr_dataeng01/editar/", {"titulo": "Senior Data Engineer", "modalidad": "remoto", "estado": "cerrada"})
        self.assertEqual(sum("se cerró" in t for t in self._titulos(DUBAL)), 1)

    def test_retirar_postulacion_avisa_a_la_empresa(self):
        entrar_como(DUBAL).post(f"/ofertas/ofr_dataeng01/postulaciones/{DUBAL}/eliminar/")
        self._avisado(MATEO, "Dubal Aguilar retiró su postulación")

    def test_avance_avisa_a_los_miembros(self):
        entrar_como(DUBAL).post(f"/proyectos/{self.FINTECH}/avances/agregar/", {"texto": "Lanzamos", "estado": "activo"})
        self._avisado(self.ANDRES, "Nuevo avance en Plataforma Fintech AI")
        self.assertFalse(any("Nuevo avance" in t for t in self._titulos(DUBAL)))

    def test_acciones_de_un_administrador_sobre_tus_datos(self):
        entrar_como(WILSON).post(f"/usuarios/{LUIS}/editar/", {"nombre": "Luis", "apellido": "Angel", "email": "luis.angel@wheelson.com"})
        self._avisado(LUIS, "Un administrador actualizó tu perfil")
        entrar_como(WILSON).post("/publicaciones/pub_dubal01/eliminar/")
        self._avisado(DUBAL, "Un administrador eliminó una de tus publicaciones")
        entrar_como(WILSON).post(f"/empresas/{self.NEXUS}/transferir/", {"uid": WILSON})
        self._avisado(MATEO, "Ya no administras Nexus Corp")

    def test_nadie_recibe_aviso_de_lo_propio(self):
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/editar/", {"nombre": "Luis", "apellido": "Angel", "email": "luis.angel@wheelson.com"})
        entrar_como("usr_jose012").post("/conexiones/solicitudes/usr_mateo005/cancelar/")
        self.assertEqual(self._titulos(LUIS), [])
        self.assertEqual(self._titulos(MATEO), [])

    def test_aparece_en_el_panel_con_enlace_y_marca_de_nuevo(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/empleos/{self.JOSE}/responder/", {"accion": "rechazar"})
        html = entrar_como(self.JOSE).get("/").content.decode()
        self.assertIn("Nexus Corp rechazó tu empleo", html)
        self.assertIn('data-aviso="notificacion:', html)
        aviso = next(a for a in avisos_para(self.JOSE) if "rechazó tu empleo" in a["titulo"])
        self.assertEqual(aviso["url"], f"/usuarios/{self.JOSE}/")
        self.assertTrue(aviso["fecha_texto"])

    def test_lo_mas_reciente_va_primero_despues_de_lo_pendiente(self):
        NotificacionService.crear(LUIS, "Primera")
        NotificacionService.crear(LUIS, "Segunda")
        titulos = [a["titulo"] for a in avisos_para(LUIS, limite=50) if not a.get("pendiente")]
        self.assertLess(titulos.index("Segunda"), titulos.index("Primera"))

    def test_son_privadas(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/empleos/{self.JOSE}/responder/", {"accion": "rechazar"})
        self.assertNotContains(entrar_como(LUIS).get("/"), "rechazó tu empleo")

    def test_eliminar_cuenta_elimina_sus_notificaciones(self):
        NotificacionService.crear(self.JOSE, "Hola")
        cliente = entrar_como(self.JOSE)
        cliente.post(f"/usuarios/{self.JOSE}/eliminar/")
        self.assertEqual(db.cypher_query("MATCH (n:Notificacion {titulo: 'Hola'}) RETURN count(n)")[0][0][0], 0)

    def test_las_notificaciones_no_entran_al_grafo_de_la_red(self):
        NotificacionService.crear(LUIS, "Hola")
        etiquetas = {a["label"] for a in entrar_como(WILSON).get("/grafo/api/data/").json()["edges"]}
        self.assertNotIn("RECIBE", etiquetas)

    def test_todos_los_iconos_de_los_avisos_existen(self):
        import pathlib
        from django.conf import settings
        sprite = (pathlib.Path(settings.BASE_DIR) / "static/icons/phosphor-sprite.svg").read_text(encoding="utf-8")
        codigo = (pathlib.Path(settings.BASE_DIR) / "core/views.py").read_text(encoding="utf-8") + (pathlib.Path(settings.BASE_DIR) / "core/presentacion.py").read_text(encoding="utf-8")
        usados = set(re.findall(r'"icono": "([a-z-]+)"', codigo)) | set(re.findall(r'icono="([a-z-]+)"', codigo))
        usados |= set(re.findall(r'_avisar\(.*, "([a-z-]+)"\)', codigo)) | {"check-circle", "x"}
        self.assertGreater(len(usados), 4)
        for nombre in usados:
            with self.subTest(icono=nombre):
                self.assertIn(f'id="{nombre}-duotone"', sprite)


class CatalogoTest(_ConDatosDeEjemplo):
    def _crear(self, uid, nombre):
        return entrar_como(uid).post("/habilidades/nueva/", {"nombre": nombre, "categoria": "tecnica"}, follow=True)

    def _cuantas(self, parecido):
        return sum(h.nombre.lower() == parecido for h in HabilidadService.all())

    def test_solo_el_administrador_agrega(self):
        self.assertEqual(self._crear(LUIS, "Rust").status_code, 403)
        self.assertEqual(self._cuantas("rust"), 0)
        self._crear(WILSON, "Rust")
        self.assertEqual(self._cuantas("rust"), 1)

    def test_el_formulario_solo_lo_ve_el_administrador(self):
        self.assertNotIn("/habilidades/nueva/", entrar_como(LUIS).get("/habilidades/").content.decode())
        self.assertIn("/habilidades/nueva/", entrar_como(WILSON).get("/habilidades/").content.decode())

    def test_sin_duplicados_por_mayusculas_tildes_o_espacios(self):
        for nombre in ("python", "PYTHON", "  Python  ", "Pythón"):
            with self.subTest(nombre=nombre):
                res = self._crear(WILSON, nombre)
                self.assertContains(res, "Ya existe una habilidad con ese nombre")
        self.assertEqual(self._cuantas("python"), 1)

    def test_espacios_internos_se_normalizan(self):
        self._crear(WILSON, "Machine   Learning Ops")
        self.assertEqual(self._cuantas("machine learning ops"), 1)
        self.assertContains(self._crear(WILSON, "machine learning ops"), "Ya existe una habilidad")

    def test_nombres_distintos_si_se_aceptan(self):
        self._crear(WILSON, "Python Avanzado")
        self.assertEqual(self._cuantas("python avanzado"), 1)

    def test_empresas_tampoco_se_duplican(self):
        for nombre in ("nexus corp", "NEXUS  CORP"):
            with self.subTest(nombre=nombre):
                res = entrar_como(LUIS).post("/empresas/nueva/", {"nombre": nombre, "industria": "IT", "tamano": "pequena"})
                self.assertContains(res, "Ya existe una empresa con este nombre")
        res = entrar_como(MARIA).post("/empresas/emp_globant03/editar/", {"nombre": "NEXUS CORP", "industria": "IT", "tamano": "grande"})
        self.assertContains(res, "Ya existe una empresa con este nombre")

    def test_una_empresa_puede_conservar_o_ajustar_su_propio_nombre(self):
        res = entrar_como(MATEO).post("/empresas/emp_nexus01/editar/", {"nombre": "NEXUS CORP", "industria": "Fintech", "tamano": "grande"})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(EmpresaService.get("emp_nexus01").nombre, "NEXUS CORP")

    def test_los_formularios_explican_como_conseguir_una_habilidad(self):
        self.assertContains(entrar_como(LUIS).get(f"/usuarios/{LUIS}/"), "Solo el administrador de la plataforma agrega habilidades")
        self.assertContains(entrar_como(MATEO).get("/ofertas/ofr_dataeng01/"), "Solo el administrador de la plataforma agrega habilidades")


class MenuTest(_ConDatosDeEjemplo):
    def _menu(self, uid):
        html = entrar_como(uid).get("/").content.decode()
        return re.findall(r'<a href="(/[^"]*)" class="ws-nav__item', html)

    def test_empresas_esta_en_el_menu_para_todos(self):
        self.assertIn("/empresas/", self._menu(LUIS))
        self.assertIn("/empresas/", self._menu(WILSON))

    def test_habilidades_solo_para_el_administrador(self):
        self.assertNotIn("/habilidades/", self._menu(LUIS))
        self.assertNotIn("/habilidades/", self._menu(MATEO))
        self.assertIn("/habilidades/", self._menu(WILSON))

    def test_marca_la_seccion_activa(self):
        html = entrar_como(LUIS).get("/empresas/").content.decode()
        self.assertRegex(html, r'href="/empresas/" class="ws-nav__item is-activo"')


class FundadorTest(_ConDatosDeEjemplo):
    def _crear(self, uid=LUIS, nombre="Luis SAS"):
        entrar_como(uid).post("/empresas/nueva/", {"nombre": nombre, "industria": "IT", "tamano": "pequena"})
        return next(e for e in EmpresaService.all() if e.nombre == nombre)

    def test_quien_crea_la_empresa_queda_como_empleado(self):
        empresa = self._crear()
        empleo = EmpleoService.listar_por_empresa(empresa.eid)
        self.assertEqual([(e["usuario"].uid, e["cargo"], e["actual"]) for e in empleo], [(LUIS, "Fundador", True)])
        self.assertTrue(EmpleoService.es_empleado(LUIS, empresa.eid))
        self.assertTrue(any(e["empresa"].eid == empresa.eid for e in EmpleoService.listar_por_usuario(LUIS)))

    def test_conserva_sus_otros_empleos(self):
        antes = len(EmpleoService.listar_por_usuario(LUIS))
        self._crear()
        self.assertEqual(len(EmpleoService.listar_por_usuario(LUIS)), antes + 1)

    def test_quien_administra_no_puede_dejar_su_empresa(self):
        res = entrar_como(MATEO).post(f"/usuarios/{MATEO}/experiencia/emp_nexus01/eliminar/", follow=True)
        self.assertContains(res, "Transfiérela primero")
        self.assertTrue(EmpleoService.es_empleado(MATEO, "emp_nexus01"))
        self.assertNotIn(f"/usuarios/{MATEO}/experiencia/emp_nexus01/eliminar/", entrar_como(MATEO).get(f"/usuarios/{MATEO}/").content.decode())

    def test_tras_transferir_si_puede_dejarla(self):
        entrar_como(MATEO).post("/empresas/emp_nexus01/transferir/", {"uid": "usr_carlos001"})
        entrar_como("usr_carlos001").post("/empresas/emp_nexus01/invitacion/responder/", {"accion": "aceptar"})
        entrar_como(MATEO).post(f"/usuarios/{MATEO}/experiencia/emp_nexus01/eliminar/")
        self.assertFalse(EmpleoService.es_empleado(MATEO, "emp_nexus01"))

    def test_sin_mas_empleados_lo_sigue_explicando(self):
        empresa = self._crear()
        self.assertContains(entrar_como(LUIS).get(f"/empresas/{empresa.eid}/"), "primero debe haber otros empleados")


class PlantillasTest(TestCase):
    def test_ningun_comentario_de_plantilla_se_imprime_como_texto(self):
        # {# #} solo funciona en una línea: en varias, Django lo muestra en la página
        import pathlib
        from django.conf import settings
        for ruta in (pathlib.Path(settings.BASE_DIR) / "core/templates").rglob("*.html"):
            with self.subTest(plantilla=ruta.name):
                self.assertNotRegex(ruta.read_text(encoding="utf-8"), r"\{#(?:(?!#\}).)*\n")


class TiposDelFeedTest(_ConDatosDeEjemplo):
    def test_cada_tipo_tiene_su_propio_formato(self):
        html = entrar_como(LUIS).get("/").content.decode()
        for clase in ("ws-hito--publicacion", "ws-hito--proyecto", "ws-hito--oferta", "ws-hito--avance", "ws-hito--conexion"):
            with self.subTest(clase=clase):
                self.assertIn(clase, html)
        self.assertIn("ws-expediente__pestana", html)
        self.assertIn("ws-enlace-personas", html)
        self.assertIn("ws-estado--activo", html)

    def test_el_avance_muestra_estado_y_quien_lo_registro(self):
        html = entrar_como(LUIS).get("/").content.decode()
        self.assertIn("Lo registró", html)
        self.assertIn("Motor de Grafos WheelsOn", html)

    def test_las_opciones_del_proyecto_siguen_solo_para_su_lider(self):
        self.assertIn("/proyectos/proy_graph01/editar/", entrar_como(MATEO).get("/?ver=proyecto").content.decode())
        self.assertNotIn("/proyectos/proy_graph01/editar/", entrar_como(LUIS).get("/?ver=proyecto").content.decode())

    def test_el_fondo_se_mueve_y_no_usa_canvas(self):
        html = entrar_como(LUIS).get("/").content.decode()
        self.assertIn("data-ws-fondo", html)
        self.assertNotIn("<canvas data-ws-fondo", html)
        css = open(finders.find("css/wheelson.css"), encoding="utf-8").read()
        self.assertIn("@keyframes ws-fluir-coral", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_el_login_usa_la_foto_nueva_sin_la_rueda_gigante(self):
        html = ClienteAnonimo().get("/login/").content.decode()
        self.assertIn("img/acceso", html)
        self.assertIn("data-ws-ola-foto", html)
        self.assertNotIn("ws-red__", html)
        self.assertTrue(finders.find("img/acceso.webp"))


class LibreriasPesadasTest(_ConDatosDeEjemplo):
    def test_solo_se_cargan_donde_se_usan(self):
        for ruta in ("/", "/proyectos/", "/empresas/"):
            html = entrar_como(LUIS).get(ruta).content.decode()
            self.assertNotIn("vis-network", html, ruta)
            self.assertNotIn("chart-4", html, ruta)
        login = ClienteAnonimo().get("/login/").content.decode()
        self.assertNotIn("vis-network", login)
        self.assertNotIn("chart-4", login)
        self.assertIn("vis-network", entrar_como(LUIS).get("/grafo/").content.decode())
        self.assertIn("vis-network", entrar_como(LUIS).get(f"/usuarios/{DUBAL}/").content.decode())
        self.assertIn("chart-4", entrar_como(LUIS).get("/analitica/").content.decode())


class MetaforasTest(_ConDatosDeEjemplo):
    """Carpetas, pasajes, edificios y personas: cada adorno sale de un dato real del grafo."""

    MATEO = "usr_mateo005"

    def _plantillas(self):
        import pathlib
        from django.conf import settings

        return pathlib.Path(settings.BASE_DIR, "core", "templates").rglob("*.html")

    def test_la_hoja_de_la_carpeta_es_el_ultimo_avance(self):
        _, avances = ProyectoService.resumen_carpetas()
        html = entrar_como(LUIS).get("/proyectos/").content.decode()
        self.assertGreater(html.count('class="ws-carpeta ws-carpeta--'), 0)
        self.assertTrue(avances)
        for total, ultimo in avances.values():
            self.assertIn(escape(ultimo), html)
            self.assertIn(f"{total} en total", html)

    def test_el_pasaje_dice_la_compatibilidad_y_lleva_el_papel_recortado(self):
        resumen = OfertaService.resumen_boletos(LUIS)
        html = entrar_como(LUIS).get("/ofertas/").content.decode()
        self.assertEqual(html.count('class="ws-boleto__papel"'), len(resumen))
        self.assertIn("ws-ruta__destino", html)

    def test_las_ventanas_encendidas_son_las_personas(self):
        svg = skyline("emp_uno", "mediana", 7)
        self.assertEqual(svg.count('class="ws-luz"'), 7)
        self.assertEqual(svg, skyline("emp_uno", "mediana", 7))
        self.assertNotEqual(svg, skyline("emp_dos", "mediana", 7))

    def test_las_ventanas_no_fallan_sin_personas(self):
        self.assertEqual(skyline("emp_uno", "mediana", None).count('class="ws-luz"'), 0)

    def test_el_grado_de_la_tarjeta_es_el_del_grafo(self):
        grados = UsuarioService.grados()
        self.assertGreater(grados[DUBAL], 0)
        res = entrar_como(LUIS).get("/usuarios/")
        self.assertContains(res, f"Grado de conexión <strong>{grados[DUBAL]}</strong>", html=False)

    def test_saltos_sin_contactos_no_inventa_rutas(self):
        db.cypher_query("CREATE (:Usuario {uid: 'usr_aislado'})")
        self.assertEqual(ConexionService.saltos_a_empresas("usr_aislado"), {})

    def test_saltos_a_la_empresa_de_un_contacto_directo(self):
        filas, _ = db.cypher_query(
            """
            MATCH (:Usuario {uid: $uid})-[:CONECTA_CON]-(c:Usuario)-[:TRABAJA_EN]->(e:Empresa)
            WHERE NOT (:Usuario {uid: $uid})-[:TRABAJA_EN]->(e)
            RETURN e.eid LIMIT 1
            """,
            {"uid": LUIS},
        )
        self.assertTrue(filas)
        self.assertEqual(ConexionService.saltos_a_empresas(LUIS)[filas[0][0]], 1)

    def test_sugerencias_marca_la_pestana_activa_y_no_muestra_listas_crudas(self):
        res = entrar_como(self.MATEO).get("/recomendaciones/?tab=colaboradores")
        html = res.content.decode()
        self.assertIn('class="is-activo"', html)
        self.assertNotIn("['", html)
        self.assertEqual(res.context["total_sugerencias"], len(res.context["rec_colaboradores"]))

    def test_consultas_y_grafo_usan_el_mismo_encabezado(self):
        for ruta in ("/consultas/", "/grafo/", "/recomendaciones/"):
            self.assertContains(entrar_como(LUIS).get(ruta), 'class="ws-seccion"')

    def test_el_grafo_filtra_sin_elipses_y_conserva_sus_controles(self):
        html = entrar_como(LUIS).get("/grafo/").content.decode()
        self.assertEqual(html.count('class="ws-tipo"'), 5)
        self.assertIn("toggleTipo('Oferta')", html)
        self.assertIn('x-text="stats.total_nodos"', html)

    def test_ninguna_plantilla_tiene_comillas_escapadas(self):
        for ruta in self._plantillas():
            self.assertNotIn('\\">', ruta.read_text(encoding="utf-8"), ruta)

    def test_no_vuelven_las_elipses_de_texto_ni_las_baldosas_de_icono(self):
        for ruta in self._plantillas():
            texto = ruta.read_text(encoding="utf-8")
            self.assertNotIn("ws-sello", texto, ruta)
            self.assertNotIn("ws-fila__icono", texto, ruta)
            for clases in re.findall(r'<span class="([^"]*)"', texto):
                if "rounded-full" in clases:
                    self.assertFalse(re.search(r"\bpx-", clases), f"{ruta}: {clases}")
        css = open(finders.find("css/wheelson.css"), encoding="utf-8").read()
        for selector in (r"\.ws-chip \{", r"\.ws-pastilla \{", r"\.ws-acceso__cifras li \{"):
            regla = re.search(selector + r"[^}]*\}", css).group(0)
            self.assertNotIn("border-radius", regla, selector)

    def test_todas_las_secciones_quedan_centradas(self):
        css = open(finders.find("css/wheelson.css"), encoding="utf-8").read()
        self.assertRegex(css, r"\.ws-main--con-franja > \* \{[^}]*max-width: 1120px;[^}]*margin-inline: auto")


class CargaPorPartesTest(_ConDatosDeEjemplo):
    def test_neo4j_devuelve_solo_la_pagina_y_el_total(self):
        pagina, total = UsuarioService.pagina("", 0, 3)
        self.assertEqual(len(pagina), 3)
        self.assertEqual(total, 15)
        siguiente, _ = UsuarioService.pagina("", 3, 3)
        self.assertFalse({u.uid for u in pagina} & {u.uid for u in siguiente})

    def test_la_primera_vista_no_trae_todo(self):
        res = entrar_como(LUIS).get("/usuarios/")
        self.assertEqual(len(res.context["usuarios"]), 8)
        self.assertEqual(res.context["total"], 15)
        self.assertContains(res, "Ver 7 más")
        self.assertContains(res, 'data-ws-ver-mas="lista-personas"')

    def test_el_fragmento_trae_solo_lo_nuevo_sin_la_pagina(self):
        primera = entrar_como(LUIS).get("/usuarios/").context["usuarios"]
        res = entrar_como(LUIS).get("/usuarios/?pagina=2&fragmento=1")
        html = res.content.decode()
        self.assertNotIn("<html", html)
        self.assertEqual(html.count('class="ws-persona"'), 7)
        self.assertFalse({u.uid for u in primera} & {u.uid for u in res.context["usuarios"]})
        self.assertNotIn("ws-ver-mas", html)

    def test_sin_javascript_el_enlace_trae_todo_lo_anterior(self):
        res = entrar_como(LUIS).get("/usuarios/?pagina=2")
        self.assertEqual(len(res.context["usuarios"]), 15)
        self.assertNotContains(res, "ws-ver-mas")

    def test_ver_mas_conserva_la_busqueda_y_no_el_fragmento(self):
        res = entrar_como(LUIS).get("/ofertas/?modalidad=remoto&pagina=1&fragmento=0")
        self.assertEqual(res.context["modalidad_filtro"], "remoto")
        vista = entrar_como(LUIS).get("/usuarios/?q=a")
        self.assertIn("q=a", vista.context["ver_mas"]["url"])
        self.assertIn("pagina=2", vista.context["ver_mas"]["url"])
        self.assertNotIn("fragmento", vista.context["ver_mas"]["url"])

    def test_pagina_invalida_no_rompe(self):
        for valor in ("abc", "-3", "0", "99999999999999999999"):
            with self.subTest(valor=valor):
                self.assertEqual(entrar_como(LUIS).get(f"/usuarios/?pagina={valor}").status_code, 200)

    def test_la_busqueda_es_parametro_y_no_se_inyecta(self):
        for lista in ("/usuarios/", "/empresas/", "/ofertas/", "/proyectos/", "/habilidades/"):
            with self.subTest(lista=lista):
                res = entrar_como(LUIS).get(lista + "?q=' OR 1=1 //")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.context["total"], 0)

    def test_busqueda_por_nombre_completo_y_tecnologia(self):
        self.assertEqual(entrar_como(LUIS).get("/usuarios/?q=mateo cis").context["total"], 1)
        pids = {p.pid for p in entrar_como(LUIS).get("/proyectos/?q=vis.js").context["proyectos"]}
        self.assertIn("proy_graph01", pids)

    def test_el_estado_del_proyecto_se_filtra_en_el_servidor(self):
        res = entrar_como(LUIS).get("/proyectos/?estado=activo")
        self.assertTrue(all(p.estado == "activo" for p in res.context["proyectos"]))
        self.assertEqual(entrar_como(LUIS).get("/proyectos/?estado=pausado").context["total"], 0)

    def test_los_resumenes_se_limitan_a_lo_que_se_ve(self):
        self.assertEqual(EmpresaService.resumen_edificios(ids=[]), {})
        self.assertEqual(set(EmpresaService.resumen_edificios(ids=["emp_nexus01"])), {"emp_nexus01"})
        self.assertEqual(set(OfertaService.resumen_boletos(LUIS, ids=["ofr_dataeng01"])), {"ofr_dataeng01"})
        miembros, _ = ProyectoService.resumen_carpetas(ids=["proy_graph01"])
        self.assertEqual(set(miembros), {"proy_graph01"})

    def test_el_feed_se_carga_por_partes_y_se_filtra(self):
        res = entrar_como(LUIS).get("/")
        self.assertEqual(len(res.context["feed_items"]), 8)
        self.assertContains(res, 'data-ws-ver-mas="lista-feed"')
        solo = entrar_como(LUIS).get("/?ver=oferta").context["feed_items"]
        self.assertTrue(solo and all(i["tipo"] == "oferta" for i in solo))
        self.assertEqual(entrar_como(LUIS).get("/?ver=inventado").context["ver"], "")

    def test_el_fragmento_del_feed_tiene_proyectos_completos(self):
        res = entrar_como(MATEO).get("/?ver=proyecto&pagina=1&fragmento=1")
        self.assertNotContains(res, "<html")
        item = res.context["feed_items"][0]
        self.assertIn("colaboradores", item)
        self.assertIn("tecnologias", item)

    def test_el_fragmento_respeta_los_permisos(self):
        self.assertNotContains(entrar_como(LUIS).get("/proyectos/?fragmento=1"), "/proyectos/proy_graph01/editar/")
        self.assertContains(entrar_como(MATEO).get("/proyectos/?fragmento=1"), "/proyectos/proy_graph01/editar/")


class OrganizacionTest(_ConDatosDeEjemplo):
    def test_mi_red_separa_contactos_de_sugerencias(self):
        res = entrar_como(MATEO).get("/conexiones/")
        self.assertContains(res, 'class="ws-contacto"')
        self.assertContains(res, 'class="ws-quizas"')
        self.assertNotContains(res, 'class="ws-persona')
        self.assertLessEqual(len(res.context["sugerencias"]), 4)
        self.assertEqual(res.context["total_conexiones"], 9)
        self.assertEqual(len(res.context["conexiones"]), 6)

    def test_las_sugerencias_de_otra_persona_no_se_ven(self):
        res = entrar_como(LUIS).get(f"/conexiones/?uid={MATEO}")
        self.assertEqual(res.context["sugerencias"], [])
        self.assertNotContains(res, "ws-quizas")

    def test_buscar_entre_los_contactos(self):
        res = entrar_como(MATEO).get("/conexiones/?q=dubal")
        self.assertEqual([c["usuario"].uid for c in res.context["conexiones"]], [DUBAL])
        self.assertEqual(res.context["total_conexiones"], 9)

    def test_desconectar_sigue_disponible_en_la_agenda(self):
        self.assertContains(entrar_como(MATEO).get("/conexiones/"), "/desconectar/")
        self.assertNotContains(entrar_como(LUIS).get(f"/conexiones/?uid={MATEO}"), "/desconectar/")

    def test_las_sugerencias_no_usan_plurales_con_parentesis(self):
        self.assertNotContains(entrar_como(MATEO).get("/conexiones/"), "(s)")

    def test_perfil_sin_datos_tecnicos_ni_inventados(self):
        html = entrar_como(LUIS).get(f"/usuarios/{MATEO}/").content.decode()
        self.assertNotIn("Disponible para trabajar", html)
        self.assertNotIn("UID:", html)
        self.assertIn("Cómo llegar a Mateo", html)

    def test_en_el_perfil_propio_no_se_ofrece_la_ruta_a_uno_mismo(self):
        html = entrar_como(MATEO).get(f"/usuarios/{MATEO}/").content.decode()
        self.assertNotIn("Cómo llegar a", html)
        self.assertNotIn("Contactos en común", html)

    def test_sin_biografia_no_se_inventa_una(self):
        db.cypher_query("MATCH (u:Usuario {uid: $uid}) SET u.biografia = '', u.ubicacion = ''", {"uid": MATEO})
        html = entrar_como(LUIS).get(f"/usuarios/{MATEO}/").content.decode()
        self.assertNotIn("Profesional apasionado", html)
        self.assertNotIn("Medellín, Colombia", html.split('ws-perfil__datos')[1].split("</p>")[0])

    def test_detalles_sin_jerga_del_grafo(self):
        for ruta in (f"/usuarios/{MATEO}/", "/proyectos/proy_graph01/", "/ofertas/ofr_dataeng01/", "/empresas/emp_nexus01/"):
            html = entrar_como(MATEO).get(ruta).content.decode()
            with self.subTest(ruta=ruta):
                self.assertNotIn("Arista semántica", html)
                self.assertNotIn("Copiar ID", html)
                self.assertNotIn("(:Usuario)", html)

    def test_cerrar_sesion_es_directo_y_el_perfil_esta_en_la_cuenta(self):
        html = entrar_como(MATEO).get("/").content.decode()
        cuenta = html[html.index('class="ws-cuenta"'):]
        self.assertIn(f'class="ws-cuenta__titular" href="/usuarios/{MATEO}/"', cuenta)
        self.assertIn('action="/logout/"', cuenta)
        self.assertNotIn("¿Quieres salir de tu cuenta?", html)

    def test_inicio_no_repite_la_identidad(self):
        html = entrar_como(MATEO).get("/").content.decode()
        self.assertNotIn("ws-inicio__acciones", html)
        self.assertNotIn("ws-acciones__movil", html)

    def test_catalogo_de_habilidades_con_cifras_reales(self):
        res = entrar_como(MATEO).get("/habilidades/?categoria=idioma")
        self.assertTrue(all(h.categoria == "idioma" for h in res.context["habilidades"]))
        self.assertNotContains(res, "xxx")
        conteo = {c[0]: c[2] for c in res.context["categorias"]}
        self.assertEqual(conteo[""], conteo["tecnica"] + conteo["blanda"] + conteo["idioma"])

    def test_la_carpeta_del_feed_integra_la_pestana(self):
        res = entrar_como(MATEO).get("/?ver=proyecto")
        self.assertContains(res, "Proyecto · En desarrollo")
        self.assertContains(res, "ws-expediente__espalda")
        self.assertNotContains(res, 'class="ws-pestana"')


class ContratacionTest(_ConDatosDeEjemplo):
    """El ciclo completo: publicar, postularse, decidir y llegar al equipo."""

    NEXUS = "emp_nexus01"
    OID = "ofr_dataeng01"
    ANGELO = "usr_angelo002"

    def _estado(self, oid=None):
        return f"/ofertas/{oid or self.OID}/postulaciones/"

    def _decidir(self, uid, estado, oid=None, sesion=MATEO):
        return entrar_como(sesion).post(f"{self._estado(oid)}{uid}/estado/", {"estado": estado}, follow=True)

    def _nueva(self, cupos=1, eid=None):
        return PropiedadService.crear_oferta(eid or self.NEXUS, titulo="Analista de Grafos", cupos=cupos).oid

    def _postular(self, oid, *uids):
        for uid in uids:
            PostulacionService.postular(uid, oid)

    def test_aceptar_suma_al_equipo_con_el_cargo_del_empleo(self):
        oid = self._nueva(cupos=2)
        self._postular(oid, LUIS)
        self.assertFalse(EmpleoService.es_empleado(LUIS, self.NEXUS))
        res = self._decidir(LUIS, "aceptada", oid)
        self.assertContains(res, "ya está en el equipo")
        self.assertEqual(PostulacionService.obtener_estado(LUIS, oid), "aceptada")
        self.assertTrue(EmpleoService.es_empleado(LUIS, self.NEXUS))
        empleo = next(e for e in EmpleoService.listar_por_empresa(self.NEXUS) if e["usuario"].uid == LUIS)
        self.assertEqual(empleo["cargo"], "Analista de Grafos")
        self.assertTrue(empleo["actual"])
        self.assertContains(entrar_como(DUBAL).get(f"/empresas/{self.NEXUS}/"), "Analista de Grafos")

    def test_llenar_el_cupo_cierra_el_empleo_y_responde_a_los_demas(self):
        oid = self._nueva()
        self._postular(oid, LUIS, DUBAL, self.ANGELO)
        PostulacionService.cambiar_estado(self.ANGELO, oid, "entrevista")
        self._decidir(LUIS, "aceptada", oid)
        self.assertEqual(OfertaService.get(oid).estado, "cerrada")
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, oid), "no_seleccionada")
        self.assertEqual(PostulacionService.obtener_estado(self.ANGELO, oid), "no_seleccionada")
        self.assertFalse(EmpleoService.es_empleado(DUBAL, self.NEXUS))
        for uid in (DUBAL, self.ANGELO):
            titulos = [n["titulo"] for n in NotificacionService.de_usuario(uid)]
            self.assertIn("El empleo Analista de Grafos ya se cubrió", titulos)
        self.assertIn("Nexus Corp te contrató", [n["titulo"] for n in NotificacionService.de_usuario(LUIS)])

    def test_no_se_puede_aceptar_a_dos_con_un_cupo(self):
        oid = self._nueva()
        self._postular(oid, LUIS, DUBAL)
        self._decidir(LUIS, "aceptada", oid)
        res = self._decidir(DUBAL, "aceptada", oid)
        self.assertContains(res, "Ya no se puede aceptar")
        self.assertEqual(PostulacionService.contar(oid)[1], 1)
        self.assertFalse(EmpleoService.es_empleado(DUBAL, self.NEXUS))

    def test_con_varios_cupos_sigue_abierto_hasta_llenarse(self):
        oid = self._nueva(cupos=2)
        self._postular(oid, LUIS, DUBAL, self.ANGELO)
        self._decidir(LUIS, "aceptada", oid)
        self.assertEqual(OfertaService.get(oid).estado, "abierta")
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, oid), "enviada")
        self._decidir(DUBAL, "aceptada", oid)
        self.assertEqual(OfertaService.get(oid).estado, "cerrada")
        self.assertEqual(PostulacionService.obtener_estado(self.ANGELO, oid), "no_seleccionada")

    def test_una_decision_no_se_cambia(self):
        oid = self._nueva(cupos=3)
        self._postular(oid, LUIS, DUBAL)
        self._decidir(LUIS, "aceptada", oid)
        self._decidir(DUBAL, "rechazada", oid)
        self.assertContains(self._decidir(LUIS, "rechazada", oid), "ya tiene una decisión")
        self.assertEqual(PostulacionService.obtener_estado(LUIS, oid), "aceptada")
        self.assertContains(self._decidir(DUBAL, "aceptada", oid), "Ya no se puede aceptar")
        self.assertContains(self._decidir(DUBAL, "revision", oid), "ya tiene una decisión")
        self.assertFalse(EmpleoService.es_empleado(DUBAL, self.NEXUS))

    def test_no_seleccionada_no_se_puede_poner_a_mano(self):
        self.assertContains(self._decidir(DUBAL, "no_seleccionada"), "estado válido")
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, self.OID), "enviada")

    def test_otro_no_puede_contratar(self):
        oid = self._nueva()
        self._postular(oid, LUIS)
        self.assertEqual(entrar_como(LUIS).post(f"{self._estado(oid)}{LUIS}/estado/", {"estado": "aceptada"}).status_code, 403)
        self.assertFalse(EmpleoService.es_empleado(LUIS, self.NEXUS))

    def test_cerrar_a_mano_responde_a_los_pendientes(self):
        oid = self._nueva(cupos=2)
        self._postular(oid, LUIS, DUBAL)
        self._decidir(LUIS, "rechazada", oid)
        entrar_como(MATEO).post(f"/ofertas/{oid}/editar/", {"titulo": "Analista de Grafos", "modalidad": "remoto", "estado": "cerrada", "cupos": 2})
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, oid), "no_seleccionada")
        self.assertEqual(PostulacionService.obtener_estado(LUIS, oid), "rechazada")

    def test_no_se_reabre_sin_cupo_ni_se_baja_de_lo_contratado(self):
        oid = self._nueva(cupos=2)
        self._postular(oid, LUIS, DUBAL)
        self._decidir(LUIS, "aceptada", oid)
        self._decidir(DUBAL, "aceptada", oid)
        datos = {"titulo": "Analista de Grafos", "modalidad": "remoto"}
        res = entrar_como(MATEO).post(f"/ofertas/{oid}/editar/", {**datos, "estado": "abierta", "cupos": 2})
        self.assertContains(res, "Auméntalos")
        self.assertEqual(OfertaService.get(oid).estado, "cerrada")
        res = entrar_como(MATEO).post(f"/ofertas/{oid}/editar/", {**datos, "estado": "cerrada", "cupos": 1})
        self.assertContains(res, "no pueden ser menos")
        entrar_como(MATEO).post(f"/ofertas/{oid}/editar/", {**datos, "estado": "abierta", "cupos": 3})
        self.assertEqual(OfertaService.get(oid).estado, "abierta")

    def test_quien_ya_trabaja_ahi_cambia_de_cargo_sin_duplicarse(self):
        oid = self._nueva()
        carlos = "usr_carlos001"
        self._postular(oid, carlos)
        self._decidir(carlos, "aceptada", oid)
        empleos = [e for e in EmpleoService.listar_por_empresa(self.NEXUS) if e["usuario"].uid == carlos]
        self.assertEqual(len(empleos), 1)
        self.assertEqual(empleos[0]["cargo"], "Analista de Grafos")

    def test_oferta_sin_empresa_no_contrata(self):
        oid = OfertaService.create(titulo="Suelta").oid
        self._postular(oid, LUIS)
        self.assertIsNone(PostulacionService.contratar(LUIS, oid))
        self.assertEqual(PostulacionService.obtener_estado(LUIS, oid), "enviada")

    def test_una_postulacion_decidida_no_se_retira(self):
        oid = self._nueva()
        self._postular(oid, LUIS, DUBAL)
        self._decidir(LUIS, "aceptada", oid)
        entrar_como(DUBAL).post(f"{self._estado(oid)}{DUBAL}/eliminar/")
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, oid), "no_seleccionada")

    def test_candidatos_solo_para_la_empresa(self):
        oid = self._nueva()
        self._postular(oid, LUIS, DUBAL)
        empresa = entrar_como(MATEO).get(f"/ofertas/{oid}/").content.decode()
        self.assertIn("Candidatos (2)", empresa)
        self.assertIn("Luis Angel", empresa)
        postulante = entrar_como(LUIS).get(f"/ofertas/{oid}/").content.decode()
        self.assertIn("Tu postulación", postulante)
        self.assertNotIn("Candidatos (", postulante)
        self.assertNotIn(f"/usuarios/{DUBAL}/", postulante.split("ws-ficha__conteo")[0].split("Tu postulación")[1])
        ajeno = entrar_como(self.ANGELO).get(f"/ofertas/{oid}/").content.decode()
        self.assertNotIn("Tu postulación", ajeno)
        self.assertNotIn("Candidatos (", ajeno)
        self.assertRegex(ajeno, r"<strong>2</strong> personas se han postulado")

    def test_el_conteo_publico_en_singular(self):
        oid = self._nueva()
        self._postular(oid, LUIS)
        self.assertContains(entrar_como(DUBAL).get(f"/ofertas/{oid}/"), "<strong>1</strong> persona se ha postulado", html=False)

    def test_los_cupos_se_ven_y_valen_al_crear(self):
        res = entrar_como(MATEO).post("/ofertas/nueva/", {"eid": self.NEXUS, "titulo": "Con cupos", "modalidad": "remoto", "estado": "abierta", "cupos": 4}, follow=True)
        self.assertEqual(res.context["oferta"].cupos, 4)
        self.assertContains(res, "0 de 4")
        invalida = entrar_como(MATEO).post("/ofertas/nueva/", {"eid": self.NEXUS, "titulo": "Sin", "modalidad": "remoto", "estado": "abierta", "cupos": 0})
        self.assertEqual(invalida.status_code, 200)
        self.assertFalse(invalida.context["form"].is_valid())

    def test_el_boton_aceptar_desaparece_sin_cupo(self):
        oid = self._nueva(cupos=1)
        self._postular(oid, LUIS)
        self.assertContains(entrar_como(MATEO).get(f"/ofertas/{oid}/"), 'value="aceptada"')
        self._decidir(LUIS, "aceptada", oid)
        self.assertNotContains(entrar_como(MATEO).get(f"/ofertas/{oid}/"), 'value="aceptada"')


class EquipoDeEmpresaTest(_ConDatosDeEjemplo):
    NEXUS = "emp_nexus01"
    CARLOS = "usr_carlos001"

    def _equipo(self):
        return {e["usuario"].uid for e in EmpleoService.listar_por_empresa(self.NEXUS) if e["actual"] is not False}

    def test_trabajo_aqui_pide_confirmacion(self):
        entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/trabajo-aqui/", {"cargo": "QA"})
        self.assertNotIn(LUIS, self._equipo())
        self.assertTrue(EmpleoService.tiene_solicitud(LUIS, self.NEXUS))
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/empleos/{LUIS}/responder/", {"accion": "aceptar"})
        self.assertIn(LUIS, self._equipo())

    def test_trabajo_aqui_exige_cargo(self):
        res = entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/trabajo-aqui/", {"cargo": " "}, follow=True)
        self.assertContains(res, "Indica tu cargo")
        self.assertFalse(EmpleoService.tiene_solicitud(LUIS, self.NEXUS))

    def test_invitar_entra_al_aceptar(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": LUIS, "cargo": "QA Lead"})
        self.assertNotIn(LUIS, self._equipo())
        self.assertContains(entrar_como(LUIS).get("/conexiones/"), "te invita a su equipo como QA Lead")
        self.assertTrue(any(a["id"] == f"invitacion_equipo:{self.NEXUS}" for a in avisos_para(LUIS, limite=50)))
        entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/invitacion/responder/", {"accion": "aceptar"})
        self.assertIn(LUIS, self._equipo())
        self.assertIsNone(EmpleoService.invitacion_de(LUIS, self.NEXUS))

    def test_rechazar_la_invitacion_no_suma(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": LUIS, "cargo": "QA"})
        entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/invitacion/responder/", {"accion": "rechazar"})
        self.assertNotIn(LUIS, self._equipo())
        self.assertIsNone(EmpleoService.invitacion_de(LUIS, self.NEXUS))

    def test_solo_el_administrador_invita_o_cancela(self):
        self.assertEqual(entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": DUBAL, "cargo": "QA"}).status_code, 403)
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": DUBAL, "cargo": "QA"})
        self.assertEqual(entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/invitacion/{DUBAL}/cancelar/").status_code, 403)
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitacion/{DUBAL}/cancelar/")
        self.assertIsNone(EmpleoService.invitacion_de(DUBAL, self.NEXUS))

    def test_nadie_responde_una_invitacion_ajena(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": LUIS, "cargo": "QA"})
        entrar_como(DUBAL).post(f"/empresas/{self.NEXUS}/equipo/invitacion/responder/", {"accion": "aceptar"})
        self.assertNotIn(DUBAL, self._equipo())
        self.assertIsNotNone(EmpleoService.invitacion_de(LUIS, self.NEXUS))

    def test_invitacion_y_solicitud_cruzadas_se_resuelven(self):
        entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/trabajo-aqui/", {"cargo": "QA"})
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": LUIS, "cargo": "QA"})
        self.assertIn(LUIS, self._equipo())
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": DUBAL, "cargo": "QA"})
        entrar_como(DUBAL).post(f"/empresas/{self.NEXUS}/equipo/trabajo-aqui/", {"cargo": "QA"})
        self.assertIn(DUBAL, self._equipo())

    def test_dejar_el_empleo_lo_conserva_como_anterior(self):
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/equipo/{self.CARLOS}/terminar/")
        self.assertNotIn(self.CARLOS, self._equipo())
        self.assertFalse(EmpleoService.es_empleado(self.CARLOS, self.NEXUS))
        empleo = next(e for e in EmpleoService.listar_por_usuario(self.CARLOS) if e["empresa"].eid == self.NEXUS)
        self.assertFalse(empleo["actual"])
        self.assertTrue(empleo["fecha_fin"])
        pagina = entrar_como(LUIS).get(f"/empresas/{self.NEXUS}/")
        self.assertContains(pagina, "Antes trabajaron aquí")
        self.assertIn(self.CARLOS, {e["usuario"].uid for e in pagina.context["antiguos"]})

    def test_la_empresa_quita_y_avisa(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/{self.CARLOS}/terminar/")
        self.assertNotIn(self.CARLOS, self._equipo())
        self.assertIn("Nexus Corp te quitó de su equipo", [n["titulo"] for n in NotificacionService.de_usuario(self.CARLOS)])

    def test_un_tercero_no_quita(self):
        self.assertEqual(entrar_como(LUIS).post(f"/empresas/{self.NEXUS}/equipo/{self.CARLOS}/terminar/").status_code, 403)
        self.assertIn(self.CARLOS, self._equipo())

    def test_el_administrador_no_puede_salir(self):
        res = entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/{MATEO}/terminar/", follow=True)
        self.assertContains(res, "Transfiérela primero")
        self.assertIn(MATEO, self._equipo())

    def test_el_conteo_y_las_rutas_solo_cuentan_a_los_de_hoy(self):
        antes = EmpresaService.resumen_edificios(ids=[self.NEXUS])[self.NEXUS]["empleados"]
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/equipo/{self.CARLOS}/terminar/")
        self.assertEqual(EmpresaService.resumen_edificios(ids=[self.NEXUS])[self.NEXUS]["empleados"], antes - 1)
        self.assertNotIn(self.NEXUS, ConexionService.saltos_a_empresas(self.CARLOS).keys() - set(ConexionService.saltos_a_empresas(LUIS)))
        self.assertNotEqual(ConexionService.saltos_a_empresas(self.CARLOS).get(self.NEXUS), 0)

    def test_quien_salio_no_puede_recibir_la_empresa(self):
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/equipo/{self.CARLOS}/terminar/")
        res = entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/transferir/", {"uid": self.CARLOS}, follow=True)
        self.assertContains(res, "Solo puedes transferirla a un miembro")

    def test_puede_volver_a_un_equipo(self):
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/equipo/{self.CARLOS}/terminar/")
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/equipo/invitar/", {"uid": self.CARLOS, "cargo": "Arquitecto"})
        entrar_como(self.CARLOS).post(f"/empresas/{self.NEXUS}/equipo/invitacion/responder/", {"accion": "aceptar"})
        self.assertIn(self.CARLOS, self._equipo())
        empleo = next(e for e in EmpleoService.listar_por_usuario(self.CARLOS) if e["empresa"].eid == self.NEXUS)
        self.assertEqual(empleo["cargo"], "Arquitecto")
        self.assertTrue(empleo["actual"])

    def test_cada_quien_ve_su_situacion_en_la_empresa(self):
        self.assertContains(entrar_como(self.CARLOS).get(f"/empresas/{self.NEXUS}/"), "Haces parte de este equipo")
        self.assertContains(entrar_como(LUIS).get(f"/empresas/{self.NEXUS}/"), "¿Trabajas aquí?")
        admin = entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/").content.decode()
        self.assertIn("Administras esta empresa", admin)
        self.assertNotIn(f"/empresas/{self.NEXUS}/equipo/{MATEO}/terminar/", admin)

    def test_no_quedan_alianzas(self):
        html = entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/").content.decode()
        self.assertNotIn("lianza", html)
        relaciones = {a["tipo"] if "tipo" in a else a.get("label") for a in entrar_como(LUIS).get("/grafo/api/data/").json()["edges"]}
        self.assertNotIn("ALIADA_DE", relaciones)


class AuditoriaDeCiclosTest(_ConDatosDeEjemplo):
    NEXUS = "emp_nexus01"
    FINTECH = "proy_fintech02"

    def _datos_proyecto(self, proyecto, estado):
        return {"nombre": proyecto.nombre, "estado": estado, "descripcion": "", "tecnologias": ""}

    def test_terminar_el_proyecto_responde_a_quien_esperaba(self):
        InvitacionService.solicitar_unirse(MARIA, self.FINTECH)
        InvitacionService.invitar_a_proyecto(WILSON, self.FINTECH, rol="QA")
        lider = PropiedadService.lider_de(self.FINTECH).uid
        res = entrar_como(lider).post(f"/proyectos/{self.FINTECH}/editar/", self._datos_proyecto(ProyectoService.get(self.FINTECH), "completado"))
        self.assertEqual(res.status_code, 302)
        self.assertIsNone(InvitacionService.estado_union(MARIA, self.FINTECH))
        self.assertIsNone(InvitacionService.tipo_invitacion_proyecto(WILSON, self.FINTECH))
        self.assertIn(f"{ProyectoService.get(self.FINTECH).nombre} terminó", [n["titulo"] for n in NotificacionService.de_usuario(MARIA)])

    def test_un_avance_que_termina_el_proyecto_tambien_responde(self):
        InvitacionService.solicitar_unirse(MARIA, self.FINTECH)
        lider = PropiedadService.lider_de(self.FINTECH).uid
        entrar_como(lider).post(f"/proyectos/{self.FINTECH}/avances/agregar/", {"texto": "Terminamos", "estado": "completado"})
        self.assertEqual(ProyectoService.get(self.FINTECH).estado, "completado")
        self.assertIsNone(InvitacionService.estado_union(MARIA, self.FINTECH))

    def test_a_un_proyecto_terminado_no_se_invita(self):
        lider = PropiedadService.lider_de(self.FINTECH).uid
        ProyectoService.update(self.FINTECH, estado="completado")
        res = entrar_como(lider).post(f"/proyectos/{self.FINTECH}/colaboradores/agregar/", {"uid": WILSON, "rol": "QA"}, follow=True)
        self.assertContains(res, "ya terminó")
        self.assertIsNone(InvitacionService.tipo_invitacion_proyecto(WILSON, self.FINTECH))

    def test_el_talento_sugerido_lleva_a_invitar(self):
        html = entrar_como(MATEO).get(f"/recomendaciones/?tab=talento&eid={self.NEXUS}").content.decode()
        self.assertIn(f"/empresas/{self.NEXUS}/?tab=gestion&amp;invitar=", html)
        res = entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/?tab=gestion&invitar={LUIS}")
        self.assertContains(res, f'<option value="{LUIS}" selected>', html=False)

    def test_quien_ya_tiene_invitacion_no_vuelve_a_sugerirse(self):
        sugeridos = entrar_como(MATEO).get(f"/recomendaciones/?tab=talento&eid={self.NEXUS}").context["rec_talento"]
        self.assertTrue(sugeridos)
        primero = sugeridos[0]["usuario"].uid
        EmpleoService.invitar(primero, self.NEXUS, "QA")
        despues = entrar_como(MATEO).get(f"/recomendaciones/?tab=talento&eid={self.NEXUS}").context["rec_talento"]
        self.assertNotIn(primero, [r["usuario"].uid for r in despues])

    def test_las_pantallas_de_empleos_hablan_de_empleos(self):
        for uid, ruta in ((MATEO, "/ofertas/nueva/"), (MATEO, "/ofertas/ofr_dataeng01/editar/"), (MATEO, "/ofertas/ofr_dataeng01/"), (MATEO, "/ofertas/")):
            with self.subTest(ruta=ruta):
                html = entrar_como(uid).get(ruta).content.decode()
                visible = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S))
                self.assertNotRegex(visible, r"[Vv]acante|Oferta Laboral")

    def test_sin_contrasena_guardada_no_rompe_ni_entra(self):
        db.cypher_query("MATCH (u:Usuario {uid: $uid}) REMOVE u.password_hash", {"uid": LUIS})
        self.assertIsNone(UsuarioService.autenticar("luis.angel@wheelson.com", "cualquiera"))


# ------------------------------------------------------------------------------
# Lo que probaría alguien que quiere hacer fallar la app durante la exposición
# ------------------------------------------------------------------------------
REGLAS_DE_INTEGRIDAD = {
    "empresa sin exactamente un administrador": "MATCH (e:Empresa) WITH e, COUNT { (:Usuario)-[:ADMINISTRA]->(e) } AS n WHERE n <> 1 RETURN e.nombre, n",
    "administrador que no trabaja en su empresa": "MATCH (u:Usuario)-[:ADMINISTRA]->(e:Empresa) WHERE NOT EXISTS { (u)-[t:TRABAJA_EN]->(e) WHERE coalesce(t.actual, true) } RETURN u.nombre, e.nombre",
    "proyecto sin exactamente un líder": "MATCH (p:Proyecto) WITH p, COUNT { (:Usuario)-[:LIDERA]->(p) } AS n WHERE n <> 1 RETURN p.nombre, n",
    "líder que no participa en su proyecto": "MATCH (u:Usuario)-[:LIDERA]->(p:Proyecto) WHERE NOT (u)-[:PARTICIPA_EN]->(p) RETURN u.nombre, p.nombre",
    "empleo sin empresa": "MATCH (o:Oferta) WHERE NOT (:Empresa)-[:PUBLICA]->(o) RETURN o.titulo",
    "aceptada que no está en el equipo": "MATCH (u:Usuario)-[:POSTULA_A {estado: 'aceptada'}]->(o:Oferta)<-[:PUBLICA]-(e:Empresa) WHERE NOT (u)-[:TRABAJA_EN]->(e) RETURN u.nombre, o.titulo",
    "más aceptados que cupos": "MATCH (o:Oferta) WITH o, COUNT { (:Usuario)-[:POSTULA_A {estado: 'aceptada'}]->(o) } AS n WHERE n > coalesce(o.cupos, 1) RETURN o.titulo, n",
    "abierto con los cupos llenos": "MATCH (o:Oferta {estado: 'abierta'}) WITH o, COUNT { (:Usuario)-[:POSTULA_A {estado: 'aceptada'}]->(o) } AS n WHERE n >= coalesce(o.cupos, 1) RETURN o.titulo, n",
    "cerrado con gente esperando": "MATCH (u:Usuario)-[r:POSTULA_A]->(o:Oferta {estado: 'cerrada'}) WHERE r.estado IN ['enviada', 'revision', 'entrevista'] RETURN u.nombre, o.titulo",
    "abierto con no seleccionados": "MATCH (u:Usuario)-[:POSTULA_A {estado: 'no_seleccionada'}]->(o:Oferta {estado: 'abierta'}) RETURN u.nombre, o.titulo",
    "postulación a un empleo propio": "MATCH (u:Usuario)-[:ADMINISTRA]->(:Empresa)-[:PUBLICA]->(o:Oferta)<-[:POSTULA_A]-(u) RETURN u.nombre, o.titulo",
    "postulación duplicada": "MATCH (u:Usuario)-[r:POSTULA_A]->(o:Oferta) WITH u, o, count(r) AS n WHERE n > 1 RETURN u.nombre, o.titulo, n",
    "conexión duplicada o en dos sentidos": "MATCH (a:Usuario)-[r:CONECTA_CON]-(b:Usuario) WHERE a.uid < b.uid WITH a, b, count(r) AS n WHERE n > 1 RETURN a.nombre, b.nombre, n",
    "conexión consigo mismo": "MATCH (a:Usuario)-[:CONECTA_CON]->(a) RETURN a.nombre",
    "pide conectar con quien ya está conectado": "MATCH (a:Usuario)-[:SOLICITA_CONEXION]-(b:Usuario) WHERE (a)-[:CONECTA_CON]-(b) RETURN a.nombre, b.nombre",
    "miembro con invitación o solicitud al mismo proyecto": "MATCH (u:Usuario)-[:INVITADO_A|SOLICITA_UNIRSE]->(p:Proyecto) WHERE (u)-[:PARTICIPA_EN]->(p) RETURN u.nombre, p.nombre",
    "pendiente en proyecto terminado": "MATCH (u:Usuario)-[:SOLICITA_UNIRSE]->(p:Proyecto {estado: 'completado'}) RETURN u.nombre, p.nombre UNION ALL MATCH (u:Usuario)-[:INVITADO_A {tipo: 'colaborar'}]->(p:Proyecto {estado: 'completado'}) RETURN u.nombre, p.nombre",
    "empleado actual con invitación o solicitud": "MATCH (u:Usuario)-[:INVITADO_A_TRABAJAR|SOLICITA_EMPLEO]->(e:Empresa) WHERE EXISTS { (u)-[t:TRABAJA_EN]->(e) WHERE coalesce(t.actual, true) } RETURN u.nombre, e.nombre",
    "más de un TRABAJA_EN a la misma empresa": "MATCH (u:Usuario)-[r:TRABAJA_EN]->(e:Empresa) WITH u, e, count(r) AS n WHERE n > 1 RETURN u.nombre, e.nombre, n",
    "empleo terminado sin fecha de fin": "MATCH (u:Usuario)-[t:TRABAJA_EN {actual: false}]->(e:Empresa) WHERE t.fecha_fin IS NULL RETURN u.nombre, e.nombre",
    "fin antes de inicio": "MATCH (u:Usuario)-[t:TRABAJA_EN]->(e:Empresa) WHERE t.fecha_fin < t.fecha_inicio RETURN u.nombre, e.nombre",
    "publicación sin autor": "MATCH (p:Publicacion) WHERE NOT ()-[:AUTOR_DE]->(p) RETURN p.pubid",
    "publicación de empresa sin quién la redactó": "MATCH (:Empresa)-[:AUTOR_DE]->(p:Publicacion) WHERE NOT (:Usuario)-[:REDACTA]->(p) RETURN p.pubid",
    "opina sobre lo que escribió": "MATCH (u:Usuario)-[:AUTOR_DE|REDACTA]->(p:Publicacion)<-[:PERCIBE]-(u) RETURN u.nombre, p.pubid",
    "opina dos veces": "MATCH (u:Usuario)-[r:PERCIBE]->(p:Publicacion) WITH u, p, count(r) AS n WHERE n > 1 RETURN u.nombre, p.pubid, n",
    "avance sin proyecto o sin autor": "MATCH (a:Avance) WHERE NOT ()-[:TIENE_AVANCE]->(a) OR NOT ()-[:REGISTRA]->(a) RETURN a.aid",
    "proyecto completado sin avance final": "MATCH (p:Proyecto {estado: 'completado'}) WHERE COUNT { (p)-[:TIENE_AVANCE]->(:Avance {estado: 'completado'}) } = 0 RETURN p.nombre",
    "correo duplicado (sin importar mayúsculas)": "MATCH (u:Usuario) WITH toLower(u.email) AS c, count(u) AS n WHERE n > 1 RETURN c, n",
    "empresa o habilidad duplicada (sin importar mayúsculas)": "MATCH (n) WHERE n:Empresa OR n:Habilidad WITH labels(n)[0] AS t, toLower(n.nombre) AS c, count(n) AS k WHERE k > 1 RETURN t, c, k",
    "nodo sin relaciones (huérfano)": "MATCH (n) WHERE (n:Oferta OR n:Proyecto OR n:Avance OR n:Publicacion) AND NOT (n)--() RETURN labels(n)[0], coalesce(n.titulo, n.nombre, n.aid, n.pubid)",
}


class _ConReglas(_ConDatosDeEjemplo):
    def assertIntegro(self):
        for regla, cypher in REGLAS_DE_INTEGRIDAD.items():
            filas, _ = db.cypher_query(cypher)
            self.assertEqual(filas, [], regla)

    def _contar(self):
        return db.cypher_query("MATCH (n) RETURN count(n)")[0][0][0], db.cypher_query("MATCH ()-[r]->() RETURN count(r)")[0][0][0]


class DatosDeDemoTest(TestCase):
    def test_la_red_cumple_todas_las_reglas(self):
        ejecutar_script_cypher("seed_data.cypher")
        ejecutar_script_cypher("datos_demo.cypher")
        for regla, cypher in REGLAS_DE_INTEGRIDAD.items():
            with self.subTest(regla=regla):
                self.assertEqual(db.cypher_query(cypher)[0], [])

    def test_el_comando_no_pisa_una_base_con_datos(self):
        ejecutar_script_cypher("seed_data.cypher")
        with self.assertRaises(CommandError):
            call_command("cargar_datos")

    def test_el_comando_carga_todo_desde_cero(self):
        call_command("cargar_datos", "--limpiar", verbosity=0)
        self.assertEqual(db.cypher_query("MATCH (u:Usuario) RETURN count(u)")[0][0][0], 40)

    def test_las_cuentas_de_demo_entran_con_su_contrasena(self):
        call_command("cargar_datos", "--limpiar", verbosity=0)
        texto = (SCRIPTS / "usuarios_demo.md").read_text(encoding="utf-8")
        filas = re.findall(r"\| [^|]+ \| (\S+@wheelson\.com) \| `([^`]+)` \|", texto)
        self.assertEqual(len(filas), 40)
        for correo, clave in filas[-3:] + filas[:2]:
            self.assertIsNotNone(UsuarioService.autenticar(correo, clave), correo)


class ExposicionEmpleosTest(_ConReglas):
    OID = "ofr_dataeng01"
    NEXUS = "emp_nexus01"

    def _nueva(self, cupos=1):
        return PropiedadService.crear_oferta(self.NEXUS, titulo="Reto", cupos=cupos).oid

    def _decidir(self, uid, estado, oid, sesion=MATEO):
        return entrar_como(sesion).post(f"/ofertas/{oid}/postulaciones/{uid}/estado/", {"estado": estado}, follow=True)

    def test_dos_aplican_aceptan_a_uno_y_el_otro_queda_respondido(self):
        oid = self._nueva()
        for uid in (LUIS, DUBAL):
            entrar_como(uid).post(f"/ofertas/{oid}/postular/", {"carta_presentacion": "Hola"})
        self._decidir(LUIS, "aceptada", oid)
        self.assertTrue(EmpleoService.es_empleado(LUIS, self.NEXUS))
        self.assertEqual(PostulacionService.obtener_estado(DUBAL, oid), "no_seleccionada")
        self.assertFalse(EmpleoService.es_empleado(DUBAL, self.NEXUS))
        pagina = entrar_como(DUBAL).get(f"/ofertas/{oid}/").content.decode()
        self.assertIn("No seleccionada", pagina)
        self.assertNotIn("Postularme", pagina)
        self.assertNotIn("Retirar mi postulación", pagina)
        self.assertIntegro()

    def test_nadie_mas_puede_postularse_a_un_empleo_cubierto(self):
        oid = self._nueva()
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        self._decidir(LUIS, "aceptada", oid)
        res = entrar_como(DUBAL).post(f"/ofertas/{oid}/postular/", follow=True)
        self.assertContains(res, "ya está cerrado")
        self.assertIsNone(PostulacionService.obtener_estado(DUBAL, oid))

    def test_rechazado_no_puede_volver_a_postularse(self):
        oid = self._nueva(cupos=2)
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        self._decidir(LUIS, "rechazada", oid)
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/", {"carta_presentacion": "Otra vez"})
        self.assertEqual(PostulacionService.obtener_estado(LUIS, oid), "rechazada")
        self.assertEqual(PostulacionService.contar(oid)[0], 1)

    def test_quien_retira_se_puede_volver_a_postular(self):
        oid = self._nueva()
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        entrar_como(LUIS).post(f"/ofertas/{oid}/postulaciones/{LUIS}/eliminar/")
        self.assertIsNone(PostulacionService.obtener_estado(LUIS, oid))
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        self.assertEqual(PostulacionService.obtener_estado(LUIS, oid), "enviada")

    def test_aceptar_a_quien_ya_retiro_desde_una_pagina_vieja(self):
        oid = self._nueva()
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        entrar_como(LUIS).post(f"/ofertas/{oid}/postulaciones/{LUIS}/eliminar/")
        res = self._decidir(LUIS, "aceptada", oid)
        self.assertContains(res, "Ya no se puede aceptar")
        self.assertFalse(EmpleoService.es_empleado(LUIS, self.NEXUS))
        self.assertEqual(OfertaService.get(oid).estado, "abierta")

    def test_aceptar_a_alguien_que_nunca_se_postulo(self):
        oid = self._nueva()
        res = self._decidir(LUIS, "aceptada", oid)
        self.assertContains(res, "Ya no se puede aceptar")
        self.assertFalse(EmpleoService.es_empleado(LUIS, self.NEXUS))

    def test_aceptar_en_un_empleo_que_ya_no_existe(self):
        oid = self._nueva()
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        entrar_como(MATEO).post(f"/ofertas/{oid}/eliminar/")
        res = entrar_como(MATEO).post(f"/ofertas/{oid}/postulaciones/{LUIS}/estado/", {"estado": "aceptada"})
        self.assertLess(res.status_code, 500)
        self.assertFalse(EmpleoService.es_empleado(LUIS, self.NEXUS))

    def test_doble_clic_en_aceptar_no_rompe_ni_duplica(self):
        oid = self._nueva(cupos=3)
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        self._decidir(LUIS, "aceptada", oid)
        self.assertContains(self._decidir(LUIS, "aceptada", oid), "Ya no se puede aceptar")
        filas = db.cypher_query("MATCH (:Usuario {uid: $u})-[r:TRABAJA_EN]->(:Empresa {eid: $e}) RETURN count(r)", {"u": LUIS, "e": self.NEXUS})[0]
        self.assertEqual(filas[0][0], 1)
        self.assertEqual(NotificacionService.de_usuario(LUIS)[0]["titulo"], "Nexus Corp te contrató")
        self.assertEqual(sum(n["titulo"] == "Nexus Corp te contrató" for n in NotificacionService.de_usuario(LUIS)), 1)

    def test_borrar_la_cuenta_del_contratado_no_deja_basura(self):
        oid = self._nueva()
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        self._decidir(LUIS, "aceptada", oid)
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/eliminar/")
        self.assertIsNone(UsuarioService.get(LUIS))
        self.assertEqual(PostulacionService.contar(oid), (0, 0))
        self.assertEqual(entrar_como(MATEO).get(f"/ofertas/{oid}/").status_code, 200)
        self.assertEqual(entrar_como(MATEO).get(f"/empresas/{self.NEXUS}/").status_code, 200)

    def test_eliminar_el_empleo_conserva_al_contratado(self):
        oid = self._nueva()
        entrar_como(LUIS).post(f"/ofertas/{oid}/postular/")
        self._decidir(LUIS, "aceptada", oid)
        entrar_como(MATEO).post(f"/ofertas/{oid}/eliminar/")
        self.assertIsNone(OfertaService.get(oid))
        self.assertTrue(EmpleoService.es_empleado(LUIS, self.NEXUS))
        self.assertIntegro()

    def test_eliminar_la_empresa_borra_sus_empleos_sin_dejar_huerfanos(self):
        entrar_como(MATEO).post(f"/empresas/{self.NEXUS}/eliminar/")
        self.assertIsNone(EmpresaService.get(self.NEXUS))
        self.assertIsNone(OfertaService.get(self.OID))
        self.assertIntegro()
        self.assertEqual(entrar_como(DUBAL).get(f"/usuarios/{DUBAL}/").status_code, 200)

    def test_borrar_una_habilidad_exigida_recalcula_sin_romper(self):
        entrar_como(WILSON).post("/habilidades/hab_py01/eliminar/")
        self.assertEqual(entrar_como(DUBAL).get(f"/ofertas/{self.OID}/").status_code, 200)
        self.assertEqual(entrar_como(DUBAL).get("/ofertas/").status_code, 200)
        self.assertEqual(entrar_como(DUBAL).get("/analitica/").status_code, 200)
        self.assertIntegro()

    def test_empleo_sin_requisitos_no_divide_entre_cero(self):
        oid = self._nueva()
        res = entrar_como(LUIS).get(f"/ofertas/{oid}/")
        self.assertContains(res, "Sin requisitos publicados")
        self.assertEqual(entrar_como(LUIS).get("/").status_code, 200)

    def test_cambiar_los_cupos_a_mano_no_se_salta_las_reglas(self):
        oid = self._nueva(cupos=2)
        base = {"titulo": "Reto", "modalidad": "remoto", "estado": "abierta"}
        for malo in ("0", "-1", "101", "abc", "1.5"):
            with self.subTest(cupos=malo):
                res = entrar_como(MATEO).post(f"/ofertas/{oid}/editar/", {**base, "cupos": malo})
                self.assertEqual(res.status_code, 200)
                self.assertEqual(OfertaService.get(oid).cupos, 2)

    def test_salario_al_reves_o_negativo(self):
        base = {"eid": self.NEXUS, "titulo": "Reto", "modalidad": "remoto", "estado": "abierta", "cupos": 1}
        for minimo, maximo in ((9000, 100), (-5, 100), (100, -5)):
            with self.subTest(minimo=minimo, maximo=maximo):
                res = entrar_como(MATEO).post("/ofertas/nueva/", {**base, "salario_min": minimo, "salario_max": maximo})
                self.assertEqual(res.status_code, 200)
                self.assertFalse(res.context["form"].is_valid())


class ExposicionEntradasTest(_ConReglas):
    MALOS = ["' OR 1=1 //", '"}) DETACH DELETE n //', "<script>alert(1)</script>", "🚀🚀🚀", "x" * 5000, "%00", "../../etc/passwd", "'; MATCH (n) DETACH DELETE n; //"]

    def _rutas(self):
        from django.urls import get_resolver
        for patron in get_resolver("core.urls").url_patterns:
            yield patron

    def _con(self, patron, valor):
        ruta = str(patron.pattern)
        return "/" + re.sub(r"<(?:\w+:)?\w+>", valor, ruta)

    def test_ids_falsos_en_todas_las_rutas_nunca_dan_error_del_servidor(self):
        antes = self._contar()
        cliente = entrar_como(WILSON)
        cliente.raise_request_exception = False
        for patron in self._rutas():
            if patron.name in ("logout",):
                continue
            url = self._con(patron, "no_existe")
            for metodo in (cliente.get, cliente.post):
                with self.subTest(url=url, metodo=metodo.__name__):
                    res = metodo(url)
                    self.assertLess(res.status_code, 500, url)
        self.assertEqual(self._contar(), antes)

    def test_ids_con_inyeccion_en_todas_las_rutas(self):
        antes = self._contar()
        cliente = entrar_como(LUIS)
        cliente.raise_request_exception = False
        for patron in self._rutas():
            if patron.name in ("logout",):
                continue
            for malo in ("x'OR'1'='1", "abc%3Cscript%3E"):
                url = self._con(patron, malo)
                with self.subTest(url=url):
                    self.assertLess(cliente.get(url).status_code, 500)
                    self.assertLess(cliente.post(url).status_code, 500)
        self.assertEqual(self._contar(), antes)

    def test_busquedas_con_cualquier_cosa(self):
        antes = self._contar()
        cliente = entrar_como(LUIS)
        for ruta in ("/usuarios/", "/empresas/", "/ofertas/", "/proyectos/", "/habilidades/", "/conexiones/"):
            for malo in self.MALOS:
                with self.subTest(ruta=ruta, malo=malo[:20]):
                    res = cliente.get(ruta, {"q": malo})
                    self.assertEqual(res.status_code, 200)
                    self.assertNotIn("<script>alert(1)", res.content.decode())
        self.assertEqual(self._contar(), antes)

    def test_parametros_de_consultas_y_grafo_con_cualquier_cosa(self):
        antes = self._contar()
        cliente = entrar_como(WILSON)
        cliente.raise_request_exception = False
        for tab in ("camino", "comun", "similares", "ruta_empresa", "demandadas", "candidatos", "ruta_oferta", "proyectos"):
            for malo in self.MALOS:
                with self.subTest(tab=tab, malo=malo[:20]):
                    res = cliente.get("/consultas/", {"tab": tab, "uid1": malo, "uid2": malo, "eid": malo, "oid": malo, "pid": malo})
                    self.assertLess(res.status_code, 500)
                    self.assertNotIn("<script>alert(1)", res.content.decode())
        for malo in self.MALOS:
            self.assertLess(cliente.get("/grafo/", {"uid": malo, "subgrafo": malo}).status_code, 500)
            self.assertLess(cliente.get("/grafo/api/data/", {"uid": malo, "subgrafo": malo, "tipos": malo}).status_code, 500)
            self.assertLess(cliente.get("/recomendaciones/", {"tab": malo, "pid": malo, "eid": malo}).status_code, 500)
            self.assertLess(cliente.get("/conexiones/", {"uid": malo}).status_code, 500)
            self.assertLess(cliente.get("/", {"ver": malo, "pagina": malo}).status_code, 500)
        self.assertEqual(self._contar(), antes)

    def test_misma_persona_como_origen_y_destino(self):
        for tab in ("camino", "comun", "similares"):
            with self.subTest(tab=tab):
                res = entrar_como(LUIS).get("/consultas/", {"tab": tab, "uid1": LUIS, "uid2": LUIS})
                self.assertEqual(res.status_code, 200)

    def test_html_guardado_nunca_se_ejecuta(self):
        veneno = "<script>alert(1)</script><img src=x onerror=alert(2)>"
        comillas = "';alert(3);//\""
        cliente = entrar_como(MATEO)
        cliente.post(f"/usuarios/{MATEO}/editar/", {"nombre": veneno[:40], "apellido": comillas, "email": "mateo@wheelson.com", "titulo_profesional": veneno, "ubicacion": veneno, "biografia": veneno})
        cliente.post("/", {"texto": veneno})
        cliente.post("/proyectos/nuevo/", {"nombre": veneno[:100], "descripcion": veneno, "estado": "activo", "tecnologias": veneno, "fecha_inicio": "2026-01-01"})
        cliente.post("/empresas/nueva/", {"nombre": veneno[:100], "industria": veneno[:50], "ubicacion": veneno[:50], "tamano": "pequena", "descripcion": veneno})
        cliente.post("/ofertas/nueva/", {"eid": "emp_nexus01", "titulo": veneno, "modalidad": "remoto", "estado": "abierta", "cupos": 1, "descripcion": veneno})
        for uid, ruta in ((LUIS, "/"), (LUIS, f"/usuarios/{MATEO}/"), (LUIS, "/usuarios/"), (LUIS, "/empresas/"), (LUIS, "/ofertas/"), (LUIS, "/proyectos/"), (LUIS, "/conexiones/"), (LUIS, "/grafo/"), (LUIS, "/consultas/"), (LUIS, "/analitica/"), (LUIS, f"/conexiones/?uid={MATEO}")):
            with self.subTest(ruta=ruta):
                html = entrar_como(uid).get(ruta).content.decode()
                self.assertNotIn("<script>alert(1)", html)
                self.assertNotIn("<img src=x", html)

    def test_correo_repetido_aunque_cambie_mayusculas(self):
        res = ClienteAnonimo().post("/registro/", {"nombre": "Otro", "apellido": "Mateo", "email": "MATEO@wheelson.com", "password": "Segura#2026", "password_confirm": "Segura#2026"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(db.cypher_query("MATCH (u:Usuario) WHERE toLower(u.email) = 'mateo@wheelson.com' RETURN count(u)")[0][0][0], 1)

    def test_empresa_y_habilidad_repetidas_aunque_cambie_mayusculas(self):
        entrar_como(LUIS).post("/empresas/nueva/", {"nombre": "NEXUS  corp", "industria": "x", "tamano": "pequena"})
        self.assertEqual(db.cypher_query("MATCH (e:Empresa) WHERE toLower(e.nombre) STARTS WITH 'nexus' RETURN count(e)")[0][0][0], 1)
        entrar_como(WILSON).post("/habilidades/nueva/", {"nombre": "PYTHON", "categoria": "tecnica"})
        self.assertEqual(db.cypher_query("MATCH (h:Habilidad) WHERE toLower(h.nombre) = 'python' RETURN count(h)")[0][0][0], 1)

    def test_campos_de_solo_espacios_no_crean_nada(self):
        antes = self._contar()
        cliente = entrar_como(MATEO)
        cliente.post("/", {"texto": "     "})
        cliente.post("/proyectos/nuevo/", {"nombre": "   ", "estado": "activo"})
        cliente.post("/empresas/nueva/", {"nombre": "   ", "industria": "  ", "tamano": "pequena"})
        cliente.post("/ofertas/nueva/", {"eid": "emp_nexus01", "titulo": "   ", "modalidad": "remoto", "estado": "abierta"})
        cliente.post("/empresas/emp_nexus01/equipo/invitar/", {"uid": LUIS, "cargo": "   "})
        self.assertEqual(self._contar(), antes)

    def test_fecha_de_fin_antes_del_inicio(self):
        res = entrar_como(MATEO).post("/proyectos/nuevo/", {"nombre": "Viaje en el tiempo", "estado": "activo", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-01-01"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context["form"].is_valid())

    def test_fechas_invalidas_no_rompen(self):
        cliente = entrar_como(MATEO)
        cliente.raise_request_exception = False
        self.assertLess(cliente.post("/proyectos/nuevo/", {"nombre": "Fechas", "estado": "activo", "fecha_inicio": "31/31/2026"}).status_code, 500)
        self.assertLess(cliente.post("/proyectos/proy_graph01/colaboradores/agregar/", {"uid": LUIS, "rol": "QA", "fecha_inicio": "ayer"}).status_code, 500)
        self.assertLess(cliente.post(f"/usuarios/{MATEO}/experiencia/agregar/", {"eid": "emp_techin02", "cargo": "QA", "fecha_inicio": "ayer"}).status_code, 500)

    def test_valores_inventados_en_listas_cerradas(self):
        cliente = entrar_como(MATEO)
        antes = self._contar()
        cliente.post("/ofertas/nueva/", {"eid": "emp_nexus01", "titulo": "X", "modalidad": "marte", "estado": "abierta"})
        cliente.post("/ofertas/nueva/", {"eid": "emp_nexus01", "titulo": "X", "modalidad": "remoto", "estado": "congelada"})
        cliente.post("/ofertas/nueva/", {"eid": "emp_globant03", "titulo": "Ajena", "modalidad": "remoto", "estado": "abierta"})
        cliente.post("/proyectos/proy_graph01/avances/agregar/", {"texto": "x", "estado": "inventado"})
        self.assertEqual(self._contar(), antes)

    def test_texto_enorme(self):
        cliente = entrar_como(MATEO)
        cliente.raise_request_exception = False
        antes = self._contar()
        self.assertLess(cliente.post("/", {"texto": "x" * 200000}).status_code, 500)
        self.assertEqual(self._contar(), antes)
        self.assertLess(cliente.post("/ofertas/ofr_dataeng01/postular/", {"carta_presentacion": "x" * 200000}).status_code, 500)


class ExposicionPermisosTest(_ConReglas):
    def test_sin_sesion_nada_se_ve_ni_se_cambia(self):
        from django.urls import get_resolver
        antes = self._contar()
        anonimo = ClienteAnonimo()
        anonimo.raise_request_exception = False
        for patron in get_resolver("core.urls").url_patterns:
            if patron.name in ("login", "registro"):
                continue
            url = "/" + re.sub(r"<(?:\w+:)?\w+>", "x", str(patron.pattern))
            with self.subTest(url=url):
                # La API responde 401 en JSON; las páginas llevan a iniciar sesión
                self.assertIn(anonimo.get(url).status_code, (301, 302, 401))
                self.assertIn(anonimo.post(url).status_code, (301, 302, 401))
        self.assertEqual(self._contar(), antes)

    def test_sin_token_csrf_se_rechaza(self):
        cliente = ClienteAnonimo(enforce_csrf_checks=True)
        cliente.force_login = None
        res = cliente.post("/login/", {"email": "mateo@wheelson.com", "password": "x"})
        self.assertEqual(res.status_code, 403)

    def test_entrar_por_url_a_lo_que_no_le_toca(self):
        antes = self._contar()
        luis = entrar_como(LUIS)
        for url in ("/ofertas/ofr_dataeng01/editar/", "/ofertas/ofr_dataeng01/eliminar/", "/empresas/emp_nexus01/editar/", "/empresas/emp_nexus01/eliminar/", "/proyectos/proy_graph01/editar/", "/proyectos/proy_graph01/eliminar/", f"/usuarios/{MATEO}/editar/", f"/usuarios/{MATEO}/eliminar/"):
            with self.subTest(url=url):
                self.assertEqual(luis.get(url).status_code, 403)
                self.assertEqual(luis.post(url, {"titulo": "Hackeado", "nombre": "Hackeado"}).status_code, 403)
        for url, datos in (("/ofertas/ofr_dataeng01/postulaciones/usr_dubal003/estado/", {"estado": "aceptada"}), ("/ofertas/ofr_dataeng01/postulaciones/usr_dubal003/eliminar/", {}), ("/habilidades/nueva/", {"nombre": "Hack", "categoria": "tecnica"}), ("/habilidades/hab_py01/eliminar/", {}), ("/empresas/emp_nexus01/transferir/", {"uid": LUIS})):
            with self.subTest(url=url):
                self.assertEqual(luis.post(url, datos).status_code, 403)
        self.assertEqual(self._contar(), antes)

    def test_nadie_se_vuelve_administrador_por_el_formulario(self):
        cliente = entrar_como(LUIS)
        cliente.post(f"/usuarios/{LUIS}/editar/", {"nombre": "Luis", "apellido": "Angel", "email": "luis.angel@wheelson.com", "rol": "admin"})
        self.assertEqual(UsuarioService.get(LUIS).rol, "usuario")
        ClienteAnonimo().post("/registro/", {"nombre": "Eva", "apellido": "Admin", "email": "eva@wheelson.com", "password": "Segura#2026", "password_confirm": "Segura#2026", "rol": "admin"})
        self.assertEqual(UsuarioService.get_by_email("eva@wheelson.com").rol, "usuario")

    def test_postularse_como_otra_persona_es_imposible(self):
        entrar_como(LUIS).post("/ofertas/ofr_arch02/postular/", {"uid": DUBAL, "uid_candidato": DUBAL})
        self.assertIsNone(PostulacionService.obtener_estado(DUBAL, "ofr_arch02"))
        self.assertEqual(PostulacionService.obtener_estado(LUIS, "ofr_arch02"), "enviada")

    def test_la_postulacion_ajena_no_se_lee_por_el_grafo(self):
        aristas = entrar_como(LUIS).get("/grafo/api/data/").json()["edges"]
        self.assertFalse([a for a in aristas if a.get("from") == DUBAL and a.get("to") == "ofr_dataeng01"])

    def test_el_administrador_anterior_ya_no_puede_actuar(self):
        carlos = "usr_carlos001"
        entrar_como(MATEO).post("/empresas/emp_nexus01/transferir/", {"uid": carlos})
        entrar_como(carlos).post("/empresas/emp_nexus01/invitacion/responder/", {"accion": "aceptar"})
        self.assertEqual(PropiedadService.administrador_de("emp_nexus01").uid, carlos)
        self.assertEqual(entrar_como(MATEO).post("/ofertas/ofr_dataeng01/postulaciones/usr_dubal003/estado/", {"estado": "aceptada"}).status_code, 403)
        self.assertFalse(EmpleoService.es_empleado(DUBAL, "emp_nexus01"))
        self.assertIntegro()

    def test_sesion_de_una_cuenta_borrada(self):
        cliente = entrar_como(LUIS)
        UsuarioService.delete(LUIS)
        res = cliente.get("/")
        self.assertIn(res.status_code, (301, 302))
        self.assertIn("/login/", res["Location"])
        self.assertIn(cliente.post("/", {"texto": "fantasma"}).status_code, (301, 302))
        self.assertEqual(db.cypher_query("MATCH (p:Publicacion {texto: 'fantasma'}) RETURN count(p)")[0][0][0], 0)


class ExposicionRedTest(_ConReglas):
    def test_conectar_consigo_mismo(self):
        antes = self._contar()
        entrar_como(LUIS).post("/conexiones/conectar/", {"uid_destino": LUIS})
        self.assertEqual(self._contar(), antes)

    def test_conectar_dos_veces_y_de_vuelta_no_duplica(self):
        wilson, jose = WILSON, "usr_jose012"
        entrar_como(wilson).post("/conexiones/conectar/", {"uid_destino": jose})
        entrar_como(wilson).post("/conexiones/conectar/", {"uid_destino": jose})
        entrar_como(jose).post("/conexiones/conectar/", {"uid_destino": wilson})
        entrar_como(jose).post("/conexiones/conectar/", {"uid_destino": wilson})
        self.assertIntegro()

    def test_aceptar_una_solicitud_que_no_existe(self):
        antes = self._contar()
        res = entrar_como(WILSON).post(f"/conexiones/solicitudes/{MARIA}/responder/", {"accion": "aceptar"}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._contar()[1], antes[1])

    def test_ruta_entre_personas_sin_camino(self):
        db.cypher_query("CREATE (:Usuario {uid: 'usr_isla', nombre: 'Isla', apellido: 'Sola', email: 'isla@wheelson.com', rol: 'usuario'})")
        for tab, datos in (("camino", {"uid1": LUIS, "uid2": "usr_isla"}), ("ruta_empresa", {"uid1": "usr_isla", "eid": "emp_nexus01"}), ("ruta_oferta", {"uid1": "usr_isla", "oid": "ofr_dataeng01"}), ("comun", {"uid1": LUIS, "uid2": "usr_isla"}), ("similares", {"uid1": "usr_isla"})):
            with self.subTest(tab=tab):
                self.assertEqual(entrar_como(LUIS).get("/consultas/", {"tab": tab, **datos}).status_code, 200)

    def test_una_persona_nueva_ve_todas_las_pantallas_sin_datos(self):
        db.cypher_query("CREATE (:Usuario {uid: 'usr_nueva', nombre: 'Nueva', apellido: 'Sin Nada', email: 'nueva@wheelson.com', rol: 'usuario'})")
        cliente = entrar_como("usr_nueva")
        for ruta in ("/", "/usuarios/usr_nueva/", "/conexiones/", "/recomendaciones/", "/recomendaciones/?tab=empleos", "/recomendaciones/?tab=colaboradores", "/recomendaciones/?tab=talento", "/analitica/", "/grafo/", "/consultas/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)

    def test_base_casi_vacia_no_rompe(self):
        db.cypher_query("MATCH (n) WHERE NOT n.uid = $u DETACH DELETE n", {"u": LUIS})
        cliente = entrar_como(LUIS)
        for ruta in ("/", "/usuarios/", "/empresas/", "/ofertas/", "/proyectos/", "/habilidades/", "/conexiones/", "/recomendaciones/", "/analitica/", "/grafo/", "/grafo/api/data/", "/consultas/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)

    def test_terminar_un_proyecto_y_borrarlo_no_deja_avances_sueltos(self):
        lider = PropiedadService.lider_de("proy_graph01").uid
        entrar_como(lider).post("/proyectos/proy_graph01/eliminar/")
        self.assertIsNone(ProyectoService.get("proy_graph01"))
        self.assertIntegro()

    def test_borrar_una_cuenta_con_todo_no_deja_basura(self):
        # Primero transfiere lo que administra, como exige la app
        carlos = "usr_carlos001"
        db.cypher_query("MATCH (u:Usuario {uid: $u})-[r:ADMINISTRA|LIDERA]->() DELETE r", {"u": LUIS})
        entrar_como(LUIS).post(f"/usuarios/{LUIS}/eliminar/")
        self.assertIsNone(UsuarioService.get(LUIS))
        self.assertIntegro()
        self.assertEqual(entrar_como(carlos).get("/").status_code, 200)

    def test_no_se_puede_borrar_al_ultimo_administrador(self):
        entrar_como(WILSON).post(f"/usuarios/{WILSON}/eliminar/")
        self.assertIsNotNone(UsuarioService.get(WILSON))

    def test_quien_administra_no_puede_borrarse_sin_transferir(self):
        entrar_como(MATEO).post(f"/usuarios/{MATEO}/eliminar/")
        self.assertIsNotNone(UsuarioService.get(MATEO))
        self.assertIntegro()


class ConcurrenciaTest(_ConReglas):
    """Varias personas a la vez, en hilos reales: lo que un doble clic o dos pestañas provocan."""

    NEXUS = "emp_nexus01"

    def _a_la_vez(self, *tareas):
        with ThreadPoolExecutor(max_workers=len(tareas)) as hilos:
            return list(hilos.map(lambda tarea: tarea(), tareas))

    def _empleo(self, cupos, *uids):
        oid = PropiedadService.crear_oferta(self.NEXUS, titulo="Carrera", cupos=cupos).oid
        for uid in uids:
            PostulacionService.postular(uid, oid)
        return oid

    GENTE = (LUIS, DUBAL, WILSON, MARIA, "usr_jose012", "usr_miguel010")

    def test_un_cupo_y_seis_aceptados_a_la_vez(self):
        oid = self._empleo(1, *self.GENTE)
        resultados = self._a_la_vez(*[lambda u=u: PostulacionService.contratar(u, oid) for u in self.GENTE])
        self.assertEqual(sum(r is not None for r in resultados), 1)
        self.assertEqual(PostulacionService.contar(oid)[1], 1)
        self.assertEqual(OfertaService.get(oid).estado, "cerrada")
        self.assertIntegro()

    def test_dos_cupos_y_seis_aceptados_a_la_vez(self):
        oid = self._empleo(2, *self.GENTE)
        self._a_la_vez(*[lambda u=u: PostulacionService.contratar(u, oid) for u in self.GENTE])
        self.assertEqual(PostulacionService.contar(oid)[1], 2)
        self.assertIntegro()

    def test_doble_clic_en_aceptar_solo_cuenta_una_vez(self):
        oid = self._empleo(3, LUIS)
        resultados = self._a_la_vez(*[lambda: PostulacionService.contratar(LUIS, oid) for _ in range(8)])
        self.assertEqual(sum(r is not None for r in resultados), 1)
        self.assertIntegro()

    def test_aceptar_y_rechazar_a_la_vez_gana_uno_solo(self):
        oid = self._empleo(2, LUIS)
        self._a_la_vez(lambda: PostulacionService.contratar(LUIS, oid), lambda: PostulacionService.cambiar_estado(LUIS, oid, "rechazada"), lambda: PostulacionService.contratar(LUIS, oid), lambda: PostulacionService.cambiar_estado(LUIS, oid, "rechazada"))
        estado = PostulacionService.obtener_estado(LUIS, oid)
        self.assertEqual(EmpleoService.es_empleado(LUIS, self.NEXUS), estado == "aceptada")
        self.assertIntegro()

    def test_retirar_y_aceptar_a_la_vez_queda_coherente(self):
        oid = self._empleo(2, LUIS)
        self._a_la_vez(lambda: PostulacionService.retirar(LUIS, oid), lambda: PostulacionService.contratar(LUIS, oid))
        estado = PostulacionService.obtener_estado(LUIS, oid)
        self.assertEqual(EmpleoService.es_empleado(LUIS, self.NEXUS), estado == "aceptada")

    def test_postularse_muchas_veces_a_la_vez_crea_una_sola(self):
        oid = self._empleo(1)
        self._a_la_vez(*[lambda: PostulacionService.postular_si_abierta(LUIS, oid) for _ in range(8)])
        self.assertEqual(PostulacionService.contar(oid)[0], 1)
        self.assertIntegro()

    def test_no_se_postula_mientras_se_cierra(self):
        oid = self._empleo(1, DUBAL)
        self._a_la_vez(lambda: PostulacionService.contratar(DUBAL, oid), lambda: PostulacionService.postular_si_abierta(LUIS, oid))
        self.assertIn(PostulacionService.obtener_estado(LUIS, oid), (None, "no_seleccionada"))
        self.assertIntegro()

    def test_dos_personas_se_piden_conexion_a_la_vez(self):
        a, b = WILSON, "usr_jose012"
        tareas = [lambda: InvitacionService.solicitar_conexion(a, b) for _ in range(6)] + [lambda: InvitacionService.solicitar_conexion(b, a) for _ in range(6)]
        self._a_la_vez(*tareas)
        pendientes = db.cypher_query("MATCH (:Usuario {uid: $a})-[r:SOLICITA_CONEXION]-(:Usuario {uid: $b}) RETURN count(r)", {"a": a, "b": b})[0][0][0]
        conexiones = db.cypher_query("MATCH (:Usuario {uid: $a})-[r:CONECTA_CON]-(:Usuario {uid: $b}) RETURN count(r)", {"a": a, "b": b})[0][0][0]
        self.assertLessEqual(pendientes, 1)
        self.assertLessEqual(conexiones, 1)
        self.assertEqual(pendientes + conexiones, 1)
        self.assertIntegro()

    def test_opinar_muchas_veces_a_la_vez_deja_una_o_ninguna(self):
        pubid = "pub_dubal01"
        self._a_la_vez(*[lambda: PublicacionService.percibir(WILSON, pubid, "buena") for _ in range(9)])
        self.assertLessEqual(db.cypher_query("MATCH (:Usuario {uid: $u})-[r:PERCIBE]->(:Publicacion {pubid: $p}) RETURN count(r)", {"u": WILSON, "p": pubid})[0][0][0], 1)

    def test_invitar_al_equipo_muchas_veces_a_la_vez(self):
        self._a_la_vez(*[lambda: EmpleoService.invitar(LUIS, self.NEXUS, "QA") for _ in range(6)])
        self.assertEqual(len(EmpleoService.invitaciones_de_empresa(self.NEXUS)), 1)
        self.assertIntegro()

    def test_pedir_unirse_muchas_veces_a_la_vez(self):
        self._a_la_vez(*[lambda: InvitacionService.solicitar_unirse(WILSON, "proy_fintech02") for _ in range(6)])
        self.assertEqual(db.cypher_query("MATCH (:Usuario {uid: $u})-[r:SOLICITA_UNIRSE]->(:Proyecto {pid: 'proy_fintech02'}) RETURN count(r)", {"u": WILSON})[0][0][0], 1)


class TemaOscuroTest(_ConDatosDeEjemplo):
    def test_el_selector_esta_en_la_cuenta_y_en_el_acceso(self):
        for html in (entrar_como(LUIS).get("/").content.decode(), ClienteAnonimo().get("/login/").content.decode(), ClienteAnonimo().get("/registro/").content.decode()):
            self.assertIn('data-ws-tema="oscuro"', html)
            self.assertIn('data-ws-tema="claro"', html)

    def test_el_tema_se_aplica_antes_de_cargar_los_estilos(self):
        html = ClienteAnonimo().get("/login/").content.decode()
        self.assertLess(html.index("wheelson-tema"), html.index("vendor/daisyui"))
        self.assertLess(html.index("wheelson-compat.css"), html.index("wheelson-oscuro.css"))

    def test_el_claro_sigue_siendo_el_predeterminado(self):
        html = ClienteAnonimo().get("/login/").content.decode()
        self.assertNotIn('<html lang="es" data-theme="wheelson" data-tema', html)

    def test_el_oscuro_es_negro_y_verde(self):
        css = open(finders.find("css/wheelson-oscuro.css"), encoding="utf-8").read()
        self.assertIn("--surface: #0E1116;", css)
        self.assertIn("--primary: #00B84C;", css)
        self.assertNotIn("#D9483B", css)
        self.assertNotIn("#6D1F6B", css)

    def test_los_graficos_toman_el_color_del_tema(self):
        html = entrar_como(LUIS).get("/analitica/").content.decode()
        self.assertIn("colorDe('--grafico-2')", html)
        self.assertNotIn("backgroundColor: '#D9483B'", html)

    def test_lo_dibujado_con_imagen_tambien_cambia(self):
        self.assertTrue(finders.find("img/rueda-mini-verde.svg"))
        self.assertNotIn("#D9483B", open(finders.find("img/rueda-mini-verde.svg"), encoding="utf-8").read())
        css = open(finders.find("css/wheelson-oscuro.css"), encoding="utf-8").read()
        for selector in (".ws-panel-avisos", "#ola-trazo", "rueda-mini-verde"):
            self.assertIn(selector, css)


class LoMioPrimeroTest(_ConDatosDeEjemplo):
    CARLOS = "usr_carlos001"

    def _esperado(self, cypher, uid, clave):
        return {f[0] for f in db.cypher_query(cypher, {"uid": uid})[0]}

    def test_proyectos_primero_los_que_lidero_y_luego_donde_participo(self):
        res = entrar_como(self.CARLOS).get("/proyectos/")
        relaciones = [p.relacion for p in res.context["proyectos"]]
        lideradas = self._esperado("MATCH (:Usuario {uid: $uid})-[:LIDERA]->(p) RETURN p.pid", self.CARLOS, "pid")
        participa = self._esperado("MATCH (:Usuario {uid: $uid})-[:PARTICIPA_EN]->(p) RETURN p.pid", self.CARLOS, "pid") - lideradas
        self.assertTrue(lideradas and participa)
        self.assertEqual([r for r in relaciones if r], ["lidera"] * len(lideradas) + ["participa"] * len(participa))
        self.assertEqual(relaciones[:len(lideradas) + len(participa)], [r for r in relaciones if r])
        self.assertContains(res, "Tu proyecto · lo lideras")
        self.assertContains(res, "Participas")

    def test_empresas_primero_la_que_administro_y_luego_donde_trabajo(self):
        res = entrar_como(MATEO).get("/empresas/")
        primera = res.context["empresas"][0]
        self.assertEqual((primera.eid, primera.relacion), ("emp_nexus01", "administra"))
        self.assertContains(res, "La administras")
        res = entrar_como(self.CARLOS).get("/empresas/")
        self.assertEqual(res.context["empresas"][0].relacion, "trabaja")
        self.assertContains(res, "Trabajas aquí")

    def test_quien_ya_no_trabaja_ahi_no_la_ve_como_suya(self):
        entrar_como(self.CARLOS).post(f"/empresas/emp_nexus01/equipo/{self.CARLOS}/terminar/")
        res = entrar_como(self.CARLOS).get("/empresas/")
        self.assertFalse(any(e.relacion for e in res.context["empresas"]))
        self.assertNotContains(res, "Trabajas aquí")

    def test_sin_relacion_no_hay_marca(self):
        db.cypher_query("CREATE (:Usuario {uid: 'usr_sola', nombre: 'Sola', apellido: 'Nueva', email: 'sola@wheelson.com', rol: 'usuario'})")
        for ruta, marca in (("/proyectos/", "ws-carpeta__mia"), ("/empresas/", "ws-edificio__mia")):
            self.assertNotContains(entrar_como("usr_sola").get(ruta), marca)

    def test_el_orden_se_respeta_al_cargar_mas_sin_repetir(self):
        uid = self.CARLOS
        primera = [p.pid for p in entrar_como(uid).get("/proyectos/").context["proyectos"]]
        todos = [p.pid for p in entrar_como(uid).get("/proyectos/?pagina=10").context["proyectos"]]
        self.assertEqual(todos[:len(primera)], primera)
        self.assertEqual(len(todos), len(set(todos)))

    def test_el_fragmento_lleva_la_marca(self):
        self.assertContains(entrar_como(MATEO).get("/empresas/?fragmento=1"), "La administras")
        self.assertContains(entrar_como(MATEO).get("/proyectos/?fragmento=1"), "lo lideras")

    def test_buscar_y_filtrar_conservan_el_orden(self):
        res = entrar_como(MATEO).get("/proyectos/?estado=activo")
        self.assertEqual(res.context["proyectos"][0].relacion, "lidera")
        self.assertTrue(all(p.estado == "activo" for p in res.context["proyectos"]))
