"""Tests for plugin API Pydantic schemas.

Validates all 12 plugin payload models including validation rules,
field requirements, and error handling.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from api.schemas.plugin import (
    PluginPayloadBase,
    SessionEvent,
    SessionEventType,
    XpSnapshot,
    CollectionLogEntry,
    QuestStatus,
    QuestState,
    DiaryProgress,
    CombatAchievementProgress,
    EquipmentState,
    LootDrop,
    LootSourceType,
    ActivityUpdate,
    BankSnapshot,
    BatchPayload,
    StatusResponse,
)


# Test data constants
VALID_RSN = "TestPlayer"
VALID_WORLD = 301
VALID_PLUGIN_VERSION = "1.0.0"
VALID_TIMESTAMP = datetime.utcnow()

ALL_SKILLS = {
    "attack": 1000, "defence": 2000, "strength": 3000, "hitpoints": 4000,
    "ranged": 5000, "prayer": 6000, "magic": 7000, "cooking": 8000,
    "woodcutting": 9000, "fletching": 10000, "fishing": 11000, "firemaking": 12000,
    "crafting": 13000, "smithing": 14000, "mining": 15000, "herblore": 16000,
    "agility": 17000, "thieving": 18000, "slayer": 19000, "farming": 20000,
    "runecraft": 21000, "hunter": 22000, "construction": 23000
}


class TestPluginPayloadBase:
    """Test base model validation."""

    def test_valid_base_payload(self):
        """Valid base payload should pass validation."""
        payload = PluginPayloadBase(
            rsn=VALID_RSN,
            world=VALID_WORLD,
            plugin_version=VALID_PLUGIN_VERSION
        )
        assert payload.rsn == VALID_RSN
        assert payload.world == VALID_WORLD
        assert payload.plugin_version == VALID_PLUGIN_VERSION
        assert isinstance(payload.timestamp, datetime)

    def test_rsn_too_short(self):
        """RSN with 0 characters should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PluginPayloadBase(
                rsn="",
                plugin_version=VALID_PLUGIN_VERSION
            )
        assert "rsn" in str(exc_info.value)

    def test_rsn_too_long(self):
        """RSN longer than 12 characters should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PluginPayloadBase(
                rsn="ThisNameIsTooLong",
                plugin_version=VALID_PLUGIN_VERSION
            )
        assert "rsn" in str(exc_info.value)

    def test_world_below_range(self):
        """World number below 300 should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PluginPayloadBase(
                rsn=VALID_RSN,
                world=299,
                plugin_version=VALID_PLUGIN_VERSION
            )
        assert "world" in str(exc_info.value)

    def test_world_above_range(self):
        """World number above 600 should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PluginPayloadBase(
                rsn=VALID_RSN,
                world=601,
                plugin_version=VALID_PLUGIN_VERSION
            )
        assert "world" in str(exc_info.value)

    def test_invalid_plugin_version_format(self):
        """Non-semver plugin version should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PluginPayloadBase(
                rsn=VALID_RSN,
                plugin_version="v1.0"
            )
        assert "plugin_version" in str(exc_info.value)


