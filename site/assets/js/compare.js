// Compare picker. Every pair has its own pre-rendered page, compare/<a>-vs-<b>/, so the URL is the selection.
// - On compare/ (index): ?a=<slug>&b=<slug> (or #a=…&b=…) redirects to that pair page with location.replace.
// - On every page with the picker: changing a select opens the chosen pair at once (the form says so up
//   front); picking the slug already chosen on the other side swaps the two; submit goes straight there.
// Valid slugs come from the <select> options, never from this file. Without JavaScript the form submits to
// compare/?a&b and the server-rendered list of every pair page stays usable.
(() => {
  "use strict";
  const form = document.querySelector("form[data-compare-base]");
  if (!form) return;
  const selA = form.querySelector('select[name="a"]');
  const selB = form.querySelector('select[name="b"]');
  const status = form.querySelector("[data-cmp-status]");
  if (!selA || !selB) return;
  const base = new URL(form.getAttribute("data-compare-base"), location.href);
  const slugs = new Set(Array.from(selA.options, (o) => o.value));

  const say = (text) => {
    if (status && status.textContent !== text) status.textContent = text;
  };
  const pairUrl = (a, b) => new URL(`${encodeURIComponent(a)}-vs-${encodeURIComponent(b)}/`, base).href;
  const go = (a, b, replace) => {
    if (!slugs.has(a) || !slugs.has(b)) return false;
    if (a === b) {
      say("Pick two different candidates.");
      return false;
    }
    say("Opening the comparison…");
    if (replace) location.replace(pairUrl(a, b));
    else location.assign(pairUrl(a, b));
    return true;
  };

  // Index page: honour ?a&b or #a=…&b=… by redirecting to the pre-rendered pair page.
  const onIndex = base.pathname === location.pathname || base.pathname === location.pathname.replace(/index\.html$/, "");
  if (onIndex) {
    const q = new URLSearchParams(location.search);
    const h = new URLSearchParams(location.hash.replace(/^#/, ""));
    const a = q.get("a") || h.get("a");
    const b = q.get("b") || h.get("b");
    if (a !== null || b !== null) {
      const bad = [a, b].filter((s) => s !== null && !slugs.has(s));
      if (bad.length) {
        console.warn("compare: unknown candidate slug(s)", bad);
        say(`Unknown candidate: ${bad.join(", ")}. Pick two from the lists.`);
      }
      if (a !== null && slugs.has(a)) selA.value = a;
      if (b !== null && slugs.has(b)) selB.value = b;
      if (a !== null && b !== null && !bad.length && go(a, b, true)) return;
    }
  }

  // Changing one side to the value of the other swaps them, so the pair is never A = A.
  const prev = new Map([[selA, selA.value], [selB, selB.value]]);
  const onChange = (sel, other) => {
    if (sel.value === other.value) other.value = prev.get(sel);
    prev.set(selA, selA.value);
    prev.set(selB, selB.value);
    go(selA.value, selB.value, false);
  };
  // Back/forward: show the selection this page stands for, not the one the user changed before leaving.
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    form.reset();
    prev.set(selA, selA.value);
    prev.set(selB, selB.value);
    say("");
  });
  selA.addEventListener("change", () => onChange(selA, selB));
  selB.addEventListener("change", () => onChange(selB, selA));
  form.addEventListener("submit", (e) => {
    if (go(selA.value, selB.value, false) || selA.value === selB.value) e.preventDefault();
  });
})();
