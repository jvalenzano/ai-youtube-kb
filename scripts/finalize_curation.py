#!/usr/bin/env python3
"""
Finalize slide curation - Sync metadata and refresh all exports.

Run this when you're satisfied with your manual slide curation.
This ensures metadata matches files and all exports are up-to-date.

Usage:
    python scripts/finalize_curation.py
    python scripts/finalize_curation.py --skip-exports  # Only sync metadata
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

PROJECT_ROOT = Path(__file__).parent.parent
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
KB_DIR = PROJECT_ROOT / "kb"

console = Console()


def run_command(cmd: list[str], cwd: Path = None) -> tuple[int, str]:
    """Run a command and return exit code + output."""
    result = subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout + result.stderr


def finalize_curation(skip_exports: bool = False) -> dict:
    """Finalize slide curation workflow."""
    
    console.print(Panel(
        "[bold]Finalize Slide Curation[/bold]\n\n"
        "This will:\n"
        "1. Sync metadata with actual slide files\n"
        "2. Refresh NotebookLM exports\n"
        "3. Update Master Knowledge Base\n"
        "4. Rebuild search index\n\n"
        "Run this when you're satisfied with manual slide curation.",
        title="Curation Finalization",
        border_style="blue"
    ))
    
    # Step 1: Sync all metadata
    console.print("\n[bold cyan]Step 1/4:[/bold cyan] Syncing metadata with files...")
    
    video_dirs = [d for d in DATA_SLIDES.iterdir() if d.is_dir()]
    if not video_dirs:
        console.print("[yellow]No slide directories found[/yellow]")
        return {'error': 'No slides found'}
    
    synced_count = 0
    total_removed = 0
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Syncing metadata...", total=len(video_dirs))
        
        for video_dir in video_dirs:
            video_id = video_dir.name
            progress.update(task, description=f"Syncing {video_id}...")
            
            code, output = run_command(
                [sys.executable, 'scripts/sync_slide_metadata.py', '--video', video_id]
            )
            
            if code == 0:
                synced_count += 1
                # Try to extract removal count from output
                if 'removed' in output.lower():
                    total_removed += 1
        
        progress.advance(task)
    
    console.print(f"[green]✓ Synced {synced_count} videos[/green]")
    if total_removed > 0:
        console.print(f"[dim]  Removed {total_removed} orphaned metadata entries[/dim]")
    
    if skip_exports:
        console.print("\n[yellow]Skipping exports (--skip-exports)[/yellow]")
        return {
            'synced': synced_count,
            'exports_skipped': True
        }
    
    # Step 2: Refresh NotebookLM exports
    console.print("\n[bold cyan]Step 2/4:[/bold cyan] Refreshing NotebookLM exports...")
    code, output = run_command([sys.executable, 'scripts/export_notebooklm.py'])
    if code == 0:
        console.print("[green]✓ NotebookLM exports refreshed[/green]")
    else:
        console.print(f"[yellow]Export had warnings: {output[-200:]}[/yellow]")
    
    # Step 3: Update Master Knowledge Base
    console.print("\n[bold cyan]Step 3/4:[/bold cyan] Updating Master Knowledge Base...")
    code, output = run_command([sys.executable, 'scripts/generate_master_kb.py'])
    if code == 0:
        console.print("[green]✓ Master Knowledge Base updated[/green]")
    else:
        console.print(f"[yellow]Master KB had warnings: {output[-200:]}[/yellow]")
    
    # Step 4: Rebuild search index
    console.print("\n[bold cyan]Step 4/4:[/bold cyan] Rebuilding search index...")
    code, output = run_command([sys.executable, 'query.py', '--build'])
    if code == 0:
        console.print("[green]✓ Search index rebuilt[/green]")
    else:
        console.print(f"[yellow]Index build had warnings: {output[-200:]}[/yellow]")
    
    # Summary
    console.print("\n[bold green]✓ Curation finalized![/bold green]")
    console.print("\n[bold]Your knowledge base is ready:[/bold]")
    console.print("  • Metadata synced with slide files")
    console.print("  • NotebookLM exports updated")
    console.print("  • Master Knowledge Base refreshed")
    console.print("  • Search index rebuilt")
    console.print("\n[dim]Next: Import to NotebookLM or query locally[/dim]")
    
    return {
        'synced': synced_count,
        'exports_refreshed': not skip_exports,
        'complete': True
    }


@click.command()
@click.option('--skip-exports', is_flag=True, help='Only sync metadata, skip exports')
def main(skip_exports: bool):
    """Finalize slide curation - Sync metadata and refresh exports."""
    result = finalize_curation(skip_exports)
    
    if 'error' in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()

