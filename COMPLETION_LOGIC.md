# Video Completion Logic

## How a Video is Marked as "Complete"

A video is considered **complete** when ALL three of these conditions are met:

1. **Reviewed** (`reviewed = True`)
   - Set when: `review_slides.py` completes and calls `mark_reviewed()`
   - Detected from metadata: `human_reviewed = true` OR `review_stats` exists

2. **Credits Added** (`credits_added = True`)
   - Set when: `add_credit_overlay.py` completes and calls `mark_credits_added()`
   - Detected from metadata: `credit_overlay.added = true`
   - OR detected from images: Credit bar detected at bottom of slides

3. **Metadata Synced** (`metadata_synced = True`)
   - Set when: `sync_slide_metadata.py` completes and calls `mark_metadata_synced()`
   - Detected from metadata: `metadata_synced = true`
   - OR assumed if: `human_reviewed = true` AND `credit_overlay.added = true`

## Where Completion is Checked

### Progress Tracking (`.curation_progress.json`)
- Stores explicit flags: `reviewed`, `credits_added`, `metadata_synced`
- Status is set to `'completed'` when all three are `True`

### Auto-Detection (`get_status_summary()`)
- For videos with no progress tracked or status='pending':
  - Calls `detect_video_state()` to check metadata/images
  - If all three conditions detected, auto-syncs to progress tracking
  - Only works if metadata has the required flags

## Common Issues

### Issue: Video shows as "pending" even though workflow was completed
**Cause**: Metadata is missing completion flags (`human_reviewed`, `credit_overlay.added`, `metadata_synced`)

**Solution**: 
1. Re-run the workflow steps for that video, OR
2. Manually add the flags to metadata.json, OR
3. Run `sync_curation_progress.py --all` to sync from actual state

### Issue: Video has credits in images but not detected
**Cause**: Credit detection only checks first slide - if first slide doesn't have credits, won't be detected

**Solution**: Ensure `credit_overlay.added = true` is set in metadata when credits are added

## Verification

To check if a video is truly complete:
1. Check progress tracking: `get_video_progress(video_id)`
2. Check metadata flags: `human_reviewed`, `credit_overlay.added`, `metadata_synced`
3. Check detected state: `detect_video_state(video_id)`

All three should indicate completion for the video to be marked complete.

