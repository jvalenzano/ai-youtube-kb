# AI YouTube KB 🔮

**1‑click YouTube playlist → team training library**  
Transcripts + slide extraction + AI curation + NotebookLM/RAG.

[![stars](https://img.shields.io/github/stars/jvalenzano/ai-youtube-kb)](https://github.com/jvalenzano/ai-youtube-kb)
[![license](https://img.shields.io/github/license/jvalenzano/ai-youtube-kb)](LICENSE)

## Why?

Turn any YouTube series into a searchable knowledge base:
- **Searchable KB**: "agent pitfalls" → quotes + charts + timestamps
- **Team NotebookLM**: Collaborative Q&A, audio overviews, shared learning
- **Local CLI RAG**: Query transcripts + slides without internet
- **95% slide accuracy**: CLIP-based detection extracts presentation visuals

**Real impact**: Transformed Scott Hebner's 27‑video AI agents series into a structured training library. Onboarding: 2 weeks → 2 days.

## Attribution & Credits

This tool works with any YouTube playlist. The example content used in this repository comes from:

- **Series**: "The Next Frontiers of AI" by [Scott Hebner](https://www.linkedin.com/in/scotthebner/)
- **Podcast**: [The Next Frontiers of AI](https://thecuberesearch.com/podcasts/the-next-frontiers-of-ai/)
- **Website**: [Hebner Advisories](https://hebneradvisories.ai/)
- **Channel**: [SiliconANGLE theCUBE](https://www.youtube.com/@siliconangle)
- **Playlist**: [AI Agents Series](https://www.youtube.com/playlist?list=PLenh213llmcYQRnnZYJAFCns3BaKkA7dv)

**Fair Use Notice**: This repository provides tools for educational and research purposes. All video content, transcripts, and extracted materials remain the property of their respective creators. This tool:
- Only processes publicly available YouTube transcripts
- Does not redistribute video content
- Provides attribution in all generated outputs
- Is designed for personal/internal team knowledge bases

When using this tool with any YouTube content, please:
1. ✅ Credit original creators in your outputs
2. ✅ Respect YouTube's Terms of Service
3. ✅ Use for educational/internal purposes
4. ✅ Link back to original content

## 1‑Click Install

```bash
git clone https://github.com/jvalenzano/ai-youtube-kb
cd ai-youtube-kb
pip install -r requirements.txt

# Option 1: Use Skill CLI (recommended)
python skills/yt-series-to-team-kb/run_skill.py --playlist YOUR_PLAYLIST_URL

# Option 2: Manual pipeline
python scripts/ingest.py --playlist YOUR_PLAYLIST_URL      # ~5-10 min
python scripts/curate.py --all                            # ~15-30 min
python scripts/extract_slides.py --all                    # ~45-90 min (longest step)
python scripts/review_slides.py --video VIDEO_ID          # Review slides (per video)
python scripts/add_credit_overlay.py --all                # Add credits to all videos
python scripts/finalize_curation.py                       # Final sync & refresh
python scripts/stage_for_notebooklm.py                    # Stage for NotebookLM upload
python query.py --build                                   # ~2-5 min
```

**⏱️ Time Expectations** (for 27-video playlist):
- **Total**: ~1.5-2.5 hours end-to-end (without review/credits)
- **With full curation**: ~2-3 hours (includes review, credits, finalization)
- **Longest step**: Slide extraction (~45-90 min with parallel processing)
- **Can run in background**: Slide extraction can be left running while you do other work
- **Check progress**: Use `python scripts/extract_slides.py --status` anytime

**Full workflow includes** (after initial processing):
- Slide review: ~5-10 min per video (interactive)
- Credit overlay: ~1-2 min per video (automated)
- Finalization: ~2-5 min (all videos)
- Staging: ~1-2 min (all videos)

## Live Demo

**📚 [NotebookLM: AI Agents Learning Guide](https://notebooklm.google.com/notebook/5b8cfe75-fe13-48aa-8022-0ee11e3ea1cc)** - Interactive notebook with 124 sources, featuring AI-generated content including video overviews, podcasts, slide decks, infographics, reports, flashcards, quizzes, and mind maps.  
**Query example**: `python query.py "futures index chart"` → Returns slide image + transcript context

> **Explore the NotebookLM notebook** to see AI-generated content from this knowledge base, including presentations, audio overviews, and visual infographics that synthesize insights from the entire corpus.

## Tech Stack ✨

- **yt-dlp** + **youtube-transcript-api**: Video metadata & transcripts
- **CLIP (transformers)** + **OpenCV**: 95% accurate slide detection
- **Claude API**: Intelligent curation, summaries, topic tagging
- **ChromaDB** + **sentence-transformers**: Local semantic search
- **NotebookLM export**: Team-ready markdown + structured modules

**Performance**: ~1.5-2.5hr processing time per 27-video playlist (with parallel slide extraction). ~14 hours of content → searchable KB.

## Team Impact

- **Onboarding**: 2 weeks → 2 days (structured learning paths)
- **Async learning**: AI-generated podcasts, summaries, key takeaways
- **Production patterns**: FedRAMP-ready architecture, multi-agent workflows

## Roadmap

- [x] Transcript extraction + curation
- [x] CLIP-based slide extraction (95% accuracy)
- [x] Skill CLI for one-command setup
- [x] NotebookLM export + local RAG
- [ ] Multi-platform support (Vimeo, Loom)
- [ ] Auto-deploy via GitHub Actions
- [ ] Web UI for query interface

⭐ **Star if useful** → Fork/PRs welcome!

---

## Technical Guide

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      This Repository                            │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │ ingest.py  │→ │ curate.py  │→ │extract_slides│→ │query.py │  │
│  │            │  │  (Claude)  │  │  (CLIP+OCR)  │  │  (RAG)  │  │
│  └────────────┘  └────────────┘  └──────────────┘  └─────────┘  │
│       ↓               ↓                ↓               ↓        │
│   data/raw/      data/clean/     data/slides/      kb/index     │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │review_slides │→ │add_credits   │→ │stage_for_notebooklm  │   │
│  │(human review)│  │(attribution) │  │(prepare for upload)  │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│         ↓                 ↓                    ↓                │
│   data/slides/      data/slides/    notebooks/notebooklm-staging│
└─────────────────────────────────────────────────────────────────┘
                                        ↓
                       ┌────────────────────────────┐
                       │        NotebookLM          │
                       │  (Team RAG, Audio, Share)  │
                       └────────────────────────────┘
```

### Project Structure

```
yt-agents-kb/
├── data/
│   ├── raw/                 # Raw transcripts (JSON)
│   ├── clean/               # Curated data (JSON)
│   └── slides/              # Extracted slides (PNG + metadata)
├── scripts/
│   ├── ingest.py            # Playlist + transcript extraction
│   ├── curate.py            # Claude summarization + tagging
│   ├── extract_slides.py    # CLIP-based slide detection + OCR
│   ├── review_slides.py     # Human-in-the-loop slide review
│   ├── add_credit_overlay.py # Add attribution to slides
│   ├── sync_slide_metadata.py # Sync metadata with files
│   ├── finalize_curation.py # Final sync & refresh (all videos)
│   ├── stage_for_notebooklm.py # Stage files for NotebookLM upload
│   ├── export_notebooklm.py # NotebookLM artifacts (basic export)
│   └── generate_master_kb.py # Master document
├── skills/
│   └── yt-series-to-team-kb/ # One-command Skill CLI
│       ├── run_skill.py
│       └── Skill.md
├── notebooks/
│   ├── notebooklm-ready/
│   │   ├── videos/          # Per-video .txt files (pre-staging)
│   │   └── modules/         # Module bundles (.md)
│   ├── notebooklm-staging/  # Staged files ready for upload (after finalization)
│   ├── Master_Knowledge_Base.md
│   └── youtube-urls.txt
├── kb/
│   ├── metadata.json
│   ├── modules.yaml
│   ├── chroma_db/           # ChromaDB vector store
│   └── vector_index.pkl     # Semantic search index
├── query.py                 # Local RAG search CLI
└── requirements.txt
```

### CLI Reference

#### Quick Reference: Export vs Staging

**`export_notebooklm.py`** (Basic Export):
- Creates text files in `notebooks/notebooklm-ready/videos/`
- Includes transcripts, summaries, slide OCR text (embedded in transcript)
- **Does NOT include slide images**
- **Does NOT move files** (keeps originals)
- Use for: Quick export, module bundles, YouTube URL lists

**`stage_for_notebooklm.py`** (Complete Staging) ⭐ Recommended:
- **Moves** files to `notebooks/notebooklm-staging/`
- Includes slide images (renamed with video_id)
- Creates companion metadata files for each slide
- Embeds metadata in every file for NotebookLM's RAG
- **Condenses repository** (removes from original locations)
- Use for: Final upload to NotebookLM with complete content

**When to use each**:
- Use `export_notebooklm.py` during development/testing
- Use `stage_for_notebooklm.py` when ready to upload to NotebookLM (after finalization)

#### Skill CLI (Recommended)

```bash
# Interactive mode
python skills/yt-series-to-team-kb/run_skill.py

# Direct mode
python skills/yt-series-to-team-kb/run_skill.py --playlist URL --topics "AI agents, workflows"
```

The Skill CLI automates the entire pipeline:
1. Ingests playlist
2. Curates with Claude
3. Extracts slides (if available)
4. **Human review** (optional): Interactive slide curation
5. Adds credit overlays
6. Exports to NotebookLM
7. Builds search index

**Note**: For final staging (moving files to `notebooklm-staging/`), run `python scripts/stage_for_notebooklm.py` after completing all curation.

**Human-in-the-Loop Feature**: After slide extraction, the Skill offers an interactive review step where you can review each flagged slide and decide: Keep or Remove. This ensures quality while preserving important content.

#### Manual Pipeline

##### ingest.py - Transcript Extraction

```bash
python scripts/ingest.py --playlist URL   # Full playlist
python scripts/ingest.py --video VIDEO_ID # Single video
python scripts/ingest.py --list           # List videos
```

##### curate.py - Claude Analysis

```bash
python scripts/curate.py --video VIDEO_ID  # Single video
python scripts/curate.py --all             # All uncurated
python scripts/curate.py --all --force     # Re-curate all
python scripts/curate.py --status          # Show progress
```

Each curated video includes:
- **Summary**: 5-10 bullet points
- **Key takeaways**: DO/DON'T guidance
- **Topics**: Searchable tags
- **Module**: Learning track assignment
- **Highlights**: Timestamped key moments

##### extract_slides.py - Slide Extraction

```bash
python scripts/extract_slides.py --video VIDEO_ID  # Single video (~5-10 min)
python scripts/extract_slides.py --all             # All videos (parallel)
python scripts/extract_slides.py --all --workers 4 # Custom worker count
python scripts/extract_slides.py --status          # Check progress
python scripts/extract_slides.py --check           # Check dependencies
```

**⚠️ Time Commitment**: Slide extraction is the longest step in the pipeline:
- **Single video**: ~5-10 minutes (download + processing)
- **Full playlist (27 videos)**:
  - Sequential: ~2-3 hours
  - With 4 workers (default): ~45-90 minutes (2.5-3x faster)
  - Adjust with `--workers N` (recommended: 2-8 based on CPU/bandwidth)

**Slide extraction pipeline** (8 stages per video):
1. **Download** video at 720p (~1-3 min per video)
2. **Extract frames** every 2 seconds
3. **Detect scene changes** via histogram comparison
4. **Classify slides** using CLIP (or text-density fallback)
5. **OCR text extraction** with pytesseract
6. **Filter quality** - Remove low-text, filler, and empty slides
7. **Deduplicate** - Remove duplicate slides using perceptual hashing
8. **Align** with transcript timestamps

**Quality Filtering** (automatic):
- **Blurry detection**: Removes blurry images using Laplacian variance (<100 threshold)
- **Low text**: Removes slides with <10 words of OCR text
- **Filler text**: Filters out branding/copyright slides (theCUBE, LinkedIn links, "Thank you", etc.)
- **Empty images**: Removes mostly black/empty images (>85% dark pixels)
- **Duplicates**: Removes duplicate slides using perceptual hashing

**Enhanced Filler Detection** catches:
- Copyright/trademark notices
- Branding slides (theCUBE, SiliconANGLE, website URLs)
- Contact/engagement slides ("Your Views?", LinkedIn links)
- Promotional content (summit announcements)
- End slides ("Thank you", "Q&A")

**Monitoring Progress**:

```bash
# Check overall status
python scripts/extract_slides.py --status

# Shows:
# - Total videos
# - Extracted count
# - Pending count
# - Per-video slide counts
```

**During Batch Processing**:
- Progress bar shows completion count
- Each video processes through 8 stages
- Errors are logged but don't stop the batch
- Completed videos are saved immediately (can check `data/slides/VIDEO_ID/`)

**Tips**:
- Run `--all` in background or terminal you can leave open
- Use `--status` anytime to check progress
- Adjust `--workers` based on your system (more workers = faster but more CPU/bandwidth)
- Failed videos can be re-run individually with `--video VIDEO_ID`

**Dependencies for slides**:
```bash
pip install opencv-python pytesseract Pillow imagehash
pip install transformers torch  # for CLIP
brew install tesseract  # macOS
apt install tesseract-ocr  # Ubuntu
```

##### review_slides.py - Human-in-the-Loop Slide Review ⭐

**Key Feature**: Interactive human curation ensures important content is never accidentally deleted.

```bash
# Interactive review (recommended)
python scripts/review_slides.py --video VIDEO_ID

# Auto-approve all flagged slides (skip review)
python scripts/review_slides.py --video VIDEO_ID --auto-approve

# Custom thresholds
python scripts/review_slides.py --video VIDEO_ID --min-words 15 --blur-threshold 80
```

**How it works**:
1. **AI flags** slides for potential removal (blurry, duplicates, filler text)
2. **Human reviews** each flagged slide one-by-one
3. **Human decides**: Keep (important) or Remove (low-quality)
4. **Updates metadata** and removes approved slides

**Review Interface**:
- Shows slide filename, timestamp, removal reason
- Displays OCR text preview
- **Displays image inline in terminal** (no window switching needed!)
- Asks: "Keep this slide?" (default: Yes - conservative)
- Shows summary before final removal

**Image Display**:
- Uses ASCII art by default (always works, displays inline in terminal)
- For better quality: Install `viu` → `brew install viu`
- Falls back to external viewer if needed
- **No window switching needed** - images appear directly in terminal

**Why Human-in-the-Loop?**
- **Quality assurance**: Human judgment catches edge cases
- **Content preservation**: Important slides aren't lost
- **Flexibility**: Adjust decisions per use case
- **Transparency**: See exactly what's being removed and why

**Example workflow**:
```bash
# 1. Extract slides
python scripts/extract_slides.py --all

# 2. Review flagged slides
python scripts/review_slides.py --video VIDEO_ID

# 3. Review shows:
#    - "Slide 1/5: slide_0m00s_blurry.png [blurry] - Keep? [Y/n]"
#    - "Slide 2/5: slide_46m06s_copyright.png [filler_text] - Keep? [Y/n]"
#    - etc.

# 4. Final confirmation before removal
```

##### sync_slide_metadata.py - Sync Metadata with Files

**Use this when you manually delete slide files** - updates metadata.json to match reality.

```bash
# Preview what needs syncing (dry run)
python scripts/sync_slide_metadata.py --video VIDEO_ID --dry-run

# Sync single video
python scripts/sync_slide_metadata.py --video VIDEO_ID

# Sync all videos
python scripts/sync_slide_metadata.py --all
```

**What it does**:
- Compares metadata.json with actual PNG files on disk
- Removes metadata entries for files that don't exist
- Updates stats (slide counts, etc.)
- Marks metadata as synced

**Use cases**:
- Manually deleted a slide file
- Files moved or renamed outside the tool
- Metadata got out of sync somehow

##### cleanup_slides.py - Batch Cleanup (No Review)

```bash
# Preview what would be removed (dry run)
python scripts/cleanup_slides.py --all --dry-run

# Cleanup all videos (removes low-quality slides without review)
python scripts/cleanup_slides.py --all

# Cleanup single video
python scripts/cleanup_slides.py --video VIDEO_ID

# Custom thresholds
python scripts/cleanup_slides.py --all --min-words 15 --filter-filler
```

**Use cases**:
- Quick cleanup when you trust the filters
- Batch processing many videos
- Preview changes before applying

**Note**: `review_slides.py` is recommended for important content. `cleanup_slides.py` is for automated cleanup.

##### finalize_curation.py - Final Sync & Refresh ⭐

**⚠️ IMPORTANT**: This processes **ALL videos** in your repository, not just one video.

**Run this when you're satisfied with manual slide curation for all videos** - syncs metadata and refreshes all exports.

```bash
# Complete finalization (recommended)
python scripts/finalize_curation.py

# Only sync metadata (skip exports)
python scripts/finalize_curation.py --skip-exports
```

**What it does**:
1. **Syncs metadata** for **all videos** (removes entries for deleted files)
2. **Refreshes NotebookLM exports** (includes updated slide set for all videos)
3. **Updates Master Knowledge Base** (includes final slide counts for all videos)
4. **Rebuilds search index** (includes updated content for all videos)

**When to run**:
- ✅ After manual slide deletions across multiple videos
- ✅ After adding custom slides to multiple videos
- ✅ Before exporting to NotebookLM (finalizes entire repository)
- ✅ Before sharing with team (ensures all exports are current)
- ✅ When satisfied with curation for **all videos**

**For single video**: If you only need to sync metadata for one video, use:
```bash
python scripts/sync_slide_metadata.py --video VIDEO_ID
```

**This is the final step** in the curation workflow for the entire repository.

##### add_credit_overlay.py - Add Credit Attribution ⭐

**Add attribution overlays to existing slides** - ensures proper credit for content creators.

```bash
# Add credits to single video
python scripts/add_credit_overlay.py --video VIDEO_ID

# Add credits to all videos
python scripts/add_credit_overlay.py --all

# Custom credit text
python scripts/add_credit_overlay.py --video VIDEO_ID \
    --credit-text "Scott Hebner • The Next Frontiers of AI"

# Preview without making changes
python scripts/add_credit_overlay.py --video VIDEO_ID --dry-run
```

**What it does**:
- Adds semi-transparent credit bar at bottom of each slide
- Updates metadata to track credit information
- Works with existing slides (retroactive attribution)
- Customizable text, author, and series

**Credit overlay features**:
- **Semi-transparent bar**: Dark bar with white text at bottom
- **Auto-sizing**: Bar height adapts to image size (5% of height, 30-60px)
- **Centered text**: Professional appearance
- **Non-destructive**: Can be re-run if needed

**When to use**:
- ✅ Adding credits to slides extracted without `--add-credit`
- ✅ Updating credit text for existing slides
- ✅ Ensuring proper attribution before sharing

**Example credit text**:
- Default: `"Scott Hebner • The Next Frontiers of AI"`
- Custom: `"Source: YouTube Video"`
- Full: `"Scott Hebner • The Next Frontiers of AI • SiliconANGLE theCUBE"`

##### export_notebooklm.py - Export Artifacts

```bash
python scripts/export_notebooklm.py        # Export curated
python scripts/export_notebooklm.py --raw  # Include raw transcripts
```

**When to use**: Creates text files in `notebooks/notebooklm-ready/` for basic NotebookLM import. For complete content with slides and embedded metadata, use `stage_for_notebooklm.py` instead (recommended after finalization).

##### stage_for_notebooklm.py - Stage Files for NotebookLM Upload ⭐

**Prepare all completed videos for NotebookLM upload** - moves files to a staging directory with embedded metadata.

```bash
# Preview what will be staged (recommended first)
python scripts/stage_for_notebooklm.py --dry-run

# Stage all completed videos
python scripts/stage_for_notebooklm.py

# Stage specific video
python scripts/stage_for_notebooklm.py --video VIDEO_ID
```

**What it does**:
1. **Moves** (not copies) all completed video files to `notebooks/notebooklm-staging/`
2. **Renames slide files** to include video_id: `VIDEO_ID_slide_TIMESTAMP.png`
3. **Creates companion `.txt` files** for each slide with full metadata
4. **Creates/updates transcript files** with slide references
5. **Organizes everything** in a flat directory structure for easy upload

**⚠️ Important**: Files are **moved** (not copied) from original locations. This condenses your repository but removes files from `data/slides/` and `notebooks/notebooklm-ready/`. If you need to keep originals, back them up first.

**Why staging?**
- **Condenses repository**: Moves completed work out of main data directories
- **Embedded metadata**: Each file is self-contained with enough context for NotebookLM's RAG
- **Individual file uploads**: NotebookLM requires individual files (not folders), so each file needs embedded metadata
- **Ready for upload**: All files in one place, properly named and organized

**What gets staged**:
- **Slide images**: `VIDEO_ID_slide_TIMESTAMP.png` (renamed with video context)
- **Companion files**: `VIDEO_ID_slide_TIMESTAMP.txt` (full metadata for each slide)
- **Transcript files**: `VIDEO_ID_transcript_TITLE.txt` (with slide references)

**After staging**:
- Files are moved from original locations (repo condensed)
- All files are in `notebooks/notebooklm-staging/`
- Ready for drag-and-drop upload to NotebookLM

**Video Completion Requirements**:
A video is marked as "completed" when **all three** conditions are met:
1. **Reviewed**: Slides have been reviewed (`review_slides.py`)
2. **Credits Added**: Credit overlays added to slides (`add_credit_overlay.py`)
3. **Metadata Synced**: Metadata synced with actual files (`sync_slide_metadata.py` or `finalize_curation.py`)

Only completed videos will be staged by default. To stage incomplete videos, use `--video VIDEO_ID --force`.

**Handling Missing Transcripts**:
If a video doesn't have a transcript (e.g., YouTube rate limiting), the staging script will:
- Create a transcript file with "Transcript Not Available" notice
- Include all slide OCR text as content
- Explain why transcript is missing
- Still provide valuable content for NotebookLM from slides

##### query.py - Local Semantic Search

```bash
python query.py --build                    # Build search index
python query.py "your question here"       # Search
python query.py --list                     # Show index stats
python query.py -n 10 "question"           # Top 10 results
```

### Modules (Learning Tracks)

Videos are auto-classified into:

| Module | Description |
|--------|-------------|
| **Foundations of AI Agents** | Core concepts, architectures, reasoning |
| **Agentic Workflows & Orchestration** | Multi-agent patterns, pipelines |
| **Tooling & Frameworks** | SDLC, dev tools, platforms |
| **Case Studies & Lessons** | Real deployments, lessons learned |

### NotebookLM Import Guide

#### Recommended: Staged Files (After Finalization)

**After completing slide curation and finalization, stage files for upload:**

```bash
# 1. Finalize all curation (syncs metadata, refreshes exports)
python scripts/finalize_curation.py

# 2. Stage all completed videos for NotebookLM
python scripts/stage_for_notebooklm.py

# 3. Upload from staging directory
```

**Upload to NotebookLM**:
1. Go to https://notebooklm.google.com
2. Create a new notebook
3. Open `notebooks/notebooklm-staging/` directory
4. Upload files individually (NotebookLM doesn't support folder uploads):
   - **Transcript files**: `VIDEO_ID_transcript_*.txt` (one per video)
   - **Slide images**: `VIDEO_ID_slide_*.png` (all slide images)
   - **Companion files**: `VIDEO_ID_slide_*.txt` (optional but recommended - provides full metadata)

**Why staged files?**
- Each file has embedded metadata (video context, timestamps, relationships)
- Files are properly named with video_id for easy identification
- Companion files ensure NotebookLM understands slide-to-video relationships
- Works with NotebookLM's individual file upload requirement

#### Option 1: Drag & Drop Files (Pre-Staging)

1. Open `notebooks/notebooklm-ready/videos/`
2. Select all `.txt` files
3. Drag into NotebookLM notebook

**Note**: This method doesn't include slide images. Use staging method above for complete content.

#### Option 2: YouTube URLs

1. Open `notebooks/youtube-urls.txt`
2. Copy URLs
3. In NotebookLM: Add source → YouTube → Paste URLs

**Note**: This imports directly from YouTube but may not include extracted slides or curated summaries.

#### Option 3: Module Bundles

For structured learning, import module files from `notebooks/notebooklm-ready/modules/`:
- `Foundations_of_AI_Agents.md`
- `Agentic_Workflows_&_Orchestration.md`
- `Case_Studies_&_Lessons.md`

#### Sharing with Team {#notebooklm-sharing}

NotebookLM supports both **private** and **public** sharing:

**Public Sharing (Recommended for demos):**
1. In NotebookLM: Click **Share** button (top-right)
2. Set access to: **"Anyone with the link can view"**
3. Copy the public link and share it
4. Viewers can:
   - Ask questions and interact with the notebook
   - Explore generated content (audio overviews, FAQs, briefing documents)
   - View all source documents and notes
   - **Cannot** edit source material (read-only)

**Private Sharing:**
- Share with specific individuals via email (up to 50 for personal accounts)
- Set permissions: **Viewer** (read-only) or **Editor** (can add/remove sources)
- Enterprise/Education accounts can share with unlimited users within their organization

**Important Notes:**
- Public sharing is available for **personal Google accounts only**
- Workspace/Education accounts can only share within their organization
- All viewers need a Google account to access shared notebooks

**Resources:**
- [NotebookLM Sharing Guide](https://support.google.com/notebooklm/answer/16206563)
- [Public Notebooks Announcement](https://blog.google/technology/google-labs/notebooklm-public-notebooks/)

### Complete Slide Curation Workflow

**Recommended workflow after slide extraction:**

```bash
# 1. Extract slides (automatic filtering happens here)
python scripts/extract_slides.py --all

# 2. Human review (recommended - ensures quality)
python scripts/review_slides.py --video VIDEO_ID_1
python scripts/review_slides.py --video VIDEO_ID_2
# ... review all videos

# 3. Add credit overlays to all videos
python scripts/add_credit_overlay.py --all

# 4. Manual curation (optional - delete/add slides manually)
# Browse data/slides/VIDEO_ID/ and delete unwanted slides
# Add custom slides if needed

# 5. Sync metadata for individual videos (after manual changes)
python scripts/sync_slide_metadata.py --video VIDEO_ID

# 6. Final sync (when satisfied with curation for ALL videos)
python scripts/finalize_curation.py

# 7. Stage files for NotebookLM upload (moves completed videos to staging)
python scripts/stage_for_notebooklm.py
```

**Note**: `finalize_curation.py` processes **all videos** in your repository. Use `sync_slide_metadata.py --video VIDEO_ID` for single-video metadata sync.

**See [SLIDE_CURATION_WORKFLOW.md](docs/SLIDE_CURATION_WORKFLOW.md) for complete workflow details.**

### Adding New Content

```bash
# Add new videos
python scripts/ingest.py --video NEW_VIDEO_ID
python scripts/curate.py --video NEW_VIDEO_ID

# Extract slides with credit overlay (recommended)
python scripts/extract_slides.py --video NEW_VIDEO_ID --add-credit

# Review and curate slides
python scripts/review_slides.py --video NEW_VIDEO_ID

# Add credits if not done during extraction
python scripts/add_credit_overlay.py --video NEW_VIDEO_ID

# Sync metadata for this video
python scripts/sync_slide_metadata.py --video NEW_VIDEO_ID

# Finalize when satisfied with ALL videos (processes entire repository)
python scripts/finalize_curation.py

# Stage for NotebookLM upload (moves completed videos to staging directory)
python scripts/stage_for_notebooklm.py
```

### Troubleshooting

#### YouTube Rate Limiting (429 Error)

Wait 10-15 minutes, then retry with `--transcripts-only`:
```bash
python scripts/ingest.py --playlist URL --transcripts-only
```

#### Missing API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Get key: https://console.anthropic.com/

#### Slow Search Index Build

First build downloads the embedding model (~100MB). Subsequent builds are faster.

#### Slide Extraction Issues

Check dependencies:
```bash
python scripts/extract_slides.py --check
```

Common issues:
- **Tesseract not found**: Install via `brew install tesseract` (macOS) or `apt install tesseract-ocr` (Ubuntu)
- **CLIP model download**: First run downloads ~500MB model. Ensure internet connection.
- **No slides detected**: Video may not contain presentation slides. Check with `--status` to see detection stats.

#### Better Image Display in Review

For better inline image quality during review:
```bash
# Install viu (recommended - best quality)
brew install viu

# Or install chafa (alternative)
brew install chafa
```

Without these, the script uses ASCII art (always works, lower quality).

#### Staging Issues

**Files not staging?**
- Check video completion status: Videos must be reviewed, have credits, and metadata synced
- Use `--dry-run` to preview what will be staged
- Use `--video VIDEO_ID --force` to stage incomplete videos

**Want to keep original files?**
- Staging **moves** files (not copies). Back up `data/slides/` and `notebooks/notebooklm-ready/` first if needed
- After staging, original files are removed from those directories

**Missing transcripts in staging?**
- Some videos may not have transcripts due to YouTube rate limiting or disabled captions
- Staging script creates transcript files with "Transcript Not Available" notice
- Slide OCR text is still included, providing valuable content for NotebookLM

### Current Stats

- **27 videos** curated
- **26 videos** completed (reviewed, credits added, metadata synced)
- **118 slides** extracted across all videos
- **3 learning modules**
- **~14 hours** of content
- **95% slide detection accuracy** (CLIP-based)

### License

MIT
