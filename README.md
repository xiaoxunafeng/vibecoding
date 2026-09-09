# VibeChat — 类 ChatGPT 对话问答系统

一个前后端分离的流式对话问答系统：FastAPI 后端通过 **OpenAI 兼容协议**对接国内大模型（DeepSeek / 通义千问 / Kimi / 智谱 GLM / 本地 Ollama 均可），React 前端提供 ChatGPT 风格界面，支持**思考 / 普通双模式**的流式思维链展示。

## 功能清单

**前端（React 18 + TypeScript + Vite）**

- ChatGPT 风格暗色界面：左侧会话列表 + 右侧对话窗口
- SSE 流式打字机效果，实时逐字渲染，支持中途停止生成
- **思考模式切换**：顶部「思考模式 / 普通模式」按钮（流式时禁用），开启后可折叠的思维链先流式增长、结束后再流式输出正文
- Markdown 渲染：表格 / 列表 / 引用 / 代码块高亮 + 一键复制代码
- 会话管理：新建、切换、重命名、删除；首轮对话自动生成标题
- 示例问题引导、错误提示条、自动滚动、中文输入法 Enter 兼容

**后端（FastAPI + SQLite）**

- `POST /api/chat/stream`：SSE 流式对话（多轮上下文 + 系统提示词），支持 `thinking` 开关
- 会话 CRUD：`GET/POST/PATCH/DELETE /api/conversations`；消息记录持久化到 SQLite，`messages.reasoning_content` 单独保存思维链
- 模型厂商零耦合：只改 `.env` 即可切换 DeepSeek / Qwen / Kimi / GLM / Ollama

## 目录结构

```
vibecoding/
├── backend/
│   ├── app/
│   │   ├── main.py               # 应用入口（CORS、路由、启动建表）
│   │   ├── config.py             # .env 配置（含 thinking 开关与 reasoning_effort）
│   │   ├── schemas.py            # ChatRequest.thinking / MessageOut.reasoning_content
│   │   ├── routers/chat.py       # 流式对话（SSE + reasoning_delta）
│   │   ├── services/llm.py       # OpenAI 兼容客户端（extra_body thinking + reasoning_effort）
│   │   └── storage/database.py   # SQLite（messages.reasoning_content，自动迁移老库）
│   ├── tests/
│   │   ├── test_deepseek_thinking.py   # 思考模式实测脚本（需外网）
│   │   └── deepseek_api_report.json    # 实测产出的字段报告
│   ├── requirements.txt
│   └── .env.example
└── frontend/src/
    ├── api/client.ts             # streamChat(thinking) + reasoning_delta 事件
    ├── hooks/useChat.ts          # thinking 状态 + toggleThinking + 流式思维链
    ├── components/MessageItem.tsx # ThinkingBlock 可折叠思维链
    └── styles.css
```

## 快速开始

### 1. 启动后端（端口 8000）

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 编辑 .env，填入 LLM_API_KEY（见下表）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

http://127.0.0.1:8000/docs

### 2. 启动前端（端口 5173）

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173。Vite 已将 `/api` 代理到 8000。

## 模型配置（backend/.env）

| 厂商 | LLM_BASE_URL | LLM_MODEL | API Key 获取 |
|---|---|---|---|
| DeepSeek 代理（实测） | `https://api.suyu.io/v1` | `deepseek-chat` / `deepseek-v4-flash` | 由你提供的 Key |
| DeepSeek 官方 | `https://api.deepseek.com/v1` | `deepseek-chat` | platform.deepseek.com |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | bailian.console.aliyun.com |
| Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | platform.moonshot.cn |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-air` | open.bigmodel.cn |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` | 无需 Key，填 `ollama` |

**思考模式相关配置**

| 变量 | 默认值 | 说明 |
|---|---|---|
| `THINKING_ENABLED_DEFAULT` | `true` | 不传 `thinking` 时的默认开关 |
| `REASONING_EFFORT` | `high` | 思考强度 `low/high/max`，映射：`low→low, medium/high/xhigh→high, max→max` |

OpenAI SDK 调用示例（与官方一致，`thinking` 必须放在 `extra_body`）：

```python
client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    stream=True,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},  # disabled 关闭思考
)
```

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat/stream` | 流式对话（SSE），body: `{conversation_id?, message, thinking?}` |
| GET | `/api/conversations` | 会话列表 |
| POST | `/api/conversations` | 新建会话 |
| GET | `/api/conversations/{id}` | 会话详情（含 `messages[].reasoning_content`） |
| PATCH | `/api/conversations/{id}` | 重命名会话 |
| DELETE | `/api/conversations/{id}` | 删除会话 |

**SSE 事件序列**

```
思考开：meta{thinking:true} → reasoning_delta* → delta* → done / error
思考关：meta{thinking:false} → delta* → done / error
```

每个事件为 `data: {json}\n\n`，字段：`reasoning_delta{content}`（思维链增量）、`delta{content}`（正文增量）、`done`、`error{message}`。

## 思考模式实测对照（基于 deepseek_api_report.json）

报告位置：`backend/tests/deepseek_api_report.json`，由 `backend/tests/test_deepseek_thinking.py` 在 `2026-09-09T17:48` 对 `https://api.suyu.io/v1`（`deepseek-v4-flash`，与 `deepseek-chat` 同为混合推理模型，行为一致）实测产出，SDK `openai==2.46.0`。

| 场景 | 请求参数 | 返回 `delta` 行为 | 验证结论 |
|---|---|---|---|
| 思考开 | `thinking: enabled + reasoning_effort: high` | 先连续 `delta.reasoning_content` 增量（30 chunks），结束后 `delta.content` 增量；`usage.completion_tokens_details.reasoning_tokens=102` | ✅ 后端 `stream_chat(thinking=true)` → `reasoning_delta` → `delta` 正确 |
| 思考关 | `thinking: disabled` | 仅 `delta.content`，无 `reasoning_content` 字段；`completion_tokens_details=null` | ✅ `thinking=false` 时无思维链 |
| 默认 | 不传思考参数 | 同思考开（`reasoning_content` 存在，`reasoning_tokens=49`） | ✅ 默认 `high`，与文档一致 |
| 多轮回传 | `messages` 含 `assistant.reasoning_content` | 正常返回新一轮的 `reasoning_content + content`，`prompt_tokens=72` 正确携带历史 | ✅ `build_llm_messages()` 保留 `reasoning_content` 正确 |

流式 `chunk` 顶层字段（与 OpenAI 协议一致）：`id / model / object=chat.completion.chunk / created / choices[] / usage（仅最后 1 个 chunk，choices=[]）`；`choices[0].delta` 含 `role/content/reasoning_content/function_call/refusal/tool_calls`，`finish_reason: stop`。前端通过 `reasoning_delta` / `delta` 分别渲染思维链与正文，后端落库 `messages.reasoning_content` 与 `content` 分离。

复现测试（需外网）：

```bash
cd backend && pip install "openai>=1.40.0" && python tests/test_deepseek_thinking.py
# 产出 tests/deepseek_api_report.json + .log
```

## 常见问题

- **401 / 鉴权错误**：检查 `.env` 中 `LLM_API_KEY` 是否正确，确认已重启后端。
- **回复一次性出现而不是逐字**：确认没有开启会缓冲响应的代理；后端已设置 `X-Accel-Buffering: no`。
- **切换模型不生效**：`--reload` 模式下保存 `.env` 不会自动重载配置，手动重启后端。
- **生产部署**：`npm run build` 产出 `frontend/dist`，由 Nginx 托管并将 `/api` 反代到 `127.0.0.1:8000`。
