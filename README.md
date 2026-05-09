# 📋 Bitácora SaaS by KzmCITO - Kassim Assad Mosri Rodríguez — Sistema de Gestión Operativa Multi-Empresa

Plataforma SaaS multi-tenant para gestión de tareas operativas con seguimiento detallado (bitácora de avances), analítica con IA, calendario visual, generación de reportes PDF, marketing asistido por IA, soporte técnico y compartición vía email/WhatsApp.

## 🚀 Inicio Rápido

### Opción A: Docker (Recomendada)

```bash
# Clonar el repositorio
git clone https://github.com/KassimCITO/bitacora.git
cd bitacora

# Levantar con Docker Compose
docker-compose up -d

# Inicializar datos de ejemplo
docker-compose exec web python seed.py
```

La aplicación estará disponible en: **http://localhost** (puerto 80 vía Nginx)

### Opción B: Desarrollo Local

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
# Editar .env con tus valores (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY)

# 4. Inicializar BD y datos de ejemplo
python seed.py

# 5. Ejecutar
python run.py
```

Disponible en: **http://localhost:5000**

## 🔑 Credenciales por Defecto

| Rol | Usuario | Contraseña | Acceso |
|-----|---------|------------|--------|
| Superuser | `superuser` | `super123` | Gestión global de empresas |
| Administrador | `admin` | `admin123` | Admin de empresa demo |
| Manager | `manager1` | `manager123` | Crear/asignar tareas |
| Usuario | `user1` | `user123` | Tareas asignadas |
| Visor | `visor1` | `visor123` | Solo lectura |

> ⚠️ **Cambiar las contraseñas** después del primer inicio de sesión.

## 📁 Estructura del Proyecto

```
bitácora/
├── app/
│   ├── __init__.py          # Application Factory
│   ├── config.py            # Configuración (dev/prod/test)
│   ├── extensions.py        # Extensiones Flask
│   ├── models/              # Modelos: Company, Group, User, Task, etc.
│   ├── routes/              # Blueprints: auth, dashboard, tasks, marketing, support, reports, api
│   ├── services/            # Servicios: IA, PDF, email, CSV, marketing, soporte
│   ├── templates/           # Plantillas Jinja2
│   ├── static/              # CSS, JS (calendar, analytics), imágenes
│   └── utils/               # Decoradores, helpers, sanitizador, crypto
├── tests/                   # Suite de tests (34+ tests)
├── docs/                    # Manuales de usuario e instalación
├── uploads/                 # Archivos adjuntos
├── Dockerfile               # Imagen Docker
├── docker-compose.yml       # Orquestación (web + PostgreSQL + Nginx)
├── nginx.conf               # Reverse proxy
├── run.py                   # Entry point
├── seed.py                  # Datos iniciales multi-tenant
└── requirements.txt         # Dependencias
```

## 🏢 Arquitectura Multi-Empresa (SaaS)

- **Superuser**: Administrador global que gestiona todas las empresas
- **Empresa**: Cada empresa tiene su propia configuración (SMTP, IA, datos fiscales)
- **Grupos**: Agrupación funcional de usuarios (Gerencia, Programación, etc.)
- **Aislamiento**: Los datos de cada empresa están completamente aislados

## 👥 Roles del Sistema

- **Superuser**: Gestión global de empresas y configuración del sistema
- **Administrador**: Admin de empresa, gestión de usuarios y grupos
- **Manager**: Crear/asignar tareas, generar reportes
- **Usuario**: Ver y actualizar tareas asignadas
- **Visor**: Solo lectura, exportar reportes

## 📊 Funcionalidades

- **Dashboard** con calendario visual (Diario/Semanal/Mensual/Anual) y mapa de calor
- **Gestión de tareas** con bitácora de avances, adjuntos y compartición
- **Analítica con IA** (OpenAI, Gemini, Anthropic) — gráficos de pie por empresa, grupo y usuario
- **Marketing** con campañas, copy RRSS, importación CSV Facebook, kit IA y CronJobs
- **Soporte técnico** con chat por empresa, adjuntos y enlace WhatsApp al celular configurado
- **Reportes PDF** profesionales con logo y datos de empresa
- **Exportación CSV** con filtros
- **Email** con configuración SMTP por empresa
- **WhatsApp** compartición de tareas

## ⚙️ Variables de Entorno

```bash
FLASK_CONFIG=development          # development | production | testing
SECRET_KEY=tu-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/bitacora_db
ENCRYPTION_KEY=tu-fernet-key      # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> La configuración de SMTP e IA se gestiona desde la UI por empresa.

## 🧪 Tests

```bash
python -m pytest tests/ -v --cov=app
```

Suite actual: **98 tests**.

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.12+ / Flask 3.x
- **Frontend**: HTML5 + Bootstrap 5.3 + Chart.js + JavaScript
- **Base de datos**: PostgreSQL 16 (producción) / SQLite (desarrollo)
- **ORM**: SQLAlchemy 2.x + Flask-Migrate
- **IA**: OpenAI, Google Gemini, Anthropic (configurable)
- **PDF**: ReportLab
- **Email**: Flask-Mail (SMTP configurable por empresa)
- **Deploy**: Docker + Gunicorn + Nginx
