#!/usr/bin/env python3
"""
Add credit overlay to existing slide images.

This script adds attribution overlays to slides that were extracted without credits.
Use this to retroactively add credits to existing slides.

Usage:
    python scripts/add_credit_overlay.py --video VIDEO_ID
    python scripts/add_credit_overlay.py --all
    python scripts/add_credit_overlay.py --video VIDEO_ID --credit-text "Custom Text"
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Import from extract_slides for consistency
sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import DATA_SLIDES, KB_DIR
from curation_progress import mark_credits_added

PROJECT_ROOT = Path(__file__).parent.parent
console = Console()


def add_credit_overlay_to_image(
    image_path: Path,
    credit_text: str,
    bar_height: Optional[int] = None
) -> Image.Image:
    """
    Add credit overlay to a single image.
    
    Args:
        image_path: Path to the image file
        credit_text: Text to display in the credit overlay
        bar_height: Height of the credit bar (auto-calculated if None)
    
    Returns:
        PIL Image with credit overlay added
    """
    # Load image
    img = Image.open(image_path)
    width, height = img.size
    
    # Calculate overlay bar height (5% of image height, min 30px, max 60px)
    if bar_height is None:
        bar_height = max(30, min(60, int(height * 0.05)))
    
    # Create overlay image
    overlay = Image.new('RGBA', (width, bar_height), (0, 0, 0, 200))  # Semi-transparent black
    draw = ImageDraw.Draw(overlay)
    
    # Try to use a nice font, fallback to default
    try:
        # Try system fonts (macOS)
        font_size = max(12, min(16, int(bar_height * 0.4)))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), credit_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (bar_height - text_height) // 2
    
    # Draw text (white)
    draw.text((x, y), credit_text, fill=(255, 255, 255, 255), font=font)
    
    # Composite overlay onto image
    result = Image.new('RGB', (width, height + bar_height), (255, 255, 255))
    result.paste(img, (0, 0))
    result.paste(overlay, (0, height), overlay)
    
    return result


def get_video_metadata(video_id: str) -> dict:
    """Load video metadata from kb/metadata.json."""
    metadata_file = KB_DIR / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            data = json.load(f)
            for video in data.get('videos', []):
                if video.get('video_id') == video_id:
                    return video
    return {'video_id': video_id, 'title': '', 'url': f'https://www.youtube.com/watch?v={video_id}'}


def generate_credit_text(
    video_id: str,
    credit_text: Optional[str] = None,
    credit_author: str = "Scott Hebner",
    credit_series: str = "The Next Frontiers of AI"
) -> str:
    """Generate credit text for a video."""
    if credit_text:
        return credit_text
    
    # Auto-generate credit text
    parts = []
    if credit_author:
        parts.append(credit_author)
    if credit_series:
        parts.append(credit_series)
    if not parts:
        # Fallback to video metadata
        video_meta = get_video_metadata(video_id)
        if video_meta.get('title'):
            parts.append("Source: YouTube")
        else:
            parts.append("Source: YouTube Video")
    
    return " • ".join(parts)


def process_video(
    video_id: str,
    credit_text: Optional[str] = None,
    credit_author: str = "Scott Hebner",
    credit_series: str = "The Next Frontiers of AI",
    dry_run: bool = False
) -> dict:
    """Add credit overlay to all slides for a video."""
    slide_dir = DATA_SLIDES / video_id
    if not slide_dir.exists():
        console.print(f"[red]No slides directory found for {video_id}[/red]")
        return {'error': 'No slides directory'}
    
    # Find all PNG files
    slide_files = list(slide_dir.glob("slide_*.png"))
    if not slide_files:
        console.print(f"[yellow]No slide images found for {video_id}[/yellow]")
        return {'error': 'No slides found'}
    
    # Generate credit text
    final_credit_text = generate_credit_text(video_id, credit_text, credit_author, credit_series)
    
    if dry_run:
        console.print(f"\n[bold]Dry run: Would add credit to {len(slide_files)} slides[/bold]")
        console.print(f"Credit text: {final_credit_text}")
        return {'dry_run': True, 'count': len(slide_files), 'credit_text': final_credit_text}
    
    # Process slides
    processed = 0
    errors = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"Processing {video_id}...", total=len(slide_files))
        
        for slide_file in slide_files:
            try:
                # Add credit overlay
                img_with_credit = add_credit_overlay_to_image(slide_file, final_credit_text)
                
                # Save back to same file (overwrite)
                img_with_credit.save(slide_file, 'PNG')
                processed += 1
            except Exception as e:
                errors.append({'file': slide_file.name, 'error': str(e)})
            
            progress.advance(task)
    
    # Update metadata to indicate credits were added
    metadata_file = slide_dir / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            metadata['credit_overlay'] = {
                'added': True,
                'credit_text': final_credit_text,
                'credit_author': credit_author,
                'credit_series': credit_series,
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Could not update metadata: {e}[/yellow]")
    
    console.print(f"\n[green]✓ Processed {processed} slides[/green]")
    if errors:
        console.print(f"[yellow]⚠ {len(errors)} errors[/yellow]")
        for err in errors[:5]:  # Show first 5 errors
            console.print(f"  [dim]{err['file']}: {err['error']}[/dim]")
    
    # Update progress tracking
    if not dry_run:
        mark_credits_added(video_id, credit_text=final_credit_text)
    
    return {
        'video_id': video_id,
        'processed': processed,
        'errors': len(errors),
        'credit_text': final_credit_text,
    }


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


def _show_next_steps_after_credits(video_id: str, result: dict):
    """Show interactive next steps after adding credit overlay."""
    console.print("\n")
    console.print(Panel(
        f"[bold green]✓ Credit overlay added![/bold green]\n\n"
        f"Processed: {result.get('processed', 0)} slides\n"
        f"Credit text: {result.get('credit_text', 'N/A')}",
        title="Credits Added",
        border_style="green"
    ))
    
    while True:
        console.print("\n[bold]What would you like to do next?[/bold]")
        console.print("\n[cyan]A)[/cyan] Continue to next step: Check for duplicate credits")
        console.print("    [dim]Command: python scripts/fix_duplicate_credits.py --video {video_id}[/dim]")
        console.print("\n[cyan]B)[/cyan] Sync metadata (if you manually deleted slides)")
        console.print("    [dim]Command: python scripts/sync_slide_metadata.py --video {video_id}[/dim]")
        console.print("\n[cyan]C)[/cyan] Review slides (if you haven't already)")
        console.print("    [dim]Command: python scripts/review_slides.py --video {video_id} --review-all[/dim]")
        console.print("\n[cyan]D)[/cyan] Add credits to another video")
        console.print("    [dim]Command: python scripts/add_credit_overlay.py --video VIDEO_ID[/dim]")
        console.print("\n[cyan]H)[/cyan] Show workflow help and useful commands")
        console.print("\n[cyan]E)[/cyan] Exit (you're done with this video)")
        
        choice = Prompt.ask(
            "\n[bold]Choose an option[/bold]",
            choices=["a", "A", "b", "B", "c", "C", "d", "D", "e", "E", "h", "H"],
            default="A"
        ).upper()
        
        if choice == "H":
            _show_workflow_help(video_id)
            continue
    
        if choice == "A":
            console.print(f"\n[bold]Running: python scripts/fix_duplicate_credits.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/fix_duplicate_credits.py", "--video", video_id])
            break
        elif choice == "B":
            console.print(f"\n[bold]Running: python scripts/sync_slide_metadata.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/sync_slide_metadata.py", "--video", video_id])
            break
        elif choice == "C":
            console.print(f"\n[bold]Running: python scripts/review_slides.py --video {video_id} --review-all[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/review_slides.py", "--video", video_id, "--review-all"])
            break
        elif choice == "D":
            new_video = Prompt.ask("\n[bold]Enter video ID to add credits to[/bold]")
            console.print(f"\n[bold]Running: python scripts/add_credit_overlay.py --video {new_video}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/add_credit_overlay.py", "--video", new_video])
            break
        else:
            console.print("\n[dim]Exiting. You can continue later with the commands shown above.[/dim]")
            break


@click.command()
@click.option('--video', '-v', help='Single video ID to add credits to')
@click.option('--all', '-a', 'process_all', is_flag=True, help='Process all videos with slides')
@click.option('--dry-run', '-d', is_flag=True, help='Preview what would be done without making changes')
@click.option('--credit-text', default='', help='Credit text (if not provided, will prompt interactively)')
@click.option('--credit-author', default='', help='Author name (used only if credit-text not provided)')
@click.option('--credit-series', default='', help='Series name (used only if credit-text not provided)')
@click.option('--non-interactive', is_flag=True, help='Skip interactive prompts (use defaults or CLI args)')
def main(video: str, process_all: bool, dry_run: bool, credit_text: str,
         credit_author: str, credit_series: str, non_interactive: bool):
    """Add credit overlay to existing slide images."""
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be modified[/yellow]\n")
    
    # Interactive credit text prompt (unless provided via CLI or non-interactive mode)
    final_credit_text = credit_text
    
    if not final_credit_text and not non_interactive:
        console.print(Panel(
            "[bold]Credit Overlay Configuration[/bold]\n\n"
            "Enter the exact text you want displayed in the credit bar at the bottom of each slide.\n"
            "This text will appear on all slides for this video.\n\n"
            "Examples:\n"
            "  • Scott Hebner • The Next Frontiers of AI\n"
            "  • Source: YouTube Video\n"
            "  • © 2025 The Cube Research\n"
            "  • [Your custom attribution text here]",
            title="Credit Text",
            border_style="blue"
        ))
        
        final_credit_text = Prompt.ask(
            "\n[bold]Enter credit text[/bold]",
            default="",
            show_default=False
        ).strip()
        
        if not final_credit_text:
            console.print("[yellow]No credit text provided. Skipping credit overlay.[/yellow]")
            if not Confirm.ask("\nContinue without credits?", default=False):
                sys.exit(0)
        else:
            # Show preview
            console.print(f"\n[dim]Preview:[/dim] [bold]{final_credit_text}[/bold]")
            if not Confirm.ask("\nUse this credit text?", default=True):
                console.print("[yellow]Credit overlay cancelled.[/yellow]")
                sys.exit(0)
    
    elif not final_credit_text and non_interactive:
        # Non-interactive mode: use defaults or auto-generate
        if credit_author or credit_series:
            parts = []
            if credit_author:
                parts.append(credit_author)
            if credit_series:
                parts.append(credit_series)
            final_credit_text = " • ".join(parts) if parts else ""
        else:
            console.print("[yellow]No credit text provided and non-interactive mode. Skipping.[/yellow]")
            sys.exit(0)
    
    if video:
        # Single video
        result = process_video(
            video,
            credit_text=final_credit_text or None,
            credit_author=credit_author,
            credit_series=credit_series,
            dry_run=dry_run
        )
        
        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        
        # Show next steps for single video (unless dry-run or non-interactive)
        if not dry_run and not non_interactive:
            _show_next_steps_after_credits(video, result)
    
    elif process_all:
        # All videos
        if not KB_DIR.exists():
            console.print("[red]No kb directory found. Run ingestion first.[/red]")
            sys.exit(1)
        
        metadata_file = KB_DIR / "metadata.json"
        if not metadata_file.exists():
            console.print("[red]No metadata.json found. Run ingestion first.[/red]")
            sys.exit(1)
        
        with open(metadata_file) as f:
            data = json.load(f)
        
        videos = [v['video_id'] for v in data.get('videos', [])]
        videos_with_slides = [
            v for v in videos
            if (DATA_SLIDES / v).exists() and list((DATA_SLIDES / v).glob("slide_*.png"))
        ]
        
        if not videos_with_slides:
            console.print("[yellow]No videos with slides found[/yellow]")
            return
        
        console.print(f"[bold]Processing {len(videos_with_slides)} videos...[/bold]\n")
        
        results = []
        for video_id in videos_with_slides:
            result = process_video(
                video_id,
                credit_text=final_credit_text or None,
                credit_author=credit_author,
                credit_series=credit_series,
                dry_run=dry_run
            )
            if 'error' not in result:
                results.append(result)
        
        # Summary
        total_processed = sum(r.get('processed', 0) for r in results)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Videos processed: {len(results)}")
        console.print(f"  Total slides: {total_processed}")
    
    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Run with --help for usage information.")


if __name__ == '__main__':
    main()

