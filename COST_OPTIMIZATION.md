# Melton Cost Optimization Guide

This guide shows you how to deploy Melton for as cheap as possible, including **completely free** options.

## 💰 Cost Comparison

| Option | Monthly Cost | Pros | Cons |
|--------|--------------|------|------|
| **Original** | $31 | Always on, fast, full features | Most expensive |
| **Budget** | $8-15 | Backend always on, affordable | Frontend may sleep |
| **Free** | $0 | Perfect for testing/demos | Services sleep, limited resources |
| **External DB** | $7-14 | Best balance of cost/performance | Requires external setup |

---

## 🎯 Recommended: Budget Option ($8/month)

**Best balance of cost and performance for small-scale production.**

### What You Get
- ✅ Backend always on (no sleep)
- ✅ Free PostgreSQL (Neon - 10GB, always on)
- ✅ Free Redis (Upstash - 10k commands/day)
- ⚠️ Frontend sleeps after 15 min (but wakes up fast)
- ✅ 1GB file storage

### Setup Steps

#### 1. Create Free Database (Neon)

1. Go to https://neon.tech and sign up
2. Create a new project: "melton"
3. Copy the connection string
4. Modify it for your app:
   ```
   Original: postgresql://user:pass@endpoint/dbname

   For DATABASE_URL: postgresql+asyncpg://user:pass@endpoint/dbname
   For DATABASE_URL_SYNC: postgresql://user:pass@endpoint/dbname
   ```

#### 2. Create Free Redis (Upstash)

1. Go to https://upstash.com and sign up
2. Create a new Redis database: "melton"
3. Copy the connection string:
   ```
   redis://default:password@endpoint:port
   ```

#### 3. Deploy to Render

```bash
# Use the budget blueprint
cp render-budget.yaml render.yaml
git add render.yaml
git commit -m "Use budget deployment"
git push
```

Then:
1. Go to https://dashboard.render.com
2. New + → Blueprint
3. Select your repository
4. Render will deploy with `render.yaml`

#### 4. Add Database URLs

In Render dashboard:
1. Go to "melton-backend" → Environment
2. Add these (from step 1 & 2):
   ```
   DATABASE_URL=postgresql+asyncpg://[from-neon]
   DATABASE_URL_SYNC=postgresql://[from-neon]
   REDIS_URL=redis://[from-upstash]
   ```
3. Save (will trigger redeploy)

#### 5. Run Migrations

In "melton-backend" → Shell:
```bash
alembic upgrade head
```

**Total Cost: $8/month**
- Neon PostgreSQL: FREE
- Upstash Redis: FREE
- Backend: $7/month (starter)
- Disk: $1/month (1GB)
- Frontend: FREE (sleeps)

---

## 🆓 Option 2: Completely Free ($0/month)

**Perfect for testing, demos, hobby projects, or low-traffic sites.**

### Limitations
- Services sleep after 15 minutes of inactivity
- 50-second cold start when waking up
- PostgreSQL free tier expires after 90 days
- No persistent disk for uploads
- Limited resources (512MB RAM)

### Setup Steps

#### 1. Create Free Redis (Upstash)

Same as budget option above - create free Redis at https://upstash.com

#### 2. Deploy with Free Tier

```bash
# Use the free tier blueprint
cp render-free-tier.yaml render.yaml
git add render.yaml
git commit -m "Use free tier deployment"
git push
```

Then deploy via Render Blueprint as usual.

#### 3. Add Redis URL

In "melton-backend-free" → Environment:
```
REDIS_URL=redis://[from-upstash]
```

#### 4. Run Migrations

After first deployment:
```bash
alembic upgrade head
```

### Making Free Tier Work Well

**1. Keep Services Awake (Optional)**

