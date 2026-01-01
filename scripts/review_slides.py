#!/usr/bin/env python3
"""
Interactive slide review tool - Human-in-the-loop quality curation.

Shows slides flagged for removal and allows human review before deletion.
This is a key feature: human curation ensures important content isn't lost.

Usage:
    python scripts/review_slides.py --video VIDEO_ID
    python scripts/review_slides.py --video VIDEO_ID --auto-approve  # Skip review, use filters
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Import quality filters
sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import SlideConfig, SlideInfo, SlideExtractor
from curation_progress import mark_reviewed, get_status_summary, get_video_progress, detect_video_state, select_video_interactive, get_next_video, show_curation_dashboard

PROJECT_ROOT = Path(__file__).parent.parent
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"

console = Console()

# Terminal width for image display
TERMINAL_WIDTH = min(console.width or 80, 120)


def display_image_in_terminal(image_path: Path) -> bool:
    """
    Display image inline in terminal using best available method.
    
    Tries in order:
    1. viu (terminal image viewer) - best quality
    2. chafa (terminal image viewer) - good quality
    3. imgcat (iTerm2) - macOS iTerm2 only
    4. PIL ASCII art - always works, lower quality
    5. Fallback: open in external viewer
    
    Returns True if displayed inline, False if opened externally.
    """
    # Flush console output before displaying image
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Method 1: Try viu (best quality, works in most terminals)
    # viu writes directly to the terminal TTY, so we don't capture output
    if shutil.which('viu'):
        try:
            # Get terminal size for optimal display
            cols = min(TERMINAL_WIDTH - 10, 80)
            # Use --blocks flag for better compatibility
            result = subprocess.run(
                ['viu', '-w', str(cols), '--blocks', str(image_path)],
                check=False
                # Don't capture output - let it write directly to terminal
            )
            sys.stdout.flush()  # Flush after viu
            if result.returncode == 0:
                return True
        except Exception as e:
            console.print(f"[dim]viu failed: {e}[/dim]")
    
    # Method 2: Try chafa (good quality, works in most terminals)
    # chafa writes directly to the terminal TTY
    if shutil.which('chafa'):
        try:
            result = subprocess.run(
                ['chafa', '--size', f'{TERMINAL_WIDTH - 10}x30', str(image_path)],
                check=False
                # Don't capture output - let it write directly to terminal
            )
            sys.stdout.flush()  # Flush after chafa
            if result.returncode == 0:
                return True
        except Exception as e:
            console.print(f"[dim]chafa failed: {e}[/dim]")
    
    # Method 3: Try imgcat (iTerm2 on macOS)
    # imgcat writes directly to the terminal TTY
    if shutil.which('imgcat'):
        try:
            result = subprocess.run(
                ['imgcat', str(image_path)],
                check=False
                # Don't capture output - let it write directly to terminal
            )
            sys.stdout.flush()  # Flush after imgcat
            if result.returncode == 0:
                return True
        except Exception as e:
            console.print(f"[dim]imgcat failed: {e}[/dim]")
    
    # Method 4: PIL-based ASCII art (always works)
    try:
        _display_ascii_image(image_path)
        return True
    except Exception as e:
        console.print(f"[dim]Could not display image inline: {e}[/dim]")
    
    # Method 5: Fallback to external viewer
    try:
        if sys.platform == 'darwin':
            subprocess.run(['open', str(image_path)], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform.startswith('linux'):
            subprocess.run(['xdg-open', str(image_path)], check=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print("[dim]Opened image in external viewer (fallback)[/dim]")
        return False
    except:
        pass
    
    return False


def _display_ascii_image(image_path: Path, max_width: int = 80, max_height: int = 20):
    """Display image as ASCII art in terminal."""
    try:
        # Load and resize image
        img = Image.open(image_path)
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convert to grayscale
        img = img.convert('L')
        
        # ASCII characters from dark to light
        ascii_chars = '@%#*+=-:. '
        
        # Convert to ASCII - get pixels as list (IMPORTANT: must convert to list first)
        # PIL's getdata() returns ImagingCore which can't be sliced directly
        pixels_data = img.getdata()
        pixels = list(pixels_data)  # Convert to list for proper slicing
        width = img.width
        height = img.height
        
        # Validate dimensions
        if len(pixels) != width * height:
            raise ValueError(f"Pixel count mismatch: expected {width * height}, got {len(pixels)}")
        
        console.print()  # Blank line before image
        for y in range(height):
            row_start = y * width
            row_end = row_start + width
            # Slice the list (now safe since pixels is a list)
            row = pixels[row_start:row_end]
            ascii_row = ''.join([ascii_chars[min(int(pixel) // 28, len(ascii_chars) - 1)] for pixel in row])
            console.print(f"[dim]{ascii_row}[/dim]")
        console.print()  # Blank line after image
        
    except Exception as e:
        raise Exception(f"ASCII conversion failed: {e}")


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


def get_removal_reason(slide: SlideInfo, extractor: SlideExtractor) -> Optional[str]:
    """Determine why a slide would be removed."""
    # Check blurry
    if extractor.config.filter_blurry and extractor._is_blurry(slide.path, extractor.config.blur_threshold):
        return "blurry"
    
    # Check mostly black
    if extractor._is_mostly_black(slide.path):
        return "mostly_black"
    
    # Check text quality
    ocr_text = slide.ocr_text or ""
    word_count = len(ocr_text.split())
    
    if word_count < extractor.config.min_ocr_words:
        return f"low_text ({word_count} words < {extractor.config.min_ocr_words})"
    
    # Check filler text
    if extractor.config.filter_filler_text and extractor._is_filler_text(ocr_text):
        return "filler_text"
    
    return None


def review_slides(video_id: str, config: SlideConfig, auto_approve: bool = False, review_all: bool = False) -> dict:
    """Interactive review of slides flagged for removal."""
    metadata = load_slide_metadata(video_id)
    if not metadata:
        console.print(f"[red]No metadata found for {video_id}[/red]")
        return {'error': 'No metadata found'}

    # Load all slides
    all_slides = []
    for slide_data in metadata.get('slides', []):
        slide_info = create_slide_info(slide_data, video_id)
        if slide_info.path.exists():
            all_slides.append(slide_info)

    if not all_slides:
        console.print(f"[yellow]No slides found for {video_id}[/yellow]")
        return {'error': 'No slides found'}

    # Create extractor for filtering
    extractor = SlideExtractor(video_id, config)
    
    # Apply filters to identify slides for removal
    slides_to_review = []
    slides_to_keep = []
    
    if review_all:
        # Review ALL slides, not just flagged ones
        for slide in all_slides:
            reason = get_removal_reason(slide, extractor)
            # Use reason if found, otherwise mark as "manual_review"
            review_reason = reason or "manual_review"
            slides_to_review.append((slide, review_reason))
    else:
        # Only review flagged slides (default behavior)
        for slide in all_slides:
            reason = get_removal_reason(slide, extractor)
            if reason:
                slides_to_review.append((slide, reason))
            else:
                slides_to_keep.append(slide)

        # Check duplicates separately
        if config.remove_duplicates:
            deduplicated = extractor.deduplicate(all_slides)
            kept_hashes = {s.perceptual_hash for s in deduplicated}
            for slide in all_slides:
                if slide.perceptual_hash and slide.perceptual_hash not in kept_hashes:
                    # Check if already in review list
                    if not any(s.path == slide.path for s, _ in slides_to_review):
                        slides_to_review.append((slide, "duplicate"))

    if not slides_to_review:
        console.print(f"[green]✓ All {len(all_slides)} slides passed quality checks![/green]")
        return {
            'video_id': video_id,
            'total': len(all_slides),
            'reviewed': 0,
            'removed': 0,
            'kept': len(all_slides)
        }

    # Deduplicate slides_to_review to ensure each slide appears only once
    # Use a dict to track seen slides by path, keeping the first occurrence
    seen_paths = {}
    deduplicated_review = []
    for slide, reason in slides_to_review:
        slide_path = str(slide.path)
        if slide_path not in seen_paths:
            seen_paths[slide_path] = True
            deduplicated_review.append((slide, reason))
        else:
            # If duplicate found, use the more specific reason if available
            for idx, (existing_slide, existing_reason) in enumerate(deduplicated_review):
                if str(existing_slide.path) == slide_path:
                    # Prefer more specific reasons over "manual_review"
                    if reason != "manual_review" and existing_reason == "manual_review":
                        deduplicated_review[idx] = (existing_slide, reason)
                    break
    
    slides_to_review = deduplicated_review

    console.print(f"\n[bold]Slide Review for {video_id}[/bold]")
    console.print(f"Total slides: {len(all_slides)}")
    if review_all:
        console.print(f"[cyan]Reviewing ALL slides (manual curation mode)[/cyan]")
    else:
        console.print(f"Passed filters: {len(slides_to_keep)}")
    console.print(f"[yellow]Flagged for review: {len(slides_to_review)}[/yellow]\n")

    if auto_approve:
        console.print("[dim]Auto-approve mode: Removing all flagged slides without review[/dim]")
        approved_removals = slides_to_review
        rejected_removals = []
    else:
        # Interactive review
        console.print(Panel(
            "[bold]Human-in-the-Loop Review[/bold]\n\n"
            "Review each flagged slide and decide:\n"
            "• [green]Keep[/green] - Slide is important, preserve it\n"
            "• [red]Remove[/red] - Slide is low-quality/duplicate\n\n"
            "This ensures important content isn't accidentally deleted.",
            title="Review Mode",
            border_style="blue"
        ))

        approved_removals = []
        rejected_removals = []

        for i, (slide, reason) in enumerate(slides_to_review, 1):
            console.print(f"\n[bold cyan]Slide {i}/{len(slides_to_review)}[/bold cyan]")
            
            # Show slide info
            table = Table(show_header=False, box=None)
            table.add_column("Property", style="dim")
            table.add_column("Value")
            
            table.add_row("Filename", slide.path.name)
            table.add_row("Timestamp", slide.timestamp_formatted)
            table.add_row("Reason", f"[yellow]{reason}[/yellow]")
            
            ocr_preview = (slide.ocr_text or "")[:200]
            if len(slide.ocr_text or "") > 200:
                ocr_preview += "..."
            table.add_row("OCR Text", ocr_preview or "[dim](no text)[/dim]")
            
            console.print(table)
            
            # Display image inline in terminal
            console.print("\n[dim]Displaying slide image...[/dim]")
            displayed_inline = display_image_in_terminal(slide.path)
            
            if not displayed_inline:
                console.print("[yellow]Tip: Install 'viu' for better inline image display:[/yellow]")
                console.print("[dim]  brew install viu[/dim]")
            
            # Ask for decision
            keep = Confirm.ask(
                f"\n[bold]Keep this slide?[/bold]",
                default=True
            )
            
            if keep:
                rejected_removals.append((slide, reason))
                console.print("[green]✓ Keeping slide[/green]")
            else:
                approved_removals.append((slide, reason))
                console.print("[red]✗ Marked for removal[/red]")

    # Summary
    console.print(f"\n[bold]Review Summary:[/bold]")
    console.print(f"  Total slides: {len(all_slides)}")
    if not review_all:
        console.print(f"  Passed filters: {len(slides_to_keep)}")
    console.print(f"  Reviewed: {len(slides_to_review)}")
    console.print(f"  [green]Kept after review: {len(rejected_removals)}[/green]")
    console.print(f"  [red]Approved for removal: {len(approved_removals)}[/red]")
    final_count = len(slides_to_keep) + len(rejected_removals) if not review_all else len(rejected_removals)
    console.print(f"  Final count: {final_count} slides")

    if approved_removals:
        # Show what will be removed
        console.print(f"\n[bold yellow]Slides to be removed:[/bold yellow]")
        removal_table = Table(show_header=True)
        removal_table.add_column("Filename", style="cyan")
        removal_table.add_column("Timestamp", style="dim")
        removal_table.add_column("Reason", style="yellow")
        
        for slide, reason in approved_removals:
            removal_table.add_row(
                slide.path.name,
                slide.timestamp_formatted,
                reason
            )
        console.print(removal_table)

        # Confirm removal
        if not auto_approve:
            proceed = Confirm.ask(
                f"\n[bold]Remove {len(approved_removals)} approved slides?[/bold]",
                default=True
            )
        else:
            proceed = True

        if proceed:
            # Remove files
            removed_count = 0
            for slide, _ in approved_removals:
                try:
                    slide.path.unlink()
                    removed_count += 1
                except Exception as e:
                    console.print(f"[red]Error removing {slide.path.name}: {e}[/red]")

            # Update metadata
            final_slides = slides_to_keep + [s for s, _ in rejected_removals]
            
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
                for s in final_slides
            ]
            
            metadata['stats']['slides_detected'] = len(final_slides)
            metadata['stats']['unique_slides'] = len(final_slides)
            metadata['stats']['duplicates'] = 0
            metadata['human_reviewed'] = True
            metadata['review_stats'] = {
                'total_reviewed': len(slides_to_review),
                'approved_removal': len(approved_removals),
                'kept_after_review': len(rejected_removals),
            }
            
            # Save updated metadata
            metadata_file = DATA_SLIDES / video_id / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            console.print(f"\n[green]✓ Removed {removed_count} slides[/green]")
            console.print(f"[green]✓ Updated metadata[/green]")
            
            # Update progress tracking
            mark_reviewed(
                video_id,
                slides_kept=len(final_slides),
                slides_removed=removed_count
            )
            
            # Final sync to ensure metadata matches files exactly
            console.print("[dim]Final sync: ensuring metadata matches files on disk...[/dim]")
            try:
                from sync_slide_metadata import sync_video_metadata
                sync_result = sync_video_metadata(video_id, dry_run=False)
                if sync_result.get('removed', 0) > 0:
                    console.print(f"[green]✓ Synced metadata (removed {sync_result['removed']} orphaned entries)[/green]")
            except Exception as e:
                console.print(f"[dim]Note: Could not auto-sync: {e}[/dim]")
                console.print(f"[dim]Run manually: python scripts/sync_slide_metadata.py --video {video_id}[/dim]")
            
            return {
                'video_id': video_id,
                'total': len(all_slides),
                'reviewed': len(slides_to_review),
                'removed': removed_count,
                'kept_after_review': len(rejected_removals),
                'final_count': len(final_slides)
            }
        else:
            console.print("[yellow]Removal cancelled[/yellow]")
            return {
                'video_id': video_id,
                'total': len(all_slides),
                'reviewed': len(slides_to_review),
                'removed': 0,
                'cancelled': True
            }
    else:
        console.print("[green]No slides to remove[/green]")
        return {
            'video_id': video_id,
            'total': len(all_slides),
            'reviewed': len(slides_to_review),
            'removed': 0,
            'kept': len(all_slides)
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


def _show_next_steps_after_review(video_id: str, result: dict):
    """Show interactive next steps after slide review."""
    console.print("\n")
    console.print(Panel(
        f"[bold green]✓ Slide review complete![/bold green]\n\n"
        f"Reviewed: {result.get('reviewed', 0)} slides\n"
        f"Kept: {result.get('final_count', 0)} slides\n"
        f"Removed: {result.get('removed', 0)} slides",
        title="Review Complete",
        border_style="green"
    ))
    
    while True:
        console.print("\n[bold]What would you like to do next?[/bold]")
        console.print("\n[cyan]A)[/cyan] Continue to next step: Add credit overlay")
        console.print("    [dim]Command: python scripts/add_credit_overlay.py --video {video_id}[/dim]")
        console.print("\n[cyan]B)[/cyan] Check for duplicate credits")
        console.print("    [dim]Command: python scripts/fix_duplicate_credits.py --video {video_id}[/dim]")
        console.print("\n[cyan]C)[/cyan] Sync metadata (if you manually deleted slides)")
        console.print("    [dim]Command: python scripts/sync_slide_metadata.py --video {video_id}[/dim]")
        console.print("\n[cyan]D)[/cyan] Review another video")
        console.print("    [dim]Command: python scripts/review_slides.py --video VIDEO_ID --review-all[/dim]")
        console.print("\n[cyan]N)[/cyan] Move to next video (start review)")
        console.print("    [dim]Automatically starts review for the next video in the list[/dim]")
        console.print("\n[cyan]S)[/cyan] Show status for this video")
        console.print("\n[cyan]H)[/cyan] Show workflow help and useful commands")
        console.print("\n[cyan]E)[/cyan] Exit (you're done with this video)")
        console.print("    [dim]You can manually delete slides and sync metadata later[/dim]")
        
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
            console.print(f"\n[bold]Running: python scripts/add_credit_overlay.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/add_credit_overlay.py", "--video", video_id])
            break
        elif choice == "B":
            console.print(f"\n[bold]Running: python scripts/fix_duplicate_credits.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/fix_duplicate_credits.py", "--video", video_id])
            break
        elif choice == "C":
            console.print(f"\n[bold]Running: python scripts/sync_slide_metadata.py --video {video_id}[/bold]\n")
            import subprocess
            subprocess.run([sys.executable, "scripts/sync_slide_metadata.py", "--video", video_id])
            break
        elif choice == "D":
            console.print("\n[bold]Select video to review:[/bold]")
            new_video = select_video_interactive("Select a video to review")
            if new_video:
                console.print(f"\n[bold]Running: python scripts/review_slides.py --video {new_video} --review-all[/bold]\n")
                import subprocess
                subprocess.run([sys.executable, "scripts/review_slides.py", "--video", new_video, "--review-all"])
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


def _show_curation_dashboard():
    """Show curation status dashboard."""
    summary = get_status_summary()
    
    console.print("\n")
    console.print(Panel(
        f"[bold]Curation Progress Dashboard[/bold]\n\n"
        f"Total videos with slides: {summary['total_videos']}\n"
        f"  [green]✓ Completed: {len(summary['completed'])}[/green]\n"
        f"  [cyan]→ Credits added: {len(summary['credits_added'])}[/cyan]\n"
        f"  [yellow]→ Reviewed: {len(summary['reviewed'])}[/yellow]\n"
        f"  [red]→ Pending: {len(summary['pending'])}[/red]",
        title="Status",
        border_style="blue"
    ))
    
    if summary['pending']:
        console.print("\n[bold red]Pending Videos (not yet reviewed):[/bold red]")
        for vid in summary['pending'][:15]:  # Show first 15
            console.print(f"  [red]• {vid}[/red]")
        if len(summary['pending']) > 15:
            console.print(f"  [dim]... and {len(summary['pending']) - 15} more[/dim]")
        console.print(f"\n[bold]Next: Review a pending video[/bold]")
        console.print(f"[dim]Example: python scripts/review_slides.py --video {summary['pending'][0]} --review-all[/dim]")
    
    if summary['reviewed']:
        console.print("\n[bold yellow]Reviewed Videos (need credits):[/bold yellow]")
        for vid in summary['reviewed'][:10]:
            vid_info = summary['videos'][vid]
            kept = vid_info.get('slides_kept', '?')
            removed = vid_info.get('slides_removed', '?')
            console.print(f"  [yellow]• {vid} ({kept} kept, {removed} removed)[/yellow]")
        if len(summary['reviewed']) > 10:
            console.print(f"  [dim]... and {len(summary['reviewed']) - 10} more[/dim]")
    
    if summary['credits_added']:
        console.print("\n[bold cyan]Videos with Credits (need finalization):[/bold cyan]")
        for vid in summary['credits_added'][:5]:
            console.print(f"  [cyan]• {vid}[/cyan]")
        if len(summary['credits_added']) > 5:
            console.print(f"  [dim]... and {len(summary['credits_added']) - 5} more[/dim]")
    
    if summary['completed']:
        console.print("\n[bold green]Completed Videos:[/bold green]")
        console.print(f"  [green]✓ {len(summary['completed'])} videos fully curated[/green]")
        if len(summary['completed']) <= 5:
            for vid in summary['completed']:
                console.print(f"    [dim]• {vid}[/dim]")
    
    console.print("\n[bold]Quick Commands:[/bold]")
    console.print("[dim]  Review: python scripts/review_slides.py --video VIDEO_ID --review-all[/dim]")
    console.print("[dim]  Status: python scripts/review_slides.py --status[/dim]")
    console.print("[dim]  Help:   Choose 'H' in any interactive menu[/dim]\n")


@click.command()
@click.option('--video', '-v', help='Video ID to review (omit for interactive selection)')
@click.option('--status', '-s', is_flag=True, help='Show curation status dashboard')
@click.option('--auto-approve', '-a', is_flag=True, help='Auto-approve all flagged slides (skip review)')
@click.option('--review-all', '-r', is_flag=True, help='Review ALL slides, not just flagged ones')
@click.option('--min-words', default=10, type=int, help='Minimum words in OCR text')
@click.option('--filter-filler/--keep-filler', default=True, help='Filter filler text slides')
@click.option('--filter-blurry/--keep-blurry', default=True, help='Filter blurry images')
@click.option('--blur-threshold', default=100.0, type=float, help='Blur detection threshold')
def main(video: str, status: bool, auto_approve: bool, review_all: bool, min_words: int, filter_filler: bool,
         filter_blurry: bool, blur_threshold: float):
    """Interactive slide review - Human-in-the-loop quality curation."""
    
    # Show curation status dashboard
    if status:
        _show_curation_dashboard()
        return
    
    # Interactive video selection if no video provided
    if not video:
        console.print("\n[bold]Interactive Video Selection[/bold]")
        selected_video = select_video_interactive("Select a video to review")
        if not selected_video:
            console.print("[yellow]No video selected. Exiting.[/yellow]")
            return
        video = selected_video
    
    # Show video-specific status before starting
    video_progress = get_video_progress(video)
    if video_progress.get('reviewed'):
        console.print(f"\n[dim]This video was previously reviewed on {video_progress.get('reviewed_date', 'unknown date')}[/dim]")
        console.print(f"[dim]Kept: {video_progress.get('slides_kept', '?')} slides, Removed: {video_progress.get('slides_removed', '?')} slides[/dim]")
        if not Confirm.ask("\n[bold]Review again?[/bold]", default=False):
            console.print("[yellow]Skipping review[/yellow]")
            return
    
    config = SlideConfig(
        min_ocr_words=min_words,
        filter_filler_text=filter_filler,
        filter_blurry=filter_blurry,
        blur_threshold=blur_threshold,
        remove_duplicates=True,
    )

    result = review_slides(video, config, auto_approve, review_all)
    
    if 'error' in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    
    # Show next steps if successful
    if not auto_approve and 'removed' in result:
        _show_next_steps_after_review(video, result)


if __name__ == '__main__':
    main()

