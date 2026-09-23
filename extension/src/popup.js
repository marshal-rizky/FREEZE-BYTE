// Popup: status situs yang sedang dibuka dan izin opt-in untuk situs di luar
// daftar bawaan. Izin diminta untuk satu origin saja, lalu content script
// didaftarkan untuk origin itu dan bertahan antar sesi.
const SCRIPTS = ["src/detect.js", "src/verdict.js", "src/anchors.js", "src/overlay.js", "src/content.js"];

document.addEventListener("DOMContentLoaded", async () => {
  const status = document.getElementById("status");
  const button = document.getElementById("enable");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  let url;
  try { url = new URL(tab.url); } catch (err) { url = null; }
  if (!url || url.protocol !== "https:") {
    status.textContent = "Halaman ini tidak didukung.";
    return;
  }

  const pattern = `${url.origin}/*`;
  if (await chrome.permissions.contains({ origins: [pattern] })) {
    status.textContent = `Aktif di ${url.hostname}.`;
    return;
  }

  status.textContent = `Belum aktif di ${url.hostname}.`;
  button.hidden = false;
  button.addEventListener("click", async () => {
    const granted = await chrome.permissions.request({ origins: [pattern] });
    if (!granted) return;
    const id = `fb-${url.hostname}`;
    const existing = await chrome.scripting.getRegisteredContentScripts({ ids: [id] });
    if (!existing.length) {
      await chrome.scripting.registerContentScripts([{
        id, matches: [pattern], js: SCRIPTS, runAt: "document_idle", persistAcrossSessions: true,
      }]);
    }
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: SCRIPTS });
    status.textContent = `Aktif di ${url.hostname}.`;
    button.hidden = true;
  });
});
