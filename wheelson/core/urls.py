from django.urls import path
from core import views

app_name = "core"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Publicaciones
    path("publicaciones/<str:pubid>/percibir/", views.publicacion_percibir, name="publicacion_percibir"),
    path("publicaciones/<str:pubid>/eliminar/", views.publicacion_eliminar, name="publicacion_eliminar"),

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

    # Dueños de los datos
    path("empresas/<str:eid>/transferir/", views.empresa_transferir, name="empresa_transferir"),
    path("empresas/<str:eid>/empleos/<str:uid>/responder/", views.empresa_empleo_responder, name="empresa_empleo_responder"),

    # Equipo de la empresa
    path("empresas/<str:eid>/equipo/trabajo-aqui/", views.empresa_trabajo_aqui, name="empresa_trabajo_aqui"),
    path("empresas/<str:eid>/equipo/invitar/", views.empresa_equipo_invitar, name="empresa_equipo_invitar"),
    path("empresas/<str:eid>/equipo/invitacion/responder/", views.empresa_equipo_invitacion_responder, name="empresa_equipo_invitacion_responder"),
    path("empresas/<str:eid>/equipo/invitacion/<str:uid>/cancelar/", views.empresa_equipo_invitacion_cancelar, name="empresa_equipo_invitacion_cancelar"),
    path("empresas/<str:eid>/equipo/<str:uid>/terminar/", views.empresa_equipo_terminar, name="empresa_equipo_terminar"),
    path("proyectos/<str:pid>/transferir/", views.proyecto_transferir, name="proyecto_transferir"),

    # Avances del proyecto
    path("proyectos/<str:pid>/avances/agregar/", views.proyecto_avance_agregar, name="proyecto_avance_agregar"),
    path("proyectos/<str:pid>/avances/<str:aid>/eliminar/", views.proyecto_avance_eliminar, name="proyecto_avance_eliminar"),

    # Pedir unirse a un proyecto
    path("proyectos/<str:pid>/unirse/", views.proyecto_unirse, name="proyecto_unirse"),
    path("proyectos/<str:pid>/unirse/cancelar/", views.proyecto_unirse_cancelar, name="proyecto_unirse_cancelar"),
    path("proyectos/<str:pid>/solicitudes/<str:uid>/responder/", views.proyecto_union_responder, name="proyecto_union_responder"),

    # Invitaciones a proyectos y empresas (se aceptan o se rechazan)
    path("proyectos/<str:pid>/invitacion/responder/", views.proyecto_invitacion_responder, name="proyecto_invitacion_responder"),
    path("proyectos/<str:pid>/invitaciones/<str:uid>/cancelar/", views.proyecto_invitacion_cancelar, name="proyecto_invitacion_cancelar"),
    path("empresas/<str:eid>/invitacion/responder/", views.empresa_invitacion_responder, name="empresa_invitacion_responder"),
    path("empresas/<str:eid>/invitacion/cancelar/", views.empresa_invitacion_cancelar, name="empresa_invitacion_cancelar"),

    # Relaciones - Conexiones (:CONECTA_CON)
    path("conexiones/", views.conexiones_red, name="conexiones_red"),
    path("conexiones/conectar/", views.conexion_conectar, name="conexion_conectar"),
    path("conexiones/desconectar/<str:uid_origen>/<str:uid_destino>/", views.conexion_desconectar, name="conexion_desconectar"),
    path("conexiones/solicitudes/<str:uid_origen>/responder/", views.conexion_solicitud_responder, name="conexion_solicitud_responder"),
    path("conexiones/solicitudes/<str:uid_destino>/cancelar/", views.conexion_solicitud_cancelar, name="conexion_solicitud_cancelar"),

    # Relaciones - Usuario <-> Habilidad (:TIENE_HABILIDAD)
    path("usuarios/<str:uid>/habilidades/agregar/", views.usuario_habilidad_agregar, name="usuario_habilidad_agregar"),
    path("usuarios/<str:uid>/habilidades/<str:hid>/eliminar/", views.usuario_habilidad_eliminar, name="usuario_habilidad_eliminar"),

    # Relaciones - Usuario <-> Empresa (:TRABAJA_EN)
    path("usuarios/<str:uid>/experiencia/agregar/", views.usuario_experiencia_agregar, name="usuario_experiencia_agregar"),
    path("usuarios/<str:uid>/experiencia/<str:eid>/eliminar/", views.usuario_experiencia_eliminar, name="usuario_experiencia_eliminar"),
    path("usuarios/<str:uid>/experiencia/<str:eid>/cancelar/", views.usuario_experiencia_cancelar, name="usuario_experiencia_cancelar"),

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
    path("ofertas/<str:oid>/postulaciones/<str:uid>/estado/", views.oferta_postulacion_estado, name="oferta_postulacion_estado"),

    # Consultas Avanzadas de Grafo (Fase 6)
    path("consultas/", views.consultas_index, name="consultas_index"),

    # Motor de Recomendaciones (Fase 7)
    path("recomendaciones/", views.recomendaciones_index, name="recomendaciones_index"),

    # Panel de Analítica de Grafos (Fase 8)
    path("analitica/", views.analitica_dashboard, name="analitica_dashboard"),

    # Visualización Interactiva de Grafos con Vis.js (Fase 9)
    path("grafo/", views.grafo_interactivo, name="grafo_interactivo"),
    path("grafo/api/data/", views.grafo_data_api, name="grafo_data_api"),

    # Autenticación y Cuentas (Fase 8 Extension)
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),
]
