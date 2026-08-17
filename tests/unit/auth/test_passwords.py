from __future__ import annotations

import pytest

from yeongyangkkuk.auth.passwords import Argon2PasswordHasher
from yeongyangkkuk.auth.service import normalize_email, normalize_login_id

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-1.1")]


def test_identifiers_are_normalized_case_insensitively() -> None:
    assert normalize_login_id("User123") == "user123"
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_password_is_stored_as_an_argon2id_hash() -> None:
    hasher = Argon2PasswordHasher()

    encoded = hasher.hash("Safe!Pass123")

    assert encoded.startswith("$argon2id$")
    assert "Safe!Pass123" not in encoded
    assert hasher.verify("Safe!Pass123", encoded) is True
    assert hasher.verify("Wrong!Pass123", encoded) is False
