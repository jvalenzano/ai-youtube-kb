#!/usr/bin/env python3
"""
Cleanup script for existing extracted slides.

Filters out low-quality slides (duplicates, empty, filler text) from already-extracted slides.

Usage:
    python scripts/cleanup_slides.py --video VIDEO_ID    # Single video
    python scripts/cleanup_slides.py --all               # All videos
    python scripts/cleanup_slides.py --dry-run           # Preview without deleting
"""

import json
import shutil
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# Import quality filters from extract_slides
import sys
sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import SlideConfig, SlideInfo, SlideExtractor

PROJECT_ROOT = Path(__file__).parent.parent
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"

console = Console()


def load_slide_metadata(video_id: str) -> Optional[dict]:
    """Load metadata for a video's slides."""
    metadata_file = DATA_SLIDES / video_id / "metadata.json"
    if not metadata_file.exists():
        return None
    
    with open(metadata_file) as f:
        return json.load(f)


def create_slide_info(slide_data: dict, video_id: str) -> SlideInfo:
    """Create SlideInfo from metadata."""
    slide_path = DATA_SLIDES / video_id / slide_data['filename']
    
    return SlideInfo(
        path=slide_path,
        timestamp=slide_data.get('timestamp_seconds', 0),
        timestamp_formatted=slide_data.get('timestamp_formatted', ''),
        perceptual_hash=slide_data.get('perceptual_hash', ''),
        ocr_text=slide_data.get('ocr_text', ''),
        clip_score=slide_data.get('clip_score'),
        is_duplicate_of=slide_data.get('is_duplicate_of'),
        transcript_context=slide_data.get('transcript_context', {})
    )


def cleanup_video(video_id: str, config: SlideConfig, dry_run: bool = False) -> dict:
    """Cleanup slides for a single video."""
    metadata = load_slide_metadata(video_id)
    if not metadata:
        return {'video_id': video_id, 'removed': 0, 'kept': 0, 'error': 'No metadata found'}

    # Convert metadata to SlideInfo objects
    slides = []
    for slide_data in metadata.get('slides', []):
        slide_info = create_slide_info(slide_data, video_id)
        if slide_info.path.exists():
            slides.append(slide_info)

    if not slides:
        return {'video_id': video_id, 'removed': 0, 'kept': 0, 'error': 'No slides found'}

    # Create extractor to use its filter methods
    extractor = SlideExtractor(video_id, config)
    
    # Apply quality filters
    initial_count = len(slides)
    
    # Filter quality
    slides = extractor.filter_quality(slides)
    quality_removed = initial_count - len(slides)
    
    # Deduplicate
    slides = extractor.deduplicate(slides)
    final_count = len(slides)
    total_removed = initial_count - final_count

    # Remove files
    removed_files = []
    kept_files = []
    
    # Get all slide files
    slide_dir = DATA_SLIDES / video_id
    all_slide_files = {f.name for f in slide_dir.glob('slide_*.png')}
    kept_slide_files = {s.path.name for s in slides}
    
    for filename in all_slide_files:
        if filename not in kept_slide_files:
            file_path = slide_dir / filename
            if not dry_run:
                file_path.unlink()
            removed_files.append(filename)
        else:
            kept_files.append(filename)

    # Update metadata
    if not dry_run and total_removed > 0:
        metadata['slides'] = [
            {
                'filename': s.path.name,
                'timestamp_seconds': int(s.timestamp),
                'timestamp_formatted': s.timestamp_formatted,
                'timestamp_url': metadata.get('url', '') + f"&t={int(s.timestamp)}s",
                'perceptual_hash': s.perceptual_hash,
                'is_duplicate_of': s.is_duplicate_of,
                'ocr_text': s.ocr_text,
                'clip_score': s.clip_score,
                'transcript_context': s.transcript_context,
            }
            for s in slides
        ]
        
        # Update stats
        metadata['stats']['slides_detected'] = final_count
        metadata['stats']['unique_slides'] = final_count
        metadata['stats']['duplicates'] = 0
        metadata['cleanup_applied'] = True
        
        # Save updated metadata
        metadata_file = slide_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    return {
        'video_id': video_id,
        'initial': initial_count,
        'removed': total_removed,
        'kept': final_count,
        'removed_files': removed_files,
        'dry_run': dry_run,
    }


