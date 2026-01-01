# YT-Series-to-Team-KB

Transform any YouTube playlist into a structured, searchable team knowledge base.

## Trigger Phrases

- "Turn this YouTube playlist into a team knowledge base: [URL]"
- "Create a knowledge base from this playlist: [URL]"
- "Build a team KB from YouTube: [URL]"

## What This Skill Does

1. **Ingests** all videos from a YouTube playlist
2. **Extracts** transcripts automatically
3. **Curates** with Claude: summaries, key takeaways, topics, module clustering
4. **Extracts slides** from videos (CLIP-based detection, OCR, deduplication)
5. **Human review** (optional): Interactive curation of extracted slides
6. **Exports** NotebookLM-ready files for team collaboration
7. **Builds** local semantic search index
8. **Generates** Master Knowledge Base document

## Key Feature: Human-in-the-Loop Slide Curation

After slide extraction, the workflow includes an **optional human review step**:
- AI flags low-quality slides (blurry, duplicates, filler text)
- Human reviews each flagged slide
- Human decides: Keep (important content) or Remove (low-quality)
- Ensures important content is never accidentally deleted

This human curation step is a **feature, not a bug** - it ensures quality while preserving valuable content.

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| playlist_url | Yes | - | YouTube playlist URL |
| topics | No | "AI agents, workflows" | Focus topics for curation |
| output_formats | No | all | notebooklm, cli, markdown |
| extract_slides | No | true | Extract presentation slides from videos |
| review_slides | No | true | Enable human-in-the-loop slide review |

## Usage Examples

```
User: Turn this YouTube playlist into a team knowledge base:
      https://www.youtube.com/playlist?list=PLxxx

User: Create a knowledge base from this playlist focusing on machine learning:
      https://www.youtube.com/playlist?list=PLyyy
```

## Output

- `notebooks/notebooklm-ready/` - Files for NotebookLM import
- `notebooks/Master_Knowledge_Base.md` - Compiled document
- `query.py` - Local search CLI
- `README.md` - Usage instructions

## Requirements

- Python 3.10+
- Anthropic API key (`ANTHROPIC_API_KEY`)
- Internet access for YouTube

## Limitations

- YouTube may rate-limit transcript extraction (retry with delays)
- Videos without captions will be skipped
- Best with English content
