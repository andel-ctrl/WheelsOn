from django.test import TestCase, Client
from django.urls import reverse
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
        self.assertContains(response, "Red Profesional Orientada a Grafos")


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






