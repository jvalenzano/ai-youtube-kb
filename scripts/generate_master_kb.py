#!/usr/bin/env python3
"""
Generate a Master Knowledge Base document compiling all modules.
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
KB_DIR = PROJECT_ROOT / "kb"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

MODULES = {
    "foundations": {
        "name": "Foundations of AI Agents",
        "description": "Core concepts, architectures, and fundamental principles of AI agents",
        "order": 1,
    },
    "workflows": {
        "name": "Agentic Workflows & Orchestration",
        "description": "Patterns for multi-agent systems, orchestration, and workflow design",
        "order": 2,
    },
    "tooling": {
        "name": "Tooling & Frameworks",
        "description": "AI engineering tools, frameworks, and development practices",
        "order": 3,
    },
    "case_studies": {
        "name": "Case Studies & Lessons",
        "description": "Real-world applications, lessons learned, and anti-patterns",
        "order": 4,
    },
}


def load_all_curated():
    """Load all curated video data."""
    videos = []
    for f in DATA_CLEAN.glob("*.json"):
        with open(f) as fp:
            videos.append(json.load(fp))
    return videos


def load_slides_for_video(video_id: str) -> list:
    """Load extracted slides for a video if available."""
    slide_meta = DATA_SLIDES / video_id / "metadata.json"
    if not slide_meta.exists():
        return []

    with open(slide_meta) as f:
        data = json.load(f)

    # Return only unique slides (not duplicates)
    slides = []
    for slide in data.get('slides', []):
        if slide.get('is_duplicate_of') is None:
            slides.append({
                'timestamp': slide.get('timestamp_formatted', ''),
                'timestamp_url': slide.get('timestamp_url', ''),
                'ocr_text': slide.get('ocr_text', ''),
                'filename': slide.get('filename', ''),
            })
    return slides


def generate_master_kb():
    """Generate the master knowledge base document."""
    videos = load_all_curated()

    # Group by module
    by_module = {}
    for v in videos:
        module = v.get('module', 'case_studies')
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(v)

    # Sort videos within each module by title
    for module in by_module:
        by_module[module].sort(key=lambda x: x.get('title', ''))

    content = []

    # Header
    content.append("# AI Agents Knowledge Base")
    content.append("")
    content.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    content.append("")
    content.append("A curated knowledge base from **The Next Frontiers of AI** podcast, covering agentic AI, workflows, architectures, and real-world lessons.")
    content.append("")

    # Stats
    total_videos = len(videos)
    total_duration = sum(v.get('duration', 0) for v in videos)
    hours = total_duration // 3600
    mins = (total_duration % 3600) // 60
    content.append(f"**{total_videos} videos** | **{hours}h {mins}m** of content | **{len(by_module)} learning tracks**")
    content.append("")

    # Table of Contents
    content.append("---")
    content.append("")
    content.append("## Table of Contents")
    content.append("")

    for module_key in sorted(MODULES.keys(), key=lambda x: MODULES[x]['order']):
        module_info = MODULES[module_key]
        video_count = len(by_module.get(module_key, []))
        anchor = module_info['name'].lower().replace(' ', '-').replace('&', '')
        content.append(f"- [{module_info['name']}](#{anchor}) ({video_count} videos)")

    content.append("- [Quick Reference](#quick-reference)")
    content.append("- [Key Takeaways](#key-takeaways)")
    content.append("")

    # Modules
    content.append("---")
    content.append("")

    for module_key in sorted(MODULES.keys(), key=lambda x: MODULES[x]['order']):
        module_info = MODULES[module_key]
        module_videos = by_module.get(module_key, [])

        content.append(f"## {module_info['name']}")
        content.append("")
        content.append(f"*{module_info['description']}*")
        content.append("")

        for i, video in enumerate(module_videos, 1):
            title = video.get('title', 'Unknown')
            url = video.get('url', '')
            duration = video.get('duration_formatted', '')
            video_id = video.get('video_id', '')

            content.append(f"### {i}. [{title}]({url})")
            content.append(f"*Duration: {duration}*")
            content.append("")

            # One-liner
            if video.get('one_liner'):
                content.append(f"> {video.get('one_liner')}")
                content.append("")

            # Summary
            content.append("**Summary:**")
            for bullet in video.get('summary', [])[:5]:
                content.append(f"- {bullet}")
            content.append("")

            # Key takeaways
            takeaways = video.get('key_takeaways', [])
            if takeaways:
                content.append("**Key Actions:**")
                for t in takeaways[:3]:
                    prefix = "✅" if t.get('type') == 'do' else "❌"
                    content.append(f"- {prefix} {t.get('text', '')}")
                content.append("")

            # Topics
            topics = video.get('topics', [])
            if topics:
                content.append(f"**Topics:** {', '.join(topics)}")
                content.append("")

            # Slides
            slides = load_slides_for_video(video_id)
            if slides:
                content.append(f"**Slides ({len(slides)}):**")
                for slide in slides[:5]:  # Show first 5 slides
                    ts = slide.get('timestamp', '')
                    ts_url = slide.get('timestamp_url', '')
                    ocr = slide.get('ocr_text', '')
                    # Truncate OCR text for readability
                    ocr_preview = ocr[:150].replace('\n', ' ') + "..." if len(ocr) > 150 else ocr.replace('\n', ' ')
                    content.append(f"- [{ts}]({ts_url}): {ocr_preview}")
                if len(slides) > 5:
                    content.append(f"- *...and {len(slides) - 5} more slides*")
                content.append("")

            content.append("---")
            content.append("")

    # Quick Reference - All Topics
    content.append("## Quick Reference")
    content.append("")
    content.append("### All Topics")
    content.append("")

    all_topics = {}
    for v in videos:
        for topic in v.get('topics', []):
            topic_lower = topic.lower()
            if topic_lower not in all_topics:
                all_topics[topic_lower] = []
            all_topics[topic_lower].append(v.get('title', ''))

    for topic in sorted(all_topics.keys()):
        video_titles = all_topics[topic]
        content.append(f"- **{topic}**: {len(video_titles)} video(s)")

    content.append("")

    # Key Takeaways - Aggregated
    content.append("## Key Takeaways")
    content.append("")
    content.append("### Do's")
    content.append("")

    dos = []
    donts = []
    for v in videos:
        for t in v.get('key_takeaways', []):
            if t.get('type') == 'do':
                dos.append(t.get('text', ''))
            else:
                donts.append(t.get('text', ''))

    for do in dos[:15]:  # Top 15
        content.append(f"- ✅ {do}")

    content.append("")
    content.append("### Don'ts")
    content.append("")

    for dont in donts[:15]:  # Top 15
        content.append(f"- ❌ {dont}")

    content.append("")
    content.append("---")
    content.append("")
    content.append("*This knowledge base was auto-generated from video transcripts using Claude. Import into [NotebookLM](https://notebooklm.google.com) for interactive Q&A.*")

    # Write to file
    output_file = NOTEBOOKS_DIR / "Master_Knowledge_Base.md"
    with open(output_file, 'w') as f:
        f.write('\n'.join(content))

    print(f"Generated: {output_file}")
    print(f"  {total_videos} videos across {len(by_module)} modules")


if __name__ == '__main__':
    generate_master_kb()
