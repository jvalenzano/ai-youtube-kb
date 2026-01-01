#!/usr/bin/env python3
"""
Curate transcripts using Claude: clean, summarize, tag, and assign modules.

Usage:
    python scripts/curate.py --video VIDEO_ID
    python scripts/curate.py --all
    python scripts/curate.py --status
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import click
from anthropic import Anthropic
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"
KB_DIR = PROJECT_ROOT / "kb"

console = Console()

# Module definitions
MODULES = {
    "foundations": {
        "name": "Foundations of AI Agents",
        "description": "Core concepts, architectures, and fundamental principles of AI agents",
        "keywords": ["fundamentals", "architecture", "basics", "concepts", "decision-making", "reasoning"],
    },
    "workflows": {
        "name": "Agentic Workflows & Orchestration",
        "description": "Patterns for multi-agent systems, orchestration, and workflow design",
        "keywords": ["workflow", "orchestration", "multi-agent", "patterns", "automation", "pipeline"],
    },
    "tooling": {
        "name": "Tooling & Frameworks",
        "description": "AI engineering tools, frameworks, and development practices",
        "keywords": ["tools", "frameworks", "development", "engineering", "implementation", "SDLC"],
    },
    "case_studies": {
        "name": "Case Studies & Lessons",
        "description": "Real-world applications, lessons learned, and anti-patterns",
        "keywords": ["case study", "lessons", "real-world", "enterprise", "business", "transformation"],
    },
}

CURATION_PROMPT = """You are an expert AI researcher and educator. Analyze this video transcript about AI agents and agentic workflows.

VIDEO METADATA:
Title: {title}
Channel: {channel}
Duration: {duration} seconds
URL: {url}

TRANSCRIPT:
{transcript}

Please provide a structured analysis in the following JSON format:

{{
    "summary": [
        "Bullet point 1 (key insight or topic covered)",
        "Bullet point 2",
        "... (5-10 total bullet points)"
    ],
    "key_takeaways": [
        {{
            "type": "do",
            "text": "Actionable recommendation from the video"
        }},
        {{
            "type": "dont",
            "text": "Anti-pattern or thing to avoid mentioned in the video"
        }}
    ],
    "topics": ["topic1", "topic2", "topic3"],
    "module": "One of: foundations, workflows, tooling, case_studies",
    "module_rationale": "Brief explanation of why this module was chosen",
    "highlights": [
        {{
            "timestamp": "MM:SS",
            "description": "Brief description of what's discussed at this timestamp"
        }}
    ],
    "one_liner": "A single sentence (max 20 words) capturing the core message of this video"
}}

Guidelines:
- For summary: Focus on the main ideas, not every detail. 5-10 bullet points.
- For key_takeaways: Extract practical do/don't guidance. 3-6 items total.
- For topics: 3-7 relevant topics/keywords for this video.
- For module: Choose the BEST fit from the 4 options based on primary content.
- For highlights: 3-5 key moments with timestamps (format: MM:SS)

