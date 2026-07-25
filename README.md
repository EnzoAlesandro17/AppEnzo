# AppEnzo

Aplicación personal de finanzas. Uso individual por ahora, pensada para eventualmente
soportar más de un usuario (cada uno con sus propios datos aislados).

## Estado

En desarrollo. **Auth** (login simple) y **módulo de tarjetas de crédito** funcionando
en local: alta de tarjetas, resúmenes por período (mes calendario, editable en cierre/
vencimiento), carga de gastos/pagos/cuotas con resolución automática por fecha, borrado
lógico de movimientos y resúmenes, página de inicio por tarjeta (balance del mes +
resumen actual + movimientos + alta rápida), historial de movimientos paginado, y
listado de resúmenes con alta de resúmenes nuevos (año/mes) o históricos.

Pendiente (ver roadmap del módulo de tarjetas más abajo): calculadora de intereses,
lista de gastos recurrentes/facturas, inflación y dólar manual.

Para levantar el entorno de nuevo: ver "Desarrollo local" más abajo (`docker compose
up -d` + `flask run`). El usuario de prueba es `admin` / `admin` (cambiar antes de
manejar datos reales).

## Stack

- **Backend**: Python (Flask), corriendo en entorno virtual (`venv`) en local.
- **Base de datos**: PostgreSQL desde el arranque (evita migración futura al deployar).
  Acceso vía **SQL crudo con `psycopg`**, sin ORM — la capa `models.py` de cada
  módulo son funciones con queries parametrizadas, no clases mágicas.
- **Frontend**: HTML server-rendered por ahora. Sin framework de JS todavía.
- **Deploy futuro**: Render.

## Principios de arquitectura

- **Separación de capas**: la UI (routes/templates) no contiene lógica de negocio ni
  acceso directo a la base de datos. La lógica vive en una capa de servicios/dominio,
  separada del acceso a datos (repositorios/modelos) y separada de la UI.
- **Nombres en inglés** en todo el código, archivos y base de datos (tablas, columnas,
  variables, funciones). El contenido/textos de cara al usuario puede estar en español.
- **Passwords hasheados** (bcrypt/argon2), nunca en texto plano.
- **IDs**: strings alfanuméricos aleatorios (mayúsculas + números, alfabeto de 36
  caracteres), sin orden ni información codificada (no timestamps, no
  secuenciales). **Largo: 12 caracteres** (ej. `A3F9K2Q7XZ4P`). Pensado para
  escalar cómodo hasta millones de registros: con 12 caracteres, la probabilidad
  de colisión con 1 millón de IDs generados es del orden de 1 en 10 millones
  (~1e-7) — prácticamente nula, sin sacrificar tiempo de generación. Igual se
  refuerza con constraint `UNIQUE` en la base de datos.
- **Multi-usuario desde el modelo de datos**: toda tabla de datos de usuario lleva
  `user_id`, aunque hoy exista un solo usuario y no haya registro público.
- **Borrado lógico (soft delete) en todas las tablas**: nunca se hace `DELETE`
  físico de datos de usuario. Cada tabla lleva `deleted_at` (nullable); "borrar"
  es setear ese timestamp, y todas las consultas filtran `deleted_at IS NULL` por
  defecto. Permite deshacer errores y mantener el historial para reportes.

## Estructura de carpetas

```
app/
  auth/               # login, sesiones, hashing (a implementar)
  main/               # página principal / dashboard (a implementar)
  cards/              # módulo de tarjetas de crédito (a implementar)
    models.py         # acceso a datos
    services.py       # lógica de negocio
    routes.py         # endpoints / vistas
    templates/
  db/
    connection.py      # conexión a Postgres (psycopg)
    schema.sql          # DDL de toda la base
  common/
    ids.py              # generador de IDs alfanuméricos de 12 caracteres
  config.py
  __init__.py            # app factory (create_app)
requirements.txt
.env.example
```

Cada módulo futuro (gastos recurrentes, calculadora de inflación/dólar, etc.) sigue
el mismo patrón: `models` / `services` / `routes` separados. `auth`, `main` y
`cards` hoy son paquetes vacíos, listos para sumarles esos tres archivos cuando
se implemente cada uno.

## Desarrollo local

Postgres corre en Docker (contenedor `appenzo-db`, ver `docker-compose.yml`),
con las mismas credenciales que `.env.example`.

