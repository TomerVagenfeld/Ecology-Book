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

  function buildButton() {
    const btn = document.createElement("button");
    btn.id = "bg-toggle-btn";
    btn.setAttribute("aria-label", "החלף רקע עמוד");
    btn.title = isEnabled() ? "הסתר רקע" : "הצג רקע";
    btn.innerHTML = `<i class="fas fa-image"></i>`;
    btn.addEventListener("click", () => {
      const next = !isEnabled();
      localStorage.setItem(STORAGE_KEY, next);
      applyState(next);
    });
    return btn;
  }

  function placeInHeader(btn) {
    const end = document.querySelector(".header-article-items__end");
    if (!end) return false;
    // Safely detach button from wherever it currently is
    btn.remove();
    const wrap = document.createElement("div");
    wrap.className = "header-article-item";
    wrap.appendChild(btn);
    end.insertAdjacentElement("afterbegin", wrap);
    return true;
  }

  function watchAndKeepInHeader(btn) {
    let debounceTimer = null;
    const observer = new MutationObserver(() => {
      if (btn.closest(".header-article-items__end")) return; // already in place
      // Debounce: wait for the theme's DOM churn to settle before re-injecting
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        if (!btn.closest(".header-article-items__end")) {
          placeInHeader(btn);
        }
      }, 300);
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // After 15 s the page should be fully stable — stop watching
    setTimeout(() => {
      observer.disconnect();
      clearTimeout(debounceTimer);
      // If still not in header by now, fall back to fixed positioning
      if (!btn.closest(".header-article-items__end")) {
        btn.remove();
        btn.style.cssText = "position:fixed;top:0.5rem;right:5rem;z-index:200;";
        document.body.appendChild(btn);
      }
    }, 15000);
  }

  function injectButton() {
    const btn = buildButton();
    const placed = placeInHeader(btn);
    if (placed) {
      watchAndKeepInHeader(btn);
    } else {
      // Header not found yet — keep trying with observer
      watchAndKeepInHeader(btn);
    }
  }

  // Apply class immediately (before paint) to avoid flash
  if (isEnabled()) document.documentElement.classList.add(BG_CLASS + "-pre");

  // Apply background on DOMContentLoaded (early, avoids flash)
  document.addEventListener("DOMContentLoaded", () => applyState(isEnabled()));

  // Inject button on window.load — after Bootstrap/theme JS have run
  window.addEventListener("load", () => injectButton());
})();
