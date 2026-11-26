# Deployment Information

## Public URL
https://k5-day14-ai-agent-xi1y.onrender.com

## Platform
Render (Blueprint IaC qua [render.yaml](render.yaml) trỏ tới thư mục `06-lab-complete/` + Render Key Value Redis `k5-day14-agent-redis`)

## Test Commands

### 1. Health Check
```bash
curl -sS -i "https://k5-day14-ai-agent-xi1y.onrender.com/health"
# HTTP/1.1 200 OK
# {"status":"ok","environment":"production"}
```

### 2. Readiness Check (Redis connected)
```bash
curl -sS -i "https://k5-day14-ai-agent-xi1y.onrender.com/ready"
# HTTP/1.1 200 OK
# {"status":"ready","redis":"ok"}
```

### 3. Authentication Check (No API Key)
```bash
curl -sS -i -X POST "https://k5-day14-ai-agent-xi1y.onrender.com/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# HTTP/1.1 401 Unauthorized
# {"detail":"Invalid or missing API key"}
```

### 4. API Test (With Authentication)
```bash
curl -sS -i -X POST "https://k5-day14-ai-agent-xi1y.onrender.com/ask" \
  -H "X-API-Key: YOUR_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
# HTTP/1.1 200 OK
# {"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","user_id":"test","usage":{"input_tokens":1,"output_tokens":24,"cost_usd":1.455e-05}}
```

## Environment Variables Set (on Render Dashboard / `render.yaml`)
- `PORT` (Render tự cấp động cho web service)
- `REDIS_URL` (Render tự nối nội bộ từ service Key Value `k5-day14-agent-redis` qua `fromService`)
- `AGENT_API_KEY` (Render tự sinh an toàn bằng `generateValue: true`, không lưu trong code)
- `ENVIRONMENT` (`production`)
- `LOG_LEVEL` (`INFO`)
- `RATE_LIMIT_PER_MINUTE` (`10`)
- `DAILY_BUDGET_USD` (`1.0`)
- `MONTHLY_BUDGET_USD` (`10.0`)

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
