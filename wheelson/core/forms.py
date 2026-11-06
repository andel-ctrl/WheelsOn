from django import forms


class BaseTailwindForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "checkbox checkbox-primary")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "select select-bordered w-full")
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "textarea textarea-bordered w-full h-24")
            else:
                field.widget.attrs.setdefault("class", "input input-bordered w-full")


class UsuarioForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=100, label="Nombre")
    apellido = forms.CharField(max_length=100, label="Apellido")
    email = forms.EmailField(label="Correo Electronico")
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        label="Contrasena",
    )
    titulo_profesional = forms.CharField(
        max_length=150,
        required=False,
        label="Titulo Profesional",
    )
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicacion",
    )
    biografia = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Biografia",
    )


class EmpresaForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=150, label="Nombre de la Empresa")
    industria = forms.CharField(max_length=100, label="Industria / Sector")
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicacion",
        initial="No especificada",
    )
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripcion",
    )
    sitio_web = forms.URLField(
        required=False,
        label="Sitio Web",
    )
    tamano = forms.ChoiceField(
        choices=[
            ("pequena", "Pequena (1-50)"),
            ("mediana", "Mediana (51-250)"),
            ("grande", "Grande (250+)"),
        ],
        label="Tamano de Empresa",
        initial="mediana",
    )


class HabilidadForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=100, label="Nombre de la Habilidad")
    categoria = forms.ChoiceField(
        choices=[
            ("tecnica", "Tecnica"),
            ("blanda", "Blanda"),
            ("idioma", "Idioma"),
        ],
        label="Categoria",
        initial="tecnica",
    )
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripcion",
    )


class ProyectoForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=150, label="Nombre del Proyecto")
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripcion",
    )
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Fecha de Inicio",
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Fecha de Fin",
    )
    estado = forms.ChoiceField(
        choices=[
            ("activo", "Activo"),
            ("completado", "Completado"),
            ("pausado", "Pausado"),
        ],
        label="Estado",
        initial="activo",
    )
    tecnologias = forms.CharField(
        required=False,
        label="Tecnologias (separadas por coma)",
        help_text="Ejemplo: Python, Django, Neo4j",
    )


class OfertaForm(BaseTailwindForm):
    titulo = forms.CharField(max_length=150, label="Titulo de la Vacante")
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripcion de la Vacante",
    )
    salario_min = forms.FloatField(
        required=False,
        min_value=0,
        label="Salario Minimo",
        initial=0.0,
    )
    salario_max = forms.FloatField(
        required=False,
        min_value=0,
        label="Salario Maximo",
        initial=0.0,
    )
    modalidad = forms.ChoiceField(
        choices=[
            ("remoto", "Remoto"),
            ("presencial", "Presencial"),
            ("hibrido", "Hibrido"),
        ],
        label="Modalidad",
        initial="remoto",
    )
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicacion",
        initial="No especificada",
    )
    estado = forms.ChoiceField(
        choices=[
            ("abierta", "Abierta"),
            ("cerrada", "Cerrada"),
        ],
        label="Estado",
        initial="abierta",
    )


# ==============================================================================
# FORMULARIOS DE GESTION DE RELACIONES (FASE 5)
# ==============================================================================

class ConectarUsuarioForm(BaseTailwindForm):
    usuario_destino = forms.CharField(max_length=64, label="Usuario a Conectar")
    mensaje = forms.CharField(
        max_length=250,
        required=False,
        label="Mensaje de Invitacion",
        widget=forms.TextInput(attrs={"placeholder": "Hola, me gustaria conectar contigo en WheelsOn..."}),
    )


class VincularHabilidadUsuarioForm(BaseTailwindForm):
    hid = forms.CharField(max_length=64, label="Habilidad")
    nivel = forms.ChoiceField(
        choices=[
            ("basico", "Basico"),
            ("intermedio", "Intermedio"),
            ("avanzado", "Avanzado"),
            ("experto", "Experto"),
        ],
        initial="intermedio",
        label="Nivel de Dominio",
    )
    anios_experiencia = forms.IntegerField(
        min_value=0,
        initial=1,
        label="Anos de Experiencia",
    )


