# -*- coding: utf-8 -*-
"""
Sanitizador de HTML para contenido de texto enriquecido (Quill.js).
Utiliza Bleach para prevenir XSS y limitar las etiquetas permitidas.
"""
import bleach


# Tags permitidos del editor Quill
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ol', 'ul', 'li',
    'a', 'blockquote', 'pre', 'code',
    'span', 'sub', 'sup', 'img',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt', 'class', 'loading'],
    'span': ['class'],
    '*': ['class'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(html_content):
    """
    Sanitiza contenido HTML proveniente del editor Quill.js.
    Elimina tags y atributos peligrosos, permite solo los seguros.

    Args:
        html_content: String con HTML del editor.

    Returns:
        String con HTML sanitizado y seguro.
    """
    if not html_content:
        return ''

    cleaned = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    return cleaned.strip()


def strip_html(html_content):
    """
    Remueve todo el HTML y retorna solo texto plano.
    Útil para búsquedas y previews.
    """
    if not html_content:
        return ''
    return bleach.clean(html_content, tags=[], strip=True).strip()
