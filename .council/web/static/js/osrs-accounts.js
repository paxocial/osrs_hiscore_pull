/**
 * OSRS Accounts -- Page Controller
 * ==================================
 * Named IIFE module for the Accounts page.
 * Provides: CRUD for accounts, inline profile expansion, snapshot trigger.
 *
 * Dependencies: OsrsCommon (osrs-common.js), API (app.js)
 */

const OsrsAccounts = (() => {
    'use strict';

    // =========================================================================
    // STATE
    // =========================================================================

    const _dom = {};
    let _expandedRow = null;
    let _expandedName = null;
    let _pendingDeleteName = null;
    let _accounts = [];

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    function init() {
        _cacheDom();
        if (!_dom.root) return;
        _bindEvents();
        loadAccounts();
        OsrsCommon.listenCouncilSwitch(() => { destroy(); init(); });
    }

    function destroy() {
        _expandedRow = null;
        _expandedName = null;
        _pendingDeleteName = null;
        _accounts = [];
    }

    function refresh() {
        loadAccounts();
    }

    // =========================================================================
    // DOM CACHE
    // =========================================================================

    function _cacheDom() {
        _dom.root = document.getElementById('osrs-accounts-root');
        _dom.loading = document.getElementById('accountsLoading');
        _dom.error = document.getElementById('accountsError');
        _dom.empty = document.getElementById('accountsEmpty');
        _dom.tableWrap = document.getElementById('accountsTableWrap');
        _dom.tableBody = document.getElementById('accountsTableBody');
        _dom.toast = document.getElementById('accountsToast');

        // Create modal
        _dom.createModal = document.getElementById('createAccountModal');
        _dom.createBackdrop = document.getElementById('createModalBackdrop');
        _dom.createNameInput = document.getElementById('createAccountName');
        _dom.createModeSelect = document.getElementById('createAccountMode');
        _dom.createError = document.getElementById('createAccountError');
        _dom.openCreateBtn = document.getElementById('openCreateModalBtn');
        _dom.closeCreateBtn = document.getElementById('closeCreateModalBtn');
        _dom.cancelCreateBtn = document.getElementById('cancelCreateBtn');
        _dom.submitCreateBtn = document.getElementById('submitCreateBtn');

        // Delete modal
        _dom.deleteModal = document.getElementById('deleteAccountModal');
        _dom.deleteBackdrop = document.getElementById('deleteModalBackdrop');
        _dom.deleteNameEl = document.getElementById('deleteAccountName');
        _dom.cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
        _dom.confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    }

    // =========================================================================
    // EVENT BINDING
    // =========================================================================

    function _bindEvents() {
        // Create modal
        if (_dom.openCreateBtn) {
            _dom.openCreateBtn.addEventListener('click', _openCreateModal);
        }
        if (_dom.closeCreateBtn) {
            _dom.closeCreateBtn.addEventListener('click', _closeCreateModal);
        }
        if (_dom.cancelCreateBtn) {
            _dom.cancelCreateBtn.addEventListener('click', _closeCreateModal);
        }
        if (_dom.createBackdrop) {
            _dom.createBackdrop.addEventListener('click', _closeCreateModal);
        }
        if (_dom.submitCreateBtn) {
            _dom.submitCreateBtn.addEventListener('click', createAccount);
        }
        if (_dom.createNameInput) {
            _dom.createNameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') createAccount();
            });
        }

        // Delete modal
        if (_dom.cancelDeleteBtn) {
            _dom.cancelDeleteBtn.addEventListener('click', _closeDeleteModal);
        }
        if (_dom.deleteBackdrop) {
            _dom.deleteBackdrop.addEventListener('click', _closeDeleteModal);
        }
        if (_dom.confirmDeleteBtn) {
            _dom.confirmDeleteBtn.addEventListener('click', _confirmDelete);
        }

        // Table row clicks (delegated)
        if (_dom.tableBody) {
            _dom.tableBody.addEventListener('click', _handleTableClick);
        }
    }

    // =========================================================================
    // LOAD ACCOUNTS
    // =========================================================================

    async function loadAccounts() {
        _showState('loading');
        OsrsCommon.hideOfflineBanner(_dom.root);

        try {
            const data = await OsrsCommon.fetchJson(
                '/accounts?page=1&page_size=50&active_only=false'
            );

            _accounts = data.accounts || [];

            if (_accounts.length === 0) {
                _showState('empty');
                return;
            }

            _renderTable(_accounts);
            _showState('table');
        } catch (err) {
            if (err.status === 503) {
                OsrsCommon.showOfflineBanner(_dom.root);
                _showState('empty');
            } else {
                _showError(err.detail || 'Failed to load accounts');
                _showState('error');
            }
        }
    }

    // =========================================================================
    // RENDER TABLE
    // =========================================================================

    function _renderTable(accounts) {
        if (!_dom.tableBody) return;

        const esc = OsrsCommon.escapeHtml;
        let html = '';

        for (const acct of accounts) {
            const name = esc(acct.name || '');
            const mode = esc(acct.default_mode || 'main');
            const modeLabel = _formatModeLabel(acct.default_mode || 'main');
            const isActive = acct.active !== false;
            const statusClass = isActive ? 'osrs-badge--online' : 'osrs-badge--offline';
            const statusLabel = isActive ? 'Active' : 'Inactive';
            const snapCount = acct.total_snapshots != null ? acct.total_snapshots : '--';
            const lastFetch = acct.latest_snapshot
                ? OsrsCommon.formatTimeAgo(acct.latest_snapshot)
                : '--';
            const isExpanded = _expandedName === acct.name;
            const expandedClass = isExpanded ? ' osrs-account-row--expanded' : '';

            html += `<tr class="osrs-account-row${expandedClass}"
                         data-account-name="${name}"
                         data-action="expand">
                <td class="osrs-account-row__name">${name}</td>
                <td><span class="osrs-badge osrs-badge--mode">${esc(modeLabel)}</span></td>
                <td><span class="osrs-badge ${statusClass}">${statusLabel}</span></td>
                <td class="osrs-account-row__meta">${snapCount}</td>
                <td class="osrs-account-row__meta">${esc(lastFetch)}</td>
                <td>
                    <button class="btn btn-danger btn-sm"
                            data-action="delete"
                            data-account-name="${name}"
                            title="Delete ${name}"
                            style="padding:var(--space-1) var(--space-2);">
                        <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
                            <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </button>
                </td>
            </tr>`;

            // If this row is expanded, include the expansion row
            if (isExpanded && _expandedRow) {
                html += _expandedRow;
            }
        }

        _dom.tableBody.innerHTML = html;
    }

    // =========================================================================
    // TABLE CLICK HANDLER (DELEGATION)
    // =========================================================================

    function _handleTableClick(e) {
        // Check for delete button first
        const deleteBtn = e.target.closest('[data-action="delete"]');
        if (deleteBtn) {
            e.stopPropagation();
            const name = deleteBtn.getAttribute('data-account-name');
            if (name) _openDeleteModal(name);
            return;
        }

        // Check for row expand
        const row = e.target.closest('[data-action="expand"]');
        if (row) {
            const name = row.getAttribute('data-account-name');
            if (name) expandProfile(name, row);
        }
    }

    // =========================================================================
    // EXPAND PROFILE
    // =========================================================================

    async function expandProfile(name, rowElement) {
        // If already expanded, collapse
        if (_expandedName === name) {
            _collapseExpanded();
            return;
        }

        // Collapse any previous expansion
        _collapseExpanded();

        _expandedName = name;

        // Mark the row as expanded
        if (rowElement) {
            rowElement.classList.add('osrs-account-row--expanded');
        }

        // Create a temporary loading row
        const loadingRow = document.createElement('tr');
        loadingRow.setAttribute('data-expansion-row', 'true');
        loadingRow.innerHTML = `<td colspan="6">
            <div class="osrs-loading" style="padding:var(--space-6);">
                <div class="osrs-loading__spinner"></div>
                <span class="osrs-loading__text">Loading profile...</span>
            </div>
        </td>`;

        // Insert after the clicked row
        if (rowElement && rowElement.parentNode) {
            rowElement.parentNode.insertBefore(loadingRow, rowElement.nextSibling);
        }

        try {
            const data = await OsrsCommon.fetchJson(
                '/accounts/' + encodeURIComponent(name) + '?include_latest_snapshot=true'
            );

            const profileHtml = _renderProfile(data);
            _expandedRow = `<tr data-expansion-row="true"><td colspan="6">${profileHtml}</td></tr>`;
            loadingRow.innerHTML = `<td colspan="6">${profileHtml}</td>`;
        } catch (err) {
            const errMsg = OsrsCommon.escapeHtml(err.detail || 'Failed to load profile');
            _expandedRow = `<tr data-expansion-row="true"><td colspan="6">
                <div class="osrs-error-box">${errMsg}</div>
            </td></tr>`;
            loadingRow.innerHTML = `<td colspan="6">
                <div class="osrs-error-box">${errMsg}</div>
            </td>`;
        }
    }

    function _collapseExpanded() {
        _expandedName = null;
        _expandedRow = null;

        // Remove expanded class from all rows
        if (_dom.tableBody) {
            const expandedRows = _dom.tableBody.querySelectorAll('.osrs-account-row--expanded');
            for (const r of expandedRows) {
                r.classList.remove('osrs-account-row--expanded');
            }

            // Remove expansion rows
            const expansionRows = _dom.tableBody.querySelectorAll('[data-expansion-row]');
            for (const r of expansionRows) {
                r.remove();
            }
        }
    }

    // =========================================================================
    // RENDER PROFILE EXPANSION
    // =========================================================================

    function _renderProfile(data) {
        const esc = OsrsCommon.escapeHtml;
        const backendUrl = OsrsCommon.getBackendBaseUrl();
        const name = esc(data.name || '');
        const mode = _formatModeLabel(data.default_mode || 'main');
        const snapshot = data.latest_snapshot_data || null;

        let html = '<div class="osrs-profile osrs-fade-in">';

        // Summary header
        html += '<div style="display:flex;align-items:center;gap:var(--space-3);flex-wrap:wrap;">';
        html += `<span style="font-family:var(--font-heading);font-size:var(--text-lg);font-weight:var(--font-bold);color:var(--text-primary);">${name}</span>`;
        html += `<span class="osrs-badge osrs-badge--mode">${esc(mode)}</span>`;

        if (snapshot) {
            const totalLevel = snapshot.total_level != null ? OsrsCommon.formatLevel(snapshot.total_level) : '--';
            const totalXp = snapshot.total_xp != null ? OsrsCommon.formatXp(snapshot.total_xp) : '--';
            html += `<span class="osrs-badge osrs-badge--info">Total Level: ${totalLevel}</span>`;
            html += `<span class="osrs-badge osrs-badge--info">Total XP: ${totalXp}</span>`;
        }

        // Run Snapshot button
        html += `<button class="btn btn-primary btn-sm" onclick="OsrsAccounts.runSnapshotForPlayer('${esc(data.name || '')}')" style="margin-left:auto;">
            <svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="margin-right:4px;vertical-align:middle;">
                <path d="M4 4l12 6-12 6V4z" fill="currentColor"/>
            </svg>
            Run Snapshot
        </button>`;
        html += '</div>';

        if (!snapshot) {
            html += '<div class="osrs-empty" style="padding:var(--space-6);"><p class="osrs-empty__message">No snapshot data yet</p><p class="osrs-empty__submessage">Run a snapshot to see skills and activities.</p></div>';
            html += '</div>';
            return html;
        }

        // Skills section
        if (snapshot.skills && snapshot.skills.length > 0) {
            html += '<div>';
            html += '<h3 class="osrs-profile__section-title">Skills</h3>';
            html += OsrsCommon.renderSkillGrid(snapshot.skills, backendUrl);
            html += '</div>';
        }

        // Activities section
        if (snapshot.activities && snapshot.activities.length > 0) {
            html += '<div>';
            html += '<h3 class="osrs-profile__section-title">Activities &amp; Bosses</h3>';
            html += OsrsCommon.renderActivityList(snapshot.activities, backendUrl);
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    // =========================================================================
    // CREATE ACCOUNT
    // =========================================================================

    async function createAccount() {
        const name = (_dom.createNameInput && _dom.createNameInput.value || '').trim();
        const mode = (_dom.createModeSelect && _dom.createModeSelect.value) || 'main';

        if (!name) {
            _showCreateError('Player name is required.');
            if (_dom.createNameInput) _dom.createNameInput.focus();
            return;
        }

        // Disable button to prevent double-submit
        if (_dom.submitCreateBtn) _dom.submitCreateBtn.disabled = true;
        _hideCreateError();

        try {
            await OsrsCommon.postJson('/accounts', {
                name: name,
                default_mode: mode
            });

            _showToast('Account created: ' + name, 'success');
            _closeCreateModal();
            await loadAccounts();
        } catch (err) {
            const detail = err.detail || 'Failed to create account';
            _showCreateError(detail);
        } finally {
            if (_dom.submitCreateBtn) _dom.submitCreateBtn.disabled = false;
        }
    }

    // =========================================================================
    // DELETE ACCOUNT
    // =========================================================================

    async function deleteAccount(name) {
        _openDeleteModal(name);
    }

    async function _confirmDelete() {
        const name = _pendingDeleteName;
        if (!name) return;

        if (_dom.confirmDeleteBtn) _dom.confirmDeleteBtn.disabled = true;

        try {
            await OsrsCommon.deleteJson('/accounts/' + encodeURIComponent(name));
            _showToast('Account deleted: ' + name, 'success');
            _closeDeleteModal();

            // If this was the expanded account, collapse it
            if (_expandedName === name) {
                _collapseExpanded();
            }

            await loadAccounts();
        } catch (err) {
            const detail = err.detail || 'Failed to delete account';
            _showToast(detail, 'error');
        } finally {
            if (_dom.confirmDeleteBtn) _dom.confirmDeleteBtn.disabled = false;
        }
    }

    // =========================================================================
    // RUN SNAPSHOT
    // =========================================================================

    async function runSnapshotForPlayer(name) {
        _showToast('Starting snapshot for ' + name + '...', 'info');

        try {
            await OsrsCommon.postJson('/snapshots/run', {
                player: name,
                mode: 'auto'
            });
            _showToast('Snapshot completed for ' + name, 'success');

            // Reload the profile if expanded
            if (_expandedName === name) {
                const row = _dom.tableBody
                    ? _dom.tableBody.querySelector(`[data-account-name="${CSS.escape(name)}"][data-action="expand"]`)
                    : null;
                if (row) {
                    _collapseExpanded();
                    await expandProfile(name, row);
                }
            }

            // Reload accounts to update snapshot count/timestamp
            await loadAccounts();
        } catch (err) {
            if (err.status === 503) {
                _showToast('Backend is offline. Start it from the Control Center.', 'error');
            } else {
                _showToast(err.detail || 'Snapshot failed', 'error');
            }
        }
    }

    // =========================================================================
    // MODAL HELPERS
    // =========================================================================

    function _openCreateModal() {
        if (_dom.createModal) {
            _dom.createModal.classList.remove('osrs-hidden');
            _hideCreateError();
            if (_dom.createNameInput) {
                _dom.createNameInput.value = '';
                _dom.createNameInput.focus();
            }
            if (_dom.createModeSelect) _dom.createModeSelect.value = 'main';
        }
    }

    function _closeCreateModal() {
        if (_dom.createModal) {
            _dom.createModal.classList.add('osrs-hidden');
        }
        _hideCreateError();
    }

    function _openDeleteModal(name) {
        _pendingDeleteName = name;
        if (_dom.deleteNameEl) {
            _dom.deleteNameEl.textContent = name;
        }
        if (_dom.deleteModal) {
            _dom.deleteModal.classList.remove('osrs-hidden');
        }
    }

    function _closeDeleteModal() {
        _pendingDeleteName = null;
        if (_dom.deleteModal) {
            _dom.deleteModal.classList.add('osrs-hidden');
        }
    }

    // =========================================================================
    // UI STATE MANAGEMENT
    // =========================================================================

    function _showState(state) {
        const hide = (el) => { if (el) el.classList.add('osrs-hidden'); };
        const show = (el) => { if (el) el.classList.remove('osrs-hidden'); };

        hide(_dom.loading);
        hide(_dom.error);
        hide(_dom.empty);
        hide(_dom.tableWrap);

        switch (state) {
            case 'loading': show(_dom.loading); break;
            case 'error': show(_dom.error); break;
            case 'empty': show(_dom.empty); break;
            case 'table': show(_dom.tableWrap); break;
        }
    }

    function _showError(message) {
        if (_dom.error) {
            _dom.error.textContent = message;
            _dom.error.classList.remove('osrs-hidden');
        }
    }

    function _showCreateError(message) {
        if (_dom.createError) {
            _dom.createError.textContent = message;
            _dom.createError.classList.remove('osrs-hidden');
        }
    }

    function _hideCreateError() {
        if (_dom.createError) {
            _dom.createError.textContent = '';
            _dom.createError.classList.add('osrs-hidden');
        }
    }

    // =========================================================================
    // TOAST NOTIFICATIONS
    // =========================================================================

    let _toastTimer = null;

    function _showToast(message, type) {
        if (!_dom.toast) return;

        // Clear any pending dismiss
        if (_toastTimer) {
            clearTimeout(_toastTimer);
            _toastTimer = null;
        }

        // Set colors based on type
        let bg, border, color;
        switch (type) {
            case 'success':
                bg = 'var(--success-glow)';
                border = 'var(--success)';
                color = 'var(--success)';
                break;
            case 'error':
                bg = 'var(--error-glow)';
                border = 'var(--error)';
                color = 'var(--error)';
                break;
            default: // info
                bg = 'var(--cyan-glow)';
                border = 'var(--cyan-500)';
                color = 'var(--cyan-400)';
                break;
        }

        _dom.toast.style.background = bg;
        _dom.toast.style.border = '1px solid ' + border;
        _dom.toast.style.color = color;
        _dom.toast.textContent = message;
        _dom.toast.classList.remove('osrs-hidden');

        // Auto-dismiss after 4 seconds
        _toastTimer = setTimeout(() => {
            _dom.toast.classList.add('osrs-hidden');
            _toastTimer = null;
        }, 4000);
    }

    // =========================================================================
    // FORMAT HELPERS
    // =========================================================================

    function _formatModeLabel(mode) {
        const labels = {
            main: 'Main',
            ironman: 'Ironman',
            hardcore_ironman: 'Hardcore',
            ultimate_ironman: 'Ultimate',
            deadman: 'Deadman',
            tournament: 'Tournament',
            seasonal: 'Seasonal'
        };
        return labels[mode] || mode;
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    return {
        init,
        destroy,
        refresh,
        createAccount,
        deleteAccount,
        expandProfile,
        runSnapshotForPlayer
    };
})();

window.OsrsAccounts = OsrsAccounts;
