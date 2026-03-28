from __future__ import annotations

import json
import logging
import re

from src.config import Settings
from src.models import DocumentInsight, ImageInsight, NeedProfile, Product

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts — kept as module-level constants for readability
# ---------------------------------------------------------------------------

_INTERPRET_SYSTEM = """\
You are the Need-Interpreter agent of a product recommendation engine.
Your job is to deeply understand what the user truly needs and translate it into \
a structured need profile that drives catalog search and ranking.

CORE RULES:
1. Think about the *underlying intent*, not just the literal words.
   - "I want to talk to my friend overseas" → the user needs a communication device (mobile phone, tablet, or laptop with calling capability).
   - "My floor is always dirty" → the user needs cleaning products (vacuum, mop, floor cleaner).
   - "I want to capture memories on my trip" → the user needs a camera, smartphone with good camera, or action camera.
   - "Something for my morning routine" → could mean grooming, fitness, kitchen, or coffee products — pick all plausible categories.
   - "Gift for a tech-savvy teenager" → gaming, headphones, wearables, tablets.

2. ALWAYS populate category_hints with at least one likely product category.
   Map the user's intent to concrete product categories even when the query is vague or indirect.

3. ALWAYS populate must_have_features with keywords that should appear in matching products.

4. Detect budget signals:
   - Explicit: "under $50", "cheap", "affordable", "budget" → cost-effective
   - Implicit: "best money can buy", "premium", "top-of-the-line" → premium
   - Gift context: "gift for mom" with no price signal → balanced
   - Comparison context: "compare X vs Y" → balanced (user is evaluating)

5. Handle multi-intent queries:
   - "I need something to clean the kitchen AND deal with pet hair" → two category hints (Kitchen Cleaning, Pet Hair), combined problem_statement.
   - "Laptop for work and gaming" → two feature sets combined.

6. When an image is provided (via image_insight), use the visual context to refine categories.
   - Image of a messy kitchen → Kitchen Cleaning products.
   - Image of a person running → Fitness, Running Shoes, Sportswear.
   - Image of a broken phone screen → Mobile Phones, Phone Accessories.

7. When a document is provided (via document_summary/keywords), treat it as additional context for the need.

8. user_priority should reflect:
   - "performance" when the user values effectiveness, speed, or quality above cost.
   - "value" when the user wants the best bang for the buck.
   - "balanced" as the default when no strong signal either way.

9. CRITICAL — distinguish WANTING a product vs wanting an ACCESSORY or COMPLEMENT for a product:
   - "need something for charging my phone" → user wants a charger/cable (Electronics, Accessories), NOT a phone.
   - "case for my laptop" → user wants a laptop case/sleeve (Accessories), NOT a laptop.
   - "screen protector for tablet" → user wants a screen protector (Accessories), NOT a tablet.
   - "ink for my printer" → user wants ink cartridges (Office Supplies), NOT a printer.
   - "food for my dog" → user wants pet food (Pet Supplies), NOT a dog.
   Focus on WHAT THE USER IS LOOKING TO BUY, not the device/item they already own.
   The category_hints must reflect the product they want to purchase.

SEARCH EXPANSION:
Also generate product-catalog search terms that would appear in matching products.
For each field, produce 5-8 short, specific terms:
- tags: product tags and keywords (e.g. "wireless", "portable", "USB-C")
- use_cases: typical use case descriptions (e.g. "desk charging", "travel")
- benefits: product benefit terms (e.g. "fast charging", "durable")
- image_hints: visual description terms (e.g. "charging pad", "power bank")

Return compact JSON with exactly these keys:
  problem_statement, budget_preference, price_cap, category_hints, must_have_features, user_priority,
  search_terms (object with keys: tags, use_cases, benefits, image_hints)
"""

