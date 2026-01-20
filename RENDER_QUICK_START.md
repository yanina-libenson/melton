# Melton - Render.com Quick Start Guide

This is a quick reference for deploying Melton to Render.com. For the complete guide, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## 📋 What You Need

- GitHub/GitLab repository (already set up ✅)
- Render.com account: https://render.com
- Cloudflare account with `meltonagents.com` domain

## 🚀 Quick Deploy (5 Steps)

### 1. Generate Secrets

```bash
python3 scripts/generate-secrets.py
```

Save the output - you'll need it for step 3.

### 2. Deploy to Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select `melton` repository
5. Render detects `render.yaml` automatically
6. Click **"Apply"**
7. Wait 10-15 minutes for deployment

### 3. Add Secrets to Backend

1. Go to **"melton-backend"** service
2. Click **"Environment"** tab
3. Add the secrets you generated in step 1:
   - `SECRET_KEY`: (paste your generated key)
   - `ENCRYPTION_KEY`: (paste your generated key)
4. Click **"Save Changes"**

### 4. Run Database Migrations

1. Still in **"melton-backend"** service
2. Click **"Shell"** tab
3. Run: `alembic upgrade head`
4. Verify migrations succeeded

### 5. Configure DNS on Cloudflare

1. Go to https://dash.cloudflare.com
2. Select **meltonagents.com** domain
3. Go to **DNS → Records**
4. Add these CNAME records (all **Proxied** = orange cloud):

   | Type  | Name | Target                           | Proxy    |
   |-------|------|----------------------------------|----------|
   | CNAME | @    | melton-frontend.onrender.com     | ✅ Proxied |
   | CNAME | www  | melton-frontend.onrender.com     | ✅ Proxied |
   | CNAME | api  | melton-backend.onrender.com      | ✅ Proxied |

5. Go to **SSL/TLS** → Set to **"Full (strict)"**
6. Go to **Edge Certificates** → Enable **"Always Use HTTPS"**

### 6. Add Custom Domains in Render

**Frontend:**
1. Go to **"melton-frontend"** → **Settings** → **Custom Domain**
2. Add: `meltonagents.com`
3. Add: `www.meltonagents.com`

**Backend:**
1. Go to **"melton-backend"** → **Settings** → **Custom Domain**
2. Add: `api.meltonagents.com`

### 7. Update URLs in Backend

1. Go to **"melton-backend"** → **Environment**
2. Update these variables:
   ```
   FRONTEND_URL=https://meltonagents.com
   BACKEND_URL=https://api.meltonagents.com
   CORS_ORIGINS=https://meltonagents.com,https://www.meltonagents.com
   ```
3. Click **"Save Changes"** (will auto-redeploy)

### 8. Verify Deployment

```bash
# Run automated verification
./scripts/verify-deployment.sh
```

Or test manually:
- Visit: https://meltonagents.com ✅
- Visit: https://api.meltonagents.com/health ✅
- Visit: https://api.meltonagents.com/docs ✅

## 📁 Files Created for Deployment

All these files are ready and committed:

```
melton/
├── render.yaml                          # Infrastructure as code
├── DEPLOYMENT.md                        # Complete deployment guide
├── RENDER_QUICK_START.md               # This file
├── frontend/
│   ├── Dockerfile                      # Production container
│   ├── .env.production                 # Production env vars
│   └── next.config.ts                  # Updated for standalone
├── backend/
│   └── Dockerfile                      # Updated (no --reload)
└── scripts/
    ├── generate-secrets.py             # Generate secure keys
    ├── verify-deployment.sh            # Test deployment
    └── render-deploy-checklist.md     # Detailed checklist
```

## 💰 Cost Estimate

**Render.com (recommended for production):**
- PostgreSQL Starter: $7/month
- Redis Starter: $10/month
- Backend Web Service: $7/month
- Frontend Web Service: $7/month
- **Total: ~$31/month**

**Free Tier (for testing):**
- Use free PostgreSQL (limited resources)
- Use free Redis alternative (Upstash)
- Free web services (sleep after 15 min inactivity)
- **Total: $0/month**

## 🔧 Optional: Add OAuth & API Keys

In **"melton-backend"** → **Environment**, add:

```bash
# MercadoLibre OAuth (if using)
MERCADOLIBRE_CLIENT_ID=your_client_id
MERCADOLIBRE_CLIENT_SECRET=your_client_secret

# LLM API Keys (optional - for system agents)
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key
```

## 🐛 Troubleshooting

### Service won't start?
Check logs in Render dashboard → Service → **Logs** tab

### CORS errors?
Verify `CORS_ORIGINS` has no trailing slashes or spaces

### Database connection issues?
- Go to PostgreSQL in Render
- Copy "Internal Database URL"
- Update `DATABASE_URL` in backend (change `postgresql://` to `postgresql+asyncpg://`)

### Domain not working?
- Wait 5-15 minutes for DNS propagation
- Test: `nslookup meltonagents.com`
- Check Cloudflare SSL is "Full (strict)"

### Frontend can't reach backend?
- Verify `NEXT_PUBLIC_API_URL=https://api.meltonagents.com` in frontend
- Check backend is deployed and running
- Test: `curl https://api.meltonagents.com/health`

## 📚 Resources

- **Complete Guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Detailed Checklist**: [scripts/render-deploy-checklist.md](./scripts/render-deploy-checklist.md)
- **Render Docs**: https://render.com/docs
- **Cloudflare Docs**: https://developers.cloudflare.com

## ✅ Success Checklist

- [ ] All services show "Live" in Render
- [ ] https://meltonagents.com loads successfully
- [ ] https://api.meltonagents.com/health returns healthy
- [ ] Can register and login
- [ ] Can create and use agents
- [ ] No errors in logs

## 🎉 You're Done!

Your Melton Agent Builder is now live at:
- **Frontend**: https://meltonagents.com
- **API**: https://api.meltonagents.com
- **API Docs**: https://api.meltonagents.com/docs

---

**Need help?** Check [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed troubleshooting.
