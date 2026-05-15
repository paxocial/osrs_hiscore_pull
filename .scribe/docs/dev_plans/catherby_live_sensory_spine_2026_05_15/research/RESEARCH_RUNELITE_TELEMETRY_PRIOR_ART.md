---
id: catherby_live_sensory_spine_2026_05_15-research-runelite-telemetry-prior-art
title: "\U0001F52C Research Runelite Telemetry Prior Art \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: RESEARCH_RUNELITE_TELEMETRY_PRIOR_ART
doc_name: RESEARCH_RUNELITE_TELEMETRY_PRIOR_ART
category: engineering
status: ready
version: '0.1'
last_updated: 2026-05-15 06:54:38 UTC
maintained_by: agent-20260515-064709-030a9d6a
created_by: agent-20260515-064709-030a9d6a
owners: []
related_docs: []
tags: []
summary: ''
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 06:54:38 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 06:54:38 UTC
  last_edited_by: agent-20260515-064709-030a9d6a
  last_action: frontmatter_update
---

# 🔬 Research Runelite Telemetry Prior Art — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 06:50:26 UTC

> Prior-art research on RuneLite telemetry/sync plugins and RuneLite event/API patterns for Catherby live sensory spine

---
## Executive Summary
<!-- ID: executive_summary -->
This research maps the upstream RuneLite telemetry and sync ecosystem to the smallest safe first nerve for Catherby. The strongest precedent is not a broad event ledger; it is a narrow session-and-XP exporter that uses `GameStateChanged`, `GameTick`, and `StatChanged` to detect login, logout, hopping, and meaningful progress, then flushes a small payload once conditions justify it.

The biggest implementation risk is copying WikiSync's public username/profile trust model or jumping straight to bank/inventory/equipment exports. Wise Old Man and XpUpdater show that low-frequency, thresholded progress sync is the established pattern for external tracking. WikiSync shows how to do delta merging and manifest-driven polling, but its contract is too permissive for Catherby's authenticated ledger goal. Bank and container plugins are accepted RuneLite patterns, but they are local UI/state patterns, not the right first exporter boundary.

Blueprint should design around a session/xp first nerve, preserve RuneLite's async OkHttp and client-thread rules, and verify auth/rate/idempotency before widening into bank or chat telemetry.
## Research Scope
<!-- ID: research_scope -->
## Executive finding
Catherby should not invent a broad, always-on telemetry contract first. The strongest upstream precedent is a low-frequency session-plus-progress exporter: Wise Old Man and XpUpdater both gate updates on login/logout/hop and overall XP deltas, while WikiSync shows a manifest-driven delta ledger for state vectors. For Catherby, the first nerve should be a narrow exporter built around `GameStateChanged` + `GameTick` + `StatChanged` (logout/hop flush, login baseline, XP delta), not bank/inventory/equipment or chat spam.

