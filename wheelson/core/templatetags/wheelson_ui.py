"""Etiquetas de plantilla del sistema de diseño de WheelsOn."""

import hashlib
import random

from django import template
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icono(nombre, peso="duotone", tam=20, clase=""):
    """Dibuja un icono Phosphor del sprite local: {% icono "house" %}."""
    return format_html(
        '<svg class="ws-icon {}" width="{}" height="{}" aria-hidden="true" focusable="false">'
        '<use href="{}#{}-{}"></use></svg>',
        clase, tam, tam, static("icons/phosphor-sprite.svg"), nombre, peso,
    )


@register.simple_tag
def cifra_porcentaje(valor):
    """Porcentaje como cifra tipográfica: el entero grande; los decimales y el símbolo, pequeños."""
    entero, _, decimal = f"{float(valor):.1f}".partition(".")
    resto = f",{decimal} %" if decimal != "0" else " %"
    return format_html('<span class="ws-cifra"><b>{}</b><small>{}</small></span>', entero, resto)


@register.filter
def editable_por(objeto, permisos):
    """{% if oferta|editable_por:permisos %}: decide si se muestran las acciones de gestión."""
    return bool(permisos) and permisos.puede_editar(objeto)


TORRES_POR_TAMANO = {"pequena": 3, "mediana": 5, "grande": 7}


@register.simple_tag
def skyline(eid, tamano, personas):
    """
    Silueta de una empresa: su tamaño define cuántas torres tiene, y cada ventana encendida
    es una persona que trabaja ahí. La forma sale del identificador: cada empresa tiene la suya.
    """
    azar = random.Random(str(eid))
    torres = TORRES_POR_TAMANO.get(tamano, 5)
    ancho_torre = 360 / torres
    ventanas, cuerpos = [], []
    for indice in range(torres):
        alto = azar.randint(52, 118)
        x = 20 + indice * ancho_torre
        ancho = ancho_torre - azar.randint(4, 12)
        techo = 130 - alto
        cuerpos.append(f'<rect x="{x:.1f}" y="{techo}" width="{ancho:.1f}" height="{alto + 4}" rx="4"/>')
        columnas = max(2, int(ancho // 11))
        separacion = ancho / columnas
        for fila in range((alto - 10) // 12):
            for columna in range(columnas):
                ventanas.append((x + columna * separacion + separacion / 2 - 2.5, techo + 8 + fila * 12))
    azar.shuffle(ventanas)
    encendidas = max(int(personas or 0), 0)
    trazos = "".join(
        f'<rect class="{"ws-luz" if i < encendidas else "ws-apagada"}" x="{x:.1f}" y="{y}" width="5" height="6" rx="1"/>'
        for i, (x, y) in enumerate(ventanas)
    )
    return mark_safe(
        '<svg class="ws-skyline" viewBox="0 0 400 134" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">'
        f'<g class="ws-torres">{"".join(cuerpos)}</g><g>{trazos}</g></svg>'
    )


@register.filter
def variante(identificador, cantidad=3):
    """Número estable entre 0 y cantidad - 1 para el mismo identificador."""
    return hashlib.md5(str(identificador).encode("utf-8")).digest()[0] % int(cantidad)


ETIQUETAS = {
    "tecnica": "Técnica", "blanda": "Blanda", "idioma": "Idioma",
    "basico": "Básico", "intermedio": "Intermedio", "avanzado": "Avanzado", "experto": "Experto",
    "obligatoria": "Obligatoria", "deseable": "Deseable",
    "remoto": "Remoto", "presencial": "Presencial", "hibrido": "Híbrido",
    "pequena": "Pequeña", "mediana": "Mediana", "grande": "Grande",
}


@register.filter
def legible(valor):
    """El nombre de un valor guardado, como 'basico' o 'tecnica', tal como se lee en pantalla."""
    return ETIQUETAS.get(str(valor), valor)
