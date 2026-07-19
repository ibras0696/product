from collections.abc import Iterable

from modules.catalog.domain.exceptions import SourceRequiredError
from modules.catalog.domain.sources import Source


def ensure_publishable(sources: Iterable[Source]) -> None:
    """Require at least one source whose provenance was verified."""
    if not any(source.is_verified for source in sources):
        raise SourceRequiredError
