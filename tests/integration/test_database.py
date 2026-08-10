from __future__ import annotations

import pytest
from sqlalchemy import text

from allyakkkuk.db.session import engine

pytestmark = pytest.mark.integration


def test_postgresql_test_database_is_isolated() -> None:
    with engine.connect() as connection:
        database_name = connection.scalar(text("SELECT current_database()"))
        database_version = connection.scalar(text("SHOW server_version"))

    assert isinstance(database_name, str)
    assert database_name.endswith("_test")
    assert isinstance(database_version, str)
