#!/usr/bin/env python3
"""저장소 템플릿으로 SDD Feature Packet 하나를 생성한다."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

FEATURE_ID = re.compile(r"^F-\d+(?:\.\d+)+$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def normalized_id(feature_id: str) -> str:
    return feature_id.lower().replace(".", "-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, dest="feature_id")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--phase", required=True, choices=("1", "2"))
    parser.add_argument("--priority", required=True, choices=("P0", "P1"))
    parser.add_argument("--owner", default="backend")
    parser.add_argument(
        "--output-root",
        type=Path,
        help="검증이나 격리 테스트를 위해 docs/features 출력 경로를 재정의한다.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not FEATURE_ID.fullmatch(args.feature_id):
        raise SystemExit("기능 ID는 F-1.1 또는 F-2.4.1 형식이어야 합니다")
    if not SLUG.fullmatch(args.slug):
        raise SystemExit("slug는 영문 소문자, 숫자와 하이픈만 사용해야 합니다")
    if not SLUG.fullmatch(args.domain):
        raise SystemExit("domain은 영문 소문자, 숫자와 하이픈만 사용해야 합니다")

    root = repository_root()
    template_root = root / "docs" / "features" / "_template"
    output_root = args.output_root or root / "docs" / "features"
    target = output_root / args.domain / f"{normalized_id(args.feature_id)}-{args.slug}"
    required = ("feature.yaml", "spec.md", "design.md", "acceptance.md", "tasks.md")

    missing = [name for name in required if not (template_root / name).is_file()]
    if missing:
        raise SystemExit(f"누락된 기능 템플릿: {', '.join(missing)}")
    if target.exists():
        raise SystemExit(f"Feature Packet이 이미 존재합니다: {target}")

    replacements = {
        "FEATURE_ID": args.feature_id,
        "FEATURE_TITLE": args.title,
        "DOMAIN": args.domain,
        "REQUIREMENT_ID": args.requirement,
        "PHASE": args.phase,
        "PRIORITY": args.priority,
        "OWNER": args.owner,
    }

    print(target)
    if args.dry_run:
        return 0

    target.mkdir(parents=True)
    for name in required:
        content = (template_root / name).read_text(encoding="utf-8")
        for key, value in replacements.items():
            content = content.replace("{{" + key + "}}", value)
        (target / name).write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc, file=sys.stderr)
        raise SystemExit(2) from exc