_EXPLAIN_SYSTEM = """\
You are a knowledgeable shopping advisor for a product recommendation engine.
Your task is to explain why the selected products were recommended and help the user make a confident buying decision.

RULES:
0. Stay strictly grounded in the provided products payload. Do not invent brands, specs, prices, warranties, or capabilities that are not present in the payload.
1. The summary should be 2-3 sentences that directly address the user's original need and explain how the recommended products solve it.
2. guidance is a list of 2-4 actionable, practical tips — NOT generic filler.
    - Return one tip per list item.
    - Do NOT combine multiple tips in a single string.
    - Do NOT prefix tips with '-', '*', or numbering.
    - Keep normal sentence case and punctuation.
   Good: "The XYZ Vacuum has a HEPA filter ideal for allergy sufferers — pair it with replacement filters for long-term savings."
   Bad: "Consider your needs carefully before purchasing."
3. per_product maps each product ID to:
   - rationale: WHY this product fits the user's specific need (reference their query/context).
   - caution: Honest limitations or trade-offs (e.g. "battery life may not last a full day with heavy use").
   - buying_tip: A concrete, actionable tip (e.g. "Buy the 256GB model if you plan to store photos locally").
4. If the user uploaded an image, reference what the image showed and how the product relates.
5. If the user has budget constraints, mention price-to-value ratio.
6. Compare products briefly when there are multiple recommendations so the user understands trade-offs.
7. If details are uncertain, acknowledge uncertainty briefly instead of guessing.

Return JSON with keys: summary, guidance (list of strings), per_product (dict of product_id → {rationale, caution, buying_tip}).
"""

_IMAGE_MATCH_SYSTEM = """\
You are an image-to-product matching agent. You receive Azure Vision analysis (description + tags) \
of a user-uploaded image, plus a shortlist of catalog products.

Your job is to determine which products are relevant to what the image shows.

MATCHING RULES:
1. Consider BOTH visual similarity AND functional relevance:
   - Image of a dirty floor → match floor cleaners, vacuums, mops (functional match).
   - Image of a laptop → match laptops, laptop bags, laptop stands (visual + functional).
   - Image of someone cooking → match kitchen tools, cookware, recipe books.
   - Image of a broken item → match replacement parts, repair tools, or replacement products.
2. Think about what the user likely WANTS based on the image context:
   - Image of a cluttered desk → organization products, desk accessories.
   - Image of a pet → pet supplies, grooming tools, pet-hair cleaning products.
3. Be inclusive when there's reasonable relevance, but exclude clearly unrelated products.
4. If NO products are a reasonable match, return an empty list — do not force matches.

Return JSON with:
  matching_product_ids: list of product IDs that match
  matching_reason: brief explanation of why these products match the image context
"""


class LLMGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = self._build_client()

    def _build_client(self):
        if not self.settings.azure_openai_ready:
            return None
        try:
            from openai import AzureOpenAI

            return AzureOpenAI(
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                azure_endpoint=self.settings.azure_openai_endpoint,
            )
        except Exception:
            return None

    # -- Query interpretation (need profile + search expansion in one call) --

    def interpret_query(
        self,
        query: str,
        transcript: str | None,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
        catalog_categories: list[str] | None = None,
    ) -> tuple[NeedProfile, dict[str, list[str]]]:
        """Interpret the user query into a structured need profile and search expansion terms.

        Returns (NeedProfile, search_expansion) where search_expansion has keys:
        tags, use_cases, benefits, image_hints — each a list of short terms.
        """
        empty_expansion: dict[str, list[str]] = {"tags": [], "use_cases": [], "benefits": [], "image_hints": []}
        normalized_query = self._normalize_query_text(query or transcript or "")
        bare_profile = NeedProfile(
            problem_statement=normalized_query or "Find products that match the user's need.",
            budget_preference="balanced",
            price_cap=None,
        )
        if self._client is None:
            logger.warning("Azure OpenAI is not configured — returning heuristic profile.")
            profile = self._heuristic_need_profile(normalized_query, image_insight, document_insight)
            return profile, self._normalize_search_expansion(empty_expansion, profile, image_insight, document_insight)

        system_prompt = _INTERPRET_SYSTEM
        if catalog_categories:
            system_prompt += (
                f"\nThe product catalog contains these categories: {', '.join(catalog_categories)}. "
                "Pick category_hints only from this list or close variants."
            )

        user_prompt = json.dumps(
            {
                "query": normalized_query,
                "transcript": transcript,
                "image_insight": image_insight.description if image_insight else None,
                "image_tags": image_insight.tags if image_insight else [],
                "document_summary": document_insight.summary if document_insight else None,
                "document_keywords": document_insight.keywords if document_insight else [],
            },
            indent=2,
        )
        try:
            response = self._client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            payload = json.loads(response.choices[0].message.content)
            profile = NeedProfile(
                problem_statement=str(payload.get("problem_statement") or bare_profile.problem_statement),
                budget_preference=str(payload.get("budget_preference") or "balanced"),
                price_cap=float(payload["price_cap"]) if payload.get("price_cap") not in (None, "") else None,
                category_hints=list(payload.get("category_hints") or []),
                must_have_features=list(payload.get("must_have_features") or []),
                user_priority=str(payload.get("user_priority") or "balanced"),
            )
            search_terms = payload.get("search_terms") or {}
            expansion = {
                "tags": list(search_terms.get("tags") or []),
                "use_cases": list(search_terms.get("use_cases") or []),
                "benefits": list(search_terms.get("benefits") or []),
                "image_hints": list(search_terms.get("image_hints") or []),
            }
            profile = self._normalize_need_profile(profile, normalized_query)
            expansion = self._normalize_search_expansion(expansion, profile, image_insight, document_insight)
            return profile, expansion
        except Exception as exc:
            logger.warning("LLM interpret-query call failed: %s — returning heuristic profile.", exc)
            profile = self._heuristic_need_profile(normalized_query, image_insight, document_insight)
            return profile, self._normalize_search_expansion(empty_expansion, profile, image_insight, document_insight)

    # -- Recommendation explanation ------------------------------------------

    def explain_recommendations(
        self,
        need_profile: NeedProfile,
        recommendations: list[Product],
        transcript: str | None,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
    ) -> dict[str, object]:
        empty: dict[str, object] = {
            "summary": "Catalog-backed recommendations are ready.",
            "guidance": [],
            "per_product": {},
        }
        if self._client is None or not recommendations:
            return empty

        user_prompt = json.dumps(
            {
                "need_profile": need_profile.to_dict(),
                "transcript": transcript,
                "image_insight": image_insight.description if image_insight else None,
                "document_summary": document_insight.summary if document_insight else None,
                "products": [product.to_dict() for product in recommendations],
            },
            indent=2,
        )
        try:
            response = self._client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _EXPLAIN_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
            payload = json.loads(response.choices[0].message.content)
            return self._normalize_explanation_payload(payload, recommendations, need_profile)
        except Exception as exc:
            logger.warning("LLM explain-recommendations call failed: %s", exc)
            return self._deterministic_explanation(recommendations, need_profile)

    # -- Image-to-product matching -------------------------------------------

    def match_products_to_image(self, image_insight: ImageInsight, products: list[Product]) -> list[str]:
        if not products:
            return []
        if self._client is None:
            logger.warning("Azure OpenAI is not configured — cannot match products to image.")
            return self._heuristic_image_match(image_insight, products)

        user_prompt = json.dumps(
            {
                "image_description": image_insight.description,
                "image_tags": image_insight.tags,
                "products": [product.to_dict() for product in products],
            },
            indent=2,
        )
        try:
            response = self._client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _IMAGE_MATCH_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            )
            payload = json.loads(response.choices[0].message.content)
            matches = payload.get("matching_product_ids")
            if not isinstance(matches, list):
                return self._heuristic_image_match(image_insight, products)
            valid_ids = {product.id for product in products}
            normalized = [str(pid) for pid in matches if str(pid) in valid_ids]
            return normalized or self._heuristic_image_match(image_insight, products)
        except Exception as exc:
            logger.warning("LLM image-match call failed: %s", exc)
            return self._heuristic_image_match(image_insight, products)

    def _normalize_query_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", (text or "").strip())
        text = re.sub(r"[^\w\s$.,\-+/]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _heuristic_need_profile(
        self,
        query: str,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
    ) -> NeedProfile:
        lower = (query or "").lower()
        budget_preference = "balanced"
        if any(token in lower for token in ["cheap", "budget", "affordable", "low cost", "under $"]):
            budget_preference = "cost-effective"
        elif any(token in lower for token in ["premium", "best", "high-end", "top of the line", "flagship"]):
            budget_preference = "premium"

        price_cap = None
        match = re.search(r"(?:under|below|less than)\s*\$?\s*(\d+(?:\.\d+)?)", lower)
        if match:
            try:
                price_cap = float(match.group(1))
            except Exception:
                price_cap = None

        features: list[str] = []
        features.extend(re.findall(r"[a-z0-9][a-z0-9\-]{2,}", lower)[:8])
        if image_insight:
            features.extend(image_insight.tags[:4])
        if document_insight:
            features.extend(document_insight.keywords[:4])

        dedup_features = []
        seen = set()
        for item in features:
            token = item.strip().lower()
            if not token or token in seen:
                continue
            seen.add(token)
            dedup_features.append(token)
            if len(dedup_features) >= 10:
                break

        return NeedProfile(
            problem_statement=query or "Find products that match the user's need.",
            budget_preference=budget_preference,
            price_cap=price_cap,
            category_hints=[],
            must_have_features=dedup_features,
            user_priority="balanced",
        )

    def _normalize_need_profile(self, profile: NeedProfile, query: str) -> NeedProfile:
        budget = (profile.budget_preference or "balanced").strip().lower()
        if budget not in {"cost-effective", "balanced", "premium"}:
            budget = "balanced"

        priority = (profile.user_priority or "balanced").strip().lower()
        if priority not in {"value", "balanced", "performance"}:
            priority = "balanced"

        category_hints = self._clean_list(profile.category_hints, limit=6)
        must_have_features = self._clean_list(profile.must_have_features, limit=12)
        problem_statement = self._normalize_query_text(profile.problem_statement or query)
        if not problem_statement:
            problem_statement = query or "Find products that match the user's need."

        price_cap = profile.price_cap
        if price_cap is not None and price_cap <= 0:
            price_cap = None

        return NeedProfile(
            problem_statement=problem_statement,
            budget_preference=budget,
            price_cap=price_cap,
            category_hints=category_hints,
            must_have_features=must_have_features,
            user_priority=priority,
        )

    def _normalize_search_expansion(
        self,
        expansion: dict[str, list[str]],
        profile: NeedProfile,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
    ) -> dict[str, list[str]]:
        normalized = {
            "tags": self._clean_list(expansion.get("tags", []), limit=10),
            "use_cases": self._clean_list(expansion.get("use_cases", []), limit=10),
            "benefits": self._clean_list(expansion.get("benefits", []), limit=10),
            "image_hints": self._clean_list(expansion.get("image_hints", []), limit=10),
        }

        if not normalized["tags"]:
            normalized["tags"] = self._clean_list(profile.must_have_features, limit=8)
        if profile.category_hints:
            normalized["use_cases"] = self._clean_list(normalized["use_cases"] + profile.category_hints, limit=10)
        if image_insight:
            normalized["image_hints"] = self._clean_list(normalized["image_hints"] + image_insight.tags, limit=10)
        if document_insight:
            normalized["benefits"] = self._clean_list(normalized["benefits"] + document_insight.keywords, limit=10)
        return normalized

    def _normalize_explanation_payload(
        self,
        payload: dict[str, object],
        recommendations: list[Product],
        need_profile: NeedProfile,
    ) -> dict[str, object]:
        fallback = self._deterministic_explanation(recommendations, need_profile)

        summary = self._normalize_query_text(str(payload.get("summary") or fallback["summary"]))
        if not summary:
            summary = str(fallback["summary"])

        guidance_raw = payload.get("guidance")
        guidance = []
        if isinstance(guidance_raw, list):
            guidance = self._normalize_guidance_items([str(item) for item in guidance_raw], limit=4)
        if not guidance:
            guidance = list(fallback["guidance"])

        valid_ids = {product.id for product in recommendations}
        per_product_payload = payload.get("per_product")
        normalized_per_product: dict[str, dict[str, str]] = {}
        if isinstance(per_product_payload, dict):
            for product_id, raw_entry in per_product_payload.items():
                pid = str(product_id)
                if pid not in valid_ids or not isinstance(raw_entry, dict):
                    continue
                normalized_per_product[pid] = {
                    "rationale": self._normalize_query_text(str(raw_entry.get("rationale") or "")),
                    "caution": self._normalize_query_text(str(raw_entry.get("caution") or "")),
                    "buying_tip": self._normalize_query_text(str(raw_entry.get("buying_tip") or "")),
                }

        for product in recommendations:
            if product.id not in normalized_per_product:
                normalized_per_product[product.id] = {
                    "rationale": f"{product.name} aligns with '{need_profile.problem_statement}' and is grounded in the catalog.",
                    "caution": "",
                    "buying_tip": f"Compare {product.name}'s key features and price against your top priority before purchase.",
                }
            else:
                entry = normalized_per_product[product.id]
                if not entry["rationale"]:
                    entry["rationale"] = f"{product.name} aligns with '{need_profile.problem_statement}' and is grounded in the catalog."
                if not entry["buying_tip"]:
                    entry["buying_tip"] = f"Compare {product.name}'s key features and price against your top priority before purchase."

        return {
            "summary": summary,
            "guidance": guidance,
            "per_product": normalized_per_product,
        }

    def _deterministic_explanation(self, recommendations: list[Product], need_profile: NeedProfile) -> dict[str, object]:
        if not recommendations:
            return {
                "summary": "Catalog-backed recommendations are ready.",
                "guidance": [],
                "per_product": {},
            }

        top_names = ", ".join(product.name for product in recommendations[:2])
        summary = (
            f"These recommendations target '{need_profile.problem_statement}' and are grounded in Azure AI Search results. "
            f"Top matches include {top_names}."
        )
        guidance = [
            "Compare feature coverage across the top products before purchasing.",
            "Use your budget and priority (value, balance, or performance) to choose the best fit.",
        ]
        per_product: dict[str, dict[str, str]] = {}
        for product in recommendations:
            per_product[product.id] = {
                "rationale": f"{product.name} matches your request and appears in the indexed catalog results.",
                "caution": "Verify any accessory or compatibility requirements before checkout.",
                "buying_tip": f"Shortlist {product.name} and compare final price, rating, and included features.",
            }
        return {"summary": summary, "guidance": guidance, "per_product": per_product}

    def _heuristic_image_match(self, image_insight: ImageInsight, products: list[Product]) -> list[str]:
        query_terms = set(self._clean_list([image_insight.description] + image_insight.tags, limit=14))
        if not query_terms:
            return []

        scored: list[tuple[int, str]] = []
        for product in products:
            haystack = product.searchable_text.lower()
            overlap = sum(1 for term in query_terms if term and term in haystack)
            if overlap > 0:
                scored.append((overlap, product.id))

        scored.sort(reverse=True)
        return [product_id for _, product_id in scored[: len(products)]]

    def _clean_list(self, values: list[str], limit: int) -> list[str]:
        cleaned: list[str] = []
        seen = set()
        for raw in values:
            token = self._normalize_query_text(str(raw)).lower()
            if len(token) < 2 or token in seen:
                continue
            seen.add(token)
            cleaned.append(token)
            if len(cleaned) >= limit:
                break
        return cleaned

    def _normalize_guidance_items(self, values: list[str], limit: int) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for raw in values:
            text = re.sub(r"\s+", " ", str(raw or "")).strip()
            if not text:
                continue

            # Handle cases where the model packs multiple '-' bullets into one string.
            if " - " in text:
                if text.startswith("- "):
                    text = text[2:]
                candidates = [part.strip(" .") for part in re.split(r"\s+-\s+", text) if part.strip(" .")]
            else:
                candidates = [text.lstrip("-* ").strip()]

            for candidate in candidates:
                compact = re.sub(r"\s+", " ", candidate).strip()
                if len(compact) < 3:
                    continue
                dedupe_key = compact.lower()
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                normalized.append(compact)
                if len(normalized) >= limit:
                    return normalized

        return normalized



    # -- Embeddings ----------------------------------------------------------

    def embed_text(self, text: str) -> list[float] | None:
        if self._client is None or not self.settings.azure_openai_embedding_deployment or not text.strip():
            return None
        try:
            response = self._client.embeddings.create(
                model=self.settings.azure_openai_embedding_deployment,
                input=text,
            )
            return list(response.data[0].embedding)
        except Exception:
            return None
