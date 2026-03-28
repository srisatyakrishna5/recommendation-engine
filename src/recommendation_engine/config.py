from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

load_dotenv(ROOT_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_title: str
    environment: str
    root_dir: Path
    data_dir: Path
    catalog_path: Path
    sample_catalog_path: Path
    azure_openai_endpoint: str | None
    azure_openai_api_key: str | None
    azure_openai_deployment: str
    azure_openai_api_version: str
    azure_openai_embedding_deployment: str | None
    azure_search_endpoint: str | None
    azure_search_api_key: str | None
    azure_search_index_name: str
    document_intelligence_endpoint: str | None
    document_intelligence_key: str | None
    vision_endpoint: str | None
    vision_key: str | None
    speech_key: str | None
    speech_region: str | None

    @property
    def azure_openai_ready(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key and self.azure_openai_deployment)

    @property
    def azure_search_ready(self) -> bool:
        return bool(self.azure_search_endpoint and self.azure_search_api_key and self.azure_search_index_name)

    @property
    def document_intelligence_ready(self) -> bool:
        return bool(self.document_intelligence_endpoint and self.document_intelligence_key)

    @property
    def vision_ready(self) -> bool:
        return bool(self.vision_endpoint and self.vision_key)

    @property
    def speech_ready(self) -> bool:
        return bool(self.speech_key and self.speech_region)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_title=os.getenv("APP_TITLE", "Azure Product Recommendation Engine"),
        environment=os.getenv("APP_ENV", "Development"),
        root_dir=ROOT_DIR,
        data_dir=DATA_DIR,
        catalog_path=DATA_DIR / "product_catalog.json",
        sample_catalog_path=DATA_DIR / "product_catalog.sample.json",
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_openai_embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        azure_search_index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "product-catalog"),
        document_intelligence_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        document_intelligence_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
        vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
        vision_key=os.getenv("AZURE_VISION_KEY"),
        speech_key=os.getenv("AZURE_SPEECH_KEY"),
        speech_region=os.getenv("AZURE_SPEECH_REGION"),
    )
