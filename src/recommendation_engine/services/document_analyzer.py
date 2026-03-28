from __future__ import annotations

import re

from ..config import Settings
from ..models import DocumentInsight


class DocumentAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
