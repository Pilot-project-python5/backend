"""개발 DB 시드 진입점."""

from yeongyangkkuk.core.config import get_settings
from yeongyangkkuk.core.logging import configure_logging
from yeongyangkkuk.db.session import engine
from yeongyangkkuk.seeding.runner import run_registered_seeds


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    run_registered_seeds(engine)


if __name__ == "__main__":
    main()
