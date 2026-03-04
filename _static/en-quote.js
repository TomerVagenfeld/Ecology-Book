(function() {
  const HEBREW_RE = /[\u0590-\u05FF]/;
  const LATIN_RE = /[A-Za-z]/g;

  function looksEnglish(text) {
    if (!text) return false;
    const trimmed = text.trim();
    if (!trimmed) return false;
    if (HEBREW_RE.test(trimmed)) return false;
    const latin = trimmed.match(LATIN_RE);
    return latin && latin.length >= 8;
  }

  function wrapCluster(cluster) {
    if (!cluster.length) return;
    const first = cluster[0];
    const parent = first.parentNode;
    if (!parent) return;

    const wrapper = document.createElement("div");
    wrapper.classList.add("en_quote");

    parent.insertBefore(wrapper, first);
    cluster.forEach(node => {
      while (node.firstChild) {
        wrapper.appendChild(node.firstChild);
      }
      node.remove();
    });
  }

  function processParent(parent) {
    const children = Array.from(parent.children);
    let cluster = [];

    function flushCluster() {
      if (cluster.length) {
        wrapCluster(cluster);
        cluster = [];
      }
    }

    children.forEach(child => {
      if (!(child instanceof HTMLElement)) {
        flushCluster();
        return;
      }
      if (child.classList.contains("en_quote") || child.closest(".en_quote") === parent) {
        flushCluster();
        processParent(child);
        return;
      }
      if (child.classList.contains("docutils") && child.classList.contains("container") && looksEnglish(child.textContent || "")) {
        cluster.push(child);
        return;
      }

      flushCluster();
      processParent(child);
    });

    flushCluster();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".bd-article").forEach(article => {
      processParent(article);
    });
  });
})();
