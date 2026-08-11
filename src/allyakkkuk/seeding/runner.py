"""기능별 시드 세트를 순서대로 멱등 실행한다."""

from __future__ import annotations

import logging
from typing import Protocol

from sqlalchemy import Connection, Engine, text

from allyakkkuk.curation.product_nutrient_seeds import ProductNutrientSeedSet
from allyakkkuk.curation.product_seeds import ProductSeedSet
from allyakkkuk.curation.seeds import ProductCategorySeedSet

logger = logging.getLogger(__name__)


class SeedSet(Protocol):
    name: str

    def apply(self, connection: Connection) -> int: ...


REGISTERED_SEEDS: tuple[SeedSet, ...] = (
    ProductCategorySeedSet(),
    ProductSeedSet(),
    ProductNutrientSeedSet(),
)


def run_registered_seeds(
    engine: Engine, seed_sets: tuple[SeedSet, ...] = REGISTERED_SEEDS
) -> int:
    affected = 0
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        for seed_set in seed_sets:
            count = seed_set.apply(connection)
            affected += count
            logger.info("시드 적용 완료 name=%s affected=%d", seed_set.name, count)
    logger.info("전체 시드 적용 완료 sets=%d affected=%d", len(seed_sets), affected)
    return affected
