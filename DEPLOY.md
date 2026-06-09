# Deploy a producción (Render.com) — checklist

> Esta guía la ejecutás **vos**. Claude no puede hacer el deploy a cloud público
> (política de seguridad), pero dejó todo listo localmente.

Dominio elegido: **meltonagents.com** (las apps iOS/watch ya apuntan a
`https://api.meltonagents.com` por default). `yani.ar` queda libre para una
landing/short-link, no como dominio del producto.

## 0. Estado / qué ya quedó listo

- `render.yaml` (Blueprint): backend (Docker) + Postgres gestionado + frontend (Docker).
- `backend/Dockerfile`: corre `alembic upgrade head` y arranca uvicorn en `$PORT`.
- `frontend/Dockerfile`: build standalone de Next.js, hornea `NEXT_PUBLIC_API_URL` en build.
- **Fix aplicado**: `config.py` normaliza la URL de Postgres de Render
  (`postgresql://` → `postgresql+asyncpg://` para el motor async; plana para Alembic).
- CORS, FRONTEND_URL, BACKEND_URL, BASE_DOMAIN ya seteados a meltonagents.com.

## 1. Pre-deploy (verificar local)

- [ ] No hay credenciales commiteadas: `git grep -nE "sk-|AKIA|xox|BEGIN PRIVATE" -- . ':!*.md'` (debe dar vacío).
- [ ] `.env` está gitignoreado (NO se commitea).
- [ ] Commits al día y pusheados al repo remoto que Render va a leer (Render despliega desde un repo Git, branch `main`). **OJO**: hoy los commits están solo locales — vas a tener que pushear a un remoto (GitHub/GitLab) que conectes a Render.

## 2. Crear el Blueprint en Render

1. Conectá el repo a Render (New → Blueprint) y apuntá a `melton/render.yaml`.
2. Render crea: `melton-postgres`, `melton-backend`, `melton-frontend`.

## 3. Secrets / env vars

**Las API keys de LLM/OpenAI son config POR USUARIO, no secrets del sistema.**
Cada usuario carga su key en el panel (Settings) → se guarda encriptada
(`UserApiKey`). El código usa la key del usuario primero y solo cae al env var
del sistema como fallback. Por eso, lo normal es:

- [ ] **Después del deploy**, entrá al panel de prod → Settings y cargá tu
      `OPENAI_API_KEY` (para voz: Whisper STT + TTS) y tu key de LLM
      (Anthropic/OpenAI/Google) para tus agentes. La DB de prod arranca vacía,
      así que se recargan ahí (no migran del dev local).

Env vars del sistema en Render (TODAS OPCIONALES — solo fallback para usuarios
que no cargaron su propia key, p. ej. un agente del sistema/compartido):

- [ ] `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` — opcionales.
- [ ] `MERCADOLIBRE_CLIENT_ID` / `MERCADOLIBRE_CLIENT_SECRET` — solo si usás la integración ML.
- [ ] `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — opcional (observabilidad).

Requeridas pero AUTOMÁTICAS (no las cargás a mano):

- `DATABASE_URL` / `DATABASE_URL_SYNC` — del Postgres gestionado (`fromDatabase`).
- `SECRET_KEY` (firma JWT) y `ENCRYPTION_KEY` (Fernet) — `generateValue: true`.

> ⚠️ **CRÍTICO — `ENCRYPTION_KEY`**: con esta key se encriptan las credenciales de
> las integraciones (ej. TelePagos) en la DB. Render la genera una vez y la
> mantiene. **Nunca la cambies/rotes después de guardar credenciales** o quedan
> indescifrables (tendrías que recargar todas las integraciones).

## 4. Dominios (en el dashboard de Render → cada servicio → Custom Domains)

- [ ] `melton-frontend`: agregar `meltonagents.com` y `www.meltonagents.com`.
- [ ] `melton-backend`: agregar `api.meltonagents.com`.
- [ ] En tu registrador de DNS, cargá los registros que Render te muestra:
  - `api` → CNAME al host `…onrender.com` del backend.
  - `www` → CNAME al host del frontend.
  - apex `meltonagents.com` → A/ALIAS/ANAME según lo que indique Render (o redirect `www`→apex).
- [ ] Esperá la verificación + el cert TLS automático de Render.

## 5. Post-deploy (verificar)

- [ ] `https://api.meltonagents.com/health` → `{"status":"healthy","database":"connected"}`.
- [ ] `https://meltonagents.com` carga el panel.
- [ ] La DB de prod arranca **vacía** (las migraciones crean el schema). Tus agentes/
      integraciones/memoria del dev local **no se migran solos**: recreá el/los agentes
      y recargá las credenciales de TelePagos en el panel de prod.
- [ ] **Apps**: iOS y watch ya default-ean a `https://api.meltonagents.com` — no hay que
      tocar nada salvo que en algún simulador hayas seteado `apiBaseURL` local (UserDefaults);
      para usar prod, sacá ese override.

## 6. Notas

- **Costo aprox. (USD/mes):** frontend `free` ($0), backend `starter` (~$7),
  Postgres `basic-256mb` (~$6), disco 1 GB (~$0.25) → **~$13/mes**. El frontend
  free **se duerme** tras ~15 min idle (cold start ~30–60s en la 1ª visita) y
  tiene límite de horas; subilo a `starter` (+$7) para always-on. Verificá en el
  dashboard si Free soporta dominio custom; si no, el frontend quedaría en
  `…onrender.com` hasta pasarlo a starter.
- Región Render: `oregon` (us-west). Para AR la latencia es aceptable; si querés un
  toque menos, `ohio` (us-east) está marginalmente más cerca. No es bloqueante.
- TelePagos en prod = **plata real** (igual que en dev): el gate de confirmación y el
  tope de $50.000 siguen activos.
- `yani.ar`: si querés, apuntalo como redirect a `meltonagents.com` o usalo para una
  landing — pero el producto/API viven en meltonagents.com.
