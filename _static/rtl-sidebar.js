// Keep desktop interactive: don't open the <dialog>; collapse the static sidebar instead.
document.addEventListener("DOMContentLoaded", () => {
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

      document.body.classList.toggle("rtl-secondary-collapsed");
    });
  }
});
