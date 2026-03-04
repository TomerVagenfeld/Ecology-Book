// _static/footnote-dir.js
(function () {
  function isHebrew(text) {
    return /[\u0590-\u05FF]/.test(text);
  }

  function classifyFootnotes() {
    // MyST/Sphinx puts footnotes in a <section class="footnotes"> with <li id="fnX">
    const liFootnotes = document.querySelectorAll('section.footnotes li[id^="fn"]');
    // Some themes also use <aside class="footnote"> blocks (cover both just in case)
    const asideFootnotes = document.querySelectorAll('aside.footnote, div.footnote');

    const nodes = [...liFootnotes, ...asideFootnotes];

    nodes.forEach(el => {
      const txt = (el.innerText || el.textContent || '').trim();
      if (!txt) return;
      const heb = isHebrew(txt);
      el.classList.remove('fn-rtl', 'fn-ltr');
      el.classList.add(heb ? 'fn-rtl' : 'fn-ltr');
      el.setAttribute('dir', heb ? 'rtl' : 'ltr');
    });
  }

  // Run after the theme finishes laying out the page
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', classifyFootnotes);
  } else {
    classifyFootnotes();
  }
})();