Respond with valid JSON only. No markdown formatting."""


def ensure_dirs():
    """Create necessary directories."""
    DATA_CLEAN.mkdir(parents=True, exist_ok=True)


def load_raw_transcript(video_id: str) -> Optional[dict]:
    """Load a raw transcript file."""
    transcript_file = DATA_RAW / f"{video_id}.json"
    if transcript_file.exists():
        with open(transcript_file) as f:
            return json.load(f)
    return None


def get_raw_video_ids() -> list[str]:
    """Get list of video IDs with raw transcripts."""
    return [f.stem for f in DATA_RAW.glob("*.json")]


def get_curated_video_ids() -> list[str]:
    """Get list of video IDs with curated data."""
    return [f.stem for f in DATA_CLEAN.glob("*.json")]


def format_transcript_for_prompt(transcript_data: dict) -> str:
    """Format transcript segments into readable text with timestamps."""
    segments = transcript_data.get('transcript', {}).get('segments', [])

    lines = []
    current_paragraph = []
    last_timestamp = 0

    for seg in segments:
        start = seg.get('start', 0)
        text = seg.get('text', '').strip()

        # Add timestamp every 60 seconds or so
        if start - last_timestamp >= 60:
            if current_paragraph:
                lines.append(' '.join(current_paragraph))
                current_paragraph = []
            minutes = int(start // 60)
            seconds = int(start % 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}]")
            last_timestamp = start

        current_paragraph.append(text)

        # Break on sentence endings
        if text.endswith(('.', '?', '!')):
            lines.append(' '.join(current_paragraph))
            current_paragraph = []

    if current_paragraph:
        lines.append(' '.join(current_paragraph))

    return '\n'.join(lines)


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


def curate_video(video_id: str, client: Anthropic) -> Optional[dict]:
    """Use Claude to curate a video transcript."""
    raw_data = load_raw_transcript(video_id)
    if not raw_data:
        console.print(f"[red]No raw transcript found for {video_id}[/red]")
        return None

    # Prepare prompt
    transcript_text = format_transcript_for_prompt(raw_data)

    # Truncate if too long (Claude has context limits)
    max_chars = 100000  # Conservative limit
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars] + "\n\n[TRANSCRIPT TRUNCATED]"

    prompt = CURATION_PROMPT.format(
        title=raw_data.get('title', 'Unknown'),
        channel=raw_data.get('channel', 'Unknown'),
        duration=raw_data.get('duration', 'Unknown'),
        url=raw_data.get('url', ''),
        transcript=transcript_text,
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # Parse JSON response
        # Handle potential markdown code blocks
        if response_text.startswith('```'):
            response_text = response_text.split('\n', 1)[1]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

        curation = json.loads(response_text)

        # Add metadata
        result = {
            'video_id': video_id,
            'title': raw_data.get('title'),
            'channel': raw_data.get('channel'),
            'url': raw_data.get('url'),
            'duration': raw_data.get('duration'),
            'duration_formatted': format_duration(raw_data.get('duration')),
            'upload_date': raw_data.get('upload_date'),
            'curated_at': datetime.now().isoformat(),
            **curation,
        }

        return result

    except json.JSONDecodeError as e:
        console.print(f"[red]Failed to parse Claude response as JSON: {e}[/red]")
        console.print(f"Response was: {response_text[:500]}...")
        return None
    except Exception as e:
        console.print(f"[red]Error curating {video_id}: {e}[/red]")
        return None


def save_curated(video_id: str, data: dict):
    """Save curated data to data/clean/{video_id}.json."""
    output_file = DATA_CLEAN / f"{video_id}.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    return output_file


@click.command()
@click.option('--video', '-v', help='Single video ID to curate')
@click.option('--all', '-a', 'curate_all', is_flag=True, help='Curate all raw transcripts')
@click.option('--status', '-s', is_flag=True, help='Show curation status')
@click.option('--force', '-f', is_flag=True, help='Force re-curation even if already curated')
def main(video: Optional[str], curate_all: bool, status: bool, force: bool):
    """Curate video transcripts using Claude."""
    ensure_dirs()

    # Check for API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        console.print("[red]ANTHROPIC_API_KEY environment variable not set[/red]")
        console.print("Set it with: export ANTHROPIC_API_KEY=your_key")
        return

    if status:
        raw_ids = set(get_raw_video_ids())
        curated_ids = set(get_curated_video_ids())

        table = Table(title="Curation Status")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green")

        table.add_row("Raw transcripts", str(len(raw_ids)))
        table.add_row("Curated", str(len(curated_ids)))
        table.add_row("Pending", str(len(raw_ids - curated_ids)))

        console.print(table)

        if raw_ids - curated_ids:
            console.print("\n[yellow]Pending videos:[/yellow]")
            for vid in sorted(raw_ids - curated_ids):
                console.print(f"  - {vid}")
        return

    client = Anthropic()

    if video:
        console.print(f"[blue]Curating video: {video}[/blue]")

        # Check if already curated
        if not force and (DATA_CLEAN / f"{video}.json").exists():
            console.print("[yellow]Already curated. Use --force to re-curate.[/yellow]")
            return

        result = curate_video(video, client)
        if result:
            output_file = save_curated(video, result)
            console.print(f"[green]Saved to {output_file}[/green]")

            # Show summary
            console.print("\n[bold]Summary:[/bold]")
            for bullet in result.get('summary', [])[:5]:
                console.print(f"  • {bullet}")

            console.print(f"\n[bold]Module:[/bold] {result.get('module')} - {MODULES.get(result.get('module', ''), {}).get('name', 'Unknown')}")
        return

    if curate_all:
        raw_ids = get_raw_video_ids()
        curated_ids = set(get_curated_video_ids())

        pending = [vid for vid in raw_ids if force or vid not in curated_ids]

        if not pending:
            console.print("[green]All videos already curated![/green]")
            return

        console.print(f"[blue]Curating {len(pending)} videos...[/blue]")

        success = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Curating...", total=len(pending))

            for vid in pending:
                raw_data = load_raw_transcript(vid)
                title = raw_data.get('title', vid) if raw_data else vid
                progress.update(task, description=f"[{vid}] {title[:40]}...")

                result = curate_video(vid, client)
                if result:
                    save_curated(vid, result)
                    success += 1
                else:
                    failed += 1

                progress.advance(task)

        console.print(f"\n[green]Successfully curated: {success}[/green]")
        if failed:
            console.print(f"[yellow]Failed: {failed}[/yellow]")
        return

    # No args - show help
    ctx = click.get_current_context()
    click.echo(ctx.get_help())


if __name__ == '__main__':
    main()
