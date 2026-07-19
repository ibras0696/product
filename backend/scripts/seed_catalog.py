"""Load reviewed catalog JSON in ordered, bounded transactions."""

import argparse
import asyncio
from pathlib import Path

from modules.catalog.seed import CatalogSeedService, CatalogSeedUnitOfWork, load_seed_batches


async def _run(path: Path, *, preserve_existing: bool) -> None:
    service = CatalogSeedService(CatalogSeedUnitOfWork)
    created = 0
    unchanged = 0
    preserved = 0
    batches = load_seed_batches(path)
    for index, payload in enumerate(batches, start=1):
        result = await service.seed(payload, preserve_existing=preserve_existing)
        created += result.created
        unchanged += result.unchanged
        preserved += result.preserved
        print(
            f"Catalog seed batch {index}/{len(batches)}: "
            f"created={result.created}, unchanged={result.unchanged}, "
            f"preserved={result.preserved}"
        )
    print(f"Catalog seed complete: created={created}, unchanged={unchanged}, preserved={preserved}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load reviewed catalog facts from JSON")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--preserve-existing",
        action="store_true",
        help="keep conflicting catalog records and add only new reviewed facts",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.path, preserve_existing=args.preserve_existing))


if __name__ == "__main__":
    main()
