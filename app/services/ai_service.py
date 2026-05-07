# -*- coding: utf-8 -*-
"""
Servicio de IA para análisis de avances.
Soporta múltiples proveedores: OpenAI, Google Gemini, Anthropic Claude.
"""
import json
from flask import current_app
from ..extensions import db
from ..models.task import Task
from ..models.user import User
from ..models.group import Group
from ..models.company import Company
from sqlalchemy import func


def _get_stats(tasks):
    """Calcula estadísticas básicas de una lista de tareas."""
    total = len(tasks)
    if total == 0:
        return {'total': 0, 'estados': {}, 'prioridades': {}, 'avance_promedio': 0}

    estados = {}
    prioridades = {}
    avances = []

    for t in tasks:
        e_label = t.estado_label
        p_label = t.prioridad_label
        estados[e_label] = estados.get(e_label, 0) + 1
        prioridades[p_label] = prioridades.get(p_label, 0) + 1
        avances.append(t.ultimo_avance)

    return {
        'total': total,
        'estados': estados,
        'prioridades': prioridades,
        'avance_promedio': round(sum(avances) / len(avances), 1) if avances else 0,
    }


def get_company_stats(empresa_id):
    """Estadísticas globales de la empresa."""
    tasks = Task.query.filter_by(empresa_id=empresa_id).all()
    stats = _get_stats(tasks)

    # Usuarios activos
    user_count = User.query.filter_by(empresa_id=empresa_id, activo=True).count()
    group_count = Group.query.filter_by(empresa_id=empresa_id, activo=True).count()

    stats['usuarios_activos'] = user_count
    stats['grupos_activos'] = group_count
    return stats


def get_group_stats(grupo_id):
    """Estadísticas de un grupo específico."""
    tasks = Task.query.filter_by(grupo_id=grupo_id).all()
    group = db.session.get(Group, grupo_id)
    stats = _get_stats(tasks)
    stats['nombre_grupo'] = group.nombre if group else '—'
    stats['miembros'] = group.member_count if group else 0

    # Avance por miembro
    if group:
        member_stats = []
        for member in group.members.filter_by(activo=True).all():
            member_tasks = [t for t in tasks if t.usuario_asignado_id == member.id]
            m_stats = _get_stats(member_tasks)
            member_stats.append({
                'nombre': member.nombre_completo,
                'id': member.id,
                'total_tareas': m_stats['total'],
                'avance_promedio': m_stats['avance_promedio'],
                'estados': m_stats['estados'],
            })
        stats['miembros_detalle'] = member_stats

    return stats


def get_user_stats(usuario_id, empresa_id):
    """Estadísticas de un usuario específico."""
    tasks = Task.query.filter_by(
        usuario_asignado_id=usuario_id,
        empresa_id=empresa_id,
    ).all()
    user = db.session.get(User, usuario_id)
    stats = _get_stats(tasks)
    stats['nombre_usuario'] = user.nombre_completo if user else '—'
    return stats


def _build_prompt(stats, context_type, context_name):
    """Construye el prompt para el análisis de IA."""
    prompt = f"""Eres un analista de productividad empresarial. Analiza los siguientes datos de {context_type} "{context_name}" y genera un informe breve, profesional y accionable en español.

Datos:
- Total de tareas: {stats['total']}
- Distribución por estado: {json.dumps(stats['estados'], ensure_ascii=False)}
- Distribución por prioridad: {json.dumps(stats['prioridades'], ensure_ascii=False)}
- Avance promedio: {stats['avance_promedio']}%
"""
    if 'usuarios_activos' in stats:
        prompt += f"- Usuarios activos: {stats['usuarios_activos']}\n"
        prompt += f"- Grupos activos: {stats['grupos_activos']}\n"

    if 'miembros_detalle' in stats:
        prompt += "\nDetalle por miembro:\n"
        for m in stats['miembros_detalle']:
            prompt += f"  - {m['nombre']}: {m['total_tareas']} tareas, avance promedio {m['avance_promedio']}%\n"

    prompt += """
Genera tu respuesta en formato JSON con las siguientes claves:
{
    "resumen": "Párrafo resumen del estado general",
    "fortalezas": ["lista de fortalezas detectadas"],
    "areas_mejora": ["lista de áreas de mejora"],
    "recomendaciones": ["lista de recomendaciones accionables"],
    "puntuacion": 0-100 (puntuación general de productividad)
}
Responde SOLO con el JSON, sin texto adicional.
"""
    return prompt


def _call_openai(api_key, model, prompt):
    """Llama a la API de OpenAI."""
    import openai
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model or 'gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content


