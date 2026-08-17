"""전문가 큐레이션 카탈로그 SQLAlchemy 모델."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from yeongyangkkuk.db.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_product_categories_slug"),
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_product_categories_slug_format",
        ),
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 50",
            name="ck_product_categories_name_length",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_product_categories_sort_order",
        ),
        Index(
            "ix_product_categories_active_sort",
            "is_active",
            "sort_order",
            "slug",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        CheckConstraint(
            "sku ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'",
            name="ck_products_sku_format",
        ),
        CheckConstraint(
            "product_type IN ('SUPPLEMENT', 'MEDICATION')",
            name="ck_products_product_type",
        ),
        CheckConstraint(
            "char_length(btrim(brand)) BETWEEN 1 AND 100",
            name="ck_products_brand_length",
        ),
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 200",
            name="ck_products_name_length",
        ),
        CheckConstraint(
            "char_length(btrim(image_url)) BETWEEN 1 AND 2048",
            name="ck_products_image_url_length",
        ),
        CheckConstraint(
            "unit_form IN ('TABLET', 'CAPSULE', 'SCOOP', 'PACKET')",
            name="ck_products_unit_form",
        ),
        CheckConstraint(
            "units_per_package > 0",
            name="ck_products_units_per_package",
        ),
        CheckConstraint(
            "display_price >= 0",
            name="ck_products_display_price",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_products_sort_order",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_products_updated_at",
        ),
        Index(
            "ix_products_published_sort",
            "is_published",
            "sort_order",
            "sku",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    unit_form: Mapped[str] = mapped_column(String(20), nullable=False)
    units_per_package: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    display_price: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ProductCategoryMapping(Base):
    __tablename__ = "product_category_mappings"
    __table_args__ = (
        Index(
            "ix_product_category_mappings_category_product",
            "category_id",
            "product_id",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_categories.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Nutrient(Base):
    __tablename__ = "nutrients"
    __table_args__ = (
        UniqueConstraint("code", name="uq_nutrients_code"),
        CheckConstraint(
            "code ~ '^[A-Z0-9]+(_[A-Z0-9]+)*$'",
            name="ck_nutrients_code_format",
        ),
        CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 100",
            name="ck_nutrients_name_length",
        ),
        CheckConstraint(
            "canonical_unit IN ('MG', 'G', 'MCG', 'IU')",
            name="ck_nutrients_canonical_unit",
        ),
        Index("ix_nutrients_active_code", "is_active", "code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProductNutrient(Base):
    __tablename__ = "product_nutrients"
    __table_args__ = (
        CheckConstraint(
            "amount_per_unit > 0",
            name="ck_product_nutrients_amount_per_unit",
        ),
        CheckConstraint(
            "unit IN ('MG', 'G', 'MCG', 'IU')",
            name="ck_product_nutrients_unit",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_product_nutrients_sort_order",
        ),
        Index(
            "ix_product_nutrients_product_sort",
            "product_id",
            "sort_order",
            "nutrient_id",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    nutrient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("nutrients.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    amount_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ExpertComment(Base):
    __tablename__ = "expert_comments"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(author_label)) BETWEEN 1 AND 100",
            name="ck_expert_comments_author_label_length",
        ),
        CheckConstraint(
            "char_length(btrim(content)) BETWEEN 1 AND 2000",
            name="ck_expert_comments_content_length",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_expert_comments_sort_order",
        ),
        Index(
            "ix_expert_comments_product_active_sort",
            "product_id",
            "is_active",
            "sort_order",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_label: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PurchaseLink(Base):
    __tablename__ = "purchase_links"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(provider_name)) BETWEEN 1 AND 100",
            name="ck_purchase_links_provider_name_length",
        ),
        CheckConstraint(
            "char_length(url) BETWEEN 9 AND 2048",
            name="ck_purchase_links_url_length",
        ),
        CheckConstraint(
            "url ~ '^https://[^[:space:]#]+$'",
            name="ck_purchase_links_url_https",
        ),
        CheckConstraint(
            "url !~ '^https://[^/]*@'",
            name="ck_purchase_links_url_no_userinfo",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_purchase_links_sort_order",
        ),
        Index(
            "ix_purchase_links_product_active_sort",
            "product_id",
            "is_active",
            "sort_order",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
