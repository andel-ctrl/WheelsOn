from neomodel import (
    StructuredNode,
    StructuredRel,
    StringProperty,
    IntegerProperty,
    FloatProperty,
    BooleanProperty,
    DateProperty,
    UniqueIdProperty,
    ArrayProperty,
    RelationshipTo,
    RelationshipFrom,
)


class ConectaConRel(StructuredRel):
    fecha = DateProperty(default_now=True)
    mensaje = StringProperty()
    estado = StringProperty(
        default="aceptada",
        choices={
            "pendiente": "Pendiente",
            "aceptada": "Aceptada",
            "rechazada": "Rechazada",
        },
    )


class TrabajaEnRel(StructuredRel):
    cargo = StringProperty(required=True)
    fecha_inicio = DateProperty()
    fecha_fin = DateProperty()
    actual = BooleanProperty(default=True)


class TieneHabilidadRel(StructuredRel):
    nivel = StringProperty(
        default="intermedio",
        choices={
            "basico": "Básico",
            "intermedio": "Intermedio",
            "avanzado": "Avanzado",
            "experto": "Experto",
        },
    )
    anios_experiencia = IntegerProperty(default=0)


class ParticipaEnRel(StructuredRel):
    rol = StringProperty(default="Colaborador")
    fecha_inicio = DateProperty()
    activo = BooleanProperty(default=True)


class PublicaRel(StructuredRel):
    fecha_publicacion = DateProperty(default_now=True)


class RequiereRel(StructuredRel):
    nivel_minimo = StringProperty(
        default="basico",
        choices={
            "basico": "Básico",
            "intermedio": "Intermedio",
            "avanzado": "Avanzado",
            "experto": "Experto",
        },
    )
    prioridad = StringProperty(
        default="obligatoria",
        choices={"obligatoria": "Obligatoria", "deseable": "Deseable"},
    )


ESTADOS_PROYECTO = {
    "activo": "Activo",
    "completado": "Completado",
    "pausado": "Pausado",
}

ESTADOS_POSTULACION = {
    "enviada": "Enviada",
    "revision": "En revisión",
    "entrevista": "Entrevista",
    "aceptada": "Aceptada",
    "rechazada": "Rechazada",
    "no_seleccionada": "No seleccionada",
}
# La empresa todavía no decide. Las demás son definitivas.
ESTADOS_EN_PROCESO = ("enviada", "revision", "entrevista")
ESTADOS_FINALES = ("aceptada", "rechazada", "no_seleccionada")


class PostulaARel(StructuredRel):
    fecha = DateProperty(default_now=True)
    fecha_estado = DateProperty()
    estado = StringProperty(default="enviada", choices=ESTADOS_POSTULACION)
    carta_presentacion = StringProperty()


class Usuario(StructuredNode):
    uid = UniqueIdProperty()
    nombre = StringProperty(required=True)
    apellido = StringProperty(required=True)
    email = StringProperty(unique_index=True, required=True)
    password_hash = StringProperty(required=True)
    titulo_profesional = StringProperty(default="Profesional")
    ubicacion = StringProperty(default="No especificada")
    biografia = StringProperty()
    foto_url = StringProperty(default="/static/img/default-avatar.svg")
    fecha_registro = DateProperty(default_now=True)
    rol = StringProperty(default="usuario", choices={"usuario": "Usuario", "admin": "Administrador"})

    conexiones = RelationshipTo("Usuario", "CONECTA_CON", model=ConectaConRel)
    empleos = RelationshipTo("Empresa", "TRABAJA_EN", model=TrabajaEnRel)
    habilidades = RelationshipTo("Habilidad", "TIENE_HABILIDAD", model=TieneHabilidadRel)
    proyectos = RelationshipTo("Proyecto", "PARTICIPA_EN", model=ParticipaEnRel)
    postulaciones = RelationshipTo("Oferta", "POSTULA_A", model=PostulaARel)
    empresas_administradas = RelationshipTo("Empresa", "ADMINISTRA")
    proyectos_liderados = RelationshipTo("Proyecto", "LIDERA")
    publicaciones = RelationshipTo("Publicacion", "AUTOR_DE")

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()

    def to_dict(self):
        return {
            "uid": self.uid,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "nombre_completo": self.nombre_completo,
            "email": self.email,
            "titulo_profesional": self.titulo_profesional,
            "ubicacion": self.ubicacion,
            "biografia": self.biografia,
            "foto_url": self.foto_url,
            "fecha_registro": str(self.fecha_registro) if self.fecha_registro else None,
        }


