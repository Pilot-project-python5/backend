"""비밀정보를 출력하지 않는 최소 구조화 로그 설정."""

from __future__ import annotations

import logging


def configure_logging(*, debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
