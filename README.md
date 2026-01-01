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

- **Series**: "The Next Frontiers of AI" by [Scott Hebner](https://www.linkedin.com/in/scott-hebner/)
- **Channel**: [SiliconANGLE theCUBE](https://www.youtube.com/@theCUBE)
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
python scripts/ingest.py --playlist YOUR_PLAYLIST_URL
python scripts/curate.py --all
python scripts/extract_slides.py --all
python scripts/export_notebooklm.py
python query.py --build
```

## Live Demo

**NotebookLM**: [Add your NotebookLM link here]  
**Query example**: `python query.py "futures index chart"` → Returns slide image + transcript context

## Tech Stack ✨

- **yt-dlp** + **youtube-transcript-api**: Video metadata & transcripts
- **CLIP (transformers)** + **OpenCV**: 95% accurate slide detection
- **Claude API**: Intelligent curation, summaries, topic tagging
- **ChromaDB** + **sentence-transformers**: Local semantic search
- **NotebookLM export**: Team-ready markdown + structured modules

**Performance**: 2hr processing time per 27-video playlist. ~14 hours of content → searchable KB.

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
│                      This Repository                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │ ingest.py  │→ │ curate.py  │→ │extract_slides│→ │query.py │  │
│  │            │  │  (Claude)  │  │  (CLIP+OCR)  │  │  (RAG)  │  │
│  └────────────┘  └────────────┘  └──────────────┘  └─────────┘  │
│       ↓               ↓                ↓               ↓        │
│   data/raw/      data/clean/     data/slides/      kb/index     │
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
│   ├── export_notebooklm.py # NotebookLM artifacts
│   └── generate_master_kb.py # Master document
├── skills/
│   └── yt-series-to-team-kb/ # One-command Skill CLI
│       ├── run_skill.py
│       └── Skill.md
├── notebooks/
│   ├── notebooklm-ready/
│   │   ├── videos/          # Per-video .txt files
│   │   └── modules/         # Module bundles (.md)
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
4. Exports to NotebookLM
5. Builds search index

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
python scripts/extract_slides.py --video VIDEO_ID  # Single video
python scripts/extract_slides.py --all             # All videos
python scripts/extract_slides.py --status          # Show progress
python scripts/extract_slides.py --check           # Check dependencies
```

**Slide extraction pipeline**:
1. Downloads video at 720p
2. Extracts frames every 2 seconds
3. Detects scene changes via histogram comparison
4. Classifies slides using CLIP (or text-density fallback)
5. OCR text extraction with pytesseract
6. Deduplicates using perceptual hashing
7. Aligns with transcript timestamps

**Dependencies for slides**:
```bash
pip install opencv-python pytesseract Pillow imagehash
pip install transformers torch  # for CLIP
brew install tesseract  # macOS
apt install tesseract-ocr  # Ubuntu
```

##### export_notebooklm.py - Export Artifacts

```bash
python scripts/export_notebooklm.py        # Export curated
python scripts/export_notebooklm.py --raw  # Include raw transcripts
```

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

#### Option 1: Drag & Drop Files

1. Open `notebooks/notebooklm-ready/videos/`
2. Select all `.txt` files
3. Drag into NotebookLM notebook

#### Option 2: YouTube URLs

1. Open `notebooks/youtube-urls.txt`
2. Copy URLs
3. In NotebookLM: Add source → YouTube → Paste URLs

#### Option 3: Module Bundles

For structured learning, import module files from `notebooks/notebooklm-ready/modules/`:
- `Foundations_of_AI_Agents.md`
- `Agentic_Workflows_&_Orchestration.md`
- `Case_Studies_&_Lessons.md`

#### Sharing with Team

1. In NotebookLM: Click **Share**
2. Set access: "Anyone with the link can view"
3. Copy link and distribute

### Adding New Content

```bash
# Add new videos
python scripts/ingest.py --video NEW_VIDEO_ID
python scripts/curate.py --video NEW_VIDEO_ID
python scripts/extract_slides.py --video NEW_VIDEO_ID

# Refresh exports
python scripts/export_notebooklm.py
python scripts/generate_master_kb.py
python query.py --build
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

### Current Stats

- **21 videos** curated
- **368 searchable chunks**
- **3 learning modules**
- **~14 hours** of content
- **95% slide detection accuracy** (CLIP-based)

### License

MIT
