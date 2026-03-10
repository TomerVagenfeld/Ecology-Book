// search-scroll.js
// After Sphinx highlights search terms on a page, scroll to the first match
// and provide prev/next navigation when there are multiple matches.
(function () {
  "use strict";

  var currentIndex = -1;
  var highlights = [];
  var bar = null;

  function scrollToMatch(idx) {
    if (highlights.length === 0) return;
    // clamp
    if (idx < 0) idx = highlights.length - 1;
    if (idx >= highlights.length) idx = 0;
    currentIndex = idx;

    // remove active class from all
    highlights.forEach(function (el) { el.classList.remove("hl-active"); });

    // add active class and scroll
    var el = highlights[currentIndex];
    el.classList.add("hl-active");
    el.scrollIntoView({ behavior: "smooth", block: "center" });

    // update counter
    if (bar) {
      var counter = bar.querySelector(".hl-counter");
      if (counter) {
        counter.textContent = (currentIndex + 1) + " / " + highlights.length;
      }
    }
  }

  function createNavBar() {
    bar = document.createElement("div");
    bar.className = "hl-nav-bar";
    bar.innerHTML =
      '<span class="hl-counter">' + (currentIndex + 1) + " / " + highlights.length + "</span>" +
      '<button class="hl-btn hl-prev" title="Previous">\u25B2</button>' +
      '<button class="hl-btn hl-next" title="Next">\u25BC</button>' +
      '<button class="hl-btn hl-close" title="Close">\u2715</button>';

    bar.querySelector(".hl-prev").addEventListener("click", function () {
      scrollToMatch(currentIndex - 1);
    });
    bar.querySelector(".hl-next").addEventListener("click", function () {
      scrollToMatch(currentIndex + 1);
    });
    bar.querySelector(".hl-close").addEventListener("click", function () {
      bar.remove();
      bar = null;
      // also remove highlights
      highlights.forEach(function (el) {
        el.classList.remove("highlighted", "hl-active");
        // unwrap: replace span with its text content
        var parent = el.parentNode;
        if (parent) {
          parent.replaceChild(document.createTextNode(el.textContent), el);
          parent.normalize();
        }
      });
      highlights = [];
    });

    document.body.appendChild(bar);

    // Force repaint so mobile browsers show the fixed bar immediately
    // (without waiting for user scroll to trigger a layout)
    requestAnimationFrame(function () {
      bar.style.opacity = "0.99";
      requestAnimationFrame(function () {
        bar.style.opacity = "1";
      });
    });
  }

  function init() {
    // Wait a bit for Sphinx highlighting to finish (it uses setTimeout(…, 10))
    setTimeout(function () {
      highlights = Array.from(document.querySelectorAll("span.highlighted"));
      if (highlights.length === 0) return;

      currentIndex = 0;

      // If the URL has a hash (section anchor), find the first highlight AFTER that section
      if (window.location.hash) {
        var anchor = document.querySelector(window.location.hash);
        if (anchor) {
          var anchorTop = anchor.getBoundingClientRect().top + window.scrollY;
          for (var i = 0; i < highlights.length; i++) {
            var hlTop = highlights[i].getBoundingClientRect().top + window.scrollY;
            if (hlTop >= anchorTop - 50) {
              currentIndex = i;
              break;
            }
          }
        }
      }

      createNavBar();
      // Small delay so the page settles
      setTimeout(function () { scrollToMatch(currentIndex); }, 150);

      // Keyboard shortcuts: n/N for next, p/P for previous
      document.addEventListener("keydown", function (e) {
        if (!bar) return;
        if (document.activeElement && document.activeElement.tagName === "INPUT") return;
        if (e.key === "n" || e.key === "N") { scrollToMatch(currentIndex + 1); e.preventDefault(); }
        if (e.key === "p" || e.key === "P") { scrollToMatch(currentIndex - 1); e.preventDefault(); }
      });
    }, 100);
  }

  // Only run on non-search pages (search.html shows results, not highlighted content)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
