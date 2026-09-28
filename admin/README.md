# Sistema de Alimentación — Etapa 1

Aplicación privada de administración (Flask + Jinja) y API JSON para las interfaces operativas.

## Instalación (Windows / PowerShell)

Desde la carpeta `code/admin`:

```powershell
py -m poetry add flask-sqlalchemy "psycopg[binary]" flask-session python-dotenv argon2-cffi
copy .env.example .env        # y completar la contraseña de PostgreSQL
py -m poetry run flask --app main reset-db
py -m poetry run flask --app main seed-db
py -m poetry run flask --app main run --debug
```

Abrir http://127.0.0.1:5000 e ingresar con `admin@hospital.local` / `Admin1234`.

> `reset-db` borra todas las tablas. Hay que correrlo cada vez que cambia el modelo.

## Usuarios de prueba

| Rol | Email | Contraseña | Dónde entra |
|---|---|---|---|
| Administrador | admin@hospital.local | Admin1234 | Aplicación de administración |
| Jefe de Servicio (Equipo De Guardia) | jefe.guardia@hospital.local | Jefe12345 | API |
| Servicio de Alimentación | alimentacion@hospital.local | Alim12345 | API |
| Sector Comedor | comedor@hospital.local | Comedor123 | API |

El seed también carga los 35 sectores del enunciado, 7 personas de prueba y cupos de 3 por comida para Equipo De Guardia.

## Estructura

```
src/core/            Modelo y lógica de negocio (no depende de Flask)
  models/            Tablas SQLAlchemy
  validators/        Validaciones del servidor: reciben datos y devuelven (datos, errores)
  *.py               Servicios: usuarios, sectores, personal, importacion, cupos,
                     pedidos, autorizaciones, entregas, resumenes, tokens, configuracion
src/web/             Capa web
  controllers/       Aplicación de administración (HTML)
  api/               API JSON (token Bearer)
  handlers/          Sesión, permisos y CSRF
  templates/         Vistas Jinja
static/              CSS y JS
docs/API.md          Referencia de la API y flujo de prueba
logs/app.log         Registro de eventos y errores (se crea solo)
```

## Decisiones de diseño

- **Pedido = sector + fecha.** Una carga semanal o mensual genera un pedido por día. Cada pedido tiene solicitudes nominadas (persona + comida) que guardan el menú y la condición regular/excepción al momento de la carga, más su autorización y su entrega. Así lo pedido, lo autorizado y lo entregado quedan separados y los cambios posteriores (ficha, cupo) no alteran el historial.
- **Cupo:** las primeras N personas de cada comida son regulares y el resto excepción. Sin cupo definido, todas son excepción.
- **Una persona no retira dos veces la misma comida del mismo día**, aunque un residente figure en pedidos de dos sectores.
- **Contraseñas** con Argon2 (`argon2-cffi`). **Tokens de API** aleatorios, guardados como hash SHA-256, con vencimiento de 8 horas y revocables.
- **Mantenimiento:** la API responde 503 con el mensaje configurado; la administración sigue disponible para poder desactivarlo.
- **Hora del hospital:** UTC-3 fijo (Argentina no tiene horario de verano).

## Pendiente para la Etapa 2

- CORS para la app Vue (`flask-cors`), porque va a correr en otro origen.
- CRUD de tipos de personal y de menú (opcional según el enunciado).
