import os
import io
import time
import cv2
import numpy as np
from typing import Dict, Any, Tuple, List


class PhotoQualityGate:
    """Fast OpenCV-based quality gate executed before any ML inference.
    Checks:
    1. Blur estimation via Variance of Laplacian
    2. Brightness / exposure distribution via grayscale histogram
    3. Foreground / framing ratio using Otsu / adaptive contour segmentation
    """

    def __init__(
        self,
        blur_laplacian_threshold: float = 65.0,
        underexposed_mean_threshold: float = 40.0,
        overexposed_mean_threshold: float = 220.0,
        min_foreground_ratio: float = 0.12,  # Fish subject must cover at least 12% of frame
    ):
        self.blur_threshold = blur_laplacian_threshold
        self.underexposed_threshold = underexposed_mean_threshold
        self.overexposed_threshold = overexposed_mean_threshold
        self.min_foreground_ratio = min_foreground_ratio

    def evaluate_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Runs the quality checks on input image bytes.
        Returns:
            {
                "passed": bool,
                "reasons": list[str],
                "metrics": dict,
                "tips_en": list[str],
                "tips_kn": list[str],
            }
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {
                "passed": False,
                "reasons": ["CORRUPT_OR_UNREADABLE_IMAGE"],
                "metrics": {},
                "tips_en": ["Please take a clear photo of the fish."],
                "tips_kn": ["ದಯವಿಟ್ಟು ಮೀನಿನ ಸ್ಪಷ್ಟ ಫೋಟೋ ತೆಗೆಯಿರಿ."],
            }

        # Convert to grayscale for blur and exposure checks
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Blur Detection (Variance of Laplacian)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry = laplacian_var < self.blur_threshold

        # 2. Exposure / Brightness (Mean pixel intensity and histogram)
        mean_brightness = float(np.mean(gray))
        is_dark = mean_brightness < self.underexposed_threshold
        is_washed_out = mean_brightness > self.overexposed_threshold

        # 3. Framing / Foreground Ratio
        # Apply slight Gaussian blur then Otsu thresholding to find main fish contours
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        foreground_pixels = np.count_nonzero(thresh)
        total_pixels = gray.shape[0] * gray.shape[1]
        foreground_ratio = float(foreground_pixels / max(1, total_pixels))
        is_badly_framed = foreground_ratio < self.min_foreground_ratio

        reasons = []
        tips_en = []
        tips_kn = []

        if is_blurry:
            reasons.append("PHOTO_BLURRY")
            tips_en.append("Hold phone steady and tap screen to focus on the fish.")
            tips_kn.append("ಫೋನ್ ಅಲುಗಾಡದಂತೆ ಹಿಡಿದು ಮೀನಿನ ಮೇಲೆ ಫೋಕಸ್ ಮಾಡಿ.")

        if is_dark:
            reasons.append("PHOTO_TOO_DARK")
            tips_en.append("Move to brighter natural daylight or turn on torch.")
            tips_kn.append("ಹೆಚ್ಚು ಬೆಳಕಿರುವ ಜಾಗದಲ್ಲಿ ಅಥವಾ ಟಾರ್ಚ್ ಬೆಳಗಿಸಿ ಫೋಟೋ ತೆಗೆಯಿರಿ.")

        if is_washed_out:
            reasons.append("PHOTO_OVEREXPOSED")
            tips_en.append("Avoid direct harsh sunlight or glare reflecting off the water.")
            tips_kn.append("ನೀರಿನಿಂದ ನೇರ ಸೂರ್ಯನ ಬೆಳಕು ಪ್ರತಿಫಲಿಸುವುದನ್ನು ತಪ್ಪಿಸಿ.")

        if is_badly_framed:
            reasons.append("SUBJECT_TOO_FAR_OR_POORLY_FRAMED")
            tips_en.append("Bring the camera closer to the fish inside the framing guide.")
            tips_kn.append("ಕ್ಯಾಮೆರಾವನ್ನು ಮೀನಿಗೆ ಹತ್ತಿರ ತಂದು ಫ್ರೇಮ್‌ನಲ್ಲಿ ಇರಿಸಿ.")

        passed = len(reasons) == 0

        return {
            "passed": passed,
            "reasons": reasons,
            "metrics": {
                "blur_laplacian_variance": round(laplacian_var, 2),
                "mean_brightness": round(mean_brightness, 2),
                "foreground_ratio": round(foreground_ratio, 3),
                "resolution": f"{img.shape[1]}x{img.shape[0]}",
            },
            "tips_en": tips_en if not passed else ["Photo quality is good for advisory check."],
            "tips_kn": tips_kn if not passed else ["ಸಲಹಾ ತಪಾಸಣೆಗೆ ಫೋಟೋ ಗುಣಮಟ್ಟ ಉತ್ತಮವಾಗಿದೆ."],
        }
