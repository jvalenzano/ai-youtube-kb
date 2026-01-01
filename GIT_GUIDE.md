# Git Basics Guide for Beginners 🚀

This guide will help you understand Git and manage your repository.

## What is Git?

Git is a version control system that tracks changes to your files. Think of it like a time machine for your code - you can see what changed, when, and why.

## Current Status ✅

Your repository is **fully set up** and connected to GitHub:
- **Local repository**: `/Users/jvalenzano/Projects/the-cube/yt-agents-kb`
- **GitHub repository**: https://github.com/jvalenzano/ai-youtube-kb
- **Branch**: `main`
- **Status**: All changes committed and pushed

## Essential Git Commands

### Check Status
```bash
git status
```
Shows what files have changed, what's staged, and what's committed.

**Example output:**
```
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```
This means: ✅ Everything is saved and synced!

### See What Changed
```bash
# See changes in files (not yet staged)
git diff

# See changes that are staged (ready to commit)
git diff --staged

# See recent commits
git log --oneline -10
```

### The Basic Workflow

When you make changes to files, follow these steps:

#### 1. Check what changed
```bash
git status
```

#### 2. Stage your changes (tell Git which files to save)
```bash
# Stage a specific file
git add README.md

# Stage all changed files
git add .

# Stage all files matching a pattern
git add scripts/*.py
```

#### 3. Commit your changes (save a snapshot)
```bash
git commit -m "Description of what you changed"
```

**Good commit messages:**
- ✅ `"Add attribution section to README"`
- ✅ `"Fix slide extraction bug"`
- ❌ `"changes"` (too vague)
- ❌ `"stuff"` (not helpful)

#### 4. Push to GitHub (upload your changes)
```bash
git push origin main
```

## Common Scenarios

### Scenario 1: You edited README.md

```bash
# 1. Check status
git status
# Output: "modified: README.md"

# 2. Stage the file
git add README.md

# 3. Commit
git commit -m "Update README with new feature"

# 4. Push to GitHub
git push origin main
```

### Scenario 2: You created a new file

```bash
# 1. Check status
git status
# Output: "Untracked files: new_script.py"

# 2. Stage the new file
git add new_script.py

# 3. Commit
git commit -m "Add new script for feature X"

# 4. Push
git push origin main
```

### Scenario 3: You want to see what changed

```bash
# See changes in a specific file
git diff README.md

# See all changes
git diff

# See commit history
git log --oneline --graph -10
```

### Scenario 4: You made a mistake

```bash
# Undo changes to a file (before staging)
git checkout -- README.md

# Unstage a file (after git add, before commit)
git reset HEAD README.md

# Undo last commit (keep changes)
git reset --soft HEAD~1

# See what you're about to undo
git show HEAD
```

## Understanding Git States

Files can be in different states:

```
┌─────────────┐
│  Untracked  │  → New file, Git doesn't know about it
└──────┬──────┘
       │ git add
       ↓
┌─────────────┐
│   Staged    │  → File is ready to be committed
└──────┬──────┘
       │ git commit
       ↓
┌─────────────┐
│  Committed  │  → Changes are saved in Git history
└──────┬──────┘
       │ git push
       ↓
┌─────────────┐
│   GitHub    │  → Changes are on GitHub (backed up!)
└─────────────┘
```

## Your Current Setup

### Local Repository
- **Location**: `/Users/jvalenzano/Projects/the-cube/yt-agents-kb`
- **Branch**: `main`
- **Remote**: `origin` → https://github.com/jvalenzano/ai-youtube-kb.git

### Recent Commits
1. `d948a02` - Add proper attribution (most recent)
2. `98f7264` - Initial: AI YouTube KB pipeline v1.0

## Quick Reference

| Command | What it does |
|---------|-------------|
| `git status` | See what's changed |
| `git add .` | Stage all changes |
| `git commit -m "message"` | Save changes with a message |
| `git push` | Upload to GitHub |
| `git pull` | Download from GitHub |
| `git log` | See commit history |
| `git diff` | See what changed |

## IDE Integration

Most IDEs (VS Code, Cursor, etc.) show Git status with:
- **Green** = New/added files
- **Yellow** = Modified files
- **Red** = Deleted files
- **U** = Untracked files

You can usually commit and push from your IDE's Git panel!

## Need Help?

- **Git documentation**: https://git-scm.com/doc
- **GitHub Guides**: https://guides.github.com/
- **Visual Git Guide**: https://learngitbranching.js.org/

## Pro Tips

1. **Commit often**: Small, frequent commits are better than huge ones
2. **Write good messages**: Future you will thank present you
3. **Check status before committing**: `git status` is your friend
4. **Pull before push**: If working with others, `git pull` first
5. **Use `.gitignore`**: Prevents committing sensitive files (API keys, etc.)

---

**Your repository is ready to go!** 🎉 All your changes are being tracked and backed up on GitHub.

