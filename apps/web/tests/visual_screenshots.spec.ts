import { test, expect } from "@playwright/test";

// Test matrix across viewports and languages
const viewports = [
  { name: "360px", width: 360, height: 740 },
  { name: "390px", width: 390, height: 844 }, // Requested iPhone 12/13/14 viewport
  { name: "768px", width: 768, height: 1024 }, // Tablet viewport
];

const languages = [
  { code: "en", label: "English" },
  { code: "kn", label: "Kannada" },
];

const tabs = ["home", "readings", "daily", "photo", "impact"];

for (const vp of viewports) {
  for (const lang of languages) {
    test.describe(`${vp.name} - ${lang.label}`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test(`Capture all screens in ${lang.label} at ${vp.name}`, async ({ page }) => {
        await page.goto("http://localhost:5173");

        // Switch language using the segmented button
        const langBtn = page.getByRole("button", { name: lang.code === "en" ? "English" : "ಕನ್ನಡ" });
        await langBtn.click();
        await page.waitForTimeout(200);

        // Screen 1: Status (Home)
        await page.screenshot({
          path: `docs/screenshots/${vp.name}_${lang.code}_1_status.png`,
          fullPage: true,
        });

        // Screen 2: Readings
        await page.getByRole("button", { name: lang.code === "en" ? "Readings" : "ಮಾಪನ" }).click();
        await page.waitForTimeout(200);
        await page.screenshot({
          path: `docs/screenshots/${vp.name}_${lang.code}_2_readings.png`,
          fullPage: true,
        });

        // Screen 3: Daily Check
        await page.getByRole("button", { name: lang.code === "en" ? "Check" : "ಪರಿಶೀಲನೆ" }).click();
        await page.waitForTimeout(200);
        await page.screenshot({
          path: `docs/screenshots/${vp.name}_${lang.code}_3_daily_check.png`,
          fullPage: true,
        });

        // Screen 4: Photo Advisory
        await page.getByRole("button", { name: lang.code === "en" ? "Photo" : "ಫೋಟೋ" }).click();
        await page.waitForTimeout(200);
        await page.screenshot({
          path: `docs/screenshots/${vp.name}_${lang.code}_4_photo.png`,
          fullPage: true,
        });

        // Screen 5: Impact Evaluation
        await page.getByRole("button", { name: lang.code === "en" ? "Impact" : "ಪ್ರಭಾವ" }).click();
        await page.waitForTimeout(200);
        await page.screenshot({
          path: `docs/screenshots/${vp.name}_${lang.code}_5_impact.png`,
          fullPage: true,
        });
      });
    });
  }
}
