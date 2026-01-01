#!/usr/bin/env python3
"""
Fix transition duplicates - Remove slides caught during transitions.

When slides transition, we sometimes capture both the transition frame (blurry)
and the final frame (clear). This script removes the earlier transition frame
if two slides are very close together in time (< 5 seconds).

Usage:
    python scripts/fix_transition_duplicates.py --video VIDEO_ID
    python scripts/fix_transition_duplicates.py --all
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm

sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import DATA_SLIDES
from curation_progress import select_video_interactive

PROJECT_ROOT = Path(__file__).parent.parent
console = Console()

# Threshold: if slides are less than this many seconds apart, consider removing the earlier one
TRANSITION_THRESHOLD = 5.0  # seconds


def parse_timestamp_from_filename(filename: str) -> Optional[float]:
    """Parse timestamp from slide filename like 'slide_18m52s_f580eaca.png'."""
    try:
        # Extract timestamp part (e.g., "18m52s")
        parts = filename.split('_')
        if len(parts) < 2:
            return None
        
        time_str = parts[1]  # e.g., "18m52s"
        
        # Parse minutes and seconds
        if 'm' in time_str and 's' in time_str:
            mins_str, secs_str = time_str.split('m')
            secs_str = secs_str.rstrip('s')
            minutes = int(mins_str)
            seconds = int(secs_str)
            return minutes * 60 + seconds
    except Exception:
        pass
    return None


def find_transition_duplicates(video_id: str, threshold: float = TRANSITION_THRESHOLD) -> list[tuple[str, str]]:
    """
    Find pairs of slides that are very close together in time.
    Returns list of (earlier_slide, later_slide) tuples.
    """
    slide_dir = DATA_SLIDES / video_id
    if not slide_dir.exists():
        return []
    
    # Get all slide files with their timestamps
    slide_files = list(slide_dir.glob("slide_*.png"))
    slides_with_times = []
    
    for slide_file in slide_files:
        timestamp = parse_timestamp_from_filename(slide_file.name)
        if timestamp is not None:
            slides_with_times.append((slide_file, timestamp))
    
    # Sort by timestamp
    slides_with_times.sort(key=lambda x: x[1])
    
    # Find pairs that are close together
    duplicates = []
    for i in range(len(slides_with_times) - 1):
        slide1, time1 = slides_with_times[i]
        slide2, time2 = slides_with_times[i + 1]
        
        time_diff = time2 - time1
        
        if 0 < time_diff < threshold:
            # These are close together - likely a transition duplicate
            duplicates.append((slide1.name, slide2.name, time_diff))
    
    return duplicates


def process_video(video_id: str, dry_run: bool = False, threshold: float = TRANSITION_THRESHOLD) -> dict:
    """Find and optionally remove transition duplicates for a video."""
    slide_dir = DATA_SLIDES / video_id
    if not slide_dir.exists():
        console.print(f"[red]No slides directory found for {video_id}[/red]")
        return {'error': 'No slides directory'}
    
    duplicates = find_transition_duplicates(video_id, threshold)
    
    if not duplicates:
        console.print(f"[green]✓ No transition duplicates found for {video_id}[/green]")
        return {
            'video_id': video_id,
            'removed': 0,
            'pairs_found': 0
        }
    
    console.print(f"\n[bold]Found {len(duplicates)} transition duplicate pairs:[/bold]")
    for earlier, later, time_diff in duplicates:
        console.print(f"  [dim]• {earlier} → {later} ({time_diff:.1f}s apart)[/dim]")
    
    if dry_run:
        console.print(f"\n[yellow]DRY RUN: Would remove {len(duplicates)} earlier slides[/yellow]")
        return {
            'video_id': video_id,
            'dry_run': True,
            'would_remove': len(duplicates),
            'pairs_found': len(duplicates)
        }
    
    # Remove earlier slides
    removed = []
    for earlier, later, time_diff in duplicates:
        earlier_path = slide_dir / earlier
        if earlier_path.exists():
            earlier_path.unlink()
            removed.append(earlier)
    
    # Update metadata
    metadata_file = slide_dir / "metadata.json"
    if metadata_file.exists() and removed:
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            # Remove from slides list
            original_count = len(metadata.get('slides', []))
            metadata['slides'] = [
                slide for slide in metadata.get('slides', [])
                if slide['filename'] not in removed
            ]
            
            # Update stats
            metadata['stats']['slides_detected'] = len(metadata['slides'])
            metadata['stats']['unique_slides'] = len(metadata['slides'])
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            console.print(f"\n[green]✓ Removed {len(removed)} transition duplicates[/green]")
            console.print(f"[dim]  Updated metadata: {original_count} → {len(metadata['slides'])} slides[/dim]")
        except Exception as e:
            console.print(f"[yellow]Could not update metadata: {e}[/yellow]")
    
    return {
        'video_id': video_id,
        'removed': len(removed),
        'pairs_found': len(duplicates)
    }


@click.command()
@click.option('--video', '-v', help='Single video ID to fix (omit for interactive selection)')
@click.option('--all', '-a', 'process_all', is_flag=True, help='Process all videos')
@click.option('--dry-run', '-d', is_flag=True, help='Preview without removing files')
@click.option('--threshold', '-t', default=5.0, type=float, help='Time threshold in seconds (default: 5.0)')
def main(video: str, process_all: bool, dry_run: bool, threshold: float):
    """Fix transition duplicates - Remove slides caught during transitions."""
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be deleted[/yellow]\n")
    
    if video:
        result = process_video(video, dry_run, threshold)
        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        
        if not dry_run and result.get('removed', 0) > 0:
            console.print(f"\n[bold]Next step:[/bold] Sync metadata")
            console.print(f"[dim]python scripts/sync_slide_metadata.py --video {video}[/dim]")
    
    elif not process_all:
        # Interactive video selection
        console.print("\n[bold]Interactive Video Selection[/bold]")
        selected_video = select_video_interactive("Select a video to fix transition duplicates")
        if selected_video:
            result = process_video(selected_video, dry_run, threshold)
            if 'error' in result:
                console.print(f"[red]Error: {result['error']}[/red]")
                sys.exit(1)
            
            if not dry_run and result.get('removed', 0) > 0:
                console.print(f"\n[bold]Next step:[/bold] Sync metadata")
                console.print(f"[dim]python scripts/sync_slide_metadata.py --video {selected_video}[/dim]")
        else:
            console.print("[yellow]No video selected. Exiting.[/yellow]")
    
    elif process_all:
        video_dirs = [d for d in DATA_SLIDES.iterdir() if d.is_dir()]
        
        if not video_dirs:
            console.print("[yellow]No slide directories found[/yellow]")
            return
        
        console.print(f"[bold]Processing {len(video_dirs)} videos...[/bold]\n")
        
        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing...", total=len(video_dirs))
            
            for video_dir in video_dirs:
                video_id = video_dir.name
                progress.update(task, description=f"Processing {video_id}...")
                result = process_video(video_id, dry_run, threshold)
                if 'error' not in result:
                    results.append(result)
                progress.advance(task)
        
        # Summary
        total_removed = sum(r.get('removed', 0) for r in results)
        total_pairs = sum(r.get('pairs_found', 0) for r in results)
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Videos processed: {len(results)}")
        console.print(f"  Transition pairs found: {total_pairs}")
        console.print(f"  Slides removed: {total_removed}")
        
        if not dry_run and total_removed > 0:
            console.print(f"\n[green]✓ Cleanup complete![/green]")
            console.print(f"[dim]Run: python scripts/sync_slide_metadata.py --all[/dim]")
        elif total_removed > 0:
            console.print(f"\n[yellow]Would remove {total_removed} slides (dry run)[/yellow]")
        else:
            console.print(f"\n[green]No transition duplicates found![/green]")
    
    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Use --dry-run to preview changes first")


if __name__ == '__main__':
    main()

