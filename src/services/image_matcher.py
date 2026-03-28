from __future__ import annotations

from src.config import Settings
from src.models import ImageInsight


class ImageCatalogMatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, file_name: str | None, raw_bytes: bytes | None) -> ImageInsight | None:
        if not raw_bytes:
            return None

        if not self.settings.vision_ready:
            return None
        return self._try_azure_vision(raw_bytes)

    def _try_azure_vision(self, raw_bytes: bytes) -> ImageInsight | None:
        try:
            from azure.ai.vision.imageanalysis import ImageAnalysisClient
            from azure.ai.vision.imageanalysis.models import VisualFeatures
            from azure.core.credentials import AzureKeyCredential

            client = ImageAnalysisClient(
                endpoint=self.settings.vision_endpoint,
                credential=AzureKeyCredential(self.settings.vision_key),
            )
            result = client.analyze(
                image_data=raw_bytes,
                visual_features=[VisualFeatures.CAPTION, VisualFeatures.TAGS],
                language="en",
                gender_neutral_caption=True,                
            )
            description = getattr(getattr(result, "caption", None), "text", "").strip()
            tags = [tag.name for tag in getattr(result, "tags", []) if getattr(tag, "name", None)]
            confidence = float(getattr(getattr(result, "caption", None), "confidence", 0.0))
            if not description and not tags:
                return None
            return ImageInsight(description=description, tags=tags[:8], confidence=confidence)
        except Exception:
            return None
