# -*- coding: utf-8 -*-
"""
Servicio de generación de reportes PDF con ReportLab.
Diseño profesional con logo, encabezado y pie de página.
"""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak
)
from reportlab.platypus.flowables import Flowable
from ..utils.sanitizer import strip_html


# Colores corporativos
PRIMARY_COLOR = colors.HexColor('#1a1a2e')
ACCENT_COLOR = colors.HexColor('#00d4aa')
HEADER_BG = colors.HexColor('#16213e')
ROW_ALT_BG = colors.HexColor('#f0f4f8')
BORDER_COLOR = colors.HexColor('#dee2e6')


def _pdf_text(value):
    return escape(strip_html(value or ''))


class HeaderFooter:
    """Dibuja encabezado y pie de página en cada página del PDF."""

    def __init__(self, logo_path, company_name):
        self.logo_path = logo_path
        self.company_name = company_name

    def __call__(self, canvas, doc):
        canvas.saveState()
        width, height = letter

        # --- Encabezado ---
        # Línea de acento
        canvas.setStrokeColor(ACCENT_COLOR)
        canvas.setLineWidth(3)
        canvas.line(30, height - 40, width - 30, height - 40)

        # Logo
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                canvas.drawImage(
                    self.logo_path, 35, height - 38, width=24, height=24,
                    preserveAspectRatio=True, mask='auto'
                )
            except Exception:
                pass

        # Nombre de empresa
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(PRIMARY_COLOR)
        canvas.drawString(65, height - 33, self.company_name)

        # Fecha de generación
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.gray)
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        canvas.drawRightString(width - 35, height - 33, f'Generado: {now}')

        # --- Pie de página ---
        canvas.setStrokeColor(BORDER_COLOR)
        canvas.setLineWidth(0.5)
        canvas.line(30, 35, width - 30, 35)

        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.gray)
        canvas.drawString(35, 22, f'© {datetime.now().year} {self.company_name} — Bitácora')
        canvas.drawRightString(width - 35, 22, f'Página {doc.page}')

        canvas.restoreState()


def _get_styles():
    """Retorna los estilos personalizados para el PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.gray,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=PRIMARY_COLOR,
        spaceBefore=16,
        spaceAfter=8,
        borderPadding=(0, 0, 4, 0),
    ))
    styles.add(ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
    ))
    styles.add(ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=PRIMARY_COLOR,
        spaceBefore=2,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        'LogComment',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#333333'),
        leftIndent=10,
    ))
    return styles


def _format_dt(dt):
    """Formatea datetime para el PDF."""
    if dt is None:
        return '—'
    return dt.strftime('%d/%m/%Y %H:%M')


def _estado_color(estado):
    """Color según el estado de la tarea."""
    mapping = {
        'pendiente': colors.HexColor('#ffc107'),
        'en_progreso': colors.HexColor('#0dcaf0'),
        'pausada': colors.HexColor('#6c757d'),
        'terminada': colors.HexColor('#198754'),
        'cancelada': colors.HexColor('#dc3545'),
    }
    return mapping.get(estado, colors.gray)


def generate_task_report(task, logo_path=None, company_name='Bitácora'):
    """
    Genera un reporte PDF completo para una tarea individual.
    Retorna el contenido del PDF como bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=55, bottomMargin=50,
        leftMargin=35, rightMargin=35,
    )
    styles = _get_styles()
    story = []

    # --- Título ---
    story.append(Paragraph(f'Reporte de Tarea #{task.id}', styles['ReportTitle']))
    story.append(Paragraph(task.nombre, styles['ReportSubtitle']))

    # --- Información general ---
    story.append(Paragraph('Información General', styles['SectionTitle']))
    story.append(HRFlowable(
        width='100%', thickness=1, color=ACCENT_COLOR,
        spaceAfter=10, spaceBefore=2
    ))

    info_data = [
        ['Campo', 'Valor'],
        ['Estado', task.estado_label],
        ['Prioridad', task.prioridad_label],
        ['Asignado a', task.usuario_asignado.nombre_completo],
        ['Creado por', task.creador.nombre_completo],
        ['Fecha inicio', _format_dt(task.fecha_hora_inicio)],
        ['Fin estimado', _format_dt(task.fecha_hora_fin_estimada)],
        ['Fin real', _format_dt(task.fecha_hora_fin_real)],
        ['Avance', f'{task.ultimo_avance}%'],
        ['Creación', _format_dt(task.fecha_creacion)],
        ['Última actualización', _format_dt(task.ultima_actualizacion)],
    ]

    info_table = Table(info_data, colWidths=[150, 350])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)

    # --- Descripción ---
    if task.descripcion:
        story.append(Spacer(1, 12))
        story.append(Paragraph('Descripción', styles['SectionTitle']))
        story.append(HRFlowable(
            width='100%', thickness=1, color=ACCENT_COLOR,
            spaceAfter=10, spaceBefore=2
        ))
        story.append(Paragraph(_pdf_text(task.descripcion), styles['Normal']))

    # --- Historial de avances ---
    from ..models.task_log import TaskLog
    logs = task.logs.order_by(None).order_by(
        TaskLog.fecha_hora.asc()
    ).all()

    if logs:
        story.append(Spacer(1, 12))
        story.append(Paragraph('Historial de Avances (Bitácora)', styles['SectionTitle']))
        story.append(HRFlowable(
            width='100%', thickness=1, color=ACCENT_COLOR,
            spaceAfter=10, spaceBefore=2
        ))

        log_data = [['#', 'Fecha', 'Usuario', 'Avance', 'Comentario']]
        for i, log in enumerate(logs, 1):
            log_data.append([
                str(i),
                _format_dt(log.fecha_hora),
                log.usuario.nombre_completo if log.usuario else '—',
                f'{log.porcentaje_avance}%',
                Paragraph(_pdf_text(log.comentario), styles['LogComment']),
            ])

        log_table = Table(log_data, colWidths=[30, 100, 100, 50, 240])
        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(log_table)

    # --- Archivos adjuntos ---
    attachments = task.attachments.all()
    if attachments:
        story.append(Spacer(1, 12))
        story.append(Paragraph('Archivos Adjuntos', styles['SectionTitle']))
        story.append(HRFlowable(
            width='100%', thickness=1, color=ACCENT_COLOR,
            spaceAfter=10, spaceBefore=2
        ))
        for att in attachments:
            story.append(Paragraph(
                f'📎 {att.nombre_archivo} — {_format_dt(att.fecha_subida)}',
                styles['Normal']
            ))

    # Construir PDF
    hf = HeaderFooter(logo_path, company_name)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buffer.seek(0)
    return buffer.getvalue()


