from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection, Engine

from yeongyangkkuk.seeding.runner import run_registered_seeds

pytestmark = pytest.mark.unit


@dataclass
class RecordingSeed:
    name: str = "fixture"
    calls: int = 0

    def apply(self, connection: Connection) -> int:
        self.calls += 1
        return 2


def test_seed_registry_runs_in_one_transaction() -> None:
    raw_engine = MagicMock()
    connection = MagicMock(spec=Connection)
    raw_engine.begin.return_value.__enter__.return_value = connection
    seed = RecordingSeed()

    affected = run_registered_seeds(cast(Engine, raw_engine), (seed,))

    assert affected == 2
    assert seed.calls == 1
    connection.execute.assert_called_once()
