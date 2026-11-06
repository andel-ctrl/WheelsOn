"""
Reglas de permisos de WheelsOn. Es el único lugar donde se decide quién puede hacer qué.

Las vistas exigen estas reglas en el servidor; las plantillas solo las usan para no mostrar
botones que no funcionarían.

    Visitante        Solo puede iniciar sesión o registrarse.
    Usuario          Consulta la red. Gestiona su perfil, sus vínculos y lo que ha creado.
    Administrador    Rol de plataforma (rol="admin"): puede gestionar todo.

El dueño de cada dato sale del propio grafo:

    Empresa   (:Usuario)-[:ADMINISTRA]->(:Empresa)
    Proyecto  (:Usuario)-[:LIDERA]->(:Proyecto)
    Oferta    la administra quien administra la empresa que la publica
"""

from functools import cached_property

from django.core.exceptions import PermissionDenied

from core.models import Empresa, Habilidad, Oferta, Proyecto, Usuario
from core.services import consulta


class Permisos:
    def __init__(self, usuario):
        self.usuario = usuario

    @property
    def uid(self):
        return self.usuario.uid if self.usuario else None

    @property
    def es_admin(self):
        return bool(self.usuario) and self.usuario.rol == "admin"

    @cached_property
    def empresas_administradas(self):
        if not self.usuario:
            return set()
        filas = consulta("MATCH (:Usuario {uid: $uid})-[:ADMINISTRA]->(e:Empresa) RETURN e.eid", uid=self.uid)
        return {fila[0] for fila in filas}

    @cached_property
    def proyectos_liderados(self):
        if not self.usuario:
            return set()
        filas = consulta("MATCH (:Usuario {uid: $uid})-[:LIDERA]->(p:Proyecto) RETURN p.pid", uid=self.uid)
        return {fila[0] for fila in filas}

    @cached_property
    def ofertas_administradas(self):
        if not self.usuario:
            return set()
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[:ADMINISTRA]->(:Empresa)-[:PUBLICA]->(o:Oferta) RETURN o.oid",
            uid=self.uid,
        )
        return {fila[0] for fila in filas}

    # ------------------------------------------------------------------ recursos
    def editar_usuario(self, uid):
        return self.es_admin or (bool(self.usuario) and self.uid == uid)

    def crear_usuario(self):
        return self.es_admin

    def gestionar_empresa(self, eid):
        return self.es_admin or eid in self.empresas_administradas

    def gestionar_proyecto(self, pid):
        return self.es_admin or pid in self.proyectos_liderados

    def gestionar_oferta(self, oid):
        return self.es_admin or oid in self.ofertas_administradas

    def postularse(self, oid):
        # La plataforma no es la empresa: solo se bloquea a quien administra la oferta.
        return bool(self.usuario) and oid not in self.ofertas_administradas

    def gestionar_publicacion(self, autor):
        """`autor` es {'uid': ..., 'eid': ...}: una publicación es de una persona o de una empresa."""
        return self.gestionar_empresa(autor["eid"]) if autor["eid"] else self.editar_usuario(autor["uid"])

    def crear_habilidad(self):
        return self.es_admin

    def eliminar_habilidad(self):
        return self.es_admin

    def puede_editar(self, objeto):
        """Regla general para decidir si se muestran las acciones de editar y eliminar."""
        if isinstance(objeto, Usuario):
            return self.editar_usuario(objeto.uid)
        if isinstance(objeto, Empresa):
            return self.gestionar_empresa(objeto.eid)
        if isinstance(objeto, Proyecto):
            return self.gestionar_proyecto(objeto.pid)
        if isinstance(objeto, Oferta):
            return self.gestionar_oferta(objeto.oid)
        if isinstance(objeto, Habilidad):
            return self.eliminar_habilidad()
        return False

    # ------------------------------------------------------------------ vínculos
    def desconectar(self, uid_a, uid_b):
        return self.es_admin or self.uid in (uid_a, uid_b)

    def quitar_empleo(self, uid, eid):
        return self.editar_usuario(uid) or self.gestionar_empresa(eid)

    def quitar_colaborador(self, uid, pid):
        return self.editar_usuario(uid) or self.gestionar_proyecto(pid)

    def retirar_postulacion(self, uid):
        # La empresa no borra candidatos: responde cambiando el estado de la postulación.
        return self.editar_usuario(uid)

    def ver_postulacion(self, uid, oid):
        return self.editar_usuario(uid) or self.gestionar_oferta(oid)


def exigir(condicion, motivo="No tienes permiso para realizar esta acción."):
    """Detiene la petición con un error 403 si no se cumple la regla."""
    if not condicion:
        raise PermissionDenied(motivo)
