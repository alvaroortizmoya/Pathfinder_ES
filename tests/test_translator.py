import unittest

from pathfinder_es.translator import Translator


class DummyEngine:
    def __init__(self, responses):
        self.responses = list(responses)

    def translate(self, _chunk):
        return self.responses.pop(0)


class TranslatorTests(unittest.TestCase):
    def test_translate_falls_back_when_provider_returns_none(self):
        text = "hola" * 3000
        chunks = [text[i : i + 4500] for i in range(0, len(text), 4500)]
        translator = Translator(engine=DummyEngine(["ok", None, "fin"]))

        out = translator.translate(text, chunk_size=4500)

        expected = "\n".join(["ok", chunks[1], "fin"])
        self.assertEqual(out, expected)

    def test_translate_returns_original_if_blank(self):
        translator = Translator(engine=DummyEngine([]))
        self.assertEqual(translator.translate("   \n"), "   \n")


if __name__ == "__main__":
    unittest.main()
