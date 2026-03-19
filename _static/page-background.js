// page-background.js
// Applies the book's geometric background to all pages with a readable content
// overlay. User preference is persisted in localStorage.

(function () {
  const STORAGE_KEY = "bookBgEnabled";
  const BG_CLASS = "with-book-bg";

  function isEnabled() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === null ? true : stored === "true"; // default ON
  }

  function applyState(enabled) {
    document.body.classList.toggle(BG_CLASS, enabled);
    const btn = document.getElementById("bg-toggle-btn");
    if (btn) {
      btn.title = enabled ? "הסתר רקע" : "הצג רקע";
      btn.classList.toggle("bg-off", !enabled);
    }
  }

  function createButton() {
    const btn = document.createElement("button");
    btn.id = "bg-toggle-btn";
    btn.setAttribute("aria-label", "החלף רקע עמוד");
    btn.title = isEnabled() ? "הסתר רקע" : "הצג רקע";
    btn.innerHTML = `<svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
      <path d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4z" opacity=".35"/>
      <circle cx="6.5" cy="8.5" r="1.5"/>
      <path d="M2.5 15l4-5 3 3.5 2.5-3L16.5 15z"/>
    </svg>`;
    btn.addEventListener("click", () => {
      const next = !isEnabled();
      localStorage.setItem(STORAGE_KEY, next);
      applyState(next);
    });
    document.body.appendChild(btn);
  }

  function init() {
    applyState(isEnabled());
    createButton();
  }

  // Apply class immediately (before paint) to avoid flash
  if (isEnabled()) document.documentElement.classList.add(BG_CLASS + "-pre");

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