class Empresa(StructuredNode):
    eid = UniqueIdProperty()
    nombre = StringProperty(unique_index=True, required=True)
    industria = StringProperty(required=True)
    ubicacion = StringProperty(default="No especificada")
    descripcion = StringProperty()
    sitio_web = StringProperty()
    logo_url = StringProperty(default="/static/img/default-company.svg")
    tamano = StringProperty(
        default="mediana",
        choices={
            "pequena": "Pequeña (1-50)",
            "mediana": "Mediana (51-250)",
            "grande": "Grande (250+)",
        },
    )

    empleados = RelationshipFrom("Usuario", "TRABAJA_EN", model=TrabajaEnRel)
    administradores = RelationshipFrom("Usuario", "ADMINISTRA")
    ofertas = RelationshipTo("Oferta", "PUBLICA", model=PublicaRel)

    def to_dict(self):
        return {
            "eid": self.eid,
            "nombre": self.nombre,
            "industria": self.industria,
            "ubicacion": self.ubicacion,
            "descripcion": self.descripcion,
            "sitio_web": self.sitio_web,
            "logo_url": self.logo_url,
            "tamano": self.tamano,
        }


class Habilidad(StructuredNode):
    hid = UniqueIdProperty()
    nombre = StringProperty(unique_index=True, required=True)
    categoria = StringProperty(
        default="tecnica",
        choices={
            "tecnica": "Tecnica",
            "blanda": "Blanda",
            "idioma": "Idioma",
        },
    )
    descripcion = StringProperty()

    usuarios = RelationshipFrom("Usuario", "TIENE_HABILIDAD", model=TieneHabilidadRel)
    ofertas = RelationshipFrom("Oferta", "REQUIERE", model=RequiereRel)

    def to_dict(self):
        return {
            "hid": self.hid,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
        }


class Proyecto(StructuredNode):
    pid = UniqueIdProperty()
    nombre = StringProperty(required=True)
    descripcion = StringProperty()
    fecha_inicio = DateProperty()
    fecha_fin = DateProperty()
    estado = StringProperty(default="activo", choices=ESTADOS_PROYECTO)
    tecnologias = ArrayProperty(StringProperty(), default=list)

    miembros = RelationshipFrom("Usuario", "PARTICIPA_EN", model=ParticipaEnRel)
    lideres = RelationshipFrom("Usuario", "LIDERA")
    avances = RelationshipTo("Avance", "TIENE_AVANCE")

    def to_dict(self):
        return {
            "pid": self.pid,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "fecha_inicio": str(self.fecha_inicio) if self.fecha_inicio else None,
            "fecha_fin": str(self.fecha_fin) if self.fecha_fin else None,
            "estado": self.estado,
            "tecnologias": self.tecnologias or [],
        }


class Publicacion(StructuredNode):
    """Lo que una persona comparte en el feed. Las reacciones son relaciones PERCIBE."""

    pubid = UniqueIdProperty()
    texto = StringProperty(required=True)
    fecha = DateProperty(default_now=True)
    creada = FloatProperty(default=0.0)  # ordena las publicaciones de un mismo día

    autor = RelationshipFrom("Usuario", "AUTOR_DE")


class Avance(StructuredNode):
    """Una novedad del proyecto, con el estado en que quedó en ese momento."""

    aid = UniqueIdProperty()
    texto = StringProperty(required=True)
    estado = StringProperty(default="activo", choices=ESTADOS_PROYECTO)
    fecha = DateProperty(default_now=True)
    creada = FloatProperty(default=0.0)

    proyecto = RelationshipFrom("Proyecto", "TIENE_AVANCE")
    autor = RelationshipFrom("Usuario", "REGISTRA")


class Oferta(StructuredNode):
    oid = UniqueIdProperty()
    titulo = StringProperty(required=True)
    descripcion = StringProperty()
    salario_min = FloatProperty(default=0.0)
    salario_max = FloatProperty(default=0.0)
    modalidad = StringProperty(
        default="remoto",
        choices={
            "remoto": "Remoto",
            "presencial": "Presencial",
            "hibrido": "Híbrido",
        },
    )
    ubicacion = StringProperty(default="No especificada")
    fecha_publicacion = DateProperty(default_now=True)
    cupos = IntegerProperty(default=1)
    estado = StringProperty(
        default="abierta",
        choices={"abierta": "Abierta", "cerrada": "Cerrada"},
    )

    empresa = RelationshipFrom("Empresa", "PUBLICA", model=PublicaRel)
    habilidades = RelationshipTo("Habilidad", "REQUIERE", model=RequiereRel)
    candidatos = RelationshipFrom("Usuario", "POSTULA_A", model=PostulaARel)

    def to_dict(self):
        return {
            "oid": self.oid,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "salario_min": self.salario_min,
            "salario_max": self.salario_max,
            "modalidad": self.modalidad,
            "ubicacion": self.ubicacion,
            "fecha_publicacion": str(self.fecha_publicacion) if self.fecha_publicacion else None,
            "cupos": self.cupos,
            "estado": self.estado,
        }
