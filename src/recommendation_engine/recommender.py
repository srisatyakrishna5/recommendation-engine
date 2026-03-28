"""LLM-powered recommendation engine.

Orchestrates retrieval -> context building -> Azure OpenAI / OpenAI streaming.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from openai import AzureOpenAI, OpenAI

from .prompts import (
    CONTEXT_TEMPLATE,
    DATA_SCIENTIST_SYSTEM_PROMPT,
    DIAGRAM_SYSTEM_PROMPT,
    DIAGRAM_USER_PROMPT,
    SYSTEM_PROMPT,
    USER_MESSAGE_TEMPLATE,
)
from .retriever import MicrosoftLearnRetriever, RetrievalResult
from .settings import Settings

logger = logging.getLogger(__name__)


class AzureRecommender:
    """Generate Azure architecture recommendations backed by live MS Learn docs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.retriever = MicrosoftLearnRetriever(max_results=settings.max_search_results)

    # ------------------------------------------------------------------
    # LLM client helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> AzureOpenAI | OpenAI:
        if self.settings.use_azure:
            return AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
            )
        return OpenAI(api_key=self.settings.openai_api_key)

    def _get_model(self) -> str:
        if self.settings.use_azure:
            return self.settings.azure_openai_deployment
        return self.settings.openai_model

    # ------------------------------------------------------------------
    # Context construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context_block(retrieval: RetrievalResult) -> str:
        formatted = retrieval.format_context()
        return CONTEXT_TEMPLATE.format(context=formatted)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve_context(self, use_case: str) -> RetrievalResult:
        """Search Microsoft Learn + Architecture Center for the given use case."""
        return self.retriever.retrieve(use_case)

    # ------------------------------------------------------------------
    # Recommendation (streaming)
    # ------------------------------------------------------------------

    def recommend_stream(
        self,
        use_case: str,
        retrieval: RetrievalResult,
        persona: str = "architect",
    ) -> Generator[str, None, None]:
        """Stream an architecture recommendation for *use_case* grounded in *retrieval*.

        Args:
            persona: ``"architect"`` (default) or ``"data_scientist"``.
        """
        client = self._get_client()
        context_block = self._build_context_block(retrieval)

        system_prompt = (
            DATA_SCIENTIST_SYSTEM_PROMPT
            if persona == "data_scientist"
            else SYSTEM_PROMPT
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": USER_MESSAGE_TEMPLATE.format(
                    context_block=context_block,
                    use_case=use_case,
                ),
            },
        ]

        stream = client.chat.completions.create(
            model=self._get_model(),
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    # ------------------------------------------------------------------
    # Diagram generation (streaming)
    # ------------------------------------------------------------------

    def generate_diagram_stream(
        self, recommendation: str
    ) -> Generator[str, None, None]:
        """Stream a Mermaid diagram based on a prior recommendation."""
        client = self._get_client()

        messages = [
            {"role": "system", "content": DIAGRAM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": DIAGRAM_USER_PROMPT.format(recommendation=recommendation),
            },
        ]

        stream = client.chat.completions.create(
            model=self._get_model(),
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
