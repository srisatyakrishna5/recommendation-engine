from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from ..config import Settings


class SpeechTranscriber:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, raw_bytes: bytes | None, file_name: str | None = None) -> str | None:
        if not raw_bytes or not self.settings.speech_ready:
            return None

        suffix = Path(file_name or "voice.wav").suffix or ".wav"
        try:
            import azure.cognitiveservices.speech as speechsdk

            with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(raw_bytes)
                temp_name = handle.name

            speech_config = speechsdk.SpeechConfig(
                subscription=self.settings.speech_key,
                region=self.settings.speech_region,
            )
            audio_config = speechsdk.audio.AudioConfig(filename=temp_name)
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            result = recognizer.recognize_once()
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text.strip()
            return None
        except Exception:
            return None
