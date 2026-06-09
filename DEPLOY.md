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

## 3. Secrets a cargar en el dashboard de Render (los marcados `sync: false`)

Backend (`melton-backend` → Environment):

- [ ] **`OPENAI_API_KEY`** — REQUERIDA para voz (Whisper STT + TTS). Sin esto, la voz no anda.
- [ ] `ANTHROPIC_API_KEY` — recomendada como fallback del sistema para el LLM de los agentes (si no, cada usuario debe cargar la suya en el panel).
- [ ] `GOOGLE_API_KEY` — opcional.
- [ ] `MERCADOLIBRE_CLIENT_ID` / `MERCADOLIBRE_CLIENT_SECRET` — solo si usás la integración ML.
- [ ] `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — opcional (observabilidad).

Auto-generadas por Render (`generateValue: true`, no tocar):

- `SECRET_KEY` (firma JWT) y `ENCRYPTION_KEY` (Fernet).

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
  Postgres `starter` (~$6–7), disco 1 GB (~$0.25) → **~$13–14/mes**. El frontend
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
