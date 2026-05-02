# -*- coding: utf-8 -*-
"""
Servicio de envío de correos electrónicos.
Utiliza Flask-Mail para envío de reportes PDF como adjuntos.
"""
from flask import current_app
from flask_mail import Message
from ..extensions import mail


def send_report_email(recipient, subject, body, pdf_bytes=None, pdf_filename='reporte.pdf'):
    """
    Envía un correo con un PDF adjunto.

    Args:
        recipient: Email del destinatario.
        subject: Asunto del correo.
        body: Cuerpo del correo (texto plano).
        pdf_bytes: Contenido del PDF como bytes.
        pdf_filename: Nombre del archivo adjunto.
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
        )

        if pdf_bytes:
            msg.attach(
                filename=pdf_filename,
                content_type='application/pdf',
                data=pdf_bytes,
            )

        mail.send(msg)
        return True, 'Correo enviado exitosamente.'
    except Exception as e:
        current_app.logger.error(f'Error enviando correo: {str(e)}')
        return False, f'Error al enviar correo: {str(e)}'
