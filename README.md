# AppEnzo

Aplicación personal de organización diaria. Uso individual por ahora, pensada
para eventualmente soportar más de un usuario (cada uno con sus propios datos
aislados).

## Estado

En desarrollo — v1: **Tareas** y **Agenda**, más la portada "Hoy" que las une.
Login simple funcionando. Los módulos de Plata, Proyectos y Entretenimiento
quedan para versiones futuras (el módulo de tarjetas de crédito que existía
sobre Postgres se retiró del working tree; sigue disponible en el historial de
git si se retoma como base de Plata).

## Stack

- **Backend**: Python (Flask), corriendo en entorno virtual (`venv`) en local.
- **Base de datos**: SQLite (`sqlite3` de la stdlib, sin ORM). Acceso vía SQL
  crudo con placeholders `?` — la capa `models.py` de cada módulo son
  funciones con queries parametrizadas, no clases mágicas.
- **Frontend**: HTML server-rendered. Sin framework de JS.
- **Deploy futuro**: Render. Este es justamente el proyecto elegido para
  aprender ese flujo — chico, propio, sin miedo a romper algo real.

## Principios de arquitectura

- **Separación de capas**: la UI (routes/templates) no contiene lógica de
  negocio ni acceso directo a la base de datos. La lógica vive en una capa de
  servicios/dominio, separada del acceso a datos (repositorios/modelos) y
  separada de la UI.
- **Nombres en inglés** en todo el código, archivos y base de datos (tablas,
  columnas, variables, funciones). El contenido/textos de cara al usuario
  puede estar en español.
- **Passwords hasheados** (bcrypt), nunca en texto plano.
- **IDs**: strings alfanuméricos aleatorios (mayúsculas + números) de 12
  caracteres, sin orden ni información codificada.
- **Multi-usuario desde el modelo de datos**: toda tabla de datos de usuario
  lleva `user_id`, aunque hoy exista un solo usuario y no haya registro
  público.
- **Borrado lógico (soft delete) en todas las tablas**: nunca se hace
  `DELETE` físico de datos de usuario. Cada tabla lleva `deleted_at`
  (nullable); "borrar" es setear ese timestamp, y todas las consultas filtran
  `deleted_at IS NULL` por defecto.
- **Fechas en la base**: se guardan como `TEXT` en formato ISO
  (`YYYY-MM-DD`), convertidas a/desde `date` de Python explícitamente en cada
  `models.py`. En la UI se muestran/cargan como `dd-mm-aaaa`
  (`app/common/dates.py`, con máscara de input en
  `app/static/js/date-mask.js`).

## La portada "Hoy"

`/` responde una sola pregunta: **qué tengo que hacer hoy y qué me vence**.
Es de solo lectura y no tiene que scrollear en tablet — cuatro secciones fijas
(Horario de hoy, Tareas de hoy, Vence esta semana, Postergado), con hasta 5
ítems cada una y un link a la pantalla completa si hay más.

El dato que une todo es la fecha: cada módulo de dominio expone
`services.get_today_summary(user_id, today)`, que devuelve una lista de
`TodayItem` (`app/common/today.py`) — una estructura normalizada (fecha,
título, tipo, si está vencido) sin importar de qué módulo viene. `main`
agrega lo que cada módulo existente reporta; así "tarea, vencimiento, turno y
pago son la misma cosa con distinto color" sin mezclar las tablas de cada
dominio entre sí. Cuando se sume Plata o Proyectos, alcanza con que expongan
la misma función para aparecer en la portada.

## Estructura de carpetas

```
app/
  auth/                  # login, sesiones, hashing
  main/                  # portada "Hoy" (agrega tasks + agenda)
  tasks/                 # módulo Tareas
    models.py            # acceso a datos
    services.py          # lógica de negocio (contextos, estados, resumen)
    routes.py             # endpoints / vistas
    templates/
  agenda/                # módulo Agenda
    models.py
    services.py
    routes.py
    templates/
  db/
    connection.py        # conexión a SQLite
    schema.sql            # DDL de toda la base
    cli.py                 # comando `flask init-db`
  common/
    ids.py                # generador de IDs alfanuméricos de 12 caracteres
    dates.py               # parseo/formato de fechas dd-mm-aaaa y en español
    today.py                # TodayItem + badge_class, contrato de la portada
  config.py
  __init__.py               # app factory (create_app)
requirements.txt
.env.example
```

