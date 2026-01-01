#!/usr/bin/env python3
"""
Sync slide metadata with actual files on disk.

Useful when slides are manually deleted or moved. Updates metadata.json
to match what's actually in the directory.

Usage:
    python scripts/sync_slide_metadata.py --video VIDEO_ID
    python scripts/sync_slide_metadata.py --all
"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).parent.parent
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"

console = Console()


def sync_video_metadata(video_id: str, dry_run: bool = False) -> dict:
    """Sync metadata for a single video."""
    slide_dir = DATA_SLIDES / video_id
    metadata_file = slide_dir / "metadata.json"
    
    if not metadata_file.exists():
        console.print(f"[yellow]No metadata found for {video_id}[/yellow]")
        return {'error': 'No metadata found'}
    
    # Load current metadata
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    # Get actual slide files on disk
    actual_files = {f.name for f in slide_dir.glob('slide_*.png')}
    
    # Get files listed in metadata
    metadata_files = {slide['filename'] for slide in metadata.get('slides', [])}
    
    # Find discrepancies
    missing_files = metadata_files - actual_files  # In metadata but not on disk
    orphaned_files = actual_files - metadata_files  # On disk but not in metadata
    
    if not missing_files and not orphaned_files:
        console.print(f"[green]✓ Metadata is in sync for {video_id}[/green]")
        return {
            'video_id': video_id,
            'synced': True,
            'removed': 0,
            'added': 0
        }
    
    # Show what will change
    console.print(f"\n[bold]Syncing metadata for {video_id}[/bold]")
    
    if missing_files:
        console.print(f"[yellow]Files in metadata but missing from disk: {len(missing_files)}[/yellow]")
        if not dry_run:
            # Remove from metadata
            metadata['slides'] = [
                slide for slide in metadata.get('slides', [])
                if slide['filename'] in actual_files
            ]
    
    if orphaned_files:
        console.print(f"[yellow]Files on disk but missing from metadata: {len(orphaned_files)}[/yellow]")
        console.print("[dim]Note: Orphaned files won't be added automatically (run extract_slides to regenerate metadata)[/dim]")
    
    # Update stats
    if not dry_run:
        metadata['stats']['slides_detected'] = len(actual_files)
        metadata['stats']['unique_slides'] = len(actual_files)
        metadata['stats']['duplicates'] = 0
        metadata['metadata_synced'] = True
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        console.print(f"[green]✓ Updated metadata: {len(missing_files)} entries removed[/green]")
        console.print(f"[green]  Final count: {len(actual_files)} slides[/green]")
    
    return {
        'video_id': video_id,
        'synced': not dry_run,
        'removed': len(missing_files),
        'added': 0,
        'orphaned': len(orphaned_files)
    }


@click.command()
@click.option('--video', '-v', help='Single video ID to sync')
@click.option('--all', '-a', 'sync_all', is_flag=True, help='Sync all videos')
@click.option('--dry-run', '-d', is_flag=True, help='Preview changes without updating')
def main(video: Optional[str], sync_all: bool, dry_run: bool):
    """Sync slide metadata with actual files on disk."""
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]\n")
    
    if video:
        result = sync_video_metadata(video, dry_run)
        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            return
    
    elif sync_all:
        video_dirs = [d for d in DATA_SLIDES.iterdir() if d.is_dir()]
        
        if not video_dirs:
            console.print("[yellow]No slide directories found[/yellow]")
            return
        
        console.print(f"[bold]Syncing {len(video_dirs)} videos...[/bold]\n")
        
        results = []
        for video_dir in video_dirs:
            video_id = video_dir.name
            result = sync_video_metadata(video_id, dry_run)
            if 'error' not in result:
                results.append(result)
        
        # Summary
        total_removed = sum(r['removed'] for r in results)
        total_orphaned = sum(r.get('orphaned', 0) for r in results)
        synced_count = sum(1 for r in results if r.get('synced'))
        
        console.print(f"\n[bold]Sync Summary:[/bold]")
        console.print(f"  Videos processed: {len(results)}")
        console.print(f"  Metadata entries removed: {total_removed}")
        console.print(f"  Orphaned files found: {total_orphaned}")
        
        if not dry_run and total_removed > 0:
            console.print(f"\n[green]✓ Synced {synced_count} videos[/green]")
        elif total_removed > 0:
            console.print(f"\n[yellow]Would remove {total_removed} metadata entries (dry run)[/yellow]")
        else:
            console.print(f"\n[green]All metadata is in sync![/green]")
    
    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Use --dry-run to preview changes first")


if __name__ == '__main__':
    main()

