// footnote-tooltip.js
// Shows footnote content as a hoverable tooltip with selectable text.
// Also ensures scroll-to-footnote and back-to-source navigation works.
(function () {
  let activeTooltip = null;
  let hideTimeout = null;

  function createTooltip(content, isRTL) {
    const tip = document.createElement("div");
    tip.className = "fn-tooltip" + (isRTL ? " fn-rtl" : " fn-ltr");
    tip.innerHTML = content;
    document.body.appendChild(tip);
    return tip;
  }

  function positionTooltip(tip, anchor) {
    const rect = anchor.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    const scrollY = window.scrollY || document.documentElement.scrollTop;
    const scrollX = window.scrollX || document.documentElement.scrollLeft;

    // Position above the anchor by default
    let top = rect.top + scrollY - tipRect.height - 8;
    let left = rect.left + scrollX + rect.width / 2 - tipRect.width / 2;

    // Flip below if not enough room above
    if (top < scrollY + 10) {
      top = rect.bottom + scrollY + 8;
    }

    // Keep within viewport horizontally
    const maxLeft = document.documentElement.clientWidth - tipRect.width - 10 + scrollX;
    left = Math.max(scrollX + 10, Math.min(left, maxLeft));

    tip.style.top = top + "px";
    tip.style.left = left + "px";
  }

  function removeTooltip() {
    if (activeTooltip) {
      activeTooltip.remove();
      activeTooltip = null;
    }
  }

  function scheduleHide() {
    hideTimeout = setTimeout(removeTooltip, 200);
  }

  function cancelHide() {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      hideTimeout = null;
    }
  }

  function getFootnoteContent(href) {
    // href is like "#fn1" or "#footnote-1" etc.
    if (!href || !href.startsWith("#")) return null;
    const target = document.getElementById(href.slice(1));
    if (!target) return null;

    // Clone content, remove the back-reference link
    const clone = target.cloneNode(true);
    const backLinks = clone.querySelectorAll(".fn-backref, .backrefs, a.footnote-backref");
    backLinks.forEach(function (el) { el.remove(); });

    // Also remove the footnote label/number at the start
    const label = clone.querySelector(".footnote-label, .label");
    if (label) label.remove();

    return clone.innerHTML || clone.textContent;
  }

  function isHebrew(text) {
    return /[\u0590-\u05FF]/.test(text);
  }

  function initFootnoteTooltips() {
    // Find all footnote references
    const refs = document.querySelectorAll(
      "a.footnote-reference, sup a[href^='#fn'], a[role='doc-noteref']"
    );

    refs.forEach(function (ref) {
      ref.addEventListener("mouseenter", function () {
        cancelHide();

        const href = ref.getAttribute("href");
        const content = getFootnoteContent(href);
        if (!content) return;

        removeTooltip();
        const rtl = isHebrew(content);
        activeTooltip = createTooltip(content, rtl);

        // Let browser render, then position
        requestAnimationFrame(function () {
          positionTooltip(activeTooltip, ref);
        });

        // Keep tooltip alive when hovering over it
        activeTooltip.addEventListener("mouseenter", cancelHide);
        activeTooltip.addEventListener("mouseleave", scheduleHide);
      });

      ref.addEventListener("mouseleave", scheduleHide);
    });
  }

  function ensureBackLinks() {
    // Ensure footnote definitions have visible back-links
    const footnotes = document.querySelectorAll(
      "aside.footnote, div.footnote, section.footnotes li"
    );

    footnotes.forEach(function (fn) {
      // Check if there's already a back-link
      const existing = fn.querySelector(".fn-backref, a.footnote-backref");
      if (existing) return;

      // Find the backref from the element's id
      const fnId = fn.id;
      if (!fnId) return;

      // Find referring link
      const refLink = document.querySelector('a[href="#' + fnId + '"]');
      if (!refLink) return;

      // Add a back-link
      const backLink = document.createElement("a");
      backLink.href = "#" + (refLink.id || refLink.parentElement.id || "");
      backLink.className = "fn-backref";
      backLink.textContent = " \u21A9";
      backLink.title = "חזרה לטקסט";
      backLink.style.textDecoration = "none";
      backLink.style.marginInlineStart = "0.3em";

      // Smooth scroll on click
      backLink.addEventListener("click", function (e) {
        e.preventDefault();
        const target = document.querySelector(backLink.getAttribute("href"));
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          // Brief highlight
          target.style.backgroundColor = "rgba(255, 255, 0, 0.3)";
          setTimeout(function () { target.style.backgroundColor = ""; }, 2000);
        }
      });

      fn.appendChild(backLink);
    });
  }

  function addSmoothScrollToRefs() {
    // Make footnote reference clicks smooth-scroll
    const refs = document.querySelectorAll(
      "a.footnote-reference, sup a[href^='#fn'], a[role='doc-noteref']"
    );

    refs.forEach(function (ref) {
      ref.addEventListener("click", function (e) {
        const href = ref.getAttribute("href");
        if (!href || !href.startsWith("#")) return;
        const target = document.getElementById(href.slice(1));
        if (!target) return;

        e.preventDefault();
        removeTooltip();
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        // Brief highlight
        target.style.backgroundColor = "rgba(168, 207, 64, 0.3)";
        setTimeout(function () { target.style.backgroundColor = ""; }, 2000);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initFootnoteTooltips();
      ensureBackLinks();
      addSmoothScrollToRefs();
    });
  } else {
    initFootnoteTooltips();
    ensureBackLinks();
    addSmoothScrollToRefs();
  }
})();
