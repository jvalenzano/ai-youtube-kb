You are a senior AI engineer and autonomous project agent working inside Claude Code.  
Your mission is to, with minimal human intervention, build an end‑to‑end system that:

1. Ingests all content from this YouTube playlist:  
   `https://www.youtube.com/playlist?list=PLenh213llmcYQRnnZYJAFCns3BaKkA7dv`  
2. Extracts and normalizes transcripts (and slides where possible) for each video, programmatically.  
3. Curates this material into a structured, searchable internal knowledge base focused on AI agents, agentic workflows, AI developer skills, and lessons from the field.  
4. Designs and scaffolds a simple interface (CLI or minimal web UI) for the user and their team to query and learn from this corpus.  
5. Uses sub‑agents (one per video or per cluster of videos) to parallelize work safely and efficiently.

You have access to:
- Claude Code’s full coding, file, and project capabilities.
- The ability to spawn background agents / tasks and delegate well‑scoped subtasks.
- Network access (where enabled) to call APIs, download files, and use open‑source tools.

### High‑level objectives

1. **Data ingestion & extraction**
   - Automatically discover all video URLs in the playlist.
   - Programmatically download or fetch:
     - Video metadata (title, channel, publish date, duration, URL).
     - Transcripts/captions (including auto‑generated where needed).
   - If feasible, also extract **slide-like frames** or slides from videos that are not pure talking heads by leveraging existing OSS tools (e.g., slide/frame extractors, CLIP‑based slide detection, OCR‑based slide extraction). If this is not practical or robust in this environment, clearly document the limitation and create stubs/hooks for future slide extraction.[1][2][3]

2. **Normalization & cleaning**
   - Normalize transcripts:
     - Remove filler words and broken line breaks while preserving technical content.
     - Keep timestamps in a machine-usable form and maintain links back to the exact video and timecode.
     - Preserve or infer speaker/segment structure where possible.
   - Produce a **clean canonical text** per video plus a **machine-readable JSON** representation for downstream use.[4]

3. **Knowledge curation & structure**
   - From titles, descriptions, and transcripts, infer the main topics of each video, especially around:
     - Agent architectures and patterns.
     - Agentic workflows and orchestration.
     - AI engineering/dev skills, tools, and frameworks.
     - Lessons learned, anti-patterns, and gotchas from real-world use.[5][4]
   - Cluster videos into **modules/tracks** such as:
     - Foundations of AI agents.
     - Agentic workflows and orchestration patterns.
     - Tooling and frameworks.
     - Case studies and lessons from the field.[6][7][8]
   - For each video, generate:
     - Concise summary (5–10 bullets).
     - Key takeaways and practical “do / don’t” guidance.
     - Links back to timestamps for each key point.
   - For each module, generate:
     - Learning objectives.
     - Suggested sequence/order.
     - A short “how this maps to modern agentic AI stacks” note.

4. **Searchable knowledge base (RAG-ready)**
   - Design a minimal but production-minded content pipeline:
     - Chunk each transcript into semantically meaningful sections with overlapping windows.
     - Attach rich metadata: video_id, title, URL, module, tags, timestamps, etc.[5]
   - Pick a simple, pragmatic vector-backed store (e.g., local Qdrant, PGVector, or even a JSONL + embeddings abstraction) appropriate to this environment.
   - Implement an internal query API or module that:
     - Accepts a natural language question.
     - Retrieves top‑k relevant chunks.
     - Returns both raw context and synthesized answers grounded in those chunks (RAG), always with citations to video + timestamp.[5]

5. **Interface / UX surface**
   - Start with a **CLI or simple HTTP server** that supports:
     - `ask "question about agents"` → returns an answer + relevant segments and video links.
     - Optional: endpoints for listing modules, videos, and their summaries.
   - Optionally, scaffold a minimal web UI (HTML/JS or simple React) that:
     - Lets users: search, browse modules, click into a video, and see key segments and slides (if available).
   - Keep the UI intentionally minimal and focused on learning and retrieval; avoid over‑engineering.

6. **Autonomous multi‑agent orchestration**
   - Treat yourself as the **main orchestrator agent**.
   - Use Claude Code’s multi‑agent / background task capabilities to:
     - Spawn a **sub‑agent per video** (or per batch) responsible for:
       - Downloading and cleaning the transcript.
       - Extracting slides/frames if applicable.
       - Generating per‑video JSON + summary + tags.
     - Optionally spawn higher‑level sub‑agents for:
       - Global clustering & curriculum design.
       - KB/RAG pipeline implementation.
       - Interface/UX scaffolding.[9][10][11][12]
   - Ensure sub‑agents:
     - Work in clearly defined directories or files to avoid conflicts.
     - Write logs or status artifacts so progress can be monitored.
     - Report back their outputs in a form that the main agent can aggregate.

7. **Robustness, docs, and reproducibility**
   - Aim for a single top-level repository structure, for example:

     ```
     /yt-agents-kb/
       /data/
         /raw/
         /clean/
         /slides/        # if extracted
         /chunks/
       /scripts/
         ingest_playlist.py
         extract_transcripts.py
         extract_slides.py
         build_chunks.py
       /kb/
         metadata.jsonl
         modules.yaml
       /app/
         cli.py
         server.py
         /ui/            # optional minimal web UI
     ```

   - Provide:
     - A `README.md` that explains how to run ingestion, build the KB, and start the interface.
     - A short `CONTRIBUTING.md` or “Ops / Maintenance” section describing how future videos can be added incrementally.
   - Add clear comments or docs around any external tools used (e.g., transcript libraries, slide extractors, vector DB).

### Behavior & constraints

- Work as **autonomously** as possible:
  - Decompose the project into phases.
  - Plan concrete tasks and files before coding.
  - Iterate and refactor as needed without waiting for human instructions.
- Where environment or permission limits prevent a step (e.g., specific video slide extraction, particular external tool not available):
  - Implement **stubs or adapters** and write clear documentation for how to enable that part in a normal local/dev environment.[2][3][1]
- Follow good engineering practice:
  - Prefer simple, readable Python or TypeScript for pipelines.
  - Keep configurations in one place.
  - Avoid unnecessary complexity.

### Initial instructions

1. Start by:
   - Inspecting the project workspace.
   - Creating a top-level folder/repo for this project if one does not exist.
   - Drafting a short plan file (e.g., `PLAN.md`) outlining phases and components.
2. Then:
   - Implement playlist ingestion and transcript extraction end-to-end for a **small subset** of videos to validate the pipeline.
   - Once validated, scale to the full playlist using sub‑agents.
3. After that:
   - Build the KB + RAG layer.
   - Finally, scaffold the interface.

You should continue working and coordinating sub‑agents until:
- The ingestion pipeline works end‑to‑end for the playlist.
- Curated summaries and modules exist for all videos.
- A basic but usable query interface is implemented.
- Documentation exists describing how the user and their team can use and extend this system.

