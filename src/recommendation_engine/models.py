from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


def _normalize_text_list(values: list[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [value.strip() for value in re.split(r"\s*\|\s*|\s*,\s*", values) if value and value.strip()]
    return [value.strip() for value in values if value and value.strip()]


@dataclass(slots=True)
class Product:
    id: str
    sku: str
    name: str
    category: str
    description: str
    price: float
    rating: float
    tags: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    image_hints: list[str] = field(default_factory=list)
    source: str = "catalog"

    @property
    def searchable_text(self) -> str:
        parts = [
            self.name,
            self.category,
            self.description,
            " ".join(self.tags),
            " ".join(self.use_cases),
            " ".join(self.benefits),
            " ".join(self.image_hints),
        ]
        return " ".join(part for part in parts if part)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "price": round(self.price, 2),
            "rating": round(self.rating, 2),
            "tags": self.tags,
            "use_cases": self.use_cases,
            "benefits": self.benefits,
            "image_hints": self.image_hints,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Product":
        return cls(
            id=str(data["id"]),
            sku=str(data.get("sku") or data["id"]),
            name=str(data["name"]),
            category=str(data.get("category", "General")),
            description=str(data.get("description", "")),
            price=float(data.get("price", 0.0)),
            rating=float(data.get("rating", 0.0)),
            tags=_normalize_text_list(data.get("tags")),
            use_cases=_normalize_text_list(data.get("use_cases")),
            benefits=_normalize_text_list(data.get("benefits")),
            image_hints=_normalize_text_list(data.get("image_hints")),
            source=str(data.get("source", "catalog")),
        )


@dataclass(slots=True)
class NeedProfile:
    problem_statement: str
    budget_preference: str
    price_cap: float | None
    category_hints: list[str] = field(default_factory=list)
    must_have_features: list[str] = field(default_factory=list)
    user_priority: str = "balanced"

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_statement": self.problem_statement,
            "budget_preference": self.budget_preference,
            "price_cap": self.price_cap,
            "category_hints": self.category_hints,
            "must_have_features": self.must_have_features,
            "user_priority": self.user_priority,
        }


@dataclass(slots=True)
class ImageInsight:
    description: str
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(slots=True)
class DocumentInsight:
    file_name: str
    summary: str
    keywords: list[str] = field(default_factory=list)
    extracted_text: str = ""


@dataclass(slots=True)
class AgentTraceStep:
    agent_name: str
    status: str
    detail: str


@dataclass(slots=True)
class Recommendation:
    product: Product
    rationale: str
    value_score: float
    caution: str = ""
    buying_tip: str = ""


@dataclass(slots=True)
class RecommendationBundle:
    summary: str
    guidance: list[str]
    recommendations: list[Recommendation]
    need_profile: NeedProfile
    trace: list[AgentTraceStep]
    search_mode: str
    transcript: str | None = None
    document_insight: DocumentInsight | None = None
    image_insight: ImageInsight | None = None


@dataclass(slots=True)
class CatalogIngestionResult:
    count: int
    message: str
