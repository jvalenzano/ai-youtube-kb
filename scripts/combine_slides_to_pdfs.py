#!/usr/bin/env python3
"""
Combine slide images into PDFs, one PDF per video.

Groups all slide images by video ID and creates a single PDF for each video.
This reduces source count from 119 individual images to ~27 PDFs.
"""

import sys
from pathlib import Path
from collections import defaultdict

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Error: PIL (Pillow) is required for this script.")
    print("Install with: pip install Pillow")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
SLIDE_IMAGES_DIR = PROJECT_ROOT / "notebooks" / "notebooklm-staging" / "03_Slide_Images"
OUTPUT_DIR = PROJECT_ROOT / "notebooks" / "notebooklm-staging" / "06_Slide_PDFs"


def extract_video_id(filename: str) -> str:
    """Extract video ID from filename (part before _slide_)."""
    if "_slide_" in filename:
        return filename.split("_slide_")[0]
    return filename.split(".")[0]  # Fallback if no _slide_


def combine_images_to_pdf(image_paths: list[Path], output_pdf: Path):
    """Combine multiple images into a single PDF."""
    if not image_paths:
        print(f"  ⚠️  No images to combine for {output_pdf.name}")
        return False
    
    # Sort images by timestamp in filename (for proper order)
    def get_timestamp(filename: str) -> str:
        if "_slide_" in filename:
            try:
                # Extract timestamp like "14m56s" or "1m54s"
                timestamp_part = filename.split("_slide_")[1].split(".")[0]
                return timestamp_part
            except:
                return filename
        return filename
    
    image_paths.sort(key=lambda p: get_timestamp(p.name))
    
    try:
        # Open all images
        images = []
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                # Convert to RGB if necessary (PDFs don't support RGBA)
                if img.mode == 'RGBA':
                    # Create white background
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
                    images.append(rgb_img)
                elif img.mode != 'RGB':
                    images.append(img.convert('RGB'))
                else:
                    images.append(img)
            except Exception as e:
                print(f"  ⚠️  Error opening {img_path.name}: {e}")
                continue
        
        if not images:
            print(f"  ⚠️  No valid images to combine for {output_pdf.name}")
            return False
        
        # Save as PDF
        if len(images) == 1:
            images[0].save(output_pdf, "PDF", resolution=100.0)
        else:
            images[0].save(
                output_pdf,
                "PDF",
                resolution=100.0,
                save_all=True,
                append_images=images[1:]
            )
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating PDF {output_pdf.name}: {e}")
        return False


def main():
    """Main function to combine slides into PDFs."""
    if not SLIDE_IMAGES_DIR.exists():
        print(f"Error: Slide images directory not found: {SLIDE_IMAGES_DIR}")
        sys.exit(1)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    # Group images by video ID
    video_groups = defaultdict(list)
    
    image_files = sorted(SLIDE_IMAGES_DIR.glob("*.png"))
    
    if not image_files:
        print("No PNG files found in slide images directory.")
        sys.exit(1)
    
    print(f"Found {len(image_files)} slide images\n")
    
    # Group by video ID
    for img_path in image_files:
        video_id = extract_video_id(img_path.name)
        video_groups[video_id].append(img_path)
    
    print(f"Grouped into {len(video_groups)} videos\n")
    print("=" * 60)
    print("Creating PDFs...")
    print("=" * 60)
    
    # Create PDF for each video
    success_count = 0
    failed_count = 0
    
    for video_id, image_paths in sorted(video_groups.items()):
        slide_count = len(image_paths)
        pdf_filename = f"{video_id}_slides.pdf"
        output_pdf = OUTPUT_DIR / pdf_filename
        
        print(f"\n{video_id}:")
        print(f"  {slide_count} slide(s)")
        print(f"  → {pdf_filename}")
        
        if combine_images_to_pdf(image_paths, output_pdf):
            # Get file size
            size_mb = output_pdf.stat().st_size / (1024 * 1024)
            print(f"  ✅ Created ({size_mb:.2f} MB)")
            success_count += 1
        else:
            print(f"  ❌ Failed")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total videos: {len(video_groups)}")
    print(f"✅ PDFs created: {success_count}")
    print(f"❌ PDFs failed: {failed_count}")
    print(f"\nSource reduction:")
    print(f"  Before: {len(image_files)} individual images")
    print(f"  After: {success_count} PDF files")
    print(f"  Reduction: {len(image_files) - success_count} fewer sources!")
    print(f"\nPDFs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

