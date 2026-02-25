from __future__ import annotations

from typing import Protocol


class TranslationEngine(Protocol):
    def translate(self, text: str) -> str | None: ...


class Translator:
    def __init__(
        self,
        source: str = "en",
        target: str = "es",
        engine: TranslationEngine | None = None,
    ) -> None:
        self.source = source
        self.target = target
        self.engine = engine or self._build_engine(source=source, target=target)

    @staticmethod
    def _build_engine(source: str, target: str) -> TranslationEngine:
        from deep_translator import GoogleTranslator

        return GoogleTranslator(source=source, target=target)

    def _translate_chunk(self, chunk: str) -> str:
        translated = self.engine.translate(chunk)
        if translated is None:
            # Algunas respuestas del proveedor pueden devolver None de forma intermitente.
            # Hacemos fallback al texto original para no romper todo el proceso.
            return chunk
        return translated

    def translate(self, text: str, chunk_size: int = 4500) -> str:
        if not text.strip():
            return text

        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        translated_chunks = [self._translate_chunk(chunk) for chunk in chunks]
        return "\n".join(translated_chunks)
