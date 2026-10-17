import { test, expect } from "vitest";
import { translations } from "../lib/i18n";

test("i18n completeness: no translation keys missing between English and Kannada", () => {
  const enKeys = Object.keys(translations.en.translation);
  const knKeys = Object.keys(translations.kn.translation);

  const missingInKn = enKeys.filter((key) => !knKeys.includes(key));
  const missingInEn = knKeys.filter((key) => !enKeys.includes(key));

  expect(missingInKn, `Keys missing in Kannada dictionary: ${missingInKn.join(", ")}`).toEqual([]);
  expect(missingInEn, `Keys missing in English dictionary: ${missingInEn.join(", ")}`).toEqual([]);

  // Verify non-empty translations
  for (const key of enKeys) {
    const enVal = (translations.en.translation as any)[key];
    const knVal = (translations.kn.translation as any)[key];
    expect(enVal.trim().length, `Empty English translation for key: ${key}`).toBeGreaterThan(0);
    expect(knVal.trim().length, `Empty Kannada translation for key: ${key}`).toBeGreaterThan(0);
  }
});
