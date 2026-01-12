import os
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv()

QDRANT_PATH = "./qdrant_data"
COLLECTION_NAME = "transcripts"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHAT_MODEL = "gpt-4o-mini"


class TranscriptRAG:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.qdrant = QdrantClient(path=QDRANT_PATH)
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
            print(f"Created collection: {COLLECTION_NAME}")

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text."""
        response = self.openai.embeddings.create(input=text, model=EMBEDDING_MODEL)
        return response.data[0].embedding

    def _chunk_transcript(self, text: str, chunk_size: int = 15) -> list[dict]:
        """
        Split transcript into chunks by conversation turns.
        Each chunk contains ~chunk_size turns with metadata.
        """
        chunks = []
        current_meeting = None
        current_date = None
        lines = text.strip().split("\n")

        buffer = []
        for line in lines:
            # Detect meeting header
            if line.startswith("=" * 10):
                continue
            if line.startswith("MEETING:"):
                current_meeting = line.replace("MEETING:", "").strip()
                continue
            if line.startswith("DATE:"):
                current_date = line.replace("DATE:", "").strip()
                continue

            # Skip empty lines
            if not line.strip():
                if buffer:
                    chunks.append({
                        "text": "\n".join(buffer),
                        "meeting": current_meeting,
                        "date": current_date,
                    })
                    buffer = []
                continue

            # Add transcript line to buffer
            if line.startswith("["):
                buffer.append(line)
                if len(buffer) >= chunk_size:
                    chunks.append({
                        "text": "\n".join(buffer),
                        "meeting": current_meeting,
                        "date": current_date,
                    })
                    buffer = []

        # Don't forget the last buffer
        if buffer:
            chunks.append({
                "text": "\n".join(buffer),
                "meeting": current_meeting,
                "date": current_date,
            })

        return chunks

    def index_transcript_file(self, file_path: str, verbose: bool = True):
        """Index a transcript file into the vector store."""
        with open(file_path, "r") as f:
            content = f.read()

        chunks = self._chunk_transcript(content)
        total = len(chunks)
        if verbose:
            print(f"         {total} chunks to embed", flush=True)

        # Check existing points count
        collection_info = self.qdrant.get_collection(COLLECTION_NAME)
        start_id = collection_info.points_count

        points = []
        for i, chunk in enumerate(chunks, 1):
            if verbose and i % 5 == 0:
                print(f"         Chunk {i}/{total}...", flush=True)
            embedding = self._get_embedding(chunk["text"])
            points.append(
                PointStruct(
                    id=start_id + i - 1,
                    vector=embedding,
                    payload={
                        "text": chunk["text"],
                        "meeting": chunk["meeting"],
                        "date": chunk["date"],
                        "source_file": str(file_path),
                    },
                )
            )

        self.qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        if verbose:
            print(f"         Done: {len(points)} chunks indexed", flush=True)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search for relevant transcript chunks."""
        query_embedding = self._get_embedding(query)
        results = self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=limit,
        ).points
        return [
            {
                "text": r.payload["text"],
                "meeting": r.payload["meeting"],
                "date": r.payload["date"],
                "score": r.score,
            }
            for r in results
        ]

    def ask(self, question: str, limit: int = 5) -> str:
        """
        Ask a question about the transcripts.
        Uses RAG: retrieves relevant chunks, then asks LLM to answer.
        """
        # Retrieve relevant context
        results = self.search(question, limit=limit)

        if not results:
            return "No relevant transcripts found. Have you indexed any files?"

        # Build context
        context_parts = []
        for r in results:
            context_parts.append(f"[{r['meeting']} - {r['date']}]\n{r['text']}")
        context = "\n\n---\n\n".join(context_parts)

        # Ask LLM
        response = self.openai.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful assistant analyzing meeting transcripts.
Answer questions based on the provided transcript excerpts.
The transcripts may be in Russian or Ukrainian - respond in the same language as the question.
If you can't find the answer in the provided context, say so.
Always cite which meeting/date the information comes from.""",
                },
                {
                    "role": "user",
                    "content": f"""Based on these transcript excerpts:

{context}

---

Question: {question}""",
                },
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content

    def get_stats(self) -> dict:
        """Get collection statistics."""
        info = self.qdrant.get_collection(COLLECTION_NAME)
        return {
            "total_chunks": info.points_count,
            "vector_size": info.config.params.vectors.size,
        }

    def clear(self):
        """Clear all indexed data."""
        self.qdrant.delete_collection(COLLECTION_NAME)
        self._ensure_collection()
        print("Cleared all indexed data")


if __name__ == "__main__":
    rag = TranscriptRAG()

    # Check if we need to index
    stats = rag.get_stats()
    if stats["total_chunks"] == 0:
        print("No data indexed. Indexing transcripts...")
        transcript_file = Path(__file__).parent / "team_calls_transcripts.txt"
        if transcript_file.exists():
            rag.index_transcript_file(str(transcript_file))
        else:
            print(f"Transcript file not found: {transcript_file}")
    else:
        print(f"Found {stats['total_chunks']} indexed chunks")

    # Interactive mode
    print("\n" + "=" * 50)
    print("Transcript RAG ready! Ask questions or type 'quit' to exit.")
    print("=" * 50 + "\n")

    while True:
        try:
            question = input("You: ").strip()
            if question.lower() in ["quit", "exit", "q"]:
                break
            if not question:
                continue

            print("\nSearching and thinking...\n")
            answer = rag.ask(question)
            print(f"Assistant: {answer}\n")
        except KeyboardInterrupt:
            break

    print("\nGoodbye!")
