#!/usr/bin/env python3
"""
Curation progress tracking - Track which videos have been reviewed and processed.

Maintains a persistent state file that tracks:
- Which videos have been reviewed
- Which videos have credits added
- Which videos are complete
- Audit log of actions taken
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
PROGRESS_FILE = DATA_SLIDES / ".curation_progress.json"


def load_progress() -> dict:
    """Load progress tracking data."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data: dict):
    """Save progress tracking data."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_video_progress(video_id: str) -> dict:
    """Get progress for a specific video."""
    progress = load_progress()
    return progress.get('videos', {}).get(video_id, {
        'status': 'pending',
        'reviewed': False,
        'credits_added': False,
        'duplicates_fixed': False,
        'metadata_synced': False,
    })


def update_video_progress(video_id: str, **updates):
    """Update progress for a specific video."""
    progress = load_progress()
    
    if 'videos' not in progress:
        progress['videos'] = {}
    
    if video_id not in progress['videos']:
        progress['videos'][video_id] = {
            'status': 'pending',
            'reviewed': False,
            'credits_added': False,
            'duplicates_fixed': False,
            'metadata_synced': False,
        }
    
    # Update fields
    for key, value in updates.items():
        progress['videos'][video_id][key] = value
    
    # Update timestamp
    progress['videos'][video_id]['last_updated'] = datetime.now().isoformat()
    
    # Update status based on progress
    # A video is "completed" if it has been reviewed, has credits, and metadata is synced
    video_progress = progress['videos'][video_id]
    if (video_progress.get('metadata_synced') and 
        video_progress.get('credits_added') and 
        video_progress.get('reviewed')):
        video_progress['status'] = 'completed'
    elif video_progress.get('credits_added'):
        video_progress['status'] = 'credits_added'
    elif video_progress.get('reviewed'):
        video_progress['status'] = 'reviewed'
    else:
        video_progress['status'] = 'pending'
    
    # Add to audit log
    if 'audit_log' not in progress:
        progress['audit_log'] = []
    
    action = updates.get('action', 'updated')
    progress['audit_log'].append({
        'timestamp': datetime.now().isoformat(),
        'video_id': video_id,
        'action': action,
        'updates': updates
    })
    
    # Keep only last 1000 audit log entries
    if len(progress['audit_log']) > 1000:
        progress['audit_log'] = progress['audit_log'][-1000:]
    
    save_progress(progress)


def mark_reviewed(video_id: str, slides_kept: int, slides_removed: int):
    """Mark a video as reviewed."""
    update_video_progress(
        video_id,
        reviewed=True,
        reviewed_date=datetime.now().isoformat(),
        slides_kept=slides_kept,
        slides_removed=slides_removed,
        action='reviewed'
    )


def mark_credits_added(video_id: str, credit_text: str = None):
    """Mark credits as added to a video."""
    updates = {
        'credits_added': True,
        'credits_date': datetime.now().isoformat(),
        'action': 'credits_added'
    }
    if credit_text:
        updates['credit_text'] = credit_text
    update_video_progress(video_id, **updates)


def mark_duplicates_fixed(video_id: str, fixed_count: int):
    """Mark duplicates as fixed for a video."""
    update_video_progress(
        video_id,
        duplicates_fixed=True,
        duplicates_fixed_date=datetime.now().isoformat(),
        duplicates_fixed_count=fixed_count,
        action='duplicates_fixed'
    )


def mark_metadata_synced(video_id: str):
    """Mark metadata as synced for a video."""
    update_video_progress(
        video_id,
        metadata_synced=True,
        metadata_synced_date=datetime.now().isoformat(),
        action='metadata_synced'
    )


def get_all_videos_with_slides() -> list[str]:
    """Get list of all video IDs that have slides."""
    if not DATA_SLIDES.exists():
        return []
    
    return [
        d.name for d in DATA_SLIDES.iterdir()
        if d.is_dir() and list(d.glob("slide_*.png"))
    ]


def detect_video_state(video_id: str) -> dict:
    """
    Detect the actual state of a video by examining metadata and images.
    Returns detected state regardless of progress tracking.
    """
    slide_dir = DATA_SLIDES / video_id
    if not slide_dir.exists():
        return {'error': 'No slides directory'}
    
    metadata_file = slide_dir / "metadata.json"
    state = {
        'has_metadata': False,
        'has_credits_in_metadata': False,
        'has_credits_in_images': False,
        'has_been_reviewed': False,
        'metadata_synced': False,
        'slide_count': 0,
    }
    
    # Check metadata
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            state['has_metadata'] = True
            state['slide_count'] = len(metadata.get('slides', []))
            
            # Check if credits were added (from metadata)
            if metadata.get('credit_overlay', {}).get('added'):
                state['has_credits_in_metadata'] = True
            
            # Check if reviewed (from metadata)
            if metadata.get('human_reviewed') or metadata.get('review_stats'):
                state['has_been_reviewed'] = True
                # Get slide counts from review stats
                review_stats = metadata.get('review_stats', {})
                if review_stats:
                    state['slides_kept'] = review_stats.get('kept_after_review') or review_stats.get('total_reviewed', 0) - review_stats.get('approved_removal', 0)
                    state['slides_removed'] = review_stats.get('approved_removal', 0)
            
            # Check if metadata is synced (explicit flag OR if it has review stats and credits, it's likely synced)
            if metadata.get('metadata_synced'):
                state['metadata_synced'] = True
            elif (metadata.get('human_reviewed') and 
                  metadata.get('credit_overlay', {}).get('added')):
                # If reviewed and has credits, assume metadata is in sync
                state['metadata_synced'] = True
        except Exception:
            pass
    
    # Check if images have credit bars (sample first slide)
    slide_files = list(slide_dir.glob("slide_*.png"))
    if slide_files:
        try:
            from PIL import Image
            import numpy as np
            
            # Check first slide for credit bar
            img = Image.open(slide_files[0])
            width, height = img.size
            
            # Check bottom 100px for dark bar
            check_height = min(100, height // 4)
            bottom_region = img.crop((0, height - check_height, width, height))
            gray = np.array(bottom_region.convert('L'))
            
            # Check if there's a dark bar at the bottom (credit overlay)
            bottom_row = gray[-1, :]
            if np.mean(bottom_row) < 50:  # Dark bar detected
                state['has_credits_in_images'] = True
        except Exception:
            pass
    
    return state


def sync_video_progress_from_state(video_id: str) -> dict:
    """
    Sync progress tracking with actual video state.
    Useful for videos that were processed before progress tracking was added.
    """
    detected_state = detect_video_state(video_id)
    
    if 'error' in detected_state:
        return detected_state
    
    # Determine what to mark based on detected state
    updates = {}
    
    # Mark as reviewed if metadata indicates it
    if detected_state.get('has_been_reviewed'):
        updates['reviewed'] = True
        if not get_video_progress(video_id).get('reviewed_date'):
            updates['reviewed_date'] = datetime.now().isoformat()
    
    # Mark credits as added if detected in metadata or images
    if detected_state.get('has_credits_in_metadata') or detected_state.get('has_credits_in_images'):
        updates['credits_added'] = True
        if not get_video_progress(video_id).get('credits_date'):
            updates['credits_date'] = datetime.now().isoformat()
    
    # Mark metadata as synced if detected
    if detected_state.get('metadata_synced'):
        updates['metadata_synced'] = True
        if not get_video_progress(video_id).get('metadata_synced_date'):
            updates['metadata_synced_date'] = datetime.now().isoformat()
    
    # Update slide counts if available
    if detected_state.get('slide_count'):
        current_progress = get_video_progress(video_id)
        if not current_progress.get('slides_kept'):
            updates['slides_kept'] = detected_state['slide_count']
    
    if updates:
        updates['action'] = 'synced_from_state'
        update_video_progress(video_id, **updates)
    
    return {
        'video_id': video_id,
        'detected_state': detected_state,
        'updates_applied': updates
    }


def get_status_summary() -> dict:
    """Get summary of curation status."""
    progress = load_progress()
    all_videos = get_all_videos_with_slides()
    video_progress = progress.get('videos', {})
    
    summary = {
        'total_videos': len(all_videos),
        'pending': [],
        'reviewed': [],
        'credits_added': [],
        'completed': [],
        'videos': {}
    }
    
    for video_id in all_videos:
        vid_progress = video_progress.get(video_id, {})
        
        # If no progress tracked, try to detect from actual state
        if not vid_progress or vid_progress.get('status') == 'pending':
            detected = detect_video_state(video_id)
            # If video appears completed, sync it
            if (detected.get('has_been_reviewed') and 
                (detected.get('has_credits_in_metadata') or detected.get('has_credits_in_images')) and
                detected.get('metadata_synced')):
                sync_video_progress_from_state(video_id)
                vid_progress = get_video_progress(video_id)
        
        status = vid_progress.get('status', 'pending')
        
        summary['videos'][video_id] = {
            'status': status,
            'reviewed': vid_progress.get('reviewed', False),
            'credits_added': vid_progress.get('credits_added', False),
            'duplicates_fixed': vid_progress.get('duplicates_fixed', False),
            'metadata_synced': vid_progress.get('metadata_synced', False),
            'slides_kept': vid_progress.get('slides_kept'),
            'slides_removed': vid_progress.get('slides_removed'),
            'last_updated': vid_progress.get('last_updated'),
        }
        
        if status == 'completed':
            summary['completed'].append(video_id)
        elif status == 'credits_added':
            summary['credits_added'].append(video_id)
        elif status == 'reviewed':
            summary['reviewed'].append(video_id)
        else:
            summary['pending'].append(video_id)
    
    return summary

