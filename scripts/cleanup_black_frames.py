#!/usr/bin/env python3
"""
Cleanup script to remove black/empty frames at 0m00s from extracted slides.

These frames are often captured at the start of videos before content begins.
This script removes them from already-extracted slide directories.

Usage:
    python scripts/cleanup_black_frames.py --video VIDEO_ID
    python scripts/cleanup_black_frames.py --all
"""

import json
import sys
from pathlib import Path

import click
import cv2
import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import DATA_SLIDES

console = Console()


def is_mostly_black(image_path: Path, threshold: float = 0.85) -> bool:
    """Check if image is mostly black/empty."""
    try:
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return True
        
        # Calculate percentage of pixels that are very dark (0-30 out of 255)
        dark_pixels = np.sum(img < 30)
        total_pixels = img.size
        dark_ratio = dark_pixels / total_pixels
        
        return dark_ratio > threshold
    except Exception:
        return False


def is_0m00s_slide(filename: str) -> bool:
    """Check if slide is at 0m00s timestamp."""
    return filename.startswith('slide_0m00s_')


def cleanup_video(video_id: str, dry_run: bool = False) -> dict:
    """Remove black frames at 0m00s from a video's slides."""
    slide_dir = DATA_SLIDES / video_id
    if not slide_dir.exists():
        console.print(f"[yellow]No slides directory found for {video_id}[/yellow]")
        return {'error': 'No slides directory'}
    
    metadata_file = slide_dir / "metadata.json"
    if not metadata_file.exists():
        console.print(f"[yellow]No metadata found for {video_id}[/yellow]")
        return {'error': 'No metadata'}
    
    # Find 0m00s slides
    slide_files = list(slide_dir.glob("slide_0m00s_*.png"))
    if not slide_files:
        console.print(f"[green]✓ No 0m00s slides found for {video_id}[/green]")
        return {'removed': 0, 'checked': 0}
    
    removed = []
    kept = []
    
    for slide_file in slide_files:
        if is_mostly_black(slide_file):
            removed.append(slide_file)
        else:
            kept.append(slide_file)
    
    if not removed:
        console.print(f"[green]✓ No black frames found at 0m00s for {video_id}[/green]")
        return {'removed': 0, 'checked': len(slide_files)}
    
    if dry_run:
        console.print(f"\n[bold]Dry run: Would remove {len(removed)} black frames from {video_id}[/bold]")
        for f in removed:
            console.print(f"  [dim]{f.name}[/dim]")
        return {'dry_run': True, 'would_remove': len(removed), 'checked': len(slide_files)}
    
    # Remove files
    for slide_file in removed:
        slide_file.unlink()
    
    # Update metadata
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    # Remove from slides list
    original_count = len(metadata.get('slides', []))
    metadata['slides'] = [
        slide for slide in metadata.get('slides', [])
        if slide['filename'] not in [f.name for f in removed]
    ]
    
    # Update stats
    metadata['stats']['slides_detected'] = len(metadata['slides'])
    metadata['stats']['unique_slides'] = len(metadata['slides'])
    
    # Save updated metadata
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    console.print(f"[green]✓ Removed {len(removed)} black frames from {video_id}[/green]")
    console.print(f"[dim]  Updated metadata: {original_count} → {len(metadata['slides'])} slides[/dim]")
    
    return {
        'video_id': video_id,
        'removed': len(removed),
        'checked': len(slide_files),
        'kept': len(kept)
    }


@click.command()
@click.option('--video', '-v', help='Single video ID to cleanup')
@click.option('--all', '-a', 'cleanup_all', is_flag=True, help='Cleanup all videos')
@click.option('--dry-run', '-d', is_flag=True, help='Preview without making changes')
def main(video: str, cleanup_all: bool, dry_run: bool):
    """Remove black frames at 0m00s from extracted slides."""
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be deleted[/yellow]\n")
    
    if video:
        result = cleanup_video(video, dry_run)
        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
    
    elif cleanup_all:
        video_dirs = [d for d in DATA_SLIDES.iterdir() if d.is_dir()]
        
        if not video_dirs:
            console.print("[yellow]No slide directories found[/yellow]")
            return
        
        console.print(f"[bold]Cleaning up {len(video_dirs)} videos...[/bold]\n")
        
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
                result = cleanup_video(video_id, dry_run)
                if 'error' not in result:
                    results.append(result)
                progress.advance(task)
        
        # Summary
        total_removed = sum(r.get('removed', 0) for r in results)
        total_checked = sum(r.get('checked', 0) for r in results)
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Videos processed: {len(results)}")
        console.print(f"  0m00s slides checked: {total_checked}")
        console.print(f"  Black frames removed: {total_removed}")
        
        if not dry_run and total_removed > 0:
            console.print(f"\n[green]✓ Cleanup complete![/green]")
        elif total_removed > 0:
            console.print(f"\n[yellow]Would remove {total_removed} black frames (dry run)[/yellow]")
        else:
            console.print(f"\n[green]No black frames found![/green]")
    
    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Use --dry-run to preview changes first")


if __name__ == '__main__':
    main()

