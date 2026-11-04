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
        initial="Profesional",
    )
    ubicacion = forms.CharField(
        max_length=150,
        required=False,
        label="Ubicacion",
        initial="No especificada",
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
