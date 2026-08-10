#!/usr/bin/env python3
"""Feature Packet 하나의 최소 구조와 추적성을 검증한다."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_FILES = ("feature.yaml", "spec.md", "design.md", "acceptance.md", "tasks.md")
REQUIRED_KEYS = (
    "id",
    "title",
    "domain",
    "requirement",
    "phase",
    "priority",
    "status",
    "owner",
)
PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
FEATURE_ID = re.compile(r"^F-\d+(?:\.\d+)+$")
LOCAL_REQUIREMENT = re.compile(
    r"(?m)^\s+requirement_path:\s*[\"']?docs/product/requirements\.md[\"']?\s*$"
)


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*[\"']?([^\"'\n#]+)", text)
    return match.group(1).strip() if match else None


def repository_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_dir", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    feature_dir = args.feature_dir.resolve()
    errors: list[str] = []

    for name in REQUIRED_FILES:
        path = feature_dir / name
        if not path.is_file():
            errors.append(f"파일 누락: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER.search(text):
            errors.append(f"치환되지 않은 자리표시자: {name}")

    feature_file = feature_dir / "feature.yaml"
    if feature_file.is_file():
        feature_text = feature_file.read_text(encoding="utf-8")
        if not LOCAL_REQUIREMENT.search(feature_text):
            errors.append(
                "feature.yaml source.requirement_path는 "
                "docs/product/requirements.md여야 합니다"
            )
        values = {key: yaml_scalar(feature_text, key) for key in REQUIRED_KEYS}
        for key, value in values.items():
            if not value:
                errors.append(f"feature.yaml 키 누락: {key}")
        feature_id = values.get("id")
        if feature_id and not FEATURE_ID.fullmatch(feature_id):
            errors.append(f"유효하지 않은 기능 ID: {feature_id}")
        if feature_id:
            expected_prefix = feature_id.lower().replace(".", "-") + "-"
            if not feature_dir.name.startswith(expected_prefix):
                errors.append(
                    "디렉터리 이름은 "
                    f"{expected_prefix}(으)로 시작해야 합니다: {feature_dir.name}"
                )
        if args.strict and values.get("status") not in {"approved", "implemented"}:
            errors.append("엄격 검증은 상태가 approved 또는 implemented여야 합니다")
        if args.strict and values.get("status") == "implemented":
            history_path = yaml_scalar(feature_text, "history_path")
            if not history_path or history_path == "null":
                errors.append("구현 완료 상태에는 history_path가 필요합니다")
            elif not history_path.startswith("docs/history/"):
                errors.append("history_path는 docs/history/ 아래를 가리켜야 합니다")
            else:
                root = repository_root(feature_dir)
                if not (root / history_path).is_file():
                    errors.append(f"구현 이력 문서를 찾을 수 없습니다: {history_path}")

    acceptance = feature_dir / "acceptance.md"
    if (
        args.strict
        and acceptance.is_file()
        and not re.search(
            r"\bAC-[A-Za-z0-9.-]+", acceptance.read_text(encoding="utf-8")
        )
    ):
        errors.append("엄격 검증에는 인수 조건 ID가 하나 이상 필요합니다")

    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1

    print(f"OK: {feature_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
