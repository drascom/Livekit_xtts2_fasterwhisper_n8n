"""
Helper launcher for LiveKit Server using environment variables from the host.

Usage (from repository root):
    python livekit/main.py

Environment variables (read from the current shell):
    LIVEKIT_API_KEY      - required
    LIVEKIT_API_SECRET   - required
    LIVEKIT_PORT         - optional (default: 7880)
    LIVEKIT_RTC_START    - optional (default: 50000)
    LIVEKIT_RTC_END      - optional (default: 50100)
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List


def build_command() -> List[str]:
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    if not api_key or not api_secret:
        sys.stderr.write("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in the environment.\n")
        sys.exit(1)

    port = os.getenv("LIVEKIT_PORT", "7880")
    rtc_start = os.getenv("LIVEKIT_RTC_START", "50000")
    rtc_end = os.getenv("LIVEKIT_RTC_END", "50100")

    return [
        "livekit-server",
        "--dev",
        "--bind",
        "0.0.0.0",
        "--port",
        port,
        "--rtc.port_range_start",
        rtc_start,
        "--rtc.port_range_end",
        rtc_end,
        "--api-key",
        api_key,
        "--api-secret",
        api_secret,
    ]


def main() -> None:
    cmd = build_command()
    sys.stdout.write(f"Starting LiveKit with command: {' '.join(cmd)}\n")
    sys.stdout.flush()
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
