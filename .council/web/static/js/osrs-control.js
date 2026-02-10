(function () {
  "use strict";

  const STORAGE_BACKEND_URL = "osrs-control.backend-url";
  const STORAGE_EMBED_PATH = "osrs-control.embed-path";
  const DEFAULT_BACKEND_URL = "http://127.0.0.1:8001";
  const DEFAULT_EMBED_PATH = "/";
  const DEFAULT_RUNTIME_PORT = 8001;
  const SNAPSHOT_MODES = [
    "auto",
    "main",
    "ironman",
    "hardcore",
    "ultimate",
    "deadman",
    "tournament",
    "seasonal",
  ];
  const ACCOUNT_MODES = SNAPSHOT_MODES.filter((mode) => mode !== "auto");

  const state = {
    view: "dashboard",
    baseUrl: DEFAULT_BACKEND_URL,
    embedPath: DEFAULT_EMBED_PATH,
    lastHealth: null,
    accounts: [],
    snapshots: [],
    runtime: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function text(el, value) {
    if (!el) {
      return;
    }
    el.textContent = value == null ? "" : String(value);
  }

  function escapeHtml(input) {
    return String(input ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function normalizeBaseUrl(value) {
    const raw = String(value ?? "").trim();
    if (!raw) {
      return DEFAULT_BACKEND_URL;
    }
    return raw.replace(/\/+$/, "");
  }

  function normalizeEmbedPath(value) {
    const raw = String(value ?? "").trim();
    if (!raw) {
      return DEFAULT_EMBED_PATH;
    }
    return raw.startsWith("/") ? raw : `/${raw}`;
  }

  function fullEmbedUrl() {
    return `${state.baseUrl}${state.embedPath}`;
  }

  function apiUrl(path) {
    return `${state.baseUrl}/api${path}`;
  }

  function parseRuntimePort() {
    try {
      const parsed = new URL(state.baseUrl);
      if (parsed.port) {
        return Number(parsed.port);
      }
      return parsed.protocol === "https:" ? 443 : 80;
    } catch (_error) {
      return DEFAULT_RUNTIME_PORT;
    }
  }

  function formatTime(isoValue) {
    if (!isoValue) {
      return "-";
    }
    const ts = new Date(isoValue);
    if (Number.isNaN(ts.getTime())) {
      return String(isoValue);
    }
    return ts.toLocaleString();
  }

  function statusTone(dotId, kind) {
    const dot = byId(dotId);
    if (!dot) {
      return;
    }
    dot.classList.remove("osrs-dot--healthy", "osrs-dot--warning", "osrs-dot--error");
    if (kind === "healthy") {
      dot.classList.add("osrs-dot--healthy");
    } else if (kind === "warning") {
      dot.classList.add("osrs-dot--warning");
    } else if (kind === "error") {
      dot.classList.add("osrs-dot--error");
    }
  }

  function setBackendStatus(label, detail, toneKind) {
    text(byId("backendStatusLabel"), label);
    text(byId("backendStatusDetail"), detail);
    statusTone("backendStatusDot", toneKind);
  }

  function setRuntimeStatus(label, detail, toneKind) {
    text(byId("runtimeStatusLabel"), label);
    text(byId("runtimeStatusDetail"), detail);
    statusTone("runtimeStatusDot", toneKind);
  }

  function setLastRefreshLabel() {
    const now = new Date();
    text(byId("lastHealthCheckedAt"), `Last checked: ${now.toLocaleTimeString()}`);
  }

  function getCouncilAuthHeaders() {
    if (window.API && typeof window.API.getAuthHeaders === "function") {
      return window.API.getAuthHeaders();
    }

    const headers = {};
    const token = window.localStorage.getItem("session_token");
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const councilId =
      window.sessionStorage.getItem("activeCouncilId") ||
      window.localStorage.getItem("selectedCouncil");
    if (councilId) {
      headers["X-Council-Id"] = councilId;
    }
    return headers;
  }

  async function parseResponse(response) {
    const raw = await response.text();
    let parsed = null;
    if (raw) {
      try {
        parsed = JSON.parse(raw);
      } catch (_err) {
        parsed = null;
      }
    }
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      if (parsed && typeof parsed === "object" && parsed.detail) {
        message = `${message}: ${parsed.detail}`;
      } else if (raw) {
        message = `${message}: ${raw.slice(0, 220)}`;
      }
      throw new Error(message);
    }
    return parsed;
  }

  async function getJson(url, options = {}) {
    const req = {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      ...options,
    };
    const response = await fetch(url, req);
    return parseResponse(response);
  }

  async function getCouncilJson(endpoint, options = {}) {
    const { headers: inputHeaders = {}, ...rest } = options;
    const req = {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...getCouncilAuthHeaders(),
        ...inputHeaders,
      },
      ...rest,
    };
    const response = await fetch(endpoint, req);
    return parseResponse(response);
  }

  function applyViewFilters() {
    const scoped = document.querySelectorAll("[data-show-on]");
    scoped.forEach((el) => {
      const allow = String(el.getAttribute("data-show-on") || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const visible = allow.length === 0 || allow.includes("all") || allow.includes(state.view);
      el.classList.toggle("osrs-hidden", !visible);
    });
  }

  function setInputValues() {
    const baseInput = byId("backendBaseUrlInput");
    if (baseInput) {
      baseInput.value = state.baseUrl;
    }
    const embedInput = byId("embedPathInput");
    if (embedInput) {
      embedInput.value = state.embedPath;
    }
  }

  function syncEmbeddedFrame() {
    const frame = byId("embeddedBackendFrame");
    if (!frame) {
      return;
    }
    frame.src = fullEmbedUrl();
  }

  function renderRuntimeState(runtime) {
    const info = runtime && typeof runtime === "object" ? runtime : {};
    const running = Boolean(info.running);
    const conflict = Boolean(info.single_instance_conflict);
    const managed = Boolean(info.managed);
    const port = info.port ?? parseRuntimePort();
    const managedPid = info.managed_pid ?? "-";
    const canStart = Boolean(info.can_start);

    text(byId("runtimePortValue"), String(port));
    text(byId("runtimePidValue"), String(managedPid));
    text(byId("runtimeManagedValue"), managed ? "yes" : "no");
    text(byId("runtimeConflictValue"), conflict ? "yes" : "no");

    if (conflict) {
      setRuntimeStatus(
        "Conflict",
        "Another matching process is online. Resolve conflict before starting a new instance.",
        "error"
      );
    } else if (running) {
      setRuntimeStatus(
        "Running",
        managed
          ? "Council is tracking a managed OSRS backend process."
          : "Backend is online but not currently marked as managed.",
        "healthy"
      );
    } else {
      setRuntimeStatus(
        "Stopped",
        "No OSRS backend runtime detected for this council.",
        "warning"
      );
    }

    const startBtn = byId("startRuntimeBtn");
    if (startBtn) {
      startBtn.disabled = running || conflict || !canStart;
    }
    const stopBtn = byId("stopRuntimeBtn");
    if (stopBtn) {
      stopBtn.disabled = !running;
    }
  }

  async function checkBackendHealth() {
    setBackendStatus("Checking...", `GET ${apiUrl("/health")}`, "warning");
    try {
      const health = await getJson(apiUrl("/health"));
      state.lastHealth = health || {};

      const stats = (state.lastHealth && state.lastHealth.stats) || {};
      text(byId("kvHealthStatus"), state.lastHealth.status || "unknown");
      text(byId("kvAccountCount"), stats.accounts ?? "-");
      text(byId("kvSnapshotCount"), stats.snapshots ?? "-");
      text(byId("kvSchemaVersion"), stats.schema_version ?? "-");

      if (state.lastHealth.status === "healthy") {
        setBackendStatus("Healthy", "Backend reachable and DB connected.", "healthy");
      } else {
        setBackendStatus(
          state.lastHealth.status || "Unhealthy",
          state.lastHealth.error || "Backend responded with a non-healthy status.",
          "warning"
        );
      }
    } catch (error) {
      setBackendStatus(
        "Unavailable",
        `${error.message}. If this is CORS, restart backend with Council origin allowed.`,
        "error"
      );
      text(byId("kvHealthStatus"), "unreachable");
      text(byId("kvAccountCount"), "-");
      text(byId("kvSnapshotCount"), "-");
      text(byId("kvSchemaVersion"), "-");
    } finally {
      setLastRefreshLabel();
    }
  }

  async function loadRuntimeStatus() {
    const runtimePort = parseRuntimePort();
    setRuntimeStatus("Checking...", "Loading Council runtime state...", "warning");
    try {
      const runtime = await getCouncilJson(`/api/osrs/runtime/status?port=${encodeURIComponent(runtimePort)}`);
      state.runtime = runtime || {};
      renderRuntimeState(state.runtime);
      text(byId("runtimeActionStatus"), "Runtime status refreshed.");
    } catch (error) {
      state.runtime = null;
      setRuntimeStatus("Unavailable", `Failed to load runtime status: ${error.message}`, "error");
      text(byId("runtimePortValue"), String(runtimePort));
      text(byId("runtimePidValue"), "-");
      text(byId("runtimeManagedValue"), "-");
      text(byId("runtimeConflictValue"), "-");
      text(byId("runtimeActionStatus"), `Runtime status failed: ${error.message}`);
      const startBtn = byId("startRuntimeBtn");
      if (startBtn) {
        startBtn.disabled = false;
      }
      const stopBtn = byId("stopRuntimeBtn");
      if (stopBtn) {
        stopBtn.disabled = true;
      }
    }
  }

  async function startRuntime() {
    const runtimePort = parseRuntimePort();
    const statusBox = byId("runtimeActionStatus");
    text(statusBox, `Starting OSRS backend on port ${runtimePort}...`);

    try {
      const payload = {
        port: runtimePort,
        wait_seconds: 30.0,
      };

      const runtime = await getCouncilJson("/api/osrs/runtime/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      state.runtime = runtime || {};
      renderRuntimeState(state.runtime);
      text(statusBox, runtime?.message || "Backend start request accepted.");

      await Promise.all([loadCouncilProcesses(), checkBackendHealth()]);
    } catch (error) {
      text(statusBox, `Start failed: ${error.message}`);
    } finally {
      await loadRuntimeStatus();
    }
  }

  async function stopRuntime() {
    const runtimePort = parseRuntimePort();
    const statusBox = byId("runtimeActionStatus");
    text(statusBox, "Stopping OSRS backend...");

    try {
      const runtime = await getCouncilJson(`/api/osrs/runtime/stop?port=${encodeURIComponent(runtimePort)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          confirm: true,
          grace_seconds: 4.0,
          force_kill: true,
        }),
      });

      state.runtime = runtime || {};
      renderRuntimeState(state.runtime);
      text(statusBox, runtime?.message || "Backend stop request completed.");

      await Promise.all([loadCouncilProcesses(), checkBackendHealth()]);
    } catch (error) {
      text(statusBox, `Stop failed: ${error.message}`);
    } finally {
      await loadRuntimeStatus();
    }
  }

  async function loadAccounts() {
    const tableBody = byId("accountsTableBody");
    if (!tableBody) {
      return;
    }

    tableBody.innerHTML = "<tr><td colspan='6'>Loading accounts...</td></tr>";
    try {
      const payload = await getJson(apiUrl("/accounts/?page=1&page_size=200&active_only=true"));
      const accounts = Array.isArray(payload?.accounts) ? payload.accounts : [];
      state.accounts = accounts;

      if (!accounts.length) {
        tableBody.innerHTML = "<tr><td colspan='6'>No accounts found.</td></tr>";
        return;
      }

      tableBody.innerHTML = accounts
        .map((account) => {
          const name = escapeHtml(account.name || "-");
          const display = escapeHtml(account.display_name || "-");
          const mode = escapeHtml(account.default_mode || "-");
          const snapshots = account.total_snapshots ?? "-";
          const latest = formatTime(account.latest_snapshot);
          const deleteKey = encodeURIComponent(account.name || "");

          return `
            <tr>
              <td><code>${name}</code></td>
              <td>${display}</td>
              <td>${mode}</td>
              <td>${snapshots}</td>
              <td>${escapeHtml(latest)}</td>
              <td>
                <span class="osrs-actions">
                  <button class="osrs-btn osrs-btn--danger osrs-btn--small" data-delete-account="${deleteKey}">Delete</button>
                </span>
              </td>
            </tr>
          `;
        })
        .join("");
    } catch (error) {
      tableBody.innerHTML = `<tr><td colspan='6'>Failed to load accounts: ${escapeHtml(error.message)}</td></tr>`;
    }
  }

  async function createAccount(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const name = String(form.elements.account_name?.value || "").trim();
    const displayName = String(form.elements.display_name?.value || "").trim();
    const mode = String(form.elements.account_mode?.value || "main").trim().toLowerCase();
    const statusBox = byId("accountActionStatus");

    if (!name) {
      text(statusBox, "Account name is required.");
      return;
    }

    const payload = {
      name,
      display_name: displayName || null,
      default_mode: mode || "main",
      active: true,
      metadata: {},
    };

    try {
      await getJson(apiUrl("/accounts/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });
      text(statusBox, `Created account ${name}.`);
      form.reset();
      if (form.elements.account_mode) {
        form.elements.account_mode.value = "main";
      }
      await loadAccounts();
      await checkBackendHealth();
    } catch (error) {
      text(statusBox, `Create failed: ${error.message}`);
    }
  }

  async function deleteAccount(accountName) {
    if (!accountName) {
      return;
    }
    const confirmed = window.confirm(`Delete account "${accountName}" and all associated snapshot records?`);
    if (!confirmed) {
      return;
    }

    const statusBox = byId("accountActionStatus");
    text(statusBox, `Deleting ${accountName}...`);
    try {
      await getJson(apiUrl(`/accounts/${encodeURIComponent(accountName)}`), {
        method: "DELETE",
      });
      text(statusBox, `Deleted ${accountName}.`);
      await loadAccounts();
      await loadLatestSnapshots();
      await checkBackendHealth();
    } catch (error) {
      text(statusBox, `Delete failed: ${error.message}`);
    }
  }

  function renderRunResults(results) {
    const container = byId("snapshotRunResults");
    if (!container) {
      return;
    }
    if (!Array.isArray(results) || !results.length) {
      container.innerHTML = "<div class='osrs-inline-note'>No result payload returned.</div>";
      return;
    }

    container.innerHTML = results
      .map((result) => {
        const ok = Boolean(result?.success);
        const tone = ok ? "osrs-tag--ok" : "osrs-tag--error";
        const label = ok ? "success" : "failed";
        const player = escapeHtml(result?.player || "-");
        const mode = escapeHtml(result?.resolved_mode || "-");
        const message = escapeHtml(result?.message || "");
        const delta = escapeHtml(result?.delta_summary || "");
        const path = escapeHtml(result?.snapshot_path || "");

        return `
          <div class="osrs-result-row">
            <div class="osrs-row">
              <span class="osrs-tag ${tone}">${label}</span>
              <span class="osrs-tag">${player}</span>
              <span class="osrs-tag">${mode}</span>
            </div>
            <div>${message}</div>
            ${delta ? `<div class="osrs-muted">${delta}</div>` : ""}
            ${path ? `<code>${path}</code>` : ""}
          </div>
        `;
      })
      .join("");
  }

  async function runSnapshot(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const player = String(form.elements.snapshot_player?.value || "").trim();
    const mode = String(form.elements.snapshot_mode?.value || "auto").trim().toLowerCase();
    const statusBox = byId("snapshotRunStatus");

    if (!player) {
      text(statusBox, "Player name is required.");
      return;
    }

    text(statusBox, `Running snapshot for ${player}...`);
    renderRunResults([]);

    try {
      const payload = { player, mode };
      const result = await getJson(apiUrl("/snapshots/run"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });

      text(statusBox, `Snapshot run completed for ${player}.`);
      renderRunResults(result?.results || []);
      await loadLatestSnapshots();
      await checkBackendHealth();
    } catch (error) {
      text(statusBox, `Snapshot run failed: ${error.message}`);
    }
  }

  async function loadLatestSnapshots() {
    const body = byId("latestSnapshotsTableBody");
    if (!body) {
      return;
    }

    body.innerHTML = "<tr><td colspan='7'>Loading snapshots...</td></tr>";
    try {
      const rows = await getJson(apiUrl("/snapshots/latest?limit=25"));
      const snapshots = Array.isArray(rows) ? rows : [];
      state.snapshots = snapshots;

      if (!snapshots.length) {
        body.innerHTML = "<tr><td colspan='7'>No snapshots available.</td></tr>";
        return;
      }

      body.innerHTML = snapshots
        .map((row) => {
          const snapshotId = row.snapshot_id || "-";
          const account = row.account_name || row.player || "-";
          const mode = row.resolved_mode || "-";
          const fetchedAt = formatTime(row.fetched_at);
          const totalLevel = row.total_level ?? "-";
          const totalXp = row.total_xp ?? "-";
          const rawLink = `${apiUrl(`/snapshots/${encodeURIComponent(snapshotId)}/raw`)}`;
          const reportLink = `${apiUrl(`/snapshots/${encodeURIComponent(snapshotId)}/report`)}`;

          return `
            <tr>
              <td><code>${escapeHtml(snapshotId)}</code></td>
              <td>${escapeHtml(account)}</td>
              <td>${escapeHtml(mode)}</td>
              <td>${escapeHtml(String(totalLevel))}</td>
              <td>${escapeHtml(String(totalXp))}</td>
              <td>${escapeHtml(fetchedAt)}</td>
              <td>
                <span class="osrs-actions">
                  <a class="osrs-btn osrs-btn--ghost osrs-btn--small" href="${rawLink}" target="_blank" rel="noopener">Raw</a>
                  <a class="osrs-btn osrs-btn--ghost osrs-btn--small" href="${reportLink}" target="_blank" rel="noopener">Report</a>
                </span>
              </td>
            </tr>
          `;
        })
        .join("");
    } catch (error) {
      body.innerHTML = `<tr><td colspan='7'>Failed to load snapshots: ${escapeHtml(error.message)}</td></tr>`;
    }
  }

  async function loadCouncilProcesses() {
    const body = byId("processTableBody");
    if (!body) {
      return;
    }

    body.innerHTML = "<tr><td colspan='6'>Loading process list...</td></tr>";
    try {
      const payload = await getCouncilJson("/api/processes");
      const list = Array.isArray(payload?.processes) ? payload.processes : [];

      if (!list.length) {
        body.innerHTML = "<tr><td colspan='6'>No managed processes reported by Council.</td></tr>";
        return;
      }

      body.innerHTML = list
        .map((processRow) => {
          const pid = processRow.pid ?? "-";
          const type = processRow.process_type ?? "-";
          const status = processRow.status ?? "-";
          const started = formatTime(processRow.started_at);
          const heartbeat = formatTime(processRow.last_heartbeat);
          const restarts = processRow.restart_count ?? 0;
          return `
            <tr>
              <td>${escapeHtml(String(pid))}</td>
              <td>${escapeHtml(String(type))}</td>
              <td>${escapeHtml(String(status))}</td>
              <td>${escapeHtml(started)}</td>
              <td>${escapeHtml(heartbeat)}</td>
              <td>${escapeHtml(String(restarts))}</td>
            </tr>
          `;
        })
        .join("");
    } catch (error) {
      body.innerHTML = `<tr><td colspan='6'>Failed to load Council processes: ${escapeHtml(error.message)}</td></tr>`;
    }
  }

  async function copyText(content, doneLabelEl) {
    try {
      await navigator.clipboard.writeText(content);
      if (doneLabelEl) {
        doneLabelEl.textContent = "Copied.";
      }
    } catch (_error) {
      if (doneLabelEl) {
        doneLabelEl.textContent = "Clipboard blocked.";
      }
    } finally {
      if (doneLabelEl) {
        window.setTimeout(() => {
          doneLabelEl.textContent = "";
        }, 1800);
      }
    }
  }

  function populateModeSelect(selectId, options, defaultValue) {
    const select = byId(selectId);
    if (!select) {
      return;
    }
    select.innerHTML = options.map((mode) => `<option value="${mode}">${mode}</option>`).join("");
    select.value = defaultValue;
  }

  function buildCommandHints() {
    const startCommand = `CORS_ALLOWED_ORIGINS="http://localhost:8000,${window.location.origin}" OSRS_BACKEND_PORT=8001 ./scripts/start_osrs_backend.sh`;
    const corsCommand = `export CORS_ALLOWED_ORIGINS="http://localhost:8000,${window.location.origin}"`;

    text(byId("startCommandText"), startCommand);
    text(byId("corsCommandText"), corsCommand);

    const copyStart = byId("copyStartCmdBtn");
    if (copyStart) {
      copyStart.addEventListener("click", async () => {
        await copyText(startCommand, byId("copyStartCmdState"));
      });
    }

    const copyCors = byId("copyCorsCmdBtn");
    if (copyCors) {
      copyCors.addEventListener("click", async () => {
        await copyText(corsCommand, byId("copyCorsCmdState"));
      });
    }
  }

  function bindEvents() {
    const saveBackendBtn = byId("saveBackendBtn");
    if (saveBackendBtn) {
      saveBackendBtn.addEventListener("click", () => {
        const baseInput = byId("backendBaseUrlInput");
        state.baseUrl = normalizeBaseUrl(baseInput ? baseInput.value : state.baseUrl);
        window.localStorage.setItem(STORAGE_BACKEND_URL, state.baseUrl);
        setInputValues();
        syncEmbeddedFrame();
        checkBackendHealth();
        loadAccounts();
        loadLatestSnapshots();
        loadRuntimeStatus();
      });
    }

    const checkBackendBtn = byId("checkBackendBtn");
    if (checkBackendBtn) {
      checkBackendBtn.addEventListener("click", async () => {
        await checkBackendHealth();
      });
    }

    const openBackendBtn = byId("openBackendBtn");
    if (openBackendBtn) {
      openBackendBtn.addEventListener("click", () => {
        window.open(fullEmbedUrl(), "_blank", "noopener");
      });
    }

    const loadEmbedBtn = byId("loadEmbedBtn");
    if (loadEmbedBtn) {
      loadEmbedBtn.addEventListener("click", () => {
        const embedInput = byId("embedPathInput");
        state.embedPath = normalizeEmbedPath(embedInput ? embedInput.value : state.embedPath);
        window.localStorage.setItem(STORAGE_EMBED_PATH, state.embedPath);
        setInputValues();
        syncEmbeddedFrame();
      });
    }

    const refreshAccountsBtn = byId("refreshAccountsBtn");
    if (refreshAccountsBtn) {
      refreshAccountsBtn.addEventListener("click", async () => {
        await loadAccounts();
      });
    }

    const refreshSnapshotsBtn = byId("refreshSnapshotsBtn");
    if (refreshSnapshotsBtn) {
      refreshSnapshotsBtn.addEventListener("click", async () => {
        await loadLatestSnapshots();
      });
    }

    const refreshProcessesBtn = byId("refreshProcessesBtn");
    if (refreshProcessesBtn) {
      refreshProcessesBtn.addEventListener("click", async () => {
        await loadCouncilProcesses();
      });
    }

    const runtimeRefreshBtn = byId("runtimeRefreshBtn");
    if (runtimeRefreshBtn) {
      runtimeRefreshBtn.addEventListener("click", async () => {
        await loadRuntimeStatus();
      });
    }

    const startRuntimeBtn = byId("startRuntimeBtn");
    if (startRuntimeBtn) {
      startRuntimeBtn.addEventListener("click", async () => {
        await startRuntime();
      });
    }

    const stopRuntimeBtn = byId("stopRuntimeBtn");
    if (stopRuntimeBtn) {
      stopRuntimeBtn.addEventListener("click", async () => {
        await stopRuntime();
      });
    }

    const accountForm = byId("accountCreateForm");
    if (accountForm) {
      accountForm.addEventListener("submit", createAccount);
    }

    const snapshotForm = byId("snapshotRunForm");
    if (snapshotForm) {
      snapshotForm.addEventListener("submit", runSnapshot);
    }

    const accountsBody = byId("accountsTableBody");
    if (accountsBody) {
      accountsBody.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
          return;
        }
        const button = target.closest("button[data-delete-account]");
        if (!button) {
          return;
        }
        const encoded = button.getAttribute("data-delete-account");
        const accountName = decodeURIComponent(encoded || "");
        await deleteAccount(accountName);
      });
    }
  }

  async function boot() {
    const root = document.querySelector("[data-osrs-control-root]");
    if (!(root instanceof HTMLElement)) {
      return;
    }

    state.view = String(root.dataset.view || "dashboard").trim().toLowerCase();
    state.baseUrl = normalizeBaseUrl(
      window.localStorage.getItem(STORAGE_BACKEND_URL) ||
        root.dataset.defaultBackendUrl ||
        DEFAULT_BACKEND_URL
    );
    state.embedPath = normalizeEmbedPath(
      window.localStorage.getItem(STORAGE_EMBED_PATH) || DEFAULT_EMBED_PATH
    );

    populateModeSelect("snapshotModeSelect", SNAPSHOT_MODES, "auto");
    populateModeSelect("accountModeSelect", ACCOUNT_MODES, "main");

    applyViewFilters();
    setInputValues();
    buildCommandHints();
    bindEvents();
    syncEmbeddedFrame();

    await checkBackendHealth();
    await Promise.all([
      loadAccounts(),
      loadLatestSnapshots(),
      loadCouncilProcesses(),
      loadRuntimeStatus(),
    ]);
  }

  window.addEventListener("DOMContentLoaded", () => {
    boot();
  });
})();
