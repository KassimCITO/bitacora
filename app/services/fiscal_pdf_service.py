# -*- coding: utf-8 -*-
"""
Extraccion best-effort de datos fiscales desde Constancia de Situacion Fiscal.

La constancia del SAT puede exponer datos en texto del PDF o en metadatos.
Este modulo no falla el guardado si el PDF no es legible; solo retorna los
campos que pudo identificar con suficiente confianza.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


RFC_RE = re.compile(r'\b[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}\b', re.IGNORECASE)
DATE_RE = re.compile(r'\s+\d{2}/\d{2}/\d{4}.*$')
SAT_TEXT_RE = re.compile(
    r'Constancia|Situaci[oó]n Fiscal|Registro Federal|RFC|R[ée]gimen|Domicilio Fiscal|SAT',
    re.IGNORECASE,
)


def _normalize_text(value):
    if not value:
        return ''
    value = value.replace('\x00', ' ')
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'[\r\t]+', '\n', value)
    value = re.sub(r'[ \f\v]+', ' ', value)
    value = re.sub(r'\n\s+', '\n', value)
    return value.strip()


def _run_text_command(command, timeout=12):
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ''

    if result.returncode != 0:
        return ''
    return result.stdout or ''


def _extract_with_pypdf(path, diagnostics):
    chunks = []

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        diagnostics['pdf_pages'] = len(reader.pages)
        if reader.metadata:
            chunks.extend(str(v) for v in reader.metadata.values() if v)
        for page in reader.pages[:3]:
            chunks.append(page.extract_text() or '')
        diagnostics['pypdf_text_chars'] = len(''.join(chunks))
        diagnostics['methods'].append('pypdf')
    except Exception:
        diagnostics['pypdf_failed'] = True

    return '\n'.join(chunks)


def _extract_with_pdftotext(path, diagnostics):
    if not shutil.which('pdftotext'):
        diagnostics['pdftotext_available'] = False
        return ''

    diagnostics['pdftotext_available'] = True
    text = _run_text_command(['pdftotext', '-f', '1', '-l', '3', '-layout', path, '-'])
    if text:
        diagnostics['methods'].append('pdftotext')
        diagnostics['pdftotext_text_chars'] = len(text)
    return text


def _extract_with_raw_bytes(path, diagnostics):
    chunks = []

    try:
        with open(path, 'rb') as file:
            raw = file.read()
        diagnostics['file_size'] = len(raw)
        diagnostics['has_pdf_header'] = raw.startswith(b'%PDF-')
        diagnostics['image_markers'] = (
            raw.count(b'/Image') + raw.count(b'/XObject') + raw.count(b'/Subtype /Image')
        )
        for encoding in ('utf-8', 'latin-1'):
            decoded = raw.decode(encoding, errors='ignore')
            if SAT_TEXT_RE.search(decoded) or RFC_RE.search(decoded.upper()):
                chunks.append(decoded)
    except Exception:
        diagnostics['raw_read_failed'] = True

    if chunks:
        diagnostics['methods'].append('raw-bytes')
    return '\n'.join(chunks)


def _extract_with_ocr(path, diagnostics):
    if not shutil.which('pdftoppm') or not shutil.which('tesseract'):
        diagnostics['ocr_available'] = False
        return ''

    diagnostics['ocr_available'] = True
    chunks = []
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_prefix = str(Path(tmpdir) / 'csf-page')
            render = subprocess.run(
                ['pdftoppm', '-f', '1', '-l', '3', '-r', '220', '-png', path, image_prefix],
                check=False,
                capture_output=True,
                text=True,
                timeout=25,
            )
            if render.returncode != 0:
                diagnostics['ocr_render_failed'] = True
                return ''

            for image_path in sorted(Path(tmpdir).glob('csf-page-*.png')):
                text = _run_text_command(
                    ['tesseract', str(image_path), 'stdout', '-l', 'spa+eng', '--psm', '6'],
                    timeout=25,
                )
                if text:
                    chunks.append(text)
    except (OSError, subprocess.SubprocessError):
        diagnostics['ocr_failed'] = True
        return ''

    if chunks:
        diagnostics['methods'].append('ocr')
        diagnostics['ocr_text_chars'] = len('\n'.join(chunks))
    return '\n'.join(chunks)


def _read_pdf_text(path):
    diagnostics = {
        'methods': [],
        'pdf_pages': 0,
        'file_size': 0,
        'has_pdf_header': False,
        'image_markers': 0,
        'ocr_available': None,
        'pdftotext_available': None,
    }

    chunks = [
        _extract_with_pypdf(path, diagnostics),
        _extract_with_pdftotext(path, diagnostics),
        _extract_with_raw_bytes(path, diagnostics),
    ]

    text = _normalize_text('\n'.join(chunks))
    if not text or (len(text) < 60 and not RFC_RE.search(text.upper())):
        ocr_text = _normalize_text(_extract_with_ocr(path, diagnostics))
        if ocr_text:
            text = _normalize_text('\n'.join([text, ocr_text]))

    diagnostics['text_chars'] = len(text)
    return text, diagnostics


def _build_unreadable_error(diagnostics):
    if diagnostics.get('file_size') == 0:
        return (
            'PDF vacío: el archivo no contiene datos. Descarga nuevamente la CSF desde el SAT '
            'y vuelve a subir el PDF original.'
        )

    if diagnostics.get('has_pdf_header') is False and diagnostics.get('pypdf_failed'):
        return (
            'El archivo tiene extensión PDF, pero no parece ser un PDF válido. '
            'Sube la Constancia de Situación Fiscal original descargada del SAT.'
        )

    image_like = diagnostics.get('image_markers', 0) > 0 or (
        diagnostics.get('pdf_pages', 0) > 0 and diagnostics.get('pypdf_text_chars', 0) == 0
    )
    if image_like:
        if diagnostics.get('ocr_available') is False:
            return (
                'La CSF parece estar escaneada o guardada como imagen y este servidor no tiene OCR disponible. '
                'Sube el PDF original del SAT con texto seleccionable, o instala Poppler y Tesseract OCR para '
                'habilitar lectura de PDFs escaneados.'
            )
        return (
            'La CSF parece estar escaneada o guardada como imagen. Se intentó OCR, pero no se pudo reconocer '
            'texto fiscal suficiente. Vuelve a escanear con mayor resolución/contraste o sube el PDF original '
            'del SAT con texto seleccionable.'
        )

    return (
        'No se pudo leer texto fiscal dentro del PDF. Verifica que sea la Constancia de Situación Fiscal '
        'del SAT, que no esté protegido/corrupto y que el texto se pueda seleccionar.'
    )


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
    text, diagnostics = _read_pdf_text(path)
    if not text:
        return {
            '__error__': _build_unreadable_error(diagnostics),
            '__error_code__': 'unreadable_pdf',
            '__diagnostics__': diagnostics,
        }

    data = {'__diagnostics__': diagnostics}

    rfc_match = RFC_RE.search(text.upper())
    if rfc_match:
        data['rfc'] = rfc_match.group(0).upper()
    else:
        labeled_rfc = re.search(r'\bRFC\s*:?\s*([A-Z&Ñ]{3,12}\d{6}[A-Z0-9]{3})\b', text.upper())
        if labeled_rfc:
            data['rfc'] = labeled_rfc.group(1)[:20]

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
