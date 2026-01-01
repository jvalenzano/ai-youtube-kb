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
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

# Import quality filters
sys.path.insert(0, str(Path(__file__).parent))
from extract_slides import SlideConfig, SlideInfo, SlideExtractor

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
    # Method 1: Try viu (best quality, works in most terminals)
    if shutil.which('viu'):
        try:
            # Get terminal size for optimal display
            cols = min(TERMINAL_WIDTH - 10, 80)
            subprocess.run(
                ['viu', '-w', str(cols), str(image_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except:
            pass
    
    # Method 2: Try chafa (good quality, works in most terminals)
    if shutil.which('chafa'):
        try:
            subprocess.run(
                ['chafa', '--size', f'{TERMINAL_WIDTH - 10}x30', str(image_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except:
            pass
    
    # Method 3: Try imgcat (iTerm2 on macOS)
    if shutil.which('imgcat'):
        try:
            subprocess.run(
                ['imgcat', str(image_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except:
            pass
    
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
        
        # Convert to ASCII
        pixels = img.getdata()
        width = img.width
        
        console.print()  # Blank line before image
        for i in range(0, len(pixels), width):
            row = pixels[i:i + width]
            ascii_row = ''.join([ascii_chars[min(pixel // 28, len(ascii_chars) - 1)] for pixel in row])
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


def review_slides(video_id: str, config: SlideConfig, auto_approve: bool = False) -> dict:
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

    console.print(f"\n[bold]Slide Review for {video_id}[/bold]")
    console.print(f"Total slides: {len(all_slides)}")
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
    console.print(f"  Passed filters: {len(slides_to_keep)}")
    console.print(f"  Reviewed: {len(slides_to_review)}")
    console.print(f"  [green]Kept after review: {len(rejected_removals)}[/green]")
    console.print(f"  [red]Approved for removal: {len(approved_removals)}[/red]")
    console.print(f"  Final count: {len(slides_to_keep) + len(rejected_removals)} slides")

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


@click.command()
@click.option('--video', '-v', required=True, help='Video ID to review')
@click.option('--auto-approve', '-a', is_flag=True, help='Auto-approve all flagged slides (skip review)')
@click.option('--min-words', default=10, type=int, help='Minimum words in OCR text')
@click.option('--filter-filler/--keep-filler', default=True, help='Filter filler text slides')
@click.option('--filter-blurry/--keep-blurry', default=True, help='Filter blurry images')
@click.option('--blur-threshold', default=100.0, type=float, help='Blur detection threshold')
def main(video: str, auto_approve: bool, min_words: int, filter_filler: bool,
         filter_blurry: bool, blur_threshold: float):
    """Interactive slide review - Human-in-the-loop quality curation."""
    
    config = SlideConfig(
        min_ocr_words=min_words,
        filter_filler_text=filter_filler,
        filter_blurry=filter_blurry,
        blur_threshold=blur_threshold,
        remove_duplicates=True,
    )

    result = review_slides(video, config, auto_approve)
    
    if 'error' in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()

