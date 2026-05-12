/**
 * OSRS Control Center -- Dashboard Controller
 * =============================================
 * Named IIFE module for the Control Center (osrs-dashboard) page.
 * Manages runtime controls, health stats, quick snapshots, and recent snapshots.
 *
 * Pattern: Named IIFE exported as window.OsrsControl
 * Dependencies: OsrsCommon (osrs-common.js), API (Council app.js)
 */

const OsrsControl = (() => {
    'use strict';

    // =========================================================================
    // CONFIGURATION
    // =========================================================================

    let _pollTimer = null;
    let _refreshTimer = null;
    const POLL_INTERVAL = 5000;     // 5s for runtime status
    const REFRESH_INTERVAL = 30000; // 30s for health + snapshots
    const RECENT_LIMIT = 10;
    const _dom = {};

    // =========================================================================
    // LIFECYCLE
    // =========================================================================

    function init() {
        _cacheDom();
        if (!_dom.root) return;
        _bindEvents();
        loadRuntimeStatus();
        loadHealth();
        loadRecentSnapshots();
        _startPolling();
        OsrsCommon.listenCouncilSwitch(() => { destroy(); init(); });
    }

    function destroy() {
        if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
        if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }
    }

    function refresh() {
        loadRuntimeStatus();
        loadHealth();
        loadRecentSnapshots();
    }

    // =========================================================================
    // DOM CACHING
    // =========================================================================

    function _cacheDom() {
        _dom.root = document.getElementById('osrs-control-root');
        // Runtime controls
        _dom.statusBadge = document.getElementById('runtime-status-badge');
        _dom.status = document.getElementById('runtime-status');
        _dom.pid = document.getElementById('runtime-pid');
        _dom.port = document.getElementById('runtime-port');
        _dom.uptime = document.getElementById('runtime-uptime');
        _dom.btnStart = document.getElementById('btn-start');
        _dom.btnStop = document.getElementById('btn-stop');
        _dom.btnRefresh = document.getElementById('btn-refresh');
        // Health KPIs
        _dom.healthBadge = document.getElementById('health-status-badge');
        _dom.kpiAccounts = document.getElementById('kpi-accounts');
        _dom.kpiSnapshots = document.getElementById('kpi-snapshots');
        _dom.kpiSchema = document.getElementById('kpi-schema');
        _dom.kpiLastCheck = document.getElementById('kpi-last-check');
        // Snapshot form
        _dom.snapshotForm = document.getElementById('quick-snapshot-form');
        _dom.snapshotPlayer = document.getElementById('snapshot-player');
        _dom.snapshotMode = document.getElementById('snapshot-mode');
        _dom.snapshotStatus = document.getElementById('snapshot-run-status');
        _dom.snapshotResults = document.getElementById('snapshot-run-results');
        // Recent snapshots table
        _dom.snapshotsLoading = document.getElementById('recent-snapshots-loading');
        _dom.snapshotsEmpty = document.getElementById('recent-snapshots-empty');
        _dom.snapshotsTable = document.getElementById('recent-snapshots-table');
        _dom.snapshotsBody = document.getElementById('recent-snapshots-body');
        _dom.btnRefreshSnapshots = document.getElementById('btn-refresh-snapshots');
        // Offline banner
        _dom.offlineBanner = document.getElementById('offline-banner');
        // Toast
        _dom.toast = document.getElementById('osrs-toast');
    }

    // =========================================================================
    // EVENT BINDING
    // =========================================================================

    function _bindEvents() {
        if (_dom.btnStart) {
            _dom.btnStart.addEventListener('click', () => startBackend());
        }
        if (_dom.btnStop) {
            _dom.btnStop.addEventListener('click', () => stopBackend());
        }
        if (_dom.btnRefresh) {
            _dom.btnRefresh.addEventListener('click', () => refresh());
        }
        if (_dom.btnRefreshSnapshots) {
            _dom.btnRefreshSnapshots.addEventListener('click', () => loadRecentSnapshots());
        }
        if (_dom.snapshotForm) {
            _dom.snapshotForm.addEventListener('submit', (e) => runSnapshot(e));
        }
    }

    // =========================================================================
    // POLLING
    // =========================================================================

    function _startPolling() {
        _pollTimer = setInterval(loadRuntimeStatus, POLL_INTERVAL);
        _refreshTimer = setInterval(() => {
            loadHealth();
            loadRecentSnapshots();
        }, REFRESH_INTERVAL);
    }

    // =========================================================================
    // RUNTIME STATUS
    // Calls osrs_runtime.py directly (Council route, NOT proxy)
    // =========================================================================

    async function loadRuntimeStatus() {
        try {
            const headers = _getAuthHeaders();
            const resp = await fetch('/api/osrs/runtime/status', { headers });
            if (!resp.ok) {
                const errBody = await resp.json().catch(() => ({}));
                throw { status: resp.status, message: errBody.detail || `HTTP ${resp.status}` };
            }
            const data = await resp.json();
            _renderRuntimeStatus(data);
        } catch (err) {
            _renderRuntimeStatus({ status: 'error', _error: err.message || String(err) });
        }
    }

    function _renderRuntimeStatus(data) {
        const running = Boolean(data.running);
        const conflict = Boolean(data.single_instance_conflict);
        const pid = data.managed_pid;
        const port = data.port || 8001;
        const canStart = Boolean(data.can_start);

        // Status text
        if (conflict) {
            _setText(_dom.status, 'Conflict');
        } else if (running) {
            _setText(_dom.status, 'Running');
        } else {
            _setText(_dom.status, 'Stopped');
        }

        // PID / Port
        _setText(_dom.pid, pid != null ? String(pid) : '--');
        _setText(_dom.port, String(port));

        // Uptime: compute from uptime_seconds if available, otherwise from started_at
        if (data.uptime_seconds != null && data.uptime_seconds > 0) {
            _setText(_dom.uptime, _formatUptime(data.uptime_seconds));
        } else if (running && data.started_at) {
            const started = new Date(data.started_at);
            const now = new Date();
            const diffSec = Math.max(0, Math.floor((now - started) / 1000));
            _setText(_dom.uptime, _formatUptime(diffSec));
        } else {
            _setText(_dom.uptime, '--');
        }

        // Badge
        if (_dom.statusBadge) {
            _dom.statusBadge.className = 'osrs-badge';
            if (conflict) {
                _dom.statusBadge.textContent = 'Conflict';
                _dom.statusBadge.classList.add('osrs-badge--warning');
            } else if (running) {
                _dom.statusBadge.textContent = 'Online';
                _dom.statusBadge.classList.add('osrs-badge--online');
            } else if (data._error) {
                _dom.statusBadge.textContent = 'Error';
                _dom.statusBadge.classList.add('osrs-badge--offline');
            } else {
                _dom.statusBadge.textContent = 'Offline';
                _dom.statusBadge.classList.add('osrs-badge--offline');
            }
        }

        // Button states
        if (_dom.btnStart) {
            _dom.btnStart.disabled = running || conflict || !canStart;
        }
        if (_dom.btnStop) {
            _dom.btnStop.disabled = !running;
        }
    }

    // =========================================================================
    // HEALTH
    // Calls through OsrsCommon proxy (/api/osrs/health)
    // =========================================================================

    async function loadHealth() {
        try {
            const data = await OsrsCommon.fetchJson('/health');
            _renderHealth(data);
            OsrsCommon.hideOfflineBanner(_dom.offlineBanner);
        } catch (err) {
            if (err.status === 503 || err.status === 502) {
                OsrsCommon.showOfflineBanner(_dom.offlineBanner);
            }
            _renderHealth(null);
        }
    }

    function _renderHealth(data) {
        if (!data) {
            _setText(_dom.kpiAccounts, '--');
            _setText(_dom.kpiSnapshots, '--');
            _setText(_dom.kpiSchema, '--');
            _setText(_dom.kpiLastCheck, '--');
            _setBadge(_dom.healthBadge, 'Offline', 'osrs-badge--offline');
            return;
        }

        const stats = data.stats || {};
        _setText(_dom.kpiAccounts, _formatNum(stats.accounts));
        _setText(_dom.kpiSnapshots, _formatNum(stats.snapshots));
        _setText(_dom.kpiSchema, stats.schema_version != null ? String(stats.schema_version) : '--');
        _setText(_dom.kpiLastCheck, _now());

        if (data.status === 'healthy') {
            _setBadge(_dom.healthBadge, 'Healthy', 'osrs-badge--online');
        } else {
            _setBadge(_dom.healthBadge, data.status || 'Unknown', 'osrs-badge--warning');
        }
    }

    // =========================================================================
    // RECENT SNAPSHOTS
    // Calls through OsrsCommon proxy (/api/osrs/snapshots/latest)
    // =========================================================================

    async function loadRecentSnapshots() {
        _showEl(_dom.snapshotsLoading);
        _hideEl(_dom.snapshotsEmpty);
        _hideEl(_dom.snapshotsTable);

        try {
            const data = await OsrsCommon.fetchJson('/snapshots/latest?limit=' + RECENT_LIMIT);
            const snapshots = Array.isArray(data) ? data : (data && Array.isArray(data.snapshots) ? data.snapshots : []);

            _hideEl(_dom.snapshotsLoading);

            if (snapshots.length === 0) {
                _showEl(_dom.snapshotsEmpty);
                _hideEl(_dom.snapshotsTable);
                return;
            }

            _hideEl(_dom.snapshotsEmpty);
            _showEl(_dom.snapshotsTable);
            _renderSnapshotsTable(snapshots);
        } catch (err) {
            _hideEl(_dom.snapshotsLoading);
            // If backend is offline, show empty state rather than error
            if (err.status === 503 || err.status === 502) {
                _showEl(_dom.snapshotsEmpty);
                if (_dom.snapshotsEmpty) {
                    const msg = _dom.snapshotsEmpty.querySelector('.osrs-empty__message');
                    if (msg) msg.textContent = 'Backend offline';
                    const sub = _dom.snapshotsEmpty.querySelector('.osrs-empty__submessage');
                    if (sub) sub.textContent = 'Start the backend to view snapshots';
                }
            } else {
                _showEl(_dom.snapshotsEmpty);
                if (_dom.snapshotsEmpty) {
                    const msg = _dom.snapshotsEmpty.querySelector('.osrs-empty__message');
                    if (msg) msg.textContent = 'Failed to load snapshots';
                    const sub = _dom.snapshotsEmpty.querySelector('.osrs-empty__submessage');
                    if (sub) sub.textContent = err.message || String(err);
                }
            }
        }
    }

    function _renderSnapshotsTable(snapshots) {
        if (!_dom.snapshotsBody) return;

        _dom.snapshotsBody.innerHTML = snapshots.map(row => {
            const player = OsrsCommon.escapeHtml(row.account_name || row.player || '--');
            const mode = OsrsCommon.escapeHtml(row.resolved_mode || row.mode || '--');
            const totalLevel = row.total_level != null ? OsrsCommon.formatLevel(row.total_level) : '--';
            const totalXp = row.total_xp != null ? OsrsCommon.formatXp(row.total_xp) : '--';
            const fetched = row.fetched_at ? OsrsCommon.formatTimeAgo(row.fetched_at) : '--';

            return '<tr>' +
                '<td>' + player + '</td>' +
                '<td><span class="osrs-badge osrs-badge--mode">' + mode + '</span></td>' +
                '<td class="osrs-mono">' + totalLevel + '</td>' +
                '<td class="osrs-mono">' + totalXp + '</td>' +
                '<td>' + fetched + '</td>' +
                '</tr>';
        }).join('');
    }

    // =========================================================================
    // START / STOP BACKEND
    // Calls osrs_runtime.py directly (Council route, NOT proxy)
    // =========================================================================

    async function startBackend() {
        if (_dom.btnStart) _dom.btnStart.disabled = true;
        _showToast('Starting backend...', 'info');

        try {
            const headers = {
                'Content-Type': 'application/json',
                ..._getAuthHeaders()
            };
            const resp = await fetch('/api/osrs/runtime/start', {
                method: 'POST',
                headers,
                body: JSON.stringify({ port: 8001, wait_seconds: 25 })
            });

            const data = await resp.json().catch(() => ({}));

            if (!resp.ok) {
                throw { status: resp.status, message: data.detail || `HTTP ${resp.status}` };
            }

            if (data.already_running) {
                _showToast('Backend is already running', 'info');
            } else if (data.started) {
                _showToast('Backend started successfully', 'success');
            } else {
                _showToast(data.message || 'Start request accepted', 'info');
            }

            // Refresh all status
            await loadRuntimeStatus();
            await loadHealth();
            await loadRecentSnapshots();
        } catch (err) {
            _showToast('Start failed: ' + (err.message || String(err)), 'error');
            if (_dom.btnStart) _dom.btnStart.disabled = false;
            await loadRuntimeStatus();
        }
    }

    async function stopBackend() {
        if (_dom.btnStop) _dom.btnStop.disabled = true;
        _showToast('Stopping backend...', 'info');

        try {
            const headers = {
                'Content-Type': 'application/json',
                ..._getAuthHeaders()
            };
            const resp = await fetch('/api/osrs/runtime/stop', {
                method: 'POST',
                headers,
                body: JSON.stringify({ confirm: true, grace_seconds: 4.0, force_kill: true })
            });

            const data = await resp.json().catch(() => ({}));

            if (!resp.ok) {
                throw { status: resp.status, message: data.detail || `HTTP ${resp.status}` };
            }

            if (data.stopped) {
                _showToast('Backend stopped', 'success');
            } else {
                _showToast(data.message || 'Stop request completed', 'info');
            }

            await loadRuntimeStatus();
            await loadHealth();
        } catch (err) {
            _showToast('Stop failed: ' + (err.message || String(err)), 'error');
            if (_dom.btnStop) _dom.btnStop.disabled = false;
            await loadRuntimeStatus();
        }
    }

    // =========================================================================
    // RUN SNAPSHOT
    // Calls through OsrsCommon proxy (/api/osrs/snapshots/run)
    // =========================================================================

    async function runSnapshot(event) {
        event.preventDefault();

        const player = (_dom.snapshotPlayer ? _dom.snapshotPlayer.value : '').trim();
        const mode = _dom.snapshotMode ? _dom.snapshotMode.value : 'auto';

        if (!player) {
            _setText(_dom.snapshotStatus, 'Player name is required.');
            return;
        }

        _setText(_dom.snapshotStatus, 'Running snapshot for ' + OsrsCommon.escapeHtml(player) + '...');
        if (_dom.snapshotResults) _dom.snapshotResults.innerHTML = '';

        try {
            const data = await OsrsCommon.postJson('/snapshots/run', { player, mode });
            _setText(_dom.snapshotStatus, 'Snapshot completed for ' + OsrsCommon.escapeHtml(player));
            _renderSnapshotResults(data);
            _showToast('Snapshot completed for ' + player, 'success');
            await loadRecentSnapshots();
            await loadHealth();
        } catch (err) {
            const msg = err.message || String(err);
            _setText(_dom.snapshotStatus, 'Snapshot failed: ' + OsrsCommon.escapeHtml(msg));
            _showToast('Snapshot failed: ' + msg, 'error');
        }
    }

    function _renderSnapshotResults(data) {
        if (!_dom.snapshotResults) return;

        const results = data && Array.isArray(data.results) ? data.results : (Array.isArray(data) ? data : []);

        if (results.length === 0) {
            _dom.snapshotResults.innerHTML = '';
            return;
        }

        _dom.snapshotResults.innerHTML = results.map(r => {
            const ok = Boolean(r.success);
            const badgeClass = ok ? 'osrs-badge--online' : 'osrs-badge--offline';
            const label = ok ? 'Success' : 'Failed';
            const playerName = OsrsCommon.escapeHtml(r.player || '--');
            const resolvedMode = OsrsCommon.escapeHtml(r.resolved_mode || '--');
            const message = OsrsCommon.escapeHtml(r.message || '');
            const delta = r.delta_summary ? OsrsCommon.escapeHtml(r.delta_summary) : '';

            return '<div style="margin-top: var(--space-2); padding: var(--space-2); background: var(--bg-surface); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">' +
                '<div style="display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap;">' +
                    '<span class="osrs-badge ' + badgeClass + '">' + label + '</span>' +
                    '<strong>' + playerName + '</strong>' +
                    '<span class="osrs-badge osrs-badge--mode">' + resolvedMode + '</span>' +
                '</div>' +
                (message ? '<div class="osrs-text-muted" style="font-size: var(--text-sm); margin-top: var(--space-1);">' + message + '</div>' : '') +
                (delta ? '<div style="font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1);">' + delta + '</div>' : '') +
            '</div>';
        }).join('');
    }

    // =========================================================================
    // TOAST NOTIFICATIONS
    // =========================================================================

    let _toastTimer = null;

    function _showToast(message, type) {
        if (!_dom.toast) return;

        if (_toastTimer) {
            clearTimeout(_toastTimer);
            _toastTimer = null;
        }

        // Style based on type
        let bg, color, border;
        switch (type) {
            case 'success':
                bg = 'var(--success-glow)';
                color = 'var(--success)';
                border = 'var(--success)';
                break;
            case 'error':
                bg = 'var(--error-glow)';
                color = 'var(--error)';
                border = 'var(--error)';
                break;
            default: // info
                bg = 'var(--cyan-glow)';
                color = 'var(--cyan-400)';
                border = 'var(--cyan-500)';
                break;
        }

        _dom.toast.style.background = bg;
        _dom.toast.style.color = color;
        _dom.toast.style.border = '1px solid ' + border;
        _dom.toast.textContent = message;
        _dom.toast.classList.remove('osrs-hidden');

        _toastTimer = setTimeout(() => {
            _dom.toast.classList.add('osrs-hidden');
            _toastTimer = null;
        }, 4000);
    }

    // =========================================================================
    // UTILITY HELPERS
    // =========================================================================

    function _getAuthHeaders() {
        if (typeof API !== 'undefined' && typeof API.getAuthHeaders === 'function') {
            return API.getAuthHeaders();
        }
        return {};
    }

    function _setText(el, value) {
        if (el) el.textContent = value != null ? String(value) : '';
    }

    function _showEl(el) {
        if (el) el.classList.remove('osrs-hidden');
    }

    function _hideEl(el) {
        if (el) el.classList.add('osrs-hidden');
    }

    function _setBadge(el, text, className) {
        if (!el) return;
        el.className = 'osrs-badge';
        el.textContent = text;
        if (className) el.classList.add(className);
    }

    function _formatUptime(totalSeconds) {
        if (totalSeconds == null || totalSeconds <= 0) return '--';
        const days = Math.floor(totalSeconds / 86400);
        const hours = Math.floor((totalSeconds % 86400) / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const secs = Math.floor(totalSeconds % 60);

        if (days > 0) return days + 'd ' + hours + 'h ' + minutes + 'm';
        if (hours > 0) return hours + 'h ' + minutes + 'm';
        if (minutes > 0) return minutes + 'm ' + secs + 's';
        return secs + 's';
    }

    function _formatNum(val) {
        if (val == null) return '--';
        const num = Number(val);
        if (Number.isNaN(num)) return String(val);
        return num.toLocaleString();
    }

    function _now() {
        return new Date().toLocaleTimeString();
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    return {
        init,
        destroy,
        refresh,
        startBackend,
        stopBackend,
        runSnapshot
    };
})();

window.OsrsControl = OsrsControl;
