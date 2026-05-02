# 📖 Guía de Usuario — Bitácora SaaS

> Sistema de Gestión Operativa Multi-Empresa con analítica IA, calendario visual y reportes PDF.

---

## 1. Inicio de Sesión

1. Abre **http://localhost** (Docker) o **http://localhost:5000** (desarrollo local).
2. Ingresa tu **usuario** y **contraseña**.
3. Si tu cuenta pertenece a una empresa, entrarás directamente a su dashboard.
4. Si tu cuenta está **desactivada**, verás un mensaje y no podrás ingresar. Contacta al administrador.

### Credenciales por Defecto

| Rol | Usuario | Contraseña | Acceso |
|-----|---------|------------|--------|
| Superuser | `superuser` | `super123` | Gestión global de empresas |
| Administrador | `admin` | `admin123` | Admin de empresa demo |
| Manager | `manager1` | `manager123` | Crear/asignar tareas |
| Usuario | `user1` | `user123` | Tareas asignadas |
| Visor | `visor1` | `visor123` | Solo lectura |

> ⚠️ **Cambia las contraseñas** después del primer inicio de sesión.

---

## 2. Roles del Sistema

| Rol | Permisos |
|-----|----------|
| **Superuser** | Gestión global: crear/editar/desactivar empresas, cambiar entre empresas, acceso total |
| **Administrador** | Admin de su empresa: gestionar usuarios, grupos, configuración, tareas y reportes |
| **Manager** | Crear y asignar tareas, generar reportes, ver analítica, compartir por email/WhatsApp |
| **Usuario** | Ver y actualizar avances en sus tareas asignadas, subir adjuntos |
| **Visor** | Solo lectura: ver tareas, exportar reportes CSV/PDF |

---

## 3. Dashboard

El dashboard muestra un resumen ejecutivo con:

- **Tarjetas de estado**: Total, Pendientes, En Progreso, Pausadas, Terminadas, Urgentes (alta prioridad activa).
- **Calendario visual (Mapa de Calor)**:
  - Densidad de tareas pendientes por día con código de color:
    - 🟢 **Verde** (0 pendientes) → 🟡 **Amarillo** (1-2) → 🟠 **Naranja** (3-5) → 🔴 **Rojo** (6+)
  - Vistas: **Diario**, **Semanal**, **Mensual**, **Anual**.
  - Navega con flechas ◀ ▶ o haz clic en **Hoy**.
- **Tareas recientes**: Las últimas 10 tareas actualizadas.

---

## 4. Gestión de Tareas

### Crear Tarea
1. Haz clic en **Nueva Tarea** (disponible para Administradores y Managers).
2. Completa: nombre, descripción (editor enriquecido Quill.js), fechas, estado, prioridad.
3. Selecciona el **usuario asignado** y opcionalmente un **grupo**.
4. Haz clic en **Guardar**.

### Ver Detalle
- Abre cualquier tarea para ver: información completa, historial de avances (bitácora), archivos adjuntos.

### Editar Tarea
- Solo **Administradores** y **Managers** pueden editar tareas.
- Modifica campos, estado, prioridad, asignación y grupo.

### Registrar Avance (Bitácora)
1. Abre el detalle de una tarea.
2. En la sección **Agregar Avance**, escribe un comentario descriptivo.
3. Ajusta el **porcentaje de avance** (0-100%).
4. Opcionalmente cambia el **estado** de la tarea.
5. El comentario es obligatorio; el avance queda registrado de forma inmutable.

### Adjuntar Archivos
- En el detalle de la tarea, usa **Subir Archivo**.
- Formatos permitidos: PDF, PNG, JPG, GIF, DOC, DOCX, XLS, XLSX, CSV, TXT, ZIP, RAR.
- Tamaño máximo: **16 MB**.
- Descarga adjuntos desde el listado de archivos.

### Filtros y Búsqueda
- Filtra por: **Estado**, **Prioridad**, **Usuario asignado**, **Grupo**.
- Busca por nombre con el campo de búsqueda.
- Paginación automática (15 tareas por página).

---

## 5. Grupos

Los grupos organizan usuarios por área funcional (ej: Gerencia, Programación, Administración).

- **Crear grupo** (solo Administradores): Menú **Grupos** → **Nuevo Grupo**.
  - Asigna nombre, descripción, color identificativo y miembros.