@click.command()
@click.option('--video', '-v', help='Single video ID to cleanup')
@click.option('--all', '-a', 'cleanup_all', is_flag=True, help='Cleanup all videos')
@click.option('--dry-run', '-d', is_flag=True, help='Preview changes without deleting')
@click.option('--min-words', default=10, type=int, help='Minimum words in OCR text')
@click.option('--remove-duplicates/--keep-duplicates', default=True, help='Remove duplicate slides')
@click.option('--filter-filler/--keep-filler', default=True, help='Filter filler text slides')
@click.option('--filter-blurry/--keep-blurry', default=True, help='Filter blurry images')
@click.option('--blur-threshold', default=100.0, type=float, help='Blur detection threshold (lower = stricter)')
def main(video: Optional[str], cleanup_all: bool, dry_run: bool,
         min_words: int, remove_duplicates: bool, filter_filler: bool,
         filter_blurry: bool, blur_threshold: float):
    """Cleanup low-quality slides from extracted slide sets."""
    
    config = SlideConfig(
        min_ocr_words=min_words,
        remove_duplicates=remove_duplicates,
        filter_filler_text=filter_filler,
        filter_blurry=filter_blurry,
        blur_threshold=blur_threshold,
    )

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be deleted[/yellow]\n")

    if video:
        # Single video
        result = cleanup_video(video, config, dry_run)
        
        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            return
        
        console.print(f"\n[bold]Cleanup Results for {video}:[/bold]")
        console.print(f"  Initial slides: {result['initial']}")
        console.print(f"  Removed: {result['removed']}")
        console.print(f"  Kept: {result['kept']}")
        
        if result['removed'] > 0 and not dry_run:
            console.print(f"[green]✓ Cleanup complete![/green]")
        elif result['removed'] > 0:
            console.print(f"[yellow]Would remove {result['removed']} slides[/yellow]")

    elif cleanup_all:
        # All videos
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
            task = progress.add_task("Cleaning up...", total=len(video_dirs))

            for video_dir in video_dirs:
                video_id = video_dir.name
                progress.update(task, description=f"Processing {video_id}...")
                
                result = cleanup_video(video_id, config, dry_run)
                results.append(result)
                
                progress.advance(task)

        # Summary
        total_initial = sum(r['initial'] for r in results if 'initial' in r)
        total_removed = sum(r['removed'] for r in results if 'removed' in r)
        total_kept = sum(r['kept'] for r in results if 'kept' in r)

        console.print(f"\n[bold]Cleanup Summary:[/bold]")
        console.print(f"  Videos processed: {len(results)}")
        console.print(f"  Total initial slides: {total_initial}")
        console.print(f"  Total removed: {total_removed}")
        console.print(f"  Total kept: {total_kept}")

        if total_removed > 0 and not dry_run:
            console.print(f"\n[green]✓ Cleanup complete![/green]")
        elif total_removed > 0:
            console.print(f"\n[yellow]Would remove {total_removed} slides (dry run)[/yellow]")

        # Show top videos by removal count
        if total_removed > 0:
            top_removed = sorted(
                [r for r in results if 'removed' in r and r['removed'] > 0],
                key=lambda x: x['removed'],
                reverse=True
            )[:5]

            if top_removed:
                console.print("\n[bold]Top videos by slides removed:[/bold]")
                table = Table(show_header=True)
                table.add_column("Video ID", style="cyan")
                table.add_column("Removed", style="red")
                table.add_column("Kept", style="green")

                for r in top_removed:
                    table.add_row(
                        r['video_id'],
                        str(r['removed']),
                        str(r['kept'])
                    )
                console.print(table)

    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Use --dry-run to preview changes first")


if __name__ == '__main__':
    main()

