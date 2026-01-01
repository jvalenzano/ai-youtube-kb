#!/usr/bin/env python3
"""
Slide extraction from YouTube videos.

Detects, extracts, OCRs, and deduplicates presentation slides from videos.
Uses hybrid detection: frame differencing for scene changes + CLIP for classification.

Usage:
    python scripts/extract_slides.py --video VIDEO_ID
    python scripts/extract_slides.py --all
    python scripts/extract_slides.py --status
    python scripts/extract_slides.py --check

Dependencies:
    pip install opencv-python pytesseract Pillow imagehash transformers torch

System requirements:
    brew install tesseract  # macOS
    apt install tesseract-ocr  # Ubuntu
"""

import json
import multiprocessing
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_SLIDES = PROJECT_ROOT / "data" / "slides"
KB_DIR = PROJECT_ROOT / "kb"

console = Console()


@dataclass
class SlideConfig:
    """Configuration for slide extraction."""
    frame_interval: float = 2.0           # Seconds between frames
    scene_threshold: float = 0.15         # Histogram difference threshold
    clip_threshold: float = 0.55          # CLIP confidence threshold
    use_clip: bool = True                 # Enable CLIP classification
    video_quality: str = "720"            # Download quality
    keep_video: bool = False              # Keep downloaded video
    phash_threshold: int = 10             # Perceptual hash difference threshold
    text_density_min: int = 15            # Minimum words for text-density detection
    text_density_max: int = 300           # Maximum words for text-density detection
    min_ocr_words: int = 10              # Minimum words in OCR text to keep slide
    remove_duplicates: bool = True        # Actually remove duplicates (not just mark)
    filter_filler_text: bool = True       # Filter out copyright/trademark slides
    filter_blurry: bool = True            # Filter out blurry images
    blur_threshold: float = 100.0         # Laplacian variance threshold for blur detection
    add_credit: bool = False              # Add credit overlay to slides
    credit_text: str = ""                 # Custom credit text (empty = auto-generate)
    credit_author: str = ""               # Author name for credit
    credit_series: str = ""               # Series name for credit
    credit_url: str = ""                  # Source URL for credit


@dataclass
class FrameInfo:
    """Information about an extracted frame."""
    path: Path
    timestamp: float
    frame_number: int


@dataclass
class SlideInfo:
    """Information about a detected slide."""
    path: Path
    timestamp: float
    timestamp_formatted: str
    perceptual_hash: str = ""
    ocr_text: str = ""
    clip_score: Optional[float] = None
    is_duplicate_of: Optional[str] = None
    transcript_context: dict = field(default_factory=dict)


class VideoDownloadError(Exception):
    """Raised when video download fails."""
    pass


