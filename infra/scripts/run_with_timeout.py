from __future__ import annotations

import os
import signal
import subprocess
import sys


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: run_with_timeout.py SECONDS COMMAND [ARG ...]")
    seconds = int(sys.argv[1])
    process = subprocess.Popen(sys.argv[2:], start_new_session=True)
    try:
        return_code = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        raise SystemExit(124) from None
    raise SystemExit(return_code)


if __name__ == "__main__":
    main()
