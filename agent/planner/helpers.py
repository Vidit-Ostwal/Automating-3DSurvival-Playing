import base64
import re

from openai import AsyncOpenAI

import config


def create_llm_client(provider: str) -> tuple[AsyncOpenAI, str]:
    if provider == "ollama":
        client = AsyncOpenAI(
            base_url=config.OLLAMA_BASE_URL,
            api_key="ollama",
        )
        return client, config.MODEL_NAME

    if provider == "openai":
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        return client, config.OPENAI_MODEL

    raise ValueError(f"Unknown LLM provider: {provider!r}. Use 'openai' or 'ollama'.")


def vision_user_content(screenshot: bytes, footer_text: str) -> list[dict]:
    b64 = base64.b64encode(screenshot).decode()
    return [
        {"type": "text", "text": "Current screenshot:"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": footer_text},
    ]


def strip_thinking(text: str) -> str:
    open_tag, close_tag = "<" + "think" + ">", "</" + "think" + ">"
    return re.sub(re.escape(open_tag) + r".*?" + re.escape(close_tag), "", text, flags=re.DOTALL).strip()


def extract_tag(tag: str, text: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


async def call_vision_llm(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_content: list,
    *,
    provider: str,
) -> tuple[str, str]:
    extra = {}
    if provider == "ollama" and not config.THINKING_ENABLED:
        extra["chat_template_kwargs"] = {"enable_thinking": False}

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=config.MAX_TOKENS,
        extra_body=extra if extra else None,
    )

    msg = response.choices[0].message
    raw = strip_thinking(msg.content or getattr(msg, "reasoning_content", "") or "")
    return raw, response.choices[0].finish_reason


def log_response_warnings(raw: str, finish_reason: str, *, expect: str) -> None:
    print(f"[LLM] finish_reason={finish_reason}  raw_length={len(raw)}")
    if not raw.strip():
        print("[LLM] WARNING: empty response from model")
    elif f"<{expect}>" not in raw:
        print(f"[LLM] WARNING: expected <{expect}> tag not found. Raw output:\n{raw[:500]}")
