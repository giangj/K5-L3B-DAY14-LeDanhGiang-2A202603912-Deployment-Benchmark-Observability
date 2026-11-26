# Day 14 Lab - Mission Answers

> **Sinh viên:** Lê Danh Giang (`K5-L3B`)  
> **Repository:** `K5-L3B-DAY14-LeDanhGiang-2A202603912-Deployment-Benchmark-Observability`

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (`01-localhost-vs-production/develop/app.py`)
1. **Hardcode secrets trong mã nguồn (dòng 17–18):** Khai báo trực tiếp `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`. Đẩy lên Git sẽ làm lộ thông tin nhạy cảm ngay lập tức.
2. **Không quản lý cấu hình qua biến môi trường (dòng 21–22):** `DEBUG = True` và `MAX_TOKENS = 500` được gán cứng trong code, không tách biệt được giữa `development`, `staging` và `production`.
3. **Dùng `print()` thay cho structured logging và in cả secret ra log (dòng 33–38):** `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` vừa làm lộ API key trên stdout, vừa không có timestamp/level/JSON format để công cụ giám sát tìm kiếm.
4. **Thiếu endpoint health check `/health` và `/ready` (dòng 42):** Nền tảng cloud hoặc load balancer không biết app còn sống hay đã sẵn sàng nhận traffic để restart hoặc điều hướng tải.
5. **Gắn cứng `host="localhost"`, `port=8000` và `reload=True` (dòng 49–54):** Chỉ lắng nghe nội bộ máy cá nhân (không chạy được trong Docker/cloud vốn cần `0.0.0.0` và biến `PORT`), đồng thời bật `reload=True` gây tốn tài nguyên và mất ổn định ở production.
6. **Không xử lý graceful shutdown (`SIGTERM`) và lifecycle (`lifespan`):** Khi container dừng hoặc deploy bản mới, request đang chạy bị ngắt kết nối đột ngột.

*(Kiểm tra đối chiếu với `01-localhost-vs-production/production/app.py`: đã chuyển cấu hình sang `config.py` đọc env vars, dùng `json.dumps` logging không in secret, thêm `lifespan`, `/health`, `/ready`, và bind `0.0.0.0` với `PORT`.)*

### Exercise 1.2: Chạy bản develop
Lệnh gọi (`POST /ask?question=Hello` qua query param):
```bash
curl -sS -i -X POST "http://127.0.0.1:18000/ask?question=Hello"
```
Kết quả thực tế:
```http
HTTP 200
{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 1.3: Comparison table

| Feature | Develop (`develop/app.py`) | Production (`production/app.py`) | Why Important? |
|---|---|---|---|
| **Config & Secrets** | Hardcode `OPENAI_API_KEY`, `DATABASE_URL`, `MAX_TOKENS` trực tiếp trong code | Đọc từ biến môi trường qua `Settings` (`os.getenv` / `.env` ngoài Git) | Tránh lộ secret trên Git; dùng chung 1 build cho nhiều môi trường (dev/staging/prod) |
| **Logging** | `print("[DEBUG] ...")`, in cả `OPENAI_API_KEY` | Structured JSON logging (`time`, `level`, `msg`, `event`), không log secret | Dễ lọc, tìm kiếm, cảnh báo tự động trên hệ thống log tập trung và bảo mật thông tin |
| **Health Checks** | Không có `/health`, `/ready` | Có `GET /health` (liveness) và `GET /ready` (readiness, trả 503 khi chưa sẵn sàng) | Giúp Docker/Render/Load Balancer tự khởi động lại container lỗi và chỉ gửi traffic khi app sẵn sàng |
| **Shutdown** | Tắt đột ngột | `lifespan` + xử lý `SIGTERM` (graceful shutdown) | Hoàn thành nốt các request đang xử lý trước khi thoát, tránh lỗi rớt kết nối cho người dùng |
| **Network & Port** | Cứng `host="localhost"`, `port=8000`, `reload=True` | `host="0.0.0.0"`, `port` từ env `PORT`, tắt `reload` ở prod | Container và nền tảng cloud cấp `PORT` động và yêu cầu lắng nghe trên mọi interface (`0.0.0.0`) |
| **CORS** | Không cấu hình | `CORSMiddleware` giới hạn `allowed_origins`, `allow_methods` | Ngăn các trang web lạ gọi trái phép API từ trình duyệt người dùng |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image:** Bản develop dùng `python:3.11` (bản đầy đủ gồm nhiều công cụ hệ thống không cần thiết khi chạy, ~1 GB). Bản production dùng `python:3.11-slim` (gọn nhẹ hơn rất nhiều).
2. **Working directory:** `WORKDIR /app` đặt thư mục làm việc mặc định bên trong container để mọi lệnh `COPY`, `RUN`, `CMD` chạy nhất quán tại `/app`.
3. **Copy `requirements.txt` trước `COPY . .`:** Tận dụng cơ chế Docker layer cache. Khi chỉ sửa code ứng dụng (`app.py`, `main.py`) mà không đổi thư viện, Docker dùng lại layer `pip install` đã cache, giúp build lại trong vài giây thay vì cài lại toàn bộ thư viện.
4. **`CMD` vs `ENTRYPOINT`:** `CMD` khai báo lệnh mặc định và dễ bị ghi đè khi truyền tham số lúc `docker run`; `ENTRYPOINT` cố định chương trình chính sẽ chạy (tham số truyền thêm lúc chạy sẽ nối vào sau `ENTRYPOINT`).

### Exercise 2.2: Build và run bản develop
Chạy `my-agent:develop` và gọi `POST /ask?question=Hello`:
```http
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 11:50:13 GMT
server: uvicorn
content-length: 126
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 2.3: Image size comparison (đo bằng `docker images` và `docker image inspect`)
- **Develop (`my-agent:develop`):** `1.67 GB` (`1,667,775,494` bytes)
- **Production (`my-agent:advanced`):** `240 MB` (`239,811,228` bytes)
- **Difference:** Giảm **`85.62%`** (`-1.43 GB`)