class TestSessionEvent:
    """Test SessionEvent model."""

    def test_valid_login_event(self):
        """Valid login event should pass."""
        event = SessionEvent(
            rsn=VALID_RSN,
            world=VALID_WORLD,
            plugin_version=VALID_PLUGIN_VERSION,
            session_id="session-123",
            event=SessionEventType.LOGIN
        )
        assert event.session_id == "session-123"
        assert event.event == SessionEventType.LOGIN

    def test_valid_logout_event_with_duration(self):
        """Valid logout event with duration should pass."""
        event = SessionEvent(
            rsn=VALID_RSN,
            world=VALID_WORLD,
            plugin_version=VALID_PLUGIN_VERSION,
            session_id="session-123",
            event=SessionEventType.LOGOUT,
            duration_seconds=3600
        )
        assert event.duration_seconds == 3600

    def test_session_event_requires_world(self):
        """Session event without world should fail."""
        with pytest.raises(ValidationError) as exc_info:
            SessionEvent(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                session_id="session-123",
                event=SessionEventType.LOGIN
            )
        assert "world" in str(exc_info.value)

    def test_negative_duration_fails(self):
        """Negative duration should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            SessionEvent(
                rsn=VALID_RSN,
                world=VALID_WORLD,
                plugin_version=VALID_PLUGIN_VERSION,
                session_id="session-123",
                event=SessionEventType.LOGOUT,
                duration_seconds=-100
            )
        assert "duration_seconds" in str(exc_info.value)


class TestXpSnapshot:
    """Test XpSnapshot model."""

    def test_valid_xp_snapshot(self):
        """Valid XP snapshot with all skills should pass."""
        snapshot = XpSnapshot(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            skills=ALL_SKILLS
        )
        assert snapshot.skills["attack"] == 1000
        assert len(snapshot.skills) == 23

    def test_missing_skill_fails(self):
        """XP snapshot missing a skill should fail."""
        incomplete_skills = ALL_SKILLS.copy()
        del incomplete_skills["attack"]

        with pytest.raises(ValidationError) as exc_info:
            XpSnapshot(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                skills=incomplete_skills
            )
        assert "Missing skill: attack" in str(exc_info.value)

    def test_negative_xp_fails(self):
        """Negative XP value should fail."""
        invalid_skills = ALL_SKILLS.copy()
        invalid_skills["attack"] = -100

        with pytest.raises(ValidationError) as exc_info:
            XpSnapshot(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                skills=invalid_skills
            )
        assert "Invalid XP for attack" in str(exc_info.value)


class TestCollectionLogEntry:
    """Test CollectionLogEntry model."""

    def test_valid_collection_log_entry(self):
        """Valid collection log entry should pass."""
        entry = CollectionLogEntry(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            item_id=1234,
            item_name="Dragon Warhammer",
            quantity=1,
            source="Lizardman Shaman",
            obtained_at=VALID_TIMESTAMP
        )
        assert entry.item_id == 1234
        assert entry.item_name == "Dragon Warhammer"

    def test_negative_item_id_fails(self):
        """Negative item ID should fail."""
        with pytest.raises(ValidationError) as exc_info:
            CollectionLogEntry(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                item_id=-1,
                item_name="Test Item",
                quantity=1,
                source="Test Source",
                obtained_at=VALID_TIMESTAMP
            )
        assert "item_id" in str(exc_info.value)

    def test_zero_quantity_fails(self):
        """Zero quantity should fail."""
        with pytest.raises(ValidationError) as exc_info:
            CollectionLogEntry(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                item_id=1234,
                item_name="Test Item",
                quantity=0,
                source="Test Source",
                obtained_at=VALID_TIMESTAMP
            )
        assert "quantity" in str(exc_info.value)


class TestQuestStatus:
    """Test QuestStatus model."""

    def test_valid_quest_complete(self):
        """Valid completed quest should pass."""
        quest = QuestStatus(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            quest_name="Dragon Slayer",
            state=QuestState.COMPLETE
        )
        assert quest.quest_name == "Dragon Slayer"
        assert quest.state == QuestState.COMPLETE

    def test_quest_in_progress(self):
        """Quest in progress state should pass."""
        quest = QuestStatus(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            quest_name="Recipe for Disaster",
            state=QuestState.IN_PROGRESS
        )
        assert quest.state == QuestState.IN_PROGRESS


class TestDiaryProgress:
    """Test DiaryProgress model."""

    def test_valid_diary_progress(self):
        """Valid diary progress should pass."""
        diary = DiaryProgress(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            region="Varrock",
            easy=True,
            medium=True,
            hard=False,
            elite=False
        )
        assert diary.region == "Varrock"
        assert diary.easy is True
        assert diary.medium is True
        assert diary.hard is False

    def test_diary_defaults_to_false(self):
        """Diary tiers should default to False."""
        diary = DiaryProgress(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            region="Lumbridge"
        )
        assert diary.easy is False
        assert diary.medium is False
        assert diary.hard is False
        assert diary.elite is False


class TestCombatAchievementProgress:
    """Test CombatAchievementProgress model."""

    def test_valid_combat_achievement_progress(self):
        """Valid combat achievement progress should pass."""
        progress = CombatAchievementProgress(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            tier_progress={"easy": 5, "medium": 3},
            completed_tasks=["Task 1", "Task 2"]
        )
        assert progress.tier_progress["easy"] == 5
        assert len(progress.completed_tasks) == 2

    def test_invalid_tier_name_fails(self):
        """Invalid tier name should fail."""
        with pytest.raises(ValidationError) as exc_info:
            CombatAchievementProgress(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                tier_progress={"invalid_tier": 5}
            )
        assert "Invalid tier: invalid_tier" in str(exc_info.value)

    def test_negative_tier_count_fails(self):
        """Negative tier count should fail."""
        with pytest.raises(ValidationError) as exc_info:
            CombatAchievementProgress(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                tier_progress={"easy": -1}
            )
        assert "Invalid count for easy" in str(exc_info.value)


class TestEquipmentState:
    """Test EquipmentState model."""

    def test_valid_equipment_state(self):
        """Valid equipment state should pass."""
        equipment = EquipmentState(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            equipment={"head": 1234, "body": 5678},
            inventory=[{"item_id": 1, "quantity": 1}]
        )
        assert equipment.equipment["head"] == 1234
        assert len(equipment.inventory) == 1

    def test_empty_equipment_valid(self):
        """Empty equipment/inventory should be valid."""
        equipment = EquipmentState(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION
        )
        assert equipment.equipment == {}
        assert equipment.inventory == []


class TestLootDrop:
    """Test LootDrop model."""

    def test_valid_loot_drop(self):
        """Valid loot drop should pass."""
        loot = LootDrop(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            item_id=1234,
            item_name="Dragon Bones",
            quantity=1,
            ge_value=2500,
            source="King Black Dragon",
            source_type=LootSourceType.BOSS
        )
        assert loot.item_name == "Dragon Bones"
        assert loot.source_type == LootSourceType.BOSS

    def test_loot_without_ge_value(self):
        """Loot drop without GE value should be valid."""
        loot = LootDrop(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            item_id=1234,
            item_name="Rare Item",
            quantity=1,
            source="Mystery Box",
            source_type=LootSourceType.CHEST
        )
        assert loot.ge_value is None


class TestActivityUpdate:
    """Test ActivityUpdate model."""

    def test_valid_activity_update(self):
        """Valid activity update should pass."""
        activity = ActivityUpdate(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            activity="Level Up",
            detail="Reached level 99 in Woodcutting"
        )
        assert activity.activity == "Level Up"
        assert activity.detail == "Reached level 99 in Woodcutting"

    def test_activity_without_detail(self):
        """Activity without detail should be valid."""
        activity = ActivityUpdate(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            activity="Login"
        )
        assert activity.detail is None


class TestBankSnapshot:
    """Test BankSnapshot model."""

    def test_valid_bank_snapshot(self):
        """Valid bank snapshot should pass."""
        bank = BankSnapshot(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            items=[
                {"item_id": 1, "quantity": 100},
                {"item_id": 2, "quantity": 50}
            ],
            total_value=1000000
        )
        assert len(bank.items) == 2
        assert bank.total_value == 1000000

    def test_bank_item_missing_fields_fails(self):
        """Bank item missing required fields should fail."""
        with pytest.raises(ValidationError) as exc_info:
            BankSnapshot(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                items=[{"item_id": 1}],  # Missing quantity
                total_value=1000
            )
        assert "must have item_id and quantity" in str(exc_info.value)

    def test_bank_item_invalid_quantity_fails(self):
        """Bank item with zero quantity should fail."""
        with pytest.raises(ValidationError) as exc_info:
            BankSnapshot(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                items=[{"item_id": 1, "quantity": 0}],
                total_value=1000
            )
        assert "quantity must be a positive integer" in str(exc_info.value)


class TestBatchPayload:
    """Test BatchPayload model."""

    def test_valid_batch_with_multiple_categories(self):
        """Valid batch with multiple categories should pass."""
        batch = BatchPayload(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION,
            xp_snapshots=[XpSnapshot(
                rsn=VALID_RSN,
                plugin_version=VALID_PLUGIN_VERSION,
                skills=ALL_SKILLS
            )],
            sessions=[SessionEvent(
                rsn=VALID_RSN,
                world=VALID_WORLD,
                plugin_version=VALID_PLUGIN_VERSION,
                session_id="batch-session",
                event=SessionEventType.LOGIN
            )]
        )
        assert len(batch.xp_snapshots) == 1
        assert len(batch.sessions) == 1

    def test_empty_batch_valid(self):
        """Batch with all categories None should be valid."""
        batch = BatchPayload(
            rsn=VALID_RSN,
            plugin_version=VALID_PLUGIN_VERSION
        )
        assert batch.sessions is None
        assert batch.xp_snapshots is None


class TestStatusResponse:
    """Test StatusResponse model."""

    def test_valid_authenticated_status(self):
        """Valid authenticated status should pass."""
        status = StatusResponse(
            status="ok",
            version="1.0.0",
            authenticated=True,
            user_id=123
        )
        assert status.status == "ok"
        assert status.authenticated is True
        assert status.user_id == 123

    def test_valid_unauthenticated_status(self):
        """Valid unauthenticated status should pass."""
        status = StatusResponse(
            status="ok",
            version="1.0.0",
            authenticated=False
        )
        assert status.authenticated is False
        assert status.user_id is None
