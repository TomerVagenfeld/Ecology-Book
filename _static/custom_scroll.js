// custom_scroll.js
// Scroll to the first highlighted search result using MutationObserver.
// (search-hebrew.js also handles this; this file is kept as a fallback)
window.addEventListener("DOMContentLoaded", function () {
  var container = document.getElementById("search-results");
  if (!container) return;

  var observer = new MutationObserver(function () {
    var first = document.querySelector(".highlighted");
    if (first) {
      first.scrollIntoView({ behavior: "smooth", block: "center" });
      observer.disconnect();
    }
  });

  observer.observe(container, { childList: true, subtree: true });
});
