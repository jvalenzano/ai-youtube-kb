# Context Warm-Up Prompt

## Current Situation

You're working on the **credit overlay feature** for the AI YouTube KB project. We're on the `feature/credit-overlay` branch testing the complete workflow.

## What Just Happened

1. ✅ **Fixed ASCII image display bug** in `review_slides.py` - converted `img.getdata()` to list before slicing
2. ✅ **Installed viu** - terminal image viewer for better inline image quality
3. ✅ **Cleared Python cache** - removed `__pycache__` directories
4. ✅ **Added credit overlay** to video `5YrnYJBOpZY` using `add_credit_overlay.py`

## Current State

**Video**: `5YrnYJBOpZY` - "22. The State of Digital Labor Transformation"

**Slides Status**:
- **10 slides remaining** (4 were auto-removed by filters)
- **Credit overlay added** to all 10 slides
- **viu installed** and working

**Current Slides**:
1. `slide_0m04s_eea630b8.png` (intro - should remove)
2. `slide_5m12s_f1c0eeb6.png` (KEEP - content)
3. `slide_7m14s_a552b5ca.png` (KEEP - content)
4. `slide_11m04s_81d0be5e.png` (KEEP - content)
5. `slide_15m20s_b091ad68.png` (KEEP - content)
6. `slide_19m04s_b4b5cb4a.png` (KEEP - content)
7. `slide_27m10s_b0e9bf85.png` (KEEP - content)
8. `slide_31m46s_81d0be5e.png` (KEEP - duplicate but keeping)
9. `slide_33m30s_91b91e6c.png` (contact - should remove)
10. `slide_33m32s_9172d8c9.png` (contact - should remove)

## What User Wants to Do Next

**Test the review script** to verify that:
1. ✅ Images display **inline in terminal** using viu (not popping out in external windows)
2. ✅ All 10 slides can be reviewed with inline image display
3. ✅ The ASCII art fallback works if viu fails

**Command to run**:
```bash
python scripts/review_slides.py --video 5YrnYJBOpZY
```

## Key Files

- **Test Document**: `TEST_BEFORE_5YrnYJBOpZY.md` - Contains before/after comparison
- **Review Script**: `scripts/review_slides.py` - Fixed ASCII display, uses viu/chafa/imgcat/ASCII fallback
- **Credit Overlay Script**: `scripts/add_credit_overlay.py` - Already run, credits added
- **Finalize Script**: `scripts/finalize_curation.py` - To run after manual curation

## Human Observation (Pre-Script)

User wants to **KEEP 7 slides** (slides 2-8 from list above - all content slides) and **REMOVE 3 slides** (slides 1, 9, 10 - intro and contact slides).

## Technical Context

- **viu installed**: `/opt/homebrew/bin/viu` (version 1.6.1)
- **Python**: 3.14.0 in virtual environment `.venv`
- **Fix applied**: `_display_ascii_image()` now converts `img.getdata()` to list before slicing
- **Image display priority**: viu → chafa → imgcat → ASCII art → external viewer

## Expected Behavior

When running `review_slides.py`:
1. Script should detect viu and use it for inline display
2. Images should appear **in the terminal** (not external windows)
3. User can review each flagged slide and decide keep/remove
4. After review, user will manually delete 3 unwanted slides
5. Then run `finalize_curation.py` to sync everything

## Next Steps After Testing

1. Verify inline image display works
2. Review all 10 slides
3. Manually remove 3 unwanted slides
4. Run `finalize_curation.py`
5. Update `TEST_BEFORE_5YrnYJBOpZY.md` with "After" state
6. Compare results with human observation

## Important Notes

- User is in virtual environment: `.venv`
- Working directory: `/Users/jvalenzano/Projects/the-cube/yt-agents-kb`
- Branch: `feature/credit-overlay`
- All fixes are committed and working
- viu is installed and tested

---

**Ready to test**: Run `python scripts/review_slides.py --video 5YrnYJBOpZY` and verify inline image display works for all 10 slides.

