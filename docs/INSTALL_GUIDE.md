# 🛠️ Guía de Instalación, Puesta a Punto y Ejecución — Bitácora SaaS by KzmCITO - Kassim Assad Mosri Rodríguez

---

## Requisitos del Sistema

| Componente | Versión Mínima | Notas |
|-----------|----------------|-------|
| Python | 3.12+ | Requerido para desarrollo local |
| PostgreSQL | 16+ | Producción (SQLite disponible para desarrollo) |
| Docker | 24+ | Opcional, recomendado para producción |
| Docker Compose | 2.20+ | Incluido en Docker Desktop |
| Git | 2.40+ | Para clonar el repositorio |

---

## Opción 1: Docker (Recomendada para Producción)

### 1. Clonar el repositorio

```bash
git clone https://github.com/KassimCITO/bitacora.git
cd bitacora
```

### 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
FLASK_CONFIG=production
SECRET_KEY=tu-clave-secreta-segura
ENCRYPTION_KEY=tu-clave-fernet
```

**Generar claves seguras:**

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY (Fernet)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Levantar los servicios

```bash
docker-compose up -d
```

Esto despliega 4 servicios:

| Servicio | Descripción | Puerto |
|----------|-------------|--------|
| **db** | PostgreSQL 16 Alpine | 5432 |
| **web** | Flask + Gunicorn (4 workers) | 5000 (interno) |
| **scheduler** | Ejecuta CronJobs de marketing con `flask marketing run-due-jobs` | interno |
| **nginx** | Reverse proxy | **80** (público) |

### 4. Inicializar la base de datos

```bash
docker-compose exec web python seed.py
```

Esto crea: roles, superuser, empresa demo, usuarios, grupos y tareas de ejemplo.

### 5. Acceder

Abre **http://localhost** en tu navegador.

### 6. Comandos útiles Docker

```bash
# Ver logs
docker-compose logs -f web

# Reiniciar servicios
docker-compose restart

# Detener todo
docker-compose down

# Reconstruir imagen (después de cambios)
docker-compose build --no-cache
docker-compose up -d

# Aplicar migraciones
docker-compose exec web flask db upgrade

# Ejecutar tests dentro del contenedor
docker-compose exec web python -m pytest tests/ -v

# Acceder al shell del contenedor
docker-compose exec web bash

# Acceder a PostgreSQL
docker-compose exec db psql -U bitacora_user -d bitacora_db
```

---

## Opción 2: Desarrollo Local

### 1. Instalar Python 3.12+

- **Windows**: Descarga desde [python.org](https://www.python.org/downloads/). Marca "Add to PATH".
- **macOS**: `brew install python@3.12`
- **Linux**: `sudo apt install python3.12 python3.12-venv`

### 2. Instalar PostgreSQL (Opcional)

Para producción, instala PostgreSQL desde [postgresql.org](https://www.postgresql.org/download/).

Crea la base de datos:
```sql
CREATE USER bitacora_user WITH PASSWORD 'bitacora_pass';
CREATE DATABASE bitacora_db OWNER bitacora_user;
GRANT ALL PRIVILEGES ON DATABASE bitacora_db TO bitacora_user;
```

> 💡 Para desarrollo rápido puedes usar **SQLite** (sin instalar PostgreSQL).

### 3. Clonar y configurar

```bash
git clone https://github.com/KassimCITO/bitacora.git
cd bitacora

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate          # Windows (CMD/PowerShell)
source venv/bin/activate       # macOS / Linux

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Configurar `.env`

**Con PostgreSQL (producción):**
```bash
FLASK_CONFIG=development
SECRET_KEY=tu-clave-secreta
DATABASE_URL=postgresql://bitacora_user:bitacora_pass@localhost:5432/bitacora_db
ENCRYPTION_KEY=tu-clave-fernet
```

**Con SQLite (desarrollo rápido):**
```bash
FLASK_CONFIG=development
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///instance/bitacora.db
ENCRYPTION_KEY=tu-clave-fernet
```

### 5. Inicializar y ejecutar

```bash
# Crear tablas y datos de ejemplo
python seed.py

# Ejecutar el servidor
python run.py
```

La app estará en: **http://localhost:5000**

---

## Variables de Entorno

| Variable | Descripción | Valor por Defecto |
|----------|-------------|-------------------|
| `FLASK_CONFIG` | Entorno: `development`, `production`, `testing` | `development` |
| `SECRET_KEY` | Clave secreta de Flask para sesiones | ⚠️ Cambiar en producción |
| `DATABASE_URL` | URI de conexión a la base de datos | SQLite local |
| `ENCRYPTION_KEY` | Clave Fernet para cifrar credenciales en BD | ⚠️ Cambiar en producción |
| `MARKETING_CRON_INTERVAL_SECONDS` | Intervalo del scheduler de CronJobs de marketing en Docker | `60` |