class SlideExtractor:
    """
    Extracts slides from YouTube videos using hybrid detection.

    Pipeline:
    1. Download video at 720p
    2. Extract frames every 2 seconds
    3. Detect scene changes via histogram comparison
    4. Classify slides using CLIP or text-density
    5. OCR text extraction
    6. Deduplicate using perceptual hashing
    7. Align with transcript timestamps
    """

    def __init__(self, video_id: str, config: Optional[SlideConfig] = None):
        self.video_id = video_id
        self.config = config or SlideConfig()
        self.output_dir = DATA_SLIDES / video_id
        self.frames_dir = self.output_dir / "frames"

        # Lazy-loaded models
        self._clip_model = None
        self._clip_processor = None

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to timestamp string like '15m11s'."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m{secs:02d}s"

    def _get_video_metadata(self) -> dict:
        """Load video metadata from kb/metadata.json."""
        metadata_file = KB_DIR / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                data = json.load(f)
                for video in data.get('videos', []):
                    if video.get('video_id') == self.video_id:
                        return video
        return {'video_id': self.video_id, 'title': '', 'url': f'https://www.youtube.com/watch?v={self.video_id}'}

    def download_video(self) -> Path:
        """Download video using yt-dlp at specified quality."""
        import yt_dlp

        self.output_dir.mkdir(parents=True, exist_ok=True)
        video_path = self.output_dir / "video.mp4"

        # Skip if already downloaded
        if video_path.exists():
            console.print(f"[dim]Video already downloaded: {video_path}[/dim]")
            return video_path

        url = f"https://www.youtube.com/watch?v={self.video_id}"

        ydl_opts = {
            'format': f'best[height<={self.config.video_quality}][ext=mp4]/best[height<={self.config.video_quality}]',
            'outtmpl': str(video_path),
            'quiet': True,
            'no_warnings': True,
            'retries': 3,
            'fragment_retries': 3,
        }

        max_retries = 3
        base_delay = 30

        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                return video_path
            except yt_dlp.utils.DownloadError as e:
                if '429' in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    console.print(f"[yellow]Rate limited. Waiting {delay}s...[/yellow]")
                    time.sleep(delay)
                else:
                    raise VideoDownloadError(f"Download failed after {max_retries} attempts: {e}")

        raise VideoDownloadError("Download failed unexpectedly")

    def extract_frames(self, video_path: Path) -> list[FrameInfo]:
        """Extract frames at configured interval using OpenCV."""
        import cv2

        self.frames_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps == 0:
            raise ValueError("Could not read video FPS")

        frame_interval_frames = int(fps * self.config.frame_interval)

        frames = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval_frames == 0:
                timestamp = frame_count / fps
                frame_path = self.frames_dir / f"frame_{frame_count:08d}.jpg"
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                frames.append(FrameInfo(
                    path=frame_path,
                    timestamp=timestamp,
                    frame_number=frame_count
                ))

            frame_count += 1

        cap.release()
        return frames

    def _compute_histogram(self, frame_path: Path):
        """Compute grayscale histogram for frame comparison."""
        import cv2
        import numpy as np

        img = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        hist = cv2.calcHist([img], [0], None, [256], [0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()

    def detect_scene_changes(self, frames: list[FrameInfo]) -> list[FrameInfo]:
        """Detect scene changes using histogram comparison."""
        import cv2

        if not frames:
            return []

        candidates = [frames[0]]  # Always include first frame
        prev_hist = self._compute_histogram(frames[0].path)

        if prev_hist is None:
            return candidates

        for frame in frames[1:]:
            curr_hist = self._compute_histogram(frame.path)

            if curr_hist is None:
                continue

            # Compare histograms (correlation method)
            correlation = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CORREL)
            diff = 1 - correlation

            if diff > self.config.scene_threshold:
                candidates.append(frame)

            prev_hist = curr_hist

        return candidates

    def _load_clip_model(self):
        """Lazy load CLIP model."""
        if self._clip_model is None:
            try:
                from transformers import CLIPProcessor, CLIPModel
                self._clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self._clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            except Exception as e:
                console.print(f"[yellow]CLIP unavailable: {e}. Using text-density fallback.[/yellow]")
                self.config.use_clip = False
                return None
        return self._clip_model

    def _classify_with_clip(self, candidates: list[FrameInfo]) -> list[SlideInfo]:
        """Use CLIP to classify frames as slides."""
        from PIL import Image
        import torch

        model = self._load_clip_model()
        if model is None:
            return self._classify_with_text_density(candidates)

        slide_prompts = [
            "a presentation slide with text and graphics",
            "a data chart or diagram",
            "a screen showing text content",
            "infographic or data visualization",
        ]
        non_slide_prompts = [
            "a person speaking on camera",
            "a talking head video interview",
            "people in a video conference",
        ]

        all_prompts = slide_prompts + non_slide_prompts
        slides = []

        for frame in candidates:
            try:
                image = Image.open(frame.path).convert('RGB')

                inputs = self._clip_processor(
                    text=all_prompts,
                    images=image,
                    return_tensors="pt",
                    padding=True
                )

                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = outputs.logits_per_image.softmax(dim=1)[0]

                # Sum probabilities for slide-like prompts vs non-slide
                slide_score = probs[:len(slide_prompts)].sum().item()
                non_slide_score = probs[len(slide_prompts):].sum().item()

                # Normalize to get slide probability
                total = slide_score + non_slide_score
                slide_prob = slide_score / total if total > 0 else 0

                if slide_prob > self.config.clip_threshold:
                    slides.append(SlideInfo(
                        path=frame.path,
                        timestamp=frame.timestamp,
                        timestamp_formatted=self._format_timestamp(frame.timestamp),
                        clip_score=round(slide_prob, 3)
                    ))
            except Exception as e:
                console.print(f"[dim]Error classifying frame {frame.path.name}: {e}[/dim]")
                continue

        return slides

    def _classify_with_text_density(self, candidates: list[FrameInfo]) -> list[SlideInfo]:
        """Fallback: classify slides by OCR text density."""
        import pytesseract
        from PIL import Image

        slides = []

        for frame in candidates:
            try:
                image = Image.open(frame.path)
                text = pytesseract.image_to_string(image)
                word_count = len(text.split())

                # Slides typically have 15-300 words
                if self.config.text_density_min < word_count < self.config.text_density_max:
                    slides.append(SlideInfo(
                        path=frame.path,
                        timestamp=frame.timestamp,
                        timestamp_formatted=self._format_timestamp(frame.timestamp),
                        ocr_text=text.strip()
                    ))
            except Exception as e:
                console.print(f"[dim]Error analyzing frame {frame.path.name}: {e}[/dim]")
                continue

        return slides

    def classify_slides(self, candidates: list[FrameInfo]) -> list[SlideInfo]:
        """Classify candidates as slides using CLIP or fallback."""
        if self.config.use_clip:
            return self._classify_with_clip(candidates)
        else:
            return self._classify_with_text_density(candidates)

    def extract_text(self, slide: SlideInfo) -> str:
        """Extract text from slide using pytesseract with preprocessing."""
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter

        try:
            image = Image.open(slide.path)

            # Preprocessing for better OCR
            image = image.convert('L')  # Grayscale
            image = ImageEnhance.Contrast(image).enhance(1.5)
            image = image.filter(ImageFilter.SHARPEN)

            # Configure tesseract for slide text
            config = '--psm 6 -c preserve_interword_spaces=1'
            text = pytesseract.image_to_string(image, config=config)

            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        except Exception as e:
            console.print(f"[dim]OCR error for {slide.path.name}: {e}[/dim]")
            return ""

    def _is_filler_text(self, text: str) -> bool:
        """Check if text is mostly filler (copyright, trademarks, branding, etc.)."""
        if not text:
            return True
        
        text_lower = text.lower()
        filler_patterns = [
            # Copyright/trademark
            'copyright', '©', 'registered trademark', '®', 'all rights reserved',
            # Branding
            'siliconangle', 'thecube', 'the cube', 'silicon angle', 'thecuberesearch',
            'go to thecuberesearch.com', 'thecuberesearch.com',
            # End slides
            'thank you', 'questions?', 'q & a', 'q&a', 'your views', 'let us know',
            'contact us', 'linkedin.com/in',
            # Promotional
            'ai agent builder summit', 'speed your way to roi',
            # Navigation/prompts
            'next frontiers of ai', 'the next frontiers',
        ]
        
        # Count how many filler patterns appear
        filler_count = sum(1 for pattern in filler_patterns if pattern in text_lower)
        word_count = len(text.split())
        
        # If very short, it's likely filler
        if word_count < 5:
            return True
        
        # If contains filler patterns and is short, it's filler
        if filler_count > 0 and word_count < 25:
            return True
        
        # If mostly branding/contact info (high filler ratio)
        if filler_count >= 2 and word_count < 30:
            return True
        
        return False

    def _is_mostly_black(self, image_path: Path, threshold: float = 0.85) -> bool:
        """Check if image is mostly black/empty."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                return True
            
            # Calculate percentage of pixels that are very dark (0-30 out of 255)
            dark_pixels = np.sum(img < 30)
            total_pixels = img.size
            dark_ratio = dark_pixels / total_pixels
            
            return dark_ratio > threshold
        except Exception:
            return False

    def _is_blurry(self, image_path: Path, threshold: float = 100.0) -> bool:
        """Check if image is blurry using Laplacian variance.
        
        Lower variance = more blurry.
        Typical threshold: 100 (below this is considered blurry).
        """
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                return True
            
            # Calculate Laplacian variance (measure of sharpness)
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            variance = laplacian.var()
            
            return variance < threshold
        except Exception:
            return False

    def filter_quality(self, slides: list[SlideInfo]) -> list[SlideInfo]:
        """Filter out low-quality slides based on content."""
        filtered = []
        removed_reasons = {
            'low_text': 0,
            'filler_text': 0,
            'mostly_black': 0,
            'blurry': 0,
        }

        for slide in slides:
            # Filter: blurry images (check first, before OCR)
            if self.config.filter_blurry and self._is_blurry(slide.path, self.config.blur_threshold):
                removed_reasons['blurry'] += 1
                continue
            
            # Filter: mostly black/empty images
            if self._is_mostly_black(slide.path):
                removed_reasons['mostly_black'] += 1
                continue
            
            # Check OCR text quality
            ocr_text = slide.ocr_text or ""
            word_count = len(ocr_text.split())
            
            # Filter: too little text
            if word_count < self.config.min_ocr_words:
                removed_reasons['low_text'] += 1
                continue
            
            # Filter: filler text (copyright, trademarks, etc.)
            if self.config.filter_filler_text and self._is_filler_text(ocr_text):
                removed_reasons['filler_text'] += 1
                continue
            
            filtered.append(slide)

        if any(removed_reasons.values()):
            console.print(f"[dim]Quality filter removed: {removed_reasons}[/dim]")
        
        return filtered

    def deduplicate(self, slides: list[SlideInfo]) -> list[SlideInfo]:
        """Remove duplicate slides using perceptual hashing."""
        import imagehash
        from PIL import Image

        if not slides:
            return slides

        hash_map = {}  # hash_str -> first slide info
        result = []
        duplicates_removed = 0

        for slide in slides:
            try:
                image = Image.open(slide.path)
                phash = imagehash.phash(image)
                phash_str = str(phash)
                slide.perceptual_hash = phash_str

                # Check for similar hashes
                is_duplicate = False
                for existing_hash, (existing_slide, existing_phash) in hash_map.items():
                    distance = phash - existing_phash

                    if distance <= self.config.phash_threshold:
                        if self.config.remove_duplicates:
                            # Actually remove duplicate
                            duplicates_removed += 1
                            is_duplicate = True
                            break
                        else:
                            # Mark as duplicate but keep it
                            slide.is_duplicate_of = existing_slide.path.name
                            is_duplicate = True
                            break

                if not is_duplicate:
                    hash_map[phash_str] = (slide, phash)
                    result.append(slide)
            except Exception as e:
                console.print(f"[dim]Hash error for {slide.path.name}: {e}[/dim]")
                result.append(slide)

        if duplicates_removed > 0:
            console.print(f"[dim]Removed {duplicates_removed} duplicate slides[/dim]")

        return result

    def _load_transcript(self) -> list[dict]:
        """Load raw transcript segments."""
        transcript_file = DATA_RAW / f"{self.video_id}.json"
        if not transcript_file.exists():
            return []

        with open(transcript_file) as f:
            data = json.load(f)

        return data.get('transcript', {}).get('segments', [])

    def _find_context(self, timestamp: float, segments: list[dict],
                      window_before: float = 15, window_after: float = 15) -> dict:
        """Find transcript text around a timestamp."""
        before = []
        during = []
        after = []

        for seg in segments:
            seg_start = seg.get('start', 0)
            seg_end = seg_start + seg.get('duration', 0)
            text = seg.get('text', '').strip().replace('\n', ' ')

            if seg_end < timestamp - window_before:
                continue
            elif seg_start > timestamp + window_after:
                break
            elif seg_end <= timestamp:
                before.append(text)
            elif seg_start >= timestamp:
                after.append(text)
            else:
                during.append(text)

        return {
            'before': ' '.join(before[-4:]),  # Last 4 segments before
            'during': ' '.join(during),
            'after': ' '.join(after[:4]),     # First 4 segments after
        }

    def align_timestamps(self, slides: list[SlideInfo]) -> list[SlideInfo]:
        """Match slide timestamps to transcript segments."""
        segments = self._load_transcript()

        if not segments:
            return slides

        for slide in slides:
            slide.transcript_context = self._find_context(slide.timestamp, segments)

        return slides

    def _add_credit_overlay(self, img: Image.Image) -> Image.Image:
        """Add credit overlay to bottom of image."""
        from PIL import ImageDraw, ImageFont
        
        # Get image dimensions
        width, height = img.size
        
        # Default credit text if not provided
        if self.config.credit_text:
            credit_text = self.config.credit_text
        else:
            # Auto-generate credit text
            parts = []
            if self.config.credit_author:
                parts.append(self.config.credit_author)
            if self.config.credit_series:
                parts.append(self.config.credit_series)
            if not parts:
                # Fallback to video metadata
                video_meta = self._get_video_metadata()
                if video_meta.get('title'):
                    parts.append("Source: YouTube")
                else:
                    parts.append("Source: YouTube Video")
            credit_text = " • ".join(parts)
        
        # Calculate overlay bar height (5% of image height, min 30px, max 60px)
        bar_height = max(30, min(60, int(height * 0.05)))
        
        # Create overlay image
        overlay = Image.new('RGBA', (width, bar_height), (0, 0, 0, 200))  # Semi-transparent black
        draw = ImageDraw.Draw(overlay)
        
        # Try to use a nice font, fallback to default
        try:
            # Try system fonts (macOS)
            font_size = max(12, min(16, int(bar_height * 0.4)))
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), credit_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (bar_height - text_height) // 2
        
        # Draw text (white)
        draw.text((x, y), credit_text, fill=(255, 255, 255, 255), font=font)
        
        # Composite overlay onto image
        result = Image.new('RGB', (width, height + bar_height), (255, 255, 255))
        result.paste(img, (0, 0))
        result.paste(overlay, (0, height), overlay)
        
        return result

    def _save_slide_image(self, slide: SlideInfo) -> Path:
        """Copy slide to final location with proper naming."""
        hash_short = slide.perceptual_hash[:8] if slide.perceptual_hash else "unknown"
        new_name = f"slide_{slide.timestamp_formatted}_{hash_short}.png"
        new_path = self.output_dir / new_name

        # Convert to PNG for better quality
        from PIL import Image
        img = Image.open(slide.path)
        
        # Add credit overlay if enabled
        if self.config.add_credit:
            img = self._add_credit_overlay(img)
        
        img.save(new_path, 'PNG')

        return new_path

    def _save_metadata(self, slides: list[SlideInfo], total_frames: int,
                       scene_changes: int) -> Path:
        """Generate and save metadata.json."""
        video_meta = self._get_video_metadata()

        unique_count = len([s for s in slides if s.is_duplicate_of is None])
        duplicate_count = len(slides) - unique_count

        # Build deduplication map
        dedup_map = {}
        for slide in slides:
            hash_key = slide.perceptual_hash
            if hash_key:
                if hash_key not in dedup_map:
                    dedup_map[hash_key] = []
                dedup_map[hash_key].append(slide.path.name)

        # Filter to only hashes with duplicates
        dedup_map = {k: v for k, v in dedup_map.items() if len(v) > 1}

        metadata = {
            'video_id': self.video_id,
            'title': video_meta.get('title', ''),
            'url': video_meta.get('url', f'https://www.youtube.com/watch?v={self.video_id}'),
            'extracted_at': datetime.now().isoformat(),
            'extraction_config': {
                'frame_interval': self.config.frame_interval,
                'use_clip': self.config.use_clip,
                'clip_threshold': self.config.clip_threshold,
                'scene_threshold': self.config.scene_threshold,
            },
            'stats': {
                'total_frames_analyzed': total_frames,
                'scene_changes_detected': scene_changes,
                'slides_detected': len(slides),
                'unique_slides': unique_count,
                'duplicates': duplicate_count,
            },
            'slides': [],
            'deduplication_map': dedup_map,
        }

        for slide in slides:
            slide_data = {
                'filename': slide.path.name,
                'timestamp_seconds': int(slide.timestamp),
                'timestamp_formatted': slide.timestamp_formatted,
                'timestamp_url': f"{video_meta.get('url', '')}&t={int(slide.timestamp)}s",
                'perceptual_hash': slide.perceptual_hash,
                'is_duplicate_of': slide.is_duplicate_of,
                'ocr_text': slide.ocr_text,
                'clip_score': slide.clip_score,
                'transcript_context': slide.transcript_context,
            }
            metadata['slides'].append(slide_data)

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return metadata_path

    def cleanup(self):
        """Remove temporary video file after extraction."""
        video_path = self.output_dir / "video.mp4"
        if video_path.exists():
            video_path.unlink()
            console.print("[dim]Cleaned up video file[/dim]")

    def _cleanup_frames(self):
        """Remove intermediate frame files."""
        if self.frames_dir.exists():
            shutil.rmtree(self.frames_dir)
            console.print("[dim]Cleaned up frame files[/dim]")

    def process(self) -> dict:
        """Execute full slide extraction pipeline."""
        console.print(f"\n[bold blue]Processing: {self.video_id}[/bold blue]")

        video_meta = self._get_video_metadata()
        if video_meta.get('title'):
            console.print(f"[dim]{video_meta['title']}[/dim]")

        # Step 1: Download video
        console.print("\n[cyan]1/8[/cyan] Downloading video...")
        video_path = self.download_video()
        console.print(f"    [green]Done[/green]")

        # Step 2: Extract frames
        console.print("[cyan]2/8[/cyan] Extracting frames...")
        frames = self.extract_frames(video_path)
        console.print(f"    [green]Extracted {len(frames)} frames[/green]")

        # Step 3: Detect scene changes
        console.print("[cyan]3/8[/cyan] Detecting scene changes...")
        candidates = self.detect_scene_changes(frames)
        console.print(f"    [green]Found {len(candidates)} scene changes[/green]")

        # Step 4: Classify slides
        method = "CLIP" if self.config.use_clip else "text-density"
        console.print(f"[cyan]4/8[/cyan] Classifying slides ({method})...")
        slides = self.classify_slides(candidates)
        console.print(f"    [green]Identified {len(slides)} slides[/green]")

        if not slides:
            console.print("[yellow]No slides detected in this video.[/yellow]")
            self._cleanup_frames()
            if not self.config.keep_video:
                self.cleanup()
            return {'video_id': self.video_id, 'slides': [], 'stats': {'slides_detected': 0}}

        # Step 5: Extract OCR text
        console.print("[cyan]5/8[/cyan] Extracting text (OCR)...")
        for slide in slides:
            if not slide.ocr_text:
                slide.ocr_text = self.extract_text(slide)
        console.print(f"    [green]OCR complete[/green]")

        # Step 6: Filter quality (before deduplication)
        console.print("[cyan]6/8[/cyan] Filtering low-quality slides...")
        initial_count = len(slides)
        slides = self.filter_quality(slides)
        filtered_count = initial_count - len(slides)
        if filtered_count > 0:
            console.print(f"    [green]Removed {filtered_count} low-quality slides[/green]")
        else:
            console.print(f"    [green]All slides passed quality check[/green]")

        # Step 7: Deduplicate
        console.print("[cyan]7/8[/cyan] Deduplicating slides...")
        slides = self.deduplicate(slides)
        unique_count = len([s for s in slides if s.is_duplicate_of is None])
        console.print(f"    [green]{len(slides)} slides remaining[/green]")

        # Step 8: Align with transcript
        console.print("[cyan]8/8[/cyan] Aligning with transcript...")
        slides = self.align_timestamps(slides)
        console.print(f"    [green]Alignment complete[/green]")

        # Save final slides
        console.print("\n[cyan]Saving results...[/cyan]")
        for slide in slides:
            new_path = self._save_slide_image(slide)
            slide.path = new_path

        # Save metadata
        metadata_path = self._save_metadata(slides, len(frames), len(candidates))

        # Cleanup
        self._cleanup_frames()
        if not self.config.keep_video:
            self.cleanup()

        console.print(f"[bold green]Complete![/bold green] {len(slides)} slides saved to {self.output_dir}")

        return {
            'video_id': self.video_id,
            'output_dir': str(self.output_dir),
            'metadata_path': str(metadata_path),
            'slides': [{'path': str(s.path), 'timestamp': s.timestamp_formatted} for s in slides],
            'stats': {
                'total_frames': len(frames),
                'scene_changes': len(candidates),
                'slides_detected': len(slides),
                'unique_slides': unique_count,
            }
        }


def check_dependencies() -> dict:
    """Check which dependencies are available."""
    deps = {}

    try:
        import cv2
        deps['opencv'] = cv2.__version__
    except ImportError:
        deps['opencv'] = None

    try:
        import pytesseract
        # Try to actually run tesseract
        try:
            pytesseract.get_tesseract_version()
            deps['pytesseract'] = 'installed'
        except:
            deps['pytesseract'] = 'module only (tesseract not found)'
    except ImportError:
        deps['pytesseract'] = None

    try:
        from PIL import Image
        import PIL
        deps['pillow'] = PIL.__version__
    except ImportError:
        deps['pillow'] = None

    try:
        import imagehash
        deps['imagehash'] = 'installed'
    except ImportError:
        deps['imagehash'] = None

    try:
        from transformers import CLIPModel
        deps['transformers'] = 'installed'
    except ImportError:
        deps['transformers'] = None

    try:
        import torch
        deps['torch'] = torch.__version__
    except ImportError:
        deps['torch'] = None

    # Check for ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        deps['ffmpeg'] = 'installed' if result.returncode == 0 else None
    except FileNotFoundError:
        deps['ffmpeg'] = None

    # Check for tesseract
    try:
        result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
        deps['tesseract'] = 'installed' if result.returncode == 0 else None
    except FileNotFoundError:
        deps['tesseract'] = None

    return deps


def get_status() -> dict:
    """Get extraction status for all videos."""
    metadata_file = KB_DIR / "metadata.json"
    if not metadata_file.exists():
        return {'total': 0, 'extracted': [], 'pending': []}

    with open(metadata_file) as f:
        data = json.load(f)

    videos = data.get('videos', [])
    extracted = []
    pending = []

    for video in videos:
        video_id = video.get('video_id')
        slide_meta = DATA_SLIDES / video_id / "metadata.json"

        if slide_meta.exists():
            with open(slide_meta) as f:
                slide_data = json.load(f)
            extracted.append({
                'video_id': video_id,
                'title': video.get('title', ''),
                'slides_count': slide_data.get('stats', {}).get('slides_detected', 0),
                'unique_count': slide_data.get('stats', {}).get('unique_slides', 0),
            })
        else:
            pending.append({
                'video_id': video_id,
                'title': video.get('title', ''),
                'duration': video.get('duration', 0),
            })

    return {
        'total': len(videos),
        'extracted': extracted,
        'pending': pending,
    }


def _extract_single_video(args: tuple) -> dict:
    """Wrapper for ProcessPoolExecutor (must be top-level for pickling)."""
    video_id, config_dict, keep_video = args
    config = SlideConfig(**config_dict)
    config.keep_video = keep_video
    try:
        extractor = SlideExtractor(video_id, config)
        return {'success': True, 'video_id': video_id, 'result': extractor.process()}
    except Exception as e:
        return {'success': False, 'video_id': video_id, 'error': str(e)}


@click.command()
@click.option('--video', '-v', help='Single video ID to extract slides from')
@click.option('--all', '-a', 'extract_all', is_flag=True, help='Extract from all videos')
@click.option('--status', '-s', is_flag=True, help='Show extraction status')
@click.option('--check', '-c', is_flag=True, help='Check dependencies')
@click.option('--force', '-f', is_flag=True, help='Re-extract even if slides exist')
@click.option('--no-clip', is_flag=True, help='Disable CLIP (use text density)')
@click.option('--keep-video', is_flag=True, help='Keep downloaded video after extraction')
@click.option('--interval', default=2.0, type=float, help='Frame extraction interval in seconds')
@click.option('--workers', '-w', default=4, type=int, help='Number of parallel workers for --all')
@click.option('--add-credit', is_flag=True, help='Add credit overlay to slides')
@click.option('--credit-text', default='', help='Credit text (if not provided, will prompt interactively)')
@click.option('--credit-author', default='', help='Author name (used only if credit-text not provided)')
@click.option('--credit-series', default='', help='Series name (used only if credit-text not provided)')
@click.option('--credit-url', default='', help='Source URL for credit overlay')
@click.option('--non-interactive', is_flag=True, help='Skip interactive prompts (use defaults or CLI args)')
def main(video: str, extract_all: bool, status: bool, check: bool, force: bool,
         no_clip: bool, keep_video: bool, interval: float, workers: int,
         add_credit: bool, credit_text: str, credit_author: str, credit_series: str, credit_url: str,
         non_interactive: bool):
    """Extract slides from YouTube videos."""

    if check:
        console.print("\n[bold]Slide Extraction Dependencies:[/bold]\n")
        deps = check_dependencies()

        required = ['opencv', 'pytesseract', 'pillow', 'imagehash', 'ffmpeg', 'tesseract']
        optional = ['transformers', 'torch']

        console.print("[bold]Required:[/bold]")
        for name in required:
            status_val = deps.get(name)
            if status_val:
                console.print(f"  [green]\u2713[/green] {name}: {status_val}")
            else:
                console.print(f"  [red]\u2717[/red] {name}: not installed")

        console.print("\n[bold]Optional (for CLIP):[/bold]")
        for name in optional:
            status_val = deps.get(name)
            if status_val:
                console.print(f"  [green]\u2713[/green] {name}: {status_val}")
            else:
                console.print(f"  [yellow]-[/yellow] {name}: not installed")

        console.print("\n[bold]Installation:[/bold]")
        console.print("  pip install opencv-python pytesseract Pillow imagehash")
        console.print("  pip install transformers torch  # for CLIP")
        console.print("  brew install tesseract  # macOS")
        console.print("  apt install tesseract-ocr  # Ubuntu")
        return

    if status:
        status_data = get_status()

        console.print(f"\n[bold]Slide Extraction Status[/bold]")
        console.print(f"Total videos: {status_data['total']}")
        console.print(f"Extracted: {len(status_data['extracted'])}")
        console.print(f"Pending: {len(status_data['pending'])}")

        if status_data['extracted']:
            console.print("\n[bold green]Extracted:[/bold green]")
            table = Table(show_header=True)
            table.add_column("Video ID", style="cyan")
            table.add_column("Slides")
            table.add_column("Unique")
            table.add_column("Title", max_width=50)

            for item in status_data['extracted']:
                table.add_row(
                    item['video_id'],
                    str(item['slides_count']),
                    str(item['unique_count']),
                    item['title'][:50]
                )
            console.print(table)

        if status_data['pending']:
            console.print("\n[bold yellow]Pending:[/bold yellow]")
            table = Table(show_header=True)
            table.add_column("Video ID", style="cyan")
            table.add_column("Duration")
            table.add_column("Title", max_width=50)

            for item in status_data['pending'][:10]:  # Show first 10
                duration_min = item['duration'] // 60
                table.add_row(
                    item['video_id'],
                    f"{duration_min}m",
                    item['title'][:50]
                )
            console.print(table)

            if len(status_data['pending']) > 10:
                console.print(f"  ... and {len(status_data['pending']) - 10} more")

        return

    # Interactive credit text prompt (if add_credit is enabled and text not provided)
    final_credit_text = credit_text
    
    if add_credit and not final_credit_text and not non_interactive:
        console.print(Panel(
            "[bold]Credit Overlay Configuration[/bold]\n\n"
            "Enter the exact text you want displayed in the credit bar at the bottom of each slide.\n"
            "This text will appear on all slides for this video.\n\n"
            "Examples:\n"
            "  • Scott Hebner • The Next Frontiers of AI\n"
            "  • Source: YouTube Video\n"
            "  • © 2025 The Cube Research\n"
            "  • [Your custom attribution text here]",
            title="Credit Text",
            border_style="blue"
        ))
        
        final_credit_text = Prompt.ask(
            "\n[bold]Enter credit text[/bold]",
            default="",
            show_default=False
        ).strip()
        
        if not final_credit_text:
            console.print("[yellow]No credit text provided. Disabling credit overlay.[/yellow]")
            add_credit = False
        else:
            # Show preview
            console.print(f"\n[dim]Preview:[/dim] [bold]{final_credit_text}[/bold]")
            if not Confirm.ask("\nUse this credit text?", default=True):
                console.print("[yellow]Credit overlay disabled.[/yellow]")
                add_credit = False
                final_credit_text = ""
    
    elif add_credit and not final_credit_text and non_interactive:
        # Non-interactive mode: use defaults or auto-generate
        if credit_author or credit_series:
            parts = []
            if credit_author:
                parts.append(credit_author)
            if credit_series:
                parts.append(credit_series)
            final_credit_text = " • ".join(parts) if parts else ""
        if not final_credit_text:
            console.print("[yellow]No credit text provided and non-interactive mode. Disabling credit overlay.[/yellow]")
            add_credit = False

    # Build config
    config = SlideConfig(
        frame_interval=interval,
        use_clip=not no_clip,
        keep_video=keep_video,
        add_credit=add_credit,
        credit_text=final_credit_text,
        credit_author=credit_author,
        credit_series=credit_series,
        credit_url=credit_url,
    )

    if video:
        # Single video extraction
        slide_meta = DATA_SLIDES / video / "metadata.json"
        if slide_meta.exists() and not force:
            console.print(f"[yellow]Slides already extracted for {video}. Use --force to re-extract.[/yellow]")
            return

        extractor = SlideExtractor(video, config)
        result = extractor.process()

        console.print(f"\n[bold]Results for {video}:[/bold]")
        console.print(f"  Slides: {result['stats']['slides_detected']}")
        console.print(f"  Unique: {result['stats']['unique_slides']}")
        console.print(f"  Output: {result.get('output_dir', 'N/A')}")

    elif extract_all:
        # Batch extraction
        status_data = get_status()
        pending = status_data['pending']

        if not pending:
            console.print("[green]All videos have been processed![/green]")
            return

        if not force:
            console.print(f"[bold]Processing {len(pending)} pending videos...[/bold]")
        else:
            # If force, process all videos
            metadata_file = KB_DIR / "metadata.json"
            with open(metadata_file) as f:
                data = json.load(f)
            pending = [{'video_id': v['video_id'], 'title': v.get('title', '')}
                       for v in data.get('videos', [])]
            console.print(f"[bold]Force processing all {len(pending)} videos...[/bold]")

        results = []
        errors = []

        # Prepare args for parallel execution
        config_dict = asdict(config)
        task_args = [(item['video_id'], config_dict, keep_video) for item in pending]

        # Determine actual worker count
        actual_workers = min(workers, len(pending), multiprocessing.cpu_count())
        console.print(f"[dim]Using {actual_workers} parallel workers[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Extracting slides...", total=len(pending))

            with ProcessPoolExecutor(max_workers=actual_workers) as executor:
                futures = {executor.submit(_extract_single_video, args): args[0]
                           for args in task_args}

                for future in as_completed(futures):
                    video_id = futures[future]
                    progress.update(task, description=f"Completed {video_id}")

                    result = future.result()
                    if result['success']:
                        results.append(result['result'])
                    else:
                        console.print(f"[red]Error: {result['video_id']}: {result['error']}[/red]")
                        errors.append({'video_id': result['video_id'], 'error': result['error']})

                    progress.advance(task)

        # Summary
        console.print(f"\n[bold]Batch Processing Complete[/bold]")
        console.print(f"  Successful: {len(results)}")
        console.print(f"  Errors: {len(errors)}")

        total_slides = sum(r['stats']['slides_detected'] for r in results)
        total_unique = sum(r['stats']['unique_slides'] for r in results)
        console.print(f"  Total slides: {total_slides}")
        console.print(f"  Total unique: {total_unique}")

        if errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for err in errors:
                console.print(f"  {err['video_id']}: {err['error']}")

    else:
        console.print("[yellow]Please specify --video VIDEO_ID or --all[/yellow]")
        console.print("Run with --help for usage information.")


if __name__ == '__main__':
    main()
