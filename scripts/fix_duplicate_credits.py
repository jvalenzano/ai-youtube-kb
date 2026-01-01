#!/usr/bin/env python3
"""
Fix duplicate credit overlays on slide images.

If the credit overlay script was run twice, this removes the duplicate
credit bars from the bottom of images.

Usage:
    python scripts/fix_duplicate_credits.py --video VIDEO_ID
"""

import sys
from pathlib import Path
from typing import Optional

import click
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import DATA_SLIDES
from curation_progress import mark_duplicates_fixed, get_video_progress, detect_video_state, select_video_interactive, get_next_video, show_curation_dashboard

console = Console()


def detect_credit_bar_height(img: Image.Image, threshold: int = 100) -> int:
    """
    Detect if there's a credit bar at the bottom of the image.
    Returns the height of the credit bar, or 0 if not found.
    """
    width, height = img.size
    
    # Check bottom 100px for dark bar (typical credit bar is 30-60px)
    check_height = min(100, height // 4)
    bottom_region = img.crop((0, height - check_height, width, height))
    
    # Convert to grayscale for analysis
    gray = bottom_region.convert('L')
    pixels = list(gray.getdata())
    
    # Check rows from bottom up
    bar_height = 0
    for y_offset in range(check_height - 1, -1, -1):
        row_start = y_offset * width
        row = pixels[row_start:row_start + width]
        avg_brightness = sum(row) / len(row)
        
        # Dark bar has low brightness (typically < 50 for black bar with alpha)
        if avg_brightness < threshold:
            bar_height = check_height - y_offset
        else:
            # If we found a bar and then hit bright pixels, we've found the top of the bar
            if bar_height > 0:
                break
    
    return bar_height


def remove_duplicate_credits(image_path: Path) -> bool:
    """
    Remove duplicate credit bars from an image.
    Returns True if a duplicate was removed, False otherwise.
    """
    img = Image.open(image_path)
    width, height = img.size
    original_height = height
    
    # Check bottom 150px for credit bars
    check_region_height = min(150, height // 3)
    bottom_region = img.crop((0, height - check_region_height, width, height))
    gray = bottom_region.convert('L')
    pixels = list(gray.getdata())
    
    # Find all dark bars (credit bars) from bottom up
    dark_rows = []
    for y_offset in range(check_region_height - 1, -1, -1):
        row_start = y_offset * width
        row = pixels[row_start:row_start + width]
        avg_brightness = sum(row) / len(row)
        
        # Dark bar has low brightness (< 80 for semi-transparent black)
        if avg_brightness < 80:
            dark_rows.append(y_offset)
    
    if not dark_rows:
        return False  # No credit bars detected
    
    # Find contiguous dark regions (credit bars)
    # Group consecutive rows
    dark_regions = []
    current_region = [dark_rows[0]]
    for i in range(1, len(dark_rows)):
        if dark_rows[i] == dark_rows[i-1] - 1:  # Consecutive
            current_region.append(dark_rows[i])
        else:
            dark_regions.append(current_region)
            current_region = [dark_rows[i]]
    if current_region:
        dark_regions.append(current_region)
    
    # Each region should be a credit bar (typically 30-60px)
    # If we have 2 regions, or one region > 80px, it's likely a duplicate
    total_dark_height = len(dark_rows)
    
    if len(dark_regions) >= 2:
        # Multiple credit bars detected - remove the bottommost one
        # Find where the first (topmost) credit bar ends
        first_bar_bottom = min(dark_regions[0])  # Top of first bar (in check region coords)
        # Convert to absolute coordinates
        first_bar_bottom_absolute = height - check_region_height + first_bar_bottom
        
        # Keep one standard credit bar (60px from the end of first bar)
        # Actually, let's keep everything up to where the first credit bar starts
        # and add back one standard credit bar
        first_bar_top = max(dark_regions[0])  # Bottom of first bar (in check region coords)
        first_bar_top_absolute = height - check_region_height + first_bar_top
        
        # Crop to remove duplicate: keep image up to first credit bar, then add one bar
        # Standard credit bar is ~60px
        new_height = first_bar_top_absolute + 60
        if new_height < height:
            img_cropped = img.crop((0, 0, width, new_height))
            img_cropped.save(image_path, 'PNG')
            return True
    
    elif total_dark_height > 80:
        # Single very tall dark region - likely two bars merged
        # Remove excess to keep one standard credit bar (~60px)
        new_height = height - (total_dark_height - 60)
        
        # Sanity check: new height should be reasonable (at least 80% of original)
        if new_height < height and new_height > height * 0.8:
            img_cropped = img.crop((0, 0, width, new_height))
            img_cropped.save(image_path, 'PNG')
            return True
    
    return False


def process_video(video_id: str, dry_run: bool = False) -> dict:
    """Fix duplicate credits for all slides in a video."""
    slide_dir = DATA_SLIDES / video_id
    if not slide_dir.exists():
        console.print(f"[red]No slides directory found for {video_id}[/red]")
        return {'error': 'No slides directory'}
    
    slide_files = list(slide_dir.glob("slide_*.png"))
    if not slide_files:
        console.print(f"[yellow]No slide images found for {video_id}[/yellow]")
        return {'error': 'No slides found'}
    
    if dry_run:
        console.print(f"\n[bold]Dry run: Would check {len(slide_files)} slides for duplicate credits[/bold]")
        return {'dry_run': True, 'count': len(slide_files)}
    
    fixed = 0
    errors = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"Checking {video_id}...", total=len(slide_files))
        
        for slide_file in slide_files:
            try:
                if remove_duplicate_credits(slide_file):
                    fixed += 1
            except Exception as e:
                errors.append({'file': slide_file.name, 'error': str(e)})
            
            progress.advance(task)
    
    console.print(f"\n[green]✓ Fixed {fixed} slides with duplicate credits[/green]")
    if errors:
        console.print(f"[yellow]⚠ {len(errors)} errors[/yellow]")
        for err in errors[:5]:
            console.print(f"  [dim]{err['file']}: {err['error']}[/dim]")
    
    # Update progress tracking
    if not dry_run:
        mark_duplicates_fixed(video_id, fixed)
    
    return {
        'video_id': video_id,
        'fixed': fixed,
        'errors': len(errors),
    }


def _show_video_status(video_id: str):
    """Show detailed status for a specific video."""
    from pathlib import Path
    from extract_slides import DATA_SLIDES
    
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


def _show_next_steps_after_fix_duplicates(video_id: str, result: dict):
    """Show interactive next steps after fixing duplicate credits."""
    console.print("\n")
    console.print(Panel(
        f"[bold green]✓ Duplicate credits fixed![/bold green]\n\n"
        f"Fixed: {result.get('fixed', 0)} slides",
        title="Fix Complete",
        border_style="green"
    ))
    
    while True:
        console.print("\n[bold]What would you like to do next?[/bold]")
        console.print("\n[cyan]A)[/cyan] Continue to next step: Sync metadata")
        console.print("    [dim]Command: python scripts/sync_slide_metadata.py --video {video_id}[/dim]")
        console.print("\n[cyan]B)[/cyan] Review slides (if you haven't already)")
        console.print("    [dim]Command: python scripts/review_slides.py --video {video_id} --review-all[/dim]")
        console.print("\n[cyan]C)[/cyan] Add credit overlay (if not done yet)")
        console.print("    [dim]Command: python scripts/add_credit_overlay.py --video {video_id}[/dim]")
        console.print("\n[cyan]D)[/cyan] Fix duplicates for another video")
        console.print("    [dim]Command: python scripts/fix_duplicate_credits.py --video VIDEO_ID[/dim]")
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
            console.print(f"\n[bold]Running: python scripts/sync_slide_metadata.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/sync_slide_metadata.py", "--video", video_id])
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
            console.print("\n[bold]Select video to fix duplicates:[/bold]")
            new_video = select_video_interactive("Select a video to fix duplicate credits")
            if new_video:
                console.print(f"\n[bold]Running: python scripts/fix_duplicate_credits.py --video {new_video}[/bold]\n")
                import subprocess
                subprocess.run([sys.executable, "scripts/fix_duplicate_credits.py", "--video", new_video])
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


@click.command()
@click.option('--video', '-v', help='Video ID to fix (omit for interactive selection)')
@click.option('--dry-run', '-d', is_flag=True, help='Preview without making changes')
def main(video: Optional[str], dry_run: bool):
    """Fix duplicate credit overlays on slides."""
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be modified[/yellow]\n")
    
    # Interactive video selection if no video provided
    if not video:
        console.print("\n[bold]Interactive Video Selection[/bold]")
        selected_video = select_video_interactive("Select a video to fix duplicate credits")
        if not selected_video:
            console.print("[yellow]No video selected. Exiting.[/yellow]")
            return
        video = selected_video
    
    result = process_video(video, dry_run=dry_run)
    
    if 'error' in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    
    # Show next steps if successful and not dry-run
    if not dry_run and 'fixed' in result:
        _show_next_steps_after_fix_duplicates(video, result)


if __name__ == '__main__':
    main()

