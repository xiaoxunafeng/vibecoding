"""DeepSeek 思考模式 API 实测脚本

目的：实际调用 api.suyu.io 的 deepseek-chat 模型，记录思考/非思考模式下的
流式返回字段结构，自动产出 deepseek_api_report.json（供前后端对接使用）
和 deepseek_api_report.log（人类可读日志）。

运行方式（需要有外网的终端）：
    pip install "openai>=1.40.0"
    python test_deepseek_thinking.py
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import openai
from openai import OpenAI

# ===== 测试配置 =====
# API Key 通过环境变量 DEEPSEEK_API_KEY 传入，避免提交到 GitHub
# 本地运行前执行：export DEEPSEEK_API_KEY=sk-xxxx
API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY") or ""
if not API_KEY:
    raise SystemExit(
        "未设置 DEEPSEEK_API_KEY 环境变量。请先执行：\n"
        "  export DEEPSEEK_API_KEY=sk-你的Key\n"
        "再运行：python test_deepseek_thinking.py"
    )
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.suyu.io/v1")
MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")

OUT_DIR = Path(__file__).parent
REPORT_PATH = OUT_DIR / "deepseek_api_report.json"
LOG_PATH = OUT_DIR / "deepseek_api_report.log"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=300, max_retries=1)

REPORT: dict = {
    "tested_at": datetime.now().isoformat(timespec="seconds"),
    "base_url": BASE_URL,
    "model": MODEL,
    "openai_sdk_version": openai.__version__,
    "tests": [],
}


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def run_stream_test(
    name: str,
    messages: list[dict],
    extra_body: dict | None,
    reasoning_effort: str | None,
) -> dict:
    """执行一次流式请求，逐 chunk 记录字段结构。"""
    log(f"\n{'=' * 70}")
    log(f"[TEST] {name}")
    log(f"  params: extra_body={extra_body}, reasoning_effort={reasoning_effort}")
    result: dict = {
        "name": name,
        "request": {"model": MODEL, "stream": True, "messages_count": len(messages)},
        "delta_fields_seen": {},  # delta 中出现过的字段 -> 出现次数
        "chunk_top_level_fields": set(),  # chunk 顶层字段名集合
        "choice_fields_seen": set(),  # choice 对象上出现过的字段名
        "reasoning_content": "",
        "content": "",
        "finish_reasons": [],
        "raw_chunks_sample": [],  # 前 6 个 + 最后 2 个 chunk 的完整结构
        "usage": None,
        "response_id": None,
        "response_model": None,
        "system_fingerprint": None,
        "first_token_latency_ms": None,
        "total_duration_ms": None,
        "error": None,
    }

    kwargs: dict = {
        "model": MODEL,
        "messages": messages,  # type: ignore[arg-type]
        "stream": True,
        "stream_options": {"include_usage": True},  # 观察流式下 usage 如何返回
    }
    if extra_body:
        kwargs["extra_body"] = extra_body
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    start = time.monotonic()
    n_chunks = 0
    try:
        stream = client.chat.completions.create(**kwargs)
        for chunk in stream:
            n_chunks += 1
            now_ms = int((time.monotonic() - start) * 1000)
            if result["first_token_latency_ms"] is None:
                result["first_token_latency_ms"] = now_ms

            chunk_dict = chunk.model_dump(exclude_none=False)
            result["chunk_top_level_fields"].update(chunk_dict.keys())
            if result["response_id"] is None:
                result["response_id"] = chunk_dict.get("id")
                result["response_model"] = chunk_dict.get("model")
                result["system_fingerprint"] = chunk_dict.get("system_fingerprint")

            choices = chunk_dict.get("choices") or []
            if choices:
                choice = choices[0]
                result["choice_fields_seen"].update(choice.keys())
                reason = choice.get("finish_reason")
                if reason:
                    result["finish_reasons"].append(reason)
                delta = choice.get("delta") or {}
                for k, v in delta.items():
                    result["delta_fields_seen"][k] = (
                        result["delta_fields_seen"].get(k, 0) + 1
                    )
                rc = delta.get("reasoning_content")
                if rc:
                    result["reasoning_content"] += rc
                content = delta.get("content")
                if content:
                    result["content"] += content

            usage = chunk_dict.get("usage")
            if usage:
                result["usage"] = usage

            # 保留样本 chunk（前 6 个 + 最后 2 个）
            sample = result["raw_chunks_sample"]
            if len(sample) < 6:
                sample.append({"_index": n_chunks, "_t_ms": now_ms, "chunk": chunk_dict})
            elif len(sample) == 6:
                sample.append({"_note": "...(middle chunks omitted)..."})
            if n_chunks > 6:
                if len(sample) >= 7:
                    sample.pop()  # 移除占位/上一个尾部样本
                sample.append({"_index": n_chunks, "_t_ms": now_ms, "chunk": chunk_dict})

            # 控制台实时输出前几个 token
            if n_chunks <= 8 and choices:
                d = choices[0].get("delta") or {}
                preview = {k: v for k, v in d.items() if v}
                log(f"  chunk#{n_chunks} t+{now_ms}ms delta={preview}")
    except Exception as exc:  # noqa: BLE001 - 测试脚本需捕获一切并记录
        result["error"] = f"{type(exc).__name__}: {exc}"
        log(f"  !! ERROR: {result['error']}")

    result["total_duration_ms"] = int((time.monotonic() - start) * 1000)
    result["n_chunks"] = n_chunks
    result["chunk_top_level_fields"] = sorted(result["chunk_top_level_fields"])
    result["choice_fields_seen"] = sorted(result["choice_fields_seen"])

    log(f"  chunks={n_chunks}, 首token延迟={result['first_token_latency_ms']}ms, "
        f"总耗时={result['total_duration_ms']}ms")
    log(f"  reasoning_content 长度={len(result['reasoning_content'])}, "
        f"content 长度={len(result['content'])}")
    log(f"  finish_reasons={result['finish_reasons']}")
    log(f"  usage={json.dumps(result['usage'], ensure_ascii=False)}")
    log(f"  reasoning 前120字: {result['reasoning_content'][:120]!r}")
    log(f"  content 前120字: {result['content'][:120]!r}")
    return result


# ---------- Turn 1：思考模式开启 ----------
QUESTION_1 = "9.11 and 9.8, which is greater?"
t1 = run_stream_test(
    name="1_thinking_enabled",
    messages=[{"role": "user", "content": QUESTION_1}],
    extra_body={"thinking": {"type": "enabled"}},
    reasoning_effort="high",
)

# ---------- Turn 1：思考模式关闭（对照组）----------
t2 = run_stream_test(
    name="2_thinking_disabled",
    messages=[{"role": "user", "content": QUESTION_1}],
    extra_body={"thinking": {"type": "disabled"}},
    reasoning_effort=None,
)

# ---------- 默认参数（不传任何思考相关参数，验证默认行为）----------
t3 = run_stream_test(
    name="3_default_no_params",
    messages=[{"role": "user", "content": "1+1等于几？用一句话回答"}],
    extra_body=None,
    reasoning_effort=None,
)

# ---------- Turn 2：多轮对话，带 reasoning_content 回传 ----------
messages_turn2 = [
    {"role": "user", "content": QUESTION_1},
    {
        "role": "assistant",
        "reasoning_content": t1["reasoning_content"],
        "content": t1["content"],
    },
    {"role": "user", "content": "How many Rs are there in the word 'strawberry'?"},
]
t4 = run_stream_test(
    name="4_multiturn_with_reasoning_content",
    messages=messages_turn2,
    extra_body={"thinking": {"type": "enabled"}},
    reasoning_effort="high",
)

REPORT["tests"] = [t1, t2, t3, t4]

# ---------- 汇总结论 ----------
all_delta_fields: dict[str, int] = {}
for t in REPORT["tests"]:
    for k, v in t["delta_fields_seen"].items():
        all_delta_fields[k] = all_delta_fields.get(k, 0) + v
REPORT["summary"] = {
    "delta_fields_union": all_delta_fields,
    "chunk_top_level_fields_union": sorted(
        {f for t in REPORT["tests"] for f in t["chunk_top_level_fields"]}
    ),
    "choice_fields_union": sorted(
        {f for t in REPORT["tests"] for f in t["choice_fields_seen"]}
    ),
    "stream_usage_supported": any(t["usage"] for t in REPORT["tests"]),
    "conclusion": "见各 test 的 delta_fields_seen / finish_reasons / usage",
}

REPORT_PATH.write_text(
    json.dumps(REPORT, ensure_ascii=False, indent=2, default=list), encoding="utf-8"
)
log(f"\n{'=' * 70}")
log(f"报告已写入: {REPORT_PATH}")
log(f"日志已写入: {LOG_PATH}")
log(f"delta 字段并集: {json.dumps(all_delta_fields, ensure_ascii=False)}")
log(f"chunk 顶层字段并集: {REPORT['summary']['chunk_top_level_fields_union']}")
log(f"choice 字段并集: {REPORT['summary']['choice_fields_union']}")
log(f"流式 usage 可用: {REPORT['summary']['stream_usage_supported']}")
