"""Load a reviewed catalog JSON seed in one transaction."""

import argparse
import asyncio
from pathlib import Path

from modules.catalog.seed import CatalogSeedService, CatalogSeedUnitOfWork, load_seed


async def _run(path: Path) -> None:
    result = await CatalogSeedService(CatalogSeedUnitOfWork).seed(load_seed(path))
    print(f"Catalog seed: created={result.created}, unchanged={result.unchanged}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load reviewed catalog facts from JSON")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    asyncio.run(_run(args.path))


if __name__ == "__main__":
    main()
