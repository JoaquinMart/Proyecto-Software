# API — Sistema de Alimentación HIAEP "Sor María Ludovica"

Base: `http://127.0.0.1:5000/api`. Todas las requests y respuestas son JSON.

## Autenticación

1. `POST /api/auth/login` con `{"email": "...", "password": "..."}` devuelve un `token`.
2. En cada request siguiente se envía el header `Authorization: Bearer <token>`.
3. El token vence a las 8 horas. `POST /api/auth/logout` lo invalida.

Sin token, o con un token inválido o vencido, cualquier endpoint (salvo el login) responde **401** antes de evaluar otra regla. Con token válido pero sin el permiso necesario responde **403**.

## Errores

Siempre con este formato:

```json
{"error": {"codigo": 400, "mensaje": "Revisá los datos ingresados.", "detalles": {"dni": "El DNI debe tener 7 u 8 números, sin puntos."}}}
```

| Código | Cuándo |
|---|---|
| 400 | Datos inválidos o faltantes |
| 401 | Falta el token, es inválido o venció |
| 403 | El rol no tiene permiso, o el recurso es de otro sector |
| 404 | El recurso no existe |
| 409 | Conflicto: DNI duplicado, pedido ya autorizado, comida ya entregada, etc. |
| 503 | Sitio en mantenimiento (el mensaje es el configurado en Ajustes) |

## Paginación

Los listados aceptan `?page=N` y responden:

```json
{"items": [...], "pagina": 1, "por_pagina": 25, "total": 60, "paginas": 3}
```

`por_pagina` es el valor configurado en Ajustes del sistema (máximo 25).

## Usuarios de prueba (seed)

| Rol | Email | Contraseña |
|---|---|---|
| Jefe de Servicio (Equipo De Guardia) | jefe.guardia@hospital.local | Jefe12345 |
| Servicio de Alimentación | alimentacion@hospital.local | Alim12345 |
| Sector Comedor | comedor@hospital.local | Comedor123 |

El Administrador no tiene acceso a la API: usa la aplicación de administración.

---

## Autenticación

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| POST | `/auth/login` | Los tres operativos | `{email, password}` → `{token, token_type, expires_at, usuario}` |
| POST | `/auth/logout` | Autenticado | Revoca el token |
| GET | `/auth/me` | Autenticado | id, nombre, apellido, email, rol y sector |

## Catálogos y configuración

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| GET | `/menu-types` | Autenticado | Tipos de menú |
| GET | `/personnel-types` | Autenticado | Tipos de personal |
| GET | `/configuration` | Autenticado | `{por_pagina, mantenimiento, mensaje_mantenimiento}`. Responde aunque el sitio esté en mantenimiento |

## Sectores

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| GET | `/sectors?estado=activo\|todos` | Alimentación, Comedor | Activos por defecto. Jefe → 403 |
| GET | `/sectors/{id}` | Alimentación, Comedor | Incluye inactivos |
| GET | `/sectors/{id}/personnel` | Jefe (solo el suyo), Alimentación, Comedor | Personal activo del sector |

## Personal

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| GET | `/personnel` | Jefe, Alimentación, Comedor | Filtros: `dni`, `nombre`, `sector_id`, `tipo_personal_id`, `estado` (`activo` por defecto, `inactivo`, `todos`), `orden` (`apellido`, `dni`, `creacion`), `dir` |
| GET | `/personnel/{id}` | Jefe, Alimentación, Comedor | |
| POST | `/personnel` | Jefe, Alimentación | Crea (queda activa) |
| PUT | `/personnel/{id}` | Jefe, Alimentación | Los campos no enviados conservan su valor |
| DELETE | `/personnel/{id}` | Jefe, Alimentación | Elimina, o desactiva si tiene historial |

Cuerpo de alta o modificación:

```json
{"dni": "30111222", "nombre": "Ana", "apellido": "Pérez", "tipo_personal_id": 1, "tipo_menu_id": 1, "sector_id": 4}
```

Reglas del Jefe de Servicio (las fuerza el backend): ve su sector y los residentes; solo crea, modifica y elimina Personal Fijo de su sector (el `sector_id` enviado se ignora y se usa el suyo); no gestiona residentes (403). DNI duplicado → 409.

## Pedidos (Jefe de Servicio)

