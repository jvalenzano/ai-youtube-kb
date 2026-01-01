#!/usr/bin/env python3
"""
Export curated content to NotebookLM-ready artifacts.

Usage:
    python scripts/export_notebooklm.py
    python scripts/export_notebooklm.py --raw  # Export raw transcripts if curated not available
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
KB_DIR = PROJECT_ROOT / "kb"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
VIDEOS_DIR = NOTEBOOKS_DIR / "notebooklm-ready" / "videos"
MODULES_DIR = NOTEBOOKS_DIR / "notebooklm-ready" / "modules"
SLIDES_EXPORT_DIR = NOTEBOOKS_DIR / "notebooklm-ready" / "slides"

console = Console()

# Module definitions
MODULES = {
    "foundations": {
        "name": "Foundations of AI Agents",
        "description": "Core concepts, architectures, and fundamental principles of AI agents",
        "learning_objectives": [
            "Understand the core architecture of AI agents",
            "Learn fundamental decision-making patterns",
            "Grasp the key concepts in agentic AI systems",
        ],
    },
    "workflows": {
        "name": "Agentic Workflows & Orchestration",
        "description": "Patterns for multi-agent systems, orchestration, and workflow design",
        "learning_objectives": [
            "Design effective multi-agent orchestration patterns",
            "Implement agentic workflows for enterprise use cases",
            "Understand coordination and communication between agents",
        ],
    },
    "tooling": {
        "name": "Tooling & Frameworks",
        "description": "AI engineering tools, frameworks, and development practices",
        "learning_objectives": [
            "Evaluate and select AI agent frameworks",
            "Implement best practices for AI development",
            "Understand the modern AI development lifecycle",
        ],
    },
    "case_studies": {
        "name": "Case Studies & Lessons",
        "description": "Real-world applications, lessons learned, and anti-patterns",
        "learning_objectives": [
            "Learn from real-world AI agent deployments",
            "Identify common pitfalls and anti-patterns",
            "Apply lessons learned to your own projects",
        ],
    },
}


def ensure_dirs():
    """Create necessary directories."""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    MODULES_DIR.mkdir(parents=True, exist_ok=True)
    SLIDES_EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    # Remove or replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:100]  # Limit length
    return safe


def format_duration(seconds: int) -> str:
    """Format duration as HH:MM:SS or MM:SS."""
    if seconds is None:
        return "Unknown"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_timestamp_link(video_url: str, timestamp: str) -> str:
    """Create a YouTube link with timestamp."""
    # Parse MM:SS or HH:MM:SS to seconds
    parts = timestamp.split(':')
    if len(parts) == 2:
        seconds = int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
        return video_url

    return f"{video_url}&t={seconds}s"


def load_curated(video_id: str) -> Optional[dict]:
    """Load curated data for a video."""
    curated_file = DATA_CLEAN / f"{video_id}.json"
    if curated_file.exists():
        with open(curated_file) as f:
            return json.load(f)
    return None


def load_raw(video_id: str) -> Optional[dict]:
    """Load raw transcript for a video."""
    raw_file = DATA_RAW / f"{video_id}.json"
    if raw_file.exists():
        with open(raw_file) as f:
            return json.load(f)
    return None


def load_slides(video_id: str) -> list:
    """Load extracted slides for a video if available."""
    slide_meta = DATA_SLIDES / video_id / "metadata.json"
    if not slide_meta.exists():
        return []

    with open(slide_meta) as f:
        data = json.load(f)

    slides = []
    for slide in data.get('slides', []):
        # Only include unique slides (not duplicates)
        if slide.get('is_duplicate_of') is None:
            slides.append({
                'timestamp': slide.get('timestamp_formatted', ''),
                'timestamp_url': slide.get('timestamp_url', ''),
                'ocr_text': slide.get('ocr_text', ''),
                'filename': slide.get('filename', ''),
                'video_id': video_id,
            })
    return slides


def format_raw_transcript(raw_data: dict) -> str:
    """Format raw transcript segments into readable text."""
    segments = raw_data.get('transcript', {}).get('segments', [])

    lines = []
    current_paragraph = []
    last_timestamp = 0

    for seg in segments:
        start = seg.get('start', 0)
        text = seg.get('text', '').strip()

        # Add timestamp every 60 seconds
        if start - last_timestamp >= 60:
            if current_paragraph:
                lines.append(' '.join(current_paragraph))
                current_paragraph = []
            minutes = int(start // 60)
            seconds = int(start % 60)
            lines.append(f"\n[{minutes:02d}:{seconds:02d}]")
            last_timestamp = start

        current_paragraph.append(text)

        # Break on sentence endings
        if text.endswith(('.', '?', '!')):
            lines.append(' '.join(current_paragraph))
            current_paragraph = []

    if current_paragraph:
        lines.append(' '.join(current_paragraph))

    return '\n'.join(lines)


def export_video_curated(video_id: str, data: dict) -> Path:
    """Export a curated video to NotebookLM format."""
    title = data.get('title', video_id)
    safe_title = sanitize_filename(title)
    output_file = VIDEOS_DIR / f"{safe_title}.txt"

    content = []

    # Header
    content.append(f"# {title}")
    content.append("")
    content.append(f"**Video ID:** {video_id}")
    content.append(f"**Channel:** {data.get('channel', 'Unknown')}")
    content.append(f"**Duration:** {data.get('duration_formatted', format_duration(data.get('duration')))}")
    content.append(f"**URL:** {data.get('url', '')}")
    content.append("")

    # Module
    module_key = data.get('module', 'case_studies')
    module_info = MODULES.get(module_key, {})
    content.append(f"**Module:** {module_info.get('name', 'Unknown')}")
    if data.get('module_rationale'):
        content.append(f"**Module Rationale:** {data.get('module_rationale')}")
    content.append("")

    # Summary
    content.append("## Summary")
    for bullet in data.get('summary', []):
        content.append(f"- {bullet}")
    content.append("")

    # Key Takeaways
    content.append("## Key Takeaways")
    for takeaway in data.get('key_takeaways', []):
        prefix = "DO" if takeaway.get('type') == 'do' else "DON'T"
        content.append(f"- **{prefix}:** {takeaway.get('text', '')}")
    content.append("")

    # Topics
    content.append("## Topics")
    topics = data.get('topics', [])
    content.append(", ".join(topics) if topics else "No topics extracted")
    content.append("")

    # Highlights
    if data.get('highlights'):
        content.append("## Key Moments")
        for highlight in data.get('highlights', []):
            ts = highlight.get('timestamp', '')
            desc = highlight.get('description', '')
            link = format_timestamp_link(data.get('url', ''), ts)
            content.append(f"- [{ts}]({link}): {desc}")
        content.append("")

    # Slides
    slides = load_slides(video_id)
    if slides:
        content.append("## Presentation Slides")
        content.append(f"*{len(slides)} unique slides extracted from this video*")
        content.append("")
        for slide in slides:
            ts = slide.get('timestamp', '')
            ts_url = slide.get('timestamp_url', '')
            ocr = slide.get('ocr_text', '').strip()
            if ocr:
                content.append(f"### Slide at [{ts}]({ts_url})")
                content.append("")
                content.append(ocr)
                content.append("")
        content.append("")

    # One-liner (if available)
    if data.get('one_liner'):
        content.append("## TL;DR")
        content.append(data.get('one_liner'))
        content.append("")

    # Transcript - use raw transcript from data/raw/
    content.append("## Full Transcript")
    content.append("")
    raw_data = load_raw(video_id)
    if raw_data:
        content.append(format_raw_transcript(raw_data))
    else:
        content.append("Transcript not available")
    content.append("")
    
    # Attribution footer
    content.append("---")
    content.append("")
    content.append(f"*Content extracted from YouTube video. Original content by {data.get('channel', 'Unknown')}. Video URL: {data.get('url', '')}*")

    with open(output_file, 'w') as f:
        f.write('\n'.join(content))

    return output_file


def export_video_raw(video_id: str, data: dict) -> Path:
    """Export a raw video transcript to NotebookLM format."""
    title = data.get('title', video_id)
    safe_title = sanitize_filename(title)
    output_file = VIDEOS_DIR / f"{safe_title}.txt"

    content = []

    # Header
    content.append(f"# {title}")
    content.append("")
    content.append(f"**Video ID:** {video_id}")
    content.append(f"**Channel:** {data.get('channel', 'Unknown')}")
    content.append(f"**Duration:** {format_duration(data.get('duration'))}")
    content.append(f"**URL:** {data.get('url', '')}")
    content.append("")
    content.append("*Note: This is a raw transcript. Run `python scripts/curate.py` to generate summaries and analysis.*")
    content.append("")

    # Transcript
    content.append("## Transcript")
    content.append("")
    content.append(format_raw_transcript(data))
    content.append("")
    
    # Attribution footer
    content.append("---")
    content.append("")
    content.append(f"*Content extracted from YouTube video. Original content by {data.get('channel', 'Unknown')}. Video URL: {data.get('url', '')}*")

    with open(output_file, 'w') as f:
        f.write('\n'.join(content))

    return output_file


def export_module(module_key: str, videos: list[dict]) -> Path:
    """Export a module bundle to NotebookLM format."""
    module_info = MODULES.get(module_key, {})
    safe_name = sanitize_filename(module_info.get('name', module_key))
    output_file = MODULES_DIR / f"{safe_name}.md"

    content = []

    # Header
    content.append(f"# {module_info.get('name', module_key)}")
    content.append("")
    content.append(module_info.get('description', ''))
    content.append("")

    # Learning Objectives
    content.append("## Learning Objectives")
    for obj in module_info.get('learning_objectives', []):
        content.append(f"- {obj}")
    content.append("")

    # Videos in this module
    content.append("## Videos in This Module")
    content.append("")

    for i, video in enumerate(videos, 1):
        content.append(f"### {i}. {video.get('title', 'Unknown')}")
        content.append(f"**URL:** {video.get('url', '')}")
        content.append(f"**Duration:** {video.get('duration_formatted', format_duration(video.get('duration')))}")
        content.append("")

        # Summary
        if video.get('summary'):
            content.append("**Summary:**")
            for bullet in video.get('summary', [])[:3]:  # First 3 bullets
                content.append(f"- {bullet}")
            content.append("")

        # Key takeaways
        if video.get('key_takeaways'):
            content.append("**Key Takeaways:**")
            for takeaway in video.get('key_takeaways', [])[:2]:
                prefix = "DO" if takeaway.get('type') == 'do' else "DON'T"
                content.append(f"- **{prefix}:** {takeaway.get('text', '')}")
            content.append("")

        content.append("---")
        content.append("")

    with open(output_file, 'w') as f:
        f.write('\n'.join(content))

    return output_file


def export_youtube_urls():
    """Export YouTube URLs for direct NotebookLM import."""
    metadata_file = KB_DIR / "metadata.json"
    if not metadata_file.exists():
        console.print("[yellow]No metadata found. Run ingest.py first.[/yellow]")
        return

    with open(metadata_file) as f:
        metadata = json.load(f)

    urls = [v.get('url', '') for v in metadata.get('videos', []) if v.get('url')]

    url_file = NOTEBOOKS_DIR / "youtube-urls.txt"
    with open(url_file, 'w') as f:
        f.write('\n'.join(urls))

    console.print(f"[green]Saved {len(urls)} URLs to {url_file}[/green]")


@click.command()
@click.option('--raw', '-r', is_flag=True, help='Export raw transcripts if curated not available')
@click.option('--modules-only', '-m', is_flag=True, help='Only generate module bundles')
def main(raw: bool, modules_only: bool):
    """Export content to NotebookLM-ready artifacts."""
    ensure_dirs()

    # Get all video IDs
    curated_files = list(DATA_CLEAN.glob("*.json"))
    raw_files = list(DATA_RAW.glob("*.json"))

    curated_ids = {f.stem for f in curated_files}
    raw_ids = {f.stem for f in raw_files}

    console.print(f"[blue]Found {len(curated_ids)} curated, {len(raw_ids)} raw transcripts[/blue]")

    # Export videos
    if not modules_only:
        exported = 0
        videos_by_module = {}

        for video_id in raw_ids:
            curated_data = load_curated(video_id)

            if curated_data:
                output = export_video_curated(video_id, curated_data)
                module = curated_data.get('module', 'case_studies')
                if module not in videos_by_module:
                    videos_by_module[module] = []
                videos_by_module[module].append(curated_data)
                exported += 1
            elif raw:
                raw_data = load_raw(video_id)
                if raw_data:
                    output = export_video_raw(video_id, raw_data)
                    exported += 1

        console.print(f"[green]Exported {exported} videos to {VIDEOS_DIR}[/green]")

    # Export module bundles (only if we have curated data)
    if curated_ids:
        videos_by_module = {}
        for video_id in curated_ids:
            curated_data = load_curated(video_id)
            if curated_data:
                module = curated_data.get('module', 'case_studies')
                if module not in videos_by_module:
                    videos_by_module[module] = []
                videos_by_module[module].append(curated_data)

        for module_key, videos in videos_by_module.items():
            if videos:
                output = export_module(module_key, videos)
                console.print(f"[green]Exported module: {MODULES.get(module_key, {}).get('name', module_key)} ({len(videos)} videos)[/green]")

    # Export YouTube URLs
    export_youtube_urls()

    # Summary
    console.print("\n[bold]NotebookLM Import Instructions:[/bold]")
    console.print("1. Go to https://notebooklm.google.com")
    console.print("2. Create a new notebook")
    console.print("3. Click 'Add source' and either:")
    console.print(f"   a. Drag/drop files from {VIDEOS_DIR}")
    console.print(f"   b. Paste URLs from {NOTEBOOKS_DIR / 'youtube-urls.txt'}")
    console.print("4. NotebookLM will auto-generate study guides and allow Q&A!")


if __name__ == '__main__':
    main()
