from modules.ai.llm.base import LLMProvider


class LLMRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        if provider.provider_name in self._providers:
            raise ValueError(f"LLM provider already registered: {provider.provider_name}")
        self._providers[provider.provider_name] = provider

    def get(self, provider_name: str) -> LLMProvider:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise LookupError(f"Unknown LLM provider: {provider_name}") from exc