class ExperienciaLaboralForm(BaseTailwindForm):
    eid = forms.CharField(max_length=64, label="Empresa")
    cargo = forms.CharField(max_length=150, label="Cargo / Posicion")
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Fecha de Inicio",
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Fecha de Finalizacion",
    )
    actual = forms.BooleanField(
        required=False,
        initial=True,
        label="Es mi empleo actual",
    )


class ParticipacionProyectoForm(BaseTailwindForm):
    uid = forms.CharField(max_length=64, required=False, label="Colaborador")
    pid = forms.CharField(max_length=64, required=False, label="Proyecto")
    rol = forms.CharField(
        max_length=100,
        initial="Colaborador",
        label="Rol / Responsabilidad",
    )
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        label="Fecha de Ingreso",
    )


class PublicarOfertaEmpresaForm(BaseTailwindForm):
    eid = forms.CharField(max_length=64, label="Empresa Emisora")


class RequisitoOfertaForm(BaseTailwindForm):
    hid = forms.CharField(max_length=64, label="Habilidad Requerida")
    nivel_minimo = forms.ChoiceField(
        choices=[
            ("basico", "Basico"),
            ("intermedio", "Intermedio"),
            ("avanzado", "Avanzado"),
            ("experto", "Experto"),
        ],
        initial="basico",
        label="Nivel Minimo Exigido",
    )
    prioridad = forms.ChoiceField(
        choices=[
            ("obligatoria", "Obligatoria"),
            ("deseable", "Deseable"),
        ],
        initial="obligatoria",
        label="Prioridad del Requisito",
    )


class PostulacionForm(BaseTailwindForm):
    uid = forms.CharField(max_length=64, required=False, label="Usuario Candidato")
    carta_presentacion = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": "Describe tu interes en el rol y aportes clave..."}),
        required=False,
        label="Carta de Presentacion",
    )


# ==============================================================================
# FORMULARIOS DE CONSULTAS AVANZADAS DE GRAFOS (FASE 6)
# ==============================================================================

class CaminoCortoForm(BaseTailwindForm):
    uid1 = forms.CharField(max_length=64, label="Usuario Origen")
    uid2 = forms.CharField(max_length=64, label="Usuario Destino")


class ContactosComunForm(BaseTailwindForm):
    uid1 = forms.CharField(max_length=64, label="Primer Usuario")
    uid2 = forms.CharField(max_length=64, label="Segundo Usuario")


class HabilidadesSimilaresForm(BaseTailwindForm):
    uid = forms.CharField(max_length=64, label="Usuario de Referencia")


class RutaEmpresaForm(BaseTailwindForm):
    uid = forms.CharField(max_length=64, label="Usuario Origen")
    eid = forms.CharField(max_length=64, label="Empresa Objetivo")


class CandidatosOfertaForm(BaseTailwindForm):
    oid = forms.CharField(max_length=64, label="Oferta Laboral")


# ==============================================================================
# FORMULARIOS DE AUTENTICACION & REGISTRO
# ==============================================================================

class LoginForm(BaseTailwindForm):
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        label="Contraseña"
    )


class RegistroForm(BaseTailwindForm):
    nombre = forms.CharField(
        max_length=100,
        label="Nombre",
        widget=forms.TextInput()
    )
    apellido = forms.CharField(
        max_length=100,
        label="Apellido",
        widget=forms.TextInput()
    )
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput()
    )
    titulo_profesional = forms.CharField(
        max_length=150,
        required=False,
        label="Título Profesional",
        widget=forms.TextInput()
    )
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicación",
        widget=forms.TextInput()
    )
    biografia = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Biografía Corta"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label="Contraseña"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(),
        label="Confirmar Contraseña"
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")
        return cleaned_data


