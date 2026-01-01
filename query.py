#!/usr/bin/env python3
"""
CLI query tool for the AI Agents Knowledge Base.

Uses sentence-transformers + numpy for local semantic search.

Usage:
    python query.py "question about agentic workflows"
    python query.py --build   # Build/rebuild the vector index
    python query.py --list    # List indexed content
"""

import json
import os
import sys
import pickle
from pathlib import Path
from typing import Optional

import click
import numpy as np
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
KB_DIR = PROJECT_ROOT / "kb"
INDEX_FILE = KB_DIR / "vector_index.pkl"

console = Console()

# Global model cache
_model = None


def get_model():
    """Get sentence-transformers model (cached)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def chunk_transcript(video_data: dict, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    """
    Chunk a video transcript into overlapping segments.

    Returns list of chunks with metadata.
    """
    # Get transcript text
    raw_file = DATA_RAW / f"{video_data['video_id']}.json"
    if not raw_file.exists():
        return []

    with open(raw_file) as f:
        raw_data = json.load(f)

    segments = raw_data.get('transcript', {}).get('segments', [])
    if not segments:
        return []

    # Build full text with timestamps
    full_text = []
    timestamps = []

    for seg in segments:
        text = seg.get('text', '').strip()
        start = seg.get('start', 0)
        if text:
            full_text.append(text)
            timestamps.append(start)

    # Join into paragraphs
    text = ' '.join(full_text)
    words = text.split()

    chunks = []
    i = 0
    chunk_id = 0

    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)

        # Estimate timestamp (rough approximation)
        word_ratio = i / max(len(words), 1)
        if timestamps:
            approx_timestamp = timestamps[int(word_ratio * len(timestamps))]
        else:
            approx_timestamp = 0

        mins = int(approx_timestamp // 60)
        secs = int(approx_timestamp % 60)

        chunks.append({
            'id': f"{video_data['video_id']}_{chunk_id}",
            'text': chunk_text,
            'video_id': video_data['video_id'],
            'title': video_data.get('title', ''),
            'url': video_data.get('url', ''),
            'timestamp': f"{mins:02d}:{secs:02d}",
            'timestamp_url': f"{video_data.get('url', '')}&t={int(approx_timestamp)}s",
            'module': video_data.get('module', ''),
            'topics': ', '.join(video_data.get('topics', [])),
        })

        i += chunk_size - overlap
        chunk_id += 1

    return chunks


def build_index():
    """Build the vector index from curated videos."""
    console.print("[blue]Building vector index...[/blue]")

    model = get_model()

    # Load all curated videos
    curated_files = list(DATA_CLEAN.glob("*.json"))

    all_chunks = []
    for f in curated_files:
        with open(f) as fp:
            video_data = json.load(fp)

        chunks = chunk_transcript(video_data)
        all_chunks.extend(chunks)

        # Also add summary as a searchable chunk
        summary = video_data.get('summary', [])
        if summary:
            summary_text = ' '.join(summary)
            all_chunks.append({
                'id': f"{video_data['video_id']}_summary",
                'text': f"Summary of {video_data.get('title', '')}: {summary_text}",
                'video_id': video_data['video_id'],
                'title': video_data.get('title', ''),
                'url': video_data.get('url', ''),
                'timestamp': '00:00',
                'timestamp_url': video_data.get('url', ''),
                'module': video_data.get('module', ''),
                'topics': ', '.join(video_data.get('topics', [])),
            })

    # Add slide OCR text as searchable chunks
    slide_count = 0
    if DATA_SLIDES.exists():
        for slide_dir in DATA_SLIDES.iterdir():
            if not slide_dir.is_dir():
                continue
            metadata_file = slide_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            with open(metadata_file) as fp:
                slide_data = json.load(fp)

            video_id = slide_data.get('video_id', '')
            title = slide_data.get('title', '')
            base_url = slide_data.get('url', '')

            for slide in slide_data.get('slides', []):
                ocr_text = slide.get('ocr_text', '').strip()
                if not ocr_text or len(ocr_text) < 20:
                    continue

                timestamp = slide.get('timestamp_formatted', '')
                timestamp_url = slide.get('timestamp_url', '')

                # Create searchable chunk from slide OCR
                all_chunks.append({
                    'id': f"{video_id}_slide_{timestamp}",
                    'text': f"Slide at {timestamp}: {ocr_text}",
                    'video_id': video_id,
                    'title': title,
                    'url': base_url,
                    'timestamp': timestamp,
                    'timestamp_url': timestamp_url,
                    'module': '',
                    'topics': 'slide',
                })
                slide_count += 1

    if slide_count > 0:
        console.print(f"[blue]Added {slide_count} slide OCR chunks[/blue]")

    if not all_chunks:
        console.print("[yellow]No chunks to index. Run curation first.[/yellow]")
        return

    # Generate embeddings
    console.print(f"[blue]Generating embeddings for {len(all_chunks)} chunks...[/blue]")
    texts = [c['text'] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True)

    # Save index
    index_data = {
        'chunks': all_chunks,
        'embeddings': embeddings,
    }

    with open(INDEX_FILE, 'wb') as f:
        pickle.dump(index_data, f)

    console.print(f"[green]Indexed {len(all_chunks)} chunks from {len(curated_files)} videos[/green]")
    console.print(f"[green]Saved to {INDEX_FILE}[/green]")


def query_index(question: str, n_results: int = 5) -> list[dict]:
    """Query the vector index using cosine similarity."""
    if not INDEX_FILE.exists():
        console.print("[yellow]Index not found. Run: python query.py --build[/yellow]")
        return []

    # Load index
    with open(INDEX_FILE, 'rb') as f:
        index_data = pickle.load(f)

    chunks = index_data['chunks']
    embeddings = index_data['embeddings']

    # Encode query
    model = get_model()
    query_embedding = model.encode([question])[0]

    # Compute cosine similarity
    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )

    # Get top results
    top_indices = np.argsort(similarities)[::-1][:n_results]

    results = []
    for idx in top_indices:
        chunk = chunks[idx]
        results.append({
            'id': chunk['id'],
            'text': chunk['text'],
            'metadata': {
                'video_id': chunk['video_id'],
                'title': chunk['title'],
                'url': chunk['url'],
                'timestamp': chunk['timestamp'],
                'timestamp_url': chunk['timestamp_url'],
                'module': chunk['module'],
                'topics': chunk['topics'],
            },
            'similarity': float(similarities[idx]),
        })

    return results


def format_answer(question: str, chunks: list[dict]) -> str:
    """Format search results as a readable answer."""
    if not chunks:
        return "No relevant content found. Try building the index first: `python query.py --build`"

    lines = []
    lines.append(f"## Results for: \"{question}\"\n")

    # Group by video
    by_video = {}
    for chunk in chunks:
        vid = chunk['metadata']['video_id']
        if vid not in by_video:
            by_video[vid] = {
                'title': chunk['metadata']['title'],
                'url': chunk['metadata']['url'],
                'module': chunk['metadata']['module'],
                'chunks': []
            }
        by_video[vid]['chunks'].append(chunk)

    for vid, data in by_video.items():
        lines.append(f"### [{data['title']}]({data['url']})")
        lines.append(f"*Module: {data['module']}*\n")

        for chunk in data['chunks'][:2]:  # Top 2 chunks per video
            ts = chunk['metadata']['timestamp']
            ts_url = chunk['metadata']['timestamp_url']
            text = chunk['text'][:300] + "..." if len(chunk['text']) > 300 else chunk['text']
            lines.append(f"**[{ts}]({ts_url})**")
            lines.append(f"> {text}\n")

    lines.append("\n---")
    lines.append("*Use NotebookLM for more detailed Q&A with source citations.*")

    return '\n'.join(lines)


@click.command()
@click.argument('question', required=False)
@click.option('--build', '-b', is_flag=True, help='Build/rebuild the vector index')
@click.option('--list', '-l', 'list_index', is_flag=True, help='List indexed content')
@click.option('--results', '-n', default=5, help='Number of results to return')
def main(question: Optional[str], build: bool, list_index: bool, results: int):
    """Query the AI Agents Knowledge Base."""

    if build:
        build_index()
        return

    if list_index:
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'rb') as f:
                index_data = pickle.load(f)
            console.print(f"[green]Index contains {len(index_data['chunks'])} chunks[/green]")
        else:
            console.print("[yellow]No index found. Run: python query.py --build[/yellow]")
        return

    if not question:
        console.print("[yellow]Usage: python query.py \"your question here\"[/yellow]")
        console.print("       python query.py --build  (to build index)")
        return

    # Check if index exists
    if not INDEX_FILE.exists():
        console.print("[yellow]Building index for first time...[/yellow]")
        build_index()

    chunks = query_index(question, n_results=results)
    answer = format_answer(question, chunks)

    console.print(Markdown(answer))


if __name__ == '__main__':
    main()
