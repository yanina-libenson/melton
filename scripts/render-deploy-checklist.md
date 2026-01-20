# Render.com Deployment Checklist

Use this checklist to ensure a smooth deployment to Render.com.

## Pre-Deployment Checks

### Code Preparation
- [ ] All features tested locally
- [ ] No hardcoded secrets in code
- [ ] `.gitignore` excludes `.env` files
- [ ] All dependencies in `pyproject.toml` and `package.json`
- [ ] Docker files are production-ready
- [ ] Database migrations are up to date

### Test Locally with Docker
```bash
# Backend
cd backend
docker build -t melton-backend .
docker run -p 8000:8000 melton-backend

# Frontend
cd frontend
docker build -t melton-frontend .
docker run -p 3000:3000 melton-frontend
```

- [ ] Backend Docker image builds successfully
- [ ] Frontend Docker image builds successfully
- [ ] Both containers run without errors

### Repository
- [ ] All changes committed
- [ ] Changes pushed to main branch
- [ ] Repository connected to Render

---

## Render Deployment Steps

### 1. Create Blueprint
- [ ] Login to Render.com
- [ ] Click "New +" → "Blueprint"
- [ ] Select repository
- [ ] Render detects `render.yaml`
- [ ] Click "Apply"

### 2. Monitor Initial Deployment
- [ ] PostgreSQL database creating
- [ ] Redis instance creating
- [ ] Backend service building
- [ ] Frontend service building
- [ ] All services show "Live" status

### 3. Configure Secrets
- [ ] Run `python3 scripts/generate-secrets.py`
- [ ] Copy SECRET_KEY to backend environment
- [ ] Copy ENCRYPTION_KEY to backend environment
- [ ] Add MERCADOLIBRE_CLIENT_ID (if using)
- [ ] Add MERCADOLIBRE_CLIENT_SECRET (if using)
- [ ] Add LLM API keys (optional)
- [ ] Save changes and wait for redeploy

### 4. Run Database Migrations
- [ ] Go to "melton-backend" service
- [ ] Click "Shell" tab
- [ ] Run: `alembic upgrade head`
- [ ] Verify: `alembic current`
- [ ] Check for any migration errors

### 5. Save Service URLs
```
Backend: _______________________________
Frontend: _______________________________
PostgreSQL Internal: _______________________________
Redis Internal: _______________________________
```

---

## DNS Configuration (Cloudflare)

### 1. Add Custom Domains in Render
- [ ] Frontend: Add `meltonagents.com`
- [ ] Frontend: Add `www.meltonagents.com`
- [ ] Backend: Add `api.meltonagents.com`
- [ ] Note DNS instructions from Render

### 2. Configure DNS Records in Cloudflare
- [ ] Login to Cloudflare dashboard
- [ ] Select `meltonagents.com` domain
- [ ] Go to DNS → Records

**Add these CNAME records:**

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | @ | melton-frontend.onrender.com | ✅ Proxied |
| CNAME | www | melton-frontend.onrender.com | ✅ Proxied |
| CNAME | api | melton-backend.onrender.com | ✅ Proxied |

- [ ] All DNS records added
- [ ] All records show "Proxied" status (orange cloud)

### 3. Configure SSL/TLS
- [ ] Go to SSL/TLS section
- [ ] Set encryption mode: "Full (strict)"
- [ ] Go to Edge Certificates
- [ ] Enable "Always Use HTTPS"
- [ ] Enable "Automatic HTTPS Rewrites"
- [ ] Enable "HTTP Strict Transport Security (HSTS)" (optional)

### 4. Wait for DNS Propagation
- [ ] Wait 5-15 minutes
- [ ] Test: `nslookup meltonagents.com`
- [ ] Test: `nslookup api.meltonagents.com`
- [ ] Both should resolve to Cloudflare IPs

---

## Update Environment Variables with Custom Domains

### Backend Service
- [ ] Go to "melton-backend" → Environment
- [ ] Update: `FRONTEND_URL=https://meltonagents.com`
- [ ] Update: `BACKEND_URL=https://api.meltonagents.com`
- [ ] Update: `CORS_ORIGINS=https://meltonagents.com,https://www.meltonagents.com`
- [ ] Click "Save Changes"
- [ ] Wait for automatic redeploy

### Frontend Service
- [ ] Go to "melton-frontend" → Environment
- [ ] Verify: `NEXT_PUBLIC_API_URL=https://api.meltonagents.com`
- [ ] If changed, save and redeploy

