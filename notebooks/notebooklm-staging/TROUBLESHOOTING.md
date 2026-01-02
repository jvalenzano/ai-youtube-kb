# NotebookLM Upload Troubleshooting Guide

## Image Upload Issues

### "Image content is not supported" Error

**What it means:**
NotebookLM may reject images that are:
- Corrupted or invalid PNG files
- Too large (file size or dimensions)
- In an unsupported format
- Have encoding issues

### How to Retry Failed Images

#### Option 1: Individual Retry (Recommended)

1. **Identify failed images**:
   - Look for red error indicators in NotebookLM's source list
   - Note the filenames that failed

2. **Remove failed sources** (if they appear in the list):
   - Click the "X" or remove button on failed images
   - This clears the error state

3. **Retry one at a time**:
   - Drag and drop individual PNG files
   - Wait for each to process before trying the next
   - This helps identify which specific images are problematic

#### Option 2: Small Batch Retry

1. **Group failed images** (5-10 at a time)
2. **Upload in small batches**
3. **Wait for processing** between batches
4. **Note which ones fail** to identify patterns

#### Option 3: Check and Fix Images First

1. **Run the health check script**:
   ```bash
   cd /Users/jvalenzano/Projects/the-cube/yt-agents-kb
   python3 scripts/check_image_health.py
   ```

2. **Review problematic images**:
   - Script will list images with issues
   - Check file sizes and dimensions

3. **Re-encode if needed** (see below)

### Best Practices for Image Uploads

#### Upload Strategy

1. **Start with transcripts first** (already done ✅)
   - This gives NotebookLM context
   - Images work better when there's related text

2. **Upload images in smaller batches**:
   - 10-20 images at a time
   - Wait for processing to complete
   - Reduces timeout/error risk

3. **Upload related images together**:
   - All slides from the same video
   - Helps NotebookLM understand relationships

4. **Monitor upload progress**:
   - Watch for error indicators
   - Remove failed uploads immediately
   - Retry individually

#### File Size Guidelines

- **Recommended**: Under 5MB per image
- **Maximum**: ~10MB (may cause issues)
- **Dimensions**: Under 2000x2000px recommended
- **Format**: PNG (8-bit RGB, non-interlaced)

### Fixing Problematic Images

#### If Images Are Too Large

**Option A: Re-encode with compression** (keeps quality):
```bash
# Install ImageMagick if needed: brew install imagemagick
cd /Users/jvalenzano/Projects/the-cube/yt-agents-kb/notebooks/notebooklm-staging/03_Slide_Images

# Re-encode a single image (replace FILENAME)
mogrify -quality 85 -strip FILENAME.png

# Or re-encode all large images
for img in *.png; do
  size=$(stat -f%z "$img")
  if [ $size -gt 5000000 ]; then  # 5MB
    mogrify -quality 85 -strip "$img"
    echo "Re-encoded: $img"
  fi
done
```

**Option B: Resize if dimensions are too large**:
```bash
# Resize to max 2000px width (maintains aspect ratio)
mogrify -resize 2000x2000\> FILENAME.png
```

#### If Images Are Corrupted

1. **Check with the health check script**:
   ```bash
   python3 scripts/check_image_health.py
   ```

2. **Try opening in an image viewer**:
   - If it won't open, the file is corrupted
   - You may need to re-extract from source

3. **Re-encode to fix minor corruption**:
   ```bash
   # This often fixes minor encoding issues
   convert INPUT.png -strip OUTPUT.png
   ```

### Common Issues and Solutions

#### Issue: "Image content is not supported"
- **Cause**: Corrupted file, wrong format, or too large
- **Solution**: Check file health, re-encode if needed, try individual upload

#### Issue: Upload times out
- **Cause**: File too large or network issues
- **Solution**: Upload in smaller batches, check file sizes

#### Issue: Some images work, others don't
- **Cause**: Specific files have issues
- **Solution**: Check individual files, compare working vs non-working

#### Issue: Images upload but don't appear
- **Cause**: Processing still in progress
- **Solution**: Wait a few minutes, refresh the page

### Recommended Workflow

1. **Upload transcripts first** ✅ (already done)
2. **Generate initial summary** (gives context)
3. **Upload images in batches of 10-20**:
   - Start with one video's slides
   - Wait for processing
   - Move to next video
4. **Monitor for errors**:
   - Check source list regularly
   - Remove failed uploads
   - Retry individually
5. **Upload companion files last** (optional)

### Quick Checklist

- [ ] Check image health with script
- [ ] Upload in small batches (10-20 images)
- [ ] Wait for processing between batches
- [ ] Remove failed uploads immediately
- [ ] Retry failed images individually
- [ ] Re-encode large/corrupted images if needed
- [ ] Don't upload all 119 images at once

### Getting Help

If images continue to fail:
1. Note the specific filenames that fail
2. Check file sizes and dimensions
3. Try opening in an image viewer
4. Re-encode problematic images
5. Contact NotebookLM support if issue persists

---

**Remember**: It's better to upload successfully in smaller batches than to have many failures from bulk uploads.

