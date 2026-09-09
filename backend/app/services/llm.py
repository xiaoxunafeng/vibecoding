from collections.abc import Iterator

from openai import OpenAI

from app.config import settings


def get_client() -> OpenAI:
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.stream_idle_timeout,
    )


def stream_chat(
    messages: list[dict],
    thinking: bool,
) -> Iterator[dict[str, str]]:
    """调用 OpenAI 兼容接口，逐段 yield 增量文本。

    开启思考模式时，会先流式返回 reasoning_content，再流式返回 content；
    关闭时则只返回 content。

    Yields:
        {"type": "reasoning", "text": "..."}  思维链增量
        {"type": "content", "text": "..."}    最终回答增量
    """
    client = get_client()
    kwargs: dict = {
        "model": settings.llm_model,
        "messages": messages,  # type: ignore[arg-type]
        "stream": True,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
        "stream_options": {"include_usage": True},
    }
    if thinking:
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        kwargs["reasoning_effort"] = settings.reasoning_effort
    else:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    stream = client.chat.completions.create(**kwargs)  # type: ignore[call-overload]
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta  # type: ignore[attr-defined]
        rc = getattr(delta, "reasoning_content", None)
        if rc:
            yield {"type": "reasoning", "text": rc}
        content = getattr(delta, "content", None)
        if content:
            yield {"type": "content", "text": content}


def build_llm_messages(
    history: list[dict],
    user_message: str,
) -> list[dict]:
    """组装带系统提示词的多轮上下文，保留 assistant 的 reasoning_content。"""
    msgs: list[dict] = [{"role": "system", "content": settings.system_prompt}]
    for m in history:
        if m["role"] == "assistant" and m.get("reasoning_content"):
            msgs.append(
                {
                    "role": "assistant",
                    "reasoning_content": m["reasoning_content"],
                    "content": m["content"],
                }
            )
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": user_message})
    return msgs
