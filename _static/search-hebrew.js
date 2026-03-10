// search-hebrew.js
// Improve Hebrew search by stripping common prefixes and enhancing result display.
(function () {
  // Common Hebrew prefixes: single-letter and two-letter combinations
  var PREFIXES = [
    "וה", "וב", "ול", "ומ", "וכ", "וש",  // vav + prefix
    "של", "על",                              // two-letter prepositions
    "שה", "כש", "מה", "לה",                 // other combos
    "ה", "ו", "ב", "ל", "מ", "כ", "ש",     // single-letter
  ];

  var HEBREW_RE = /[\u0590-\u05FF]/;
  var MIN_STEM_LENGTH = 2;

  function stripHebrewPrefixes(term) {
    // Only strip prefixes from Hebrew words
    if (!HEBREW_RE.test(term) || term.length < 3) return [term];

    var variants = [term];

    for (var i = 0; i < PREFIXES.length; i++) {
      var prefix = PREFIXES[i];
      if (term.startsWith(prefix) && term.length - prefix.length >= MIN_STEM_LENGTH) {
        variants.push(term.slice(prefix.length));
      }
    }

    return variants;
  }

  function patchSearch() {
    // Wait for Sphinx search to be loaded
    if (typeof Search === "undefined" || !Search.query) {
      setTimeout(patchSearch, 200);
      return;
    }

    var originalQuery = Search.query;

    Search.query = function (query) {
      // Expand Hebrew terms with prefix-stripped variants
      var terms = query.split(/\s+/);
      var expanded = [];

      for (var i = 0; i < terms.length; i++) {
        var variants = stripHebrewPrefixes(terms[i]);
        // Use the original term + stripped version joined with OR logic
        // Sphinx search uses space as AND, so we search for the best variant
        expanded.push(variants[0]);
        // Add stripped variants as additional searches
        for (var j = 1; j < variants.length; j++) {
          expanded.push(variants[j]);
        }
      }

      // Run original search with expanded terms
      return originalQuery.call(this, expanded.join(" "));
    };
  }

  function enhanceSearchResults() {
    // Use MutationObserver instead of polling for search results
    var resultsContainer = document.getElementById("search-results");
    if (!resultsContainer) return;

    var observer = new MutationObserver(function (mutations) {
      var items = resultsContainer.querySelectorAll("ul.search li");
      if (items.length === 0) return;

      items.forEach(function (item) {
        var link = item.querySelector("a");
        if (!link || link.dataset.enhanced) return;
        link.dataset.enhanced = "true";

        // Extract chapter info from href
        var href = link.getAttribute("href") || "";
        var chMatch = href.match(/ch(\d+)_/);
        if (chMatch) {
          var chNum = chMatch[1];
          var breadcrumb = document.createElement("span");
          breadcrumb.className = "search-breadcrumb";
          breadcrumb.textContent = "\u05E4\u05E8\u05E7 " + chNum + " \u203A ";
          breadcrumb.style.cssText = "color: #666; font-size: 0.85em; margin-inline-end: 0.3em;";
          link.insertBefore(breadcrumb, link.firstChild);
        }
      });

      // Scroll to first highlighted result
      var firstHighlight = resultsContainer.querySelector(".highlighted");
      if (firstHighlight) {
        firstHighlight.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });

    observer.observe(resultsContainer, { childList: true, subtree: true });
  }

  function hebrewizePlaceholder() {
    var input = document.getElementById("search-input");
    if (input) {
      input.placeholder = "\u05D7\u05D9\u05E4\u05D5\u05E9 \u05D1\u05E1\u05E4\u05E8\u2026";  // "חיפוש בספר…"
      input.setAttribute("aria-label", "\u05D7\u05D9\u05E4\u05D5\u05E9 \u05D1\u05E1\u05E4\u05E8");
    }
  }

  function addSlashShortcut() {
    // Replace the Ctrl+K badge text with "/" in the header search button
    var kbdBadges = document.querySelectorAll(".search-button__kbd-shortcut");
    kbdBadges.forEach(function (badge) {
      badge.innerHTML = '<kbd class="kbd-shortcut__modifier">/</kbd>';
    });

    // Listen for "/" key to open the search overlay (common in docs sites)
    document.addEventListener("keydown", function (e) {
      // Don't trigger if user is typing in an input/textarea
      var tag = document.activeElement && document.activeElement.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      // Don't trigger with modifier keys
      if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;

      if (e.key === "/") {
        e.preventDefault();
        // Find and click the search button to open the overlay
        var searchBtn = document.querySelector(".search-button__button");
        if (searchBtn) {
          searchBtn.click();
        } else {
          // Fallback: focus the search input directly (e.g. on search.html)
          var input = document.getElementById("search-input");
          if (input) { input.focus(); input.select(); }
        }
      }
    });
  }

  function markSearchPage() {
    // Add body class on search.html so CSS can hide sidebars and go full-width
    if (document.getElementById("search-results")) {
      document.body.classList.add("search-page");
    }
  }

  function init() {
    markSearchPage();
    patchSearch();
    enhanceSearchResults();
    hebrewizePlaceholder();
    addSlashShortcut();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
