#!/usr/bin/env python3
"""저장소 OpenAPI 기준과 현재 FastAPI 계약을 비교한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.openapi import render_openapi


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, default=Path("openapi.json"))
    args = parser.parse_args()
    if not args.expected.is_file():
        print(f"오류: OpenAPI 기준 파일이 없습니다: {args.expected}")
        return 1
    if args.expected.read_text(encoding="utf-8") != render_openapi():
        print("오류: openapi.json이 현재 FastAPI 계약과 다릅니다")
        print("make openapi로 갱신한 뒤 변경 내용을 검토하세요")
        return 1
    print(f"OpenAPI 계약 확인: {args.expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