Use a free service like [UptimeRobot](https://uptimerobot.com) to ping your site every 5 minutes:
- Monitor: https://meltonagents.com
- Monitor: https://api.meltonagents.com/health

This keeps services awake during your active hours.

**2. Handle Uploads Without Persistent Disk**

Since free tier doesn't support persistent disks, store uploads externally:

**Option A: Cloudflare R2 (Free)**
- 10GB storage free
- No egress fees
- S3-compatible API

**Option B: AWS S3 Free Tier**
- 5GB storage free (12 months)
- Standard S3 API

You'd need to modify the upload handler in your backend to use these instead of local disk.

**Total Cost: $0/month**

---

## 💡 Option 3: Single Paid Service ($7/month)

Deploy both frontend and backend in a single web service.

### Architecture
```
Single Container:
├── Nginx (reverse proxy)
├── FastAPI (backend) :8000
└── Next.js (frontend) :3000
```

### Pros
- Cheapest paid option
- No CORS issues
- Single deployment

### Cons
- More complex setup
- Need to modify deployment
- Less scalable

### Setup

I can create this architecture for you if you want. It requires:
1. Combined Dockerfile
2. Nginx configuration
3. Modified start script

Let me know if you want me to create this!

---

## 📊 Feature Comparison

| Feature | Free | Budget | Original |
|---------|------|--------|----------|
| **Backend Uptime** | Sleeps | ✅ Always | ✅ Always |
| **Frontend Uptime** | Sleeps | Sleeps | ✅ Always |
| **Database** | 1GB/90days | ✅ 10GB | ✅ Unlimited |
| **Redis** | ✅ 10k/day | ✅ 10k/day | ✅ Unlimited |
| **File Storage** | ❌ None | ✅ 1GB | ✅ Unlimited |
| **Cold Start** | 50 sec | Frontend only | None |
| **Backups** | Manual | Auto | Auto |
| **Performance** | Slow | Good | Fast |

---

## 🎓 My Recommendation

### For Development/Testing
→ **Free Tier** - Perfect for testing before going live

### For Small Production (< 100 users)
→ **Budget Option ($8/month)** - Best value
- Backend always fast
- Frontend wakes up quickly (static pages)
- External free DB/Redis are reliable

### For Growing Business (> 100 users)
→ **Original ($31/month)** - Worth it
- Everything always on
- Faster performance
- Better reliability
- Managed backups

### For Tight Budget
→ **Free Tier + UptimeRobot** - Keeps services awake during business hours

---

## 🔧 Additional Cost Savings

### 1. Optimize Docker Images

Reduce build times and costs:

```dockerfile
# Use alpine for smaller images
FROM python:3.11-slim → FROM python:3.11-alpine
FROM node:20-alpine (already done ✅)
```

### 2. Reduce Disk Usage

Only need uploads for:
- User avatars
- Agent icons
- MercadoLibre product images

Start with 1GB disk ($1/month), upgrade if needed.

### 3. Use Cloudflare Caching

Already done via Cloudflare proxy:
- Static assets cached at edge
- Reduces backend load
- Faster for users

### 4. Optimize Database

PostgreSQL optimization:
- Add indexes for common queries
- Use connection pooling
- Archive old conversations

### 5. Choose Cheaper Regions

Render regions by price:
- Oregon: Standard pricing
- Ohio: Standard pricing
- Frankfurt: May be more expensive

Stick with Oregon for best value.

---

## 📈 Scaling Path

Start cheap, upgrade as you grow:

**Month 1-3: Free Tier ($0)**
- Test and validate idea
- Get first users
- Fix bugs

**Month 4-6: Budget ($8)**
- Growing user base
- Need reliability
- Backend always on

**Month 7+: Full Paid ($31)**
- Significant traffic
- Need performance
- Professional service

---

## 🎯 Quick Start: Budget Deployment

If you want the budget option ($8/month), here's what to do:

```bash
# 1. Create external services
# - Neon: https://neon.tech (get PostgreSQL URL)
# - Upstash: https://upstash.com (get Redis URL)

# 2. Use budget blueprint
cp render-budget.yaml render.yaml

# 3. Deploy
git add render.yaml
git commit -m "Deploy with budget option"
git push

# 4. Deploy via Render Blueprint
# - Add DATABASE_URL, DATABASE_URL_SYNC, REDIS_URL manually

# 5. Run migrations
# - In backend shell: alembic upgrade head
```

That's it! You'll have a production-ready Melton for $8/month.

---

## 🆘 Need Help?

**Want me to set up a specific option?** Let me know:
- "Set up budget option" - I'll prepare everything for $8/month
- "Set up free tier" - I'll optimize for free deployment
- "Set up single service" - I'll create combined architecture

**Questions about:**
- External database setup
- Redis alternatives
- Upload storage options
- Performance optimization

Just ask!

---

## 📚 External Service Guides

### Neon PostgreSQL (Free)
- **Free Tier**: 10GB storage, unlimited compute
- **Setup**: https://neon.tech/docs/get-started-with-neon
- **Connection String**: In project dashboard → Connection Details

### Upstash Redis (Free)
- **Free Tier**: 10,000 commands/day
- **Setup**: https://docs.upstash.com/redis/overall/getstarted
- **Connection String**: In database details → REST API URL

### Cloudflare R2 (Free)
- **Free Tier**: 10GB storage, unlimited egress
- **Setup**: https://developers.cloudflare.com/r2/get-started/
- **Use Case**: Store uploaded files instead of persistent disk

---

**Choose your option and let's deploy! 🚀**
