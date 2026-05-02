# -*- coding: utf-8 -*-
"""
Utilidad de cifrado para credenciales sensibles.
"""
from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    """Obtiene la instancia de Fernet para cifrado/descifrado."""
    key = current_app.config.get('ENCRYPTION_KEY', '')
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def encrypt_value(value):
    """Cifra un valor sensible."""
    if not value:
        return None
    f = get_fernet()
    if f:
        return f.encrypt(value.encode('utf-8')).decode('utf-8')
    return value


def decrypt_value(value):
    """Descifra un valor sensible."""
    if not value:
        return None
    f = get_fernet()
    if f:
        try:
            return f.decrypt(value.encode('utf-8')).decode('utf-8')
        except Exception:
            return value
    return value
