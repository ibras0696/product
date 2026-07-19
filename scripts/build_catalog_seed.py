#!/usr/bin/env python3
"""Build deterministic, bounded catalog seed batches from local research inputs."""

import argparse

from research_seed.batching import preserve_legacy_record_ids, rendered_batches, sync_output
from research_seed.categories_itog import build_categories_payload
from research_seed.common import (
    CATEGORIES_ITOG_OUTPUT_ROOT,
    CATEGORIES_ITOG_ROOT,
    DEMO_OUTPUT_ROOT,
    OUTPUT_ROOT,
    load_inputs,
)
from research_seed.harvest import build_demo_payload, build_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="owner-approved local demo: publish reviewed-source candidates in the same catalog",
    )
    parser.add_argument(
        "--categories-itog",
        action="store_true",
        help="build the final filtered catalog from docs/test/graph/categories_itog",
    )
    args = parser.parse_args()
    if args.categories_itog:
        payload = build_categories_payload(CATEGORIES_ITOG_ROOT)
        output = CATEGORIES_ITOG_OUTPUT_ROOT
    else:
        dataset, harvest, mappings = load_inputs()
        payload = (
            build_demo_payload(dataset, harvest, mappings)
            if args.demo
            else build_payload(dataset, harvest, mappings)
        )
        payload = preserve_legacy_record_ids(payload)
        output = DEMO_OUTPUT_ROOT if args.demo else OUTPUT_ROOT
    rendered = rendered_batches(payload)
    sync_output(output, rendered, check=args.check)
    if not args.check:
        records = sum(len(group) for group in payload.values())
        print(f"Generated {len(rendered)} ordered batches ({records} logical records) in {output}")


if __name__ == "__main__":
    main()
