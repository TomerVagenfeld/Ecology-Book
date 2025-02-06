document.addEventListener("DOMContentLoaded", function() {
  // Only proceed if a search query is present in the URL
  const params = new URLSearchParams(window.location.search);
  const query = params.get("q");
  if (query) {
    // Wait a bit to allow the page to fully render
    setTimeout(() => {
      const highlighted = document.querySelector('.highlighted');
      if (highlighted) {
        highlighted.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 300);
  }
});
