"""Retrieve documentation via the official Microsoft Learn MCP Server.

Uses the MCP Python SDK to connect to the Microsoft Learn MCP Server
(https://learn.microsoft.com/api/mcp) over Streamable HTTP.  All documentation
retrieval goes through the server's published tools — no scraping, no local
catalogs.

MCP tools exposed by the server (discovered dynamically at runtime):
  - microsoft_docs_search        — semantic search across Microsoft docs
  - microsoft_docs_fetch         — fetch a Learn page as markdown
  - microsoft_code_sample_search — search official code samples
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass, field

from mcp import ClientSession
from mcp import types as mcp_types
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)

LEARN_MCP_ENDPOINT = "https://learn.microsoft.com/api/mcp"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RetrievedDoc:
    title: str
    url: str
    description: str
    content: str = ""


@dataclass
class RetrievalResult:
    learn_docs: list[RetrievedDoc] = field(default_factory=list)
    architecture_docs: list[RetrievedDoc] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.learn_docs) + len(self.architecture_docs)

    def format_context(self) -> str:
        """Render retrieved documents as an LLM-friendly context string."""
        parts: list[str] = []

        if self.learn_docs:
            parts.append("#### Microsoft Learn Documentation")
            for doc in self.learn_docs:
                text = doc.content or doc.description
                if text:
                    parts.append(f"**{doc.title}** — {doc.url}\n{text}\n")

        if self.architecture_docs:
            parts.append("#### Azure Architecture Center")
            for doc in self.architecture_docs:
                text = doc.content or doc.description
                if text:
                    parts.append(f"**{doc.title}** — {doc.url}\n{text}\n")

        return "\n".join(parts) if parts else "No documentation retrieved."


# ---------------------------------------------------------------------------
# MCP-backed retriever
# ---------------------------------------------------------------------------

class MicrosoftLearnRetriever:
    """Search & fetch Microsoft Learn docs via the official MCP Server."""

    def __init__(self, max_results: int = 5) -> None:
        self.max_results = max_results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(result: mcp_types.CallToolResult) -> str:
        """Pull plain text out of an MCP CallToolResult."""
        parts: list[str] = []
        for block in result.content:
            if isinstance(block, mcp_types.TextContent):
                parts.append(block.text)
        return "\n".join(parts)

    async def _search(
        self, session: ClientSession, query: str
    ) -> list[RetrievedDoc]:
        """Invoke ``microsoft_docs_search`` and parse the structured output."""
        try:
            result = await session.call_tool(
                "microsoft_docs_search", {"query": query}
            )
            return self._parse_search_results(result)
        except Exception:
            logger.warning(
                "microsoft_docs_search failed for: %s", query, exc_info=True
            )
            return []

    async def _fetch_page(self, session: ClientSession, url: str) -> str:
        """Invoke ``microsoft_docs_fetch`` and return the markdown content."""
        try:
            result = await session.call_tool(
                "microsoft_docs_fetch", {"url": url}
            )
            return self._extract_text(result)
        except Exception:
            logger.warning(
                "microsoft_docs_fetch failed for: %s", url, exc_info=True
            )
            return ""

    # ------------------------------------------------------------------
    # Search-result parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_search_results(
        result: mcp_types.CallToolResult,
    ) -> list[RetrievedDoc]:
        """Parse MCP search results.

        The server returns structured JSON via ``structuredContent``:
        ``{"results": [{"title": ..., "content": ..., "contentUrl": ...}, ...]``
        We prefer that, falling back to JSON-parsing the text block.
        """
        import json

        raw: dict | None = None

        # Prefer structuredContent (typed dict)
        if hasattr(result, "structuredContent") and result.structuredContent:
            raw = result.structuredContent  # type: ignore[assignment]

        # Fallback: parse text block as JSON
        if raw is None:
            for block in result.content:
                if isinstance(block, mcp_types.TextContent):
                    try:
                        raw = json.loads(block.text)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break

        if not raw or "results" not in raw:
            return []

        docs: list[RetrievedDoc] = []
        for item in raw["results"]:
            docs.append(
                RetrievedDoc(
                    title=item.get("title", "Untitled"),
                    url=item.get("contentUrl", ""),
                    description="",
                    content=item.get("content", ""),
                )
            )
        return docs

    # ------------------------------------------------------------------
    # Public API (async)
    # ------------------------------------------------------------------

    async def retrieve_async(
        self, query: str, fetch_content: bool = True
    ) -> RetrievalResult:
        """Search Learn + Architecture Center via MCP, optionally fetch pages."""
        async with streamable_http_client(LEARN_MCP_ENDPOINT) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                learn_query = f"Azure {query}"
                arch_query = f"Azure architecture reference {query}"

                learn_docs, arch_docs = await asyncio.gather(
                    self._search(session, learn_query),
                    self._search(session, arch_query),
                )

                learn_docs = learn_docs[: self.max_results]
                arch_docs = arch_docs[: self.max_results]

                # The search already returns content snippets.
                # Optionally fetch full pages for top results.
                if fetch_content:
                    docs_to_fetch = [
                        d for d in (learn_docs[:2] + arch_docs[:1])
                        if d.url and len(d.content) < 500
                    ]
                    if docs_to_fetch:
                        fetched = await asyncio.gather(
                            *(self._fetch_page(session, d.url)
                              for d in docs_to_fetch)
                        )
                        for doc, page in zip(docs_to_fetch, fetched):
                            if page:
                                doc.content = page

                return RetrievalResult(
                    learn_docs=learn_docs, architecture_docs=arch_docs
                )

    # ------------------------------------------------------------------
    # Public API (sync wrapper)
    # ------------------------------------------------------------------

    def retrieve(self, query: str, fetch_content: bool = True) -> RetrievalResult:
        """Synchronous convenience wrapper around :meth:`retrieve_async`.

        Handles the common case where the caller is already inside a
        running event loop (e.g. Streamlit) by offloading to a new thread.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run,
                    self.retrieve_async(query, fetch_content),
                ).result()
        return asyncio.run(self.retrieve_async(query, fetch_content))
