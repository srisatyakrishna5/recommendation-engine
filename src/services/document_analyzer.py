from __future__ import annotations

import logging
import re

from src.config import Settings
from src.models import DocumentInsight, Product

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze_pdf_bytes_for_product_load(self, raw_bytes: bytes) -> list[Product]:
        document_intelligence_client = DocumentIntelligenceClient(
            endpoint=self.settings.document_intelligence_endpoint,
            credential=AzureKeyCredential(self.settings.document_intelligence_key),
        )
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            AnalyzeDocumentRequest(bytes_source=raw_bytes),
        )
        result = poller.result()
        return self._extract_products_from_tables(result)

    def _extract_products_from_tables(self, result) -> list[Product]:
        products = []
        total_tables = len(result.tables) if hasattr(result, "tables") else 0
        logger.info("Total tables detected: %d", total_tables)

        for table_idx, table in enumerate(result.tables):
            try:
                logger.debug(
                    "Processing table %d (%dx%d)",
                    table_idx,
                    table.row_count,
                    table.column_count,
                )

                # Build a row -> {col_index: content} map
                rows: dict[int, dict[int, str]] = {}
                for cell in table.cells:
                    rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content

                # Attempt to parse as key-value pairs
                # Strategy: Look for "id" field to detect product boundaries in large tables
                current_product = {}
                products_in_table = []
                
                for row_idx in sorted(rows):
                    row = rows[row_idx]
                    raw_key = row.get(0, "").strip()
                    value = row.get(1, "").strip()
                    
                    if not raw_key:
                        continue
                    
                    # Normalize key
                    normalized_key = raw_key.lower().replace(" ", "_")
                    
                    # If we see an 'id' field and already have product data, save the current product
                    if normalized_key == "id" and current_product and "name" in current_product:
                        products_in_table.append(current_product)
                        current_product = {}
                    
                    current_product[normalized_key] = value
                
                # Don't forget the last product
                if current_product:
                    products_in_table.append(current_product)
                
                logger.debug("Found %d product(s) in table %d", len(products_in_table), table_idx)
                
                # Create Product objects from extracted data
                for prod_idx, table_json in enumerate(products_in_table):
                    try:
                        table_json.setdefault("id", f"product-{table_idx}-{prod_idx}")
                        table_json.setdefault("name", f"Extracted Product {table_idx}-{prod_idx}")
                        
                        product = Product.from_dict(table_json)
                        products.append(product)
                        logger.debug("Extracted product: %s", product.name)
                    except Exception as e:
                        logger.warning("Failed to create product from table %d row %d: %s", table_idx, prod_idx, e)
                
            except Exception as e:
                logger.exception("Error processing table %d: %s", table_idx, e)
                continue

        logger.info("Summary: extracted %d total products", len(products))
        return products

    def analyze_pdf(self, file_name: str, raw_bytes: bytes | None) -> DocumentInsight | None:
        if not raw_bytes:
            return None

        if not self.settings.document_intelligence_ready:
            return None

        extracted_text = self._try_azure_analysis(raw_bytes)
        if not extracted_text:
            return None

        cleaned = re.sub(r"\s+", " ", extracted_text).strip()
        if not cleaned:
            cleaned = "The document was uploaded but no readable text was extracted."
        summary = cleaned[:600] + ("..." if len(cleaned) > 600 else "")
        keywords = self._extract_keywords(cleaned)
        return DocumentInsight(
            file_name=file_name,
            summary=summary,
            keywords=keywords,
            extracted_text=cleaned,
        )

    def _try_azure_analysis(self, raw_bytes: bytes) -> str:
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            client = DocumentIntelligenceClient(
                endpoint=self.settings.document_intelligence_endpoint,
                credential=AzureKeyCredential(self.settings.document_intelligence_key),
            )
            poller = client.begin_analyze_document(
                "prebuilt-layout",
                body=raw_bytes,
                content_type="application/pdf",
            )
            result = poller.result()
            paragraphs = [paragraph.content for paragraph in getattr(result, "paragraphs", []) if paragraph.content]
            return "\n".join(paragraphs)
        except Exception:
            return ""

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower())
        ignore = {"with", "that", "this", "from", "your", "have", "into", "will", "about", "there"}
        seen: list[str] = []
        for word in words:
            if word in ignore or word in seen:
                continue
            seen.append(word)
            if len(seen) == 8:
                break
        return seen
