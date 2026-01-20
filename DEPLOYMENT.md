# Melton Deployment Guide - Render.com

This guide provides step-by-step instructions for deploying the Melton Agent Builder to Render.com with your custom domain `meltonagents.com`.

## Prerequisites

- GitHub/GitLab account with your Melton repository
- Render.com account (sign up at https://render.com)
- Cloudflare account with `meltonagents.com` domain configured
- All changes committed and pushed to your repository

## Architecture Overview

Your deployment will consist of:
- **PostgreSQL Database** - For storing agents, conversations, users
- **Redis Instance** - For caching and session management
- **Backend Service** - FastAPI application (Python)
- **Frontend Service** - Next.js application (Node.js)

## Cost Estimate

**Render.com:**
- PostgreSQL Starter: $7/month
- Redis Starter: $10/month
- Backend Web Service: $7/month
- Frontend Web Service: $7/month
- **Total: ~$31/month**

**Alternative (Lower Cost):**
- Use free tiers initially (services sleep after 15 min inactivity)
- Upgrade to paid when you have users

---

## Step 1: Push Your Code

Ensure all deployment files are committed:

```bash
git add .
git commit -m "Add Render.com deployment configuration"
git push origin main
```

Files that were created:
- `frontend/Dockerfile` - Frontend production container
- `backend/Dockerfile` - Backend production container (updated)
- `render.yaml` - Infrastructure as code
- `frontend/.env.production` - Production environment variables
- `frontend/next.config.ts` - Updated for standalone output

---

## Step 2: Deploy Using Render Blueprint (Recommended)

### Option A: Deploy via Render Dashboard (Easiest)

1. **Login to Render.com**
   - Go to https://dashboard.render.com
   - Click "Get Started" or login

2. **Create New Blueprint**
   - Click "New +"
   - Select "Blueprint"
   - Connect your GitHub/GitLab repository
   - Select your `melton` repository
   - Render will automatically detect `render.yaml`
   - Click "Apply"

3. **Wait for Deployment**
   - Render will create all services (databases, backend, frontend)
   - This takes about 10-15 minutes
   - Monitor the progress in the dashboard

4. **Run Database Migrations**
   - Once backend is deployed, go to "melton-backend" service
   - Click "Shell" tab
   - Run: `alembic upgrade head`
   - Verify migrations completed successfully

5. **Save Your Service URLs**
   - Backend URL: `https://melton-backend.onrender.com`
   - Frontend URL: `https://melton-frontend.onrender.com`

---

## Step 3: Add Required Secrets

Some environment variables need to be added manually for security:

1. **Go to Backend Service Settings**
   - Click on "melton-backend" service
   - Go to "Environment" tab
   - Add/Update these variables:

   ```
   SECRET_KEY=<generate-random-64-char-string>
   ENCRYPTION_KEY=<generate-random-64-char-string>
   ```

   To generate secure keys, run locally:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

2. **Add OAuth Credentials (if using MercadoLibre)**
   ```
   MERCADOLIBRE_CLIENT_ID=<your-client-id>
   MERCADOLIBRE_CLIENT_SECRET=<your-client-secret>
   ```

3. **Add LLM API Keys (Optional - for system agents)**
   ```
   ANTHROPIC_API_KEY=<your-key>
   OPENAI_API_KEY=<your-key>
   GOOGLE_API_KEY=<your-key>
   ```

4. **Click "Save Changes"** - Backend will automatically redeploy

---

## Step 4: Configure Custom Domains on Render

### Add Domain to Frontend Service

1. Go to "melton-frontend" service
2. Click "Settings" → Scroll to "Custom Domain"
3. Click "Add Custom Domain"
4. Enter: `meltonagents.com`
5. Click "Verify"
6. Render will show you need to add a CNAME record

### Add Domain to Backend Service

1. Go to "melton-backend" service
2. Click "Settings" → Scroll to "Custom Domain"
3. Click "Add Custom Domain"
4. Enter: `api.meltonagents.com`
5. Click "Verify"

### Add www Subdomain (Optional)

1. Go back to "melton-frontend" service
2. Add another custom domain: `www.meltonagents.com`

---

## Step 5: Configure DNS on Cloudflare

1. **Login to Cloudflare**
   - Go to https://dash.cloudflare.com
   - Select your `meltonagents.com` domain

2. **Add DNS Records**
   - Click "DNS" → "Records"

   **For Frontend (meltonagents.com):**
   - Type: `CNAME`
   - Name: `@`
   - Target: `melton-frontend.onrender.com`
   - Proxy status: ✅ Proxied (orange cloud)
   - TTL: Auto
   - Click "Save"

   **For www:**
   - Type: `CNAME`
   - Name: `www`
   - Target: `melton-frontend.onrender.com`
   - Proxy status: ✅ Proxied
   - Click "Save"

   **For API:**
   - Type: `CNAME`
   - Name: `api`
   - Target: `melton-backend.onrender.com`
   - Proxy status: ✅ Proxied
   - Click "Save"

3. **Configure SSL/TLS**
   - Go to "SSL/TLS" section
   - Set encryption mode to "Full (strict)"
   - Go to "Edge Certificates"
   - Enable "Always Use HTTPS"
   - Enable "Automatic HTTPS Rewrites"

4. **Wait for DNS Propagation**
   - Usually takes 5-15 minutes
   - Test with: `nslookup meltonagents.com`

---

## Step 6: Update Environment Variables with Custom Domains

Once DNS is configured and domains are verified:

### Update Backend Environment

1. Go to "melton-backend" service → "Environment"
2. Update these variables:
   ```
   FRONTEND_URL=https://meltonagents.com
   BACKEND_URL=https://api.meltonagents.com
   CORS_ORIGINS=https://meltonagents.com,https://www.meltonagents.com
   ```
3. Click "Save Changes" (will trigger redeploy)

### Update Frontend Environment

1. Go to "melton-frontend" service → "Environment"
2. Verify:
   ```
   NEXT_PUBLIC_API_URL=https://api.meltonagents.com
   ```
3. If it needs updating, save and redeploy

---

## Step 7: Verify Deployment

### Test Endpoints

1. **Frontend**: https://meltonagents.com
   - Should load the Melton interface
   - Check that styling loads correctly

2. **Backend Health**: https://api.meltonagents.com/health
   - Should return: `{"status":"healthy","database":"connected","redis":"connected"}`

3. **API Docs**: https://api.meltonagents.com/docs
   - Should show FastAPI Swagger documentation

### Test Core Features

1. **Create Account**
   - Go to https://meltonagents.com
   - Register a new user
   - Verify email/password works

2. **Create Agent**
   - Create a test agent
   - Configure tools
   - Test agent conversation

3. **OAuth Flow** (if configured)
   - Test MercadoLibre integration
   - Verify OAuth callback works

### Check Logs

1. **Backend Logs**
   - Go to "melton-backend" → "Logs"
   - Look for any errors or warnings

2. **Frontend Logs**
   - Go to "melton-frontend" → "Logs"
   - Verify no build or runtime errors

---

## Step 8: Set Up Monitoring (Optional)

1. **Enable Health Checks**
   - Already configured in render.yaml
   - Backend: `/health` endpoint
   - Render will monitor automatically

2. **Set Up Alerts**
   - Go to each service settings
   - Configure "Notifications"
   - Add your email for failure alerts

3. **Monitor Resource Usage**
   - Check CPU and Memory usage
   - Upgrade plan if needed

---

## Troubleshooting

### Service Won't Start

**Check Environment Variables:**
- Verify all required env vars are set
- Check DATABASE_URL format is correct
- Ensure SECRET_KEY and ENCRYPTION_KEY are set

**Check Logs:**
```bash
# In Render dashboard
Go to service → Logs tab
Look for error messages
```

### Database Connection Issues

**Update Connection String:**
- Go to PostgreSQL database in Render
- Copy "Internal Database URL"
- Update DATABASE_URL in backend service
- For DATABASE_URL: change `postgresql://` to `postgresql+asyncpg://`
- For DATABASE_URL_SYNC: keep as `postgresql://`

### CORS Errors

**Update CORS Settings:**
```
CORS_ORIGINS=https://meltonagents.com,https://www.meltonagents.com
```

Make sure no trailing slashes or extra spaces.

### Custom Domain Not Working

**Check DNS:**
```bash
nslookup meltonagents.com
nslookup api.meltonagents.com
```

Should point to Render's servers.

**Check Cloudflare SSL:**
- SSL/TLS mode should be "Full (strict)"
- Verify "Always Use HTTPS" is enabled

### Frontend Can't Connect to Backend

**Check API URL:**
- Frontend env: `NEXT_PUBLIC_API_URL=https://api.meltonagents.com`
- Should match backend custom domain
- Redeploy frontend after changes

---

## Manual Deployment (Alternative)

If you prefer not to use render.yaml, you can create services manually:

### Create PostgreSQL Database
1. New + → PostgreSQL
2. Name: `melton-postgres`
3. Database: `melton`
4. Plan: Starter
5. Create

### Create Redis
1. New + → Redis
2. Name: `melton-redis`
3. Plan: Starter
4. Create

### Create Backend Service
1. New + → Web Service
2. Connect repository
3. Name: `melton-backend`
4. Runtime: Docker
5. Docker Build Context: `backend`
6. Add all environment variables from render.yaml
7. Add disk: name=`uploads`, mount=`/app/uploads`, size=1GB
8. Create

### Create Frontend Service
1. New + → Web Service
2. Connect repository
3. Name: `melton-frontend`
4. Runtime: Docker
5. Docker Build Context: `frontend`
6. Add environment variables
7. Create

---

## Post-Deployment Tasks

### Security Hardening

1. **Rate Limiting** (on Cloudflare)
   - Go to Security → WAF
   - Set up rate limiting rules
   - Protect login endpoints

2. **Firewall Rules**
   - Block malicious traffic
   - Geo-blocking if needed

3. **DDoS Protection**
   - Already enabled with Cloudflare proxy

### Backups

1. **Database Backups**
   - Render automatically backs up PostgreSQL
   - Verify backup schedule in database settings
   - Consider downloading periodic backups

2. **Uploaded Files**
   - Render's persistent disk is backed up
   - Consider syncing to S3 for redundancy

### Monitoring & Analytics

1. **Add Analytics** (optional)
   - Google Analytics
   - Plausible
   - PostHog

2. **Error Tracking** (optional)
   - Sentry
   - Rollbar

3. **Performance Monitoring**
   - Render provides basic metrics
   - Consider New Relic or Datadog for advanced monitoring

---

## Updating Your Application

### Deploy Updates

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Update feature X"
   git push origin main
   ```

2. **Auto-Deploy**
   - Render automatically deploys on push to main
   - Monitor deployment in dashboard

3. **Manual Deploy**
   - Go to service
   - Click "Manual Deploy" → "Deploy latest commit"

### Database Migrations

After deploying backend changes with new migrations:

1. Go to "melton-backend" → Shell
2. Run: `alembic upgrade head`
3. Verify: `alembic current`

### Rolling Back

If deployment fails:

1. Go to service → "Events"
2. Find previous successful deploy
3. Click "Rollback to this version"

---

## Cost Optimization Tips

### Use Free Tiers Initially
- Start with free PostgreSQL (limited)
- Use Upstash free Redis
- Free web services (will sleep)
- Total: $0/month for testing

### Optimize Later
- Upgrade to paid tiers when you have users
- Monitor resource usage
- Right-size your plans

### Alternative Redis
- Use Upstash Redis (generous free tier)
- Update REDIS_URL in backend environment

---

## Support & Resources

- **Render Docs**: https://render.com/docs
- **Cloudflare Docs**: https://developers.cloudflare.com
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Next.js Docs**: https://nextjs.org/docs

---

## Checklist

### Pre-Deployment
- [ ] All code committed and pushed
- [ ] Docker files created
- [ ] render.yaml configured
- [ ] Environment files created

### Render Setup
- [ ] Render account created
- [ ] Repository connected
- [ ] Blueprint deployed
- [ ] Database migrations run
- [ ] Environment variables set
- [ ] Services are running

### DNS Configuration
- [ ] Custom domains added to services
- [ ] DNS records added to Cloudflare
- [ ] SSL/TLS configured
- [ ] Domains verified in Render
- [ ] DNS propagation complete

### Testing
- [ ] Frontend loads at meltonagents.com
- [ ] API responds at api.meltonagents.com
- [ ] User registration works
- [ ] Agent creation works
- [ ] Conversations work
- [ ] OAuth works (if configured)
- [ ] No errors in logs

### Production Ready
- [ ] Monitoring configured
- [ ] Backups verified
- [ ] Security hardening done
- [ ] Performance tested
- [ ] Documentation updated

---

**Congratulations! Your Melton Agent Builder is now live at https://meltonagents.com** 🎉