# (helper removed — using SQLAlchemy model column ordering directly)


def generate_range_report(tasks, start_date, end_date, logo_path=None, company_name='Bitácora'):
    """
    Genera un reporte PDF para múltiples tareas en un rango de fechas.
    Retorna el contenido del PDF como bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=55, bottomMargin=50,
        leftMargin=35, rightMargin=35,
    )
    styles = _get_styles()
    story = []

    # --- Título ---
    story.append(Paragraph('Reporte por Rango de Fechas', styles['ReportTitle']))
    story.append(Paragraph(
        f'Período: {start_date.strftime("%d/%m/%Y")} — {end_date.strftime("%d/%m/%Y")}',
        styles['ReportSubtitle']
    ))

    # --- Resumen ---
    story.append(Paragraph('Resumen', styles['SectionTitle']))
    story.append(HRFlowable(
        width='100%', thickness=1, color=ACCENT_COLOR,
        spaceAfter=10, spaceBefore=2
    ))

    total = len(tasks)
    estados = {}
    for t in tasks:
        estados[t.estado_label] = estados.get(t.estado_label, 0) + 1

    summary_data = [['Indicador', 'Valor']]
    summary_data.append(['Total de tareas', str(total)])
    for estado, count in estados.items():
        summary_data.append([estado, str(count)])

    summary_table = Table(summary_data, colWidths=[250, 250])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)

    # --- Detalle de tareas ---
    story.append(Spacer(1, 16))
    story.append(Paragraph('Detalle de Tareas', styles['SectionTitle']))
    story.append(HRFlowable(
        width='100%', thickness=1, color=ACCENT_COLOR,
        spaceAfter=10, spaceBefore=2
    ))

    task_data = [['#', 'Tarea', 'Estado', 'Prioridad', 'Asignado', 'Avance']]
    for t in tasks:
        task_data.append([
            str(t.id),
            Paragraph(t.nombre, styles['LogComment']),
            t.estado_label,
            t.prioridad_label,
            t.usuario_asignado.nombre_completo if t.usuario_asignado else '—',
            f'{t.ultimo_avance}%',
        ])

    task_table = Table(task_data, colWidths=[30, 180, 70, 60, 100, 50])
    task_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(task_table)

    # Construir PDF
    hf = HeaderFooter(logo_path, company_name)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buffer.seek(0)
    return buffer.getvalue()
