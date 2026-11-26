# Deployment Information

## Public URL
https://k5-day14-ai-agent.onrender.com *(cập nhật URL thực tế từ Render Dashboard sau khi Apply Blueprint)*

## Platform
Render (Blueprint IaC qua [render.yaml](render.yaml) trỏ tới thư mục `06-lab-complete/` + Render Key Value Redis)

## Test Commands

### 1. Health Check
```bash
curl -sS -o /dev/null -w '%{http_code}\n' "https://YOUR_RENDER_URL/health"
# Expected: 200
```

### 2. Readiness Check (Redis connected)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' "https://YOUR_RENDER_URL/ready"
# Expected: 200
```

### 3. Authentication Check (No API Key)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "https://YOUR_RENDER_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
# Expected: 401
```

### 4. API Test (With Authentication)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "https://YOUR_RENDER_URL/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_AGENT_API_KEY" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: 200
```

## Environment Variables Set (on Render Dashboard / `render.yaml`)
- `PORT` (Render tự cấp động cho web service)
- `REDIS_URL` (Render tự nối từ service Key Value `k5-day14-agent-redis` qua `fromService`)
- `AGENT_API_KEY` (Render tự sinh an toàn bằng `generateValue: true`, không lưu trong code)
- `ENVIRONMENT` (`production`)
- `LOG_LEVEL` (`INFO`)
- `RATE_LIMIT_PER_MINUTE` (`10`)
- `DAILY_BUDGET_USD` (`1.0`)
- `MONTHLY_BUDGET_USD` (`10.0`)

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png) *(chụp sau khi Deploy Live trên Render)*
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
