import os
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFilter
import numpy as np


def create_synthetic_fixtures(output_dir: str = "ml/tests/fixtures"):
    """Creates synthetic image test fixtures to test the OpenCV quality gate:
    1. good_photo.jpg: sharp focus, proper exposure, centered fish silhouette
    2. blurry_photo.jpg: low Laplacian variance via heavy Gaussian blur
    3. dark_photo.jpg: severely underexposed
    4. far_framed_photo.jpg: tiny subject occupying < 5% of pixels
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Good Photo (sharp high-contrast fish shape on pond water background)
    img_good = Image.new("RGB", (640, 480), color=(30, 80, 110))
    draw = ImageDraw.Draw(img_good)
    # Draw high-contrast fish body
    draw.ellipse([150, 160, 490, 320], fill=(210, 180, 140), outline=(50, 30, 20), width=4)
    # Fish tail & fins
    draw.polygon([(150, 240), (80, 170), (80, 310)], fill=(190, 160, 120))
    # Scales pattern for edge sharpness
    for x in range(220, 420, 20):
        for y in range(190, 290, 20):
            draw.arc([x, y, x + 25, y + 25], 0, 180, fill=(40, 30, 20), width=2)
    img_good.save(out_path / "good_photo.jpg")

    # 2. Blurry Photo (heavily blurred version of the good photo)
    img_blurry = img_good.filter(ImageFilter.GaussianBlur(radius=15))
    img_blurry.save(out_path / "blurry_photo.jpg")

    # 3. Dark Photo (severely underexposed mean intensity)
    img_dark = Image.new("RGB", (640, 480), color=(10, 12, 15))
    draw_dark = ImageDraw.Draw(img_dark)
    draw_dark.ellipse([150, 160, 490, 320], fill=(25, 20, 18))
    img_dark.save(out_path / "dark_photo.jpg")

    # 4. Far / Poorly Framed Photo (subject is a tiny dot)
    img_far = Image.new("RGB", (640, 480), color=(40, 90, 120))
    draw_far = ImageDraw.Draw(img_far)
    draw_far.ellipse([300, 230, 320, 245], fill=(200, 180, 140))
    img_far.save(out_path / "far_framed_photo.jpg")

    print(f"Test fixtures successfully generated in: {out_path}")


if __name__ == "__main__":
    create_synthetic_fixtures()
