# Demonstration Walkthrough Script: Pond Health Alert (PS 1.1)

**Target Audience:** Coastal Karnataka Fisheries Field Evaluators & Farmers
**Demo Duration:** 3 Minutes

---

## 1. Sequence 1: Baseline Optimal Pond (Green Status)
- **Action:** Open application at `/`.
- **Observation:**
  - Notice the bilingual Kannada/English toggle in the top bar.
  - Prominent banner: *"Demo uses public & simulated data"*.
  - Large High-Contrast Card: **GREEN - OPTIMAL** (`OPTIMAL_WATER_QUALITY`).
  - Press the **"Read aloud" (ಧ್ವನಿಯಲ್ಲಿ ಕೇಳಿ)** button: plays spoken Kannada audio advisory.

---

## 2. Sequence 2: Impending Hypoxia Warning via 7-Day Trend (Amber Status)
- **Action:** Select demo scenario: *Falling Dissolved Oxygen Trend*.
- **Observation:**
  - DO is currently 5.2 mg/L (technically still within the >5.0 green threshold!).
  - **Early Warning Trigger:** The 7-day linear regression slope detects DO dropping by -0.32 mg/L/day and projects breach within 1.5 days.
  - Card turns **AMBER - CAUTION** (`FALLING_DO_TREND`).
  - Notice the advice: *"Prepare backup aeration before DO falls below safe threshold"*. Proves early intervention before a fish kill occurs.

---

## 3. Sequence 3: Oxygen Crash + Fish Mortality (Red Status)
- **Action:** Simulate nocturnal algae crash: DO drops to 2.1 mg/L and Daily Check reports 4 dead fish.
- **Observation:**
  - Card turns **RED - CRITICAL** (`CRITICAL_LOW_DO + AMBER_WITH_RISING_MORTALITY`).
  - Reason code displayed prominently in plain Kannada & English.
  - Immediate actions checklist: *"Start all aerators immediately and halt feeding"*.

---

## 4. Sequence 4: Sensor Dropout & Stale Data (Can't Tell Status - Never False Green)
- **Action:** Simulate sensor battery death (no data transmitted for 50 hours).
- **Observation:**
  - The system **NEVER displays a false green**.
  - Status immediately flips to **CAN'T TELL** (`STALE_DATA`).
  - Plain language reason: *"Water data is 50.0 hours old (limit 48h). Fresh readings required."*

---

## 5. Sequence 5: Photo Quality Gate & Advisory Retake
- **Action:** Upload a blurry camera capture of a carp.
- **Observation:**
  - The OpenCV Quality Gate intercepts the image before model inference.
  - Rejection: `PHOTO_BLURRY` (Laplacian variance low).
  - Screen displays framing tips in Kannada: *"ಫೋನ್ ಅಲುಗಾಡದಂತೆ ಹಿಡಿದು ಮೀನಿನ ಮೇಲೆ ಫೋಕಸ್ ಮಾಡಿ."*
