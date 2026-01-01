#!/usr/bin/env python3
"""
Ingest YouTube playlist: discover videos, extract transcripts.

Usage:
    python scripts/ingest.py --playlist URL
    python scripts/ingest.py --list
    python scripts/ingest.py --video VIDEO_ID
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import click
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
KB_DIR = PROJECT_ROOT / "kb"

console = Console()


def ensure_dirs():
    """Create necessary directories."""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    KB_DIR.mkdir(parents=True, exist_ok=True)


def extract_playlist_metadata(playlist_url: str) -> list[dict]:
    """
    Extract video metadata from a YouTube playlist.

    Returns list of dicts with: video_id, title, channel, duration, url, upload_date
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }

    videos = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(playlist_url, download=False)

        if 'entries' not in result:
            console.print("[red]No videos found in playlist[/red]")
            return []

        for entry in result['entries']:
            if entry is None:
                continue

            video = {
                'video_id': entry.get('id'),
                'title': entry.get('title'),
                'channel': entry.get('uploader') or entry.get('channel'),
                'duration': entry.get('duration'),
                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                'upload_date': entry.get('upload_date'),
            }
            videos.append(video)

    return videos


def get_video_details(video_id: str) -> Optional[dict]:
    """Get detailed metadata for a single video."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    url = f"https://www.youtube.com/watch?v={video_id}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(url, download=False)
            return {
                'video_id': result.get('id'),
                'title': result.get('title'),
                'channel': result.get('uploader') or result.get('channel'),
                'duration': result.get('duration'),
                'duration_string': result.get('duration_string'),
                'url': url,
                'upload_date': result.get('upload_date'),
                'description': result.get('description', ''),
                'view_count': result.get('view_count'),
                'like_count': result.get('like_count'),
            }
        except Exception as e:
            console.print(f"[red]Error getting video details: {e}[/red]")
            return None


def extract_transcript_ytdlp(video_id: str) -> Optional[dict]:
    """Fallback: Extract transcript using yt-dlp subtitles."""
    import tempfile
    import os

    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'subtitlesformat': 'json3',
            'skip_download': True,
            'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Look for subtitle file
            for ext in ['.en.json3', '.en-orig.json3']:
                sub_file = os.path.join(tmpdir, f"{video_id}{ext}")
                if os.path.exists(sub_file):
                    with open(sub_file) as f:
                        data = json.load(f)

                    segments = []
                    for event in data.get('events', []):
                        if 'segs' in event:
                            text = ''.join(s.get('utf8', '') for s in event['segs'])
                            if text.strip():
                                segments.append({
                                    'start': event.get('tStartMs', 0) / 1000,
                                    'duration': event.get('dDurationMs', 0) / 1000,
                                    'text': text.strip(),
                                })

                    if segments:
                        return {
                            'segments': segments,
                            'language': 'en',
                            'is_generated': True,
                        }

            return None
        except Exception as e:
            console.print(f"[yellow]yt-dlp fallback failed: {e}[/yellow]")
            return None


def extract_transcript(video_id: str) -> Optional[dict]:
    """
    Extract transcript for a video.

    Returns dict with:
        - segments: list of {start, duration, text}
        - language: transcript language
        - is_generated: whether it's auto-generated
    """
    try:
        # Create API instance (new API style)
        api = YouTubeTranscriptApi()

        # Try to get transcript list
        transcript_list = api.list(video_id)

        # Prefer manual transcripts
        transcript = None
        is_generated = False

        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                is_generated = True
            except NoTranscriptFound:
                # Try any available transcript
                for t in transcript_list:
                    transcript = t
                    is_generated = t.is_generated
                    break

        if transcript is None:
            return None

        fetched = transcript.fetch()
        # Convert to list of dicts
        segments = [{'start': s.start, 'duration': s.duration, 'text': s.text} for s in fetched]

        return {
            'segments': segments,
            'language': transcript.language_code,
            'is_generated': is_generated,
        }

    except TranscriptsDisabled:
        console.print(f"[yellow]Transcripts disabled for {video_id}[/yellow]")
        return None
    except NoTranscriptFound:
        console.print(f"[yellow]No transcript found for {video_id}[/yellow]")
        return None
    except Exception as e:
        # Try yt-dlp fallback
        console.print(f"[yellow]Trying yt-dlp fallback for {video_id}...[/yellow]")
        result = extract_transcript_ytdlp(video_id)
        if result:
            console.print(f"[green]yt-dlp fallback succeeded![/green]")
            return result
        console.print(f"[red]All methods failed for {video_id}[/red]")
        return None


def save_metadata(videos: list[dict]):
    """Save playlist metadata to kb/metadata.json."""
    metadata_file = KB_DIR / "metadata.json"

    data = {
        'last_updated': datetime.now().isoformat(),
        'video_count': len(videos),
        'videos': videos,
    }

    with open(metadata_file, 'w') as f:
        json.dump(data, f, indent=2)

    console.print(f"[green]Saved metadata for {len(videos)} videos to {metadata_file}[/green]")


def save_transcript(video_id: str, video_metadata: dict, transcript_data: dict):
    """Save raw transcript to data/raw/{video_id}.json."""
    transcript_file = DATA_RAW / f"{video_id}.json"

    data = {
        'video_id': video_id,
        'title': video_metadata.get('title'),
        'channel': video_metadata.get('channel'),
        'url': video_metadata.get('url'),
        'duration': video_metadata.get('duration'),
        'upload_date': video_metadata.get('upload_date'),
        'transcript': transcript_data,
        'extracted_at': datetime.now().isoformat(),
    }

    with open(transcript_file, 'w') as f:
        json.dump(data, f, indent=2)

    return transcript_file


def load_metadata() -> Optional[dict]:
    """Load existing metadata."""
    metadata_file = KB_DIR / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            return json.load(f)
    return None


@click.command()
@click.option('--playlist', '-p', help='YouTube playlist URL to ingest')
@click.option('--video', '-v', help='Single video ID to ingest')
@click.option('--list', '-l', 'list_videos', is_flag=True, help='List ingested videos')
@click.option('--transcripts-only', '-t', is_flag=True, help='Only extract transcripts (skip metadata refresh)')
def main(playlist: Optional[str], video: Optional[str], list_videos: bool, transcripts_only: bool):
    """Ingest YouTube playlist or single video."""
    ensure_dirs()

    if list_videos:
        metadata = load_metadata()
        if not metadata:
            console.print("[yellow]No metadata found. Run with --playlist first.[/yellow]")
            return

        table = Table(title="Ingested Videos")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Duration", style="green")
        table.add_column("Transcript", style="yellow")

        for v in metadata.get('videos', []):
            transcript_file = DATA_RAW / f"{v['video_id']}.json"
            has_transcript = "Yes" if transcript_file.exists() else "No"
            duration = str(v.get('duration', 'N/A'))
            table.add_row(v['video_id'], v['title'][:50], duration, has_transcript)

        console.print(table)
        return

    if video:
        # Single video mode
        console.print(f"[blue]Ingesting single video: {video}[/blue]")

        video_meta = get_video_details(video)
        if not video_meta:
            console.print("[red]Failed to get video details[/red]")
            return

        console.print(f"[green]Found: {video_meta['title']}[/green]")

        transcript = extract_transcript(video)
        if transcript:
            save_transcript(video, video_meta, transcript)
            console.print(f"[green]Saved transcript ({len(transcript['segments'])} segments)[/green]")
        else:
            console.print("[yellow]No transcript available[/yellow]")
        return

    if playlist:
        # Full playlist mode
        console.print(f"[blue]Ingesting playlist: {playlist}[/blue]")

        # Extract playlist metadata
        with console.status("[bold blue]Extracting playlist metadata..."):
            videos = extract_playlist_metadata(playlist)

        if not videos:
            console.print("[red]No videos found[/red]")
            return

        console.print(f"[green]Found {len(videos)} videos[/green]")

        # Save metadata
        save_metadata(videos)

        # Extract transcripts
        success_count = 0
        fail_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting transcripts...", total=len(videos))

            for v in videos:
                video_id = v['video_id']
                progress.update(task, description=f"[{video_id}] {v['title'][:40]}...")

                # Check if already extracted
                transcript_file = DATA_RAW / f"{video_id}.json"
                if transcript_file.exists() and transcripts_only:
                    progress.advance(task)
                    success_count += 1
                    continue

                # Get detailed metadata
                video_meta = get_video_details(video_id)
                if not video_meta:
                    video_meta = v  # Fall back to playlist metadata

                # Extract transcript
                transcript = extract_transcript(video_id)
                if transcript:
                    save_transcript(video_id, video_meta, transcript)
                    success_count += 1
                else:
                    fail_count += 1

                progress.advance(task)

        console.print(f"\n[green]Successfully extracted: {success_count}[/green]")
        if fail_count:
            console.print(f"[yellow]Failed/missing: {fail_count}[/yellow]")

        return

    # No args - show help
    ctx = click.get_current_context()
    click.echo(ctx.get_help())


if __name__ == '__main__':
    main()
