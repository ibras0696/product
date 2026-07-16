from typing import Protocol


class SourceConnector(Protocol):
    @property
    def source_name(self) -> str: ...

    async def fetch(self, query: str) -> list[dict[str, object]]: ...
