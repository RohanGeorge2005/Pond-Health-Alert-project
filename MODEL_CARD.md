# Model Card: Fish Disease Advisory Vision Classifier

## Model Details
- **Architecture:** Pretrained EfficientNet-B0 / MobileNetV3 backbone fine-tuned for South Asian freshwater fish aquaculture.
- **Serving Format:** Exported ONNX graph served via ONNX Runtime for lightweight CPU deployment.
- **Input:** 224x224 RGB image, normalized with ImageNet mean and standard deviation.
- **Output:** Class probability distribution across 7 conditions + Grad-CAM saliency heatmaps.

---

## Intended Use & Advisory Limits
- **Intended Use:** Field screening tool for rural smallholder fish farmers in coastal Karnataka.
- **Strict Limitation:** **Advisory tool only.** Never a clinical diagnosis. The system instructs the farmer to confirm findings with a Taluk Fisheries Extension Officer before applying any chemical, probiotic, or antibiotic treatments.

---

## Quality Gate (Pre-Inference)
All incoming photos must pass an OpenCV quality filter before reaching the model:
1. **Variance of Laplacian:** Blur detection (threshold: 65.0).
2. **Mean Luminance:** Underexposed (<40.0) or overexposed (>220.0) images are rejected.
3. **Framing Ratio:** Otsu contour foreground ratio must exceed 12% of the frame.

Photos failing any quality metric receive immediate retake tips and **never receive a green health status**.

---

## Confidence Thresholding
Predictions with confidence below **0.65** are flagged as `UNCERTAIN_PHOTO_PREDICTION` and cannot upgrade a pond to Green status.
