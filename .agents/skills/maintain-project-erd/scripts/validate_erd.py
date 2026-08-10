#!/usr/bin/env python3
"""로컬 Mermaid ERD의 필수 구조와 엔티티 정의를 검증한다."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_ENTITIES = {
    "USERS",
    "HEALTH_PROFILES",
    "EMAIL_VERIFICATIONS",
    "REFRESH_SESSIONS",
    "PRODUCT_CATEGORIES",
    "PRODUCTS",
    "PRODUCT_CATEGORY_MAPPINGS",
    "NUTRIENTS",
    "PRODUCT_NUTRIENTS",
    "MEDICATION_DETAILS",
    "EXPERT_COMMENTS",
    "PURCHASE_LINKS",
    "NUTRIENT_REFERENCE_VERSIONS",
    "NUTRIENT_REFERENCE_VALUES",
    "CARE_ITEMS",
    "CARE_NUTRIENT_SNAPSHOTS",
    "CARE_STATUS_HISTORIES",
    "NOTIFICATIONS",
    "EMAIL_DELIVERIES",
}
REQUIRED_SECTIONS = ("## ERD 변경 규칙", "## 미확정 설계 항목")
PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}|\b(?:TODO|TBD|FIXME)\b")
MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
ENTITY_BLOCK = re.compile(r"(?ms)^\s*([A-Z][A-Z0-9_]*)\s*\{(.*?)^\s*\}")
RELATION = re.compile(
    r"(?m)^\s*([A-Z][A-Z0-9_]*)\s+[|o}{.\-]+\s+"
    r"([A-Z][A-Z0-9_]*)\s*:"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "erd_file",
        nargs="?",
        type=Path,
        default=Path("docs/architecture/erd.md"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.erd_file.resolve()
    errors: list[str] = []

    if not path.is_file():
        print(f"오류: ERD 파일이 없습니다: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    if PLACEHOLDER.search(text):
        errors.append("ERD에 미완료 자리표시자가 있습니다")

    for section in REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"필수 섹션 누락: {section}")

    mermaid_blocks = MERMAID_BLOCK.findall(text)
    erd_blocks = [
        block for block in mermaid_blocks if re.search(r"(?m)^erDiagram\s*$", block)
    ]
    if not erd_blocks:
        errors.append("mermaid erDiagram 블록이 하나 이상 필요합니다")

    combined = "\n".join(erd_blocks)
    definitions = {name: body for name, body in ENTITY_BLOCK.findall(combined)}
    missing = sorted(REQUIRED_ENTITIES - definitions.keys())
    if missing:
        errors.append(f"필수 엔티티 정의 누락: {', '.join(missing)}")

    for entity in sorted(REQUIRED_ENTITIES & definitions.keys()):
        if not re.search(r"(?m)^\s*\w+\s+\w+\s+[^\n]*\bPK\b", definitions[entity]):
            errors.append(f"PK 표기 누락: {entity}")

    relationships = RELATION.findall(combined)
    if not relationships:
        errors.append("엔티티 관계가 하나 이상 필요합니다")
    else:
        referenced = {entity for pair in relationships for entity in pair}
        undefined = sorted(referenced - definitions.keys())
        if undefined:
            errors.append(f"관계에만 있고 정의되지 않은 엔티티: {', '.join(undefined)}")

    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1

    print(
        f"확인: {path} | ERD 블록 {len(erd_blocks)}개 | "
        f"필수 엔티티 {len(REQUIRED_ENTITIES)}개 | 관계 {len(relationships)}개"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