**Giải thích:** Multi-stage build tách riêng stage `builder` (dùng để cài `gcc`, `libpq-dev` và compile các thư viện Python) với stage `runtime` (chỉ copy thư mục `/root/.local` chứa các gói đã cài và mã nguồn vào image `python:3.11-slim`, chạy bằng user non-root `appuser`). Nhờ loại bỏ hoàn toàn trình biên dịch, cache apt và các file trung gian, image cuối nhỏ hơn ~7 lần và giảm bề mặt tấn công bảo mật.

### Exercise 2.4: Docker Compose stack (`02-docker/production/`)
Sơ đồ kiến trúc các service:
```text
Client ──▶ Nginx (:80 / :443, reverse proxy & LB)
              └──▶ Agent x2 (internal :8000, multi-stage runtime)
                     ├──▶ Redis (:6379, session cache & rate limit)
                     └──▶ Qdrant (:6333, vector database)
```
Kết quả test qua Nginx (`GET http://127.0.0.1:80/health`):
```http
HTTP/1.1 200 OK
Server: nginx
Date: Thu, 26 Nov 2026 11:52:16 GMT
Content-Type: application/json
Content-Length: 95
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"status":"ok","uptime_seconds":3.9,"version":"2.0.0","timestamp":"2026-11-26T11:52:16.815539"}
```

---

## Part 3: Cloud Deployment

### Exercise 3.1 / 3.2: Deploy lên Render (`render.yaml` Blueprint)
- **Nền tảng chọn chính:** Render (Blueprint với `render.yaml` cấu hình sẵn `web` service runtime `docker` trỏ tới `06-lab-complete/` + dịch vụ `keyvalue` Redis kết nối tự động qua `REDIS_URL`).
- **Public URL:** https://k5-day14-ai-agent-xi1y.onrender.com
- **Screenshots:** [dashboard.png](screenshots/dashboard.png), [running.png](screenshots/running.png), [test.png](screenshots/test.png)
- **Kết quả 4 lệnh tự kiểm CP6 trên URL public (đã che `AGENT_API_KEY`):**
  - `GET /health` → **`200`** (`{"status":"ok","environment":"production"}`)
  - `GET /ready` → **`200`** (`{"status":"ready","redis":"ok"}`)
  - `POST /ask` (thiếu key) → **`401`** (`{"detail":"Invalid or missing API key"}`)
  - `POST /ask` (có `X-API-Key`) → **`200`** (`{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock)...","user_id":"test","usage":{"input_tokens":1,"output_tokens":24,"cost_usd":1.455e-05}}`)

### So sánh `railway.toml` vs `render.yaml`
| Tiêu chí | `railway.toml` | `render.yaml` |
|---|---|---|
| **Định dạng & phạm vi** | TOML (`[build]`, `[deploy]`), cấu hình cho **1 service** đơn lẻ | YAML Blueprint (`services:`), khai báo **cả stack nhiều service** (web + keyvalue/Redis) trong cùng file |
| **Cách chỉ định build/runtime** | `builder = "DOCKERFILE"` hoặc `"NIXPACKS"` (kèm `startCommand`) | `runtime: docker` (kèm `rootDir`, `dockerfilePath`, `dockerContext`) hoặc `runtime: python` |
| **Health check** | `healthcheckPath = "/health"` (chữ `c` thường) và `healthcheckTimeout` | `healthCheckPath: /health` (camelCase chữ `C` hoa) |
| **Quản lý biến môi trường & liên kết Redis** | Đặt thủ công trên Railway Dashboard/CLI (`railway variables set`); nối Redis bằng reference variable (`${{Redis.REDIS_URL}}`) | Khai báo trực tiếp trong `envVars`: sinh key tự động bằng `generateValue: true`, nhập tay bảo mật với `sync: false`, và tự nối Redis nội bộ qua `fromService` (`property: connectionString`) |
| **Lý do khác biệt** | Thiết kế gọn nhẹ cho từng service riêng biệt trên Railway | Thiết kế theo hướng Infrastructure-as-Code (IaC) để Render dựng đồng thời cả web service lẫn database/cache từ Git repo |

