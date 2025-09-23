// Keep desktop interactive: don't open the <dialog>; collapse the static sidebar instead.
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".sidebar-toggle.primary-toggle");
  const dlg = document.getElementById("pst-primary-sidebar-modal");
  if (!toggle) return;

  toggle.addEventListener("click", (e) => {
    const isDesktop = window.matchMedia("(min-width: 992px)").matches;
    if (!isDesktop) return;                 // mobile: let theme open dialog

    e.preventDefault();                     // stop showModal()
    // If the dialog was opened by theme JS before our handler ran, close it:
    if (dlg && dlg.open && typeof dlg.close === "function") dlg.close();

    document.body.classList.toggle("rtl-sidebar-collapsed");
  });
});
