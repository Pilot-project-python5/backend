#!/usr/bin/env python3
"""Feature Packet에서 기능 구현 이력 문서 초안을 생성한다."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

FEATURE_ID = re.compile(r"^F-\d+(?:\.\d+)+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*[\"']?([^\"'\n#]+)", text)
    return match.group(1).strip() if match else None


def normalized_id(feature_id: str) -> str:
    return feature_id.lower().replace(".", "-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_dir", type=Path)
    parser.add_argument(
        "--completed-on",
        default=date.today().isoformat(),
        help="완료일을 YYYY-MM-DD 형식으로 지정합니다.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="격리 테스트를 위해 docs/history 출력 경로를 재정의합니다.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not DATE.fullmatch(args.completed_on):
        raise SystemExit("완료일은 YYYY-MM-DD 형식이어야 합니다")

    root = repository_root()
    feature_dir = args.feature_dir.resolve()
    feature_file = feature_dir / "feature.yaml"
    if not feature_file.is_file():
        raise SystemExit(f"feature.yaml이 없습니다: {feature_file}")

    feature_text = feature_file.read_text(encoding="utf-8")
    feature_id = yaml_scalar(feature_text, "id")
    title = yaml_scalar(feature_text, "title")
    requirement = yaml_scalar(feature_text, "requirement")
    domain = yaml_scalar(feature_text, "domain")
    status = yaml_scalar(feature_text, "status")

    if not feature_id or not FEATURE_ID.fullmatch(feature_id):
        raise SystemExit(f"유효하지 않은 기능 ID: {feature_id}")
    if not title or not requirement or not domain:
        raise SystemExit("feature.yaml의 title, requirement, domain이 필요합니다")
    if status not in {"approved", "implemented"}:
        raise SystemExit("승인되거나 구현된 Feature Packet만 이력을 생성할 수 있습니다")

    prefix = normalized_id(feature_id) + "-"
    if not feature_dir.name.startswith(prefix):
        raise SystemExit(f"Feature Packet 디렉터리는 {prefix}(으)로 시작해야 합니다")
    slug = feature_dir.name[len(prefix) :]
    if not slug:
        raise SystemExit("Feature Packet 디렉터리에 slug가 필요합니다")

    template = root / "docs" / "history" / "_template.md"
    if not template.is_file():
        raise SystemExit(f"이력 템플릿이 없습니다: {template}")

    output_root = args.output_root or root / "docs" / "history"
    target = output_root / domain / f"{prefix}{slug}.md"
    if target.exists():
        raise SystemExit(f"기능 이력 문서가 이미 존재합니다: {target}")

    try:
        feature_packet_path = feature_dir.relative_to(root).as_posix()
    except ValueError:
        feature_packet_path = feature_dir.as_posix()

    replacements = {
        "FEATURE_ID": feature_id,
        "FEATURE_TITLE": title,
        "REQUIREMENT_ID": requirement,
        "DOMAIN": domain,
        "COMPLETED_ON": args.completed_on,
        "FEATURE_PACKET_PATH": feature_packet_path,
    }

    content = template.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)

    print(target)
    if args.dry_run:
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc, file=sys.stderr)
        raise SystemExit(2) from exc
