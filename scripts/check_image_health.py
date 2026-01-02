#!/usr/bin/env python3
"""
Check PNG images for potential upload issues to NotebookLM.

Identifies:
- Corrupted images
- Unusually large files
- Non-standard formats
- Files that might need re-encoding
"""

import sys
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

PROJECT_ROOT = Path(__file__).parent.parent
SLIDE_IMAGES_DIR = PROJECT_ROOT / "notebooks" / "notebooklm-staging" / "03_Slide_Images"

# NotebookLM limits (approximate)
MAX_FILE_SIZE_MB = 10  # Conservative limit
MAX_DIMENSION = 5000  # Max width or height
RECOMMENDED_DIMENSION = 2000  # Recommended max for better processing


def check_image(image_path: Path) -> dict:
    """Check a single image for potential issues."""
    result = {
        "path": image_path.name,
        "valid": False,
        "issues": [],
        "size_mb": 0,
        "dimensions": None,
        "format": None,
    }
    
    try:
        # Check file size
        file_size = image_path.stat().st_size
        result["size_mb"] = file_size / (1024 * 1024)
        
        if result["size_mb"] > MAX_FILE_SIZE_MB:
            result["issues"].append(f"File too large: {result['size_mb']:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
        
        if HAS_PIL:
            # Try to open and validate image
            with Image.open(image_path) as img:
                result["valid"] = True
                result["dimensions"] = img.size
                result["format"] = img.format
                
                # Check dimensions
                width, height = img.size
                if width > MAX_DIMENSION or height > MAX_DIMENSION:
                    result["issues"].append(
                        f"Dimensions too large: {width}x{height} (max: {MAX_DIMENSION}x{MAX_DIMENSION})"
                    )
                elif width > RECOMMENDED_DIMENSION or height > RECOMMENDED_DIMENSION:
                    result["issues"].append(
                        f"Large dimensions: {width}x{height} (recommended max: {RECOMMENDED_DIMENSION})"
                    )
                
                # Verify it's actually a PNG
                if img.format != "PNG":
                    result["issues"].append(f"Format is {img.format}, not PNG")
                
                # Try to load image data (catches corruption)
                img.load()
        else:
            # Basic check without PIL - just file size
            result["valid"] = True
            if result["size_mb"] > MAX_FILE_SIZE_MB:
                result["valid"] = False
            
    except Exception as e:
        result["valid"] = False
        result["issues"].append(f"Error reading image: {str(e)}")
    
    return result


def check_all_images():
    """Check all images in the slide images directory."""
    if not SLIDE_IMAGES_DIR.exists():
        print(f"Error: Directory not found: {SLIDE_IMAGES_DIR}")
        return
    
    image_files = sorted(SLIDE_IMAGES_DIR.glob("*.png"))
    
    if not image_files:
        print("No PNG files found in slide images directory.")
        return
    
    print(f"Checking {len(image_files)} images...\n")
    
    results = []
    for image_path in image_files:
        result = check_image(image_path)
        results.append(result)
    
    # Categorize results
    valid_images = [r for r in results if r["valid"] and not r["issues"]]
    problematic_images = [r for r in results if not r["valid"] or r["issues"]]
    large_images = [r for r in results if r["size_mb"] > 5]
    
    # Print summary
    print("=" * 60)
    print("IMAGE HEALTH CHECK SUMMARY")
    print("=" * 60)
    print(f"Total images: {len(results)}")
    print(f"✅ Valid images: {len(valid_images)}")
    print(f"⚠️  Problematic images: {len(problematic_images)}")
    print(f"📦 Large images (>5MB): {len(large_images)}")
    print()
    
    # Show problematic images
    if problematic_images:
        print("⚠️  PROBLEMATIC IMAGES:")
        print("-" * 60)
        for result in problematic_images:
            print(f"\n{result['path']}")
            print(f"  Size: {result['size_mb']:.2f}MB")
            if result['dimensions']:
                print(f"  Dimensions: {result['dimensions'][0]}x{result['dimensions'][1]}")
            for issue in result['issues']:
                print(f"  ⚠️  {issue}")
    
    # Show large images
    if large_images:
        print("\n📦 LARGE IMAGES (>5MB):")
        print("-" * 60)
        for result in sorted(large_images, key=lambda x: x['size_mb'], reverse=True):
            print(f"  {result['path']}: {result['size_mb']:.2f}MB")
    
    # Generate retry list
    if problematic_images:
        print("\n" + "=" * 60)
        print("RETRY LIST (copy these filenames):")
        print("=" * 60)
        for result in problematic_images:
            print(result['path'])
    
    return problematic_images


if __name__ == "__main__":
    if not HAS_PIL:
        print("⚠️  PIL (Pillow) not installed - running basic checks only")
        print("   Install with: pip install Pillow (for full image validation)")
        print()
    
    check_all_images()