### Exercise 3.3: GCP Cloud Run CI/CD (`03-cloud-deployment/production-cloud-run/`)
Pipeline trong `cloudbuild.yaml` chạy tự động qua 4 bước tuần tự (`waitFor`):
1. **`test`**: Dùng image `python:3.11-slim` cài dependencies và chạy `pytest tests/` để đảm bảo code không lỗi trước khi đóng gói.
2. **`build`**: Build Docker image gắn tag `$COMMIT_SHA` và `:latest`, tận dụng `--cache-from` để tăng tốc build layer.
3. **`push`**: Đẩy image vừa build lên Container Registry (`gcr.io/$PROJECT_ID/ai-agent`).
4. **`deploy`**: Dùng `gcloud run deploy` triển khai image mới lên Cloud Run (`asia-southeast1`), cấu hình `--min-instances=1` (tránh cold start), giới hạn `--max-instances=10`, CPU/RAM và nạp API key an toàn từ Secret Manager (`--set-secrets`). Song song, `service.yaml` mô tả đặc tả Knative chuẩn IaC gồm autoscaling target `80` concurrent requests, `livenessProbe` (`/health`) và `startupProbe` (`/ready`).

---

## Part 4: API Security

### Exercise 4.1–4.3: Test results (`04-api-gateway/`)