```bash
cp .env.example .env          # completar si hace falta
docker compose up -d          # levanta Postgres en localhost:5432

# cargar/actualizar el schema
docker exec -i appenzo-db psql -U user -d appenzo < app/db/schema.sql

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Autenticación

Login simple (usuario + contraseña hasheada + sesión). Sin registro público por ahora;
el diseño de datos ya contempla múltiples usuarios para poder sumar personas más
adelante sin rehacer el esquema.

---

## Módulo 1: Tarjetas de crédito

### Conceptos

- **Card (tarjeta)**: pertenece a un usuario. Un usuario puede tener varias
  tarjetas (arrancamos con 3).
- **Currency (moneda)**: `ARS` o `USD` por ahora. **Una misma tarjeta puede tener
  actividad en ambas monedas a la vez** (ej. un resumen con $100.000 ARS + 10 USD).
  Por eso la moneda no es un atributo fijo de la tarjeta, sino de cada `entry`. El
  balance de un resumen se calcula por separado por moneda (total ARS, total USD).
  Lo habitual es pagar cada moneda con la misma moneda, pero excepcionalmente se
  puede pagar todo en pesos al cambio del día — para ese caso el pago guarda el
  `exchange_rate` usado, a modo de registro.
- **Statement (resumen)**: se identifica por `period` (el 1er día del mes que lo
  nombra, ej. `2026-07-01` = "resumen 2026-07") — eso da a la vez el orden y el
  nombre, sin un ID secuencial ni un label libre. Tiene fecha de cierre y fecha
  de vencimiento (pago), editables a mano cuando el banco las confirma (nunca son
  fijas: las corre mes a mes, a veces se equivoca). La fecha de inicio **no se
  guarda**: se calcula siempre como "cierre del resumen del período anterior + 1
  día". El estado (Cerrado / Abierto / Futuro) tampoco se guarda: se deriva
  comparando `period` contra el mes calendario real de hoy.
- **Entry (gasto o pago)**: registro individual dentro de un resumen. Campos: `id`,
  `date`, `card_id`, `currency`, `amount`, `description`, tipo (gasto/pago/cargo),
  `statement_id`.
- **Cargos fijos por resumen** (ej. impuesto al sello): no siguen la lógica de
  asignación por fecha — se cargan directamente a un `statement_id` puntual,
  sin importar qué fecha tengan (la fecha, si se carga, es solo informativa).
- **Balance**: la tarjeta funciona en parte como una cuenta — permite pagos
  parciales del saldo, no solo el pago total del resumen.

### Reglas de asignación a resumen

- **Gasto simple** (sin cuotas), **pago**, o la **1ra cuota** de una compra en
  cuotas: se resuelven **por fecha**. Si algún resumen ya tiene `closing_date`
  confirmado y la fecha cae dentro de su rango (contiguo al del resumen
  anterior, sin saltos), se usa ese. Si ningún cierre confirmado la delimita
  (típicamente el mes en curso, que todavía no cerró), cae en el resumen de su
  mes calendario — creándolo si no existía.
- **Cuotas 2ª en adelante**: **no se recalculan por fecha**, nunca. Cada una es
  simplemente "el próximo período" a partir de donde cayó la 1ra cuota — la
  fecha que llevan es solo informativa/formalidad. Aunque después se edite el
  cierre de un resumen intermedio, la cuota no salta ni se duplica.
- Los resúmenes futuros que hacen falta para las cuotas (2ª, 3ª...) se crean
  automáticamente en el momento de cargar la compra, aunque todavía no tengan
  fecha de cierre — por eso pueden existir resúmenes "Futuro" vacíos, a la
  espera de que llegue esa cuota.

### Fuera de alcance de esta primera etapa (roadmap)

- Calculadora/estimador de intereses por pago fuera de fecha de vencimiento.
- Lista centralizada de gastos/facturas con:
  - fecha(s) de vencimiento (pueden ser más de una) y recargos por mora,
  - facturas sin recargo,
  - deudas informales con interés propio,
  - gastos recurrentes: tomar el último valor como base y, con el tiempo, mejorar
    la estimación con un promedio ponderado (dar más peso a ciertos factores).
- Carga manual de inflación anual y cotización del dólar (reemplazable por una API
  en el futuro).

## Preguntas abiertas

- Definir cómo se corrige/edita una cuota ya generada si cambia el monto total
  redondeado por el banco.
- Definir si el pago cross-currency (pagar deuda en USD con ARS al cambio del día)
  se registra como un solo `entry` de pago o como dos movimientos vinculados
  (uno que salda el ARS, otro que salda el USD).