---

## Verification & Testing

### Automated Tests
```bash
# Run verification script
chmod +x scripts/verify-deployment.sh
./scripts/verify-deployment.sh
```

### Manual Tests
- [ ] Visit https://meltonagents.com - loads successfully
- [ ] Visit https://www.meltonagents.com - redirects properly
- [ ] Visit https://api.meltonagents.com - shows API info
- [ ] Visit https://api.meltonagents.com/docs - shows Swagger UI
- [ ] Visit https://api.meltonagents.com/health - shows healthy status

### Feature Tests
- [ ] Register new user account
- [ ] Login with credentials
- [ ] Create a new agent
- [ ] Configure agent with tools
- [ ] Test agent conversation
- [ ] Test file uploads (if applicable)
- [ ] Test OAuth flow (if configured)
- [ ] Check agent persistence (refresh page)

### Check Logs
- [ ] Backend logs - no errors
- [ ] Frontend logs - no errors
- [ ] PostgreSQL - connection successful
- [ ] Redis - connection successful

---

## Post-Deployment Configuration

### Monitoring
- [ ] Set up health check alerts in Render
- [ ] Add email notifications for failures
- [ ] Configure uptime monitoring (optional)

### Security
- [ ] Review Cloudflare security settings
- [ ] Enable Cloudflare Web Application Firewall (WAF)
- [ ] Set up rate limiting rules
- [ ] Review API security headers

### Backups
- [ ] Verify PostgreSQL automatic backups enabled
- [ ] Download initial database backup
- [ ] Document backup restoration process
- [ ] Set up backup alerts

### Performance
- [ ] Check service resource usage
- [ ] Monitor response times
- [ ] Enable Cloudflare caching (if applicable)
- [ ] Consider CDN for static assets

---

## Troubleshooting Common Issues

### Service Won't Start
- [ ] Check environment variables are set correctly
- [ ] Verify DATABASE_URL format (postgresql+asyncpg://)
- [ ] Check logs for specific error messages
- [ ] Verify Docker build succeeds locally

### CORS Errors
- [ ] Verify CORS_ORIGINS includes all domains
- [ ] Check no trailing slashes in URLs
- [ ] Verify FRONTEND_URL matches actual domain
- [ ] Test with browser dev tools network tab

### Database Connection Issues
- [ ] Verify DATABASE_URL is using internal URL
- [ ] Check PostgreSQL service is running
- [ ] Test connection from backend shell: `python -c "from app.database import engine; print('OK')"`
- [ ] Run migrations if needed

### Domain Not Working
- [ ] Check DNS propagation: `nslookup meltonagents.com`
- [ ] Verify CNAME records point to correct targets
- [ ] Check Cloudflare proxy status (should be orange cloud)
- [ ] Verify SSL/TLS mode is "Full (strict)"
- [ ] Wait longer for DNS propagation (up to 48h)

### Frontend Can't Reach Backend
- [ ] Verify NEXT_PUBLIC_API_URL is correct
- [ ] Check CORS settings in backend
- [ ] Test API directly: `curl https://api.meltonagents.com/health`
- [ ] Check browser console for errors
- [ ] Verify backend is deployed and running

---

## Success Criteria

All checks must pass:

- ✅ All services show "Live" in Render dashboard
- ✅ https://meltonagents.com loads the application
- ✅ https://api.meltonagents.com/health returns healthy status
- ✅ User can register and login
- ✅ User can create and use agents
- ✅ No errors in service logs
- ✅ SSL certificates are valid
- ✅ DNS resolves correctly

---

## Final Steps

- [ ] Announce deployment to team/users
- [ ] Update documentation with production URLs
- [ ] Set calendar reminder for monthly cost review
- [ ] Schedule regular backup checks
- [ ] Document any custom configuration
- [ ] Share admin credentials securely

---

## Emergency Contacts & Resources

**Render Support:**
- Dashboard: https://dashboard.render.com
- Docs: https://render.com/docs
- Support: support@render.com

**Cloudflare Support:**
- Dashboard: https://dash.cloudflare.com
- Docs: https://developers.cloudflare.com
- Community: https://community.cloudflare.com

**Your Services:**
- Frontend: https://meltonagents.com
- Backend API: https://api.meltonagents.com
- API Docs: https://api.meltonagents.com/docs

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Production URL:** https://meltonagents.com
**Status:** ⬜ In Progress  ⬜ Complete
