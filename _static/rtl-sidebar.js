// Keep desktop interactive: don't open the <dialog>; collapse the static sidebar instead.
document.addEventListener("DOMContentLoaded", () => {
  // Dispose Bootstrap tooltips on sidebar toggles — they fire too aggressively
  // (Bootstrap initialises them via data-bs-toggle="tooltip" and shows on focus/scroll)
  setTimeout(() => {
    document.querySelectorAll(".sidebar-toggle").forEach(btn => {
      try { bootstrap.Tooltip.getInstance(btn)?.dispose(); } catch(e) {}
      btn.removeAttribute("data-bs-toggle");
      btn.removeAttribute("data-bs-original-title");
    });
  }, 500);

  const primaryToggle = document.querySelector(".sidebar-toggle.primary-toggle");
  const primaryDialog = document.getElementById("pst-primary-sidebar-modal");
  if (primaryToggle) {
    primaryToggle.addEventListener("click", (e) => {
      const isDesktop = window.matchMedia("(min-width: 992px)").matches;
      if (!isDesktop) return;                 // mobile: let theme open dialog

      e.preventDefault();                     // stop showModal()
      // If the dialog was opened by theme JS before our handler ran, close it:
      if (primaryDialog && primaryDialog.open && typeof primaryDialog.close === "function") {
        primaryDialog.close();
      }

      document.body.classList.toggle("rtl-sidebar-collapsed");
    });
  }

  const secondaryToggle = document.querySelector(".sidebar-toggle.secondary-toggle");
  const secondaryDialog = document.getElementById("pst-secondary-sidebar-modal");
  if (secondaryToggle) {
    secondaryToggle.addEventListener("click", (e) => {
      const isDesktop = window.matchMedia("(min-width: 992px)").matches;
      if (!isDesktop) return;                 // mobile: let theme open dialog

      e.preventDefault();                     // stop showModal()
      if (secondaryDialog && secondaryDialog.open && typeof secondaryDialog.close === "function") {
        secondaryDialog.close();
      }
      // Also uncheck the checkbox-based toggle so the overlay doesn't appear
      const cb = document.getElementById("pst-secondary-sidebar-checkbox");
      if (cb) cb.checked = false;

      document.body.classList.toggle("rtl-secondary-collapsed");
    });
  }
});
