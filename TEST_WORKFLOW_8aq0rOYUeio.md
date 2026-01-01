# Complete Test Workflow: Video 8aq0rOYUeio

**Video**: "13. Charting the Agentic AI Adoption Curve: What's Next?"  
**Video ID**: `8aq0rOYUeio`  
**Starting State**: 11 slides (after black frame cleanup)

---

## Step-by-Step Commands

### Step 1: Review All Slides (Human Curation)
```bash
cd /Users/jvalenzano/Projects/the-cube/yt-agents-kb
source .venv/bin/activate
python scripts/review_slides.py --video 8aq0rOYUeio --review-all
```

**What to expect:**
- Shows all 11 slides one by one
- Each slide displays inline in terminal (pixelated but visible)
- For each slide, you'll see:
  - Filename, timestamp, reason (or "manual_review")
  - OCR text preview
  - Image display
  - Prompt: "Keep this slide? [y/n] (y):"

**Your actions:**
- Type `y` to keep a slide
- Type `n` to mark for removal
- Review all 11 slides
- At the end, confirm removal of slides you marked `n`

---

### Step 2: Add Credit Overlay (Interactive Prompt)
```bash
python scripts/add_credit_overlay.py --video 8aq0rOYUeio
```

**What to expect:**
- Interactive panel appears with examples
- Prompt: "Enter credit text"
- You type exactly what you want (e.g., "Scott Hebner • The Next Frontiers of AI")
- Preview shown
- Confirmation: "Use this credit text? [Y/n]"
- Credits added to all slides

**Your actions:**
- Type your desired credit text when prompted
- Review the preview
- Confirm with `y` or `Enter`

---

### Step 3: Check for Duplicate Credits (If Needed)
```bash
python scripts/fix_duplicate_credits.py --video 8aq0rOYUeio
```

**What to expect:**
- Script checks all slides for duplicate credit bars
- Reports how many were fixed (if any)
- If credits were added twice, this removes the duplicate

**Note**: Only run this if you suspect duplicate credits (e.g., if you ran add_credit_overlay twice)

---

### Step 4: Sync Metadata (After Manual Changes)
```bash
python scripts/sync_slide_metadata.py --video 8aq0rOYUeio
```

**What to expect:**
- Compares metadata.json with actual PNG files
- Removes metadata entries for deleted files
- Updates slide counts in metadata

**When to run**: After any manual slide deletions or if metadata seems out of sync

---

### Step 5: Finalize Curation (Complete Sync & Refresh) ⚠️
```bash
python scripts/finalize_curation.py
```

**⚠️ IMPORTANT**: This processes **ALL videos** in your repository, not just the current one!

**What to expect:**
- Syncs metadata for **all videos** (removes entries for deleted files)
- Refreshes NotebookLM exports (includes all videos)
- Updates Master Knowledge Base (includes all videos)
- Rebuilds search index (includes all videos)

**When to run**:
- ✅ When you're satisfied with curation for **all videos**
- ✅ Before exporting to NotebookLM
- ✅ Before sharing with team
- ⏸️ **Skip this step** if you only want to finalize one video (you've already synced metadata in Step 4)

**Alternative**: If you only want to sync metadata for all videos without refreshing exports:
```bash
python scripts/finalize_curation.py --skip-exports
```

---

## Quick Reference: Complete Workflow

```bash
# 1. Review all slides
python scripts/review_slides.py --video 8aq0rOYUeio --review-all

# 2. Add credit overlay (interactive)
python scripts/add_credit_overlay.py --video 8aq0rOYUeio

# 3. Fix duplicate credits (if needed)
python scripts/fix_duplicate_credits.py --video 8aq0rOYUeio

# 4. Sync metadata (after manual changes)
python scripts/sync_slide_metadata.py --video 8aq0rOYUeio

# 5. Finalize everything (OPTIONAL - processes ALL videos)
python scripts/finalize_curation.py
```

**Note**: Steps 1-4 complete curation for this single video. Step 5 is optional and processes all videos in the repository.

---

## Expected Results

**After Step 1 (Review):**
- Some slides may be removed (depending on your decisions)
- Metadata updated with review stats
- Final slide count: 7-11 slides (your choice)

**After Step 2 (Credits):**
- All remaining slides have credit overlay at bottom
- Credit text matches what you entered
- Metadata updated with credit info

**After Step 3 (Fix Duplicates):**
- Any duplicate credit bars removed
- Slides have single credit bar (~60px height)

**After Step 4 (Sync):**
- Metadata matches actual files on disk
- Slide counts accurate

**After Step 5 (Finalize):**
- **All videos** metadata synced
- **All videos** exports refreshed
- **All videos** search index updated
- Ready for NotebookLM import

**Note**: Step 5 is optional for single-video testing. You've already completed Steps 1-4 which fully curate this video. Run Step 5 when you're ready to finalize the entire repository.

---

## Notes

- **Virtual environment**: Make sure `.venv` is activated (`source .venv/bin/activate`)
- **Working directory**: Commands assume you're in `yt-agents-kb/` directory
- **Interactive prompts**: Both review and credit overlay will pause for your input
- **Image display**: Slides show inline in terminal (pixelated but functional)

---

**Ready to start?** Begin with Step 1!

