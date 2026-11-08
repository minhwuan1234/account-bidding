"""Download the CPU embedding model during the Railway build."""
from sentence_transformers import SentenceTransformer

from business.semantic import MODEL_ID, MODEL_PATH


if __name__ == "__main__":
    model = SentenceTransformer(MODEL_ID, device="cpu")
    model.save(str(MODEL_PATH))
    print(f"Embedding model saved to {MODEL_PATH}", flush=True)
