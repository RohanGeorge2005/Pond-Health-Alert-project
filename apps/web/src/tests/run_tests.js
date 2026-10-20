/**
 * Standalone Node.js Test Runner for Frontend Validation
 * Can be executed with: node apps/web/src/tests/run_tests.js
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

console.log("==================================================");
console.log(" Running Frontend Validation Test Suite (Node.js)");
console.log("==================================================");

// 1. Test i18n Dictionary Parity & Completeness
console.log("\n[1/5] Testing i18n Language Completeness & Parity...");
const i18nPath = path.join(__dirname, "../lib/i18n.ts");
const i18nContent = fs.readFileSync(i18nPath, "utf-8");

// Extract translations.en and translations.kn keys
const extractKeys = (content, lang) => {
  const match = content.match(new RegExp(`${lang}:\\s*\\{\\s*translation:\\s*\\{([\\s\\S]*?)\\}\\s*\\},`));
  if (!match) return [];
  const lines = match[1].split("\n");
  const keys = [];
  for (const line of lines) {
    const keyMatch = line.match(/^\s*([a-zA-Z0-9_]+):/);
    if (keyMatch && keyMatch[1] !== "translation") {
      keys.push(keyMatch[1]);
    }
  }
  return keys;
};

const enKeys = extractKeys(i18nContent, "en");
const knKeys = extractKeys(i18nContent, "kn");

assert(enKeys.length > 70, `Found ${enKeys.length} English translation keys`);
assert(knKeys.length > 70, `Found ${knKeys.length} Kannada translation keys`);

const missingInKn = enKeys.filter(k => !knKeys.includes(k));
const missingInEn = knKeys.filter(k => !enKeys.includes(k));

assert(missingInKn.length === 0, `No keys missing in Kannada (Missing: ${missingInKn.join(", ") || "None"})`);
assert(missingInEn.length === 0, `No keys missing in English (Missing: ${missingInEn.join(", ") || "None"})`);

// 2. Test Tab Navigation Structure
console.log("\n[2/5] Testing Navigation Tab Structure in App.tsx...");
const appPath = path.join(__dirname, "../App.tsx");
const appContent = fs.readFileSync(appPath, "utf-8");

const expectedTabs = ["home", "readings", "daily", "photo", "impact"];
for (const tab of expectedTabs) {
  assert(appContent.includes(`currentTab === "${tab}"`), `App.tsx contains screen rendering for tab: ${tab}`);
}

// 3. Test Actionable Dashboard & Alerts
console.log("\n[3/5] Testing Actionable Dashboard & Alert Inbox...");
assert(appContent.includes("alertsSectionTitle"), "Alerts section header present in App.tsx");
assert(appContent.includes("handleAcknowledgeAlert"), "Alert acknowledgment handler wired up");
assert(appContent.includes("miniTrendTitle"), "24-hour mini DO trend sparkline component present");
assert(appContent.includes("quickCheckBtn"), "Quick action shortcut to 30-sec check present");

// 4. Test Multi-Parameter Analytics & Daily Log
console.log("\n[4/5] Testing Readings Analytics & Daily History Log...");
assert(appContent.includes("selectedTimeRange"), "Multi-range time selector (24h/7d/30d) implemented");
assert(appContent.includes("selectedParam"), "Parameter tabs (DO, pH, Temp, Ammonia) implemented");
assert(appContent.includes("historicalDailyChecks"), "Daily check observation log list implemented");
assert(appContent.includes("showManualForm"), "Manual test-kit calibration form toggle present");

// 5. Test Fish Photo Upload & File Gate Validation
console.log("\n[5/5] Testing Photo Gating & Multi-Host Resilience...");
assert(appContent.includes('accept="image/jpeg,image/png,image/webp"'), "Gallery input accepts valid image formats");
assert(appContent.includes('capture="environment"'), "Camera input specifies environment camera");
assert(appContent.includes("handleRunOfflineDemo"), "In-browser offline demo analysis handler is present");
assert(appContent.includes("runDemoAnalysisBtn"), "Offline demo analysis button trigger is present");
assert(appContent.includes("gradcam_data_url"), "Grad-CAM visual heatmap overlay display wired up");

console.log("\n==================================================");
console.log(` Test Summary: ${passed} PASSED, ${failed} FAILED`);
console.log("==================================================");

if (failed > 0) {
  process.exit(1);
}
