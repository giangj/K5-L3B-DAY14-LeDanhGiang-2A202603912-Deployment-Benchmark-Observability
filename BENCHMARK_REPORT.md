# Benchmark & Observability Report — Day 14

> Mọi con số dưới đây được trích xuất trực tiếp từ các file JSON trong `reports/`, file CSV trong `benchmark-results/`, Jaeger UI và log JSON của container trong quá trình chạy thực tế.

**Họ tên:** Lê Danh Giang (`K5-L3B`)  
**Ngày chạy:** 2026-11-26  
**Môi trường:** Windows 11 + Docker Desktop 29.9.3 (WSL2 Linux engine) + Python 3.11.9

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | `< 500 ms` | Với mock LLM cơ bản (~120ms + jitter ≤ 60ms + retrieval ~20ms), 95% request bình thường hoàn thành dưới 250ms; ngưỡng 500ms đảm bảo trải nghiệm mượt mà và phát hiện sớm hiện tượng nghẽn hàng đợi hoặc tail latency tăng cao. |
| Error rate `/ask` | `< 2.0 %` | Mock LLM có tỉ lệ lỗi upstream ngẫu nhiên mặc định 1% (`MOCK_ERROR_RATE=0.01`). Cho phép error budget 2% để dung sai các lỗi nhất thời nhưng bắt được sự cố dịch vụ. |
| Accuracy trên golden dataset | `≥ 80 %` (mục tiêu sau sửa KB: `100 %`) | Đảm bảo chất lượng câu trả lời RAG (agent v2) không bị tụt hậu (regression) trước khi merge hoặc deploy phiên bản mới. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2, 300 requests/mức)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 3.92 | 202.1 | 242.9 | 1714.8 | 0.67% | ✅ PASS |
| 10 | 39.50 | 197.5 | 243.8 | 1699.9 | 0.33% | ✅ PASS |
| 50 | 42.17 | 408.5 | 2824.8 | 5155.6 | 1.33% | ❌ FAIL |
| 100 | 35.60 | 1360.3 | 5695.6 | 6549.7 | 1.67% | ❌ FAIL |

**Nhận xét:** RPS **không tăng tuyến tính** theo concurrency. Từ `c=1` lên `c=10`, RPS tăng gần 10 lần (`3.92` → `39.50 req/s`) vì 1 worker vẫn dư khả năng xử lý `asyncio` I/O song song mà không bị xếp hàng (`p95 = 243.8 ms`). Tuy nhiên từ `c=50` lên `c=100`, RPS đạt bão hoà (~`42.17` rồi giảm còn `35.60 req/s`), trong khi `p95` vọt lên `2824.8 ms` và `5695.6 ms` do CPU/event-loop của 1 process bị quá tải và các request phải chờ trong hàng đợi.

### 2.2 Tail latency (`concurrency=20`, 300 requests)

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 200.4 | 246.8 | 255.0 |
| 0.03 (mặc định) | 242.2 | 246.8 | 1709.9 |
| 0.1 | 386.1 | 1702.6 | 1726.3 |

