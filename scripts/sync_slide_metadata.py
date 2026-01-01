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
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

PROJECT_ROOT = Path(__file__).parent.parent
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"

console = Console()

# Import progress tracking
sys.path.insert(0, str(Path(__file__).parent))
from curation_progress import mark_metadata_synced, get_video_progress, detect_video_state, select_video_interactive, get_next_video, show_curation_dashboard


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
        if not dry_run:
            mark_metadata_synced(video_id)
        return {
            'video_id': video_id,
            'synced': True,
            'removed': 0,
            'added': 0,
            'current_count': len(actual_files)
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
        
        # Update progress tracking
        mark_metadata_synced(video_id)
        
        console.print(f"[green]✓ Updated metadata: {len(missing_files)} entries removed[/green]")
        console.print(f"[green]  Final count: {len(actual_files)} slides[/green]")
    
    return {
        'video_id': video_id,
        'synced': not dry_run,
        'removed': len(missing_files),
        'added': 0,
        'orphaned': len(orphaned_files),
        'current_count': len(actual_files)
    }


@click.command()
@click.option('--video', '-v', help='Single video ID to sync (omit for interactive selection)')
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
        
        # Show next steps for single video (unless dry-run)
        if not dry_run:
            _show_next_steps_after_sync(video, result)
    
    elif not sync_all:
        # Interactive video selection
        console.print("\n[bold]Interactive Video Selection[/bold]")
        selected_video = select_video_interactive("Select a video to sync metadata")
        if selected_video:
            result = sync_video_metadata(selected_video, dry_run)
            if 'error' in result:
                console.print(f"[red]Error: {result['error']}[/red]")
                return
            
            if not dry_run:
                _show_next_steps_after_sync(selected_video, result)
        else:
            console.print("[yellow]No video selected. Exiting.[/yellow]")
    
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


def _show_video_status(video_id: str):
    """Show detailed status for a specific video."""
    video_progress = get_video_progress(video_id)
    detected_state = detect_video_state(video_id)
    
    slide_dir = DATA_SLIDES / video_id
    slide_files = list(slide_dir.glob("slide_*.png")) if slide_dir.exists() else []
    
    console.print("\n")
    console.print(Panel(
        f"[bold]Video Status: {video_id}[/bold]\n\n"
        f"Slides on disk: {len(slide_files)}\n"
        f"Status: {video_progress.get('status', 'pending').upper()}\n\n"
        f"Progress Tracking:\n"
        f"  Reviewed: {'✓' if video_progress.get('reviewed') else '✗'}\n"
        f"  Credits added: {'✓' if video_progress.get('credits_added') else '✗'}\n"
        f"  Duplicates fixed: {'✓' if video_progress.get('duplicates_fixed') else '✗'}\n"
        f"  Metadata synced: {'✓' if video_progress.get('metadata_synced') else '✗'}\n\n"
        f"Detected State:\n"
        f"  Has credits: {'✓' if (detected_state.get('has_credits_in_metadata') or detected_state.get('has_credits_in_images')) else '✗'}\n"
        f"  Has been reviewed: {'✓' if detected_state.get('has_been_reviewed') else '✗'}\n"
        f"  Metadata synced: {'✓' if detected_state.get('metadata_synced') else '✗'}",
        title="Video Status",
        border_style="cyan"
    ))
    
    # Check if complete
    is_complete = (
        video_progress.get('reviewed') and
        video_progress.get('credits_added') and
        video_progress.get('metadata_synced')
    )
    
    if is_complete:
        console.print("\n[bold green]✓ This video is COMPLETE![/bold green]")
        console.print("[dim]All curation steps have been completed.[/dim]")
    else:
        missing = []
        if not video_progress.get('reviewed'):
            missing.append("Review slides")
        if not video_progress.get('credits_added'):
            missing.append("Add credits")
        if not video_progress.get('metadata_synced'):
            missing.append("Sync metadata")
        
        if missing:
            console.print(f"\n[yellow]Remaining steps: {', '.join(missing)}[/yellow]")


def _show_workflow_help(video_id: str = None):
    """Show workflow help and useful commands."""
    help_text = f"""
[bold]Complete Slide Curation Workflow[/bold]

[cyan]Stage 1: Extract Slides[/cyan]
  python scripts/extract_slides.py --all
  • Downloads videos and extracts slides
  • Automatic filtering (blurry, low-text, filler)
  • ~45-90 min for full playlist

[cyan]Stage 2: Human Review (Recommended)[/cyan]
  python scripts/review_slides.py --video VIDEO_ID --review-all
  • Review all slides interactively
  • Decide: Keep or Remove
  • Auto-syncs metadata

[cyan]Stage 3: Add Credits[/cyan]
  python scripts/add_credit_overlay.py --video VIDEO_ID
  • Add attribution to slides
  • Interactive credit text prompt

[cyan]Stage 4: Fix Duplicates (If Needed)[/cyan]
  python scripts/fix_duplicate_credits.py --video VIDEO_ID
  • Remove duplicate credit bars

[cyan]Stage 5: Sync Metadata[/cyan]
  python scripts/sync_slide_metadata.py --video VIDEO_ID
  • Sync metadata after manual deletions

[cyan]Stage 6: Finalize (All Videos)[/cyan]
  python scripts/finalize_curation.py
  • ⚠️  Processes ALL videos
  • Syncs metadata, refreshes exports, rebuilds index

[bold]Useful Commands[/bold]

[dim]Check extraction status:[/dim]
  python scripts/extract_slides.py --status

[dim]Review specific video:[/dim]
  python scripts/review_slides.py --video VIDEO_ID --review-all

[dim]Sync single video metadata:[/dim]
  python scripts/sync_slide_metadata.py --video VIDEO_ID

[dim]Sync all videos metadata:[/dim]
  python scripts/sync_slide_metadata.py --all

[dim]Cleanup black frames:[/dim]
  python scripts/cleanup_black_frames.py --video VIDEO_ID

[dim]View workflow documentation:[/dim]
  See: SLIDE_CURATION_WORKFLOW.md or README.md
"""
    
    console.print(Panel(help_text, title="Workflow Help", border_style="blue"))
    if video_id:
        console.print(f"\n[dim]Current video: {video_id}[/dim]")


def _show_next_steps_after_sync(video_id: str, result: dict):
    """Show interactive next steps after syncing metadata."""
    console.print("\n")
    console.print(Panel(
        f"[bold green]✓ Metadata synced![/bold green]\n\n"
        f"Removed: {result.get('removed', 0)} orphaned entries\n"
        f"Current slides: {result.get('current_count', 0)}",
        title="Sync Complete",
        border_style="green"
    ))
    
    while True:
        console.print("\n[bold]What would you like to do next?[/bold]")
        console.print("\n[cyan]A)[/cyan] Continue to next step: Finalize curation (processes ALL videos)")
        console.print("    [dim]Command: python scripts/finalize_curation.py[/dim]")
        console.print("    [dim]Note: This will sync all videos and refresh exports[/dim]")
        console.print("\n[cyan]B)[/cyan] Review slides (if you haven't already)")
        console.print("    [dim]Command: python scripts/review_slides.py --video {video_id} --review-all[/dim]")
        console.print("\n[cyan]C)[/cyan] Add credit overlay (if not done yet)")
        console.print("    [dim]Command: python scripts/add_credit_overlay.py --video {video_id}[/dim]")
        console.print("\n[cyan]D)[/cyan] Sync another video")
        console.print("    [dim]Command: python scripts/sync_slide_metadata.py --video VIDEO_ID[/dim]")
        console.print("\n[cyan]N)[/cyan] Move to next video (start review)")
        console.print("    [dim]Automatically starts review for the next video in the list[/dim]")
        console.print("\n[cyan]S)[/cyan] Show status for this video")
        console.print("\n[cyan]H)[/cyan] Show workflow help and useful commands")
        console.print("\n[cyan]E)[/cyan] Exit (you're done with this video)")
        
        choice = Prompt.ask(
            "\n[bold]Choose an option[/bold]",
            choices=["a", "A", "b", "B", "c", "C", "d", "D", "e", "E", "h", "H", "n", "N", "s", "S"],
            default="A"
        ).upper()
        
        if choice == "H":
            _show_workflow_help(video_id)
            console.print()  # Add blank line
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")
            continue
        elif choice == "S":
            status_choice = Prompt.ask(
                "\n[bold]Show status for:[/bold] [cyan](T)[/cyan]his video or [cyan](A)[/cyan]ll videos?",
                choices=["t", "T", "a", "A"],
                default="T"
            ).upper()
            if status_choice == "T":
                _show_video_status(video_id)
            else:
                show_curation_dashboard()
            continue
    
        if choice == "A":
            console.print("\n[bold]Running: python scripts/finalize_curation.py[/bold]")
            console.print("[yellow]⚠️  This will process ALL videos in your repository[/yellow]\n")
            if Prompt.ask("Continue?", choices=["y", "Y", "n", "N"], default="Y").upper() == "Y":
                import subprocess
                subprocess.run([sys.executable, "scripts/finalize_curation.py"])
            break
        elif choice == "B":
            console.print(f"\n[bold]Running: python scripts/review_slides.py --video {video_id} --review-all[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/review_slides.py", "--video", video_id, "--review-all"])
            break
        elif choice == "C":
            console.print(f"\n[bold]Running: python scripts/add_credit_overlay.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/add_credit_overlay.py", "--video", video_id])
            break
        elif choice == "D":
            console.print("\n[bold]Select video to sync:[/bold]")
            new_video = select_video_interactive("Select a video to sync metadata")
            if new_video:
                console.print(f"\n[bold]Running: python scripts/sync_slide_metadata.py --video {new_video}[/bold]\n")
                import subprocess
                subprocess.run([sys.executable, "scripts/sync_slide_metadata.py", "--video", new_video])
            break
        elif choice == "N":
            next_video = get_next_video(video_id)
            if next_video:
                console.print(f"\n[bold]Moving to next video: {next_video}[/bold]")
                console.print(f"[bold]Running: python scripts/review_slides.py --video {next_video} --review-all[/bold]\n")
                import subprocess
                subprocess.run([sys.executable, "scripts/review_slides.py", "--video", next_video, "--review-all"])
            else:
                console.print("\n[yellow]No next video found. This is the last video in the list.[/yellow]")
            break
        else:
            console.print("\n[dim]Exiting. You can continue later with the commands shown above.[/dim]")
            break


if __name__ == '__main__':
    main()

