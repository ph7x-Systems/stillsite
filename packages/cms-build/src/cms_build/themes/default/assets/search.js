/* <site-search> — progressive-enhancement island (ADR-0010).
 *
 * Filters the blog listing client-side using the per-language
 * search-index.json the builder emits. The page is complete without this
 * script; the element upgrades in place and makes no external requests.
 */

class SiteSearch extends HTMLElement {
  connectedCallback() {
    if (this._upgraded) return;
    this._upgraded = true;
    this._index = null;

    const label = this.getAttribute("label") || "Search";
    this.innerHTML = `
      <form role="search" class="site-search-form">
        <label>
          <span class="site-search-label">${label}</span>
          <input class="hoo-input-text" type="search" name="q" autocomplete="off">
        </label>
      </form>
      <p class="site-search-count" aria-live="polite" hidden></p>
      <ul class="site-search-results" hidden></ul>
    `;
    this._form = this.querySelector("form");
    this._input = this.querySelector("input");
    this._count = this.querySelector(".site-search-count");
    this._results = this.querySelector(".site-search-results");

    this._form.addEventListener("submit", (event) => event.preventDefault());
    this._input.addEventListener("input", () => this._onInput());
  }

  async _load() {
    if (this._index) return this._index;
    const url = this.getAttribute("index-url");
    const response = await fetch(url, { credentials: "omit" });
    this._index = response.ok ? await response.json() : [];
    return this._index;
  }

  async _onInput() {
    const query = this._input.value.trim().toLowerCase();
    if (!query) {
      this._render([]);
      return;
    }
    const index = await this._load();
    const matches = index.filter((entry) =>
      [entry.t, entry.e, entry.c]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(query))
    );
    this._render(matches, query);
  }

  _render(matches, query) {
    const active = Boolean(query);
    this._count.hidden = !active;
    this._results.hidden = !active;
    if (!active) {
      this._results.replaceChildren();
      this._count.textContent = "";
      return;
    }
    this._count.textContent = String(matches.length);
    this._results.replaceChildren(
      ...matches.map((entry) => {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = entry.u;
        link.textContent = entry.t;
        item.appendChild(link);
        if (entry.e) {
          const summary = document.createElement("p");
          summary.textContent = entry.e;
          item.appendChild(summary);
        }
        return item;
      })
    );
  }
}

customElements.define("site-search", SiteSearch);
