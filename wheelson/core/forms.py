from django.core.validators import MaxLengthValidator
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django import forms

from core.models import ESTADOS_PROYECTO


TOPE_TEXTO_LARGO = 3000


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
                # Ningún texto largo es ilimitado: un texto gigante no debe guardarse ni romper la página
                if isinstance(field, forms.CharField) and field.max_length is None:
                    field.max_length = TOPE_TEXTO_LARGO
                    field.validators.append(MaxLengthValidator(TOPE_TEXTO_LARGO))
                    field.widget.attrs.setdefault("maxlength", str(TOPE_TEXTO_LARGO))
            else:
                field.widget.attrs.setdefault("class", "input input-bordered w-full")


def _validar_rango(formulario, datos, inicio, fin, campo_error, mensaje):
    """Marca un error si `fin` es anterior a `inicio`. Un valor vacío no se compara."""
    if datos.get(inicio) and datos.get(fin) and datos[fin] < datos[inicio]:
        formulario.add_error(campo_error, mensaje)


class UsuarioForm(BaseTailwindForm):
    def __init__(self, *args, verificar_clave_de=None, **kwargs):
        """Con `verificar_clave_de`, cambiar la contraseña exige escribir la actual de esa cuenta."""
        super().__init__(*args, **kwargs)
        self.verificar_clave_de = verificar_clave_de
        if verificar_clave_de is not None:
            self.fields["password_actual"] = forms.CharField(
                widget=forms.PasswordInput(attrs={"class": "input input-bordered w-full", "autocomplete": "current-password"}),
                required=False,
                label="Contraseña actual",
            )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_password(self):
        clave = self.cleaned_data.get("password")
        if clave:
            validate_password(clave)
        return clave

    def clean(self):
        datos = super().clean()
        if self.verificar_clave_de is not None:
            actual = datos.pop("password_actual", "")
            if datos.get("password") and not check_password(actual, self.verificar_clave_de.password_hash or ""):
                self.add_error("password_actual", "Escribe tu contraseña actual para poder cambiarla.")
        return datos

    nombre = forms.CharField(max_length=100, label="Nombre")
    apellido = forms.CharField(max_length=100, label="Apellido")
    email = forms.EmailField(label="Correo Electrónico")
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        label="Contraseña",
    )
    titulo_profesional = forms.CharField(
        max_length=150,
        required=False,
        label="Título profesional",
    )
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicación",
    )
    biografia = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Biografía",
    )


class EmpresaForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=150, label="Nombre de la Empresa")
    industria = forms.CharField(max_length=100, label="Industria / Sector")
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicación",
        initial="No especificada",
    )
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripción",
    )
    sitio_web = forms.URLField(
        required=False,
        label="Sitio Web",
    )
    tamano = forms.ChoiceField(
        choices=[
            ("pequena", "Pequeña (1-50)"),
            ("mediana", "Mediana (51-250)"),
            ("grande", "Grande (250+)"),
        ],
        label="Tamano de Empresa",
        initial="mediana",
    )


class PublicacionForm(BaseTailwindForm):
    texto = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(),
        label="Publicación",
        error_messages={
            "required": "Escribe algo para publicar.",
            "max_length": "La publicación no puede pasar de 2000 caracteres.",
        },
    )


class AvanceForm(BaseTailwindForm):
    texto = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(),
        label="¿Qué hay de nuevo?",
        error_messages={
            "required": "Cuenta qué hay de nuevo en el proyecto.",
            "max_length": "El avance no puede pasar de 1000 caracteres.",
        },
    )
    estado = forms.ChoiceField(choices=list(ESTADOS_PROYECTO.items()), label="Estado del proyecto")


class HabilidadForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=100, label="Nombre de la Habilidad")
    categoria = forms.ChoiceField(
        choices=[
            ("tecnica", "Tecnica"),
            ("blanda", "Blanda"),
            ("idioma", "Idioma"),
        ],
        label="Categoría",
        initial="tecnica",
    )
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripción",
    )


class ProyectoForm(BaseTailwindForm):
    nombre = forms.CharField(max_length=150, label="Nombre del Proyecto")
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripción",
    )
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        required=False,
        label="Fecha de Inicio",
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
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
        label="Tecnologías (separadas por coma)",
        help_text="Ejemplo: Python, Django, Neo4j",
    )

    def clean(self):
        datos = super().clean()
        _validar_rango(self, datos, "fecha_inicio", "fecha_fin", "fecha_fin", "La fecha de fin no puede ser anterior a la de inicio.")
        return datos


