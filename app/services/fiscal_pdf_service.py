# -*- coding: utf-8 -*-
"""
Extraccion best-effort de datos fiscales desde Constancia de Situacion Fiscal.

La constancia del SAT puede exponer datos en texto del PDF o en metadatos.
Este modulo no falla el guardado si el PDF no es legible; solo retorna los
campos que pudo identificar con suficiente confianza.
"""
import re


RFC_RE = re.compile(r'\b[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}\b', re.IGNORECASE)
DATE_RE = re.compile(r'\s+\d{2}/\d{2}/\d{4}.*$')


def _normalize_text(value):
    if not value:
        return ''
    value = value.replace('\x00', ' ')
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'[\r\t]+', '\n', value)
    value = re.sub(r'[ \f\v]+', ' ', value)
    value = re.sub(r'\n\s+', '\n', value)
    return value.strip()


def _read_pdf_text(path):
    chunks = []

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        if reader.metadata:
            chunks.extend(str(v) for v in reader.metadata.values() if v)
        for page in reader.pages[:3]:
            chunks.append(page.extract_text() or '')
    except Exception:
        pass

    try:
        with open(path, 'rb') as file:
            raw = file.read()
        for encoding in ('utf-8', 'latin-1'):
            chunks.append(raw.decode(encoding, errors='ignore'))
    except Exception:
        pass

    return _normalize_text('\n'.join(chunks))