- **Editar grupo**: Cambia miembros, color o nombre en cualquier momento.
- **Eliminar grupo**: Se elimina el grupo pero no los usuarios ni tareas.
- **Asignar tareas a grupo**: Al crear/editar una tarea, selecciona el grupo.
- Los **colores** de grupo se usan en el calendario y analítica para identificación visual.

---

## 6. Analítica

Accesible para Administradores, Managers y Visores.

### Gráficos de Pie
- **Por empresa**: Distribución global de tareas por estado.
- **Por grupo**: Estado de tareas por cada grupo.
- **Por usuario**: Ranking de usuarios ordenados por avance promedio.

### Análisis con IA
1. Haz clic en el botón **Análisis IA** en el dashboard de analítica.
2. La IA genera: **Resumen**, **Fortalezas**, **Áreas de mejora**, **Recomendaciones** y **Puntuación**.
3. Proveedores soportados: **OpenAI (GPT)**, **Google Gemini**, **Anthropic (Claude)**.
4. Requiere configurar la API Key en la **Configuración de Empresa** → pestaña **IA**.
5. **Sin IA configurada**: El sistema genera un análisis estadístico local automáticamente (fallback).

---

## 7. Reportes

### PDF Individual
- Desde el detalle de una tarea, genera un PDF profesional con logo, información completa, historial y adjuntos.

### PDF por Rango de Fechas
- En el módulo **Reportes**, selecciona fecha inicio y fin.
- Se genera un PDF con resumen y detalle de todas las tareas del período.

### Exportación CSV
- Exporta tareas filtradas a formato CSV con todos los campos.
- Ideal para análisis en Excel o Google Sheets.

### Compartir por Email
- Envía el PDF como adjunto a cualquier dirección de correo.
- Usa la configuración SMTP de la empresa.

### Compartir por WhatsApp
- Genera un enlace de WhatsApp con resumen de la tarea.
- Se abre WhatsApp Web/App para enviar directamente.

---

## 8. Gestión de Empresas (Superuser)

El **Superuser** es el administrador global del sistema SaaS:

- **Crear empresa**: Define nombre, datos generales, fiscales, SMTP e IA.
- **Editar empresa**: Actualiza cualquier dato incluyendo logo y constancia fiscal.
- **Activar/Desactivar**: Desactiva una empresa sin eliminar datos.
- **Cambiar empresa activa**: Desde el listado, haz clic en **Usar** para cambiar la empresa de trabajo.

---

## 9. Configuración de Empresa

Solo **Administradores** y **Superuser** acceden a la configuración:

### Tab General
- Nombre, representante legal, dirección, teléfono, email de contacto, sitio web, logo.

### Tab Fiscal
- RFC, razón social, régimen fiscal, constancia de situación fiscal (PDF adjunto).

### Tab Email (SMTP)
- Servidor, puerto, TLS/SSL, usuario, contraseña, remitente predeterminado.
- La contraseña se almacena **cifrada** en la base de datos.

### Tab IA
- Proveedor: OpenAI, Gemini o Anthropic.
- API Key (cifrada en BD), modelo específico.

---

## 10. Gestión de Usuarios

Solo **Administradores** de la empresa:

- **Crear usuario**: Nombre, email, contraseña, rol, grupos.
- **Editar usuario**: Modificar datos, rol, grupos, contraseña.
- **Activar/Desactivar**: Desactiva sin eliminar — el usuario no podrá iniciar sesión.
- No se puede asignar el rol **Superuser** desde esta interfaz.

---

## 11. Preguntas Frecuentes (FAQ)

| Pregunta | Respuesta |
|----------|-----------|
| ¿Puedo usar el sistema sin IA? | Sí. La analítica funciona con análisis estadístico local como fallback. |
| ¿Los datos de mi empresa son visibles para otras? | No. El aislamiento multi-tenant es estricto — cada empresa solo ve sus datos. |
| ¿Puedo adjuntar cualquier tipo de archivo? | Solo los formatos permitidos (PDF, imágenes, documentos Office, CSV, TXT, ZIP, RAR). |
| ¿Cómo cambio mi contraseña? | Un Administrador puede cambiarla desde Gestión de Usuarios → Editar. |
| ¿Qué pasa si el email no se envía? | Verifica la configuración SMTP en la pestaña Email de la empresa. |
| ¿Puedo exportar mis datos? | Sí, mediante CSV o reportes PDF desde el módulo de Reportes. |
| ¿Cómo genero una API Key para IA? | Visita el sitio del proveedor (OpenAI, Google AI Studio, Anthropic Console) y genera una clave. |
