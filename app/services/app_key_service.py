# -*- coding: utf-8 -*-
"""
Licenciamiento APP-Key.

La clave se deriva de la razon social obtenida de la CSF. Es deterministica:
para la misma razon social, vigencia y llave de instalacion, produce la misma
APP-Key KMR-XXXXX-XXXXX-XXXXX-XXXXX. Las claves legadas sin fecha se siguen
validando durante su ventana migrada para no cortar acceso existente.
"""
import base64
import hashlib
import hmac
import re
import unicodedata
from datetime import datetime, timedelta, timezone


APP_KEY_RE = re.compile(r'^KMR-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}$')
DEFAULT_APP_KEY_VALID_DAYS = 365
MIN_APP_KEY_VALID_DAYS = 1
MAX_APP_KEY_VALID_DAYS = 3650


def utcnow():
    return datetime.now(timezone.utc)


def normalize_company_name(name):
    value = unicodedata.normalize('NFKD', name or '')
    value = ''.join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r'[^A-Za-z0-9& ]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip().upper()
    return value


def normalize_valid_days(days):
    try:
        value = int(days)
    except (TypeError, ValueError):
        value = DEFAULT_APP_KEY_VALID_DAYS
    return max(MIN_APP_KEY_VALID_DAYS, min(MAX_APP_KEY_VALID_DAYS, value))


def ensure_aware(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_app_key_window(valid_days=None, issued_at=None):
    issued_at = ensure_aware(issued_at) or utcnow()
    valid_days = normalize_valid_days(valid_days)
    expires_at = issued_at + timedelta(days=valid_days)
    return issued_at, expires_at, valid_days


def _key_payload(company_name, expires_at=None):
    normalized_name = normalize_company_name(company_name) or 'SIN RAZON SOCIAL'
    expires_at = ensure_aware(expires_at)
    if not expires_at:
        return normalized_name
    return f'{normalized_name}|EXP:{expires_at.date().isoformat()}'


def generate_app_key(company_name, secret, expires_at=None):
    payload = _key_payload(company_name, expires_at)
    if not payload:
        return None
    secret_bytes = str(secret or 'PC y Sistemas Mosri').encode('utf-8')
    digest = hmac.new(secret_bytes, payload.encode('utf-8'), hashlib.sha256).digest()
    token = base64.b32encode(digest).decode('ascii').rstrip('=')
    body = token[:20]
    return 'KMR-' + '-'.join(body[index:index + 5] for index in range(0, 20, 5))


def is_valid_app_key_format(app_key):
    return bool(APP_KEY_RE.fullmatch((app_key or '').strip()))


def normalize_app_key(app_key):
    candidate = (app_key or '').strip().upper()
    return candidate if is_valid_app_key_format(candidate) else ''


def validate_app_key(company_name, app_key, secret, expires_at=None, allow_legacy=False, now=None):
    candidate = normalize_app_key(app_key)
    if not is_valid_app_key_format(candidate):
        return False

    expires_at = ensure_aware(expires_at)
    if expires_at and (ensure_aware(now) or utcnow()) > expires_at:
        return False

    expected = generate_app_key(company_name, secret, expires_at)
    if expected and hmac.compare_digest(candidate.upper(), expected.upper()):
        return True

    if allow_legacy:
        legacy_expected = generate_app_key(company_name, secret)
        return bool(legacy_expected and hmac.compare_digest(candidate.upper(), legacy_expected.upper()))

    return False


def company_has_valid_app_key(company, secret):
    if not company or not company.razon_social:
        return True
    return validate_app_key(
        company.razon_social,
        company.app_key,
        secret,
        getattr(company, 'app_key_expires_at', None),
        allow_legacy=True,
    )
