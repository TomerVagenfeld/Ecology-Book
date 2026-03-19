// image-zoom.js
// Click a figure image to view it fullscreen; click again or press Escape to close.
(function () {
  "use strict";

  function openZoom(img) {
    var overlay = document.createElement("div");
    overlay.className = "img-zoom-overlay";

    var clone = document.createElement("img");
    clone.src = img.currentSrc || img.src;
    clone.alt = img.alt || "";
    overlay.appendChild(clone);

    // Close on click
    overlay.addEventListener("click", function () {
      overlay.remove();
      document.removeEventListener("keydown", onKey);
    });

    // Close on Escape
    function onKey(e) {
      if (e.key === "Escape") {
        overlay.remove();
        document.removeEventListener("keydown", onKey);
      }
    }
    document.addEventListener("keydown", onKey);

    document.body.appendChild(overlay);
  }

  function init() {
    // Attach to all figure images in the article
    document.querySelectorAll(".bd-article figure img, .bd-article .figure img").forEach(function (img) {
      // Sphinx wraps figure images in <a class="image-reference"> links.
      // We must intercept clicks on the <a> (or the <img> if unwrapped)
      // to prevent the browser from navigating to the raw image file.
      var anchor = img.closest("a");
      var clickTarget = anchor || img;

      clickTarget.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        openZoom(img);
      });

      // Visual affordance
      clickTarget.style.cursor = "zoom-in";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
