import os
import glob
from typing import List, Dict
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

# ----------------------------
# Configuration
# ----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"
PERSIST_DIRECTORY = "knowledge/vector_store"
DOCUMENTS_PATH = "knowledge/documents/*.md"
TOP_K = 6

client = OpenAI(api_key=OPENAI_API_KEY)

# Use OpenAI embeddings via Chroma
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)

# ----------------------------
# 1. Load and Chunk Documents
# ----------------------------
def load_and_chunk_documents(path_pattern: str = DOCUMENTS_PATH) -> List[Dict]:
    """
    Loads all markdown files and splits them into simple chunks.
    Each chunk keeps its Source ID (filename-based).
    """
    chunks = []
    files = glob.glob(path_pattern)

    for file_path in files:
        filename = os.path.basename(file_path)
        source_id = filename.split("_")[0]  # e.g. SRC-001

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # Simple chunking by paragraphs (good enough for small policy docs)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        for i, para in enumerate(paragraphs):
            chunks.append({
                "id": f"{source_id}_{i}",
                "source_id": source_id,
                "text": para,
                "metadata": {
                    "source_id": source_id,
                    "filename": filename
                }
            })

    print(f"Loaded {len(chunks)} chunks from {len(files)} documents.")
    return chunks


# ----------------------------
# 2. Create / Load Vector Store
# ----------------------------
def get_or_create_collection():
    chroma_client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

    collection = chroma_client.get_or_create_collection(
        name="sme_procurement_corpus",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def index_documents(chunks: List[Dict], collection):
    """Indexes chunks into Chroma. Skips if already indexed."""
    if collection.count() > 0:
        print(f"Collection already contains {collection.count()} items. Skipping indexing.")
        return

    collection.add(
        documents=[c["text"] for c in chunks],
        ids=[c["id"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks]
    )
    print(f"Indexed {len(chunks)} chunks.")


# ----------------------------
# 3. Retrieval
# ----------------------------
def retrieve(query: str, collection, top_k: int = TOP_K) -> List[Dict]:
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    retrieved = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        retrieved.append({
            "text": doc,
            "source_id": meta["source_id"],
            "distance": dist
        })
    return retrieved


# ----------------------------
# 4. Build Context + Call Model
# ----------------------------
RAG_SYSTEM_PROMPT = """You are a careful and precise Procurement Assistant for a Ugandan Small or Medium Enterprise (SME). 
You answer questions using ONLY the information provided in the retrieved context below. 

Strict rules you must follow:
- Use only the facts that appear in the provided context.
- If the exact information needed is not present in the context, you must reply: "Insufficient information in the knowledge base."
- Do not use any external or pre-trained knowledge.
- Do not invent stock levels, prices, lead times, policies, or supplier details.
- Always cite the Source ID(s) you used (e.g., SRC-001, SRC-010) at the end of your answer.
- If multiple sources are used, list all of them.
- Keep the tone professional, clear, and concise.
- Never suggest placing an order, selecting a final supplier, or committing funds.

Output format:
1. Direct answer to the question
2. Supporting details (only from context)
3. Sources: SRC-XXX, SRC-YYY
"""

def ask_rag(question: str, collection) -> str:
    # Retrieve
    retrieved = retrieve(question, collection, top_k=TOP_K)

    # Build context string
    context_parts = []
    for item in retrieved:
        context_parts.append(f"[{item['source_id']}] {item['text']}")
    context = "\n\n".join(context_parts)

    # Full user message
    user_message = f"""Retrieved context:
{context}

Question: {question}
"""

    # Call the model
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.15
    )

    return response.choices[0].message.content


# ----------------------------
# 5. Main / Demo
# ----------------------------
if __name__ == "__main__":
    print("=== SME Procurement RAG Pipeline ===")

    # Load & index (only needed once)
    chunks = load_and_chunk_documents()
    collection = get_or_create_collection()
    index_documents(chunks, collection)

    # Example questions
    test_questions = [
        "What is the rule for flagging an item as needing reorder?",
        "What should the system do when current stock data is missing?",
        "Can the system place an order on its own?",
        "What is the average monthly usage of Iron Sheets Gauge 28?"
    ]

    for q in test_questions:
        print("\n" + "="*80)
        print(f"Question: {q}")
        print("-"*80)
        answer = ask_rag(q, collection)
        print(answer)