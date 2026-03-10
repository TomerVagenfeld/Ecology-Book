// image-zoom.js
// On mobile: tap a figure image to view it fullscreen; tap again or swipe to close.
(function () {
  "use strict";

  // Only activate on narrow screens (mobile / small tablets)
  function isMobile() {
    return window.innerWidth < 992;
  }

  function openZoom(img) {

    var overlay = document.createElement("div");
    overlay.className = "img-zoom-overlay";

    var clone = document.createElement("img");
    clone.src = img.src;
    clone.alt = img.alt || "";
    overlay.appendChild(clone);

    // Close on tap
    overlay.addEventListener("click", function () {
      overlay.remove();
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
      img.addEventListener("click", function (e) {
        e.preventDefault();
        openZoom(img);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