## Repository / source list
- [wise-old-man/wiseoldman-runelite-plugin](https://github.com/wise-old-man/wiseoldman-runelite-plugin) @ `d826b91a5888f2c059487efc9ccf67f0aa7c9d5b` (cloned 2026-05-15).
- [runelite/plugin-hub](https://github.com/runelite/plugin-hub) @ `98401f6e61ca6aa3ed5c1e3838518dda4dc30f91` (cloned 2026-05-15). Manifest anchor: `plugins/wom-utils:1-4`, `plugins/wikisync:1-4`, `plugins/bank-value:1`.
- [weirdgloop/WikiSync](https://github.com/weirdgloop/WikiSync) @ `1ff4ea0653395b552844d658d3668815d82e0a79` (cloned 2026-05-15).
- [weirdgloop/wikisync-api](https://github.com/weirdgloop/wikisync-api) @ `11d0fbb89650e399002959eba226b249f3c5aeba` (cloned 2026-05-15).
- [spudjb/runelite-bank-value](https://github.com/spudjb/runelite-bank-value) @ `20fb572b20722c43304c5f596921290ba0808c90` (cloned 2026-05-15).
- [runelite/example-plugin](https://github.com/runelite/example-plugin) @ `5370caa0f5f6a5bba4fbb42931722ca535ad3fd5` (cloned 2026-05-15).
- [runelite/runelite](https://github.com/runelite/runelite) @ `686a9cd1e9ded3fbb6800cec1629159c41147488` (cloned 2026-05-15).

## High-level comparison
- Wise Old Man is a client-side sync helper, not a raw telemetry ledger. It pushes name changes, group member syncs, and player XP/account updates, but it does so through a narrow, session-driven contract.
- WikiSync is a broader state ledger that polls a server-provided manifest and sends a delta object containing varbits/varps/levels plus collection-log state. It is the best example of event-less batch sync from RuneLite, but it is also the least appropriate auth model for Catherby because it trusts username/profile rather than an API key.
- Bank Value and similar container plugins show that `ItemContainerChanged` on `BANK` is accepted in RuneLite, but this is a UI-only local pattern, not a reason to export high-volume bank state immediately.
- RuneLite examples show the canonical patterns for `StatChanged`, `GameStateChanged`, `ClientTick`, `ChatMessage`, and `SessionOpen`/`SessionClose`, plus async HTTP via OkHttp `enqueue` and debounce/cancel patterns for request spam control.
## Findings
<!-- ID: findings -->
## Findings

### Finding 1: session and XP gating is the safest first telemetry nerve
- Summary: The strongest upstream precedent is a narrow progress exporter driven by login/logout/hop plus XP change detection, not by full inventory or bank snapshots.
- Evidence: Wise Old Man uses `GameStateChanged`, `GameTick`, and `StatChanged` with a 10k XP threshold and logout/hop flush behavior; XpUpdater does the same for WOM, TempleOSRS, and CML with async HTTP and no blocking requests.
- Confidence: high.

### Finding 2: WikiSync proves delta merging, not a good auth model
- Summary: WikiSync is useful for understanding manifest-driven deltas and backoff, but it should not be copied as a security model because the server contract is username/profile based and effectively public.
- Evidence: `WikiSyncPlugin` builds `PlayerDataSubmission` from varbits, varps, levels, and collection-log bitsets; `wikisync-api` merges data by username/profile and exposes public result views.
- Confidence: high.

### Finding 3: bank and equipment access are accepted locally, but they are later-wave exports
- Summary: RuneLite plugins routinely read BANK, WORN, and INV containers, but the accepted pattern is local UI or state derivation, not immediate outbound telemetry.
- Evidence: `BankValuePlugin` repopulates a sidebar from `ItemContainerChanged` on BANK; `RegenMeterPlugin` and `ItemChargePlugin` do worn/inventory updates only when the relevant container changes.
- Confidence: high.

### Finding 4: async HTTP and client-thread handoff are the rule
- Summary: RuneLite plugins generally use OkHttp async callbacks and bounce UI updates back onto the client thread.
- Evidence: `GrandExchangeClient`, `XpUpdaterPlugin`, `DiscordPlugin`, and `WikiSearchChatboxTextInput` all use `enqueue(...)`; UI mutations are funneled through `clientThread.invokeLater(...)` where needed.
- Confidence: high.
## Technical Analysis
<!-- ID: technical_analysis -->
## System surface map

### 1) Wise Old Man RuneLite plugin
- Issue / requirement: learn how a live RuneLite sync plugin identifies the player, batches updates, and limits noise without inventing a new contract.
- Mapped surface: `wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/WomUtilsPlugin.java:286-375, 467-973`, `.../web/WomClient.java:116-556`, `.../WomUtilsConfig.java:129-176`, `.../beans/GroupMemberAddition.java:8-13`, `.../beans/WomPlayerUpdate.java:5-9`, `.../README.md:7-80`.
- Integration type: API/contract + tooling/runtime.
- Why this is the correct integration point: the plugin is explicitly a RuneLite-side sync helper that ships player names, group membership, and player accountHash updates to WOM; it is not a generic telemetry firehose.
- Confidence: high.
- Trace: UI -> `WomUtilsPlugin` and `WomUtilsConfig` -> state: `queue`, `previousSkillLevels`, `recentlyLoggedIn`, `playerName`, `accountHash`, `levelupThisSession` -> data source: `NameableNameChanged`, `StatChanged`, `GameStateChanged`, `GameTick`, clan settings, friend/ignore containers, local player -> validation: XP threshold of 10k, `GameState.LOGGED_IN` gating, duplicate-name-change suppression, verificationCode config, `response.code()==429` handling.

### 2) WikiSync RuneLite plugin and server contract
- Issue / requirement: understand manifest-driven sync, payload shape, and the server's trust model.
- Mapped surface: `WikiSync/src/main/java/com/andmcadams/wikisync/WikiSyncPlugin.java:95-520`, `.../PlayerDataSubmission.java:6-13`, `.../PlayerData.java:10-30`, `.../dps/DpsDataFetcher.java:41-149`, `.../SyncButtonManager.java:109-124`, `.../WikiSyncConfig.java:37-50`, `wikisync-api/src/runelite/router.ts:16-109`, `.../service.ts:6-103`, `.../constants.ts:12-27`, `.../runescape/router.ts:14-68`.
- Integration type: persistence + API/contract + tooling/runtime.
- Why this is the correct integration point: WikiSync is the clearest example of a RuneLite plugin that maintains a client-side delta cache, sends a structured submission object, and relies on a server-provided manifest to decide which state vectors matter.
- Confidence: high.
- Trace: UI -> `WikiSyncPlugin`, `SyncButtonManager`, `DpsDataFetcher` -> state: `playerDataMap`, `cyclesSinceSuccessfulCall`, `clogItemsBitSet`, `clogItemsCount`, `collectionLogItemIdsFromCache`, `webSocketStarted` -> data source: `GameStateChanged`, `ScriptPreFired`, `GameTick`, manifest endpoint, local player, `client.getVarbitValue`, `client.getVarpValue`, `client.getRealSkillLevel`, collection-log cache -> validation: logged-in only, manifest required, profile enum check on server, collection-log length cap on server, quadratic backoff, timeout of 3 seconds, only changed deltas are submitted.

### 3) Bank value and bank/container access patterns
- Issue / requirement: discover what container access is normal in RuneLite and what is too heavy for a first exporter.
- Mapped surface: `runelite-bank-value/src/main/java/spudjb/bankvalue/BankValuePlugin.java:41-87`, `runelite-client/src/main/java/net/runelite/client/plugins/regenmeter/RegenMeterPlugin.java:108-190`, `runelite-client/src/main/java/net/runelite/client/plugins/itemcharges/ItemChargePlugin.java:466-520`, `runelite-client/src/main/java/net/runelite/client/plugins/runecraft/RunecraftPlugin.java:163-173`, `runelite-client/src/main/java/net/runelite/client/plugins/wintertodt/WintertodtPlugin.java:445-445`.
- Integration type: state management + UI composition.
- Why this is the correct integration point: accepted container patterns are local and event-driven. They read `InventoryID.BANK`, `InventoryID.WORN`, or `InventoryID.INV` via `ItemContainerChanged`, then update UI/infobox state on the client thread.
- Confidence: high.
- Trace: UI -> plugin panel or overlay -> state: cached item list, worn-equipment booleans, charge counters -> data source: `ItemContainerChanged` on bank/worn/inventory containers, `client.getItemContainer(...)`, `client.getItemDefinition(...)`, item manager price lookup -> validation: container-id filter, canonicalize item filter, null checks, Swing thread handoff, no network side effect.

### 4) RuneLite example and core patterns for event subscriptions and HTTP
- Issue / requirement: confirm canonical RuneLite patterns for event wiring, session/login/logout, chat, async HTTP, and request spam control.
- Mapped surface: `runelite/example-plugin/src/main/java/com/example/ExamplePlugin.java:27-46`, `runelite-client/src/main/java/net/runelite/client/plugins/xpdrop/XpDropPlugin.java:120-290`, `.../playerindicators/PlayerIndicatorsPlugin.java:181-226`, `.../account/AccountPlugin.java:75-148`, `.../grandexchange/GrandExchangePlugin.java:329-420`, `.../grandexchange/GrandExchangeClient.java:65-101`, `.../xpupdater/XpUpdaterPlugin.java:94-245`, `.../discord/DiscordPlugin.java:144-258`, `.../wiki/WikiSearchChatboxTextInput.java:87-166`, `.../wiki/WikiPlugin.java:162-280`.
- Integration type: tooling/runtime + API/contract.
- Why this is the correct integration point: RuneLite itself uses `StatChanged`, `GameTick`, `ClientTick`, `ChatMessage`, `GameStateChanged`, `SessionOpen`, and `SessionClose` as ordinary extension points, and it sends HTTP asynchronously with OkHttp callbacks rather than blocking the client.
- Confidence: high.
- Trace: UI -> plugin or input listener -> state: login flags, previous skill XP, session UUID, menu-entry decorations -> data source: `GameStateChanged`, `StatChanged`, `ClientTick`, `SessionOpen`, `SessionClose`, text input changes, `OkHttpClient.newCall(...).enqueue(...)` -> validation: login/logout gating, XP delta checks, menu-open checks, debounce/cancel before search, client-thread handoff for UI mutations, auth headers or config gate where applicable.

## Payload and schema observations

### Wise Old Man
- `NameChangeEntry` is just `{ oldName, newName }`.
- `GroupMemberAddition` is `{ verificationCode, members, roleOrders }`.
- `WomPlayerUpdate` is `{ accountHash }`.
- The client posts name changes to `POST /names/bulk`, group syncs to `PUT /groups/:id`, and player progress to `POST /players/:username`.
- Identification is session-ish rather than key-based: the plugin uses `verificationCode` from config plus `accountHash`, and the repo warning in plugin-hub says the plugin submits names to WOM.

### WikiSync
- `PlayerDataSubmission` is `{ username, profile, data }`.
- `PlayerData` / `data` contains `varb`, `varp`, `level`, `collectionLog?`, `collectionLogSlots?`, and `collectionLogItemCount`.
- The server merges deltas into persisted JSON rows keyed by lowercase username and profile.
- The publishable response is not a raw event stream; it is a denormalized view derived from server transforms such as quests, diaries, levels, music, combat achievements, league tasks, bingo tasks, collection log, and sailing.

### RuneLite examples
- `GrandExchangeTrade` carries a machine/session identity via RuneLite auth headers and a `login` burst flag.
- `XpUpdaterPlugin` sends only `accountHash` plus username in a form body, gated by world type and a 10k XP threshold.
- `WikiSearchChatboxTextInput` is a good debounce example: cancel the previous future before issuing the next async search.

## Auth, network, and batching observations

### Wise Old Man
- API base: `https://api.wiseoldman.net/v2` or `league` for seasonal worlds.
- Network pattern: OkHttp async calls with 30 second connect/read/write timeouts.
- Rate control: no client-side retry loop; the plugin relies on event gating, a 10k XP threshold, `sendUpdate()` every 30 minutes, and explicit 429 handling.
- User identification: RSN, group id, verification code, and accountHash are the important identifiers.
- Anti-spam signal: name changes are queued and filtered against current friend/ignore state before bulk submission.

### WikiSync
- API base: `https://sync.runescape.wiki/runelite`.
- Network pattern: async POST/GET with a 3 second timeout for submit calls, plus a 20 minute manifest refresh and a 10 second submit cadence.
- Rate control: quadratic backoff via perfect-square gating on `cyclesSinceSuccessfulCall`, plus delta merging so unchanged payloads are not resent.
- Identification: username + profile; no plugin API key.
- Anti-spam signal: the client only submits when `subtract(new, old)` leaves actual changes.

### RuneLite core
- Session identity patterns exist in `AccountPlugin` (`SessionOpen` / `SessionClose`) and `GrandExchangeClient` (`RUNELITE_AUTH`, `RUNELITE_MACHINEID`).
- Async HTTP is normal: `OkHttpClient.newCall(request).enqueue(...)` is used across plugin code, not synchronous blocking calls.

## Bank/container observations
- The accepted client pattern for bank/inventory/equipment access is local state derivation from `ItemContainerChanged` and `client.getItemContainer(...)`, not pushing the full container every tick.
- `BankValuePlugin` only reacts when the changed container is the bank and then repopulates a UI panel.
- `RegenMeterPlugin` and `ItemChargePlugin` show worn/inventory access for equipment state and charge tracking.
- `RunecraftPlugin` and `WintertodtPlugin` show inventory/container changes tied to gameplay state, but still local-first and event-gated.
- For Catherby, bank/container exporting should be a later wave, after a much narrower session/xp nerve proves the pipeline.

## Safe first RuneLite exporter recommendation
- First exporter family: `session` plus `xp` only.
- First event set: `GameStateChanged` for `LOGGED_IN`, `LOGIN_SCREEN`, and `HOPPING`; `GameTick` for baseline capture on login; `StatChanged` for dirty-state marking; logout/hop flush when XP changed.
- Reasoning: this is the narrowest contract with strong precedent in `XpUpdaterPlugin` and `WomUtilsPlugin`, minimal privacy exposure, low payload cardinality, and obvious dedupe/delta rules.
- What not to start with: bank, inventory, equipment, chat, or collection-log exports. Those are all valid RuneLite patterns, but they are higher-volume and more privacy-sensitive than the first nerve should be.

## Risks and open questions for Blueprint
- Unknown: exact Wise Old Man server-side rate limits, replay policy, and whether any hidden auth or anti-abuse headers exist beyond the client code we inspected.
- Unknown: WikiSync production auth story is effectively absent in the client contract; if there is a separate service-side trust layer, it was not visible in the code we reviewed.
- Unknown: the right Catherby payload boundaries for bank and chat exports are not yet justified by upstream examples; they should stay out of wave 1.
- Risk: copying WikiSync's public username/profile trust model would create a non-authenticated export path that is too permissive for Catherby.
- Risk: copying bank-value style item-container polling into the first nerve would inflate payload volume without adding enough signal.
- Risk: treating `ChatMessage` as telemetry rather than notification would likely create spam and filtering problems.
## Recommendations
<!-- ID: recommendations -->
## Recommendations

### Immediate next steps
- Define the first Catherby exporter as a `session` plus `xp` contract built around `GameStateChanged`, `GameTick`, and `StatChanged`.
- Preserve RuneLite's async shape: use OkHttp callbacks, and route all UI mutations back onto the client thread.
- Add explicit auth/rate/idempotency decisions before any bank, inventory, or chat payloads are allowed to leave the client.
- Treat WikiSync as a delta-merging reference only; do not inherit its username/profile trust model.
- Keep bank and equipment telemetry out of the first wave until the narrow exporter is proven and can be rate-limited cleanly.

### Longer-term opportunities
- Once the first nerve is stable, add a second-wave container exporter for bank/equipment/inventory with strict payload caps and quarantine rules.
- Reuse the manifest/delta idea from WikiSync for feature negotiation, but only behind Catherby's authenticated contract.
- Reuse the session identity patterns from RuneLite core, especially `SessionOpen`/`SessionClose` and auth-machine headers, for any future hosted sync surfaces.
## Appendix
<!-- ID: appendix -->
## Appendix

## Relevant files

### Local Catherby surfaces
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md`
- `README.md`
- `api/dependencies.py:24-83`
- `api/endpoints/plugin.py:1-260`
- `api/schemas/plugin.py:1-260`
- `api/endpoints/runelite.py:1-220`
- `api/endpoints/snapshots.py:1-240`
- `docs/dev_plans/PLUGIN_API_SCHEMA.md`
- `docs/dev_plans/RUNELITE_PLUGIN_NEXT_STEPS.md`
- `database/models.py`
- `database/connection.py`

### Upstream prior-art surfaces
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/WomUtilsPlugin.java:286-375, 467-973`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/web/WomClient.java:116-556`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/WomUtilsConfig.java:1-260`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/beans/GroupMemberAddition.java:1-13`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/beans/WomPlayerUpdate.java:1-9`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/beans/NameChangeEntry.java:1-10`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/src/main/java/net/wiseoldman/events/WomRequestFailed.java:1-10`
- `/tmp/catherby_prior_art/wiseoldman-runelite-plugin/README.md`
- `/tmp/catherby_prior_art/WikiSync/src/main/java/com/andmcadams/wikisync/WikiSyncPlugin.java:95-520`
- `/tmp/catherby_prior_art/WikiSync/src/main/java/com/andmcadams/wikisync/PlayerDataSubmission.java:1-13`
- `/tmp/catherby_prior_art/WikiSync/src/main/java/com/andmcadams/wikisync/PlayerData.java:1-30`
- `/tmp/catherby_prior_art/WikiSync/src/main/java/com/andmcadams/wikisync/dps/DpsDataFetcher.java:41-149`
- `/tmp/catherby_prior_art/WikiSync/src/main/java/com/andmcadams/wikisync/SyncButtonManager.java:109-124`
- `/tmp/catherby_prior_art/WikiSync/src/main/java/com/andmcadams/wikisync/WikiSyncConfig.java:1-50`
- `/tmp/catherby_prior_art/WikiSync/README.md`
- `/tmp/catherby_prior_art/wikisync-api/src/runelite/router.ts:16-109`
- `/tmp/catherby_prior_art/wikisync-api/src/runelite/service.ts:6-103`
- `/tmp/catherby_prior_art/wikisync-api/src/runelite/constants.ts:12-27`
- `/tmp/catherby_prior_art/wikisync-api/src/runescape/router.ts:14-68`
- `/tmp/catherby_prior_art/runelite-bank-value/src/main/java/spudjb/bankvalue/BankValuePlugin.java:41-87`
- `/tmp/catherby_prior_art/runelite-bank-value/README.md`
- `/tmp/catherby_prior_art/runelite/example-plugin/src/main/java/com/example/ExamplePlugin.java:27-46`
- `/tmp/catherby_prior_art/runelite/example-plugin/src/main/java/com/example/ExampleConfig.java:1-18`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/xpdrop/XpDropPlugin.java:120-290`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/playerindicators/PlayerIndicatorsPlugin.java:181-226`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/account/AccountPlugin.java:75-148`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/grandexchange/GrandExchangePlugin.java:329-420`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/grandexchange/GrandExchangeClient.java:65-101`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/xpupdater/XpUpdaterPlugin.java:94-245`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/discord/DiscordPlugin.java:144-258`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/wiki/WikiSearchChatboxTextInput.java:87-166`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/wiki/WikiPlugin.java:162-280`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/regenmeter/RegenMeterPlugin.java:108-190`
- `/tmp/catherby_prior_art/runelite/runelite-client/src/main/java/net/runelite/client/plugins/itemcharges/ItemChargePlugin.java:466-520`

## Existing verification surfaces
- Local repo tests present: `api/test_accounts.py`, `database/simple_test.py`, `database/simple_migration_test.py`.
- Upstream plugin tests present: `wiseoldman-runelite-plugin/src/test/java/net/wiseoldman/WomUtilsPluginTest.java`, `WikiSync/src/test/java/com/andmcadams/wikisync/WikiSyncPluginTest.java`, `runelite-bank-value/src/test/java/spudjb/bankvalue/BankValuePluginTest.java`.
- Candidate commands for Blueprint or later validation: `pytest api/test_accounts.py`, `pytest database/simple_test.py`, and the appropriate Gradle test task in the upstream RuneLite clones.

## Handoff
Blueprint should design around a narrow authenticated session/xp nerve, preserve RuneLite's async/client-thread conventions, and verify auth, rate limiting, idempotency, and payload caps before broadening into container, inventory, equipment, or chat telemetry.

## Unknowns
- Exact Wise Old Man server-side abuse and replay policy remain unknown from client code alone.
- WikiSync's production auth story is effectively absent in the client contract and should be treated as unsafe for Catherby without additional evidence.
- The right first bank/container export contract for Catherby is still unknown and should remain out of wave 1.
