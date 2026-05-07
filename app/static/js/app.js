/**
 * Bitácora — Frontend JavaScript
 * Dark/Light theme toggle + interactive features
 */
(function () {
    'use strict';

    // ========================================
    // Theme Toggle (Dark / Light)
    // ========================================
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const html = document.documentElement;

    function setTheme(theme) {
        html.setAttribute('data-bs-theme', theme);
        localStorage.setItem('bitacora-theme', theme);
        if (themeIcon) {
            themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        }
    }

    // Cargar tema guardado o usar dark por defecto
    const savedTheme = localStorage.getItem('bitacora-theme') || 'dark';
    setTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const current = html.getAttribute('data-bs-theme');
            setTheme(current === 'dark' ? 'light' : 'dark');
        });
    }

    // ========================================
    // Auto-dismiss flash alerts after 5s
    // ========================================
    document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // ========================================
    // Confirm destructive actions
    // ========================================
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            if (!confirm(el.dataset.confirm || '¿Estás seguro?')) {
                e.preventDefault();
            }
        });
    });

    // ========================================
    // Tooltip initialization
    // ========================================
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (el) {
        bootstrap.Tooltip.getOrCreateInstance(el, { trigger: 'hover focus', container: 'body' });
    });

})();
