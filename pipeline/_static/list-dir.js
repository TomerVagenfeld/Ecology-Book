// _static/list-dir.js
// Attribute-only list direction: if ANY Hebrew present -> RTL, else LTR.
(function () {
  const HEBREW = /[\u0590-\u05FF]/;

  function classifyLists() {
    // Cover docutils .simple and normal lists in article & footnotes
    const lists = document.querySelectorAll(
      ".bd-article ul, .bd-article ol, section.footnotes ul, section.footnotes ol"
    );

    lists.forEach(list => {
      // Gather a short sample from the first few items
      const items = Array.from(list.querySelectorAll(":scope > li")).slice(0, 6);
      const sample = items.map(li => (li.innerText || "").trim()).join(" ");

      const dir = HEBREW.test(sample) ? "rtl" : "ltr";

      // Set attribute (single source of truth) and scrub any stale classes
      list.setAttribute("dir", dir);
      list.classList.remove("list-ltr", "list-rtl"); // from older builds

      // Propagate to direct items so inner paragraphs inherit the same direction
      items.forEach(li => li.setAttribute("dir", dir));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", classifyLists);
  } else {
    classifyLists();
  }
})();
