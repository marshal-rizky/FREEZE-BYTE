// Cocokkan URL dengan pola match-pattern gaya manifest ("https://a/b*").
// Murni: hanya dipakai popup.js untuk membaca content_scripts[0].matches
// sendiri, tidak pernah dimuat sebagai content script.
(function (root) {
  const ESCAPE = /[.*+?^${}()|[\]\\]/g;
  const escapeRe = (s) => s.replace(ESCAPE, "\\$&");

  function patternToRegExp(pattern) {
    const m = /^https:\/\/([^/]+)(\/.*)$/.exec(pattern);
    if (!m) return null;
    const [, host, path] = m;
    const hostRe = host.startsWith("*.")
      ? `(?:[a-z0-9-]+\\.)*${escapeRe(host.slice(2))}`
      : escapeRe(host);
    const pathRe = path.split("*").map(escapeRe).join(".*");
    return new RegExp(`^https://${hostRe}${pathRe}$`, "i");
  }

  function matchesPattern(url, pattern) {
    const re = patternToRegExp(pattern);
    return !!re && re.test(url);
  }

  function matchesAnyPattern(url, patterns) {
    return patterns.some((p) => matchesPattern(url, p));
  }

  const api = { matchesPattern, matchesAnyPattern };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
