import unittest
from pathlib import Path
from ml.photo_gate import PhotoQualityGate
from ml.tests.generate_fixtures import create_synthetic_fixtures


class TestPhotoQualityGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = Path("ml/tests/fixtures")
        create_synthetic_fixtures(str(cls.fixture_dir))
        cls.gate = PhotoQualityGate(
            blur_laplacian_threshold=65.0,
            underexposed_mean_threshold=40.0,
            min_foreground_ratio=0.10,
        )

    def test_good_photo_passes_gate(self):
        with open(self.fixture_dir / "good_photo.jpg", "rb") as f:
            res = self.gate.evaluate_image(f.read())
        self.assertTrue(res["passed"])
        self.assertEqual(len(res["reasons"]), 0)

    def test_blurry_photo_fails_with_retake_tip(self):
        with open(self.fixture_dir / "blurry_photo.jpg", "rb") as f:
            res = self.gate.evaluate_image(f.read())
        self.assertFalse(res["passed"])
        self.assertIn("PHOTO_BLURRY", res["reasons"])
        # Ensures bilingual retake prompt exists
        self.assertTrue(any("focus" in tip.lower() for tip in res["tips_en"]))
        self.assertTrue(any("ಫೋಕಸ್" in tip for tip in res["tips_kn"]))

    def test_dark_photo_fails_with_lighting_tip(self):
        with open(self.fixture_dir / "dark_photo.jpg", "rb") as f:
            res = self.gate.evaluate_image(f.read())
        self.assertFalse(res["passed"])
        self.assertIn("PHOTO_TOO_DARK", res["reasons"])
        self.assertTrue(any("daylight" in tip.lower() or "torch" in tip.lower() for tip in res["tips_en"]))

    def test_poorly_framed_photo_fails(self):
        with open(self.fixture_dir / "far_framed_photo.jpg", "rb") as f:
            res = self.gate.evaluate_image(f.read())
        self.assertFalse(res["passed"])
        self.assertIn("SUBJECT_TOO_FAR_OR_POORLY_FRAMED", res["reasons"])


if __name__ == "__main__":
    unittest.main()
