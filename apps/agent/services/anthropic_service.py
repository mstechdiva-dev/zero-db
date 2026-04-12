import os
import re
import anthropic
from typing import AsyncGenerator

MODEL_PATTERN = re.compile(r"Model:\s*(\S+)", re.IGNORECASE)
TEMPERATURE_PATTERN = re.compile(r"Temperature:\s*([\d.]+)", re.IGNORECASE)
MAX_TOKENS_PATTERN = re.compile(r"Max tokens:\s*(\d+)", re.IGNORECASE)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024


def _parse_setting(pattern: re.Pattern, text: str, default):
    match = pattern.search(text)
    if match:
        try:
            return type(default)(match.group(1))
        except (ValueError, TypeError):
            pass
    return default


class AnthropicService:
    def __init__(self, system_prompt: str, agent_name: str):
        self.system_prompt = system_prompt
        self.agent_name = agent_name
        self.client = anthropic.AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.model = _parse_setting(MODEL_PATTERN, system_prompt, DEFAULT_MODEL)
        self.temperature = float(
            _parse_setting(TEMPERATURE_PATTERN, system_prompt, DEFAULT_TEMPERATURE)
        )
        self.max_tokens = int(
            _parse_setting(MAX_TOKENS_PATTERN, system_prompt, DEFAULT_MAX_TOKENS)
        )

    async def chat(self, message: str, history: list[dict]) -> str:
        messages = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]
        messages.append({"role": "user", "content": message})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text

    async def stream_chat(
        self, message: str, history: list[dict]
    ) -> AsyncGenerator[str, None]:
        messages = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]
        messages.append({"role": "user", "content": message})

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
