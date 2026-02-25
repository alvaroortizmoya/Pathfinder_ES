from __future__ import annotations

from deep_translator import GoogleTranslator


class Translator:
    def __init__(self, source: str = "en", target: str = "es") -> None:
        self.source = source
        self.target = target
        self.engine = GoogleTranslator(source=source, target=target)

    def translate(self, text: str, chunk_size: int = 4500) -> str:
        if not text.strip():
            return text

        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        translated_chunks: list[str] = []
        for chunk in chunks:
            translated_chunks.append(self.engine.translate(chunk))
        return "\n".join(translated_chunks)
