# Deploy a producción — checklist

> Esta guía la ejecutás **vos**. Claude no puede crear cuentas/recursos en
> Fly.io, Neon o Cloudflare (política de seguridad), pero dejó todo el código
> y config listos localmente.

Dominio elegido: **meltonagents.com** (las apps iOS/watch ya apuntan a
`https://api.meltonagents.com` por default). `yani.ar` queda libre para una
landing/short-link, no como dominio del producto.

## Arquitectura (~US$2/mes)

| Componente | Servicio | Plan |
|---|---|---|
| Backend (FastAPI) | [Fly.io](https://fly.io) | shared-cpu-1x / 256MB, siempre despierto (~US$2/mes) |
| Base de datos | [Neon](https://neon.tech) | Free (10GB, always-on, no duerme) |
| Uploads de imágenes | [Cloudflare R2](https://dash.cloudflare.com) | Free (10GB) |
| Frontend (Next.js) | Cloudflare Workers (vía OpenNext) | Free (100k requests/día) |

> Por qué Fly.io y no Render free: Render da 750h/mes gratis **compartidas
> entre todos los servicios free del workspace**. Si además tenés otro proyecto
> (ej. Connie) corriendo 24/7 en la misma cuenta, entre los dos superan las
> 750h y Render suspende todo. Fly.io cobra por uso real (~US$2/mes por un
> servicio chico siempre-on) y no comparte pool con otros proyectos.

## 0. Estado / qué ya quedó listo

- `backend/fly.toml`: config de Fly.io (región `sea`/Seattle, cerca de Neon en
  Oregon; `min_machines_running = 1` y `auto_stop_machines = "off"` para que
  no duerma). Reutiliza `backend/Dockerfile` tal cual (corre `alembic upgrade
  head` y arranca uvicorn en `$PORT`, sin cambios).
- `backend/app/storage.py`: sube imágenes a R2 vía boto3 (S3-compatible).
- `frontend/`: Next.js 15.5.20 + `@opennextjs/cloudflare` + `wrangler.jsonc` +
  `open-next.config.ts` — build validado localmente con `npm run cf:deploy`
  (requiere Node ≥22 para el CLI de wrangler).
- **Fix aplicado y probado con una connection string real de Neon**:
  `config.py` normaliza la URL de Postgres (`postgresql://` →
  `postgresql+asyncpg://` para el motor async) y **además saca `sslmode` /
  `channel_binding`** del query string solo para el lado async — `asyncpg`
  no entiende esos parámetros (son de `libpq`/psycopg2) y sin este fix el
  backend no arranca contra Neon. El lado sync (Alembic, psycopg2) los
  mantiene sin problema.

## 1. Pre-deploy (verificar local)

- [ ] No hay credenciales commiteadas: `git grep -nE "sk-|AKIA|xox|BEGIN PRIVATE" -- . ':!*.md'` (debe dar vacío).
- [ ] `.env` está gitignoreado (NO se commitea).
- [ ] Commits al día.

## 2. Base de datos — Neon ✅ hecho

Proyecto `melton` creado bajo la cuenta `admin@ixi.ar` (org Neon `ixi`),
región `aws-us-west-2` (Oregon), Postgres 18. Project id: `wispy-forest-81462706`.
La connection string (con host `-pooler`) ya está cargada como secret en Fly
(paso 4). Si necesitás rehacer esto: `neonctl` está instalado localmente y
`NEON_API_KEY` vive en el perfil **Personal** de Flock
(`~/Library/Application Support/Flock/environments.json`).

## 3. Uploads — Cloudflare R2 ✅ hecho

Bucket `melton-uploads` creado en la cuenta `admin@ixi.ar` (account id
`2ba1312f6d5066c0efa84bc819733e79`), acceso público habilitado vía el dominio
gestionado `pub-9c9c5f95c88547d085b8ba4dd5e2c653.r2.dev`. Token S3 con permiso
"Object Read & Write" scopeado solo a ese bucket. Secrets ya cargados en Fly
(`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_PUBLIC_URL`).
Probado end-to-end con `boto3` directo: `put_object` + fetch público → OK.

> El token general de Cloudflare (`CLOUDFLARE_API_TOKEN`, perfil Personal de
> Flock) originalmente solo tenía permisos de DNS — hubo que agregarle
> "Workers R2 Storage: Edit" para poder crear el bucket vía API. El token S3
> (Access Key ID/Secret) es uno aparte, específico de R2, generado desde
> R2 → Manage API Tokens en el dashboard (no se puede crear vía la API general
> sin un permiso de "editar tokens" que no le dimos a propósito).

> ⚠️ `pub-*.r2.dev` es para desarrollo — Cloudflare lo rate-limita. Para
> producción con más tráfico, conviene un dominio custom sobre el bucket
> (requiere tener `meltonagents.com` en esta misma cuenta Cloudflare — ver nota
> de dominio en la sección 6).

## 4. Backend — Fly.io ✅ desplegado

App `melton-backend` corriendo en `sjc` (San Jose — la región válida más
cercana a Oregon; Fly no tiene datacenter en Seattle) bajo la org `ixi ar`
(slug `personal`) de la cuenta `admin@ixi.ar`.

- Login: `fly auth login` (una vez; queda guardado en disco, no hace falta
  repetirlo por sesión).
- App creada con `fly launch --copy-config --name melton-backend --org personal
  --region sjc --no-deploy --yes` (reusa `backend/fly.toml` tal cual).
- Secrets cargados: `DATABASE_URL`, `DATABASE_URL_SYNC`, `SECRET_KEY`,
  `ENCRYPTION_KEY`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
  `R2_PUBLIC_URL` — todos deployados.
- **Deploy real hecho y verificado**: `fly deploy --app melton-backend` corrió
  las migraciones de Alembic y levantó uvicorn. `https://melton-backend.fly.dev/health`
  responde `{"status":"healthy","database":"connected"}`.
- ⚠️ **Gotcha real**: el primer `fly deploy` crea automáticamente **2 máquinas**
  ("high availability"), aunque `fly.toml` tenga `min_machines_running = 1` —
  eso duplica el costo a ~US$4/mes. Lo bajé a una sola con
  `fly scale count 1 --app melton-backend --yes`. Si volvés a desplegar desde
  cero (o borrás el app y lo recreás), repetí ese `scale count 1`.
- Dominio propio: `fly certs add api.meltonagents.com --app melton-backend` y
  cargá el CNAME/A que te indique en tu DNS (todavía no hecho — hoy el backend
  vive en `melton-backend.fly.dev`).

> ⚠️ **CRÍTICO — `ENCRYPTION_KEY`**: con esta key se encriptan las credenciales
> de las integraciones (ej. TelePagos) en la DB. **Nunca la cambies/rotes
> después de guardar credenciales** o quedan indescifrables.

## 5. Env vars opcionales (secrets, mismo mecanismo que el paso 4.4)

- [ ] `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` — opcionales,
      solo fallback (cada usuario carga su propia key en Settings).
- [ ] `MERCADOLIBRE_CLIENT_ID` / `MERCADOLIBRE_CLIENT_SECRET` — solo si usás la integración ML.
- [ ] `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — opcional (observabilidad).

## 6. Frontend — Cloudflare Workers ✅ desplegado

- Worker `melton-frontend` desplegado en la cuenta `admin@ixi.ar`, subdominio
  `workers.dev` registrado como `melton-ixi` (no existía, lo creé vía API:
  `PUT /accounts/{id}/workers/subdomain`).
- **URL viva**: https://melton-frontend.melton-ixi.workers.dev
- Buildeado con `NEXT_PUBLIC_API_URL=https://melton-backend.fly.dev` (el
  dominio propio `api.meltonagents.com` todavía no existe — ver nota de
  dominio abajo). Si cambia la URL del backend, hay que rebuildear y
  redeployar el frontend (queda horneada en el bundle JS, no es runtime).
- Deploy: `cd frontend && export NEXT_PUBLIC_API_URL=... && npx wrangler deploy`
  (requiere Node ≥22 — `nvm use 22` — y `CLOUDFLARE_API_TOKEN` con permisos de
  DNS + R2 + **Workers Scripts: Edit** en el perfil Personal de Flock).
- Probado end-to-end: la home carga (200), el bundle JS tiene la URL del
  backend horneada, `/en` redirige a `/` (comportamiento esperado de
  next-intl con `localePrefix: 'as-needed'`).

## 7. ⚠️ Dominio propio — pendiente, no automatizable con lo que tengo

`meltonagents.com` usa nameservers de Cloudflare (`duke`/`melody.ns.cloudflare.com`,
confirmado por WHOIS/DNS), pero **no está en la cuenta `admin@ixi.ar`** — esa
cuenta solo tiene `connie.ar` e `ixi.ar` (nameservers `elly`/`steven`, distintos).
Debe vivir en otra cuenta de Cloudflare tuya. Hasta que no me digas cuál y me
des un token de esa cuenta (o migres el dominio a `admin@ixi.ar`), el stack
sigue funcionando con las URLs por defecto:
- Backend: `https://melton-backend.fly.dev`
- Frontend: `https://melton-frontend.melton-ixi.workers.dev`

Cuando se resuelva: `fly certs add api.meltonagents.com --app melton-backend`
+ CNAME en esa cuenta Cloudflare; Workers → `melton-frontend` → Custom Domains
→ agregar `meltonagents.com`/`www`. Después rebuildear el frontend con
`NEXT_PUBLIC_API_URL=https://api.meltonagents.com` y actualizar `CORS_ORIGINS`/
`FRONTEND_URL`/`BACKEND_URL` en `backend/fly.toml` + `fly deploy`.

## 8. Post-deploy (verificado)

- [x] `https://melton-backend.fly.dev/health` → `{"status":"healthy","database":"connected"}`.
- [x] `https://melton-frontend.melton-ixi.workers.dev` carga el panel.
- [x] Upload a R2 probado directo con boto3 (put_object + fetch público) → OK.
- [ ] La DB de Neon arranca **vacía** (las migraciones crearon el schema, pero no
      hay agentes/usuarios todavía); creá tu usuario y agentes en esta prod nueva.
- [ ] **Apps**: iOS y watch default-ean a `https://api.meltonagents.com`, que
      todavía no existe (sección 7) — para probar contra esta prod hoy, hay que
      apuntarlas manualmente a `https://melton-backend.fly.dev` hasta que el
      dominio esté listo.

## 9. Notas

- **Costo real: ~US$2/mes** (Fly.io shared-cpu-1x/256MB, 1 sola máquina
  siempre-on). Neon, R2 y Cloudflare Workers en $0 mientras no superes sus
  free tiers (Workers: 100k requests/día; R2: 10GB / clase A-B ops — son los
  primeros límites a vigilar si crece el tráfico).
- Todas las credenciales usadas (Neon, Cloudflare, Fly vía `fly auth login`)
  viven bajo la cuenta `admin@ixi.ar` — ver [[melton-infra-account]] en memoria.
- Fly.io región `sea` (Seattle) — la más cercana a Neon en Oregon (us-west-2)
  para minimizar latencia backend↔DB.
- TelePagos en prod = **plata real** (igual que en dev): el gate de confirmación y el
  tope de $50.000 siguen activos.
- `yani.ar`: si querés, apuntalo como redirect a `meltonagents.com` o usalo para una
  landing — pero el producto/API viven en meltonagents.com.
