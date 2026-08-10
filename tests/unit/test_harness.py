from __future__ import annotations

from pathlib import Path

import pytest
from scripts import harness

pytestmark = pytest.mark.unit


def write_packet(root: Path, directory: str, feature_id: str) -> Path:
    packet = root / "docs" / "features" / "auth" / directory
    packet.mkdir(parents=True)
    (packet / "feature.yaml").write_text(f'id: "{feature_id}"\n', encoding="utf-8")
    return packet


def test_feature_directory_matches_exact_hierarchical_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = write_packet(tmp_path, "f-1-1-signup", "F-1.1")
    write_packet(tmp_path, "f-1-1-1-login-id-availability", "F-1.1.1")
    monkeypatch.setattr(harness, "ROOT", tmp_path)

    assert harness.feature_dir("F-1.1") == expected