El sector siempre sale del usuario autenticado.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/requests` | Filtros: `fecha_desde`, `fecha_hasta`, `comida`, `tipo_menu_id`, `estado` |
| POST | `/requests` | Crea un pedido por cada fecha del rango |
| GET | `/requests/{id}` | Detalle con solicitudes nominadas |
| PUT | `/requests/{id}` | Reemplaza las personas (solo si está `confirmado`; si no, 409) |
| DELETE | `/requests/{id}` | Elimina (solo si está `confirmado`). 204 |

Cuerpo de alta:

```json
{
  "periodicidad": "semanal",
  "fecha_desde": "2026-10-05",
  "comidas": {
    "almuerzo": [1, 2, 3, 4, 6],
    "cena": [1, 2]
  }
}
```

- `periodicidad`: `diaria` (un día), `semanal` (7 días) o `mensual` (hasta fin de mes). Se puede enviar `fecha_hasta` para un rango propio (máximo 31 días).
- Por cada fecha y comida, las primeras N personas (N = cupo del sector) quedan **regulares** y el resto **excepción**. Sin cupo definido, todas son excepción.
- El tipo de menú de cada persona se copia a la solicitud al cargarla.
- Personal Fijo de otro sector, personas inactivas o inexistentes → 400. Si ya hay un pedido del sector para alguna de las fechas → 409.

Para el `PUT` se envía solo `{"comidas": {...}}`; la condición regular/excepción se recalcula con el cupo actual.

## Autorizaciones (Servicio de Alimentación)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/authorizations` | Pedidos de todos los sectores. Filtros: `fecha_desde`, `fecha_hasta`, `sector_id`, `comida`, `tipo_menu_id`, `estado` (`confirmado` = pendiente) |
| GET | `/authorizations/{id}` | Detalle con pedidas y autorizadas por separado |
| PUT | `/authorizations/{id}` | Autorización nominada |
| POST | `/authorizations/{id}/reject` | Rechaza el pedido completo. Cuerpo opcional `{"motivo": "..."}` |

Autorización individual (las solicitudes no mencionadas quedan no autorizadas):

```json
{"solicitudes": [{"id": 11, "autorizada": true}, {"id": 12, "autorizada": false}]}
```

Autorización masiva: `{"autorizar_todas": true}`. Pedido ya revisado → 409. Solicitud de otro pedido → 400.

## Cupos

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| GET | `/quotas` | Alimentación, Comedor, Jefe (solo el suyo) | Filtros: `sector_id`, `comida` |
| POST | `/quotas` | Alimentación | `{"sector_id": 4, "comida": "almuerzo", "cantidad": 10}` |
| GET | `/quotas/{id}` | Alimentación, Comedor, Jefe (solo el suyo) | |
| PUT | `/quotas/{id}` | Alimentación | Solo afecta pedidos futuros |
| DELETE | `/quotas/{id}` | Alimentación | 204 |

Sector inactivo → 400. Ya existe un cupo para ese sector y comida → 409.

## Comidas autorizadas y entregas

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| GET | `/authorized-meals` | Comedor, Alimentación | Filtros: `fecha` (hoy por defecto), `dni`, `nombre`, `sector_id`, `comida`. Exige al menos uno (si no, 400). Incluye `resumen` de autorizadas y entregadas |
| GET | `/authorized-meals/{persona_id}?fecha=` | Comedor, Alimentación | Comidas autorizadas de la persona e indicación de si ya se entregaron |
| GET | `/deliveries` | Comedor, Alimentación | Filtros: `fecha` (hoy), `sector_id`, `comida` |
| GET | `/deliveries/summary` | Comedor, Alimentación | Autorizadas vs. entregadas del día por comida y menú |
| POST | `/deliveries` | Comedor | Registra un retiro |
| GET | `/deliveries/{id}` | Comedor, Alimentación | Detalle |

Registro de entrega (varias personas y/o comidas en una operación):

```json
{
  "items": [
    {"persona_id": 1, "comida": "almuerzo"},
    {"persona_id": 2, "comida": "almuerzo"}
  ],
  "responsable": {"persona_id": 1}
}
```

También se acepta `{"comida": "almuerzo", "personas": [1, 2], "responsable": {...}}`. Si quien retira no está registrado: `"responsable": {"dni": "25111222", "nombre": "Nombre Apellido"}`.

Fecha, hora y usuario los completa el servidor. Sin autorización vigente para hoy → 400. Comida ya entregada → 409.

## Resúmenes

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| GET | `/summaries/requests` | Alimentación, Jefe (su sector) | Pedidas, regulares y excepciones |
| GET | `/summaries/authorizations` | Alimentación | Pedidas vs. autorizadas y diferencia |
| GET | `/summaries/deliveries` | Alimentación | Autorizadas vs. entregadas y diferencia |

Filtros comunes: `fecha_desde`, `fecha_hasta`, `sector_id`, `comida`, `tipo_menu_id` y `agrupar` (`dia`, `semana`, `mes`, `sector`, `comida`, `menu`).

---

## Flujo completo de prueba

Con cualquier cliente HTTP (Thunder Client, Postman, Bruno o `curl`):

1. **Jefe:** login → `GET /personnel` → `POST /requests` con 4 personas en almuerzo. El cupo de prueba es 3, así que la cuarta queda como excepción.
2. **Alimentación:** login → `GET /authorizations?estado=confirmado` → `PUT /authorizations/{id}` autorizando algunas solicitudes.
3. **Comedor:** login → `GET /authorized-meals?dni=30111222` → `POST /deliveries` → repetir el `POST` y verificar el 409.

El pedido tiene que ser para **hoy** para que el comedor pueda entregarlo.
