/**
 * Bitácora — Analytics Charts & AI Integration
 * Uses Chart.js for pie charts and fetches AI analysis via AJAX.
 */

const CHART_COLORS = ['#00d4aa','#0dcaf0','#ffc107','#dc3545','#6c757d','#198754','#6610f2','#fd7e14'];
const ESTADO_COLORS = {'Pendiente':'#ffc107','En Progreso':'#0dcaf0','Pausada':'#6c757d','Terminada':'#198754','Cancelada':'#dc3545'};

function initCharts(estadosData, gruposData, usuariosData) {
    // Estados pie chart
    const ctxEstados = document.getElementById('chartEstados');
    if (ctxEstados && Object.keys(estadosData).length > 0) {
        const labels = Object.keys(estadosData);
        const data = Object.values(estadosData);
        const colors = labels.map(l => ESTADO_COLORS[l] || '#6c757d');
        new Chart(ctxEstados, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
            options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true } } } }
        });
    }

    // Groups pie chart
    const ctxGrupos = document.getElementById('chartGrupos');
    if (ctxGrupos && gruposData.length > 0) {
        const labels = gruposData.map(g => g.nombre);
        const data = gruposData.map(g => g.stats.avance_promedio);
        const colors = gruposData.map(g => g.color || '#00d4aa');
        new Chart(ctxGrupos, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
            options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true } } } }
        });
    }

    // Users pie chart
    const ctxUsuarios = document.getElementById('chartUsuarios');
    if (ctxUsuarios && usuariosData.length > 0) {
        const top = usuariosData.slice(0, 8);
        const labels = top.map(u => u.nombre.split(' ')[0]);
        const data = top.map(u => u.stats.avance_promedio);
        new Chart(ctxUsuarios, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: CHART_COLORS.slice(0, top.length), borderWidth: 0 }] },
            options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true } } } }
        });
    }
}

function requestAiAnalysis(contextType, contextId) {
    const panel = document.getElementById('aiPanel');
    const content = document.getElementById('aiContent');
    const badge = document.getElementById('aiProviderBadge');

    panel.style.display = 'block';
    content.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-accent"></div><p class="text-muted mt-2">Generando análisis...</p></div>';
    panel.scrollIntoView({ behavior: 'smooth' });

    fetch('/analytics/api/ai-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_type: contextType, context_id: contextId || null })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            content.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        badge.textContent = data.ai_provider || '';
        const a = data.analysis;
        let html = `<p class="mb-3">${a.resumen}</p>`;
        if (a.puntuacion !== undefined) {
            const color = a.puntuacion >= 70 ? 'success' : a.puntuacion >= 40 ? 'warning' : 'danger';
            html += `<div class="mb-3"><span class="badge bg-${color} fs-6">Puntuación: ${a.puntuacion}/100</span></div>`;
        }
        if (a.fortalezas && a.fortalezas.length) {
            html += '<h6 class="fw-semibold text-success"><i class="bi bi-check-circle me-1"></i>Fortalezas</h6><ul class="mb-3">';
            a.fortalezas.forEach(f => html += `<li>${f}</li>`);
            html += '</ul>';
        }
        if (a.areas_mejora && a.areas_mejora.length) {
            html += '<h6 class="fw-semibold text-warning"><i class="bi bi-exclamation-circle me-1"></i>Áreas de Mejora</h6><ul class="mb-3">';
            a.areas_mejora.forEach(f => html += `<li>${f}</li>`);
            html += '</ul>';
        }
        if (a.recomendaciones && a.recomendaciones.length) {
            html += '<h6 class="fw-semibold text-info"><i class="bi bi-lightbulb me-1"></i>Recomendaciones</h6><ul class="mb-0">';
            a.recomendaciones.forEach(f => html += `<li>${f}</li>`);
            html += '</ul>';
        }
        content.innerHTML = html;
    })
    .catch(() => {
        content.innerHTML = '<div class="alert alert-danger">Error al generar análisis.</div>';
    });
}
