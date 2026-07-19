/* AdminLTE's theme-init, verbatim from the reference pages (prevents the
   flash of the wrong theme on load). External file instead of inline only
   because the CSP allows no inline scripts; it still loads first in <head>
   and runs before first paint. */
(() => {
  'use strict';
  const STORAGE_KEY = 'lte-theme';
  let stored = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch {
    // localStorage may be unavailable (private mode, sandboxed iframe).
  }
  const prefersDark = globalThis.matchMedia('(prefers-color-scheme: dark)').matches;
  // Explicit "dark"/"light" win, otherwise ("auto" or unset) fall back to
  // the OS preference.
  let resolved = 'light';
  if (stored === 'dark' || stored === 'light') {
    resolved = stored;
  } else if (prefersDark) {
    resolved = 'dark';
  }
  document.documentElement.setAttribute('data-bs-theme', resolved);
  document.documentElement.style.colorScheme = resolved;
})();
