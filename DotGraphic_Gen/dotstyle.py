from PIL import Image, ImageDraw


def convert_to_dot_style(input_path: str, output_path: str, dot_size: int = 8, palette_colors: int = 32) -> None:
    """Convert an image to a dot‑style (pixel‑art) version.

    Args:
        input_path (str): Path to the source image.
        output_path (str): Where to save the dot‑style image.
        dot_size (int, optional): Approximate diameter of each dot/pixel in the
            final image. Larger values produce chunkier dots. Defaults to 8.
        palette_colors (int, optional): Number of colors to keep after palette
            reduction. Fewer colors give a more stylised, retro look. Defaults to 32.
    """
    # --- Load and normalise image ---
    img = Image.open(input_path).convert("RGB")

    # --- 1) Pixelate: down‑sample then up‑sample with NEAREST filter ---
    small_w = max(1, img.width // dot_size)
    small_h = max(1, img.height // dot_size)
    small = img.resize((small_w, small_h), Image.NEAREST)
    pixelated = small.resize(img.size, Image.NEAREST)

    # --- 2) Optional palette reduction for a cleaner 8‑bit look ---
    reduced = pixelated.convert("P", palette=Image.ADAPTIVE, colors=palette_colors)
    pixelated = reduced.convert("RGB")

    # --- 3) Draw circular "dots" to soften square pixels ---
    dot_img = Image.new("RGB", img.size, (0, 0, 0))
    draw = ImageDraw.Draw(dot_img)

    step = dot_size
    radius = step // 2

    for y in range(0, img.height, step):
        for x in range(0, img.width, step):
            color = pixelated.getpixel((x, y))
            cx, cy = x + radius, y + radius
            bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
            draw.ellipse(bbox, fill=color, outline=None)

    # --- 4) Save result ---
    dot_img.save(output_path)


if __name__ == "__main__":
    # Example usage:
    #   python dot_style_conversion.py input.png output_dot.png 10 16

    import sys

    if len(sys.argv) < 3:
        print("Usage: python dot_style_conversion.py <input> <output> [dot_size] [palette_colors]")
        sys.exit(1)

    inp, out = sys.argv[1:3]
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    colors = int(sys.argv[4]) if len(sys.argv) > 4 else 32

    convert_to_dot_style(inp, out, size, colors)

