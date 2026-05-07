# -*- coding: utf-8 -*-
"""
Licenciamiento APP-Key.

La clave se deriva de la razon social obtenida de la CSF. Es deterministica:
para la misma razon social y la misma llave de instalacion, produce la misma
APP-Key KMR-XXXXX-XXXXX-XXXXX-XXXXX.
"""
import base64
import hashlib
import hmac
import re
import unicodedata


APP_KEY_RE = re.compile(r'^KMR-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}$')


def normalize_company_name(name):
    value = unicodedata.normalize('NFKD', name or '')
    value = ''.join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r'[^A-Za-z0-9& ]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip().upper()
    return value


def generate_app_key(company_name, secret):
    normalized_name = normalize_company_name(company_name)
    if not normalized_name:
        return None

    secret_bytes = str(secret or 'PC y Sistemas Mosri').encode('utf-8')
    digest = hmac.new(secret_bytes, normalized_name.encode('utf-8'), hashlib.sha256).digest()
    token = base64.b32encode(digest).decode('ascii').rstrip('=')
    body = token[:20]
    return 'KMR-' + '-'.join(body[index:index + 5] for index in range(0, 20, 5))


def is_valid_app_key_format(app_key):
    return bool(APP_KEY_RE.fullmatch((app_key or '').strip()))


def normalize_app_key(app_key):
    candidate = (app_key or '').strip().upper()
    return candidate if is_valid_app_key_format(candidate) else ''


def validate_app_key(company_name, app_key, secret):
    candidate = normalize_app_key(app_key)
    if not is_valid_app_key_format(candidate):
        return False
    expected = generate_app_key(company_name, secret)
    return bool(expected and hmac.compare_digest(candidate.upper(), expected.upper()))


def company_has_valid_app_key(company, secret):
    if not company or not company.razon_social:
        return True
    return validate_app_key(company.razon_social, company.app_key, secret)
