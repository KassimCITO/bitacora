# -*- coding: utf-8 -*-
"""
Servicio de exportación de datos a CSV.
"""
import csv
import io
from ..utils.helpers import format_datetime


def export_tasks_csv(tasks):
    """
    Exporta una lista de tareas a formato CSV.
    Retorna el contenido como string.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Encabezados
    writer.writerow([
        'ID', 'Nombre', 'Estado', 'Prioridad',
        'Asignado a', 'Creado por',
        'Fecha Inicio', 'Fin Estimado', 'Fin Real',
        'Avance (%)', 'Fecha Creación', 'Última Actualización',
    ])

    # Datos
    for task in tasks:
        writer.writerow([
            task.id,
            task.nombre,
            task.estado_label,
            task.prioridad_label,
            task.usuario_asignado.nombre_completo if task.usuario_asignado else '',
            task.creador.nombre_completo if task.creador else '',
            format_datetime(task.fecha_hora_inicio),
            format_datetime(task.fecha_hora_fin_estimada),
            format_datetime(task.fecha_hora_fin_real),
            task.ultimo_avance,
            format_datetime(task.fecha_creacion),
            format_datetime(task.ultima_actualizacion),
        ])

    return output.getvalue()
