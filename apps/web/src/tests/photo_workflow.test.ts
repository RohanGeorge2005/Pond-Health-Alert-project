import { test, expect } from "vitest";

describe("Fish Photo Upload & Validation Workflow", () => {
  const MIN_SIZE_BYTES = 5 * 1024; // 5 KB
  const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
  const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];

  function validatePhotoFile(file: { type: string; size: number }) {
    if (!file.type || !file.type.startsWith("image/")) {
      return { valid: false, error: "Please select a valid image file (JPEG, PNG, or WebP)." };
    }
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      return { valid: false, error: "Unsupported image format. Allowed: JPEG, PNG, WebP." };
    }
    if (file.size > MAX_SIZE_BYTES) {
      return { valid: false, error: "Image file is too large. Maximum size is 10 MB." };
    }
    if (file.size < MIN_SIZE_BYTES) {
      return { valid: false, error: "Image file is suspiciously small (< 5 KB). Please upload a clear photo." };
    }
    return { valid: true, error: null };
  }

  test("rejects non-image mime types", () => {
    const res = validatePhotoFile({ type: "application/pdf", size: 50 * 1024 });
    expect(res.valid).toBe(false);
    expect(res.error).toContain("valid image file");
  });

  test("rejects unsupported image types (e.g. svg or tiff)", () => {
    const res = validatePhotoFile({ type: "image/svg+xml", size: 50 * 1024 });
    expect(res.valid).toBe(false);
    expect(res.error).toContain("Unsupported image format");
  });

  test("rejects files smaller than 5 KB (suspicious empty or corrupted placeholder)", () => {
    const res = validatePhotoFile({ type: "image/jpeg", size: 1024 });
    expect(res.valid).toBe(false);
    expect(res.error).toContain("< 5 KB");
  });

  test("rejects files larger than 10 MB", () => {
    const res = validatePhotoFile({ type: "image/jpeg", size: 12 * 1024 * 1024 });
    expect(res.valid).toBe(false);
    expect(res.error).toContain("too large");
  });

  test("accepts valid JPEG, PNG, WebP within 5KB to 10MB", () => {
    const resJpeg = validatePhotoFile({ type: "image/jpeg", size: 2 * 1024 * 1024 });
    expect(resJpeg.valid).toBe(true);
    expect(resJpeg.error).toBeNull();

    const resPng = validatePhotoFile({ type: "image/png", size: 500 * 1024 });
    expect(resPng.valid).toBe(true);

    const resWebp = validatePhotoFile({ type: "image/webp", size: 150 * 1024 });
    expect(resWebp.valid).toBe(true);
  });
});
