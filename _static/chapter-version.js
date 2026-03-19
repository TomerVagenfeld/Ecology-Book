// chapter-version.js
// Injects an "עודכן: [date]" badge below the chapter title on each page.
// update_apply.py updates CHAPTER_VERSIONS automatically when new content is applied.

const CHAPTER_VERSIONS = {
  default: "אוקטובר 2025",
  // Per-chapter overrides — add entries like:
  // "ch3_energy": "נובמבר 2025",
};

(function () {
  function getPageSlug() {
    const path = window.location.pathname.replace(/\/+$/, ""); // strip trailing slashes
    const parts = path.split("/");
    const filename = parts[parts.length - 1].replace(/\.html$/, "");
    return filename;
  }

  function getVersion(slug) {
    return CHAPTER_VERSIONS[slug] || CHAPTER_VERSIONS["default"] || null;
  }

  function inject() {
    // Only inject on chapter pages (ch1–ch15)
    const slug = getPageSlug();
    if (!/^ch\d+/.test(slug)) return;

    const version = getVersion(slug);
    if (!version) return;

    // Find the main content h1 — try progressively broader selectors
    const h1 =
      document.querySelector(".bd-content section > h1") ||
      document.querySelector("article.bd-article h1") ||
      document.querySelector(".bd-content h1");
    if (!h1) return;

    // Don't inject twice (e.g. if script somehow runs twice)
    if (h1.nextElementSibling && h1.nextElementSibling.classList.contains("chapter-version-badge")) return;

    const badge = document.createElement("div");
    badge.className = "chapter-version-badge";
    badge.textContent = "עודכן: " + version;
    h1.insertAdjacentElement("afterend", badge);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inject);
  } else {
    inject();
  }
})();
