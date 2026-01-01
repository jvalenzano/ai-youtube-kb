#!/usr/bin/env python3
"""
Stage completed videos for NotebookLM upload with embedded metadata.

This script prepares files for NotebookLM upload by:
1. Renaming slide images to include video_id (VIDEO_ID_slide_TIMESTAMP.png)
2. Creating companion text files for each slide with full metadata
3. Ensuring all files are self-contained with enough context for NotebookLM
4. Moving (not copying) files to a flat staging directory

NotebookLM can only upload individual files (not folders), so each file must
contain enough metadata to understand relationships.

Usage:
    python scripts/stage_for_notebooklm.py              # Stage completed videos
    python scripts/stage_for_notebooklm.py --dry-run    # Preview what will be moved
    python scripts/stage_for_notebooklm.py --video VIDEO_ID  # Stage specific video
"""

import json
import shutil
from pathlib import Path
from typing import Optional

import sys
import click
from rich.console import Console
from rich.table import Table

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from curation_progress import get_status_summary, get_video_progress

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
STAGING_DIR = NOTEBOOKS_DIR / "notebooklm-staging"

console = Console()


def ensure_staging_dir():
    """Create staging directory (flat structure for NotebookLM)."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


def get_completed_videos() -> list[str]:
    """Get list of completed video IDs."""
    summary = get_status_summary()
    return summary['completed']


def get_video_title(video_id: str) -> str:
    """Get video title from curated data or raw data."""
    curated_file = DATA_CLEAN / f"{video_id}.json"
    if curated_file.exists():
        try:
            with open(curated_file) as f:
                data = json.load(f)
                return data.get('title', video_id)
        except Exception:
            pass
    
    raw_file = DATA_RAW / f"{video_id}.json"
    if raw_file.exists():
        try:
            with open(raw_file) as f:
                data = json.load(f)
                return data.get('title', video_id)
        except Exception:
            pass
    
    return video_id


def get_video_metadata(video_id: str) -> dict:
    """Get complete video metadata from curated data, raw data, or slide metadata."""
    curated_file = DATA_CLEAN / f"{video_id}.json"
    if curated_file.exists():
        try:
            with open(curated_file) as f:
                return json.load(f)
        except Exception:
            pass
    
    raw_file = DATA_RAW / f"{video_id}.json"
    if raw_file.exists():
        try:
            with open(raw_file) as f:
                return json.load(f)
        except Exception:
            pass
    
    # Fallback: Get metadata from slide metadata.json
    slide_metadata_file = DATA_SLIDES / video_id / "metadata.json"
    if slide_metadata_file.exists():
        try:
            with open(slide_metadata_file) as f:
                slide_meta = json.load(f)
                return {
                    'video_id': video_id,
                    'title': slide_meta.get('title', video_id),
                    'url': slide_meta.get('url', f'https://www.youtube.com/watch?v={video_id}'),
                    'channel': 'Unknown',
                    'duration_formatted': 'Unknown'
                }
        except Exception:
            pass
    
    return {'video_id': video_id, 'title': video_id, 'url': f'https://www.youtube.com/watch?v={video_id}'}


def create_slide_companion_file(video_id: str, video_meta: dict, slide_data: dict, 
                                new_filename: str, dry_run: bool = False) -> bool:
    """
    Create a companion text file for a slide with all metadata.
    This ensures NotebookLM can understand the slide's context.
    """
    companion_file = STAGING_DIR / f"{new_filename.stem}.txt"
    
    content = []
    content.append(f"# Slide from: {video_meta.get('title', video_id)}")
    content.append("")
    content.append("## Video Information")
    content.append(f"**Video ID:** {video_id}")
    content.append(f"**Title:** {video_meta.get('title', 'Unknown')}")
    content.append(f"**Channel:** {video_meta.get('channel', 'Unknown')}")
    content.append(f"**URL:** {video_meta.get('url', '')}")
    content.append(f"**Duration:** {video_meta.get('duration_formatted', 'Unknown')}")
    content.append("")
    
    # Module info
    if video_meta.get('module'):
        # Module definitions (same as in export_notebooklm.py)
        MODULES = {
            "foundations": {"name": "Foundations of AI Agents"},
            "workflows": {"name": "Agentic Workflows & Orchestration"},
            "tooling": {"name": "Tooling & Frameworks"},
            "case_studies": {"name": "Case Studies & Lessons"},
        }
        module_key = video_meta.get('module')
        module_info = MODULES.get(module_key, {})
        content.append(f"**Module:** {module_info.get('name', module_key)}")
        if video_meta.get('module_rationale'):
            content.append(f"**Module Rationale:** {video_meta.get('module_rationale')}")
        content.append("")
    
    # Slide-specific information
    content.append("## Slide Information")
    content.append(f"**Timestamp:** {slide_data.get('timestamp_formatted', 'Unknown')}")
    content.append(f"**Timestamp URL:** {slide_data.get('timestamp_url', '')}")
    content.append(f"**Original Filename:** {slide_data.get('filename', 'Unknown')}")
    content.append("")
    
    # Transcript context
    transcript_context = slide_data.get('transcript_context', {})
    if transcript_context:
        content.append("## Transcript Context")
        if transcript_context.get('before'):
            content.append(f"**Before:** {transcript_context['before']}")
        if transcript_context.get('during'):
            content.append(f"**During:** {transcript_context['during']}")
        if transcript_context.get('after'):
            content.append(f"**After:** {transcript_context['after']}")
        content.append("")
    
    # OCR text
    ocr_text = slide_data.get('ocr_text', '').strip()
    if ocr_text:
        content.append("## Slide Content (OCR)")
        content.append(ocr_text)
        content.append("")
    
    # Attribution
    content.append("---")
    content.append("")
    content.append(f"*This slide is from the video: {video_meta.get('title', video_id)}*")
    content.append(f"*Original content by {video_meta.get('channel', 'Unknown')}*")
    content.append(f"*Video URL: {video_meta.get('url', '')}*")
    content.append(f"*Slide timestamp: {slide_data.get('timestamp_formatted', 'Unknown')}*")
    
    if not dry_run:
        try:
            with open(companion_file, 'w') as f:
                f.write('\n'.join(content))
            return True
        except Exception as e:
            console.print(f"  [red]Error creating companion file: {e}[/red]")
            return False
    return True


def stage_video_files(video_id: str, dry_run: bool = False) -> dict:
    """
    Stage all files for a completed video with embedded metadata.
    Returns dict with counts of moved files.
    """
    stats = {
        'slides_moved': 0,
        'companion_files': 0,
        'transcript_moved': False,
        'errors': []
    }
    
    # Get video metadata
    video_meta = get_video_metadata(video_id)
    
    # 1. Process slides - rename and create companion files
    slide_source_dir = DATA_SLIDES / video_id
    if slide_source_dir.exists():
        metadata_file = slide_source_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    slide_metadata = json.load(f)
                
                slides = slide_metadata.get('slides', [])
                for slide_data in slides:
                    # Skip duplicates
                    if slide_data.get('is_duplicate_of'):
                        continue
                    
                    original_filename = slide_data.get('filename')
                    original_path = slide_source_dir / original_filename
                    
                    if not original_path.exists():
                        continue
                    
                    # Create new filename with video_id: VIDEO_ID_slide_TIMESTAMP.png
                    timestamp = slide_data.get('timestamp_formatted', '').replace('m', 'm').replace('s', 's')
                    new_filename = STAGING_DIR / f"{video_id}_slide_{timestamp}.png"
                    
                    if not dry_run:
                        try:
                            # Copy (not move) the slide image
                            shutil.copy2(str(original_path), str(new_filename))
                            stats['slides_moved'] += 1
                            
                            # Create companion text file
                            if create_slide_companion_file(video_id, video_meta, slide_data, 
                                                          new_filename, dry_run=False):
                                stats['companion_files'] += 1
                        except Exception as e:
                            stats['errors'].append(f"Error processing slide {original_filename}: {e}")
                    else:
                        stats['slides_moved'] += 1
                        stats['companion_files'] += 1
            except Exception as e:
                stats['errors'].append(f"Error reading slide metadata: {e}")
    
    # 2. Create/update transcript file with slide references
    # Find existing transcript or create new one
    videos_dir = NOTEBOOKS_DIR / "notebooklm-ready" / "videos"
    transcript_found = False
    
    # Load slide metadata for transcript updates
    slide_metadata_for_transcript = {}
    if slide_source_dir.exists():
        metadata_file = slide_source_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    slide_metadata_for_transcript = json.load(f)
            except Exception:
                pass
    
    if videos_dir.exists():
        for txt_file in videos_dir.glob("*.txt"):
            try:
                with open(txt_file) as f:
                    content = f.read()
                    if f'**Video ID:** {video_id}' in content:
                        # Update transcript to reference new slide filenames
                        updated_content = update_transcript_slide_references(
                            content, video_id, slide_metadata_for_transcript
                        )
                        
                        # Create new filename with video_id
                        safe_title = sanitize_filename(video_meta.get('title', video_id))
                        new_transcript_file = STAGING_DIR / f"{video_id}_transcript_{safe_title}.txt"
                        
                        if not dry_run:
                            try:
                                with open(new_transcript_file, 'w') as f:
                                    f.write(updated_content)
                                # Move original transcript
                                shutil.move(str(txt_file), str(STAGING_DIR / f"{video_id}_transcript_original.txt"))
                                stats['transcript_moved'] = True
                                transcript_found = True
                            except Exception as e:
                                stats['errors'].append(f"Error moving transcript: {e}")
                        else:
                            stats['transcript_moved'] = True
                            transcript_found = True
                        break
            except Exception:
                continue
    
    # If no transcript found, create one from curated data
    if not transcript_found and not dry_run:
        try:
            transcript_content = create_transcript_from_metadata(video_id, video_meta)
            safe_title = sanitize_filename(video_meta.get('title', video_id))
            transcript_file = STAGING_DIR / f"{video_id}_transcript_{safe_title}.txt"
            with open(transcript_file, 'w') as f:
                f.write(transcript_content)
            stats['transcript_moved'] = True
        except Exception as e:
            stats['errors'].append(f"Error creating transcript: {e}")
    
    # 3. After staging, remove original files (if not dry run)
    if not dry_run:
        # Remove slide directory
        if slide_source_dir.exists():
            try:
                # Only remove if we successfully processed slides
                if stats['slides_moved'] > 0:
                    shutil.rmtree(slide_source_dir)
            except Exception as e:
                stats['errors'].append(f"Error removing slide directory: {e}")
    
    return stats


def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    import re
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:100]  # Limit length
    return safe


def update_transcript_slide_references(content: str, video_id: str, slide_metadata: dict) -> str:
    """
    Update transcript to reference new slide filenames (VIDEO_ID_slide_TIMESTAMP.png).
    """
    slides = slide_metadata.get('slides', [])
    
    # Create mapping from old format to new format
    slide_map = {}
    for slide in slides:
        if slide.get('is_duplicate_of'):
            continue
        old_ref = slide.get('filename', '')
        timestamp = slide.get('timestamp_formatted', '')
        new_ref = f"{video_id}_slide_{timestamp}.png"
        slide_map[old_ref] = new_ref
    
    # Update references in content
    for old_ref, new_ref in slide_map.items():
        content = content.replace(old_ref, new_ref)
    
    # Add header note about slide files
    if slide_map:
        header_note = f"\n\n---\n**Note:** This transcript references {len(slide_map)} slide images. "
        header_note += f"Each slide has a companion .txt file with full metadata. "
        header_note += f"Slide filenames follow the pattern: {video_id}_slide_TIMESTAMP.png\n"
        content = header_note + content
    
    return content


def create_transcript_from_metadata(video_id: str, video_meta: dict) -> str:
    """Create transcript file from curated metadata or slide data."""
    content = []
    
    # Header
    title = video_meta.get('title', video_id)
    content.append(f"# {title}")
    content.append("")
    content.append(f"**Video ID:** {video_id}")
    content.append(f"**Channel:** {video_meta.get('channel', 'Unknown')}")
    content.append(f"**Duration:** {video_meta.get('duration_formatted', 'Unknown')}")
    content.append(f"**URL:** {video_meta.get('url', '')}")
    content.append("")
    
    # Check if we have curated data (full transcript) or just slides
    has_curated_data = bool(video_meta.get('summary') or video_meta.get('key_takeaways'))
    
    if not has_curated_data:
        # No transcript available - create document from slides only
        content.append("## ⚠️ Transcript Not Available")
        content.append("")
        content.append("**Note:** Full video transcript is not available for this video.")
        content.append("This may be due to:")
        content.append("- YouTube rate limiting during batch processing")
        content.append("- Transcripts disabled or not available for this video")
        content.append("- Video age or accessibility restrictions")
        content.append("")
        content.append("**Content Available:**")
        content.append("- Presentation slides with OCR text (below)")
        content.append("- Slide companion files with full metadata")
        content.append("- Slide images with timestamps")
        content.append("")
    
    # Summary (if available from curation)
    if video_meta.get('summary'):
        content.append("## Summary")
        for bullet in video_meta.get('summary', []):
            content.append(f"- {bullet}")
        content.append("")
    
    # Key Takeaways (if available from curation)
    if video_meta.get('key_takeaways'):
        content.append("## Key Takeaways")
        for takeaway in video_meta.get('key_takeaways', []):
            prefix = "DO" if takeaway.get('type') == 'do' else "DON'T"
            content.append(f"- **{prefix}:** {takeaway.get('text', '')}")
        content.append("")
    
    # Slides section with references
    slide_source_dir = DATA_SLIDES / video_id
    if slide_source_dir.exists():
        metadata_file = slide_source_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                slide_metadata = json.load(f)
            
            slides = [s for s in slide_metadata.get('slides', []) if not s.get('is_duplicate_of')]
            if slides:
                content.append("## Presentation Slides")
                if not has_curated_data:
                    content.append(f"*{len(slides)} unique slides extracted from this video*")
                    content.append("*Content below is extracted from slide OCR text.*")
                else:
                    content.append(f"*{len(slides)} unique slides extracted from this video*")
                content.append("")
                content.append("**Note:** Each slide image has a companion .txt file with full metadata.")
                content.append(f"Slide filenames: {video_id}_slide_TIMESTAMP.png")
                content.append("")
                for slide in slides:
                    ts = slide.get('timestamp_formatted', '')
                    ts_url = slide.get('timestamp_url', '')
                    slide_filename = f"{video_id}_slide_{ts}.png"
                    ocr = slide.get('ocr_text', '').strip()
                    if ocr:
                        content.append(f"### Slide: [{slide_filename}]({ts_url}) at {ts}")
                        content.append("")
                        content.append(ocr)
                        content.append("")
                content.append("")
    
    # Full Transcript section (only if we have curated data with transcript)
    if has_curated_data and video_meta.get('transcript'):
        content.append("## Full Transcript")
        content.append("")
        content.append(video_meta.get('transcript', ''))
        content.append("")
    elif not has_curated_data:
        content.append("## Full Transcript")
        content.append("")
        content.append("*Transcript not available. Content extracted from presentation slides only.*")
        content.append("")
    
    # Attribution
    content.append("---")
    content.append("")
    if not has_curated_data:
        content.append(f"*Content extracted from YouTube video slides. Full transcript not available.")
        content.append(f"*Original content by {video_meta.get('channel', 'Unknown')}. Video URL: {video_meta.get('url', '')}*")
    else:
        content.append(f"*Content extracted from YouTube video. Original content by {video_meta.get('channel', 'Unknown')}. Video URL: {video_meta.get('url', '')}*")
    
    return '\n'.join(content)


def show_staging_summary(videos_staged: list[str], stats_by_video: dict, dry_run: bool):
    """Display summary of staging operation."""
    table = Table(title="Staging Summary", show_header=True, header_style="bold magenta")
    table.add_column("Video ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Slides", justify="right")
    table.add_column("Companions", justify="right")
    table.add_column("Transcript", justify="center")
    table.add_column("Status", style="green")
    
    total_slides = 0
    total_companions = 0
    
    for video_id in videos_staged:
        title = get_video_title(video_id)
        stats = stats_by_video.get(video_id, {})
        slides = stats.get('slides_moved', 0)
        companions = stats.get('companion_files', 0)
        transcript = "✅" if stats.get('transcript_moved') else "❌"
        
        status = "✅ Ready" if not stats.get('errors') else "⚠️  Errors"
        if stats.get('errors'):
            status += f" ({len(stats['errors'])} errors)"
        
        table.add_row(
            video_id,
            title[:50] + "..." if len(title) > 50 else title,
            str(slides),
            str(companions),
            transcript,
            status
        )
        
        total_slides += slides
        total_companions += companions
    
    console.print(table)
    
    # Summary stats
    total_files = total_slides + total_companions + sum(1 for s in stats_by_video.values() if s.get('transcript_moved'))
    console.print(f"\n[bold]Total:[/bold] {len(videos_staged)} videos, {total_slides} slides, {total_companions} companion files, {total_files} total files")
    
    if dry_run:
        console.print("\n[yellow]This was a dry run. No files were actually moved.[/yellow]")
        console.print("[yellow]Run without --dry-run to actually stage files.[/yellow]")
    else:
        console.print(f"\n[green]✅ Files staged to: {STAGING_DIR}[/green]")
        console.print("\n[bold]NotebookLM Upload Instructions:[/bold]")
        console.print("1. Go to https://notebooklm.google.com")
        console.print("2. Create a new notebook")
        console.print("3. Upload files from the staging directory:")
        console.print(f"   - Transcript files: {video_id}_transcript_*.txt")
        console.print(f"   - Slide images: {video_id}_slide_*.png")
        console.print(f"   - Companion files: {video_id}_slide_*.txt (optional but recommended)")
        console.print("4. Each file is self-contained with metadata for NotebookLM's RAG")
        console.print("\n[bold]Note:[/bold] Files have been moved from original locations (repo condensed)")


@click.command()
@click.option('--dry-run', '-n', is_flag=True, help='Preview what will be staged without actually staging files')
@click.option('--video', '-v', help='Stage specific video ID (bypasses completion check)')
@click.option('--force', '-f', is_flag=True, help='Force stage even if video is not marked as completed')
def main(dry_run: bool, video: Optional[str], force: bool):
    """Stage completed videos for NotebookLM upload with embedded metadata."""
    ensure_staging_dir()
    
    if video:
        # Stage specific video
        videos_to_stage = [video]
        if not force:
            progress = get_video_progress(video)
            if progress.get('status') != 'completed':
                console.print(f"[yellow]Warning: Video {video} is not marked as completed.[/yellow]")
                console.print(f"[yellow]Status: {progress.get('status', 'unknown')}[/yellow]")
                if not click.confirm("Continue anyway?"):
                    return
    else:
        # Get all completed videos
        completed = get_completed_videos()
        if not completed:
            console.print("[yellow]No completed videos found.[/yellow]")
            console.print("[yellow]Videos are marked as completed when they have been:")
            console.print("  - Reviewed (review_slides.py)")
            console.print("  - Credits added (add_credit_overlay.py)")
            console.print("  - Metadata synced (sync_slide_metadata.py)")
            return
        
        videos_to_stage = completed
    
    if not videos_to_stage:
        console.print("[yellow]No videos to stage.[/yellow]")
        return
    
    # Show what will be staged
    console.print(f"\n[bold]Staging {len(videos_to_stage)} video(s) for NotebookLM upload...[/bold]")
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be staged[/yellow]\n")
    
    # Stage each video
    stats_by_video = {}
    for video_id in videos_to_stage:
        title = get_video_title(video_id)
        console.print(f"[cyan]Processing:[/cyan] {video_id} - {title}")
        stats = stage_video_files(video_id, dry_run=dry_run)
        stats_by_video[video_id] = stats
        
        if stats.get('errors'):
            for error in stats['errors']:
                console.print(f"  [red]Error:[/red] {error}")
    
    # Show summary
    console.print()
    show_staging_summary(videos_to_stage, stats_by_video, dry_run)


if __name__ == '__main__':
    main()
