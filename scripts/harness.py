#!/usr/bin/env python3
"""기능 패킷과 구현 이력을 안정적인 make 명령에 연결한다."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE_ID = re.compile(r"^F-\d+(?:\.\d+)+$")
PAIR = re.compile(r"(\w+):\s*(?:\"([^\"]*)\"|([^,}]+))")


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def normalized_id(feature_id: str) -> str:
    if not FEATURE_ID.fullmatch(feature_id):
        raise SystemExit("기능 ID는 F-1.1 또는 F-2.4.1 형식이어야 합니다")
    return feature_id.lower().replace(".", "-")


def manifest_feature(feature_id: str) -> dict[str, str]:
    manifest = ROOT / "docs" / "features" / "manifest.yaml"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("- {"):
            continue
        values = {
            key: quoted if quoted else raw.strip()
            for key, quoted, raw in PAIR.findall(line)
        }
        if values.get("id") == feature_id:
            return values
    raise SystemExit(f"manifest에서 기능을 찾을 수 없습니다: {feature_id}")


def feature_dir(feature_id: str) -> Path:
    prefix = normalized_id(feature_id) + "-"
    matches: list[Path] = []
    for path in (ROOT / "docs" / "features").glob(f"*/{prefix}*"):
        feature_file = path / "feature.yaml"
        if not path.is_dir() or not feature_file.is_file():
            continue
        packet_id = yaml_scalar(feature_file.read_text(encoding="utf-8"), "id")
        if packet_id == feature_id:
            matches.append(path)
    matches.sort()
    if not matches:
        raise SystemExit(f"Feature Packet이 없습니다: {feature_id}")
    if len(matches) > 1:
        joined = ", ".join(path.as_posix() for path in matches)
        raise SystemExit(f"Feature Packet이 여러 개입니다: {joined}")
    return matches[0]


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*[\"']?([^\"'\n#]+)", text)
    return match.group(1).strip() if match else None


def feature_new(feature_id: str) -> None:
    metadata = manifest_feature(feature_id)
    if metadata.get("status") in {"external", "deferred"}:
        raise SystemExit(f"현재 백엔드 구현 대상이 아닙니다: {feature_id}")
    required = ("title", "slug", "domain", "requirement", "phase", "priority", "owner")
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise SystemExit(f"manifest 메타데이터 누락: {', '.join(missing)}")
    run(
        sys.executable,
        ".agents/skills/specify-sdd-feature/scripts/create_feature.py",
        "--id",
        feature_id,
        "--slug",
        metadata["slug"],
        "--title",
        metadata["title"],
        "--domain",
        metadata["domain"],
        "--requirement",
        metadata["requirement"],
        "--phase",
        metadata["phase"],
        "--priority",
        metadata["priority"],
        "--owner",
        metadata["owner"],
    )


def feature_check(feature_id: str, *, with_tests: bool) -> None:
    packet = feature_dir(feature_id)
    run(
        sys.executable,
        ".agents/skills/specify-sdd-feature/scripts/validate_feature.py",
        str(packet),
        "--strict",
    )
    if with_tests:
        run(
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--feature-id",
            feature_id,
        )


def history_new(feature_id: str) -> None:
    run(
        sys.executable,
        ".agents/skills/record-feature-history/scripts/create_history.py",
        str(feature_dir(feature_id)),
    )


def history_check(feature_id: str) -> None:
    packet = feature_dir(feature_id)
    history_path = yaml_scalar(
        (packet / "feature.yaml").read_text(encoding="utf-8"), "history_path"
    )
    if not history_path or history_path == "null":
        raise SystemExit(f"history_path가 없습니다: {feature_id}")
    run(
        sys.executable,
        ".agents/skills/record-feature-history/scripts/validate_history.py",
        history_path,
        "--strict",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("feature-new", "history-new", "history-check"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--feature", required=True)
    check_parser = subparsers.add_parser("feature-check")
    check_parser.add_argument("--feature", required=True)
    check_parser.add_argument("--with-tests", action="store_true")
    args = parser.parse_args()

    if args.command == "feature-new":
        feature_new(args.feature)
    elif args.command == "feature-check":
        feature_check(args.feature, with_tests=args.with_tests)
    elif args.command == "history-new":
        history_new(args.feature)
    else:
        history_check(args.feature)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
