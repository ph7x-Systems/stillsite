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

/* Markdown editor (ADR-0023): EasyMDE on marked textareas, formatting
   toolbar only — the builder's server-rendered preview stays the truth,
   so EasyMDE's own preview/side-by-side/fullscreen are not offered.
   Toolbar titles come from the i18n catalogs via data-markdown-labels. */
document.addEventListener('DOMContentLoaded', function () {
  if (typeof EasyMDE === 'undefined') return;
  document.querySelectorAll('textarea[data-markdown-editor]').forEach(function (area) {
    let labels = {};
    try {
      labels = JSON.parse(area.dataset.markdownLabels || '{}');
    } catch {
      labels = {};
    }
    // EasyMDE's built-in buttons expect Font Awesome; the admin ships
    // Bootstrap Icons (ADR-0017), so each button maps to a bi glyph and
    // to the editor's exported action.
    const buttons = {
      'bold': ['bi bi-type-bold', EasyMDE.toggleBold],
      'italic': ['bi bi-type-italic', EasyMDE.toggleItalic],
      'heading': ['bi bi-type-h1', EasyMDE.toggleHeadingSmaller],
      'quote': ['bi bi-quote', EasyMDE.toggleBlockquote],
      'unordered-list': ['bi bi-list-ul', EasyMDE.toggleUnorderedList],
      'ordered-list': ['bi bi-list-ol', EasyMDE.toggleOrderedList],
      'link': ['bi bi-link-45deg', EasyMDE.drawLink],
      'image': ['bi bi-image', EasyMDE.drawImage],
      'code': ['bi bi-code', EasyMDE.toggleCodeBlock],
      'guide': ['bi bi-question-circle', 'https://www.markdownguide.org/basics/'],
    };
    const named = function (name) {
      return { name: name, action: buttons[name][1], className: buttons[name][0],
               title: labels[name] || name };
    };
    const mde = new EasyMDE({
      element: area,
      autoDownloadFontAwesome: false,
      spellChecker: false,
      status: false,
      toolbar: [
        named('bold'), named('italic'), named('heading'), '|',
        named('quote'), named('unordered-list'), named('ordered-list'), '|',
        named('link'), named('image'), named('code'), '|', named('guide'),
      ],
      minHeight: '280px',
    });
    // CodeMirror's editing surface is its own textarea; carry the field's
    // visible label over so the editor stays labeled (WCAG).
    const label = document.querySelector('label[for="' + area.id + '"]');
    const input = mde.codemirror.getInputField();
    if (label && input) input.setAttribute('aria-label', label.textContent.trim());
  });
});