def _call_gemini(api_key, model, prompt):
    """Llama a la API de Google Gemini."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model or 'gemini-1.5-flash')
    response = gen_model.generate_content(prompt)
    return response.text


def _call_anthropic(api_key, model, prompt):
    """Llama a la API de Anthropic Claude."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model or 'claude-3-haiku-20240307',
        max_tokens=1000,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return response.content[0].text


def _fallback_analysis(stats, context_type, context_name):
    """Análisis estadístico local sin IA (fallback)."""
    total = stats.get('total', 0)
    estados = stats.get('estados', {})
    avance = stats.get('avance_promedio', 0)

    terminadas = estados.get('Terminada', 0)
    pendientes = estados.get('Pendiente', 0)
    en_progreso = estados.get('En Progreso', 0)
    canceladas = estados.get('Cancelada', 0)

    tasa_completado = round((terminadas / total) * 100, 1) if total > 0 else 0
    puntuacion = min(100, int(avance * 0.4 + tasa_completado * 0.6))

    fortalezas = []
    areas_mejora = []
    recomendaciones = []

    if tasa_completado > 70:
        fortalezas.append('Alta tasa de completado de tareas')
    if avance > 60:
        fortalezas.append('Buen avance promedio en tareas activas')
    if pendientes == 0:
        fortalezas.append('No hay tareas pendientes sin atender')

    if pendientes > total * 0.5:
        areas_mejora.append('Gran cantidad de tareas pendientes sin iniciar')
        recomendaciones.append('Priorizar y asignar las tareas pendientes')
    if canceladas > total * 0.2:
        areas_mejora.append('Alto porcentaje de tareas canceladas')
        recomendaciones.append('Revisar criterios de planificación para reducir cancelaciones')
    if avance < 30 and en_progreso > 0:
        areas_mejora.append('Bajo avance en tareas en progreso')
        recomendaciones.append('Identificar bloqueos y asignar recursos adicionales')

    if not fortalezas:
        fortalezas.append('Estructura de tareas organizada')
    if not recomendaciones:
        recomendaciones.append('Mantener el ritmo actual de trabajo')

    resumen = (
        f'{context_type.capitalize()} "{context_name}" tiene {total} tareas registradas '
        f'con un avance promedio del {avance}%. '
        f'Se han completado {terminadas} de {total} tareas ({tasa_completado}%).'
    )

    return {
        'resumen': resumen,
        'fortalezas': fortalezas,
        'areas_mejora': areas_mejora,
        'recomendaciones': recomendaciones,
        'puntuacion': puntuacion,
    }


def generate_ai_analysis(empresa_id, context_type='empresa', context_id=None):
    """
    Genera análisis de IA para una empresa, grupo o usuario.

    Args:
        empresa_id: ID de la empresa.
        context_type: 'empresa', 'grupo', o 'usuario'.
        context_id: ID del grupo o usuario (None para empresa).

    Returns:
        dict con análisis y estadísticas.
    """
    company = db.session.get(Company, empresa_id)
    if not company:
        return {'error': 'Empresa no encontrada'}

    # Obtener estadísticas según contexto
    if context_type == 'grupo' and context_id:
        stats = get_group_stats(context_id)
        context_name = stats.get('nombre_grupo', '—')
    elif context_type == 'usuario' and context_id:
        stats = get_user_stats(context_id, empresa_id)
        context_name = stats.get('nombre_usuario', '—')
    else:
        stats = get_company_stats(empresa_id)
        context_name = company.nombre
        context_type = 'empresa'

    # Intentar llamar a la IA
    analysis = None
    ai_used = False

    if company.ai_provider and company.ai_api_key:
        try:
            prompt = _build_prompt(stats, context_type, context_name)
            providers = {
                'openai': _call_openai,
                'gemini': _call_gemini,
                'anthropic': _call_anthropic,
            }
            call_fn = providers.get(company.ai_provider)
            if call_fn:
                raw_response = call_fn(company.ai_api_key, company.ai_model, prompt)
                # Parsear JSON de la respuesta
                cleaned = raw_response.strip()
                if cleaned.startswith('```'):
                    cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0]
                analysis = json.loads(cleaned)
                ai_used = True
        except Exception as e:
            current_app.logger.warning(f'Error en análisis IA ({company.ai_provider}): {e}')

    # Fallback a análisis estadístico
    if not analysis:
        analysis = _fallback_analysis(stats, context_type, context_name)

    return {
        'stats': stats,
        'analysis': analysis,
        'ai_used': ai_used,
        'ai_provider': company.ai_provider_label if ai_used else 'Análisis Estadístico',
        'context_type': context_type,
        'context_name': context_name,
    }
