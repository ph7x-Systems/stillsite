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
      forceSync: true,
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
    // CodeMirror edits outside the original textarea. Mirror its change as
    // a bubbling input event so the generic autosave form sees it.
    mde.codemirror.on('change', function () {
      area.dispatchEvent(new Event('input', { bubbles: true }));
    });
  });
});

/* ADR-0027 phase 2: valid source edits autosave after a short debounce and
   refresh the iframe with the server-rendered real theme. Requests are
   serialized; a manual Save waits for any active autosave, then remains the
   revision-producing final write. Forms still work normally without JS. */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form[data-autosave]').forEach(function (form) {
    const status = form.querySelector('[data-autosave-status]');
    let timer = null;
    let inFlight = false;
    let queued = false;
    let submitAfter = false;
    let submitter = null;

    const showStatus = function (kind) {
      if (!status) return;
      status.textContent = status.dataset[kind] || '';
      status.classList.toggle('text-success', kind === 'saved');
      status.classList.toggle('text-danger', kind === 'invalid');
    };

    const refreshPreview = function (previewPath) {
      if (!previewPath) return;
      const container = document.querySelector('[data-design-preview-container]');
      if (!container) return;
      let frame = container.querySelector('[data-design-preview]');
      if (!frame) {
        frame = document.createElement('iframe');
        frame.className = 'admin-design-preview';
        frame.title = container.dataset.previewTitle || 'Design preview';
        frame.loading = 'lazy';
        frame.setAttribute('data-design-preview', '');
        container.querySelector('[data-preview-empty]')?.remove();
        container.appendChild(frame);
      }
      const url = new URL(previewPath, window.location.origin);
      url.searchParams.set('autosave', Date.now().toString());
      frame.src = url.pathname + url.search;
    };

    const save = async function () {
      if (inFlight) {
        queued = true;
        return;
      }
      inFlight = true;
      queued = false;
      showStatus('saving');
      try {
        const response = await fetch(form.dataset.autosaveUrl, {
          method: 'POST',
          body: new FormData(form),
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' },
        });
        const result = await response.json();
        if (!response.ok || !result.ok) {
          showStatus('invalid');
        } else {
          showStatus('saved');
          refreshPreview(result.preview_path);
        }
      } catch {
        showStatus('invalid');
      } finally {
        inFlight = false;
        if (submitAfter) {
          submitAfter = false;
          form.requestSubmit(submitter);
        } else if (queued) {
          window.clearTimeout(timer);
          timer = window.setTimeout(save, 0);
        }
      }
    };

    const schedule = function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(save, 1200);
    };
    form.addEventListener('input', schedule);
    form.addEventListener('change', schedule);
    form.addEventListener('submit', function (event) {
      window.clearTimeout(timer);
      queued = false;
      if (inFlight) {
        event.preventDefault();
        submitAfter = true;
        submitter = event.submitter;
      }
    });
  });
});

/* Section drag-and-drop reorder (#127): progressive enhancement over the
   up/down buttons, which remain the keyboard and no-JS path. On drop the
   full order posts to the order endpoint — the server validates it is a
   permutation. */
document.addEventListener('DOMContentLoaded', function () {
  const orderForm = document.querySelector('[data-section-order-form]');
  if (!orderForm) return;
  const tbody = document.querySelector('tr[data-section-key]')?.closest('tbody');
  if (!tbody) return;
  let dragged = null;
  tbody.querySelectorAll('tr[data-section-key]').forEach(function (row) {
    row.addEventListener('dragstart', function () { dragged = row; row.classList.add('admin-dragging'); });
    row.addEventListener('dragend', function () { row.classList.remove('admin-dragging'); });
    row.addEventListener('dragover', function (event) {
      event.preventDefault();
      if (!dragged || dragged === row) return;
      const after = (event.clientY - row.getBoundingClientRect().top) > row.offsetHeight / 2;
      row.parentNode.insertBefore(dragged, after ? row.nextSibling : row);
    });
    row.addEventListener('drop', function (event) {
      event.preventDefault();
      tbody.querySelectorAll('tr[data-section-key]').forEach(function (item) {
        const field = document.createElement('input');
        field.type = 'hidden';
        field.name = 'key_order';
        field.value = item.dataset.sectionKey;
        orderForm.appendChild(field);
      });
      orderForm.submit();
    });
  });
});

/* Editorial calendar (#132): drag a scheduled chip onto a day cell to
   reschedule; the entry editor's date field remains the no-JS path. */
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('[data-calendar-form]');
  if (!form) return;
  let dragged = null;
  document.querySelectorAll('.admin-calendar-chip[draggable]').forEach(function (chip) {
    chip.addEventListener('dragstart', function () { dragged = chip; });
  });
  document.querySelectorAll('[data-calendar-day]').forEach(function (cell) {
    cell.addEventListener('dragover', function (event) { if (dragged) event.preventDefault(); });
    cell.addEventListener('drop', function (event) {
      event.preventDefault();
      if (!dragged) return;
      form.querySelector('[name=kind]').value = dragged.dataset.chipKind;
      form.querySelector('[name=entity_id]').value = dragged.dataset.chipId;
      form.querySelector('[name=day]').value = cell.dataset.calendarDay;
      form.submit();
    });
  });
});