#### 1. API Key authentication (`04-api-gateway/develop/app.py`, `AGENT_API_KEY=secret-key-123`)
Không có API key (`401`):
```http
HTTP/1.1 401
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```
Có API key hợp lệ (`200`):
```http
HTTP/1.1 200
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

#### 2. JWT + Rate Limiting 10 req/phút (`04-api-gateway/production/app.py`, tài khoản `student` / `demo123`)
Lấy token tại `POST /auth/token` → `200 OK` (token đã được che: `<JWT_TOKEN_MASKED>`). Gửi liên tiếp 12 request bằng `Authorization: Bearer <JWT_TOKEN_MASKED>`:
```http
--- Req 1 ---
HTTP/1.1 200
{"question":"What is docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
--- Req 2..9 --- HTTP/1.1 200
--- Req 10 ---
HTTP/1.1 200
{"question":"What is docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!","usage":{"requests_remaining":0,"budget_remaining_usd":0.000189}}
--- Req 11 ---
HTTP/1.1 429
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
--- Req 12 ---
HTTP/1.1 429
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4: Cost guard implementation
- **Cơ chế hoạt động (`04-api-gateway/production/cost_guard.py` và `06-lab-complete/app/cost_guard.py`):**
  - Trước khi gọi LLM, hàm `check_budget()` đọc tổng chi phí đã tiêu trong ngày/tháng. Nếu `spent >= budget` thì chặn ngay bằng HTTP **`402 Payment Required`**, không tốn thêm tiền gọi model.
  - Sau khi LLM trả lời, hàm `record_cost(input_tokens, output_tokens)` tính chi phí theo đơn giá token (`PRICE_INPUT_PER_1K = 0.00015`, `PRICE_OUTPUT_PER_1K = 0.0006`) rồi cộng dồn vào Redis bằng `INCRBYFLOAT` (kèm `EXPIRE` tự dọn key cũ).
- **Vì sao cần cả Rate Limit lẫn Cost Guard?** Rate limit chỉ giới hạn **tần suất gọi** (số request/phút) nhưng không kiểm soát kích thước prompt/output — một attacker vẫn có thể gửi ít request nhưng prompt cực dài để đốt tiền. Cost guard kiểm soát trực tiếp **ngân sách USD** dựa trên số token thực tế tiêu thụ.

---

## Part 5: Scaling & Reliability

### Exercise 5.1–5.5: Implementation notes
1. **Health check (`/health`) vs Readiness check (`/ready`):**
   - `/health` (liveness) kiểm tra tiến trình web còn phản hồi hay không (luôn trả `200`, kể cả khi Redis tạm ngắt). Nếu fail, nền tảng sẽ restart container.
   - `/ready` (readiness) kiểm tra các phụ thuộc thiết yếu như Redis (`redis_healthy()`). Khi mất Redis, `/ready` trả `503` để load balancer tạm ngừng điều hướng traffic tới instance đó mà không restart oan container.
2. **Graceful shutdown (`SIGTERM`):**
   - Dùng `lifespan` của FastAPI và chạy `uvicorn` làm PID 1 (`exec uvicorn ...`) trong Docker để nhận trực tiếp tín hiệu `SIGTERM`. Khi nhận `SIGTERM`, server ngừng nhận kết nối mới, hoàn thành nốt các request đang xử lý (in-flight) rồi đóng kết nối Redis và thoát sạch với exit code `0`.
3. **Stateless design (Redis vs RAM) & Load balancing (`Nginx` + `--scale agent=3`):**
   - Nếu lưu session trong RAM (in-memory dict), khi chạy 3 instance sau Nginx round-robin, request 1 vào `instance-1` nhưng request 2 sang `instance-2` sẽ bị mất ngữ cảnh. Lưu session/rate-limit/cost vào Redis giúp mọi instance chia sẻ chung trạng thái.

#### Kết quả chạy thực tế `docker compose -p k5-day14-scaling up -d --build --scale agent=3` và `python test_stateless.py`:
```text
============================================================
Stateless Scaling Demo
============================================================

Session ID: 009c7769-b37b-4820-b0f1-c153dc1dbe92

Request 1: [instance-5a3c3b]
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!...

Request 2: [instance-4af9a7]
  Q: Why do we need containers?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...

Request 3: [instance-1af577]
  Q: What is Kubernetes?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 4: [instance-5a3c3b]
  Q: How does load balancing work?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 5: [instance-4af9a7]
  Q: What is Redis used for?
  A: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận....

------------------------------------------------------------
Total requests: 5
Instances used: {'instance-5a3c3b', 'instance-1af577', 'instance-4af9a7'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
  [user]: What is Docker?...
  [assistant]: Container là cách đóng gói app để chạy ở mọi nơi. Build once...
  [user]: Why do we need containers?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: What is Kubernetes?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: How does load balancing work?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: What is Redis used for?...
  [assistant]: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã đư...

✅ Session history preserved across all instances via Redis!
```
**Giải thích:** 5 request trong cùng 1 `session_id` được Nginx chia xoay vòng qua cả 3 container (`instance-5a3c3b`, `instance-4af9a7`, `instance-1af577`), nhưng khi gọi `GET /chat/{session_id}/history` vẫn thu đủ toàn bộ 10 message (5 câu hỏi + 5 câu trả lời) vì toàn bộ lịch sử được lưu tập trung trong Redis.

---

## Part 6: Final Project (`06-lab-complete/`)

Kết quả chạy `python check_production_ready.py` trong môi trường Linux container kết nối Docker daemon (ảnh build đạt **238 MB**, `docker stop` thoát với exit code `0` trong `1.0s`):

```text
================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 42/42 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

---

## AI log

1. **Hỏi gì:** Cách thiết kế đầy đủ các module còn `TODO` trong `06-lab-complete/` (`config.py`, `redis_client.py`, `auth.py`, `rate_limiter.py`, `cost_guard.py`, `main.py`, `Dockerfile`, `docker-compose.yml`, `render.yaml`) đạt chuẩn 12-Factor, stateless qua Redis, structured JSON logging và `SIGTERM` graceful shutdown.  
   **Nhận gì:** Đề xuất cấu trúc sliding-window rate limiter bằng Redis sorted set (`ZREMRANGEBYSCORE` → `ZCARD` → `ZADD` → `EXPIRE`), cost guard dùng `INCRBYFLOAT`, `JsonFormatter` cho logger, `lifespan` trong FastAPI, và multi-stage `Dockerfile` non-root dùng `exec uvicorn`.  
   **Tự sửa & tự kiểm tra:** Rà soát kỹ từng yêu cầu trong `06-lab-complete/README.md`, chạy `python check_production_ready.py` đầy đủ trong môi trường POSIX có Docker daemon → xác nhận `Result: 12/12 tiêu chí đạt · 42/42 checks passed` (`PASS 12/12`, image `238 MB`, `docker stop` `1.0s`).
2. **Hỏi gì:** Giải thích các điểm khác biệt giữa bản develop và production ở Part 1–5 và kiểm tra cú pháp `render.yaml` Blueprint cho Docker + Render Key Value (Redis).  
   **Nhận gì:** Gợi ý đối chiếu từng anti-pattern theo dòng code và cấu trúc `fromService` (`type: keyvalue`, `property: connectionString`) cho `render.yaml`.  
   **Tự sửa & tự kiểm tra:** Tự chạy toàn bộ các app thực hành Part 1, 2, 4, 5 trên máy bằng Python và Docker Compose, đo dung lượng image thật (`1.67 GB` vs `240 MB`), chụp output HTTP (`401`/`200`/`429`) và `test_stateless.py` (3 instance, 10 messages) trước khi đưa vào báo cáo.
