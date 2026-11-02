import unittest
from pathlib import Path

from evidence import evidence_units
from matching import match_requirements, requirement_units


class FakeEmbedder:
    def encode(self, texts, normalize_embeddings=False):
        self.texts = texts
        return [[1.0, 0.0] if "prototype" in text.lower() else [0.0, 1.0] for text in texts]


class MatchingTests(unittest.TestCase):
    def test_only_approved_explicit_requirements_are_compared(self):
        chunks = [
            {"id": "a", "file": "rfp.docx", "pages": [], "section_path": ["Scope"],
             "labels": {"topics": ["Prototype"]}, "requirement_tier": "approved",
             "blocks": [{"kind": "paragraph", "text": "The bidder must provide a prototype. Background information follows."}]},
            {"id": "b", "labels": {"topics": ["Budget"]}, "requirement_tier": "reject",
             "blocks": [{"kind": "paragraph", "text": "The bidder must provide a budget."}]},
        ]
        self.assertEqual(len(requirement_units(chunks)), 1)
        evidence = [{"file": "portfolio.docx", "text": "We have delivered a prototype.", "section_path": [], "page": None, "kind": "paragraph"}]
        result = match_requirements(chunks, evidence, embedder=FakeEmbedder())
        self.assertEqual(result["counts"]["matched"], 1)
        self.assertEqual(result["requirements"][0]["evidence"]["file"], "portfolio.docx")

    def test_evidence_retains_file_and_page(self):
        units = evidence_units(Path(__file__).parent / "samples" / "sample.pdf")
        self.assertTrue(units)
        self.assertTrue(all(item["file"] == "sample.pdf" for item in units))
        self.assertTrue(any(item["page"] == 1 for item in units))

    def test_different_required_number_needs_review(self):
        chunks = [{"id": "a", "file": "rfp.docx", "pages": [], "section_path": [],
                   "labels": {"topics": ["Experience"]}, "requirement_tier": "approved",
                   "blocks": [{"kind": "paragraph", "text": "The bidder must provide 5 years of experience."}]}]
        evidence = [{"file": "profile.docx", "text": "We provide 2 years of experience.", "section_path": [], "page": None, "kind": "paragraph"}]
        class SameEmbedder:
            def encode(self, texts, normalize_embeddings=False):
                return [[1.0, 0.0] for _ in texts]
        result = match_requirements(chunks, evidence, embedder=SameEmbedder())
        self.assertEqual(result["requirements"][0]["status"], "review")
        self.assertTrue(result["requirements"][0]["numeric_conflict"])

    def test_no_reference_evidence_is_missing(self):
        chunks = [{"id": "a", "file": "rfp.docx", "pages": [], "section_path": [],
                   "labels": {"topics": ["Prototype"]}, "requirement_tier": "approved",
                   "blocks": [{"kind": "paragraph", "text": "The bidder must provide a prototype."}]}]
        result = match_requirements(chunks, [], embedder=FakeEmbedder())
        self.assertEqual(result["counts"]["missing"], 1)
        self.assertIsNone(result["requirements"][0]["evidence"])


if __name__ == "__main__":
    unittest.main()
