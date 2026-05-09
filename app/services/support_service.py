# -*- coding: utf-8 -*-
"""Servicios auxiliares para soporte y WhatsApp."""
import re
import urllib.parse


def normalize_whatsapp_phone(phone):
    """Normaliza un celular a dígitos internacionales para wa.me."""
    if not phone:
        return ''
    return re.sub(r'\D+', '', phone)


def build_whatsapp_url(phone, message):
    """Construye URL wa.me con mensaje precargado."""
    normalized = normalize_whatsapp_phone(phone)
    if not normalized:
        return None
    return f'https://wa.me/{normalized}?text={urllib.parse.quote(message)}'
