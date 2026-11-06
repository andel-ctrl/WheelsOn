from django.urls import path
from core import views

app_name = "core"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Usuarios
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("usuarios/<str:uid>/", views.usuario_detalle, name="usuario_detalle"),
    path("usuarios/<str:uid>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<str:uid>/eliminar/", views.usuario_eliminar, name="usuario_eliminar"),

    # Empresas
    path("empresas/", views.empresas_lista, name="empresas_lista"),
    path("empresas/nueva/", views.empresa_crear, name="empresa_crear"),
    path("empresas/<str:eid>/", views.empresa_detalle, name="empresa_detalle"),
    path("empresas/<str:eid>/editar/", views.empresa_editar, name="empresa_editar"),
    path("empresas/<str:eid>/eliminar/", views.empresa_eliminar, name="empresa_eliminar"),

    # Habilidades
    path("habilidades/", views.habilidades_lista, name="habilidades_lista"),
    path("habilidades/nueva/", views.habilidad_crear, name="habilidad_crear"),
    path("habilidades/<str:hid>/eliminar/", views.habilidad_eliminar, name="habilidad_eliminar"),

    # Proyectos
    path("proyectos/", views.proyectos_lista, name="proyectos_lista"),
    path("proyectos/nuevo/", views.proyecto_crear, name="proyecto_crear"),
    path("proyectos/<str:pid>/", views.proyecto_detalle, name="proyecto_detalle"),
    path("proyectos/<str:pid>/editar/", views.proyecto_editar, name="proyecto_editar"),
    path("proyectos/<str:pid>/eliminar/", views.proyecto_eliminar, name="proyecto_eliminar"),

    # Ofertas
    path("ofertas/", views.ofertas_lista, name="ofertas_lista"),
    path("ofertas/nueva/", views.oferta_crear, name="oferta_crear"),
    path("ofertas/<str:oid>/", views.oferta_detalle, name="oferta_detalle"),
    path("ofertas/<str:oid>/editar/", views.oferta_editar, name="oferta_editar"),
    path("ofertas/<str:oid>/eliminar/", views.oferta_eliminar, name="oferta_eliminar"),

    # Relaciones - Conexiones (:CONECTA_CON)
    path("conexiones/", views.conexiones_red, name="conexiones_red"),
    path("conexiones/conectar/", views.conexion_conectar, name="conexion_conectar"),
    path("conexiones/desconectar/<str:uid_origen>/<str:uid_destino>/", views.conexion_desconectar, name="conexion_desconectar"),

    # Relaciones - Usuario <-> Habilidad (:TIENE_HABILIDAD)
    path("usuarios/<str:uid>/habilidades/agregar/", views.usuario_habilidad_agregar, name="usuario_habilidad_agregar"),
    path("usuarios/<str:uid>/habilidades/<str:hid>/eliminar/", views.usuario_habilidad_eliminar, name="usuario_habilidad_eliminar"),

    # Relaciones - Usuario <-> Empresa (:TRABAJA_EN)
    path("usuarios/<str:uid>/experiencia/agregar/", views.usuario_experiencia_agregar, name="usuario_experiencia_agregar"),
    path("usuarios/<str:uid>/experiencia/<str:eid>/eliminar/", views.usuario_experiencia_eliminar, name="usuario_experiencia_eliminar"),

    # Relaciones - Usuario <-> Proyecto (:PARTICIPA_EN)
    path("proyectos/<str:pid>/colaboradores/agregar/", views.proyecto_colaborador_agregar, name="proyecto_colaborador_agregar"),
    path("proyectos/<str:pid>/colaboradores/<str:uid>/eliminar/", views.proyecto_colaborador_eliminar, name="proyecto_colaborador_eliminar"),

    # Relaciones - Oferta <-> Empresa (:PUBLICA)
    path("ofertas/<str:oid>/empresa/asignar/", views.oferta_empresa_asignar, name="oferta_empresa_asignar"),

    # Relaciones - Oferta <-> Habilidad (:REQUIERE)
    path("ofertas/<str:oid>/requisitos/agregar/", views.oferta_requisito_agregar, name="oferta_requisito_agregar"),
    path("ofertas/<str:oid>/requisitos/<str:hid>/eliminar/", views.oferta_requisito_eliminar, name="oferta_requisito_eliminar"),

    # Relaciones - Usuario <-> Oferta (:POSTULA_A)
    path("ofertas/<str:oid>/postular/", views.oferta_postular, name="oferta_postular"),
    path("ofertas/<str:oid>/postulaciones/<str:uid>/eliminar/", views.oferta_postulacion_eliminar, name="oferta_postulacion_eliminar"),

    # Consultas Avanzadas de Grafo (Fase 6)
    path("consultas/", views.consultas_index, name="consultas_index"),

    # Motor de Recomendaciones (Fase 7)
    path("recomendaciones/", views.recomendaciones_index, name="recomendaciones_index"),

    # Panel de Analítica de Grafos (Fase 8)
    path("analitica/", views.analitica_dashboard, name="analitica_dashboard"),

    # Autenticación y Cuentas (Fase 8 Extension)
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),
]
