# Human-in-the-Loop Slide Review - Walkthrough

## Overview

The **Human-in-the-Loop Review** is a key feature that ensures important content is never accidentally deleted. After AI filters flag low-quality slides, you review each one and decide: Keep or Remove.

## Why Human-in-the-Loop?

- ✅ **Quality Assurance**: Human judgment catches edge cases AI might miss
- ✅ **Content Preservation**: Important slides aren't lost to over-aggressive filtering
- ✅ **Flexibility**: Adjust decisions based on your specific use case
- ✅ **Transparency**: See exactly what's being removed and why

## Quick Start

### Test on Your Video (5qhDifJM8M8)

```bash
cd /Users/jvalenzano/Projects/the-cube/yt-agents-kb
source .venv/bin/activate

# Run interactive review
python scripts/review_slides.py --video 5qhDifJM8M8
```

## What You'll See

### 1. Initial Summary
```
Slide Review for 5qhDifJM8M8
Total slides: 13
Passed filters: 8
Flagged for review: 5
```

### 2. Review Each Slide

For each flagged slide, you'll see:

```
Slide 1/5

┌─────────────────────────────────────┐
│ Property    │ Value                 │
├─────────────┼───────────────────────┤
│ Filename    │ slide_0m00s_c7e9381d.png │
│ Timestamp   │ 0m00s                 │
│ Reason      │ blurry                │
│ OCR Text    │ (no text)             │
└─────────────────────────────────────┘

Opened image in default viewer

Keep this slide? [Y/n]:
```

**Your options:**
- **Y (Enter)**: Keep the slide (default - conservative)
- **n**: Mark for removal

### 3. Final Summary

After reviewing all slides:

```
Review Summary:
  Total slides: 13
  Passed filters: 8
  Reviewed: 5
  Kept after review: 2
  Approved for removal: 3
  Final count: 10 slides

Slides to be removed:
┌──────────────────────────┬───────────┬──────────────┐
│ Filename                 │ Timestamp │ Reason       │
├──────────────────────────┼───────────┼──────────────┤
│ slide_0m00s_c7e9381d.png │ 0m00s     │ blurry       │
│ slide_46m06s_c03fc03f.png│ 46m06s    │ filler_text  │
│ slide_10m44s_95726be4.png│ 10m44s    │ duplicate    │
└──────────────────────────┴───────────┴──────────────┘

Remove 3 approved slides? [Y/n]:
```

### 4. Confirmation

- **Y**: Remove approved slides and update metadata
- **n**: Cancel (no changes made)

## Expected Results for 5qhDifJM8M8

Based on your feedback, these slides should be flagged:

| Slide | Reason | Expected Action |
|-------|--------|-----------------|
| `slide_0m00s_c7e9381d.png` | blurry | Remove |
| `slide_10m44s_95726be4.png` | duplicate | Remove |
| `slide_43m16s_d014ef6b.png` | filler_text | Remove (branding) |
| `slide_45m12s_8c73b38d.png` | filler_text | Remove (branding) |
| `slide_45m50s_e1741f87.png` | filler_text | Remove (promotional) |
| `slide_46m06s_c03fc03f.png` | filler_text | Remove (copyright) |

## Integration with Skill CLI

When using the Skill CLI, the review step is offered automatically:

```bash
python skills/yt-series-to-team-kb/run_skill.py --playlist URL
```

After slide extraction completes:
- Skill asks: "Review slides now? (Recommended)"
- If Yes: Runs `review_slides.py` for each video
- If No: You can review later manually

## Manual Review Workflow

```bash
# 1. Extract slides (if not done)
python scripts/extract_slides.py --video 5qhDifJM8M8

# 2. Review flagged slides
python scripts/review_slides.py --video 5qhDifJM8M8

# 3. Review other videos
python scripts/review_slides.py --video VIDEO_ID_2
```

## Auto-Approve Mode

If you trust the filters completely:

```bash
python scripts/review_slides.py --video 5qhDifJM8M8 --auto-approve
```

This skips the interactive review and removes all flagged slides automatically.

## Custom Thresholds

Adjust filtering sensitivity:

```bash
# Stricter (removes more)
python scripts/review_slides.py --video 5qhDifJM8M8 --min-words 15 --blur-threshold 120

# More lenient (removes less)
python scripts/review_slides.py --video 5qhDifJM8M8 --min-words 5 --blur-threshold 80
```

## What Gets Updated

After review:
- ✅ Slide files removed from `data/slides/VIDEO_ID/`
- ✅ Metadata updated in `data/slides/VIDEO_ID/metadata.json`
- ✅ Review stats saved (how many reviewed, kept, removed)
- ✅ Export scripts will use cleaned slide set

## Tips

1. **Default is conservative**: "Keep?" defaults to Yes - you have to explicitly reject
2. **Image opens automatically**: On macOS, images open in Preview for easy viewing
3. **OCR preview helps**: Even if image is blurry, OCR text can help decide
4. **Review in batches**: Review a few videos, then continue with others
5. **Can re-run**: If you make a mistake, re-extract and review again

## Troubleshooting

**Image doesn't open?**
- macOS: Should work automatically
- Linux: May need to set `DISPLAY` or use `--auto-approve` mode

**Too many slides flagged?**
- Adjust thresholds: `--min-words 5` (more lenient)
- Or keep more slides during review (default is conservative)

**Want to review later?**
- Run extraction now: `python scripts/extract_slides.py --all`
- Review later: `python scripts/review_slides.py --video VIDEO_ID`

