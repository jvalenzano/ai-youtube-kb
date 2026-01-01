#!/usr/bin/env python3
"""
Sync curation progress with actual video state.

Useful for videos that were processed before progress tracking was added,
or to update progress after manual changes.

Usage:
    python scripts/sync_curation_progress.py --video VIDEO_ID
    python scripts/sync_curation_progress.py --all
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

sys.path.insert(0, str(Path(__file__).parent))
from curation_progress import (
    sync_video_progress_from_state,
    get_all_videos_with_slides,
    get_status_summary
)

console = Console()


@click.command()
@click.option('--video', '-v', help='Single video ID to sync')
@click.option('--all', '-a', 'sync_all', is_flag=True, help='Sync all videos')
def main(video: str, sync_all: bool):
    """Sync curation progress with actual video state."""
    
    if video:
        console.print(f"[bold]Syncing progress for {video}...[/bold]\n")
        result = sync_video_progress_from_state(video)
        
        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            return
        
        detected = result['detected_state']
        updates = result['updates_applied']
        
        console.print(Panel(
            f"[bold]Detected State:[/bold]\n\n"
            f"Reviewed: {detected.get('has_been_reviewed', False)}\n"
            f"Credits (metadata): {detected.get('has_credits_in_metadata', False)}\n"
            f"Credits (images): {detected.get('has_credits_in_images', False)}\n"
            f"Metadata synced: {detected.get('metadata_synced', False)}\n"
            f"Slide count: {detected.get('slide_count', 0)}",
            title="Video State",
            border_style="blue"
        ))
        
        if updates:
            console.print(f"\n[green]✓ Updated progress: {', '.join(updates.keys())}[/green]")
        else:
            console.print("\n[yellow]No updates needed (progress already matches state)[/yellow]")
    
    elif sync_all:
        all_videos = get_all_videos_with_slides()
        
        if not all_videos:
            console.print("[yellow]No videos with slides found[/yellow]")
            return
        
        console.print(f"[bold]Syncing progress for {len(all_videos)} videos...[/bold]\n")
        
        synced_count = 0
        updated_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Syncing...", total=len(all_videos))
            
            for video_id in all_videos:
                progress.update(task, description=f"Syncing {video_id}...")
                result = sync_video_progress_from_state(video_id)
                
                if 'error' not in result:
                    synced_count += 1
                    if result.get('updates_applied'):
                        updated_count += 1
                
                progress.advance(task)
        
        console.print(f"\n[bold]Sync Summary:[/bold]")
        console.print(f"  Videos processed: {synced_count}")
        console.print(f"  Progress updated: {updated_count}")
        
        # Show updated status
        summary = get_status_summary()
        console.print(f"\n[bold]Current Status:[/bold]")
        console.print(f"  Completed: {len(summary['completed'])}")
        console.print(f"  Credits added: {len(summary['credits_added'])}")
        console.print(f"  Reviewed: {len(summary['reviewed'])}")
        console.print(f"  Pending: {len(summary['pending'])}")
    
    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Use --help for usage information")


if __name__ == '__main__':
    main()