> La configuración de **SMTP** e **IA** se gestiona desde la interfaz web por cada empresa.

---

## Configuración SMTP (por Empresa)

Se configura desde la UI: **Configuración de Empresa** → pestaña **Email**.

### Ejemplo: Gmail con App Password

| Campo | Valor |
|-------|-------|
| Servidor | `smtp.gmail.com` |
| Puerto | `587` |
| TLS | ✅ Activado |
| SSL | ❌ Desactivado |
| Usuario | tu-correo@gmail.com |
| Contraseña | [App Password](https://myaccount.google.com/apppasswords) |
| Remitente | tu-correo@gmail.com |

### Ejemplo: Outlook/Office 365

| Campo | Valor |
|-------|-------|
| Servidor | `smtp.office365.com` |
| Puerto | `587` |
| TLS | ✅ Activado |
| Usuario | tu-correo@outlook.com |
| Contraseña | tu contraseña |

---

## Configuración de IA (por Empresa)

Se configura desde la UI: **Configuración de Empresa** → pestaña **IA**.

### Modelos Recomendados

| Proveedor | Modelo Económico | Modelo Avanzado |
|-----------|-----------------|-----------------|
| **OpenAI** | `gpt-4o-mini` | `gpt-4o` |
| **Google Gemini** | `gemini-1.5-flash` | `gemini-1.5-pro` |
| **Anthropic** | `claude-3-haiku-20240307` | `claude-3-5-sonnet-20241022` |

> Sin API Key configurada, el sistema usa análisis estadístico local (fallback automático).

---

## Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con cobertura de código
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Solo tests de un archivo
python -m pytest tests/test_app.py -v

# Solo una clase de tests
python -m pytest tests/test_services.py::TestPDFService -v
```

**Suite actual**: 98 tests cubriendo modelos, autenticación, rutas, servicios (PDF, CSV, IA), marketing, soporte, CRUD, seguridad multi-tenant y edge cases.

---

## Backup de Base de Datos

### PostgreSQL (Docker)

```bash
# Crear backup
docker-compose exec db pg_dump -U bitacora_user bitacora_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup_20260502.sql | docker-compose exec -T db psql -U bitacora_user -d bitacora_db
```

### PostgreSQL (Local)

```bash
pg_dump -U bitacora_user bitacora_db > backup.sql
psql -U bitacora_user -d bitacora_db < backup.sql
```

### SQLite

```bash
# Simplemente copia el archivo
cp instance/bitacora.db instance/bitacora_backup.db
```

---

## Actualización del Sistema

```bash
# 1. Detener servicios
docker-compose down

# 2. Obtener última versión
git pull origin main

# 3. Reconstruir y levantar
docker-compose build --no-cache
docker-compose up -d

# 4. Aplicar migraciones (si hay cambios de BD)
docker-compose exec web flask db upgrade
```

---

## Producción con HTTPS

Para habilitar HTTPS, coloca tus certificados SSL y modifica `nginx.conf`:

```nginx
server {
    listen 443 ssl;
    server_name tu-dominio.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    client_max_body_size 16M;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name tu-dominio.com;
    return 301 https://$server_name$request_uri;
}
```

Monta los certificados en `docker-compose.yml`:
```yaml
nginx:
  volumes:
    - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - ./ssl:/etc/nginx/ssl:ro
```

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Error de conexión a PostgreSQL | Verifica que el servicio esté corriendo y las credenciales en `.env` sean correctas |
| Error `ENCRYPTION_KEY` inválida | Genera una clave Fernet válida: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| Error al enviar email | Verifica la configuración SMTP en la pestaña Email de la empresa |
| IA no genera análisis | Verifica la API Key y el proveedor en la pestaña IA de la empresa. El sistema usará fallback estadístico |
| Docker Compose falla al iniciar | Asegúrate de tener Docker Desktop corriendo. Ejecuta `docker-compose logs` para ver errores |
| Puerto 80 ocupado | Cambia el puerto en `docker-compose.yml`: `"8080:80"` |
| `seed.py` falla | Asegúrate de que la BD esté accesible y las tablas no existan previamente |
| Archivo adjunto no se sube | Verifica que el archivo sea de un tipo permitido y no supere 16 MB |
| La app no inicia en Windows | Usa `venv\Scripts\activate` (no `source`) y asegúrate de tener Python 3.12+ |
| Error de migraciones | Ejecuta `flask db stamp head` para sincronizar, luego `flask db upgrade` |
