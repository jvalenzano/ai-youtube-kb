# NotebookLM Upload Guide

Files are organized in numbered folders for sequential upload.

## 🎯 Access the Completed Notebook

**📚 [Open NotebookLM: AI Agents Learning Guide](https://notebooklm.google.com/notebook/5b8cfe75-fe13-48aa-8022-0ee11e3ea1cc)**

This interactive NotebookLM notebook transforms 27 curated YouTube videos (14+ hours of content) into a comprehensive, searchable learning resource. The notebook contains **124 sources** including transcripts, slide images, and metadata, all processed and enriched with AI-generated content.

**What makes this notebook special:**
- **Complete Knowledge Base**: 27 video transcripts + 119 extracted slides + comprehensive metadata
- **AI-Generated Content**: NotebookLM automatically creates videos, podcasts, presentations, infographics, and study materials
- **Interactive Learning**: Ask questions, explore concepts, and get cited answers from the entire corpus
- **Multiple Learning Formats**: Content available as videos, audio, slides, infographics, flashcards, quizzes, and more
- **Real-World Insights**: Covers practical topics like agentic workflows, organizational challenges, and implementation strategies

The notebook has been enriched with multiple generated content formats to enhance learning and exploration:

### 📹 Generated Content Available

This notebook showcases NotebookLM's powerful content generation capabilities, automatically creating multiple formats from the 124-source knowledge base:

**Multimedia Content:**
- **Video Overviews** - Visual summaries of key topics (e.g., "The Agentic Revolution") that synthesize complex concepts into engaging video presentations
- **Audio Overviews & Podcasts** - Audio content for on-the-go learning (e.g., "Why AI Execution Scores Plummet to 1.8") - perfect for listening during commutes or workouts
- **Slide Decks** - Presentation-ready slide decks synthesized from the entire corpus, ready for team meetings or training sessions

**Visual Content:**
- **Infographics** - Visual representations of complex concepts that make data and insights easily digestible (see example below)
- **Mind Maps** - Visual knowledge maps showing relationships between concepts, helping understand the interconnected nature of AI agent topics

**Learning Materials:**
- **Flashcards** - Study aids for key concepts and terminology, perfect for quick review and knowledge retention
- **Quizzes** - Interactive assessments to test understanding and reinforce learning
- **Reports** - Comprehensive written reports and analyses (e.g., "The Architect's Roadmap to Agentic AI Transformation") that provide deep insights into specific topics
- **Data Tables** - Structured data extracted from sources, making it easy to compare and analyze information

### 📊 Example: Generated Infographic

One example of the rich content generated from this knowledge base is "The AI Reality Gap: Bridging Enterprise Aspiration and Execution":

![The AI Reality Gap: Bridging Enterprise Aspiration and Execution](../docs/AI-Reality-Gap.png)

This infographic visualizes the disconnect between enterprise AI vision (4.1) and execution reality (1.8), highlighting key challenges like trust deficits and siloed implementation, while offering three strategic approaches to bridge the gap: starting small, running in parallel, and focusing on augmentation.

All content is dynamically generated from the 124-source knowledge base, ensuring comprehensive coverage of topics including:
- The transition from generative AI to agentic AI
- Organizational challenges and execution gaps in AI adoption
- Causal AI and reasoning-based agents
- Business-IT collaboration strategies
- Domain-specific AI implementations
- The future of AI assistants and brand discovery
- Workforce transformation through digital labor

---

## 📁 Folder Structure

- **00_Backups/** - Backup transcript files (DO NOT UPLOAD - for reference only)
- **01_Master_Knowledge_Base/** - Upload Master Knowledge Base first
- **02_Transcripts/** - Upload all transcript files (27 files)
- **03_Slide_Images/** - Individual slide images (119 files) - **NOT RECOMMENDED** (hits 50 source limit)
- **04_Companion_Files/** - Companion metadata files (119 files, optional)
- **05_Retry/** - Failed images for retry (23 files)
- **06_Slide_PDFs/** - Combined slide PDFs (one per video) - **RECOMMENDED** ✅

## 📁 Upload Order (Recommended)

1. **01_Master_Knowledge_Base/** - Upload Master Knowledge Base first
2. **02_Transcripts/** - Upload all transcript files (27 files)
3. **06_Slide_PDFs/** - Upload slide PDFs (one per video, ~27 PDFs) ✅ **RECOMMENDED**
4. **04_Companion_Files/** - Upload companion metadata files (optional)

**Note:** 
- Skip `00_Backups/` - backup files not needed
- Skip `03_Slide_Images/` - use `06_Slide_PDFs/` instead (avoids 50 source limit)
- Skip `05_Retry/` - only if retrying failed individual images

## 🚀 Quick Start

### 1. Create Notebook
- Go to [notebooklm.google.com](https://notebooklm.google.com)
- Sign in with **personal Google account** (required for public sharing)
- Click "New Notebook" → Name: "AI Agents: Complete Learning Guide"
- Select "Learning Notebook" type

### 2. Create Slide PDFs (IMPORTANT!)
**Before uploading**, combine images into PDFs to avoid 50 source limit:

```bash
cd /Users/jvalenzano/Projects/the-cube/yt-agents-kb
python3 scripts/combine_slides_to_pdfs.py
```

**Requirements:** `pip install Pillow` (if not already installed)

This creates PDFs in `06_Slide_PDFs/` (one PDF per video, ~27 PDFs instead of 119 images)

### 3. Upload in Order
- Upload folder **01** → Wait for processing
- Upload folder **02** → Wait for processing → **Generate Summary & Audio Overview**
- Upload folder **06** (Slide PDFs) → Wait for processing ✅
- Upload folder **04** (optional) → Wait for processing

### 4. Generate Features
After transcripts (folder 02) are processed:
- **Summary** - Click "Generate" → "Summary"
- **Audio Overview** - Sidebar → "Audio Overview"
- **Study Guide** - Sidebar → "Study Guide"

After all files are processed:
- **Flashcards** - Sidebar → "Flashcards"
- **Quizzes** - Sidebar → "Quiz"
- **Mind Maps** - Sidebar → "Mind Map"

### 5. Make Public
- Click **"Share"** (top-right)
- Select **"Get shareable link"**
- Set to **"Anyone with the link can view"**
- Copy link and update repository README

## ⚠️ Important Notes

- **Wait for processing** before uploading next folder
- **Generate features incrementally** (after transcripts, then after all files)
- **Test in incognito** before sharing publicly
- **Personal Google account required** for public sharing

## 📊 File Counts

- Transcripts: 27 files
- Slide Images: 119 files (individual - not recommended due to source limit)
- Slide PDFs: ~27 files (one per video - **RECOMMENDED** ✅)
- Companion Files: 119 files (optional)
- Backup files skipped: 21 (not needed)

## ⚠️ Source Limit Warning

NotebookLM free plan has a **50 source limit per notebook**.

**If uploading individual images:**
- 27 transcripts + 1 Master KB + 119 images = 147 sources ❌ (exceeds limit)

**If uploading PDFs:**
- 27 transcripts + 1 Master KB + 27 PDFs = 55 sources ⚠️ (still over, but closer)

**Best approach:** Upload transcripts + PDFs, skip companion files to stay under 50 sources.

---

*For detailed instructions, see [NotebookLM Creation Guide](../../docs/NOTEBOOKLM_CREATION_GUIDE.md)*
