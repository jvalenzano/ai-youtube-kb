# Contributing to AI YouTube KB

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ai-youtube-kb.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit: `git commit -m "Add feature: description"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install sentence-transformers  # For local search

# Install slide extraction dependencies (optional)
pip install opencv-python pytesseract Pillow imagehash
pip install transformers torch  # for CLIP
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small

## Testing

Before submitting a PR, please:
- Test your changes with a small playlist
- Verify slide extraction works (if modifying that code)
- Check that NotebookLM export still works
- Ensure query.py search index builds correctly

## Pull Request Process

1. Update README.md if you've changed functionality
2. Add tests if applicable
3. Ensure all existing tests pass
4. Update CHANGELOG.md (if it exists) with your changes
5. Request review from maintainers

## Areas for Contribution

- **Multi-platform support**: Vimeo, Loom, other video platforms
- **Web UI**: Browser-based query interface
- **Performance**: Faster slide extraction, better caching
- **Documentation**: Examples, tutorials, video guides
- **Bug fixes**: See open issues

## Questions?

Open an issue with the `question` label, or reach out to maintainers.

Thank you for contributing! 🚀

