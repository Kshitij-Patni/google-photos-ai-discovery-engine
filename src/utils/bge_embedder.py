from sentence_transformers import SentenceTransformer
import torch

class BGEEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", device: str = None):
        """Initializes the BGE Embedder model."""
        if not device:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device
            
        print(f"Loading {model_name} on device: {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device)
        # For retrieval tasks, BGE uses an instruction prefix for queries (but not for indexing)
        self.instruction_prefix = "Represent this sentence for retrieving relevant documents: "

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds documents (for indexing). No prefix needed."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
        
    def embed_query(self, text: str) -> list[float]:
        """Embeds a query using the instruction prefix."""
        query = f"{self.instruction_prefix}{text}"
        embedding = self.model.encode(query, normalize_embeddings=True)
        return embedding.tolist()

if __name__ == "__main__":
    # Simple test
    embedder = BGEEmbedder()
    doc_emb = embedder.embed_documents(["This is a test document."])
    query_emb = embedder.embed_query("This is a test query.")
    print(f"Document embedding shape: {len(doc_emb[0])} dimensions")
    print(f"Query embedding shape: {len(query_emb)} dimensions")
