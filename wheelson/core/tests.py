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