**Nhận xét:** **p99** (và **p95** khi tỉ lệ slow > 5%) nhạy nhất với các request chậm bất thường. Ở `MOCK_SLOW_RATE=0.03`, `avg` chỉ tăng thêm `41.8 ms` (`200.4` → `242.2 ms`), nhưng `p99` nhảy vọt gần 7 lần từ `255.0 ms` lên `1709.9 ms`. Ở `0.1`, `avg` vẫn dưới `400 ms` (`386.1 ms`) nhưng `p95` đã vọt lên `1702.6 ms` (vi phạm SLO). Vì vậy **không được đặt SLO theo giá trị trung bình (average)** vì nó che giấu hoàn toàn trải nghiệm tệ của nhóm người dùng gặp tail latency.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (`1/23`) | 91.3% (`21/23`) | 100.0% (`23/23`) |
| Avg tokens / câu | 56.6 | 108.8 | 113.0 |
| Tổng cost (USD) | $0.000397 | $0.000757 | $0.000784 |
| Cost / câu đúng (USD) | $0.00039675 | $0.00003607 | $0.00003410 |
| Quality gate | ❌ FAIL (với baseline v2, exit=1) | ✅ PASS (so với v1) | ✅ PASS (`--min-accuracy 1.0`, 0 regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa (`KNOWLEDGE_BASE` trong `utils/mock_llm.py`):**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm entry `(["jwt", "json web token", "api key"], ...)` giải thích JWT là token có chữ ký số và thời gian hết hạn (`exp`), khác với API key tĩnh. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm entry `(["kubernetes", "hpa", "horizontal pod autoscaler"], ...)` mô tả Kubernetes HPA scale dựa trên CPU, Memory hoặc custom metrics. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**  
Agent v2 thêm bước retrieval (`+20 ms`) và chèn context vào prompt nên tốn gần gấp đôi số token (`108.8`–`113.0` so với `56.6` tokens/câu) và `p95` tăng nhẹ (`195.6 ms` → `219.4–237.4 ms`). Đổi lại, độ chính xác tăng từ `4.3%` lên `100.0%`, kéo **`cost / câu đúng` giảm hơn 11 lần** (`$0.00039675` → `$0.00003410`). Đây là đánh đổi hoàn toàn xứng đáng cho sản phẩm thật.

**Quality gate trong CI (Exercise 7.3):**  
Khi chạy `python eval/run_eval.py --url http://127.0.0.1:18001 --baseline reports/eval_v2.json` cho v1, script báo **20 câu bị regression** và thoát với **exit code `1`**. Trong GitHub Actions, dùng exit code này để tự động chặn merge PR khi chất lượng tụt dưới ngưỡng hoặc có regression:
```yaml
- name: Run Agent Quality Gate
  run: |
    cd 06-lab-complete/benchmark-observability/develop
    AGENT_VERSION=v2 MOCK_ERROR_RATE=0 PORT=8000 python app.py &
    sleep 3
    python eval/run_eval.py --url http://127.0.0.1:8000 --min-accuracy 1.0 --baseline ../../../reports/eval_v2.json
```

---

## 4. Observability stack (production)

### 4.1 Screenshot & giải thích Exercise 7.4
- [x] Dashboard Grafana khi đang có tải ([grafana-dashboard.png](screenshots/grafana-dashboard.png))
- [x] Một trace chậm trong Jaeger ([jaeger-slow-trace.png](screenshots/jaeger-slow-trace.png))
- [x] Một trace lỗi trong Jaeger ([jaeger-error-trace.png](screenshots/jaeger-error-trace.png))
- [x] Trang Alerts của Prometheus với các alert đang **firing** ([prometheus-alert-firing.png](screenshots/prometheus-alert-firing.png))

**Giải thích quan sát từ Dashboard Grafana (Exercise 7.4):**
- **Khoảng cách `avg` vs `p99`:** Đường `p99` nằm sát `~1.8s` trong khi `avg` và `p50` nằm quanh `200–300 ms`, phản ánh trực tiếp ~3% request chậm từ mock LLM mà chỉ số trung bình làm mờ đi.
- **Input token > Output token:** Với RAG (agent v2), hệ thống nhồi thêm system prompt và tài liệu retrieve được vào ngữ cảnh đầu vào nên lượng input token luôn lớn hơn câu trả lời ngắn ở output.
- **Vì sao Nginx chặn `/metrics` (trả về `404` ở cổng `8080`)?** Endpoint `/metrics` chứa thông tin nội bộ của hệ thống (số lượng request, tên model, lỗi, tài nguyên) chỉ dành cho Prometheus scrape trong mạng nội bộ Docker (`obs_net`), không được công khai ra internet vì lý do bảo mật và tránh bị tấn công DoS khi gọi scrape liên tục.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | `102.2s` | `Error rate` (chuyển đỏ), `Requests/s theo status code` (xuất hiện 503) |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | `157.4s` | `Latency /ask — p50 / p95 / p99` (p95 vượt ngưỡng 1s) |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | `27.0s` (sau khi 5m burn rate vượt $2/h) | `Cost burn rate (USD/giờ)` & `LLM latency p95 theo model` |
| D | `docker pause` 1 instance | `AgentInstanceDown` | `39.3s` | `Instances` (số instance up giảm còn 1) |
| E | `AGENT_VERSION=v1` | Không có alert mới nào firing | Không firing | `Retrieval hit ratio` mất dữ liệu, `Tokens/s` giảm, bảng version đổi sang `v1` |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**  
Observability hạ tầng chỉ đo lường sức khoẻ kỹ thuật (uptime, HTTP status, latency, CPU), không đánh giá được **ngữ nghĩa hay độ chính xác** của câu trả lời AI. Để phát hiện lỗi chất lượng khi model/prompt đổi sang v1 hoặc bị suy giảm, production cần:
1. Chạy **Eval chất lượng tự động (CI quality gate)** với `golden_dataset.jsonl` trước mọi lần deploy.
2. Theo dõi các **metric chất lượng/domain** (như `retrieval_hit_ratio`, tỷ lệ fallback trả lời chung chung, điểm LLM-as-a-judge sampling theo thời gian thực, và nút thumbs-up/down từ người dùng).

### 4.3 Debug bằng trace

Chọn trace chậm nhất tìm được từ log & Jaeger UI:

- `trace_id`: `4374d51a7ec0587ba6cdd41e7097f592`
- Tổng thời gian: `2070.3 ms` (Root span `POST /ask`, hiển thị trên Jaeger UI tổng trace `2.3s`)
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` (`~2.0s` / ~`98%` thời gian trong `agent.run`, trong khi `agent.retrieve_context` chỉ mất `32.9 ms`)
- Dòng log tương ứng (grep theo `trace_id` từ `docker compose -p k5-day14-observability logs agent`):

```json
{"ts": "2026-11-26T12:20:08.186737+00:00", "level": "INFO", "service": "observable-agent", "instance": "bc41b11f7bae", "event": "http_request", "trace_id": "4374d51a7ec0587ba6cdd41e7097f592", "span_id": "4bdadc6e2f337a78", "request_id": "0d39dd431b4c", "method": "POST", "route": "/ask", "status": 200, "ms": 2070.3}
```

*(Trace lỗi minh hoạ trong [jaeger-error-trace.png](screenshots/jaeger-error-trace.png): `trace_id` `b8a953c19a7e3cd0ba5edba5266564cf`, `121 ms`, gắn lỗi `503` trên `POST /ask` và `chat mock-llm-small` tương ứng log `event: "llm_error"`.)*

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Số liệu `Aggregated` (và riêng `POST /ask`) từ `benchmark-results/scale_1_stats.csv` và `benchmark-results/scale_3_stats.csv`:

| Số instance | RPS (`Aggregated` / `/ask`) | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | `61.13` / `55.94` | `220` / `220` | `1200` / `1200` | `1800` / `1800` | `77` (`1.06%` / `1.16%`) |
| 3 | `64.46` / `58.88` | `200` / `200` | `450` / `480` | `1700` / `1700` | `68` (`0.89%` / `0.97%`) |

**Giải thích kết quả:**  
- **Scale từ 1 lên 3 instance cải thiện `p95` rất mạnh** (`1200 ms` → `450 ms` tổng hợp, `480 ms` cho `/ask`) vì với 1 container bị giới hạn `0.5 CPU`, 100 user đồng thời tạo nghẽn xử lý và xếp hàng ở event loop/CPU; khi chia sang 3 container qua Nginx, áp lực hàng đợi biến mất và `p95` quay về dưới ngưỡng SLO `500 ms`.
- Tuy nhiên, **`p50` (`220` → `200 ms`), `p99` (`1800` → `1700 ms`) và tổng RPS (`61.13` → `64.46`) thay đổi rất ít** do `locustfile.py` có `wait_time` giữa các request của 100 user và **nút thắt thời gian xử lý từng request nằm ở bước gọi upstream LLM** (`MOCK_LATENCY_MS=120`, `MOCK_SLOW_RATE=0.03` cộng thêm `1500 ms` tail latency). Tăng số bản sao agent giải quyết được nghẽn tải đồng thời nhưng không làm giảm độ trễ nội tại của nhà cung cấp LLM.

---

## 6. Kết luận

- 3 điều học được về benchmark & observability:
  1. **Average có thể đánh lừa:** Luôn đánh giá hiệu năng bằng `p95`/`p99` và kiểm tra SLO bằng load test có tải đồng thời thực tế thay vì đo vài request đơn lẻ.
  2. **Observability hạ tầng ≠ Chất lượng AI:** Prometheus/Grafana/Jaeger bắt tốt lỗi 5xx, nghẽn latency và đốt tiền, nhưng chỉ có **Eval trên Golden Dataset + Quality Gate** mới phát hiện được AI trả lời sai hoặc bị regression.
  3. **Liên kết 3 trụ cột qua `trace_id`:** Dashboard chỉ ra *khi nào* có vấn đề, Jaeger chỉ ra *span nào* chậm (`chat mock-llm-small`), và JSON log chứa `trace_id` cung cấp *chi tiết sự kiện* để sửa tận gốc.
- Nếu đưa agent này lên production thật, sẽ bổ sung thêm metric / alert:
  1. Metric & alert cho **Redis latency / connection errors** và **Nginx 502/504 upstream timeout** (vì 504 tại LB không lọt vào metric của agent).
  2. Metric đánh giá chất lượng online: **`retrieval_empty_rate`** (tỉ lệ câu hỏi không tìm thấy tài liệu liên quan), tỉ lệ HTTP **`429`/`402`** theo nhóm khách hàng, và cảnh báo sớm khi **chi phí ngày đạt 80% budget**.
