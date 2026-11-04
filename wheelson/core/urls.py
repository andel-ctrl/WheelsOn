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
]
