/**
 * OSRS Common -- Shared IIFE Module
 * ====================================
 * Shared utilities used by all OSRS council page modules.
 * Pattern: Named IIFE exported as window.OsrsCommon
 *
 * Dependencies: None (OSRS proxy is unauthenticated — public game data).
 */

const OsrsCommon = (() => {
    'use strict';

    // =========================================================================
    // CONFIGURATION
    // =========================================================================

    const API_PREFIX = '/api/osrs';
    const BACKEND_BASE_URL_KEY = 'osrs_backend_url';
    const DEFAULT_BACKEND_URL = 'http://localhost:8001';

    // =========================================================================
    // SKILL ICON MAP
    // Ported from web/templates/macros/skill_icons.html -- single source of truth
    // Includes all canonical names plus common aliases.
    // =========================================================================

    const SKILL_ICON_MAP = {
        // Canonical 23 skills
        attack: 'Attack_icon.png',
        strength: 'Strength_icon.png',
        defence: 'Defence_icon.png',
        ranged: 'Ranged_icon.png',
        prayer: 'Prayer_icon.png',
        magic: 'Magic_icon.png',
        runecraft: 'Runecraft_icon.png',
        construction: 'Construction_icon.png',
        hitpoints: 'Hitpoints_icon.png',
        agility: 'Agility_icon.png',
        herblore: 'Herblore_icon.png',
        thieving: 'Thieving_icon.png',
        crafting: 'Crafting_icon.png',
        fletching: 'Fletching_icon.png',
        slayer: 'Slayer_icon.png',
        hunter: 'Hunter_icon.png',
        mining: 'Mining_icon.png',
        smithing: 'Smithing_icon.png',
        fishing: 'Fishing_icon.png',
        cooking: 'Cooking_icon.png',
        firemaking: 'Firemaking_icon.png',
        woodcutting: 'Woodcutting_icon.png',
        farming: 'Farming_icon.png',

        // Aliases (from skill_icons.html macro)
        defense: 'Defence_icon.png',
        runecrafting: 'Runecraft_icon.png',
        hitpoint: 'Hitpoints_icon.png',

        // Additional / meta
        sailing: 'Sailing_icon.png',
        combat: 'Combat.png',
        overall: 'Stats_icon.png',
    };

    // Canonical skill display order (OSRS hiscore order, 3-column layout)
    const SKILL_ORDER = [
        'attack', 'hitpoints', 'mining',
        'strength', 'agility', 'smithing',
        'defence', 'herblore', 'fishing',
        'ranged', 'thieving', 'cooking',
        'prayer', 'crafting', 'firemaking',
        'magic', 'fletching', 'woodcutting',
        'runecraft', 'slayer', 'farming',
        'construction', 'hunter'
    ];

    const SNAPSHOT_MODES = [
        'auto', 'main', 'ironman', 'hardcore_ironman',
        'ultimate_ironman', 'deadman', 'tournament', 'seasonal'
    ];

    // Special game icon overrides (bosses/minigames with non-standard names)
    const GAME_ICON_OVERRIDES = {
        deadmanpoints: 'minigame_icon_hs_thumb.png',
        gridpoints: 'minigame_icon_hs_thumb.png',
        leaguepoints: 'minigame_icon_hs_thumb.png',
    };

    // =========================================================================
    // HTTP HELPERS
    // OSRS proxy endpoints are unauthenticated (public game data).
    // Only X-Council-Id is sent for council isolation.
    // =========================================================================

    function _councilHeaders() {
        const headers = {};
        const councilId = (typeof sessionStorage !== 'undefined' && sessionStorage.getItem('activeCouncilId'))
            || (typeof localStorage !== 'undefined' && localStorage.getItem('selectedCouncil'));
        if (councilId) {
            headers['X-Council-Id'] = councilId;
        }
        return headers;
    }

    /**
     * GET JSON from the OSRS proxy.
     * @param {string} path - Path after /api/osrs (e.g. '/health')
     * @param {object} options - Additional fetch options
     * @returns {Promise<object>} Parsed JSON response
     */
    async function fetchJson(path, options = {}) {
        const url = API_PREFIX + path;
        const { headers: extraHeaders, ...restOptions } = options;
        const response = await fetch(url, {
            ...restOptions,
            headers: {
                ..._councilHeaders(),
                ...(extraHeaders || {})
            }
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw { status: response.status, detail: error.detail || response.statusText, ...error };
        }
        return response.json();
    }

    /**
     * POST JSON to the OSRS proxy.
     * @param {string} path - Path after /api/osrs
     * @param {object} body - Request body (will be JSON.stringify'd)
     * @returns {Promise<object>} Parsed JSON response
     */
    async function postJson(path, body) {
        const url = API_PREFIX + path;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ..._councilHeaders()
            },
            body: JSON.stringify(body)
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw { status: response.status, detail: error.detail || response.statusText, ...error };
        }
        return response.json();
    }

    /**
     * DELETE to the OSRS proxy.
     * @param {string} path - Path after /api/osrs
     * @returns {Promise<object>} Parsed JSON response
     */
    async function deleteJson(path) {
        const url = API_PREFIX + path;
        const response = await fetch(url, {
            method: 'DELETE',
            headers: _councilHeaders()
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw { status: response.status, detail: error.detail || response.statusText, ...error };
        }
        return response.json();
    }

    // =========================================================================
    // FORMATTERS
    // =========================================================================

    /**
     * Format XP with commas. Returns "--" for null/undefined/-1.
     * @param {number|null} xp
     * @returns {string}
     */
    function formatXp(xp) {
        if (xp == null || xp < 0) return '--';
        return Number(xp).toLocaleString('en-US');
    }

    /**
     * Format level. Returns "--" for null/undefined/-1.
     * @param {number|null} level
     * @returns {string}
     */
    function formatLevel(level) {
        if (level == null || level < 0) return '--';
        return String(level);
    }

    /**
     * Format rank as "#N" with commas. Returns "--" for -1/null.
     * @param {number|null} rank
     * @returns {string}
     */
    function formatRank(rank) {
        if (rank == null || rank < 0) return '--';
        return '#' + Number(rank).toLocaleString('en-US');
    }

    /**
     * Format a delta value with sign and color class name.
     * Returns an object with { text, className }.
     * @param {number|null} value
     * @returns {{ text: string, className: string }}
     */
    function formatDelta(value) {
        if (value == null || value === 0) {
            return { text: '0', className: 'osrs-delta-chip--neutral' };
        }
        if (value > 0) {
            return {
                text: '+' + Number(value).toLocaleString('en-US'),
                className: 'osrs-delta-chip--positive'
            };
        }
        return {
            text: Number(value).toLocaleString('en-US'),
            className: 'osrs-delta-chip--negative'
        };
    }

    /**
     * Format ISO timestamp to locale string.
     * e.g. "Mar 4, 2026 07:30 UTC"
     * @param {string} iso
     * @returns {string}
     */
    function formatTimestamp(iso) {
        if (!iso) return '--';
        try {
            const date = new Date(iso);
            if (isNaN(date.getTime())) return '--';
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZoneName: 'short'
            });
        } catch {
            return '--';
        }
    }

    /**
     * Format ISO timestamp to "Xh ago", "Xd ago" style relative time.
     * @param {string} iso
     * @returns {string}
     */
    function formatTimeAgo(iso) {
        if (!iso) return '--';
        try {
            const date = new Date(iso);
            if (isNaN(date.getTime())) return '--';
            const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
            if (seconds < 0) return 'just now';
            if (seconds < 60) return `${seconds}s ago`;
            const minutes = Math.floor(seconds / 60);
            if (minutes < 60) return `${minutes}m ago`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}h ago`;
            const days = Math.floor(hours / 24);
            if (days < 30) return `${days}d ago`;
            const months = Math.floor(days / 30);
            return `${months}mo ago`;
        } catch {
            return '--';
        }
    }

    /**
     * Escape HTML special characters for safe innerHTML insertion.
     * Delegates to window.escapeHtml (from app.js) if available, else own impl.
     * @param {string} text
     * @returns {string}
     */
    function escapeHtml(text) {
        if (typeof window.escapeHtml === 'function') {
            return window.escapeHtml(text);
        }
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;'
        };
        return String(text).replace(/[&<>"']/g, c => map[c]);
    }

    // =========================================================================
    // ICON RENDERING
    // =========================================================================

    /**
     * Normalize a skill/activity name for icon lookup.
     * Matches the Jinja2 macro: name|lower|replace(' ', '')|replace('_','')|replace('-','')
     * @param {string} name
     * @returns {string}
     */
    function _normalizeName(name) {
        return String(name || '').toLowerCase().replace(/[ _\-]/g, '');
    }

    /**
     * Get the URL for a skill icon.
     * @param {string} name - Skill name (e.g. 'attack', 'Defence', 'hit points')
     * @param {string} baseUrl - Backend base URL (e.g. 'http://localhost:8001')
     * @returns {string} Full URL to the icon PNG
     */
    function skillIconUrl(name) {
        const normalized = _normalizeName(name);
        const filename = SKILL_ICON_MAP[normalized] || 'Combat.png';
        return `/council-static/img/skills/${filename}`;
    }

    /**
     * Get the URL for a game/boss/activity icon.
     * Convention: game_icon_{normalized}.png
     * @param {string} name - Activity name
     * @param {string} baseUrl - Backend base URL
     * @returns {string} Full URL to the icon PNG
     */
    function gameIconUrl(name) {
        const normalized = _normalizeName(name);

        // Check special overrides first
        if (GAME_ICON_OVERRIDES[normalized]) {
            return `/council-static/img/game/${GAME_ICON_OVERRIDES[normalized]}`;
        }

        // Convention: remove spaces, apostrophes, hyphens, parens, colons
        const slug = String(name || '')
            .toLowerCase()
            .replace(/[' \-():]/g, '')
            .replace(/_+/g, '_');
        return `/council-static/img/game/game_icon_${slug}.png`;
    }

    /**
     * Render an <img> tag for a skill icon.
     * @param {string} name - Skill name
     * @param {string} baseUrl - Backend base URL
     * @returns {string} HTML string
     */
    function renderSkillIcon(name) {
        const url = skillIconUrl(name);
        const safe = escapeHtml(name);
        return `<img src="${escapeHtml(url)}" alt="${safe}" class="osrs-skill-icon" width="20" height="20" loading="lazy" decoding="async" fetchpriority="low">`;
    }

    /**
     * Render an <img> tag for a game/activity icon.
     * @param {string} name - Activity name
     * @returns {string} HTML string
     */
    function renderGameIcon(name) {
        const url = gameIconUrl(name);
        const safe = escapeHtml(name);
        return `<img src="${escapeHtml(url)}" alt="${safe}" class="osrs-skill-icon" width="20" height="20" loading="lazy" decoding="async" fetchpriority="low">`;
    }

    // =========================================================================
    // UI HELPERS
    // =========================================================================

    /**
     * Render a complete skill grid HTML string.
     * Each skill card: icon + name + level + xp + rank
     * Uses SKILL_ORDER for display order. Highlights 99 skills.
     *
     * @param {Array} skills - Array of { name, level, xp, rank }
     * @param {string} baseUrl - Backend base URL for icons
     * @returns {string} HTML string for the skill grid
     */
    function renderSkillGrid(skills, baseUrl) {
        if (!skills || !skills.length) {
            return '<div class="osrs-empty"><p class="osrs-empty__message">No skill data</p></div>';
        }

        // Build lookup by normalized name
        const lookup = {};
        for (const skill of skills) {
            if (skill && skill.name) {
                lookup[_normalizeName(skill.name)] = skill;
            }
        }

        let html = '<div class="osrs-skill-grid">';

        // Check for "overall" first
        const overall = lookup['overall'];
        if (overall) {
            html += _renderOneSkillCard('overall', overall, baseUrl);
        }

        // Then render in canonical order
        for (const skillName of SKILL_ORDER) {
            const skill = lookup[_normalizeName(skillName)];
            if (skill) {
                html += _renderOneSkillCard(skillName, skill, baseUrl);
            }
        }

        html += '</div>';
        return html;
    }

    /**
     * Render a single skill card.
     * @private
     */
    function _renderOneSkillCard(name, skill, baseUrl) {
        const level = skill.level != null ? skill.level : -1;
        const is99 = level >= 99;
        const modifier = is99 ? ' osrs-skill-card--99' : '';

        return `<div class="osrs-skill-card${modifier}">
            ${renderSkillIcon(name, baseUrl)}
            <div class="osrs-skill-card__info">
                <span class="osrs-skill-card__name">${escapeHtml(name)}</span>
                <span class="osrs-skill-card__level">${formatLevel(level)}</span>
                <span class="osrs-skill-card__xp">${formatXp(skill.xp)}</span>
            </div>
        </div>`;
    }

    /**
     * Render an activity/boss list HTML string.
     * Each row: icon + name + score + rank
     *
     * @param {Array} activities - Array of { name, score, rank }
     * @param {string} baseUrl - Backend base URL for icons
     * @returns {string} HTML string for the activity list
     */
    function renderActivityList(activities, baseUrl) {
        if (!activities || !activities.length) {
            return '<div class="osrs-empty"><p class="osrs-empty__message">No activity data</p></div>';
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
            html += `<div class="osrs-activity-row">
                ${renderGameIcon(activity.name, baseUrl)}
                <span class="osrs-activity-row__name">${escapeHtml(activity.name)}</span>
                <span class="osrs-activity-row__score">${score}</span>
                <span class="osrs-activity-row__rank">${rank}</span>
            </div>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Show an offline banner inside a container element.
     * @param {HTMLElement} container - The DOM element to insert the banner into
     */
    function showOfflineBanner(container) {
        if (!container) return;
        // Remove existing banner first
        hideOfflineBanner(container);

        const banner = document.createElement('div');
        banner.className = 'osrs-offline-banner';
        banner.setAttribute('data-offline-banner', 'true');
        banner.innerHTML = `
            <span class="osrs-offline-banner__icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M10 6v4m0 4h.01M3 10a7 7 0 1114 0 7 7 0 01-14 0z"
                          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </span>
            <span class="osrs-offline-banner__text">
                <strong>Backend Offline</strong> -- The OSRS backend is not responding.
                Start it from the Control Center or check the connection settings.
            </span>`;
        container.prepend(banner);
    }

    /**
     * Hide/remove the offline banner from a container.
     * @param {HTMLElement} container - The DOM element to remove the banner from
     */
    function hideOfflineBanner(container) {
        if (!container) return;
        const existing = container.querySelector('[data-offline-banner]');
        if (existing) existing.remove();
    }

    /**
     * Get the backend base URL from localStorage or default.
     * @returns {string}
     */
    function getBackendBaseUrl() {
        try {
            return localStorage.getItem(BACKEND_BASE_URL_KEY) || DEFAULT_BACKEND_URL;
        } catch {
            return DEFAULT_BACKEND_URL;
        }
    }

    /**
     * Register a callback for the councilSwitched event.
     * Called when the user switches to a different council in the nav.
     * @param {Function} callback - Event handler
     */
    function listenCouncilSwitch(callback) {
        window.addEventListener('councilSwitched', callback);
    }

    // =========================================================================
    // CLIPBOARD
    // =========================================================================

    /**
     * Fetch a proxy path as plain text.
     * @param {string} path - Path after /api/osrs (e.g. '/snapshots/{id}/raw')
     * @returns {Promise<string>} Response text
     */
    async function fetchText(path) {
        const url = API_PREFIX + path;
        const response = await fetch(url, {
            headers: {
                'Accept': 'text/plain',
                ..._councilHeaders()
            }
        });
        if (!response.ok) {
            throw { status: response.status, detail: response.statusText };
        }
        return response.text();
    }

    /**
     * Copy text to clipboard with Clipboard API fallback.
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} true on success
     */
    async function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch { /* fall through to fallback */ }
        }
        // execCommand fallback for older browsers / non-HTTPS
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            return true;
        } finally {
            document.body.removeChild(textarea);
        }
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    return {
        // Configuration
        API_PREFIX,
        SKILL_ICON_MAP,
        SKILL_ORDER,
        SNAPSHOT_MODES,

        // HTTP helpers
        fetchJson,
        postJson,
        deleteJson,
        fetchText,

        // Formatters
        formatXp,
        formatLevel,
        formatRank,
        formatDelta,
        formatTimestamp,
        formatTimeAgo,
        escapeHtml,

        // Icon rendering
        skillIconUrl,
        gameIconUrl,
        renderSkillIcon,
        renderGameIcon,

        // UI helpers
        renderSkillGrid,
        renderActivityList,
        showOfflineBanner,
        hideOfflineBanner,
        copyToClipboard,

        // Lifecycle
        getBackendBaseUrl,
        listenCouncilSwitch
    };
})();

window.OsrsCommon = OsrsCommon;
