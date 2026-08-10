#!/usr/bin/env python3
"""FastAPI 애플리케이션에서 저장소 OpenAPI 기준 파일을 생성한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.openapi import render_openapi


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("openapi.json"))
    args = parser.parse_args()
    args.output.write_text(render_openapi(), encoding="utf-8")
    print(f"OpenAPI 생성: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
