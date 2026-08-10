#!/usr/bin/env python3
"""기능 구현 이력 문서의 구조, 추적성과 완료 상태를 검증한다."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

FEATURE_ID = re.compile(r"^F-\d+(?:\.\d+)+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
UNRESOLVED = re.compile(r"\{\{[A-Z0-9_]+\}\}|HISTORY_REQUIRED")
REQUIRED_KEYS = (
    "feature_id",
    "title",
    "requirement_id",
    "domain",
    "status",
    "completed_on",
    "feature_packet",
)
REQUIRED_HEADINGS = (
    "## 구현 요약",
    "## 구현 범위",
    "## 주요 구현 내용",
    "## API 변경",
    "## 데이터·ERD·마이그레이션",
    "## 보안과 개인정보",
    "## 테스트 및 검증",
    "## 주요 결정과 근거",
    "## 알려진 제약",
    "## 후속 작업",
    "## 관련 문서",
)
REQUIRED_SCOPE_HEADINGS = ("### 포함", "### 제외")
REQUIRED_TEST_ROWS = ("인수 조건", "대상 기능 검사", "전체 로컬 검증")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history_file", type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def section_body(text: str, heading: str, level: int) -> str | None:
    pattern = re.compile(
        rf"(?ms)^{re.escape(heading)}\s*$\n(.*?)(?=^#{{1,{level}}}\s|\Z)"
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def has_meaningful_content(text: str | None) -> bool:
    if text is None:
        return False
    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    without_headings = re.sub(r"(?m)^#{1,6}\s+.*$", "", without_comments)
    return bool(re.search(r"[0-9A-Za-z가-힣]", without_headings))


def test_row_is_complete(text: str, label: str) -> bool:
    match = re.search(rf"(?m)^\|\s*{re.escape(label)}\s*\|([^\n]+)$", text)
    if not match:
        return False
    cells = [cell.strip() for cell in match.group(1).rstrip("|").split("|")]
    return len(cells) == 2 and all(cells)


def main() -> int:
    args = parse_args()
    root = repository_root()
    path = args.history_file.resolve()
    errors: list[str] = []

    if not path.is_file():
        print(f"오류: 이력 문서가 없습니다: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    frontmatter_match = FRONTMATTER.search(text)
    if not frontmatter_match:
        print("오류: YAML frontmatter가 필요합니다")
        return 1

    frontmatter = frontmatter_match.group(1)
    values = {key: yaml_scalar(frontmatter, key) for key in REQUIRED_KEYS}
    for key, value in values.items():
        if not value or value == "null":
            errors.append(f"frontmatter 값 누락: {key}")

    feature_id = values.get("feature_id")
    if feature_id and not FEATURE_ID.fullmatch(feature_id):
        errors.append(f"유효하지 않은 기능 ID: {feature_id}")
    completed_on = values.get("completed_on")
    if completed_on and not DATE.fullmatch(completed_on):
        errors.append("completed_on은 YYYY-MM-DD 형식이어야 합니다")
    if values.get("status") not in {"draft", "implemented"}:
        errors.append("status는 draft 또는 implemented여야 합니다")

    if feature_id:
        expected_prefix = feature_id.lower().replace(".", "-") + "-"
        if not path.name.startswith(expected_prefix):
            errors.append(f"파일명은 {expected_prefix}(으)로 시작해야 합니다")
        if f"# {feature_id} " not in text:
            errors.append("문서 제목에 기능 ID가 필요합니다")

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"필수 섹션 누락: {heading}")

    feature_packet_value = values.get("feature_packet")
    feature_file: Path | None = None
    if feature_packet_value:
        feature_packet = Path(feature_packet_value)
        if not feature_packet.is_absolute():
            feature_packet = root / feature_packet
        feature_file = feature_packet / "feature.yaml"
        if not feature_file.is_file():
            errors.append(f"Feature Packet을 찾을 수 없습니다: {feature_packet}")
        else:
            feature_text = feature_file.read_text(encoding="utf-8")
            comparisons = {
                "feature_id": "id",
                "title": "title",
                "requirement_id": "requirement",
                "domain": "domain",
            }
            for history_key, feature_key in comparisons.items():
                expected = yaml_scalar(feature_text, feature_key)
                if values.get(history_key) != expected:
                    errors.append(
                        f"Feature Packet 불일치: {history_key}="
                        f"{values.get(history_key)} 예상값={expected}"
                    )

    if args.strict:
        if values.get("status") != "implemented":
            errors.append("엄격 검증은 status=implemented여야 합니다")
        if UNRESOLVED.search(text):
            errors.append("필수 구현 이력 표식이 남아 있습니다")
        for heading in REQUIRED_HEADINGS:
            if not has_meaningful_content(section_body(text, heading, 2)):
                errors.append(f"필수 섹션 내용 누락: {heading}")
        for heading in REQUIRED_SCOPE_HEADINGS:
            if not has_meaningful_content(section_body(text, heading, 3)):
                errors.append(f"구현 범위 내용 누락: {heading}")
        for label in REQUIRED_TEST_ROWS:
            if not test_row_is_complete(text, label):
                errors.append(f"검증 표의 명령 또는 결과 누락: {label}")
        try:
            expected_history_path = path.relative_to(root).as_posix()
        except ValueError:
            expected_history_path = None
        if expected_history_path and feature_file and feature_file.is_file():
            linked_path = yaml_scalar(
                feature_file.read_text(encoding="utf-8"), "history_path"
            )
            if linked_path != expected_history_path:
                errors.append(
                    "Feature Packet history_path가 이력 문서를 가리켜야 합니다: "
                    f"{expected_history_path}"
                )

    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1

    mode = "엄격" if args.strict else "구조"
    print(f"확인: {path} | {mode} 검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