## Desarrollo local

```bash
cp .env.example .env          # completar si hace falta
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

flask init-db                 # crea instance/appenzo.db con el schema
flask create-user             # alta de usuario (email + password por prompt)
flask run
```

## Autenticación

Login simple (usuario + contraseña hasheada + sesión). Sin registro público
por ahora; el diseño de datos ya contempla múltiples usuarios para poder
sumar personas más adelante sin rehacer el esquema.

---

## Módulo Tareas

Cada tarea pertenece a un `context` fijo (`home`/`work`/`shopping`/`projects`
→ Casa/Trabajo/Compras/Proyectos) y a un `status` que resuelve estado y
avance a la vez (`pending` → `in_progress`/`blocked` → `done`). `due_date` es
opcional — hay tareas sin fecha. El alta rápida vive como un form siempre
visible arriba del listado de `/tasks`, sin navegar a otra pantalla.

## Módulo Agenda

Eventos puntuales cargados a mano: turnos, francos, pagos, turnos médicos y
trámites (`kind`: `shift`/`day_off`/`payment`/`medical`/`other`), con fecha,
hora opcional y notas. **Los turnos rotativos no tienen lógica de
recurrencia** — se cargan día por día como cualquier otro evento, decisión
tomada a propósito para mantener v1 simple. La vista es un listado
cronológico de dos semanas con navegación "semana anterior / siguiente"; no
hay calendario visual.

## Deploy a Render

El repo ya está preparado (`render.yaml`, `gunicorn` en `requirements.txt`,
`.python-version`). Falta solo crear la cuenta en render.com (podés usar tu
GitHub) — el registro en sí no pide tarjeta.

**Importante — disco persistente**: la base es un archivo SQLite. El plan
free de Render tiene filesystem efímero (se borra en cada deploy/reinicio),
así que en ese plan los datos no persisten de verdad — sirve para practicar
el flujo, no para uso real. Para que persista hace falta un "Persistent
Disk", que requiere un plan pago (arranca ~USD 7/mes) — ahí Render sí pide
tarjeta. El bloque `disk` en `render.yaml` está comentado; se activa cuando
llegue ese momento (y hay que cambiar `DATABASE_PATH` al `mountPath` del
disco).

**Pasos** (Blueprint, recomendado):
1. render.com → New → Blueprint → elegís este repo → Apply. Lee
   `render.yaml` solo y crea el servicio.
2. Antes del primer deploy (o después, en Environment): agregar
   `ADMIN_EMAIL` y `ADMIN_PASSWORD` a mano en el dashboard. **Render free no
   tiene shell interactivo**, así que `flask create-user` (que pide la
   contraseña por prompt) no se puede correr ahí — con estas dos variables,
   el usuario se crea solo la primera vez que arranca el servicio
   (`app/db/cli.py`, `_ensure_admin_from_env`). No se versionan en el repo.
3. Deploy. La primera vez corre `flask init-db` (crea el schema) y después
   `gunicorn`.

Alternativa manual (sin `render.yaml`): New → Web Service → build command
`pip install -r requirements.txt`, start command
`flask init-db && gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT`, y
cargar `SECRET_KEY`/`DATABASE_PATH`/`ADMIN_EMAIL`/`ADMIN_PASSWORD` a mano en
Environment.

## Fuera de alcance de v1 (roadmap)

- **Plata**: tarjetas (cierre, apertura, gastos), gastos no vencidos,
  postergados, presupuesto — reemplazo del Excel actual.
- **Proyectos**: panacar, MyTools, etc., con avance y próximo paso.
- **Entretenimiento**: pelis y series pendientes.
