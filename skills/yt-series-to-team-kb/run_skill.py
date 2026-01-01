#!/usr/bin/env python3
"""
YT-Series-to-Team-KB Skill

Transform any YouTube playlist into a structured team knowledge base.

Usage:
    python run_skill.py
    python run_skill.py --playlist URL
    python run_skill.py --playlist URL --topics "machine learning, deep learning"
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Template location (this project)
TEMPLATE_DIR = Path(__file__).parent.parent.parent


def validate_playlist_url(url: str) -> bool:
    """Check if URL looks like a YouTube playlist."""
    return 'youtube.com/playlist' in url or 'youtu.be' in url


def run_command(cmd: list[str], cwd: Path, env: dict = None) -> tuple[int, str]:
    """Run a command and return exit code + output."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=full_env,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout + result.stderr


def create_project(
    playlist_url: str,
    output_dir: Path,
    topics: str = "AI agents, agentic workflows",
    api_key: Optional[str] = None
) -> bool:
    """Create a new knowledge base project from template."""

    console.print(Panel(
        f"[bold]Creating Knowledge Base[/bold]\n\n"
        f"Playlist: {playlist_url}\n"
        f"Topics: {topics}\n"
        f"Output: {output_dir}",
        title="YT-Series-to-Team-KB"
    ))

    # Check API key
    if not api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY not set![/red]")
        console.print("Set it with: export ANTHROPIC_API_KEY=your_key")
        return False

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy template files
    console.print("[blue]Setting up project structure...[/blue]")

    dirs_to_copy = ['scripts', 'kb']
    files_to_copy = ['requirements.txt', 'query.py']

    for d in dirs_to_copy:
        src = TEMPLATE_DIR / d
        dst = output_dir / d
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)

    for f in files_to_copy:
        src = TEMPLATE_DIR / f
        dst = output_dir / f
        if src.exists():
            shutil.copy2(src, dst)

    # Create data directories
    (output_dir / 'data' / 'raw').mkdir(parents=True, exist_ok=True)
    (output_dir / 'data' / 'clean').mkdir(parents=True, exist_ok=True)
    (output_dir / 'notebooks' / 'notebooklm-ready' / 'videos').mkdir(parents=True, exist_ok=True)
    (output_dir / 'notebooks' / 'notebooklm-ready' / 'modules').mkdir(parents=True, exist_ok=True)

    # Create venv and install deps
    console.print("[blue]Installing dependencies...[/blue]")
    run_command([sys.executable, '-m', 'venv', '.venv'], output_dir)

    venv_python = output_dir / '.venv' / 'bin' / 'python'
    run_command([str(venv_python), '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'], output_dir)
    run_command([str(venv_python), '-m', 'pip', 'install', '-q', 'sentence-transformers'], output_dir)

    env = {'ANTHROPIC_API_KEY': api_key}

    # Step 1: Ingest playlist
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Ingesting playlist...", total=None)

        code, output = run_command(
            [str(venv_python), 'scripts/ingest.py', '--playlist', playlist_url],
            output_dir, env
        )

        if code != 0:
            console.print(f"[red]Ingestion failed:[/red]\n{output}")
            return False

        progress.update(task, description="Ingestion complete!")

    # Count videos
    raw_files = list((output_dir / 'data' / 'raw').glob('*.json'))
    console.print(f"[green]Extracted {len(raw_files)} transcripts[/green]")

    # Step 2: Curate with Claude
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Curating with Claude...", total=None)

        code, output = run_command(
            [str(venv_python), 'scripts/curate.py', '--all'],
            output_dir, env
        )

        if code != 0:
            console.print(f"[yellow]Some curation errors (may be partial):[/yellow]\n{output[-500:]}")

        progress.update(task, description="Curation complete!")

    # Step 3: Export
    console.print("[blue]Exporting NotebookLM artifacts...[/blue]")
    run_command([str(venv_python), 'scripts/export_notebooklm.py'], output_dir, env)

    # Step 4: Generate master KB
    console.print("[blue]Generating Master Knowledge Base...[/blue]")
    run_command([str(venv_python), 'scripts/generate_master_kb.py'], output_dir, env)

    # Step 5: Build search index
    console.print("[blue]Building search index...[/blue]")
    run_command([str(venv_python), 'query.py', '--build'], output_dir, env)

    # Generate README
    readme_content = f"""# Knowledge Base: {playlist_url}

Generated by YT-Series-to-Team-KB

## Quick Start

```bash
source .venv/bin/activate

# Search locally
python query.py "your question here"

# View all content
cat notebooks/Master_Knowledge_Base.md
```

## Import to NotebookLM

1. Go to https://notebooklm.google.com
2. Create new notebook
3. Add source → drag files from `notebooks/notebooklm-ready/videos/`
4. Share with team!

## Files

- `notebooks/Master_Knowledge_Base.md` - Complete knowledge base
- `notebooks/notebooklm-ready/` - Files for NotebookLM
- `query.py` - Local semantic search
"""
    (output_dir / 'README.md').write_text(readme_content)

    # Summary
    console.print(Panel(
        f"[bold green]Knowledge Base Created![/bold green]\n\n"
        f"Location: {output_dir}\n"
        f"Videos: {len(raw_files)}\n\n"
        f"[bold]Next Steps:[/bold]\n"
        f"1. cd {output_dir}\n"
        f"2. source .venv/bin/activate\n"
        f"3. python query.py \"your question\"\n"
        f"4. Import notebooks/notebooklm-ready/ to NotebookLM",
        title="Success"
    ))

    return True


@click.command()
@click.option('--playlist', '-p', help='YouTube playlist URL')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--topics', '-t', default='AI agents, agentic workflows', help='Focus topics')
@click.option('--api-key', envvar='ANTHROPIC_API_KEY', help='Anthropic API key')
def main(playlist: Optional[str], output: Optional[str], topics: str, api_key: Optional[str]):
    """Transform a YouTube playlist into a team knowledge base."""

    console.print(Panel(
        "[bold]YT-Series-to-Team-KB[/bold]\n\n"
        "Transform any YouTube playlist into a structured,\n"
        "searchable team knowledge base.",
        title="Welcome"
    ))

    # Interactive mode if no playlist provided
    if not playlist:
        playlist = Prompt.ask("YouTube playlist URL")

    if not validate_playlist_url(playlist):
        console.print("[red]Invalid playlist URL. Should contain 'youtube.com/playlist'[/red]")
        return

    if not output:
        # Generate default name from playlist
        default_name = f"kb-{playlist.split('list=')[-1][:8]}"
        output = Prompt.ask("Output directory", default=default_name)

    output_path = Path(output).resolve()

    if output_path.exists():
        if not Confirm.ask(f"{output_path} exists. Overwrite?"):
            return

    if not api_key:
        api_key = Prompt.ask("Anthropic API key", password=True)

    # Confirm
    if not Confirm.ask(f"Create knowledge base at {output_path}?"):
        return

    success = create_project(playlist, output_path, topics, api_key)

    if not success:
        console.print("[red]Failed to create knowledge base[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()
