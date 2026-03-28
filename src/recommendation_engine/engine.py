from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .catalog import CatalogRepository
from .config import Settings
from .models import (
    AgentTraceStep,
    CatalogIngestionResult,
    DocumentInsight,
    ImageInsight,
    NeedProfile,
    Product,
    Recommendation,
    RecommendationBundle,
)
from .services import CatalogSearchService, DocumentAnalyzer, ImageCatalogMatcher, LLMGateway, SpeechTranscriber


# ---------------------------------------------------------------------------
# Internal pipeline context — carries state between pipeline stages
# ---------------------------------------------------------------------------

@dataclass
class _PipelineContext:
    query: str
    limit: int
    trace: list[AgentTraceStep] = field(default_factory=list)
    normalized_query: str = ""
    transcript: str | None = None
    image_insight: ImageInsight | None = None
    document_insight: DocumentInsight | None = None
    need_profile: NeedProfile | None = None
    search_expansion: dict[str, list[str]] = field(default_factory=dict)
    candidates: list[Product] = field(default_factory=list)
    ranked: list[Product] = field(default_factory=list)
    search_mode: str = "not-run"

    @property
    def effective_query(self) -> str:
        return self.normalized_query or self.query or self.transcript or ""


# ---------------------------------------------------------------------------
# Minimum value score for a product to be considered a viable recommendation
# ---------------------------------------------------------------------------
_MIN_VIABLE_SCORE = 4.0


