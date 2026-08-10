"""결정적인 OpenAPI JSON을 생성하는 공통 함수."""

from __future__ import annotations

import json

from allyakkkuk.main import app


def render_openapi() -> str:
    return (
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True).rstrip()
        + "\n"
    )
