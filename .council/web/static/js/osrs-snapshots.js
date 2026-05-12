/**
 * OSRS Snapshots -- Snapshot Explorer Module
 * =============================================
 * Browsing, filtering, inline detail expansion with delta chips.
 * Pattern: Named IIFE exported as window.OsrsSnapshots
 *
 * Dependencies:
 *   - window.OsrsCommon (osrs-common.js)
 *   - window.API (Council app.js) for auth headers
 */

const OsrsSnapshots = (() => {
    'use strict';

    // =========================================================================
    // STATE
    // =========================================================================

    const _dom = {};
    let _expandedRow = null;
    let _expandedId = null;
    let _currentFilters = { limit: 25 };
    let _snapshotsData = [];

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    function init() {
        _cacheDom();
        if (!_dom.root) return;
        _populateModeSelects();
        _bindEvents();
        loadSnapshots();
        OsrsCommon.listenCouncilSwitch(() => { destroy(); init(); });
    }

    function destroy() {
        _expandedRow = null;
        _expandedId = null;
        _snapshotsData = [];
    }

    function refresh() {
        loadSnapshots();
    }

    // =========================================================================
    // DOM CACHE
    // =========================================================================

    function _cacheDom() {
        _dom.root = document.getElementById('osrs-snapshots-root');
        if (!_dom.root) return;

        _dom.offlineBanner = document.getElementById('snapshots-offline-banner');
        _dom.refreshBtn = document.getElementById('snapshots-refresh-btn');
        _dom.loading = document.getElementById('snapshots-loading');
        _dom.empty = document.getElementById('snapshots-empty');
        _dom.tableWrap = document.getElementById('snapshots-table-wrap');
        _dom.tableBody = document.getElementById('snapshots-table-body');

        // Filter elements
        _dom.filterAccount = document.getElementById('filter-account');
        _dom.filterMode = document.getElementById('filter-mode');
        _dom.filterLimit = document.getElementById('filter-limit');
        _dom.filterApplyBtn = document.getElementById('filter-apply-btn');

        // Run snapshot elements
        _dom.runForm = document.getElementById('run-snapshot-form');
        _dom.runPlayer = document.getElementById('run-player');
        _dom.runMode = document.getElementById('run-mode');
        _dom.runStatus = document.getElementById('run-snapshot-status');
    }

    // =========================================================================
    // EVENT BINDING
    // =========================================================================

    function _bindEvents() {
        if (_dom.refreshBtn) {
            _dom.refreshBtn.addEventListener('click', refresh);
        }
        if (_dom.filterApplyBtn) {
            _dom.filterApplyBtn.addEventListener('click', applyFilters);
        }
        if (_dom.filterAccount) {
            _dom.filterAccount.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); applyFilters(); }
            });
        }
        if (_dom.runForm) {
            _dom.runForm.addEventListener('submit', runSnapshot);
        }

        // Delegated handlers for raw JSON toggle/copy inside detail rows
        if (_dom.tableBody) {
            _dom.tableBody.addEventListener('click', _handleRawActions);
        }
    }

    /**
     * Delegated click handler for Report/Raw toggle, mode switch, and Copy.
     * Data flow:
     *   1. "Show Report" fetches the markdown report (falls back to raw JSON)
     *   2. "Show Raw JSON" / "Show Report" switches between cached content
     *   3. "Copy" copies whichever content is currently displayed
     */
    async function _handleRawActions(evt) {
        const section = evt.target.closest('.osrs-raw-section');
        if (!section) return;

        const toggleBtn = evt.target.closest('.osrs-raw-toggle');
        const modeBtn = evt.target.closest('.osrs-raw-mode-toggle');
        const copyBtn = evt.target.closest('.osrs-raw-copy');
        const codebox = section.querySelector('.osrs-raw-codebox');
        const copyAction = section.querySelector('.osrs-raw-copy');
        const modeSwitchBtn = section.querySelector('.osrs-raw-mode-toggle');

        // ---- Show / Hide toggle ----
        if (toggleBtn) {
            evt.stopPropagation();

            if (codebox.classList.contains('osrs-hidden')) {
                // Show — fetch report first time
                if (!codebox.dataset.reportLoaded && !codebox.dataset.rawLoaded) {
                    toggleBtn.textContent = 'Loading...';
                    toggleBtn.disabled = true;
                    const reportPath = toggleBtn.dataset.reportPath;
                    const rawPath = toggleBtn.dataset.rawPath;
                    try {
                        const text = await OsrsCommon.fetchText(reportPath);
                        codebox.textContent = text;
                        codebox.dataset.reportLoaded = '1';
                        codebox.dataset.reportContent = text;
                        codebox.dataset.activeMode = 'report';
                        if (modeSwitchBtn) modeSwitchBtn.textContent = 'Show Raw JSON';
                    } catch {
                        // Report not found — fall back to raw JSON
                        try {
                            const text = await OsrsCommon.fetchText(rawPath);
                            codebox.textContent = text;
                            codebox.dataset.rawLoaded = '1';
                            codebox.dataset.rawContent = text;
                            codebox.dataset.activeMode = 'raw';
                            if (modeSwitchBtn) modeSwitchBtn.textContent = 'Show Report';
                        } catch (err2) {
                            codebox.textContent = 'Failed to load: ' + (err2.detail || err2.message || 'unknown error');
                        }
                    }
                    toggleBtn.disabled = false;
                }
                codebox.classList.remove('osrs-hidden');
                toggleBtn.textContent = 'Hide';
                if (copyAction) copyAction.classList.remove('osrs-hidden');
                if (modeSwitchBtn) modeSwitchBtn.classList.remove('osrs-hidden');
            } else {
                // Hide
                codebox.classList.add('osrs-hidden');
                toggleBtn.textContent = codebox.dataset.activeMode === 'report' ? 'Show Report' : 'Show Raw JSON';
                if (copyAction) copyAction.classList.add('osrs-hidden');
                if (modeSwitchBtn) modeSwitchBtn.classList.add('osrs-hidden');
            }
            return;
        }

        // ---- Report / Raw mode switch ----
        if (modeBtn) {
            evt.stopPropagation();
            const mainToggle = section.querySelector('.osrs-raw-toggle');
            const activeMode = codebox.dataset.activeMode || 'report';

            if (activeMode === 'report') {
                // Switch to raw JSON
                if (!codebox.dataset.rawLoaded) {
                    modeBtn.textContent = 'Loading...';
                    modeBtn.disabled = true;
                    const rawPath = mainToggle ? mainToggle.dataset.rawPath : '';
                    try {
                        const text = await OsrsCommon.fetchText(rawPath);
                        codebox.dataset.rawLoaded = '1';
                        codebox.dataset.rawContent = text;
                    } catch (err) {
                        codebox.dataset.rawContent = 'Failed to load raw JSON: ' + (err.detail || err.message || 'unknown error');
                    }
                    modeBtn.disabled = false;
                }
                codebox.textContent = codebox.dataset.rawContent || '';
                codebox.dataset.activeMode = 'raw';
                modeBtn.textContent = 'Show Report';
            } else {
                // Switch to report
                if (!codebox.dataset.reportLoaded) {
                    modeBtn.textContent = 'Loading...';
                    modeBtn.disabled = true;
                    const reportPath = mainToggle ? mainToggle.dataset.reportPath : '';
                    try {
                        const text = await OsrsCommon.fetchText(reportPath);
                        codebox.dataset.reportLoaded = '1';
                        codebox.dataset.reportContent = text;
                    } catch (err) {
                        codebox.dataset.reportContent = 'No report available for this snapshot.';
                    }
                    modeBtn.disabled = false;
                }
                codebox.textContent = codebox.dataset.reportContent || '';
                codebox.dataset.activeMode = 'report';
                modeBtn.textContent = 'Show Raw JSON';
            }
            return;
        }

        // ---- Copy ----
        if (copyBtn) {
            evt.stopPropagation();
            const text = codebox.textContent || '';
            try {
                await OsrsCommon.copyToClipboard(text);
                const original = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('osrs-btn--success');
                setTimeout(() => {
                    copyBtn.textContent = original;
                    copyBtn.classList.remove('osrs-btn--success');
                }, 2000);
            } catch {
                copyBtn.textContent = 'Failed';
                setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
            }
            return;
        }
    }

    // =========================================================================
    // MODE SELECTS
    // =========================================================================

    function _populateModeSelects() {
        const modes = OsrsCommon.SNAPSHOT_MODES;

        // Filter mode -- includes "All Modes" option
        if (_dom.filterMode) {
            _dom.filterMode.innerHTML = '<option value="">All Modes</option>';
            for (const mode of modes) {
                const opt = document.createElement('option');
                opt.value = mode;
                opt.textContent = _formatModeName(mode);
                _dom.filterMode.appendChild(opt);
            }
        }

        // Run mode
        if (_dom.runMode) {
            _dom.runMode.innerHTML = '';
            for (const mode of modes) {
                const opt = document.createElement('option');
                opt.value = mode;
                opt.textContent = _formatModeName(mode);
                _dom.runMode.appendChild(opt);
            }
        }
    }

    /**
     * Format a mode slug to display name.
     * e.g. "hardcore_ironman" -> "Hardcore Ironman"
     */
    function _formatModeName(mode) {
        return mode
            .split('_')
            .map(w => w.charAt(0).toUpperCase() + w.slice(1))
            .join(' ');
    }

    // =========================================================================
    // LOAD SNAPSHOTS
    // =========================================================================

    async function loadSnapshots() {
        _showLoading();
        OsrsCommon.hideOfflineBanner(_dom.offlineBanner);

        try {
            const params = new URLSearchParams();
            if (_currentFilters.limit) params.set('limit', String(_currentFilters.limit));
            if (_currentFilters.account_name) params.set('account_name', _currentFilters.account_name);
            if (_currentFilters.mode) params.set('mode', _currentFilters.mode);

            const queryStr = params.toString();
            const path = '/snapshots/latest' + (queryStr ? '?' + queryStr : '');
            const data = await OsrsCommon.fetchJson(path);

            _snapshotsData = Array.isArray(data) ? data : [];
            _renderTable(_snapshotsData);

        } catch (err) {
            if (err && err.status === 503) {
                OsrsCommon.showOfflineBanner(_dom.offlineBanner);
                _showEmpty();
            } else {
                console.error('[OsrsSnapshots] Failed to load snapshots:', err);
                _showEmpty();
            }
        }
    }

    // =========================================================================
    // FILTERS
    // =========================================================================

    function applyFilters() {
        _currentFilters = {
            limit: _dom.filterLimit ? parseInt(_dom.filterLimit.value, 10) || 25 : 25,
            account_name: _dom.filterAccount ? _dom.filterAccount.value.trim() || undefined : undefined,
            mode: _dom.filterMode ? _dom.filterMode.value || undefined : undefined
        };

        // Collapse any expanded row
        _collapseExpanded();

        loadSnapshots();
    }

    // =========================================================================
    // TABLE RENDERING
    // =========================================================================

    function _renderTable(snapshots) {
        if (!snapshots || snapshots.length === 0) {
            _showEmpty();
            return;
        }

        _showTable();

        let html = '';
        for (const snap of snapshots) {
            const sid = OsrsCommon.escapeHtml(snap.snapshot_id || '');
            const sidShort = sid.length > 8 ? sid.substring(0, 8) : sid;
            const account = _resolveAccountName(snap);
            const mode = OsrsCommon.escapeHtml(snap.resolved_mode || snap.requested_mode || '--');
            const totalLevel = OsrsCommon.formatLevel(snap.total_level);
            const totalXp = OsrsCommon.formatXp(snap.total_xp);
            const fetchedAt = OsrsCommon.formatTimeAgo(snap.fetched_at);
            const fullTimestamp = OsrsCommon.formatTimestamp(snap.fetched_at);
            const isExpanded = _expandedId === sid;

            html += `<tr class="osrs-snapshot-row${isExpanded ? ' osrs-snapshot-row--expanded' : ''}"
                         data-snapshot-id="${sid}"
                         onclick="OsrsSnapshots.expandSnapshot('${sid}', this)"
                         title="Click to expand details">
                <td><code class="osrs-mono">${sidShort}</code></td>
                <td>${OsrsCommon.escapeHtml(account)}</td>
                <td><span class="osrs-badge osrs-badge--mode">${mode}</span></td>
                <td class="osrs-mono">${totalLevel}</td>
                <td class="osrs-mono">${totalXp}</td>
                <td title="${OsrsCommon.escapeHtml(fullTimestamp)}">${fetchedAt}</td>
            </tr>`;

            // If this row is expanded, add the detail row
            if (isExpanded && _expandedRow) {
                html += _expandedRow;
            }
        }

        _dom.tableBody.innerHTML = html;
    }

    /**
     * Resolve account name from snapshot data.
     * Priority: account_name field > metadata.player > account_id fallback
     */
    function _resolveAccountName(snap) {
        if (snap.account_name) return snap.account_name;
        if (snap.metadata && snap.metadata.player) return snap.metadata.player;
        if (snap.account_id) return 'Account #' + snap.account_id;
        return '--';
    }

    // =========================================================================
    // EXPAND / COLLAPSE SNAPSHOT DETAIL
    // =========================================================================

    async function expandSnapshot(snapshotId, rowElement) {
        // If clicking the same row, collapse it
        if (_expandedId === snapshotId) {
            _collapseExpanded();
            _renderTable(_snapshotsData);
            return;
        }

        // Collapse any existing expansion
        _collapseExpanded();

        _expandedId = snapshotId;

        // Mark the row as expanded visually
        if (rowElement) {
            rowElement.classList.add('osrs-snapshot-row--expanded');
        }

        // Show a loading detail row
        const loadingHtml = `<tr class="osrs-snapshot-detail-row" data-detail-for="${OsrsCommon.escapeHtml(snapshotId)}">
            <td colspan="6">
                <div class="osrs-snapshot-detail">
                    <div class="osrs-loading">
                        <div class="osrs-loading__spinner"></div>
                        <span class="osrs-loading__text">Loading snapshot details...</span>
                    </div>
                </div>
            </td>
        </tr>`;

        // Insert loading row after the clicked row
        if (rowElement && rowElement.parentNode) {
            rowElement.insertAdjacentHTML('afterend', loadingHtml);
        }

        try {
            const data = await OsrsCommon.fetchJson('/snapshots/' + encodeURIComponent(snapshotId) + '?include_deltas=true');
            _expandedRow = _buildDetailRow(snapshotId, data);

            // Re-render to update
            _renderTable(_snapshotsData);

        } catch (err) {
            console.error('[OsrsSnapshots] Failed to load snapshot detail:', err);

            const errorHtml = `<tr class="osrs-snapshot-detail-row" data-detail-for="${OsrsCommon.escapeHtml(snapshotId)}">
                <td colspan="6">
                    <div class="osrs-snapshot-detail">
                        <div class="osrs-error-box">Failed to load snapshot details. ${OsrsCommon.escapeHtml(err.detail || '')}</div>
                    </div>
                </td>
            </tr>`;

            _expandedRow = errorHtml;
            _renderTable(_snapshotsData);
        }
    }

    function _collapseExpanded() {
        _expandedId = null;
        _expandedRow = null;
    }

    // =========================================================================
    // DETAIL ROW BUILDER
    // =========================================================================

    function _buildDetailRow(snapshotId, data) {
        const snapshot = data.snapshot || data;
        const deltas = data.deltas || null;
        const account = data.account || null;
        const baseUrl = OsrsCommon.getBackendBaseUrl();

        let contentHtml = '';

        // Snapshot metadata section
        contentHtml += '<div class="osrs-profile__section-title">Snapshot Metadata</div>';
        contentHtml += '<div class="osrs-stat-row">';
        contentHtml += `<span class="osrs-stat-row__label">Snapshot ID</span>`;
        contentHtml += `<span class="osrs-stat-row__value">${OsrsCommon.escapeHtml(snapshot.snapshot_id || snapshotId)}</span>`;
        contentHtml += '</div>';
        if (account && account.account_name) {
            contentHtml += '<div class="osrs-stat-row">';
            contentHtml += `<span class="osrs-stat-row__label">Account</span>`;
            contentHtml += `<span class="osrs-stat-row__value">${OsrsCommon.escapeHtml(account.account_name)}</span>`;
            contentHtml += '</div>';
        }
        contentHtml += '<div class="osrs-stat-row">';
        contentHtml += `<span class="osrs-stat-row__label">Game Mode</span>`;
        contentHtml += `<span class="osrs-stat-row__value">${OsrsCommon.escapeHtml(snapshot.resolved_mode || snapshot.requested_mode || '--')}</span>`;
        contentHtml += '</div>';
        contentHtml += '<div class="osrs-stat-row">';
        contentHtml += `<span class="osrs-stat-row__label">Total Level</span>`;
        contentHtml += `<span class="osrs-stat-row__value">${OsrsCommon.formatLevel(snapshot.total_level)}</span>`;
        contentHtml += '</div>';
        contentHtml += '<div class="osrs-stat-row">';
        contentHtml += `<span class="osrs-stat-row__label">Total XP</span>`;
        contentHtml += `<span class="osrs-stat-row__value">${OsrsCommon.formatXp(snapshot.total_xp)}</span>`;
        contentHtml += '</div>';
        contentHtml += '<div class="osrs-stat-row">';
        contentHtml += `<span class="osrs-stat-row__label">Fetched At</span>`;
        contentHtml += `<span class="osrs-stat-row__value">${OsrsCommon.formatTimestamp(snapshot.fetched_at)}</span>`;
        contentHtml += '</div>';

        if (deltas && deltas.total_xp_delta != null) {
            const totalDelta = OsrsCommon.formatDelta(deltas.total_xp_delta);
            contentHtml += '<div class="osrs-stat-row">';
            contentHtml += `<span class="osrs-stat-row__label">Total XP Change</span>`;
            contentHtml += `<span class="osrs-stat-row__value"><span class="osrs-delta-chip ${totalDelta.className}">${totalDelta.text}</span></span>`;
            contentHtml += '</div>';
        }

        // Skills section with delta chips
        if (snapshot.skills && snapshot.skills.length > 0) {
            contentHtml += '<div class="osrs-profile__section-title">Skills</div>';
            contentHtml += _renderSkillGridWithDeltas(snapshot.skills, deltas, baseUrl);
        }

        // Activities section with delta chips
        if (snapshot.activities && snapshot.activities.length > 0) {
            contentHtml += '<div class="osrs-profile__section-title">Activities</div>';
            contentHtml += _renderActivityListWithDeltas(snapshot.activities, deltas, baseUrl);
        }

        // Report / Raw JSON codebox with tab toggle
        const eid = OsrsCommon.escapeHtml(snapshotId);
        const reportPath = '/snapshots/' + encodeURIComponent(snapshotId) + '/report';
        const rawPath = '/snapshots/' + encodeURIComponent(snapshotId) + '/raw';
        contentHtml += '<div class="osrs-raw-section">';
        contentHtml += '  <div class="osrs-raw-section__header">';
        contentHtml += '    <span class="osrs-profile__section-title" style="margin:0">Snapshot Output</span>';
        contentHtml += '    <div class="osrs-raw-section__actions">';
        contentHtml += `      <button class="osrs-btn osrs-btn--ghost osrs-btn--sm osrs-raw-toggle" data-report-path="${OsrsCommon.escapeHtml(reportPath)}" data-raw-path="${OsrsCommon.escapeHtml(rawPath)}" data-snapshot-id="${eid}" data-mode="report">Show Report</button>`;
        contentHtml += `      <button class="osrs-btn osrs-btn--ghost osrs-btn--sm osrs-raw-mode-toggle osrs-hidden" data-snapshot-id="${eid}">Show Raw JSON</button>`;
        contentHtml += `      <button class="osrs-btn osrs-btn--ghost osrs-btn--sm osrs-raw-copy osrs-hidden">Copy</button>`;
        contentHtml += '    </div>';
        contentHtml += '  </div>';
        contentHtml += `  <pre class="osrs-raw-codebox osrs-hidden" data-snapshot-id="${eid}"></pre>`;
        contentHtml += '</div>';

        return `<tr class="osrs-snapshot-detail-row" data-detail-for="${OsrsCommon.escapeHtml(snapshotId)}">
            <td colspan="6">
                <div class="osrs-snapshot-detail osrs-fade-in">
                    ${contentHtml}
                </div>
            </td>
        </tr>`;
    }

    // =========================================================================
    // SKILL GRID WITH DELTAS
    // =========================================================================

    /**
     * Render skill grid with delta chips overlaid on each skill card.
     * Uses OsrsCommon.SKILL_ORDER for consistent ordering.
     * Delta chips show XP change for each skill (green/red/neutral).
     */
    function _renderSkillGridWithDeltas(skills, deltas, baseUrl) {
        if (!skills || !skills.length) {
            return '<div class="osrs-empty"><p class="osrs-empty__message">No skill data</p></div>';
        }

        // Build lookup by normalized name for skills
        const skillLookup = {};
        for (const skill of skills) {
            if (skill && skill.name) {
                skillLookup[_normalizeName(skill.name)] = skill;
            }
        }

        // Build delta lookup by normalized name
        const deltaLookup = {};
        if (deltas && deltas.skill_deltas) {
            for (const d of deltas.skill_deltas) {
                if (d && d.name) {
                    deltaLookup[_normalizeName(d.name)] = d;
                }
            }
        }

        let html = '<div class="osrs-skill-grid">';

        // Overall first
        const overall = skillLookup['overall'];
        if (overall) {
            html += _renderOneSkillWithDelta('overall', overall, deltaLookup['overall'], baseUrl);
        }

        // Then in canonical order
        for (const skillName of OsrsCommon.SKILL_ORDER) {
            const normalized = _normalizeName(skillName);
            const skill = skillLookup[normalized];
            if (skill) {
                html += _renderOneSkillWithDelta(skillName, skill, deltaLookup[normalized], baseUrl);
            }
        }

        html += '</div>';
        return html;
    }

    /**
     * Render a single skill card with optional delta chip.
     */
    function _renderOneSkillWithDelta(name, skill, delta, baseUrl) {
        const level = skill.level != null ? skill.level : -1;
        const is99 = level >= 99;
        const modifier = is99 ? ' osrs-skill-card--99' : '';

        let deltaHtml = '';
        if (delta) {
            // Show XP delta as the primary delta chip
            const xpDelta = OsrsCommon.formatDelta(delta.xp_delta);
            deltaHtml = `<span class="osrs-delta-chip ${xpDelta.className}">${xpDelta.text} xp</span>`;

            // If level changed, show that too
            if (delta.level_delta && delta.level_delta > 0) {
                const lvlDelta = OsrsCommon.formatDelta(delta.level_delta);
                deltaHtml += ` <span class="osrs-delta-chip ${lvlDelta.className}">${lvlDelta.text} lvl</span>`;
            }
        }

        return `<div class="osrs-skill-card${modifier}">
            ${OsrsCommon.renderSkillIcon(name, baseUrl)}
            <div class="osrs-skill-card__info">
                <span class="osrs-skill-card__name">${OsrsCommon.escapeHtml(name)}</span>
                <span class="osrs-skill-card__level">${OsrsCommon.formatLevel(level)}</span>
                <span class="osrs-skill-card__xp">${OsrsCommon.formatXp(skill.xp)}</span>
                ${deltaHtml ? '<span class="osrs-skill-card__rank">' + deltaHtml + '</span>' : ''}
            </div>
        </div>`;
    }

    // =========================================================================
    // ACTIVITY LIST WITH DELTAS
    // =========================================================================

    /**
     * Render activity list with delta chips for score changes.
     */
    function _renderActivityListWithDeltas(activities, deltas, baseUrl) {
        if (!activities || !activities.length) {
            return '<div class="osrs-empty"><p class="osrs-empty__message">No activity data</p></div>';
        }

        // Build delta lookup
        const deltaLookup = {};
        if (deltas && deltas.activity_deltas) {
            for (const d of deltas.activity_deltas) {
                if (d && d.name) {
                    deltaLookup[_normalizeName(d.name)] = d;
                }
            }
        }

        let html = '<div class="osrs-activity-list">';
        for (const activity of activities) {
            if (!activity || !activity.name) continue;

            const score = activity.score != null && activity.score >= 0
                ? Number(activity.score).toLocaleString('en-US')
                : '--';
            const rank = activity.rank != null && activity.rank >= 0
                ? '#' + Number(activity.rank).toLocaleString('en-US')
                : '--';

            // Check for delta
            const normalized = _normalizeName(activity.name);
            const delta = deltaLookup[normalized];
            let deltaHtml = '';
            if (delta && delta.score_delta) {
                const scoreDelta = OsrsCommon.formatDelta(delta.score_delta);
                deltaHtml = `<span class="osrs-delta-chip ${scoreDelta.className}">${scoreDelta.text}</span>`;
            }

            html += `<div class="osrs-activity-row">
                ${OsrsCommon.renderGameIcon(activity.name, baseUrl)}
                <span class="osrs-activity-row__name">${OsrsCommon.escapeHtml(activity.name)}</span>
                <span class="osrs-activity-row__score">${score}</span>
                ${deltaHtml}
                <span class="osrs-activity-row__rank">${rank}</span>
            </div>`;
        }
        html += '</div>';
        return html;
    }

    // =========================================================================
    // RUN SNAPSHOT
    // =========================================================================

    async function runSnapshot(event) {
        event.preventDefault();

        const player = _dom.runPlayer ? _dom.runPlayer.value.trim() : '';
        const mode = _dom.runMode ? _dom.runMode.value : 'auto';

        if (!player) {
            _showRunStatus('Please enter a player name.', 'warn');
            return;
        }

        _showRunStatus('Running snapshot for ' + OsrsCommon.escapeHtml(player) + '...', 'info');

        try {
            const result = await OsrsCommon.postJson('/snapshots/run', {
                player: player,
                mode: mode
            });

            const count = result && result.results ? result.results.length : 0;
            _showRunStatus('Snapshot complete! ' + count + ' result(s) returned.', 'success');

            // Clear the form
            if (_dom.runPlayer) _dom.runPlayer.value = '';

            // Reload the snapshot list
            loadSnapshots();

        } catch (err) {
            if (err && err.status === 503) {
                OsrsCommon.showOfflineBanner(_dom.offlineBanner);
                _showRunStatus('Backend is offline. Start it from the Control Center.', 'error');
            } else {
                _showRunStatus('Snapshot failed: ' + OsrsCommon.escapeHtml(err.detail || 'Unknown error'), 'error');
            }
        }
    }

    function _showRunStatus(message, type) {
        if (!_dom.runStatus) return;
        _dom.runStatus.classList.remove('osrs-hidden');

        let className = '';
        if (type === 'success') className = 'osrs-text-success';
        else if (type === 'error') className = 'osrs-text-error';
        else if (type === 'warn') className = 'osrs-text-warning';
        else className = '';

        _dom.runStatus.innerHTML = `<span class="${className}">${message}</span>`;
    }

    // =========================================================================
    // DISPLAY STATE MANAGEMENT
    // =========================================================================

    function _showLoading() {
        if (_dom.loading) _dom.loading.classList.remove('osrs-hidden');
        if (_dom.empty) _dom.empty.classList.add('osrs-hidden');
        if (_dom.tableWrap) _dom.tableWrap.classList.add('osrs-hidden');
    }

    function _showEmpty() {
        if (_dom.loading) _dom.loading.classList.add('osrs-hidden');
        if (_dom.empty) _dom.empty.classList.remove('osrs-hidden');
        if (_dom.tableWrap) _dom.tableWrap.classList.add('osrs-hidden');
    }

    function _showTable() {
        if (_dom.loading) _dom.loading.classList.add('osrs-hidden');
        if (_dom.empty) _dom.empty.classList.add('osrs-hidden');
        if (_dom.tableWrap) _dom.tableWrap.classList.remove('osrs-hidden');
    }

    // =========================================================================
    // UTILITIES
    // =========================================================================

    /**
     * Normalize a name for lookup matching.
     * Same pattern as OsrsCommon's internal _normalizeName.
     */
    function _normalizeName(name) {
        return String(name || '').toLowerCase().replace(/[ _\-]/g, '');
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    return {
        init,
        destroy,
        refresh,
        applyFilters,
        expandSnapshot,
        runSnapshot
    };
})();

window.OsrsSnapshots = OsrsSnapshots;
