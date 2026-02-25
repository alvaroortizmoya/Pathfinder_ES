import unittest

from pathfinder_es.semantic import build_hash_embedding, cosine


class SemanticTests(unittest.TestCase):
    def test_embedding_is_normalized(self):
        vec = build_hash_embedding("attack action damage")
        norm_sq = sum(v * v for v in vec)
        self.assertAlmostEqual(norm_sq, 1.0, places=6)

    def test_cosine_prefers_similar_text(self):
        source = build_hash_embedding("fireball spell damage area")
        similar = build_hash_embedding("fireball spell area burst")
        different = build_hash_embedding("crafting downtime item price")

        self.assertGreater(cosine(source, similar), cosine(source, different))


if __name__ == "__main__":
    unittest.main()
