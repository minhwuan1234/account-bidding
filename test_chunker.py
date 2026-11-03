import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from docx import Document

from chunker import Block, chunk_file, make_chunks
from labels import attach_labels
from requirements_filter import NEGATIVE, POSITIVE, mark_requirement_candidates, tier_for
from semantic import split_semantic


SAMPLES = Path(__file__).parent / "samples"


class NullEmbedder:
    def encode(self, texts, normalize_embeddings=False):
        return [[0.0, 0.0] for _ in texts]


class ChunkerTests(unittest.TestCase):
    def test_requirement_tier_boundaries(self):
        self.assertEqual(tier_for(0.4999), "reject")
        self.assertEqual(tier_for(0.5), "considerable")
        self.assertEqual(tier_for(0.7499), "considerable")
        self.assertEqual(tier_for(0.75), "approved")

    def test_docx_structure_and_table(self):
        result = chunk_file(SAMPLES / "sample.docx", embedder=NullEmbedder())
        self.assertEqual(result["chunk_count"], 4)
        deliverables = result["chunks"][2]
        self.assertEqual(deliverables["section_path"], ["Project Brief", "1. Scope of Work", "1.1 Deliverables"])
        self.assertEqual(deliverables["blocks"][0]["kind"], "table")
        self.assertEqual(deliverables["blocks"][0]["rows"][1], ["Prototype", "Week 2"])
        self.assertIsNone(deliverables["page_start"])

    def test_pdf_structure_table_and_page(self):
        result = chunk_file(SAMPLES / "sample.pdf", embedder=NullEmbedder())
        self.assertGreaterEqual(result["chunk_count"], 3)
        all_text = " ".join(c["text"] for c in result["chunks"])
        self.assertIn("working prototype", all_text)
        self.assertIn("Prototype", all_text)
        self.assertTrue(all(c["page_start"] == 1 for c in result["chunks"]))
        self.assertTrue(any(b["kind"] == "table" for c in result["chunks"] for b in c["blocks"]))

    def test_semantic_split_keeps_section_table_and_page(self):
        class FakeEmbedder:
            def encode(self, texts, normalize_embeddings=False):
                self.texts = texts
                self.normalized = normalize_embeddings
                return [[1, 0], [0.98, 0.2], [0, 1]]

        blocks = [
            Block("heading", "Scope", page=2, level=1),
            Block("paragraph", "Design the prototype.", page=2),
            Block("paragraph", "Build the prototype.", page=2),
            Block("table", "Item | Due", page=3, rows=[["Item", "Due"]]),
            Block("paragraph", "Submit the financial proposal.", page=3),
        ]
        fake = FakeEmbedder()
        chunks = split_semantic(make_chunks(blocks, "sample.pdf"), threshold=0.78, embedder=fake)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["section_path"], ["Scope"])
        self.assertEqual(chunks[0]["pages"], [2, 3])
        self.assertEqual(chunks[0]["blocks"][-1]["kind"], "table")
        self.assertEqual(chunks[1]["pages"], [3])
        self.assertLess(chunks[1]["split_similarity"], 0.78)
        self.assertTrue(all(text.startswith("query: ") for text in fake.texts))
        self.assertTrue(fake.normalized)

    def test_semantic_split_can_find_shift_inside_one_paragraph(self):
        class FakeEmbedder:
            def encode(self, texts, normalize_embeddings=False):
                self.texts = texts
                return [[1, 0], [0.98, 0.2], [0, 1], [0.2, 0.98]]

        blocks = [
            Block("heading", "Requirements", level=1),
            Block("paragraph", "Design the website. Build the prototype. Pay the invoice. Send the receipt."),
        ]
        fake = FakeEmbedder()
        chunks = split_semantic(make_chunks(blocks, "example.docx"), threshold=0.85, embedder=fake)
        self.assertEqual(len(fake.texts), 4)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["text"], "Design the website. Build the prototype.")
        self.assertEqual(chunks[1]["text"], "Pay the invoice. Send the receipt.")

    def test_semantic_embeddings_are_batched_across_sections(self):
        class FakeEmbedder:
            def __init__(self):
                self.calls = 0

            def encode(self, texts, normalize_embeddings=False):
                self.calls += 1
                return [[1.0, 0.0] for _ in texts]

        blocks = [
            Block("heading", "Scope", level=1),
            Block("paragraph", "Design the prototype."),
            Block("paragraph", "Build the prototype."),
            Block("heading", "Submission", level=1),
            Block("paragraph", "Prepare the offer."),
            Block("paragraph", "Submit the offer."),
        ]
        fake = FakeEmbedder()
        chunks = split_semantic(make_chunks(blocks, "example.docx"), embedder=fake)
        self.assertEqual(fake.calls, 1)
        self.assertEqual([chunk["section_path"] for chunk in chunks], [["Scope"], ["Submission"]])

    def test_plain_section_heading_becomes_label(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "rfq.docx"
            doc = Document()
            doc.add_paragraph("Request for Quotation")
            doc.add_paragraph("SECTION 1: REQUEST FOR QUOTATION (RFQ)")
            doc.add_paragraph("UNDP kindly requests your quotation.")
            doc.save(path)
            chunks = chunk_file(path, embedder=NullEmbedder())["chunks"]
        self.assertEqual(chunks[0]["section_path"], [])
        self.assertEqual(chunks[1]["section_path"], ["SECTION 1: REQUEST FOR QUOTATION (RFQ)"])
        self.assertEqual(chunks[1]["heading"], "SECTION 1: REQUEST FOR QUOTATION (RFQ)")
        self.assertEqual(chunks[1]["labels"]["source"], "content_embedding")

    def test_topic_is_extracted_from_chunk_content(self):
        class FakeEmbedder:
            def encode(self, texts, normalize_embeddings=False):
                self.normalized = normalize_embeddings
                return [[1.0, 0.0] if "deadline" in text.lower() else [0.0, 1.0] for text in texts]

        chunks = [
            {"heading": None, "section_path": [], "text": "Deadline for submission is 20 October 2026.", "blocks": [{"kind": "paragraph", "text": "Deadline for submission is 20 October 2026.", "page": 1}]},
            {"heading": None, "section_path": [], "text": "UNDP welcomes your interest in this project.", "blocks": [{"kind": "paragraph", "text": "UNDP welcomes your interest in this project.", "page": 1}]},
        ]
        fake = FakeEmbedder()
        attach_labels(chunks, embedder=fake)
        self.assertIn("deadline", chunks[0]["labels"]["topics"][0].lower())
        self.assertEqual(chunks[0]["labels"]["topic_details"][0]["evidence"], "Deadline for submission is 20 October 2026.")
        self.assertTrue(chunks[1]["labels"]["topics"][0])
        self.assertNotEqual(chunks[1]["labels"]["topics"][0], "Thông tin chung")
        self.assertEqual(chunks[1]["labels"]["source"], "content_embedding")
        self.assertTrue(fake.normalized)

    def test_requirement_tiers_use_tags_only_and_feedback(self):
        from tag_store import save_approved

        class FakeEmbedder:
            def encode(self, texts, normalize_embeddings=False):
                self.texts = texts
                output = []
                for text in texts:
                    value = text.removeprefix("query: ")
                    if value in POSITIVE or value == "Submission requirements":
                        output.append([1.0, 0.0])
                    elif value in NEGATIVE or value == "UNDP overview":
                        output.append([0.0, 1.0])
                    else:
                        output.append([0.7, 0.7])
                return output

        chunks = [
            {"labels": {"topics": ["Submission requirements"]}, "text": "A very long document section."},
            {"labels": {"topics": ["UNDP overview"]}, "text": "Another long section."},
        ]
        fake = FakeEmbedder()
        with TemporaryDirectory() as folder:
            db = Path(folder) / "tags.sqlite3"
            mark_requirement_candidates(chunks, embedder=fake, db_path=db)
            self.assertEqual(chunks[0]["requirement_tier"], "approved")
            self.assertEqual(chunks[1]["requirement_tier"], "reject")
            self.assertFalse(any("long" in text for text in fake.texts))
            save_approved("UNDP overview", [0.0, 1.0], db)
            mark_requirement_candidates(chunks, embedder=fake, db_path=db)
            self.assertEqual(chunks[1]["requirement_tier"], "approved")
            self.assertTrue(chunks[1]["approved_by_user"])


if __name__ == "__main__":
    unittest.main()
