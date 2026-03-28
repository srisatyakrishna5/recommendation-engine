from __future__ import annotations

import csv
import json
import re
from io import StringIO
from pathlib import Path
from uuid import uuid4

from src.config import Settings
from src.models import CatalogIngestionResult, Product
from src.services.document_analyzer import DocumentAnalyzer


def _split_text_field(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    return [item.strip() for item in re.split(r"[|,]", value) if item and item.strip()]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or f"product-{uuid4().hex[:8]}"


class CatalogRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self._bootstrap_catalog()

    def _bootstrap_catalog(self) -> None:
        if not self.settings.catalog_path.exists() and self.settings.sample_catalog_path.exists():
            self.settings.catalog_path.write_text(
                self.settings.sample_catalog_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    def load_products(self) -> list[Product]:
        if not self.settings.catalog_path.exists():
            return []
        raw_data = json.loads(self.settings.catalog_path.read_text(encoding="utf-8"))
        return [Product.from_dict(item) for item in raw_data]
    
    def load_products_from_pdf(self, raw_bytes: bytes) -> list[Product]:
        analyzer = DocumentAnalyzer(self.settings)
        return analyzer.analyze_pdf_bytes_for_product_load(raw_bytes)

    def save_products(self, products: list[Product]) -> None:
        payload = [product.to_dict() for product in products]
        self.settings.catalog_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def import_catalog(self, filename: str, raw_bytes: bytes, replace: bool = True) -> CatalogIngestionResult:
        suffix = Path(filename).suffix.lower()
        if suffix == ".json":
            rows = json.loads(raw_bytes.decode("utf-8"))
            if not isinstance(rows, list):
                raise ValueError("JSON catalog must contain a list of product objects.")
            products = [self._product_from_row(row) for row in rows]
        elif suffix == ".csv":
            reader = csv.DictReader(StringIO(raw_bytes.decode("utf-8")))
            rows = list(reader)
            products = [self._product_from_row(row) for row in rows]
        elif suffix == ".pdf":
            products = self.load_products_from_pdf(raw_bytes)
        else:
            raise ValueError("Only CSV, JSON, and PDF catalogs are supported.")

        # Filter out non-product rows (empty names, summary/statistics rows)
        products = [
            p for p in products
            if p.name and p.name != "Unnamed product"
            and p.category not in ("Summary Statistics", "Total Products")
            and not p.name.startswith("$")
            and not p.name.replace(",", "").replace(".", "").isdigit()
        ]
        existing = [] if replace else self.load_products()
        merged = existing + products
        self.save_products(merged)
        action = "replaced" if replace else "extended"
        return CatalogIngestionResult(
            count=len(products),
            message=f"Catalog {action} with {len(products)} products.",
        )

    def add_product(self, product: Product) -> None:
        products = self.load_products()
        products.append(product)
        self.save_products(products)

    def _product_from_row(self, row: dict[str, object]) -> Product:
        # Normalize keys: lowercase, strip whitespace, replace spaces with underscores
        normalized = {
            k.strip().lower().replace(" ", "_"): v
            for k, v in row.items()
        }
        name = str(normalized.get("product_name") or normalized.get("name") or normalized.get("title") or "Unnamed product")
        product_id = str(normalized.get("id") or normalized.get("sku") or _slugify(name))
        normalized.setdefault("id", product_id)
        normalized.setdefault("sku", str(normalized.get("sku") or product_id))
        normalized.setdefault("name", name)
        normalized.setdefault("category", "General")
        normalized.setdefault("description", str(normalized.get("summary") or ""))
        normalized.setdefault("source", "uploaded-catalog")
        return Product.from_dict(normalized)

    def create_manual_product(
        self,
        *,
        name: str,
        category: str,
        description: str,
        price: float,
        rating: float,
        tags: str,
        use_cases: str,
        benefits: str,
    ) -> Product:
        product_id = _slugify(name)
        return Product(
            id=product_id,
            sku=product_id.upper().replace("-", "")[:16],
            name=name,
            category=category,
            description=description,
            price=price,
            rating=rating,
            tags=_split_text_field(tags),
            use_cases=_split_text_field(use_cases),
            benefits=_split_text_field(benefits),
            image_hints=_split_text_field(tags),
            source="manual-entry",
        )
