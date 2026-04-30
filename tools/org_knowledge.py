"""
Organization Knowledge Base — powered by ChromaDB.

Loads org documents → chunks them → embeds them → stores in ChromaDB.
Then provides SEMANTIC SEARCH (search by meaning, not just keywords).
"""
import os
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import chromadb
from chromadb.config import Settings
import tempfile

console = Console()

KNOWLEDGE_DIR = os.path.join("data", "org_knowledge")
if os.environ.get("STREAMLIT_CLOUD"):
    CHROMA_DIR = os.path.join(tempfile.gettempdir(), "chromadb")
else:
    CHROMA_DIR = os.path.join("data", "chromadb")

COLLECTION_NAME = "org_knowledge"

CHUNK_SIZE = 500      
CHUNK_OVERLAP = 50    

def get_chroma_client() -> chromadb.ClientAPI:
    """
    Create or connect to the ChromaDB database.
    
    WHY PersistentClient?
    ChromaDB has two modes:
      - EphemeralClient: lives in memory, gone when script ends
      - PersistentClient: saved to disk, survives between runs
    """
    os.makedirs(CHROMA_DIR, exist_ok=True)
    
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client

def get_or_create_collection(client: chromadb.ClientAPI):
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Organization knowledge base documents"
                  ,"id":"every document id"},)
    return collection

def load_documents() -> dict:
    documents = {}
    knowledge_path = Path(KNOWLEDGE_DIR)
    if not knowledge_path.exists():
        console.print(f"[red]Knowledge directory not found: {KNOWLEDGE_DIR}[/red]")
        return documents
    
    supported_extensions = {".md", ".txt", ".markdown"}

    for file_path in sorted(knowledge_path.iterdir()):
        if file_path.suffix.lower() in supported_extensions:
            try:
                content = file_path.read_text(encoding="utf-8")
                documents[file_path.name] = content
                console.print(f"  [dim]Loaded: {file_path.name} ({len(content):,} chars)[/dim]")
            except Exception as e:
                console.print(f"  [red]Failed to load {file_path.name}: {e}[/red]")
    
    return documents

def chunk_document(text: str, source: str) -> list:
    sections = re.split(r'\n(?=#{1,4}\s)|(?:\n\s*\n)', text)
    chunks = []
    chunk_id = 0
    for section in sections:
        section=section.strip()
        if len(section) < 30:  # Skip tiny sections (empty headers, etc.)
            continue

        if len(section) <= CHUNK_SIZE:
            chunks.append({
                "id": f"{source}_chunk_{chunk_id}",
                "text": section,
                "source": source,
                "chunk_index": chunk_id,
            })
            chunk_id += 1
        else:            
            sentences = re.split(r'(?<=[.!?])\s+', section)
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > CHUNK_SIZE and current_chunk:
                    chunks.append({
                            "id": f"{source}_chunk_{chunk_id}",
                            "text": current_chunk.strip(),
                            "source": source,
                            "chunk_index": chunk_id,
                        })
                    chunk_id += 1
                    overlap_text = current_chunk[-CHUNK_OVERLAP:] if len(current_chunk) > CHUNK_OVERLAP else ""
                    current_chunk = overlap_text + " " + sentence
            else:
                    current_chunk += " " + sentence

            if current_chunk.strip():
                chunks.append({
                        "id": f"{source}_chunk_{chunk_id}",
                        "text": current_chunk.strip(),
                        "source": source,
                        "chunk_index": chunk_id,
                    })
                chunk_id += 1
        
        return chunks

def build_knowledge_base(force_rebuild: bool = False) -> int:
        """
    Build the ChromaDB knowledge base.
    This is the INDEXING step
    """

        console.print("\n[bold]Building knowledge base...[/bold]")
        client = get_chroma_client()
        if force_rebuild:
            console.print("[yellow]Force rebuild — deleting existing data...[/yellow]")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        collection = get_or_create_collection(client)

        existing_count = collection.count()
        if existing_count > 0 and not force_rebuild:
            console.print(f"[green]Knowledge base already built: {existing_count} chunks[/green]")
            console.print("[dim]Use force_rebuild=True to re-index[/dim]")
            return existing_count
    
    # Load documents
        console.print("[dim]Loading documents...[/dim]")
        documents = load_documents()
        if not documents:
            console.print("[red]No documents found to index![/red]")
            return 0

        console.print("[dim]Chunking documents...[/dim]")
        all_chunks = []
        for filename, content in documents.items():
            chunks = chunk_document(content, filename)
            all_chunks.extend(chunks)
            console.print(f"  [dim]{filename}: {len(chunks)} chunks[/dim]")
    
        console.print(f"[dim]Total chunks: {len(all_chunks)}[/dim]")
        console.print("[dim]Embedding and storing (this may take a moment)...[/dim]")

        BATCH_SIZE = 100

        for i in range(0, len(all_chunks), BATCH_SIZE):
                batch = all_chunks[i:i + BATCH_SIZE]
                
                collection.add(
                    ids=[chunk["id"] for chunk in batch],
                    documents=[chunk["text"] for chunk in batch],
                    metadatas=[{
                        "source": chunk["source"],
                        "chunk_index": chunk["chunk_index"],
                    } for chunk in batch],
                )
                
                console.print(f"  [dim]Indexed {min(i + BATCH_SIZE, len(all_chunks))}/{len(all_chunks)} chunks[/dim]")
                
                final_count = collection.count()
                console.print(f"[green]✓ Knowledge base built: {final_count} chunks indexed[/green]")
            
        return final_count

