from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from fastapi import APIRouter, Query
from pydantic import BaseModel


def _log_payload(tag: str, payload) -> None:
    """Append payloads to a local log for inspection."""
    log_path = Path("data/plugin_api.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "tag": tag,
        "payload": payload,
    }
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Best effort logging; ignore failures to avoid breaking plugin calls.
        pass


router = APIRouter()


# ---- Models matching RuneLite plugin payloads (trimmed) ----
class NameChange(BaseModel):
    oldName: str
    newName: str


class Member(BaseModel):
    username: str
    role: str


class RoleIndex(BaseModel):
    role: str
    index: int


class GroupMemberAddition(BaseModel):
    verificationCode: str
    members: List[Member]
    roleOrders: Set[RoleIndex]


class AnalyticsPlayerUpdate(BaseModel):
    accountHash: Optional[int] = None


# ---- Endpoints ----
@router.post("/names/bulk")
async def bulk_name_changes(changes: List[NameChange]):
    _log_payload("names_bulk", [c.model_dump() for c in changes])
    return {"status": "ok", "count": len(changes)}


@router.get("/groups/{group_id}")
async def get_group(group_id: int):
    _log_payload("groups_get", {"group_id": group_id})
    now = datetime.utcnow().isoformat()
    return {
        "id": group_id,
        "name": f"Group {group_id}",
        "memberCount": 1,
        "memberships": [
            {
                "playerId": 1,
                "groupId": group_id,
                "role": "member",
                "createdAt": now,
                "updatedAt": now,
                "player": {
                    "id": 1,
                    "username": "SamplePlayer",
                    "displayName": "SamplePlayer",
                    "type": "regular",
                    "build": "main",
                },
            }
        ],
    }


@router.put("/groups/{group_id}")
async def sync_group(group_id: int, payload: GroupMemberAddition):
    data = payload.model_dump()
    data["group_id"] = group_id
    _log_payload("groups_put", data)
    now = datetime.utcnow().isoformat()
    memberships = [
        {
            "playerId": i,
            "groupId": group_id,
            "role": m.role,
            "createdAt": now,
            "updatedAt": now,
            "player": {
                "id": i,
                "username": m.username,
                "displayName": m.username,
                "type": "regular",
                "build": "main",
            },
        }
        for i, m in enumerate(payload.members, start=1)
    ]
    return {
        "id": group_id,
        "name": f"Group {group_id}",
        "memberCount": len(memberships),
        "memberships": memberships,
    }


@router.get("/players/{username}")
async def get_player(username: str):
    _log_payload("players_get", {"username": username})
    now = datetime.utcnow().isoformat()
    return {
        "id": 1,
        "username": username,
        "displayName": username,
        "type": "regular",
        "build": "main",
        "registeredAt": now,
        "updatedAt": now,
        "latestSnapshot": {
          "id": 1,
          "playerId": 1,
          "createdAt": now,
          "importedAt": now,
          "data": {
            "skills": {
              "overall": {"metric": "overall", "experience": 1_000_000, "rank": 0, "level": 126, "ehp": 0.0}
            },
            "bosses": {},
            "activities": {},
            "computed": {}
          }
        }
    }


@router.post("/players/{username}")
async def update_player(username: str, payload: AnalyticsPlayerUpdate):
    data = payload.model_dump()
    data["username"] = username
    _log_payload("players_post", data)
    return {"status": "queued", "username": username, "accountHash": payload.accountHash}


@router.get("/players/{username}/competitions")
async def player_competitions(username: str, status: str = Query("ongoing")):
    _log_payload("players_competitions", {"username": username, "status": status})
    now = datetime.utcnow().isoformat()
    comp = {
        "id": 1,
        "title": "Sample Competition",
        "metric": "overall",
        "type": "classic",
        "startsAt": now,
        "endsAt": now,
        "groupId": 1,
        "score": 0,
        "createdAt": now,
        "updatedAt": now,
        "participantCount": 1,
        "group": {"id": 1, "name": "Sample Group"},
    }
    return [
        {
            "playerId": 1,
            "competitionId": comp["id"],
            "teamName": None,
            "createdAt": now,
            "updatedAt": now,
            "competition": comp,
        }
    ]


@router.get("/players/{username}/competitions/standings")
async def player_competition_standings(username: str, status: str = Query("ongoing")):
    _log_payload("players_competitions_standings", {"username": username, "status": status})
    now = datetime.utcnow().isoformat()
    comp = {
        "id": 1,
        "title": "Sample Competition",
        "metric": "overall",
        "type": "classic",
        "startsAt": now,
        "endsAt": now,
        "groupId": 1,
        "score": 0,
        "createdAt": now,
        "updatedAt": now,
        "participantCount": 1,
        "group": {"id": 1, "name": "Sample Group"},
    }
    return [
        {
            "playerId": 1,
            "competitionId": comp["id"],
            "teamName": None,
            "createdAt": now,
            "updatedAt": now,
            "progress": {"start": 0, "end": 1_000_000, "gained": 12_345},
            "rank": 1,
            "competition": comp,
        }
    ]
