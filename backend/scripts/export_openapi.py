import json
import sys
from pathlib import Path

from main import app


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/export_openapi.py OUTPUT_PATH")
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
