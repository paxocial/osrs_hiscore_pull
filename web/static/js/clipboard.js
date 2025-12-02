// Clipboard + copy bar handling for snapshot content.
(function () {
  document.addEventListener("htmx:afterSwap", function (evt) {
    // If snapshot-content was updated, show copy bar
    if (evt.target && evt.target.id === "snapshot-content") {
      const copyBar = document.getElementById("copy-actions");
      if (copyBar) copyBar.style.display = "flex";
    }
  });

  // Direct fetch-based copy to avoid HTML swaps or HTMX interference.
  document.addEventListener("click", function (evt) {
    const btn = evt.target.closest("[data-copy-type][data-copy-url]");
    if (!btn) return;
    evt.preventDefault();
    const url = btn.dataset.copyUrl;
    if (!url) return;
    fetch(url, { headers: { Accept: "text/plain" } })
      .then(async (resp) => {
        const text = await resp.text();
        const contentType = (resp.headers.get("content-type") || "").toLowerCase();
        const looksHtml = contentType.includes("text/html") || text.trim().toLowerCase().startsWith("<!doctype");
        const feedback = document.getElementById("copy-feedback");
        if (looksHtml) {
          console.warn("Copy request returned HTML, skipping clipboard write.");
          if (feedback) {
            feedback.innerHTML = `<div class="alert error">Copy failed: received HTML instead of ${btn.dataset.copyType} text</div>`;
          }
          return;
        }
        await navigator.clipboard.writeText(text);
        if (feedback) {
          feedback.innerHTML = `<div class="alert success">Copied ${btn.dataset.copyType} content to clipboard</div>`;
        }
      })
      .catch(() => {
        const feedback = document.getElementById("copy-feedback");
        if (feedback) {
          feedback.innerHTML = `<div class="alert error">Copy failed: unable to fetch or write to clipboard</div>`;
        }
      });
  });

  // Expose helper to toggle copy mode and set endpoints
  window.snapshotCopyMode = function (type, btn) {
    const copyBar = document.getElementById("copy-actions");
    if (!copyBar) return;
    const reportBtn = document.getElementById("copy-report-btn");
    const jsonBtn = document.getElementById("copy-json-btn");
    if (type === "report" && reportBtn && btn.dataset.copyReport) {
      reportBtn.dataset.copyUrl = btn.dataset.copyReport;
      reportBtn.setAttribute("data-copy-type", "report");
      reportBtn.style.display = "inline-block";
      if (jsonBtn) jsonBtn.style.display = "none";
    } else if (type === "json" && jsonBtn && btn.dataset.copyJson) {
      jsonBtn.dataset.copyUrl = btn.dataset.copyJson;
      jsonBtn.setAttribute("data-copy-type", "json");
      jsonBtn.style.display = "inline-block";
      if (reportBtn) reportBtn.style.display = "none";
    }
  };
})();
