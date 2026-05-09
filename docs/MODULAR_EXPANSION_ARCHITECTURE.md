# Arquitectura de Expansión Modular

## Objetivo
Evolucionar Bitácora desde gestión de tareas hacia una plataforma de work management multi-empresa con módulos configurables: Proyectos, Tareas, Marketing, Diseño, CRM, Software, TI, Operaciones y Producto.

## Modelo Propuesto
- `Workspace`: área de trabajo dentro de una empresa. Ejemplos: Dirección, Marketing, Soporte, Implementaciones.
- `Board`: módulo configurable dentro de un workspace. Ejemplos: Proyectos, Campañas, Tickets TI, Pipeline CRM.
- `BoardItem`: registro operativo común. Sustituye el patrón rígido de una sola entidad por items con estado, responsable, prioridad, fechas y actividad.
- `FieldDefinition`: definición de campos por board: texto, número, fecha, usuario, estado, selección, archivo, moneda, enlace.
- `FieldValue`: valor de cada campo por item.
- `BoardView`: vistas persistentes por board: tabla, kanban, calendario, galería y timeline.

## Migración Gradual
1. Mantener `Task` estable como módulo operativo actual.
2. Priorizar Marketing como primer módulo de expansión: campañas, canales, audiencia, mensajes, presupuesto y materiales enriquecidos.
3. Agregar `Project` como agrupador superior de tareas y campañas, con estado, cliente interno/externo, fechas, avance y responsable.
4. Introducir `Workspace` y `Board` sin migrar todavía todas las tareas.
5. Crear boards configurables para Operaciones reutilizando usuarios, grupos, adjuntos y bitácora de actividad.
6. Migrar Tareas a un board nativo cuando el motor configurable ya cubra permisos, filtros, reportes y analytics.

## Navegación Objetivo
- Inicio
- Proyectos
- Tareas
- Marketing
- CRM
- Operaciones
- Reportes
- Analytics
- Configuración

Cada módulo debe incluir dashboard, lista filtrable, detalle, adjuntos, actividad, permisos por rol y exportación.

## Criterios de Arquitectura
- Todo registro debe pertenecer a `empresa_id`.
- Los módulos configurables no deben duplicar lógica de adjuntos, usuarios, permisos ni bitácora.
- Las vistas deben ser configurables por empresa y por usuario.
- Los reportes y analytics deben poder consumir tanto `Task` como `BoardItem`.
- Las automatizaciones se agregan después del motor de campos para evitar reglas rígidas por módulo.

## Roadmap Comercial
- Fase 1: Marketing + mejoras de Tareas.
- Fase 2: Proyectos y Operaciones con boards configurables.
- Fase 3: CRM, TI y Producto.
- Fase 4: Plantillas por industria, automatizaciones, integraciones y dashboards cross-board.