class OfertaForm(BaseTailwindForm):
    def clean_cupos(self):
        return self.cleaned_data.get("cupos") or 1

    def __init__(self, *args, empresas=None, **kwargs):
        """Al crear, `empresas` son las que puede usar esta persona para publicar la oferta."""
        super().__init__(*args, **kwargs)
        if empresas is not None:
            self.fields["eid"] = forms.ChoiceField(
                label="Empresa que publica",
                choices=[(empresa.eid, empresa.nombre) for empresa in empresas],
                widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
            )

    titulo = forms.CharField(max_length=150, label="Título del empleo")
    descripcion = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="Descripción",
    )
    salario_min = forms.FloatField(
        required=False,
        min_value=0,
        max_value=1_000_000_000_000,
        label="Salario mínimo",
        initial=0.0,
    )
    salario_max = forms.FloatField(
        required=False,
        min_value=0,
        max_value=1_000_000_000_000,
        label="Salario máximo",
        initial=0.0,
    )
    modalidad = forms.ChoiceField(
        choices=[
            ("remoto", "Remoto"),
            ("presencial", "Presencial"),
            ("hibrido", "Híbrido"),
        ],
        label="Modalidad",
        initial="remoto",
    )
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicación",
        initial="No especificada",
    )
    cupos = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        required=False,
        label="Cupos",
        help_text="Cuántas personas vas a contratar. Al llenarse, el empleo se cierra.",
    )
    estado = forms.ChoiceField(
        choices=[
            ("abierta", "Abierta"),
            ("cerrada", "Cerrada"),
        ],
        label="Estado",
        initial="abierta",
    )

    def clean(self):
        datos = super().clean()
        _validar_rango(self, datos, "salario_min", "salario_max", "salario_max", "El salario máximo no puede ser menor que el mínimo.")
        return datos


# ==============================================================================
# FORMULARIOS DE GESTION DE RELACIONES (FASE 5)
# ==============================================================================

class ConectarUsuarioForm(BaseTailwindForm):
    usuario_destino = forms.CharField(max_length=64, label="Usuario a Conectar")
    mensaje = forms.CharField(
        max_length=250,
        required=False,
        label="Mensaje de Invitación",
        widget=forms.TextInput(attrs={"placeholder": "Hola, me gustaria conectar contigo en WheelsOn..."}),
    )


class VincularHabilidadUsuarioForm(BaseTailwindForm):
    hid = forms.CharField(max_length=64, label="Habilidad")
    nivel = forms.ChoiceField(
        choices=[
            ("basico", "Básico"),
            ("intermedio", "Intermedio"),
            ("avanzado", "Avanzado"),
            ("experto", "Experto"),
        ],
        initial="intermedio",
        label="Nivel de Dominio",
    )
    anios_experiencia = forms.IntegerField(
        min_value=0,
        max_value=70,
        initial=1,
        label="Años de experiencia",
    )


class ExperienciaLaboralForm(BaseTailwindForm):
    ERROR_FECHA = {"invalid": "La fecha no es valida. Usa el formato AAAA-MM-DD."}

    eid = forms.CharField(max_length=64, label="Empresa")
    cargo = forms.CharField(max_length=150, label="Cargo / Posicion")
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        required=False,
        label="Fecha de Inicio",
        error_messages=ERROR_FECHA,
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        required=False,
        label="Fecha de Finalizacion",
        error_messages=ERROR_FECHA,
    )

    def clean(self):
        datos = super().clean()
        _validar_rango(self, datos, "fecha_inicio", "fecha_fin", "fecha_fin", "La fecha de fin no puede ser anterior a la de inicio.")
        return datos

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
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        required=False,
        label="Fecha de Ingreso",
    )


class PublicarOfertaEmpresaForm(BaseTailwindForm):
    eid = forms.CharField(max_length=64, label="Empresa Emisora")


class RequisitoOfertaForm(BaseTailwindForm):
    hid = forms.CharField(max_length=64, label="Habilidad Requerida")
    nivel_minimo = forms.ChoiceField(
        choices=[
            ("basico", "Básico"),
            ("intermedio", "Intermedio"),
            ("avanzado", "Avanzado"),
            ("experto", "Experto"),
        ],
        initial="basico",
        label="Nivel mínimo exigido",
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
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "tu@correo.com", "autofocus": True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Tu contraseña"}),
        label="Contraseña"
    )


class RegistroForm(BaseTailwindForm):
    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

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
        if p1:
            try:
                validate_password(p1)
            except ValidationError as error:
                self.add_error("password", error)
        return cleaned_data


