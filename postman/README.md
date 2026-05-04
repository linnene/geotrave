# Postman / Newman API 集成测试

## 文件说明

| 文件 | 用途 |
|------|------|
| `GeoTrave-API-Tests.json` | Postman Collection v2.1 — 6 个 API 测试场景 |
| `GeoTrave-Local.postman_environment.json` | 本地环境变量（base_url, session_id） |

## 快速开始

### 方式一：Newman CLI（推荐 CI / 一键运行）

```bash
# 自动启动服务 → 运行测试 → 停止服务
uv run python script/run_api_tests.py

# 服务已运行时跳过启停
uv run python script/run_api_tests.py --no-server --base-url http://localhost:8000

# 输出 JSON 报告
uv run python script/run_api_tests.py --json --output report.json
```

脚本内部通过 `script/newman_runner.py` 封装 Newman CLI，自动处理：
- uvicorn 服务启动/就绪检测/停止
- session_id 动态生成（`newman-{timestamp}-{random}`）
- Newman JSON 输出解析为结构化报告

### 方式二：直接调用 Newman

```bash
# 需先启动服务
uv run python -m src.main &

# 运行集合（session_id 会自动生成）
npx newman run postman/GeoTrave-API-Tests.json \
  -e postman/GeoTrave-Local.postman_environment.json \
  --env-var "base_url=http://localhost:8000"
```

### 方式三：Postman 桌面应用

1. File → Import → 选择 `GeoTrave-API-Tests.json`
2. 右上角 Environments → Import → 选择 `GeoTrave-Local.postman_environment.json`
3. 选择 `GeoTrave Local` 环境，点击 Run Collection

## 测试场景

| # | 场景 | 端点 | 预期 |
|---|------|------|------|
| 1 | Health Check | `GET /docs` | 200, Swagger UI |
| 2 | 正常对话 | `POST /chat/` | 200, `status=success`, reply 非空 |
| 3 | 空消息校验 | `POST /chat/` message="" | 422, Pydantic 校验失败 |
| 4 | 多轮对话 | `POST /chat/` 同 session 两条消息 | 200, 两次 reply 不同 |
| 5 | 缺失 session_id | `POST /chat/` 只传 message | 200, `session_id=default_session` |
| 6 | 超长消息 | `POST /chat/` ~12KB 消息体 | 200 |

## CI 集成

GitHub Actions（`.github/workflows/Agent-node-test.yml`）在 pytest 之后运行：

```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: "22"

- name: Run API Integration Tests (Newman)
  run: uv run python script/run_api_tests.py --timeout 120
```

LLM API 密钥通过 GitHub Secrets 注入，服务子进程自动继承。

## 添加新测试

编辑 `GeoTrave-API-Tests.json`，在 `item` 数组中追加：

```json
{
  "name": "场景名称",
  "event": [{
    "listen": "test",
    "script": { "exec": ["pm.test(...)", "..."], "type": "text/javascript" }
  }],
  "request": {
    "method": "POST",
    "header": [{ "key": "Content-Type", "value": "application/json" }],
    "body": { "mode": "raw", "raw": "{...}" },
    "url": { "raw": "{{base_url}}/chat/", "host": ["{{base_url}}"], "path": ["chat"] }
  }
}
```

`{{base_url}}` 和 `{{session_id}}` 由环境变量注入，pre-request 脚本自动补全缺失的 session_id。

## 结构化日志

每次运行自动在 `output/` 目录生成 `run-{UTC时间戳}.json` 日志文件。日志结构：

```
output/
  run-2026-05-04T04-12-25.json   # 完整运行日志
```

### 日志内容

```json
{
  "run_id": "run-2026-05-04T04-12-25",
  "timestamp": "2026-05-04T04:12:25Z",
  "base_url": "http://localhost:8000",
  "collection": "GeoTrave-API-Tests.json",
  "summary": {
    "requests":    { "total": 6, "passed": 6, "failed": 0 },
    "assertions":  { "total": 17, "passed": 17, "failed": 0 },
    "duration_ms": 30203
  },
  "requests": [
    {
      "name": "POST /chat/ — 正常对话",
      "status": 200,
      "response_time_ms": 6593,
      "assertions_passed": 4,
      "assertions_failed": 0,
      "assertions": [
        { "name": "Status 200", "passed": true, "error": null },
        { "name": "status is success", "passed": true, "error": null }
      ]
    }
  ],
  "failures": []
}
```

每个请求逐条断言记录 pass/fail 及错误信息，便于 CI 后审计或趋势分析。

自定义输出目录：

```bash
uv run python script/run_api_tests.py --output-dir ./custom-logs
```
