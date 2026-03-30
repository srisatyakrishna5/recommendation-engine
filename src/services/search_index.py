from __future__ import annotations

import logging
import re
import hashlib
from typing import TYPE_CHECKING

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from src.config import Settings
from src.models import DocumentInsight, ImageInsight, NeedProfile, Product
from src.services.llm import LLMGateway

if TYPE_CHECKING:
    from src.catalog import CatalogRepository

logger = logging.getLogger(__name__)

SEARCH_TEXT_FIELDS = ("tags", "use_cases", "benefits", "image_hints")


class CatalogSearchService:
    def __init__(self, settings: Settings, catalog_repository: CatalogRepository, llm_gateway: LLMGateway) -> None:
        self.settings = settings
        self.catalog_repository = catalog_repository
        self.llm_gateway = llm_gateway

    def search_products(
        self,
        query: str,
        need_profile: NeedProfile,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
        search_expansion: dict[str, list[str]] | None = None,
        limit: int = 8,
    ) -> tuple[list[Product], str]:
        expansion = search_expansion or {"tags": [], "use_cases": [], "benefits": [], "image_hints": []}
        if not self.settings.azure_search_ready:
            return [], "azure-datastore-unavailable (not-configured)"

        try:
            products = self._search_azure(query, need_profile, image_insight, document_insight, expansion, limit)
            if products:
                return products, "azure-ai-search"
            return [], "azure-ai-search-no-results"
        except Exception as exc:
            logger.warning("Azure AI Search query failed: %s", exc)
            return [], f"azure-datastore-unavailable ({type(exc).__name__})"
        
    def sync_catalog(self) -> tuple[bool, str]:
        products = self.catalog_repository.load_products()
        if not self.settings.azure_search_ready:
            return False, "Azure AI Search is not configured. Local catalog remains active."
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            index = self._ensure_index()
            field_types = self._field_type_map(index)
            client = SearchClient(
                endpoint=self.settings.azure_search_endpoint,
                index_name=self.settings.azure_search_index_name,
                credential=AzureKeyCredential(self.settings.azure_search_api_key),
            )

            # Delete all existing documents before re-indexing so stale
            # entries (removed/renamed products) do not linger in the index.
            existing_ids = [
                result["id"]
                for result in client.search(search_text="*", select=["id"], top=1000)
            ]
            if existing_ids:
                client.delete_documents([{"id": doc_id} for doc_id in existing_ids])
                logger.info("Deleted %d existing documents from index '%s'.", len(existing_ids), self.settings.azure_search_index_name)

            upload_payload = [
                self._product_to_search_document(product, field_types)
                for product in products
            ]

            if not upload_payload:
                return True, "Catalog is empty. Azure AI Search index was cleared and no documents were uploaded."

            client.upload_documents(upload_payload)
            return True, (
                f"Cleared {len(existing_ids)} existing entries and uploaded "
                f"{len(upload_payload)} products to Azure AI Search index "
                f"'{self.settings.azure_search_index_name}'."
            )
        except Exception as exc:
            return False, f"Azure AI Search sync failed: {exc}"

    def _search_azure(
        self,
        query: str,
        need_profile: NeedProfile,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
        search_expansion: dict[str, list[str]],
        limit: int,
    ) -> list[Product]:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.models import VectorizedQuery
        from azure.search.documents.indexes import SearchIndexClient

        # TODO: Uncomment below code to connect to Azure AI search
        # index_client = SearchIndexClient(
        #     endpoint=self.settings.azure_search_endpoint,
        #     credential=AzureKeyCredential(self.settings.azure_search_api_key),
        # )
        # index = index_client.get_index(self.settings.azure_search_index_name)
        # client = SearchClient(
        #     endpoint=self.settings.azure_search_endpoint,
        #     index_name=self.settings.azure_search_index_name,
        #     credential=AzureKeyCredential(self.settings.azure_search_api_key),
        # )

        # Build two separate query texts:
        #   - keyword_query: pre-computed LLM-expanded product-level terms for BM25
        #   - semantic_query: full rich context for the semantic reranker

        keyword_query = self._keyword_query(query, need_profile, image_insight, document_insight, search_expansion)
        rich_query = self._rich_query(query, need_profile, image_insight, document_insight)
        relaxed_query = self._relaxed_keyword_query(query, need_profile, image_insight, document_insight)
        filter_expression = self._build_filter_expression(need_profile)

        vector_queries = []
        vector = self.llm_gateway.embed_text(rich_query)
        field_types = self._field_type_map(index)
        has_vector_field = field_types.get("contentVector") == "Collection(Edm.Single)"
        if vector and has_vector_field:
            vector_queries.append(
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=max(limit, 5),
                    fields="contentVector",
                )
            )

        # TODO: Uncomment below code to execute the query to fetch products from AI search index
        # primary_results = self._execute_query(
        #     client,
        #     index,
        #     keyword_query=keyword_query,
        #     semantic_query_text=rich_query,
        #     limit=max(limit * 2, 10),
        #     vector_queries=vector_queries,
        #     filter_expression=filter_expression,
        #     allow_semantic=True,
        # )

        primary_products = self._products_from_results(primary_results)
        if len(primary_products) >= limit:
            return primary_products[:limit]

        secondary_results = self._execute_query(
            client,
            index,
            keyword_query=relaxed_query,
            semantic_query_text=relaxed_query,
            limit=max(limit * 2, 10),
            vector_queries=None,
            filter_expression=filter_expression,
            allow_semantic=False,
        )
        secondary_products = self._products_from_results(secondary_results)
        return self._merge_and_limit(primary_products, secondary_products, limit)

    def _execute_query(
        self,
        client,
        index,
        *,
        keyword_query: str,
        semantic_query_text: str,
        limit: int,
        vector_queries,
        filter_expression: str | None,
        allow_semantic: bool,
    ):
        semantic_config_names = []
        semantic_search = getattr(index, "semantic_search", None)
        if semantic_search and getattr(semantic_search, "configurations", None):
            semantic_config_names = [configuration.name for configuration in semantic_search.configurations if configuration.name]

        if semantic_config_names and allow_semantic:
            try:
                return client.search(
                    search_text=keyword_query,
                    semantic_query=semantic_query_text,
                    search_mode="any",
                    top=limit,
                    vector_queries=vector_queries or None,
                    filter=filter_expression,
                    query_type="semantic",
                    semantic_configuration_name=semantic_config_names[0],
                )
            except HttpResponseError:
                pass

        return client.search(
            search_text=keyword_query,
            search_mode="any",
            top=limit,
            vector_queries=vector_queries or None,
            filter=filter_expression,
        )

    def _products_from_results(self, results) -> list[Product]:
        products = []
        for result in results:
            products.append(
                Product.from_dict(
                    {
                        "id": result.get("id"),
                        "sku": result.get("sku"),
                        "name": result.get("name"),
                        "category": result.get("category"),
                        "description": result.get("description"),
                        "price": result.get("price", 0.0),
                        "rating": result.get("rating", 0.0),
                        "tags": result.get("tags", []),
                        "use_cases": result.get("use_cases", []),
                        "benefits": result.get("benefits", []),
                        "image_hints": result.get("image_hints", []),
                        "source": result.get("source", "azure-ai-search"),
                    }
                )
            )
        return products

    def _merge_and_limit(self, primary: list[Product], secondary: list[Product], limit: int) -> list[Product]:
        merged: list[Product] = []
        seen_ids: set[str] = set()
        for product in primary + secondary:
            if product.id in seen_ids:
                continue
            seen_ids.add(product.id)
            merged.append(product)
            if len(merged) >= limit:
                break
        return merged

    def _keyword_query(
        self,
        query: str,
        need_profile: NeedProfile,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
        expanded: dict[str, list[str]] | None = None,
    ) -> str:
        """Focused keyword text for BM25 — LLM-expanded product-level terms."""
        pieces = [self._normalize_for_search(query)]
        if expanded:
            for field_terms in expanded.values():
                pieces.extend(field_terms)
        pieces.append(" ".join(need_profile.category_hints))
        pieces.append(" ".join(need_profile.must_have_features))
        if image_insight:
            pieces.append(" ".join(image_insight.tags[:5]))
        if document_insight:
            pieces.append(" ".join(document_insight.keywords[:5]))
        compact = " ".join(piece for piece in pieces if piece).strip()
        return self._normalize_for_search(compact)

    def _rich_query(
        self,
        query: str,
        need_profile: NeedProfile,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
    ) -> str:
        """Full rich context for semantic reranking and vector embedding."""
        pieces = [
            query,
            need_profile.problem_statement,
            " ".join(need_profile.category_hints),
            " ".join(need_profile.must_have_features),
            image_insight.description if image_insight else "",
            " ".join(image_insight.tags) if image_insight else "",
            document_insight.summary if document_insight else "",
            " ".join(document_insight.keywords) if document_insight else "",
        ]
        return self._normalize_for_search(" ".join(piece for piece in pieces if piece).strip())

    def _relaxed_keyword_query(
        self,
        query: str,
        need_profile: NeedProfile,
        image_insight: ImageInsight | None,
        document_insight: DocumentInsight | None,
    ) -> str:
        core = [
            self._normalize_for_search(query),
            self._normalize_for_search(need_profile.problem_statement),
            " ".join(need_profile.must_have_features[:8]),
        ]
        if image_insight:
            core.append(" ".join(image_insight.tags[:4]))
        if document_insight:
            core.append(" ".join(document_insight.keywords[:4]))
        relaxed = " ".join(piece for piece in core if piece)
        return self._normalize_for_search(relaxed)

    def _build_filter_expression(self, need_profile: NeedProfile) -> str | None:
        if need_profile.price_cap is None:
            return None
        cap = max(0.0, float(need_profile.price_cap))
        # Give retrieval slight tolerance above stated cap to avoid over-pruning.
        tolerant_cap = round(cap * 1.1, 2)
        return f"price ge 0 and price le {tolerant_cap}"

    def _normalize_for_search(self, text: str) -> str:
        lowered = (text or "").lower()
        lowered = re.sub(r"[^a-z0-9$+\-\s]", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered).strip()
        return lowered

    def _ensure_index(self) -> None:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SearchableField,
            SemanticConfiguration,
            SemanticField,
            SemanticPrioritizedFields,
            SemanticSearch,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        index_client = SearchIndexClient(
            endpoint=self.settings.azure_search_endpoint,
            credential=AzureKeyCredential(self.settings.azure_search_api_key),
        )
        try:
            return index_client.get_index(self.settings.azure_search_index_name)
        except ResourceNotFoundError:
            pass

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="sku", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="name", type=SearchFieldDataType.String),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchableField(name="tags", type=SearchFieldDataType.String),
            SearchableField(name="use_cases", type=SearchFieldDataType.String),
            SearchableField(name="benefits", type=SearchFieldDataType.String),
            SearchableField(name="image_hints", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="source", type=SearchFieldDataType.String),
            SimpleField(name="price", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="rating", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SearchField(
                name="contentVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="default-vector-profile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-hnsw",
                )
            ],
        )
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default-semantic",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="name"),
                        content_fields=[SemanticField(field_name="description"), SemanticField(field_name="content")],
                        keywords_fields=[SemanticField(field_name="tags")],
                    ),
                )
            ]
        )
        
        # TODO: Uncomment the below code to create index with the defined fields and configurations
        # index = SearchIndex(
        #     name=self.settings.azure_search_index_name,
        #     fields=fields,
        #     vector_search=vector_search,
        #     semantic_search=semantic_search,
        # )
        # return index_client.create_index(index)

    def _field_type_map(self, index) -> dict[str, str]:
        return {field.name: str(field.type) for field in getattr(index, "fields", [])}

    def _product_to_search_document(self, product: Product, field_types: dict[str, str]) -> dict[str, object]:
        document: dict[str, object] = {}
        raw = product.to_dict()
        for field_name, value in raw.items():
            field_type = field_types.get(field_name)
            if field_type is None:
                continue
            if field_name in SEARCH_TEXT_FIELDS:
                if field_type == "Collection(Edm.String)":
                    document[field_name] = value
                else:
                    document[field_name] = self._join_text_list(value)
                continue
            document[field_name] = value

        # Azure AI Search document keys only allow letters, digits, underscore, dash, and equals.
        # Keep catalog IDs unchanged in storage, but sanitize the search-index key during upload.
        if "id" in document:
            document["id"] = self._sanitize_document_key(str(document["id"]))

        if "content" in field_types:
            document["content"] = product.searchable_text

        if field_types.get("contentVector") == "Collection(Edm.Single)":
            embedding = self.llm_gateway.embed_text(product.searchable_text)
            if embedding:
                document["contentVector"] = embedding

        return document

    def _sanitize_document_key(self, key: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_\-=]", "-", (key or "").strip())
        cleaned = re.sub(r"-+", "-", cleaned).strip("-")
        if not cleaned:
            digest = hashlib.sha1((key or "").encode("utf-8")).hexdigest()[:12]
            return f"doc-{digest}"
        return cleaned

    def _join_text_list(self, value) -> str:
        if isinstance(value, list):
            return " | ".join(str(item).strip() for item in value if str(item).strip())
        return str(value or "")
