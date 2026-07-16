from typing import Protocol


class LLMProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def generate(self, prompt: str) -> str: ...