def _find_labeled_value(text, labels, stop_labels=None, max_len=180):
    stop_labels = stop_labels or []
    stop_pattern = '|'.join(re.escape(label) for label in stop_labels)

    for line in text.splitlines():
        clean_line = _normalize_text(line)
        for label in labels:
            if stop_pattern:
                pattern = rf'(?:^|\s){re.escape(label)}\s*:?\s*(.*?)(?=\s+(?:{stop_pattern})\s*:|$)'
            else:
                pattern = rf'(?:^|\s){re.escape(label)}\s*:?\s*(.+)$'
            match = re.search(pattern, clean_line, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip(' :-')
                if value:
                    return value[:max_len].strip()

    label_pattern = '|'.join(re.escape(label) for label in labels)

    if stop_pattern:
        pattern = rf'(?:{label_pattern})\s*:?\s*(.+?)(?=\n\s*(?:{stop_pattern})\s*:|\n{{2,}}|$)'
    else:
        pattern = rf'(?:{label_pattern})\s*:?\s*(.+?)(?=\n{{2,}}|$)'

    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ''

    value = _normalize_text(match.group(1))
    value = re.sub(r'\s{2,}', ' ', value).strip(' :-')
    return value[:max_len].strip()


def _person_name(text):
    names = _find_labeled_value(
        text,
        ['Nombre (s)', 'Nombre(s)', 'Nombres'],
        ['Primer Apellido', 'Segundo Apellido', 'Fecha inicio'],
        max_len=120,
    )
    first_last = _find_labeled_value(
        text,
        ['Primer Apellido'],
        ['Segundo Apellido', 'Fecha inicio', 'Estatus'],
        max_len=80,
    )
    second_last = _find_labeled_value(
        text,
        ['Segundo Apellido'],
        ['Fecha inicio', 'Estatus', 'Nombre Comercial'],
        max_len=80,
    )
    full_name = ' '.join(part for part in [names, first_last, second_last] if part)
    return re.sub(r'\s+', ' ', full_name).strip()


def _regimen_from_table(text):
    match = re.search(
        r'Reg[íi]menes?\s*:?\s*.*?R[ée]gimen\s+Fecha Inicio\s+Fecha Fin\s*(.+?)(?=\n\s*Obligaciones\s*:|\n\s*Sus datos personales|\Z)',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ''

    for line in match.group(1).splitlines():
        value = _normalize_text(line)
        if not value:
            continue
        value = DATE_RE.sub('', value).strip()
        if value:
            return value[:220]
    return ''


def _compose_address(text):
    parts = []
    fields = [
        ['Codigo Postal', 'Código Postal', 'C.P.'],
        ['Tipo de Vialidad'],
        ['Nombre de Vialidad'],
        ['Numero Exterior', 'Número Exterior', 'No. Exterior'],
        ['Numero Interior', 'Número Interior', 'No. Interior'],
        ['Nombre de la Colonia', 'Colonia'],
        ['Nombre de la Localidad', 'Localidad'],
        ['Nombre del Municipio o Demarcacion Territorial', 'Nombre del Municipio o Demarcación Territorial', 'Municipio o Demarcacion Territorial', 'Municipio o Demarcación Territorial', 'Municipio'],
        ['Nombre de la Entidad Federativa', 'Entidad Federativa'],
        ['Entre Calle'],
        ['Y Calle'],
    ]

    stops = [
        'Código Postal', 'Codigo Postal', 'C.P.', 'Tipo de Vialidad',
        'Nombre de Vialidad', 'Numero Exterior', 'Número Exterior', 'No. Exterior',
        'Numero Interior', 'Número Interior', 'No. Interior', 'Nombre de la Colonia',
        'Colonia', 'Nombre de la Localidad', 'Localidad',
        'Nombre del Municipio o Demarcacion Territorial',
        'Nombre del Municipio o Demarcación Territorial',
        'Municipio o Demarcacion Territorial', 'Municipio o Demarcación Territorial',
        'Municipio', 'Nombre de la Entidad Federativa', 'Entidad Federativa',
        'Entre Calle', 'Y Calle', 'Actividad Economica', 'Actividad Económica',
        'Regimen', 'Régimen', 'Regímenes', 'Obligaciones',
    ]

    for labels in fields:
        value = _find_labeled_value(text, labels, stops, max_len=90)
        if value and value.lower() not in {'nombre de la', 'nombre del'} and value not in parts:
            parts.append(value)

    if parts:
        return ', '.join(parts)

    return _find_labeled_value(
        text,
        ['Domicilio Fiscal', 'Direccion Fiscal', 'Dirección Fiscal'],
        [
            'Actividad Economica', 'Actividad Económica', 'Regimen', 'Régimen',
            'Obligaciones', 'Datos de Identificacion', 'Datos de Identificación',
        ],
        max_len=500,
    )


def extract_constancia_fiscal_data(path):
    """
    Retorna datos detectados en la constancia:
    rfc, razon_social, direccion, regimen_fiscal.
    """
    text = _read_pdf_text(path)
    if not text:
        return {
            '__error__': 'No se pudo leer el contenido del PDF. Verifica que sea un PDF válido y no esté escaneado como imagen.'
        }

    data = {}

    rfc_match = RFC_RE.search(text.upper())
    if rfc_match:
        data['rfc'] = rfc_match.group(0).upper()

    razon_social = _find_labeled_value(
        text,
        [
            'Denominación/Razón Social',
            'Denominacion/Razon Social',
            'Razón Social',
            'Razon Social',
            'Nombre, denominación o razón social',
            'Nombre denominación o razón social',
        ],
        [
            'RFC', 'CURP', 'Estatus', 'Nombre Comercial', 'Fecha inicio',
            'Código Postal', 'Codigo Postal', 'Domicilio', 'Actividad Economica',
            'Actividad Económica',
        ],
        max_len=220,
    )
    if not razon_social or 'denominación' in razon_social.lower() or 'razón' in razon_social.lower():
        razon_social = _person_name(text)
    if razon_social:
        data['razon_social'] = razon_social

    direccion = _compose_address(text)
    if direccion:
        data['direccion'] = direccion

    regimen = _regimen_from_table(text) or _find_labeled_value(
        text,
        ['Régimen Fiscal', 'Regimen Fiscal', 'Regímenes', 'Regimenes', 'Régimen', 'Regimen'],
        ['Obligaciones', 'Fecha de alta', 'Actividad Economica', 'Actividad Económica'],
        max_len=220,
    )
    if regimen:
        data['regimen_fiscal'] = regimen

    return data
