/**
 * Editor enriquecido reutilizable.
 * Soporta imágenes optimizadas y PDFs con visor modal propio.
 */
(function () {
    'use strict';

    function uploadFile(file, type) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type);

        return fetch(window.BITACORA_EDITOR_UPLOAD_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': window.BITACORA_CSRF_TOKEN },
            body: formData
        }).then(async function (response) {
            const data = await response.json();
            if (!response.ok || !data.url) {
                throw new Error(data.error || 'No se pudo subir el archivo.');
            }
            return data;
        });
    }

    function chooseFile(accept, callback) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = accept;
        input.click();
        input.addEventListener('change', function () {
            const file = input.files && input.files[0];
            if (file) { callback(file); }
        });
    }

    function insertUploadStatus(quill, range, text) {
        quill.insertText(range.index, text, 'user');
        return function removeStatus() {
            quill.deleteText(range.index, text.length);
        };
    }

    function imageHandler(quill) {
        chooseFile('image/png,image/jpeg,image/webp,image/gif,image/avif', async function (file) {
            const range = quill.getSelection(true);
            const removeStatus = insertUploadStatus(quill, range, 'Subiendo imagen...');
            try {
                const data = await uploadFile(file, 'image');
                removeStatus();
                quill.insertEmbed(range.index, 'image', data.url, 'user');
                quill.setSelection(range.index + 1, 0);
            } catch (error) {
                removeStatus();
                alert(error.message || 'No se pudo subir la imagen.');
            }
        });
    }

    function pdfHandler(quill) {
        chooseFile('application/pdf,.pdf', async function (file) {
            const range = quill.getSelection(true);
            const removeStatus = insertUploadStatus(quill, range, 'Subiendo PDF...');
            try {
                const data = await uploadFile(file, 'pdf');
                removeStatus();
                const label = data.name || 'Documento PDF';
                const safeUrl = data.url.replace(/"/g, '&quot;');
                const safeLabel = label
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');
                const html = `<p><a href="${safeUrl}" class="pdf-viewer-link" data-pdf-url="${safeUrl}" target="_blank" rel="noopener"><span class="pdf-viewer-icon"></span><span class="pdf-viewer-copy"><span class="pdf-viewer-kicker">Documento PDF</span><span class="pdf-viewer-name">${safeLabel}</span></span></a></p>`;
                quill.clipboard.dangerouslyPasteHTML(range.index, html, 'user');
                quill.setSelection(range.index + label.length + 2, 0);
            } catch (error) {
                removeStatus();
                alert(error.message || 'No se pudo subir el PDF.');
            }
        });
    }

    function createEditor(editorEl) {
        const input = document.getElementById(editorEl.dataset.input);
        const placeholder = editorEl.dataset.placeholder || 'Escribe contenido...';
        const quill = new Quill(editorEl, {
            theme: 'snow',
            placeholder: placeholder,
            modules: {
                toolbar: {
                    container: [
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['blockquote', 'code-block'],
                        ['link', 'image', 'pdf'],
                        ['clean']
                    ],
                    handlers: {
                        image: function () { imageHandler(quill); },
                        pdf: function () { pdfHandler(quill); }
                    }
                }
            }
        });

        const toolbar = editorEl.parentElement.querySelector('.ql-toolbar');
        const pdfButton = toolbar ? toolbar.querySelector('button.ql-pdf') : null;
        if (pdfButton) {
            pdfButton.setAttribute('type', 'button');
            pdfButton.setAttribute('title', 'Insertar PDF');
            pdfButton.setAttribute('aria-label', 'Insertar PDF');
        }

        if (input) {
            const form = editorEl.closest('form');
            if (form) {
                form.addEventListener('submit', function () {
                    const html = quill.root.innerHTML;
                    input.value = (html === '<p><br></p>') ? '' : html;
                });
            }
        }

        window.BITACORA_RICH_EDITORS = window.BITACORA_RICH_EDITORS || {};
        if (editorEl.dataset.input) {
            window.BITACORA_RICH_EDITORS[editorEl.dataset.input] = quill;
        }

        return quill;
    }

    window.initRichEditors = function initRichEditors() {
        document.querySelectorAll('.js-rich-editor').forEach(function (editorEl) {
            if (!editorEl.dataset.initialized) {
                editorEl.dataset.initialized = '1';
                createEditor(editorEl);
            }
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        if (window.Quill) { window.initRichEditors(); }
    });
})();
