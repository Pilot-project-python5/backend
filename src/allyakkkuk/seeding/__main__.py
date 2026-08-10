"""개발 DB 시드 진입점."""

from allyakkkuk.core.config import get_settings
from allyakkkuk.core.logging import configure_logging
from allyakkkuk.db.session import engine
from allyakkkuk.seeding.runner import run_registered_seeds


def main() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    run_registered_seeds(engine)


if __name__ == "__main__":
    main()
