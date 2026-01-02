# Slide PDFs

This folder contains PDFs created by combining slide images, one PDF per video.

## Purpose

Instead of uploading 119 individual PNG images (119 sources), we combine them into PDFs:
- **Before**: 119 individual images = 119 sources
- **After**: ~27 PDFs (one per video) = 27 sources
- **Savings**: 92 fewer sources!

## How to Create PDFs

Run the combination script:

```bash
cd /Users/jvalenzano/Projects/the-cube/yt-agents-kb
python3 scripts/combine_slides_to_pdfs.py
```

**Requirements:**
- Pillow (PIL) library: `pip install Pillow`

## Upload to NotebookLM

1. Upload PDFs from this folder instead of individual PNGs
2. Each PDF contains all slides for one video
3. NotebookLM can extract and understand images from PDFs
4. Much more efficient for source limits!

## File Naming

PDFs are named: `VIDEO_ID_slides.pdf`

Example:
- `5YrnYJBOpZY_slides.pdf` - Contains all slides from video 5YrnYJBOpZY
- `cg9q5wnssH0_slides.pdf` - Contains all slides from video cg9q5wnssH0

## Notes

- PDFs maintain image quality
- Slides are ordered by timestamp
- Original PNG files remain in `03_Slide_Images/` (not deleted)

