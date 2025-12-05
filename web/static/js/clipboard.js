// Clipboard + copy bar handling for snapshot content (desktop + mobile friendly).
(function () {
  function resolveFeedback(targets, triggerEl) {
    const order = Array.isArray(targets) ? targets.filter(Boolean) : [];
    if (triggerEl) {
      const local = triggerEl.closest(".copy-feedback");
      if (local) return local;
    }
    for (const selector of order) {
      const el = typeof selector === "string" ? document.querySelector(selector) : null;
      if (el) return el;
    }
    return document.getElementById("copy-feedback");
  }

  function setFeedback(message, variant, opts = {}) {
    const el = resolveFeedback(opts.targets, opts.trigger);
    if (!el) return;
    el.innerHTML = `<div class="alert ${variant}">${message}</div>`;
  }

  function looksHtml(text, contentType) {
    const lowered = (contentType || "").toLowerCase();
    if (lowered.includes("text/html")) return true;
    const sample = (text || "").trim().toLowerCase();
    return sample.startsWith("<!doctype") || sample.startsWith("<html");
  }

  function fallbackExecCopy(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  }

  async function writeToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return "clipboard";
      } catch (err) {
        console.warn("Clipboard API failed, trying fallback", err);
      }
    }
    if (fallbackExecCopy(text)) {
      return "fallback";
    }
    throw new Error("Clipboard unavailable");
  }

  async function copyFromUrl(url, type, opts = {}) {
    const targets = opts.feedbackSelectors || [];
    let text = "";
    try {
      const resp = await fetch(url, { headers: { Accept: "text/plain" }, credentials: "same-origin" });
      if (!resp.ok) {
        setFeedback(`Copy failed: ${resp.status} ${resp.statusText || ""}`.trim(), "error", {
          targets,
          trigger: opts.trigger,
        });
        return false;
      }
      text = await resp.text();
      const contentType = resp.headers.get("content-type") || "";
      if (looksHtml(text, contentType)) {
        setFeedback(`Copy failed: received HTML instead of ${type} text`, "error", { targets, trigger: opts.trigger });
        return false;
      }
      const method = await writeToClipboard(text);
      const label = type === "report" ? "report" : type || "content";
      const note = method === "fallback" ? " (fallback used for mobile)" : "";
      setFeedback(`${opts.label ? opts.label + " " : ""}${label} copied to clipboard${note}`, "success", {
        targets,
        trigger: opts.trigger,
      });
      return true;
    } catch (err) {
      // Offer share sheet as a softer fallback when a user gesture exists.
      if (opts.allowShare && navigator.share && text) {
        try {
          await navigator.share({ text });
          setFeedback(`Shared ${type} because clipboard is blocked`, "success", { targets, trigger: opts.trigger });
          return true;
        } catch (shareErr) {
          console.warn("Share fallback failed", shareErr);
        }
      }
      setFeedback(`Copy failed: ${err?.message || "unable to access clipboard"}`, "error", {
        targets,
        trigger: opts.trigger,
      });
      return false;
    }
  }

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
    copyFromUrl(url, btn.dataset.copyType || "content", {
      feedbackSelectors: [btn.dataset.feedbackTarget, "#copy-feedback"],
      trigger: btn,
      allowShare: true,
    });
  });

  // Expose helper to toggle copy mode and set endpoints
  window.snapshotCopyMode = function (type, btn) {
    const copyBar = document.getElementById("copy-actions");
    if (!copyBar) return;
    const reportBtn = document.getElementById("copy-report-btn");
    const jsonBtn = document.getElementById("copy-json-btn");
    const feedbackTarget = btn?.dataset?.feedbackTarget || "#copy-feedback";
    if (type === "report" && reportBtn && btn.dataset.copyReport) {
      reportBtn.dataset.copyUrl = btn.dataset.copyReport;
      reportBtn.setAttribute("data-copy-type", "report");
      reportBtn.dataset.feedbackTarget = feedbackTarget;
      reportBtn.style.display = "inline-block";
      if (jsonBtn) jsonBtn.style.display = "none";
    } else if (type === "json" && jsonBtn && btn.dataset.copyJson) {
      jsonBtn.dataset.copyUrl = btn.dataset.copyJson;
      jsonBtn.setAttribute("data-copy-type", "json");
      jsonBtn.dataset.feedbackTarget = feedbackTarget;
      jsonBtn.style.display = "inline-block";
      if (reportBtn) reportBtn.style.display = "none";
    }
  };

  // Auto-copy helper for snapshot completion flows
  window.autoCopySnapshotReport = function (params) {
    if (!params || !params.snapshotId) return;
    const selectors = Array.isArray(params.feedbackSelectors) ? params.feedbackSelectors.slice() : [];
    selectors.push("#copy-feedback");
    copyFromUrl(`/api/snapshots/${params.snapshotId}/report`, "report", {
      feedbackSelectors: selectors,
      allowShare: false, // avoid auto-opening share sheets on mobile
      label: params.player,
    });
  };
})();