def search_org_knowledge(query: str, n_results: int = 5) -> str:
    """
    Semantic search of org knowledge.
    
    HOW IT WORKS:
    1. ChromaDB converts your query to an embedding
    2. Compares against all stored chunk embeddings
    3. Returns the N closest matches by cosine similarity
    4. Cosine similarity measures the "angle" between two vectors:
       - 1.0 = identical meaning
       - 0.0 = unrelated
       - The higher the score, the more relevant the chunk
    
    Args:
        query: What to search for
        n_results: How many results to return 
    
    Returns:
        Formatted string of relevant chunks 
    """
    client = get_chroma_client()
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        console.print("[yellow]Knowledge base not built yet. Building now...[/yellow]")
        build_knowledge_base()
        collection = client.get_collection(COLLECTION_NAME)
            
    # Perform semantic search

    results = collection.query(
        query_texts=[query],  
        n_results=n_results,  
    )
    if not results["documents"][0]:

        return f"No relevant content found for: {query}"
    
    formatted = f"=== RELEVANT ORG CONTENT FOR: {query} ===\n\n"

    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        similarity = 1 / (1 + distance)

        formatted += f"[Source: {metadata['source']} | "
        formatted += f"Relevance: {similarity:.0%}]\n"
        formatted += f"{doc}\n"
        formatted += f"{'-' * 40}\n\n"
    
    return formatted

def search_org_knowledge_raw(query: str, n_results: int = 5) -> list:
    """
    Same as search_org_knowledge but returns raw results (list of dicts).
    Useful when you need to process results in code, not just display them.
    """
    client = get_chroma_client()

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        build_knowledge_base()
        collection = client.get_collection(COLLECTION_NAME)
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    
    processed = []
    for i in range(len(results["documents"][0])):
        distance = results["distances"][0][i]
        processed.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
            "distance": distance,
            "similarity": 1 / (1 + distance),
        })
    
    return processed

def get_relevant_context(funder_priorities: str, n_results: int = 8) -> str:
    """
    Given a funder's priorities, find the most relevant org content.
     Args:
        funder_priorities: Text describing what the funder cares about
        n_results: How many chunks to retrieve
    
    Returns:
        Formatted string of relevant org content
    """
    return search_org_knowledge(funder_priorities, n_results)

def get_full_context() -> str:
    """
    Load ALL org documents as one string.
    """
    
    documents = load_documents()
    
    if not documents:
        return "NO ORGANIZATION DOCUMENTS AVAILABLE."
    
    combined = "=== ORGANIZATION KNOWLEDGE BASE ===\n\n"
    
    for filename, content in documents.items():
        combined += f"\n{'=' * 50}\n"
        combined += f"DOCUMENT: {filename}\n"
        combined += f"{'=' * 50}\n\n"
        combined += content
        combined += "\n"
    
    return combined


def print_knowledge_status():
    """Pretty print the status of the knowledge base"""
    
    # Check documents
    documents = load_documents()
    
    # Check ChromaDB
    client = get_chroma_client()
    try:
        collection = client.get_collection(COLLECTION_NAME)
        chunk_count = collection.count()
        db_exists = True
    except Exception:
        chunk_count = 0
        db_exists = False
    
    # Display
    console.print(Panel.fit(
        "[bold]Organization Knowledge Base[/bold]",
        border_style="blue"
    ))
    
    if not documents:
        console.print("[yellow]No documents found.[/yellow]")
        console.print(f"[dim]Add .md or .txt files to: {KNOWLEDGE_DIR}/[/dim]")
        return
    
    # Documents table
    doc_table = Table(title="Documents")
    doc_table.add_column("File", style="cyan")
    doc_table.add_column("Words", justify="right", style="green")
    doc_table.add_column("Characters", justify="right", style="blue")
    
    total_words = 0
    total_chars = 0
    for filename, content in documents.items():
        words = len(content.split())
        chars = len(content)
        total_words += words
        total_chars += chars
        doc_table.add_row(filename, f"{words:,}", f"{chars:,}")
    
    doc_table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_words:,}[/bold]",
        f"[bold]{total_chars:,}[/bold]",
    )
    console.print(doc_table)
    
    # ChromaDB status
    console.print(f"\n[bold]ChromaDB Status:[/bold]")
    if db_exists:
        console.print(f"  [green]✓ Database exists: {chunk_count} chunks indexed[/green]")
        console.print(f"  [dim]Location: {os.path.abspath(CHROMA_DIR)}[/dim]")
    else:
        console.print(f"  [yellow]⚠ Not built yet. Run build_knowledge_base() first.[/yellow]")