@dataclass
class RecommendationEngine:
    settings: Settings

    def __post_init__(self) -> None:
        self.catalog_repository = CatalogRepository(self.settings)
        self.llm_gateway = LLMGateway(self.settings)
        self.image_matcher = ImageCatalogMatcher(self.settings)
        self.document_analyzer = DocumentAnalyzer(self.settings)
        self.speech_transcriber = SpeechTranscriber(self.settings)
        self.catalog_search = CatalogSearchService(self.settings, self.catalog_repository, self.llm_gateway)

    # -- Public API ----------------------------------------------------------

    def catalog_rows(self) -> list[dict[str, object]]:
        return [product.to_dict() for product in self.catalog_repository.load_products()]

    def import_catalog(self, filename: str, raw_bytes: bytes, replace: bool = True) -> CatalogIngestionResult:
        return self.catalog_repository.import_catalog(filename, raw_bytes, replace=replace)

    def add_manual_product(
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
    ) -> None:
        product = self.catalog_repository.create_manual_product(
            name=name,
            category=category,
            description=description,
            price=price,
            rating=rating,
            tags=tags,
            use_cases=use_cases,
            benefits=benefits,
        )
        self.catalog_repository.add_product(product)

    def sync_catalog_to_search(self) -> tuple[bool, str]:
        return self.catalog_search.sync_catalog()

    def recommend(
        self,
        *,
        query: str,
        audio_bytes: bytes | None = None,
        audio_name: str | None = None,
        image_bytes: bytes | None = None,
        image_name: str | None = None,
        doc_bytes: bytes | None = None,
        doc_name: str | None = None,
        limit: int = 4,
    ) -> RecommendationBundle:
        ctx = _PipelineContext(query=query, limit=limit)

        self._stage_transcribe(ctx, audio_bytes, audio_name)
        self._stage_analyze_image(ctx, image_bytes, image_name)
        self._stage_analyze_document(ctx, doc_bytes, doc_name)
        self._stage_preprocess_query(ctx)

        if image_bytes and not ctx.image_insight:
            return self._no_match_bundle(ctx,
                summary="I could not analyze the uploaded image with Azure Vision, so I cannot find matching products from the catalog.",
                guidance=[
                    "Verify that Azure AI Vision is configured and reachable.",
                    "Upload a clearer image that shows the product or component directly.",
                ],
            )

        self._stage_interpret(ctx)

        self._stage_retrieve_candidates(ctx)

        if ctx.search_mode.startswith("azure-datastore-unavailable"):
            return self._no_match_bundle(
                ctx,
                summary=(
                    "I cannot retrieve products from the catalog because the Azure AI Search datastore "
                    "is unavailable right now."
                ),
                guidance=[
                    "Verify AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, and AZURE_SEARCH_INDEX_NAME.",
                    "Confirm the Azure AI Search service and index are reachable.",
                    "Retry after the datastore is available.",
                ],
            )

        if not ctx.candidates:
            return self._no_match_bundle(ctx,
                summary=(
                    "I could not find any products in Azure AI Search that match your request. "
                    f"Try rephrasing the request '{ctx.need_profile.problem_statement}' with specific product terms."
                ),
                guidance=[
                    "Try including product type, key features, and budget in your query.",
                    "Ask an admin to sync or refresh the Azure AI Search index from the Catalog tab if needed.",
                ],
            )

        self._stage_rank_and_filter(ctx)

        if not ctx.ranked:
            return self._no_match_bundle(ctx,
                summary=(
                    f"The catalog has some loosely related products, but none are a strong match "
                    f"for '{ctx.need_profile.problem_statement}'."
                ),
                guidance=[
                    "Try a narrower request with concrete product requirements.",
                    "Ask an admin to update and re-sync catalog data to Azure AI Search if relevant products are missing.",
                ],
            )

        if ctx.image_insight:
            self._stage_image_filter(ctx)
            if not ctx.ranked:
                return self._no_match_bundle(ctx,
                    summary="I could not find any catalog products that match the uploaded image.",
                    guidance=[
                        "Try uploading a more direct image of the product or component.",
                        "Expand the catalog with products that include richer image hints, tags, or component descriptions.",
                    ],
                )

        return self._stage_explain_and_build(ctx)

    # -- Pipeline stages -----------------------------------------------------

    def _stage_transcribe(self, ctx: _PipelineContext, audio_bytes: bytes | None, audio_name: str | None) -> None:
        ctx.transcript = self.speech_transcriber.transcribe(audio_bytes, audio_name)
        if ctx.transcript:
            ctx.trace.append(AgentTraceStep("SpeechInput", "completed", "Speech transcribed via Azure Speech Service."))
        elif audio_bytes:
            ctx.trace.append(AgentTraceStep("SpeechInput", "fallback", "Audio provided but no transcript generated."))

    def _stage_analyze_image(self, ctx: _PipelineContext, image_bytes: bytes | None, image_name: str | None) -> None:
        ctx.image_insight = self.image_matcher.analyze(image_name, image_bytes)
        if ctx.image_insight:
            ctx.trace.append(AgentTraceStep("VisionAnalyzer", "completed", "Derived image caption and tags for catalog matching."))
        elif image_bytes:
            ctx.trace.append(AgentTraceStep("VisionAnalyzer", "failed", "Azure Vision did not return usable image analysis."))

    def _stage_analyze_document(self, ctx: _PipelineContext, doc_bytes: bytes | None, doc_name: str | None) -> None:
        ctx.document_insight = self.document_analyzer.analyze_pdf(doc_name or "document.pdf", doc_bytes)
        if ctx.document_insight:
            ctx.trace.append(AgentTraceStep("DocumentAnalyzer", "completed", f"Extracted text and keywords from '{doc_name}'."))
        elif doc_bytes:
            ctx.trace.append(AgentTraceStep("DocumentAnalyzer", "fallback", "Document provided but no usable text extracted."))

    def _stage_preprocess_query(self, ctx: _PipelineContext) -> None:
        base_query = ctx.query or ctx.transcript or ""
        normalized = self._normalize_query_text(base_query)
        expanded = self._expand_query_aliases(normalized)

        if ctx.document_insight and ctx.document_insight.keywords:
            doc_keywords = " ".join(ctx.document_insight.keywords[:5])
            expanded = f"{expanded} {self._normalize_query_text(doc_keywords)}".strip()

        if ctx.image_insight and ctx.image_insight.tags:
            image_tags = " ".join(ctx.image_insight.tags[:5])
            expanded = f"{expanded} {self._normalize_query_text(image_tags)}".strip()

        ctx.normalized_query = expanded
        ctx.trace.append(AgentTraceStep(
            "QueryPreprocessor",
            "completed",
            f"Normalized query for retrieval: '{ctx.normalized_query[:160]}'.",
        ))

    def _stage_interpret(self, ctx: _PipelineContext) -> None:
        ctx.need_profile, ctx.search_expansion = self.llm_gateway.interpret_query(
            ctx.effective_query, ctx.transcript, ctx.image_insight, ctx.document_insight,
        )
        ctx.trace.append(AgentTraceStep(
            "QueryInterpreter", "completed",
            f"Interpreted as '{ctx.need_profile.problem_statement}' "
            f"({ctx.need_profile.budget_preference} budget). "
            f"Expanded into {sum(len(v) for v in ctx.search_expansion.values())} search terms.",
        ))

    def _stage_retrieve_candidates(self, ctx: _PipelineContext) -> None:
        ctx.candidates, ctx.search_mode = self.catalog_search.search_products(
            query=ctx.effective_query,
            need_profile=ctx.need_profile,
            image_insight=ctx.image_insight,
            document_insight=ctx.document_insight,
            search_expansion=ctx.search_expansion,
            limit=max(ctx.limit * 2, 6),
        )
        status = "completed" if ctx.candidates else "no-match"
        detail = (
            f"Retrieved {len(ctx.candidates)} candidates via {ctx.search_mode}."
            if ctx.candidates
            else f"No products found via {ctx.search_mode}."
        )
        ctx.trace.append(AgentTraceStep("CatalogSearch", status, detail))

    def _stage_rank_and_filter(self, ctx: _PipelineContext) -> None:
        scored = []
        for position, product in enumerate(ctx.candidates):
            relevance_bonus = max(0.0, (len(ctx.candidates) - position)) * 0.5
            value = self._value_score(product, ctx.need_profile) + relevance_bonus
            scored.append((value, product))
        scored.sort(key=lambda item: item[0], reverse=True)
        ranked = [product for _, product in scored][:ctx.limit]

        ctx.ranked = [p for p in ranked if self._value_score(p, ctx.need_profile) >= _MIN_VIABLE_SCORE]
        if ctx.ranked:
            ctx.trace.append(AgentTraceStep(
                "ValueScorer", "completed",
                f"Scored and ranked {len(ctx.candidates)} candidates. Selected top {len(ctx.ranked)} products.",
            ))

    def _stage_image_filter(self, ctx: _PipelineContext) -> None:
        matched_ids = set(self.llm_gateway.match_products_to_image(ctx.image_insight, ctx.ranked))
        ctx.ranked = [p for p in ctx.ranked if p.id in matched_ids]
        if ctx.ranked:
            ctx.trace.append(AgentTraceStep(
                "ImageMatcher", "completed",
                f"Retained {len(ctx.ranked)} products matching the uploaded image.",
            ))
        else:
            ctx.trace.append(AgentTraceStep(
                "ImageMatcher", "completed",
                "No catalog products matched the image description.",
            ))

    def _stage_explain_and_build(self, ctx: _PipelineContext) -> RecommendationBundle:
        explanation = self.llm_gateway.explain_recommendations(
            need_profile=ctx.need_profile,
            recommendations=ctx.ranked,
            transcript=ctx.transcript,
            image_insight=ctx.image_insight,
            document_insight=ctx.document_insight,
        )

        per_product = explanation.get("per_product", {})
        recommendations = self._build_recommendations(ctx.ranked, ctx.need_profile, per_product)

        ctx.trace.append(AgentTraceStep("Explainer", "completed", "Generated product rationale and buying guidance."))
        ctx.trace.append(AgentTraceStep("Validator", "completed", "Verified each recommendation maps to a catalog product."))

        return RecommendationBundle(
            summary=str(explanation.get("summary") or "Catalog-backed recommendations are ready."),
            guidance=[str(item) for item in explanation.get("guidance", [])],
            recommendations=recommendations,
            need_profile=ctx.need_profile,
            trace=ctx.trace,
            search_mode=ctx.search_mode,
            transcript=ctx.transcript,
            document_insight=ctx.document_insight,
            image_insight=ctx.image_insight,
        )

    # -- Helpers -------------------------------------------------------------

    def _build_recommendations(
        self,
        ranked: list[Product],
        need_profile: NeedProfile,
        per_product: Any,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        for product in ranked:
            value = self._value_score(product, need_profile)
            metadata = per_product.get(product.id, {}) if isinstance(per_product, dict) else {}
            rationale = str(metadata.get("rationale") or "").strip()
            caution = str(metadata.get("caution") or "").strip()
            buying_tip = str(metadata.get("buying_tip") or "").strip()

            if not rationale:
                rationale = self._fallback_rationale(product, need_profile)
            if not buying_tip:
                buying_tip = self._fallback_buying_tip(product, need_profile)

            recommendations.append(Recommendation(
                product=product,
                rationale=rationale,
                caution=caution,
                buying_tip=buying_tip,
                value_score=value,
            ))
        return recommendations

    def _no_match_bundle(
        self,
        ctx: _PipelineContext,
        *,
        summary: str,
        guidance: list[str],
    ) -> RecommendationBundle:
        if ctx.need_profile is None:
            ctx.need_profile, _ = self.llm_gateway.interpret_query(
                "", ctx.transcript, ctx.image_insight, ctx.document_insight,
            )
        ctx.trace.append(AgentTraceStep(
            "Validator", "completed",
            "Returned a grounded no-match response — no catalog product could be verified.",
        ))
        return RecommendationBundle(
            summary=summary,
            guidance=guidance,
            recommendations=[],
            need_profile=ctx.need_profile,
            trace=ctx.trace,
            search_mode=ctx.search_mode,
            transcript=ctx.transcript,
            document_insight=ctx.document_insight,
            image_insight=ctx.image_insight,
        )

    @staticmethod
    def _words_overlap(text_a: str, text_b: str) -> int:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        return len(words_a & words_b)

    @staticmethod
    def _value_score(product: Product, need_profile: NeedProfile) -> float:
        score = 5.0
        score += min(product.rating, 5.0) * 0.5

        if need_profile.price_cap is not None and product.price <= need_profile.price_cap:
            score += 1.0
        if need_profile.budget_preference == "cost-effective":
            score += max(0.0, 60.0 - min(product.price, 60.0)) / 30.0
        elif need_profile.budget_preference == "premium":
            score += min(product.price, 120.0) / 80.0

        category_matched = False
        for category in need_profile.category_hints:
            cat_lower = category.lower()
            if cat_lower in product.category.lower():
                score += 4.0
                category_matched = True
            elif RecommendationEngine._words_overlap(category, product.category) > 0:
                score += 3.0
                category_matched = True
            elif RecommendationEngine._words_overlap(category, product.searchable_text) > 0:
                score += 2.0
                category_matched = True

        if need_profile.category_hints and not category_matched:
            score -= 5.0
        if not need_profile.category_hints:
            score -= 2.0

        for feature in need_profile.must_have_features:
            if feature.lower() in product.searchable_text.lower():
                score += 2.5

        return round(score, 1)

    @staticmethod
    def _normalize_query_text(text: str) -> str:
        cleaned = re.sub(r"[^\w\s$.,+\-/]", " ", (text or "").strip().lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _expand_query_aliases(text: str) -> str:
        if not text:
            return ""
        alias_map = {
            "tv": "television",
            "fridge": "refrigerator",
            "vac": "vacuum",
            "cellphone": "phone",
            "earbuds": "earphones",
            "headset": "headphones",
            "charger": "charging adapter cable",
            "lappy": "laptop",
        }
        expanded = text
        for source, target in alias_map.items():
            expanded = re.sub(rf"\b{re.escape(source)}\b", f"{source} {target}", expanded)
        return re.sub(r"\s+", " ", expanded).strip()

    @staticmethod
    def _fallback_rationale(product: Product, need_profile: NeedProfile) -> str:
        return (
            f"{product.name} aligns with '{need_profile.problem_statement}' and remains grounded in indexed catalog data."
        )

    @staticmethod
    def _fallback_buying_tip(product: Product, need_profile: NeedProfile) -> str:
        if need_profile.budget_preference == "cost-effective":
            return f"Compare {product.name} against similar options under your budget cap before checkout."
        if need_profile.budget_preference == "premium":
            return f"Check warranty and premium feature coverage to confirm {product.name} justifies the higher price."
        return f"Review key features and ratings to validate that {product.name} best matches your primary need."
