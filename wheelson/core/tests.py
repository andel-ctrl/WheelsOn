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
)
from core.forms import (
    UsuarioForm,
    EmpresaForm,
    HabilidadForm,
    ProyectoForm,
    OfertaForm,
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

