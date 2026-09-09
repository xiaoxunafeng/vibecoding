import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import ChatRequest
from app.services.llm import build_llm_messages, stream_chat
from app.storage import database as db

router = APIRouter(prefix="/api", tags=["chat"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """流式对话：支持思考/非思考两种模式。

    - thinking 为 True 时：SSE 先推送 reasoning_delta（思维链），再推送 delta（最终回答）
    - thinking 为 False/None 时：只推送 delta
    落库时 assistant 的 reasoning_content 与 content 分别保存，多轮对话回传时保留。
    """
    try:
        conversation = db.ensure_conversation(req.conversation_id)
    except ValueError as exc:
        return StreamingResponse(
            iter([_sse({"type": "error", "message": str(exc)})]),
            media_type="text/event-stream; charset=utf-8",
        )
    conv_id = conversation["id"]
    thinking = req.thinking if req.thinking is not None else settings.thinking_enabled_default

    db.add_message(conv_id, "user", req.message)
    db.auto_title_if_default(conv_id, req.message)
    history = db.get_messages(conv_id, limit=settings.history_limit - 1)
    llm_messages = build_llm_messages(history, req.message)

    async def event_stream() -> AsyncGenerator[str, None]:
        full_reasoning = ""
        full_reply = ""
        try:
            # 让前端可区分思考/非思考模式，用于首帧渲染
            yield _sse({"type": "meta", "conversation_id": conv_id, "thinking": thinking})
            for item in stream_chat(llm_messages, thinking=thinking):
                if item["type"] == "reasoning":
                    full_reasoning += item["text"]
                    yield _sse({"type": "reasoning_delta", "content": item["text"]})
                else:
                    full_reply += item["text"]
                    yield _sse({"type": "delta", "content": item["text"]})
            if full_reasoning or full_reply:
                db.add_message(conv_id, "assistant", full_reply, reasoning_content=full_reasoning)
            yield _sse({"type": "done"})
        except GeneratorExit:
            raise
        except Exception as exc:  # noqa: BLE001 - SSE 需将异常转为事件
            if full_reasoning or full_reply:
                db.add_message(conv_id, "assistant", full_reply, reasoning_content=full_reasoning)
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
