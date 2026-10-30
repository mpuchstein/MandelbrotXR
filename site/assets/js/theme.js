// Colour theme: follows prefers-color-scheme unless the visitor picks light or dark.
// Loaded synchronously in <head> (external file, CSP-safe) so the stored choice applies before first paint.
(function () {
  "use strict";
  var KEY = "mxr-theme", root = document.documentElement;
  function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function set(v) { try { if (v) localStorage.setItem(KEY, v); else localStorage.removeItem(KEY); } catch (e) { /* storage blocked */ } }
  function apply(v) { if (v === "light" || v === "dark") root.setAttribute("data-theme", v); else root.removeAttribute("data-theme"); }
  apply(get());
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var order = [null, "light", "dark"], names = { null: "Auto", light: "Light", dark: "Dark" };
    function label() {
      var v = get();
      v = v === "light" || v === "dark" ? v : null;
      btn.querySelector(".theme-text").textContent = names[v];
      btn.setAttribute("aria-label", "Colour theme: " + (v ? v : "follows system") + ". Activate to change.");
    }
    btn.hidden = false;
    label();
    btn.addEventListener("click", function () {
      var cur = get(), next = order[(order.indexOf(cur === "light" || cur === "dark" ? cur : null) + 1) % order.length];
      set(next); apply(next); label();
    });
  });
})();
