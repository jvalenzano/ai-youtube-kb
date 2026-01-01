# Complete Slide Curation Workflow

## Overview

This document outlines the complete workflow for slide curation, including manual deletion/addition and final synchronization.

## Workflow Stages

### Stage 1: Initial Extraction (Automatic)

```bash
# Extract slides for all videos
python scripts/extract_slides.py --all
```

**What happens:**
- Downloads videos
- Extracts frames
- Detects and classifies slides
- **Automatic filtering**: Removes blurry, low-text, filler slides
- **Automatic deduplication**: Removes duplicate slides
- Saves slides + metadata

**Time**: ~45-90 minutes for 27 videos (with 4 workers)

---

### Stage 2: Optional Quick Cleanup (Automated, No Review)

**When to use**: You trust the filters and want to remove obvious low-quality slides quickly.

```bash
# Preview what would be removed
python scripts/cleanup_slides.py --all --dry-run

# Actually cleanup (no human review)
python scripts/cleanup_slides.py --all
```

**What it does:**
- Applies quality filters
- Removes flagged slides automatically
- Updates metadata

**Skip this** if you want human review (recommended for important content).

---

### Stage 3: Human Review (Recommended) ⭐

**When to use**: You want to ensure important content isn't lost.

```bash
# Review all videos interactively
python scripts/review_slides.py --video VIDEO_ID

# Or review each video individually
for video in $(python scripts/extract_slides.py --status | grep "Video ID" | awk '{print $3}'); do
    python scripts/review_slides.py --video $video
done
```

**What happens:**
- Shows each flagged slide
- Opens image for visual review
- You decide: Keep or Remove
- Removes approved slides
- **Auto-syncs metadata** after removal

**This is the recommended step** - ensures quality while preserving important content.

---

### Stage 4: Manual Curation (Your Control)

**After review, you may want to manually:**
- Delete additional slides (browse `data/slides/VIDEO_ID/` and delete PNGs)
- Add custom slides (place PNGs in the directory)
- Rename or organize slides

**This is expected and supported!** The workflow accommodates manual curation.

---

### Stage 5: Final Sync & Refresh (When Satisfied) ⭐

**Run this when you're done with all manual curation:**

```bash
# Complete finalization (syncs metadata + refreshes all exports)
python scripts/finalize_curation.py

# Or just sync metadata (if exports are fine)
python scripts/finalize_curation.py --skip-exports
```

**What it does:**
1. **Syncs metadata** with actual files (removes entries for deleted files)
2. **Refreshes NotebookLM exports** (includes updated slide set)
3. **Updates Master Knowledge Base** (includes final slide counts)
4. **Rebuilds search index** (includes updated content)

**This is the final step** - run when you're satisfied with your curation.

---

## Complete Workflow Example

```bash
# 1. Extract slides (automatic filtering)
python scripts/extract_slides.py --all

# 2. Human review (recommended)
python scripts/review_slides.py --video VIDEO_ID_1
python scripts/review_slides.py --video VIDEO_ID_2
# ... review all videos

# 3. Manual curation (optional)
# - Browse data/slides/VIDEO_ID/
# - Delete unwanted slides manually
# - Add custom slides if needed

# 4. Final sync (when satisfied)
python scripts/finalize_curation.py
```

## Workflow Decision Tree

```
Extract Slides
    ↓
    ├─→ Trust filters completely?
    │   └─→ cleanup_slides.py --all (skip to Stage 5)
    │
    └─→ Want human review? (Recommended)
        └─→ review_slides.py --video VIDEO_ID
            ↓
        Manual curation needed?
            └─→ Delete/add slides manually
                ↓
        Satisfied with curation?
            └─→ finalize_curation.py
```

## Key Points

### ✅ What's Automatic
- Quality filtering during extraction
- Metadata updates during review
- Auto-sync after review removals

### ✅ What's Manual (Supported)
- Manual file deletion
- Adding custom slides
- Final sync when satisfied

### ✅ When to Run Final Sync
- After manual deletions
- After adding custom slides
- Before exporting to NotebookLM
- Before sharing with team

## Metadata Sync Scenarios

### Scenario 1: Manual Deletion
```bash
# You deleted slide_10m44s_xxx.png manually
python scripts/sync_slide_metadata.py --video VIDEO_ID
# Removes entry from metadata.json
```

### Scenario 2: Added Custom Slide
```bash
# You added custom_slide.png manually
# Note: Custom slides won't be in metadata automatically
# They'll be included in exports but won't have OCR/metadata
# Consider re-running extract_slides for that video if you want full metadata
```

### Scenario 3: Multiple Manual Changes
```bash
# After all manual changes, finalize everything
python scripts/finalize_curation.py
# Syncs all videos + refreshes exports
```

## Integration with Skill CLI

The Skill CLI workflow:

1. Extract slides → Automatic filtering
2. Offers human review → Interactive curation
3. **Pauses for manual curation** → You can delete/add slides
4. **Final sync step** → Run `finalize_curation.py` when ready
5. Exports → Uses final curated slide set

## Best Practices

1. **Extract first**: Let automatic filtering do initial cleanup
2. **Review second**: Human review catches edge cases
3. **Manual curation**: Fine-tune as needed
4. **Final sync**: Always run before exports/sharing
5. **Re-sync anytime**: If you make more manual changes

## Troubleshooting

**Metadata out of sync?**
```bash
python scripts/sync_slide_metadata.py --all
```

**Exports missing slides?**
```bash
python scripts/finalize_curation.py
```

**Want to start over?**
```bash
python scripts/extract_slides.py --video VIDEO_ID --force
```

