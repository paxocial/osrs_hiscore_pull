/**
 * OSRS Compare -- Player Comparison Module
 * ==========================================
 * Autocomplete player search, head-to-head comparison, skill/activity rendering.
 * Pattern: Named IIFE exported as window.OsrsCompare
 *
 * Dependencies:
 *   - OsrsCommon (osrs-common.js) for fetchJson, escapeHtml, formatXp, etc.
 *   - API global (Council app.js) for auth headers (used indirectly via OsrsCommon)
 */

const OsrsCompare = (() => {
    'use strict';

    // =========================================================================
    // STATE
    // =========================================================================

    const _dom = {};
    let _debounceTimerA = null;
    let _debounceTimerB = null;
    let _selectedPlayerA = null;
    let _selectedPlayerB = null;
    let _activeDropdown = null;     // 'a' | 'b' | null
    let _activeSuggestionIdx = -1;  // keyboard navigation index
    let _lastComparisonData = null; // cached for refresh
    let _documentClickBound = null; // reference for cleanup

    const DEBOUNCE_MS = 300;
    const MIN_QUERY_LENGTH = 2;

    // =========================================================================
    // LIFECYCLE
    // =========================================================================

    /**
     * Initialize the compare module.
     * Caches DOM refs, binds events, sets up council switch listener.
     */
    function init() {
        _cacheDom();
        if (!_dom.root) return;
        _bindEvents();
        OsrsCommon.listenCouncilSwitch(() => { destroy(); init(); });
    }

    /**
     * Clean up timers and event listeners.
     */
    function destroy() {
        if (_debounceTimerA) { clearTimeout(_debounceTimerA); _debounceTimerA = null; }
        if (_debounceTimerB) { clearTimeout(_debounceTimerB); _debounceTimerB = null; }
        if (_documentClickBound) {
            document.removeEventListener('click', _documentClickBound);
            _documentClickBound = null;
        }
        _selectedPlayerA = null;
        _selectedPlayerB = null;
        _lastComparisonData = null;
        _activeDropdown = null;
        _activeSuggestionIdx = -1;
    }

    /**
     * Re-run comparison if players were previously selected.
     */
    function refresh() {
        if (_selectedPlayerA && _selectedPlayerB) {
            runComparison();
        }
    }

    // =========================================================================
    // DOM CACHING
    // =========================================================================

    function _cacheDom() {
        _dom.root = document.getElementById('osrs-compare-root');
        if (!_dom.root) return;

        _dom.inputA = document.getElementById('compare-player-a');
        _dom.inputB = document.getElementById('compare-player-b');
        _dom.suggestionsA = document.getElementById('compare-suggestions-a');
        _dom.suggestionsB = document.getElementById('compare-suggestions-b');
        _dom.timeframe = document.getElementById('compare-timeframe');
        _dom.runBtn = document.getElementById('compare-run-btn');
        _dom.error = document.getElementById('compare-error');
        _dom.loading = document.getElementById('compare-loading');
        _dom.empty = document.getElementById('compare-empty');
        _dom.results = document.getElementById('compare-results');
        _dom.summary = document.getElementById('compare-summary');
        _dom.skillsBody = document.getElementById('compare-skills-body');
        _dom.activitiesBody = document.getElementById('compare-activities-body');
        _dom.thPlayerA = document.getElementById('compare-th-player-a');
        _dom.thPlayerB = document.getElementById('compare-th-player-b');
        _dom.actThA = document.getElementById('compare-act-th-a');
        _dom.actThB = document.getElementById('compare-act-th-b');
    }

    // =========================================================================
    // EVENT BINDING
    // =========================================================================

    function _bindEvents() {
        // Player A input: keyup -> debounce search
        if (_dom.inputA) {
            _dom.inputA.addEventListener('input', () => {
                _selectedPlayerA = null;
                _debounceSearch('a');
            });
            _dom.inputA.addEventListener('keydown', (e) => _handleKeydown(e, 'a'));
            _dom.inputA.addEventListener('focus', () => {
                // Re-show suggestions if there are items and input has value
                if (_dom.inputA.value.length >= MIN_QUERY_LENGTH && _dom.suggestionsA.children.length > 0) {
                    _openDropdown('a');
                }
            });
        }

        // Player B input: keyup -> debounce search
        if (_dom.inputB) {
            _dom.inputB.addEventListener('input', () => {
                _selectedPlayerB = null;
                _debounceSearch('b');
            });
            _dom.inputB.addEventListener('keydown', (e) => _handleKeydown(e, 'b'));
            _dom.inputB.addEventListener('focus', () => {
                if (_dom.inputB.value.length >= MIN_QUERY_LENGTH && _dom.suggestionsB.children.length > 0) {
                    _openDropdown('b');
                }
            });
        }

        // Compare button
        if (_dom.runBtn) {
            _dom.runBtn.addEventListener('click', () => runComparison());
        }

        // Click outside suggestions -> close dropdowns
        _documentClickBound = (e) => {
            if (!_dom.root) return;
            const wrapperA = document.getElementById('compare-player-a-wrapper');
            const wrapperB = document.getElementById('compare-player-b-wrapper');
            if (wrapperA && !wrapperA.contains(e.target)) {
                _closeDropdown('a');
            }
            if (wrapperB && !wrapperB.contains(e.target)) {
                _closeDropdown('b');
            }
        };
        document.addEventListener('click', _documentClickBound);
    }

    // =========================================================================
    // AUTOCOMPLETE SEARCH
    // =========================================================================

    /**
     * Debounce the player search for a given side.
     * @param {'a'|'b'} side
     */
    function _debounceSearch(side) {
        if (side === 'a') {
            if (_debounceTimerA) clearTimeout(_debounceTimerA);
            _debounceTimerA = setTimeout(() => _searchPlayers(side), DEBOUNCE_MS);
        } else {
            if (_debounceTimerB) clearTimeout(_debounceTimerB);
            _debounceTimerB = setTimeout(() => _searchPlayers(side), DEBOUNCE_MS);
        }
    }

    /**
     * Search for players via the compare/search proxy endpoint.
     * @param {'a'|'b'} side
     */
    async function _searchPlayers(side) {
        const input = side === 'a' ? _dom.inputA : _dom.inputB;
        const suggestionsEl = side === 'a' ? _dom.suggestionsA : _dom.suggestionsB;

        if (!input || !suggestionsEl) return;

        const query = input.value.trim();
        if (query.length < MIN_QUERY_LENGTH) {
            _closeDropdown(side);
            suggestionsEl.innerHTML = '';
            return;
        }

        try {
            // GET /api/osrs/compare/search?q={query}
            const data = await OsrsCommon.fetchJson(
                '/compare/search?q=' + encodeURIComponent(query)
            );

            const results = data.results || [];
            _renderSuggestions(side, results);

            if (results.length > 0) {
                _openDropdown(side);
            } else {
                _closeDropdown(side);
            }
        } catch (err) {
            // On error (e.g. backend offline), close dropdown silently
            _closeDropdown(side);
            suggestionsEl.innerHTML = '';
        }
    }

    /**
     * Render the suggestion dropdown items.
     * @param {'a'|'b'} side
     * @param {string[]} results - Array of player names
     */
    function _renderSuggestions(side, results) {
        const suggestionsEl = side === 'a' ? _dom.suggestionsA : _dom.suggestionsB;
        if (!suggestionsEl) return;

        _activeSuggestionIdx = -1;

        if (results.length === 0) {
            suggestionsEl.innerHTML = '<div class="osrs-compare-suggestions__item osrs-text-muted" style="pointer-events:none;">No players found</div>';
            return;
        }

        let html = '';
        for (let i = 0; i < results.length; i++) {
            const name = OsrsCommon.escapeHtml(results[i]);
            html += `<div class="osrs-compare-suggestions__item" data-index="${i}" data-name="${name}">${name}</div>`;
        }
        suggestionsEl.innerHTML = html;

        // Bind click handlers on suggestions
        const items = suggestionsEl.querySelectorAll('.osrs-compare-suggestions__item[data-name]');
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                _selectPlayer(side, item.getAttribute('data-name'));
            });
        });
    }

    /**
     * Handle keyboard navigation in suggestion dropdown.
     * @param {KeyboardEvent} e
     * @param {'a'|'b'} side
     */
    function _handleKeydown(e, side) {
        const suggestionsEl = side === 'a' ? _dom.suggestionsA : _dom.suggestionsB;
        if (!suggestionsEl) return;

        const items = suggestionsEl.querySelectorAll('.osrs-compare-suggestions__item[data-name]');
        if (items.length === 0) return;

        const isOpen = suggestionsEl.classList.contains('osrs-compare-suggestions--open');
        if (!isOpen) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                _activeSuggestionIdx = Math.min(_activeSuggestionIdx + 1, items.length - 1);
                _highlightSuggestion(items, _activeSuggestionIdx);
                break;

            case 'ArrowUp':
                e.preventDefault();
                _activeSuggestionIdx = Math.max(_activeSuggestionIdx - 1, 0);
                _highlightSuggestion(items, _activeSuggestionIdx);
                break;

            case 'Enter':
                e.preventDefault();
                if (_activeSuggestionIdx >= 0 && _activeSuggestionIdx < items.length) {
                    _selectPlayer(side, items[_activeSuggestionIdx].getAttribute('data-name'));
                }
                break;

            case 'Escape':
                e.preventDefault();
                _closeDropdown(side);
                break;
        }
    }

    /**
     * Highlight a suggestion item by index.
     * @param {NodeList} items
     * @param {number} idx
     */
    function _highlightSuggestion(items, idx) {
        items.forEach((item, i) => {
            if (i === idx) {
                item.classList.add('osrs-compare-suggestions__item--active');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('osrs-compare-suggestions__item--active');
            }
        });
    }

    /**
     * Select a player from suggestions.
     * @param {'a'|'b'} side
     * @param {string} name
     */
    function _selectPlayer(side, name) {
        const input = side === 'a' ? _dom.inputA : _dom.inputB;
        if (!input) return;

        input.value = name;
        if (side === 'a') {
            _selectedPlayerA = name;
        } else {
            _selectedPlayerB = name;
        }

        _closeDropdown(side);
        _activeSuggestionIdx = -1;
    }

    /**
     * Open the suggestion dropdown.
     * @param {'a'|'b'} side
     */
    function _openDropdown(side) {
        const el = side === 'a' ? _dom.suggestionsA : _dom.suggestionsB;
        if (el) {
            el.classList.add('osrs-compare-suggestions--open');
            _activeDropdown = side;
        }
    }

    /**
     * Close the suggestion dropdown.
     * @param {'a'|'b'} side
     */
    function _closeDropdown(side) {
        const el = side === 'a' ? _dom.suggestionsA : _dom.suggestionsB;
        if (el) {
            el.classList.remove('osrs-compare-suggestions--open');
            if (_activeDropdown === side) _activeDropdown = null;
            _activeSuggestionIdx = -1;
        }
    }

    // =========================================================================
    // COMPARISON
    // =========================================================================

    /**
     * Run the player comparison.
     * Validates selection, fetches data, renders results.
     */
    async function runComparison() {
        if (!_selectedPlayerA || !_selectedPlayerB) {
            _showError('Please select two players to compare.');
            return;
        }

        if (_selectedPlayerA.toLowerCase() === _selectedPlayerB.toLowerCase()) {
            _showError('Please select two different players to compare.');
            return;
        }

        _hideError();
        _showLoading();
        _hideEmpty();
        _hideResults();

        const timeframe = _dom.timeframe ? _dom.timeframe.value : '7d';

        try {
            // GET /api/osrs/compare/data?a={playerA}&b={playerB}&timeframe={tf}
            const data = await OsrsCommon.fetchJson(
                '/compare/data?a=' + encodeURIComponent(_selectedPlayerA) +
                '&b=' + encodeURIComponent(_selectedPlayerB) +
                '&timeframe=' + encodeURIComponent(timeframe)
            );

            _lastComparisonData = data;
            OsrsCommon.hideOfflineBanner(_dom.root);

            if (!data.players || data.players.length < 2) {
                _hideLoading();
                _showError(
                    data.players && data.players.length === 1
                        ? 'One player was not found. Make sure both accounts have been snapshotted.'
                        : 'Neither player was found. Check the names and try again.'
                );
                _showEmpty();
                return;
            }

            _renderResults(data);
            _hideLoading();
            _showResults();
        } catch (err) {
            _hideLoading();
            if (err && err.status === 503) {
                OsrsCommon.showOfflineBanner(_dom.root);
                _showError('OSRS backend is offline. Start it from the Control Center.');
            } else {
                _showError(
                    (err && err.detail) ? err.detail : 'Failed to fetch comparison data.'
                );
            }
        }
    }

    // =========================================================================
    // RENDERING
    // =========================================================================

    /**
     * Render the full comparison results.
     * @param {object} data - The compare/data response
     */
    function _renderResults(data) {
        const pa = data.players[0];
        const pb = data.players[1];
        const skillWinners = data.skill_winners || {};
        const baseUrl = OsrsCommon.getBackendBaseUrl();

        _renderSummaryCards(pa, pb, baseUrl);
        _renderSkillTable(pa, pb, skillWinners, baseUrl);
        _renderActivityTable(pa, pb, baseUrl);
    }

    /**
     * Render summary comparison cards.
     * Winner is determined by higher total_xp.
     */
    function _renderSummaryCards(pa, pb, baseUrl) {
        if (!_dom.summary) return;

        const aWins = (pa.total_xp || 0) > (pb.total_xp || 0);
        const bWins = (pb.total_xp || 0) > (pa.total_xp || 0);

        _dom.summary.innerHTML =
            _renderOnePlayerCard(pa, aWins) +
            _renderOnePlayerCard(pb, bWins);
    }

    /**
     * Render a single player summary card.
     * @param {object} player
     * @param {boolean} isWinner
     * @returns {string} HTML
     */
    function _renderOnePlayerCard(player, isWinner) {
        const esc = OsrsCommon.escapeHtml;
        const fmtXp = OsrsCommon.formatXp;
        const fmtDelta = OsrsCommon.formatDelta;

        const winnerClass = isWinner ? ' osrs-compare-player--winner' : '';
        const xpGain = fmtDelta(player.xp_gain);
        const levelGain = fmtDelta(player.level_gain);

        const modeBadge = player.mode && player.mode !== 'main'
            ? `<span class="osrs-badge osrs-badge--mode">${esc(player.mode)}</span>`
            : '';

        return `<div class="osrs-compare-player${winnerClass}">
            <div class="osrs-compare-player__name">
                ${esc(player.name)} ${modeBadge}
            </div>
            <div class="osrs-compare-player__stats">
                <div class="osrs-kpi">
                    <span class="osrs-kpi__value">${fmtXp(player.total_xp)}</span>
                    <span class="osrs-kpi__label">Total XP</span>
                    <span class="osrs-delta-chip ${xpGain.className}">${xpGain.text}</span>
                </div>
                <div class="osrs-kpi">
                    <span class="osrs-kpi__value">${player.total_level != null ? player.total_level.toLocaleString('en-US') : '--'}</span>
                    <span class="osrs-kpi__label">Total Level</span>
                    <span class="osrs-delta-chip ${levelGain.className}">${levelGain.text}</span>
                </div>
            </div>
        </div>`;
    }

    /**
     * Render the skill comparison table.
     * Three columns: Player A stats | Skill icon + name | Player B stats
     */
    function _renderSkillTable(pa, pb, skillWinners, baseUrl) {
        if (!_dom.skillsBody) return;

        const esc = OsrsCommon.escapeHtml;
        const fmtXp = OsrsCommon.formatXp;
        const fmtLvl = OsrsCommon.formatLevel;
        const fmtRank = OsrsCommon.formatRank;

        // Update table headers with player names
        if (_dom.thPlayerA) _dom.thPlayerA.textContent = pa.name;
        if (_dom.thPlayerB) _dom.thPlayerB.textContent = pb.name;

        // Build skill lookups by normalized name
        const skillsA = {};
        const skillsB = {};
        if (pa.skills) {
            for (const sk of pa.skills) {
                if (sk && sk.name) skillsA[sk.name.toLowerCase()] = sk;
            }
        }
        if (pb.skills) {
            for (const sk of pb.skills) {
                if (sk && sk.name) skillsB[sk.name.toLowerCase()] = sk;
            }
        }

        // Determine full skill order: Overall first, then SKILL_ORDER, then any remaining
        const order = ['overall', ...OsrsCommon.SKILL_ORDER];
        const seen = new Set(order);
        // Add any skills not in our canonical order
        const allSkillNames = new Set([
            ...Object.keys(skillsA),
            ...Object.keys(skillsB)
        ]);
        for (const name of allSkillNames) {
            if (!seen.has(name)) {
                order.push(name);
                seen.add(name);
            }
        }

        let html = '';
        for (const skillName of order) {
            const skA = skillsA[skillName] || { level: -1, xp: -1, rank: -1, xp_gain: 0, level_gain: 0 };
            const skB = skillsB[skillName] || { level: -1, xp: -1, rank: -1, xp_gain: 0, level_gain: 0 };

            // Find the display name from whichever side has it
            const displayName = (skA.name || skB.name || skillName);

            // Determine winner for this skill
            const aXp = skA.xp != null && skA.xp >= 0 ? skA.xp : 0;
            const bXp = skB.xp != null && skB.xp >= 0 ? skB.xp : 0;
            const maxXp = Math.max(aXp, bXp);
            const aPct = maxXp > 0 ? Math.round((aXp / maxXp) * 100) : 0;
            const bPct = maxXp > 0 ? Math.round((bXp / maxXp) * 100) : 0;

            // Use skill_winners if available, otherwise compute from XP
            let winner = 'tie';
            const winnerKey = displayName;
            if (skillWinners[winnerKey]) {
                winner = skillWinners[winnerKey] === pa.name ? 'a'
                       : skillWinners[winnerKey] === pb.name ? 'b'
                       : 'tie';
            } else if (aXp > bXp) {
                winner = 'a';
            } else if (bXp > aXp) {
                winner = 'b';
            }

            const aWinCls = winner === 'a' ? ' osrs-compare-table__value--winner' : (winner === 'b' ? ' osrs-compare-table__value--loser' : '');
            const bWinCls = winner === 'b' ? ' osrs-compare-table__value--winner' : (winner === 'a' ? ' osrs-compare-table__value--loser' : '');

            // XP gain delta chips for each side
            const aGainHtml = _renderInlineGain(skA.xp_gain);
            const bGainHtml = _renderInlineGain(skB.xp_gain);

            html += `<tr>
                <td class="osrs-compare-table__player-a${aWinCls}">
                    <div>${fmtLvl(skA.level)} &middot; ${fmtXp(skA.xp)}</div>
                    <div class="osrs-compare-bar"><div class="osrs-compare-bar__fill" style="width: ${aPct}%;"></div></div>
                    ${aGainHtml}
                </td>
                <td style="text-align: center;">
                    <div class="osrs-compare-table__skill-cell">
                        ${OsrsCommon.renderSkillIcon(skillName, baseUrl)}
                        <span>${esc(displayName)}</span>
                    </div>
                </td>
                <td class="osrs-compare-table__player-b${bWinCls}">
                    <div>${fmtLvl(skB.level)} &middot; ${fmtXp(skB.xp)}</div>
                    <div class="osrs-compare-bar"><div class="osrs-compare-bar__fill" style="width: ${bPct}%;"></div></div>
                    ${bGainHtml}
                </td>
            </tr>`;
        }

        _dom.skillsBody.innerHTML = html;
    }

    /**
     * Render an inline XP gain indicator.
     * @param {number|null} gain
     * @returns {string} HTML
     */
    function _renderInlineGain(gain) {
        if (gain == null || gain === 0) return '';
        const delta = OsrsCommon.formatDelta(gain);
        return `<span class="osrs-delta-chip ${delta.className}" style="font-size: var(--text-xs);">${delta.text} xp</span>`;
    }

    /**
     * Render the activity comparison table.
     * Three columns: Activity name | Player A score | Player B score
     */
    function _renderActivityTable(pa, pb, baseUrl) {
        if (!_dom.activitiesBody) return;

        const esc = OsrsCommon.escapeHtml;
        const fmtScore = (score) => {
            if (score == null || score < 0) return '--';
            return Number(score).toLocaleString('en-US');
        };

        // Update activity table headers with player names
        if (_dom.actThA) _dom.actThA.textContent = pa.name;
        if (_dom.actThB) _dom.actThB.textContent = pb.name;

        // Build activity lookups
        const actsA = {};
        const actsB = {};
        if (pa.activities) {
            for (const act of pa.activities) {
                if (act && act.name) actsA[act.name.toLowerCase()] = act;
            }
        }
        if (pb.activities) {
            for (const act of pb.activities) {
                if (act && act.name) actsB[act.name.toLowerCase()] = act;
            }
        }

        // Combine all activity names, preserving order from player A first
        const orderedNames = [];
        const seenActs = new Set();
        const addIfUnseen = (act) => {
            if (act && act.name) {
                const key = act.name.toLowerCase();
                if (!seenActs.has(key)) {
                    seenActs.add(key);
                    orderedNames.push({ key, displayName: act.name });
                }
            }
        };
        if (pa.activities) pa.activities.forEach(addIfUnseen);
        if (pb.activities) pb.activities.forEach(addIfUnseen);

        // Filter to only show activities where at least one player has a positive score
        const relevantActivities = orderedNames.filter(({ key }) => {
            const scoreA = (actsA[key] && actsA[key].score != null && actsA[key].score >= 0) ? actsA[key].score : 0;
            const scoreB = (actsB[key] && actsB[key].score != null && actsB[key].score >= 0) ? actsB[key].score : 0;
            return scoreA > 0 || scoreB > 0;
        });

        if (relevantActivities.length === 0) {
            _dom.activitiesBody.innerHTML = `<tr><td colspan="3" class="osrs-empty" style="padding: var(--space-6);">
                <p class="osrs-empty__message">No activity data for these players</p>
            </td></tr>`;
            return;
        }

        let html = '';
        for (const { key, displayName } of relevantActivities) {
            const actA = actsA[key] || { score: -1, rank: -1, score_gain: 0 };
            const actB = actsB[key] || { score: -1, rank: -1, score_gain: 0 };

            const scoreA = (actA.score != null && actA.score >= 0) ? actA.score : 0;
            const scoreB = (actB.score != null && actB.score >= 0) ? actB.score : 0;

            const aLeads = scoreA > scoreB;
            const bLeads = scoreB > scoreA;

            const aWinCls = aLeads ? ' osrs-compare-table__value--winner' : (bLeads ? ' osrs-compare-table__value--loser' : '');
            const bWinCls = bLeads ? ' osrs-compare-table__value--winner' : (aLeads ? ' osrs-compare-table__value--loser' : '');

            // Score gain chips
            const aGainHtml = _renderScoreGain(actA.score_gain);
            const bGainHtml = _renderScoreGain(actB.score_gain);

            html += `<tr>
                <td style="text-align: center;">
                    <div class="osrs-compare-table__skill-cell">
                        ${OsrsCommon.renderGameIcon(displayName, baseUrl)}
                        <span>${esc(displayName)}</span>
                    </div>
                </td>
                <td class="osrs-compare-table__player-a${aWinCls}" style="text-align: right;">
                    ${fmtScore(actA.score)}
                    ${aGainHtml}
                </td>
                <td class="osrs-compare-table__player-b${bWinCls}" style="text-align: left;">
                    ${fmtScore(actB.score)}
                    ${bGainHtml}
                </td>
            </tr>`;
        }

        _dom.activitiesBody.innerHTML = html;
    }

    /**
     * Render an inline score gain indicator.
     * @param {number|null} gain
     * @returns {string} HTML
     */
    function _renderScoreGain(gain) {
        if (gain == null || gain === 0) return '';
        const delta = OsrsCommon.formatDelta(gain);
        return `<span class="osrs-delta-chip ${delta.className}" style="font-size: var(--text-xs);">${delta.text}</span>`;
    }

    // =========================================================================
    // UI STATE MANAGEMENT
    // =========================================================================

    function _showLoading() {
        if (_dom.loading) _dom.loading.classList.remove('osrs-hidden');
    }

    function _hideLoading() {
        if (_dom.loading) _dom.loading.classList.add('osrs-hidden');
    }

    function _showEmpty() {
        if (_dom.empty) _dom.empty.classList.remove('osrs-hidden');
    }

    function _hideEmpty() {
        if (_dom.empty) _dom.empty.classList.add('osrs-hidden');
    }

    function _showResults() {
        if (_dom.results) _dom.results.classList.remove('osrs-hidden');
    }

    function _hideResults() {
        if (_dom.results) _dom.results.classList.add('osrs-hidden');
    }

    function _showError(message) {
        if (!_dom.error) return;
        _dom.error.textContent = message;
        _dom.error.classList.remove('osrs-hidden');
    }

    function _hideError() {
        if (!_dom.error) return;
        _dom.error.textContent = '';
        _dom.error.classList.add('osrs-hidden');
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    return { init, destroy, refresh, runComparison };
})();

window.OsrsCompare = OsrsCompare;
