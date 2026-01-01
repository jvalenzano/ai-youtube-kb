# Complete Slide Curation Workflow - Summary

## The Problem You Identified

After slide extraction, you need:
1. ✅ Clean up low-quality slides
2. ✅ Human review to catch edge cases
3. ✅ Manual curation (delete/add slides)
4. ✅ Final sync when satisfied

## The Solution: 5-Stage Workflow

### Stage 1: Extract (Automatic)
```bash
python scripts/extract_slides.py --all
```
- Automatic filtering removes obvious low-quality slides
- Duplicates removed automatically
- ~45-90 minutes for full playlist

### Stage 2: Optional Quick Cleanup
```bash
# Skip if doing human review (recommended)
python scripts/cleanup_slides.py --all
```
- Only if you trust filters completely
- **Skip this** if doing human review (recommended)

### Stage 3: Human Review (Recommended) ⭐
```bash
python scripts/review_slides.py --video VIDEO_ID
```
- Review each flagged slide
- Decide: Keep or Remove
- Auto-syncs metadata after removal

### Stage 4: Manual Curation (Your Control)
- Browse `data/slides/VIDEO_ID/`
- Delete unwanted slides manually
- Add custom slides if needed
- **This is expected and supported!**

### Stage 5: Final Sync (When Satisfied) ⭐
```bash
python scripts/finalize_curation.py
```
- Syncs all metadata with files
- Refreshes NotebookLM exports
- Updates Master Knowledge Base
- Rebuilds search index

## Answer to Your Questions

### Q: Do we clean first, then review?
**A: No - the workflow is:**
1. Extract (automatic filtering happens)
2. Review (human catches edge cases)
3. Manual curation (your control)
4. Final sync (when satisfied)

**Why**: Human review is more valuable after automatic filtering - you only review what the AI flagged, not everything.

### Q: What if I manually delete/add slides?
**A: Fully supported!**
- Delete slides → Run `sync_slide_metadata.py` or `finalize_curation.py`
- Add slides → They'll be included in exports (may not have metadata)
- Final sync → Handles everything when you're satisfied

### Q: How do I re-run metadata sync?
**A: Use `finalize_curation.py`**
- Syncs all videos at once
- Refreshes all exports
- One command when satisfied

## Recommended Workflow

```bash
# 1. Extract (automatic filtering)
python scripts/extract_slides.py --all

# 2. Review (human-in-the-loop)
for video in $(python scripts/extract_slides.py --status | grep "Video ID"); do
    python scripts/review_slides.py --video $video
done

# 3. Manual curation (browse and delete/add as needed)
# Open data/slides/VIDEO_ID/ in Finder/Explorer
# Delete unwanted slides
# Add custom slides

# 4. Final sync (when satisfied)
python scripts/finalize_curation.py
```

## Integration with Skill CLI

The Skill CLI now:
1. Extracts slides
2. Offers human review
3. **Pauses for manual curation** (reminds you)
4. **Suggests finalize_curation.py** when ready
5. Continues with exports

## Key Features

✅ **Automatic filtering** during extraction  
✅ **Human review** for edge cases  
✅ **Manual curation** fully supported  
✅ **Final sync** handles everything  
✅ **Re-sync anytime** if you make more changes  

## Quick Reference

| Task | Command |
|------|---------|
| Extract slides | `python scripts/extract_slides.py --all` |
| Review slides | `python scripts/review_slides.py --video VIDEO_ID` |
| Sync metadata | `python scripts/sync_slide_metadata.py --all` |
| Finalize everything | `python scripts/finalize_curation.py` |

