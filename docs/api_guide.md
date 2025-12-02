# 📊 OSRS Highscores & Runelite Integration Knowledge Pack

## 📑 Table of Contents

1. [OSRS Highscore API](#osrs-highscore-api)
   - [Overview](#overview)
   - [Game Modes and Endpoints](#game-modes-and-endpoints)
   - [Additional API Functions](#additional-api-functions)
   - [Limitations and Notes](#limitations-and-notes)
2. [OSRS JSON Hiscores Library](#osrs-json-hiscores-library)
   - [Purpose](#purpose)
   - [Key Functions](#key-functions)
   - [Constants and Enumerations](#constants-and-enumerations)
   - [Data Structures](#data-structures)
3. [RuneLite Plugin Architecture](#runelite-plugin-architecture)
   - [Overview](#overview-1)
   - [Example](#example)
   - [Event Types](#event-types)
4. [Integration Strategy](#integration-strategy)
5. [References](#references)

---

## 🎮 OSRS Highscore API
**EXAMPLE REPO THAT ACCOMPLISHES SIMILAR FEAT:** https://github.com/maxswa/osrs-json-hiscores
### Overview

OSRS provides a "hiscores lite" API accessible via `https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player=<name>` for main accounts. There are equivalent endpoints for ironman and hardcore ironman game modes (e.g. `https://secure.runescape.com/m=hiscore_ironman/index_lite.ws?player=<name>`). These endpoints return the player's rank, level and experience or score for each skill and activity in **CSV format**.

A **JSON endpoint** is also available (`index_lite.json?player=`). The [OSRS JSON hiscores library](https://github.com/maxswa/osrs-json-hiscores) uses constants (`JSON_STATS_URL`) to build these URLs.

### Game Modes and Endpoints

| Game Mode | Endpoint Path |
|-----------|--------------|
| Regular (main) | `https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player=<name>` |
| Ironman | `https://secure.runescape.com/m=hiscore_ironman/index_lite.ws?player=<name>` |
| Hardcore Ironman | `https://secure.runescape.com/m=hiscore_hardcore_ironman/index_lite.ws?player=<name>` |
| Ultimate Ironman | `https://secure.runescape.com/m=hiscore_ultimate/index_lite.ws?player=<name>` |
| Seasonal/Tournament | Additional modes with distinct base URLs in `GAMEMODE_URL` constants |

Each `index_lite` endpoint returns lines for all **25 skills** followed by **activities** (clues, bounty hunter modes, bosses and miscellaneous activities), with each line containing either `rank,level,xp` or `rank,score` values.

OSRS also exposes web-based hiscore pages which can be scraped to retrieve leaderboards. `getSkillPageURL` builds skill leaderboard URLs (`...overall.ws?table=<skill_index>&page=<n>`) and `getActivityPageURL` builds activity/boss pages (`...overall.ws?category_type=1&table=<activity_index>&page=<n>`).

### Additional API Functions

- **Seasonal events** – `getRankings` and `getHiscoreDetails` endpoints return seasonal rankings and meta-information about temporary events.
- **Clan hiscores** – `clanRanking.json` returns top clans and `members_lite.ws` returns lists of clan members and their stats.

### Limitations and Notes

- **CORS restrictions** – Jagex does not include `Access-Control-Allow-Origin` headers in their responses, so direct browser calls are blocked by CORS. Requests should be made from a server or through a proxy.
- The API may return **404 for missing players**; the library wraps these responses in a `PlayerNotFoundError`.
- **Rate limits are not documented**; consuming applications should implement backoff and avoid excessive requests.

---

## 🔧 OSRS JSON Hiscores Library

**Repository:** [https://github.com/maxswa/osrs-json-hiscores](https://github.com/maxswa/osrs-json-hiscores)

### Purpose

The `osrs-json-hiscores` library converts the official hiscore CSV/JSON into a structured object and infers game modes. It exposes functions such as `getStats`, `getStatsByGamemode`, `getSkillPage` and `getActivityPage`.

### Key Functions

- **`getOfficialStats(rsn, mode)`** – Builds the correct URL via `getStatsURL` and requests JSON data. If the underlying HTTP request returns 404 it throws `PlayerNotFoundError`.

- **`parseJsonStats(json)`** – Converts the raw JSON to a `Stats` object by iterating over defined skills (`SKILLS`) and activities (`BH_MODES`, `CLUES`, `BOSSES`) to build nested objects for skills, league points, bounty hunter, clues and bosses.

- **`getStats(rsn, options)`** – Fetches the player's main stats and optionally additional modes (ironman, hardcore, ultimate). It detects if the player has died or de-ironed by comparing total XP across modes. Flags (`dead`, `deulted`, `deironed`) are set accordingly and the resulting `Player` object includes a `main`, `ironman`, `hardcore` and/or `ultimate` section.

- **`getStatsByGamemode(rsn, mode)`** – Returns the `Stats` object for a single mode without inferring anything.

- **`getSkillPage(skill, mode, page)`** – Scrapes the official hiscore webpage to return an array of 25 players with `name`, `rank`, `level`, `xp` and `dead` fields.

- **`getActivityPage(activity, mode, page)`** – Similar to `getSkillPage` but for clue scroll tiers, minigames and bosses.

### Constants and Enumerations

- **Base URLs** – `BASE_URL = https://secure.runescape.com/m=hiscore_oldschool` and `STATS_URL = 'index_lite.ws?player='`, `JSON_STATS_URL = 'index_lite.json?player='`.

- **`GAMEMODE_URL`** – Maps gamemodes (main, ironman, hardcore, ultimate, deadman, seasonal, tournament, skiller variants) to their respective base URLs.

- **Lists** – `SKILLS` (25 skills), `CLUES` (clue tiers), `BH_MODES`, `BOSSES` and aggregated `ACTIVITIES` define the order of entries returned by the API.

- **Formatted names** – `FORMATTED_SKILL_NAMES`, `FORMATTED_BOSS_NAMES`, etc., translate internal keys into human-readable names.

### Data Structures

#### Stats Object

Contains nested objects:

- **`skills`**: maps each skill to a structure `{rank, level, xp}`.
- **Activity objects** (`leaguePoints`, `deadmanPoints`, `bountyHunter`, `lastManStanding`, `pvpArena`, `soulWarsZeal`, `riftsClosed`, `colosseumGlory`, `collectionsLogged`) each hold `{rank, score}`.
- **`clues`**: counts for each clue tier (all, beginner, easy, etc.).
- **`bosses`**: kill counts for each boss defined in `BOSSES`.

#### Player Object

Contains:

- **`name`**: formatted or provided RSN.
- **`mode`**: determined gamemode (e.g. main, ironman, hardcore).
- **Flags**: `dead`, `deulted`, `deironed` indicating if the player died as a hardcore ironman or removed an ironman/ultimate status.
- **Sub-objects**: `main`, `ironman`, `hardcore`, `ultimate` representing stats for each mode.

---

## ⚙️ RuneLite Plugin Architecture

### Overview

RuneLite is a Java client that supports extending functionality via plugins. A plugin must:

- Reside in its own package and extend `net.runelite.client.plugins.Plugin`.
- Be annotated with `@PluginDescriptor`, providing metadata such as the plugin's name.
- Use dependency injection (`@Inject`) to access services like the `Client` and configuration classes.
- Override `startUp()` and `shutDown()` methods to initialize resources when the plugin is activated and clean up when deactivated.
- Use the **EventBus**: methods annotated with `@Subscribe` listen for RuneLite events (e.g. `GameStateChanged`, `ItemContainerChanged`) and run automatically when those events occur.
- Define configuration interfaces annotated with `@ConfigGroup` and `@ConfigItem` to expose settings in the client UI.

### Example

A simple plugin class from the Sly Automation guide:

```java
@PluginDescriptor(name = "Awesome")
public class AwesomePlugin extends Plugin
{
    @Inject private Client client;
    @Inject private AwesomeConfig config;

    @Override
    protected void startUp() throws Exception
    {
        log.info("The Awesomeness has started!");
    }

    @Override
    protected void shutDown() throws Exception
    {
        log.info("Awesomeness has stopped!");
    }

    @Subscribe
    public void onGameStateChanged(GameStateChanged gameStateChanged)
    {
        if (gameStateChanged.getGameState() == GameState.LOGGED_IN)
        {
            client.addChatMessage(ChatMessageType.GAMEMESSAGE, "", "I think " +
                config.greeting(), null);
        }
    }
}
```

This example shows the typical use of `@Inject`, lifecycle methods and `@Subscribe` to respond to events.

### Event Types

RuneLite's API exposes many event classes under `net.runelite.api.events`. Some notable events for data capture include:

- **`StatChanged`** – Fired when a player's skill experience changes; useful for tracking XP gains in real time.
- **`ItemContainerChanged`** – Triggered when items in a container (inventory, equipment, bank) change.
- **`GameTick` / `ClientTick`** – Periodic ticks that can be used to poll data.
- **`ChatMessage`** – Captures in-game chat messages.

Plugins can subscribe to these events and write the data to disk or send it to an external API. The PlayerScraper plugin demonstrates adding a JSON library to RuneLite's build and writing player equipment data to JSON.

---

## 🚀 Integration Strategy

To develop a snapshot agent that captures comprehensive OSRS data:

### 1. Server-Side Snapshot

Use the [osrs-json-hiscores library](https://github.com/maxswa/osrs-json-hiscores) (or re-implement the API calls in Python) to fetch the player's hiscores via the JSON endpoint. Normalize the data into structured objects using the schema described above. Schedule periodic snapshots and save them with timestamps.

### 2. Supplemental Data via RuneLite (future expansion)

Develop a RuneLite plugin that subscribes to events such as `StatChanged`, `ItemContainerChanged`, `PlayerDeath` and `GameTick` to collect data not exposed by the hiscore API (e.g. live inventory, equipment, XP gains, chat logs). The plugin can serialize this data to JSON and forward it to your agent.

### 3. Rate-Limiting and User-Agent

Include a custom `User-Agent` header when making HTTP requests to the hiscore API to avoid Jagex's DDoS protection. Respect rate limits and avoid rapid repeated requests; the library fetches up to five endpoints per player call.

### 4. Game Mode Detection

Replicate the library's logic to detect whether a player has died or removed their iron status by comparing total XP across modes.

### 5. Data Storage

Use deterministic naming such as `<username>/<YYYYMMDD_HHMMSS>.json` and include retrieval metadata (timestamp, confidence scores) to assist later ingestion. Align storage with your `AGENTS.md` guidelines.

### 6. Configuration and Security

Keep any API keys or user credentials in configuration files or environment variables. Ensure that your RuneLite plugin and agent comply with Jagex's terms of service and handle data responsibly.

---

## 📚 References

1. [Application programming interface | RuneScape Wiki | Fandom](https://runescape.fandom.com/wiki/Application_programming_interface)
2. [osrs-json-hiscores GitHub Repository](https://github.com/maxswa/osrs-json-hiscores)
3. [helpers.ts](https://github.com/maxswa/osrs-json-hiscores/blob/main/src/utils/helpers.ts)
4. [constants.ts](https://github.com/maxswa/osrs-json-hiscores/blob/main/src/utils/constants.ts)
5. [README.md](https://github.com/maxswa/osrs-json-hiscores/blob/main/README.md)
6. [hiscores.ts](https://github.com/maxswa/osrs-json-hiscores/blob/main/src/hiscores.ts)
7. [Creating your first Runelite Plugin - Sly Automation](https://www.slyautomation.com/blog/creating-your-first-runelite-plugin/)
8. [OSRSBox | Blog | Watercooler: PlayerScraper - A RuneLite Plugin to Dump Player Equipment](https://www.osrsbox.com/blog/2018/12/24/watercooler-analysis-of-bank-standing-equipment/)
9. [net.runelite.api.events (RuneLite API 1.11.22 API)](https://static.runelite.net/runelite-api/apidocs/net/runelite/api/events/package-summary.html)

---

**This knowledge pack provides the key technical details you need to build a hiscore snapshot agent and plan future RuneLite integration. Use the OSRS hiscore API for high-level statistics and rely on RuneLite plugins for richer, real-time data capture when needed.**
