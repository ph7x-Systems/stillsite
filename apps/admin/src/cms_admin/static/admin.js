/* Sardine CMS admin — the page-level init the AdminLTE reference pages run
   inline (ADR-0020). The CSP allows no inline scripts, so it lives here.
   Everything else (sidebar toggle, treeview, dropdowns) is AdminLTE's and
   Bootstrap's own vendored code. */

const SELECTOR_SIDEBAR_WRAPPER = '.sidebar-wrapper';
const Default = {
  scrollbarTheme: 'os-theme-light',
  scrollbarAutoHide: 'leave',
  scrollbarClickScroll: true,
};
document.addEventListener('DOMContentLoaded', function () {
  const sidebarWrapper = document.querySelector(SELECTOR_SIDEBAR_WRAPPER);

  // Disable OverlayScrollbars on mobile devices to prevent touch interference
  const isMobile = window.innerWidth <= 992;

  if (
    sidebarWrapper &&
    OverlayScrollbarsGlobal?.OverlayScrollbars !== undefined &&
    !isMobile
  ) {
    OverlayScrollbarsGlobal.OverlayScrollbars(sidebarWrapper, {
      scrollbars: {
        theme: Default.scrollbarTheme,
        autoHide: Default.scrollbarAutoHide,
        clickScroll: Default.scrollbarClickScroll,
      },
    });
  }
});
