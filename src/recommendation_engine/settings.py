import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration loaded from environment variables or overrides."""

    def __init__(self, **overrides: str | int) -> None:
        # Azure OpenAI
        self.azure_openai_endpoint: str = (
            str(overrides.get("azure_openai_endpoint") or "")
            or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        )
        self.azure_openai_api_key: str = (
            str(overrides.get("azure_openai_api_key") or "")
            or os.getenv("AZURE_OPENAI_API_KEY", "")
        )
        self.azure_openai_deployment: str = (
            str(overrides.get("azure_openai_deployment") or "")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        )
        self.azure_openai_api_version: str = (
            str(overrides.get("azure_openai_api_version") or "")
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        )
        # Standard OpenAI
        self.openai_api_key: str = (
            str(overrides.get("openai_api_key") or "")
            or os.getenv("OPENAI_API_KEY", "")
        )
        self.openai_model: str = (
            str(overrides.get("openai_model") or "")
            or os.getenv("OPENAI_MODEL", "gpt-4o")
        )
        # Retrieval
        self.max_search_results: int = int(
            overrides.get("max_search_results") or os.getenv("MAX_SEARCH_RESULTS", "5")
        )

    @property
    def use_azure(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def is_configured(self) -> bool:
        return self.use_azure or bool(self.openai_api_key)
