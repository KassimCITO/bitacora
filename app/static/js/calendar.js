/**
 * Bitácora — Calendar Grid
 * Renders a heatmap calendar with Daily/Weekly/Monthly/Yearly views.
 * Fetches data via AJAX from /api/calendar-data
 */
(function () {
    'use strict';

    const MONTHS_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const DAYS_ES = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];

    let currentView = 'monthly';
    let currentDate = new Date();

    const grid = document.getElementById('calendarGrid');
    const title = document.getElementById('calendarTitle');
    if (!grid) return;

    // View buttons
    document.querySelectorAll('#calViewButtons [data-view]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#calViewButtons .btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;
            loadCalendar();
        });
    });

    // Navigation
    document.getElementById('calPrev')?.addEventListener('click', () => navigate(-1));
    document.getElementById('calNext')?.addEventListener('click', () => navigate(1));
    document.getElementById('calToday')?.addEventListener('click', () => {
        currentDate = new Date();
        loadCalendar();
    });

    function navigate(dir) {
        const d = new Date(currentDate);
        if (currentView === 'daily') d.setDate(d.getDate() + dir);
        else if (currentView === 'weekly') d.setDate(d.getDate() + dir * 7);
        else if (currentView === 'monthly') d.setMonth(d.getMonth() + dir);
        else if (currentView === 'yearly') d.setFullYear(d.getFullYear() + dir);
        currentDate = d;
        loadCalendar();
    }

    function formatDate(d) {
        return d.toISOString().split('T')[0];
    }

    function getLevel(pendientes) {
        if (pendientes === 0) return 0;
        if (pendientes <= 2) return 1;
        if (pendientes <= 5) return 2;
        return 3;
    }

    function loadCalendar() {
        const dateStr = formatDate(currentDate);
        grid.innerHTML = '<div class="text-center py-4"><div class="spinner-border spinner-border-sm text-accent" role="status"></div></div>';

        fetch(`/api/calendar-data?view=${currentView}&date=${dateStr}`)
            .then(r => r.json())
            .then(data => renderCalendar(data))
            .catch(() => {
                grid.innerHTML = '<p class="text-muted text-center py-3">Error al cargar calendario</p>';
            });
    }

    function renderCalendar(data) {
        const items = data.items || {};
        const start = new Date(data.start + 'T00:00:00');
        const end = new Date(data.end + 'T00:00:00');
        const today = formatDate(new Date());

        // Update title
        if (currentView === 'daily') {
            title.textContent = `${start.getDate()} ${MONTHS_ES[start.getMonth()]} ${start.getFullYear()}`;
        } else if (currentView === 'weekly') {
            title.textContent = `${start.getDate()} — ${end.getDate()} ${MONTHS_ES[start.getMonth()]} ${start.getFullYear()}`;
        } else if (currentView === 'monthly') {
            title.textContent = `${MONTHS_ES[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
        } else {
            title.textContent = `${currentDate.getFullYear()}`;
        }

        if (currentView === 'daily') {
            renderDailyView(items, start, today);
        } else if (currentView === 'weekly') {
            renderWeeklyView(items, start, today);
        } else if (currentView === 'monthly') {
            renderMonthlyView(items, start, end, today);
        } else {
            renderYearlyView(items, today);
        }
    }

    function renderDailyView(items, start, today) {
        const key = formatDate(start);
        const item = items[key] || { total: 0, pendientes: 0, terminadas: 0 };
        const level = getLevel(item.pendientes);

        grid.innerHTML = `
            <div class="cal-daily-view">
                <div class="cal-daily-cell cal-level-${level}">
                    <div class="cal-daily-number">${start.getDate()}</div>
                    <div class="cal-daily-stats">
                        <span><i class="bi bi-clock"></i> ${item.pendientes} pendientes</span>
                        <span><i class="bi bi-check-circle"></i> ${item.terminadas} terminadas</span>
                        <span><i class="bi bi-clipboard2-data"></i> ${item.total} total</span>
                    </div>
                </div>
            </div>`;
    }

    function renderWeeklyView(items, start, today) {
        let html = '<div class="cal-weekly-view">';
        const d = new Date(start);
        for (let i = 0; i < 7; i++) {
            const key = formatDate(d);
            const item = items[key] || { total: 0, pendientes: 0, terminadas: 0 };
            const level = getLevel(item.pendientes);
            const isToday = key === today;

            html += `
                <div class="cal-week-cell cal-level-${level} ${isToday ? 'cal-today' : ''}" title="${item.pendientes} pendientes, ${item.terminadas} terminadas">
                    <div class="cal-week-day">${DAYS_ES[i]}</div>
                    <div class="cal-week-number">${d.getDate()}</div>
                    <div class="cal-week-count">${item.total}</div>
                </div>`;
            d.setDate(d.getDate() + 1);
        }
        html += '</div>';
        grid.innerHTML = html;
    }

    function renderMonthlyView(items, start, end, today) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        let startDow = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1; // Monday=0

        let html = '<div class="cal-month-view">';
        // Day headers
        DAYS_ES.forEach(d => {
            html += `<div class="cal-month-header">${d}</div>`;
        });

        // Empty cells before first day
        for (let i = 0; i < startDow; i++) {
            html += '<div class="cal-month-cell cal-empty"></div>';
        }

        // Day cells
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const dateObj = new Date(year, month, day);
            const key = formatDate(dateObj);
            const item = items[key] || { total: 0, pendientes: 0, terminadas: 0 };
            const level = getLevel(item.pendientes);
            const isToday = key === today;

            html += `
                <div class="cal-month-cell cal-level-${level} ${isToday ? 'cal-today' : ''}"
                     title="${day}/${month+1}: ${item.pendientes} pendientes, ${item.terminadas} terminadas, ${item.total} total">
                    <span class="cal-day-num">${day}</span>
                    ${item.total > 0 ? `<span class="cal-day-count">${item.total}</span>` : ''}
                </div>`;
        }

        html += '</div>';
        grid.innerHTML = html;
    }

    function renderYearlyView(items, today) {
        const year = currentDate.getFullYear();
        let html = '<div class="cal-yearly-view">';

        for (let m = 0; m < 12; m++) {
            html += `<div class="cal-year-month">`;
            html += `<div class="cal-year-month-title">${MONTHS_ES[m].substring(0, 3)}</div>`;
            html += '<div class="cal-year-grid">';

            const firstDay = new Date(year, m, 1);
            const lastDay = new Date(year, m + 1, 0);
            let startDow = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;

            for (let i = 0; i < startDow; i++) {
                html += '<div class="cal-year-cell cal-empty"></div>';
            }

            for (let day = 1; day <= lastDay.getDate(); day++) {
                const key = formatDate(new Date(year, m, day));
                const item = items[key] || { total: 0, pendientes: 0 };
                const level = getLevel(item.pendientes);
                const isToday = key === today;

                html += `<div class="cal-year-cell cal-level-${level} ${isToday ? 'cal-today' : ''}"
                              title="${day}/${m+1}/${year}: ${item.pendientes} pend."></div>`;
            }

            html += '</div></div>';
        }

        html += '</div>';
        grid.innerHTML = html;
    }

    // Initial load
    loadCalendar();
})();
