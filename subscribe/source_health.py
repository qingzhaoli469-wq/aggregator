# -*- coding: utf-8 -*-
"""Persistent consecutive-failure tracking for configured subscription sources."""

import json
from datetime import datetime, timedelta, timezone

import utils
from logger import logger

FAILURE_LIMIT = 3
COOLDOWN_HOURS = 72


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None


def load(push, item) -> dict:
    """Load public, non-sensitive source health state from the configured storage."""
    if not item or not push.validate(item):
        return {"version": 1, "sources": {}}
    try:
        raw = utils.http_get(url=push.raw_url(item), retry=1, timeout=15)
        data = json.loads(raw) if raw else {}
        if isinstance(data, dict) and isinstance(data.get("sources"), dict):
            return data
    except Exception as exc:
        logger.warning(f"[SourceHealth] cannot load persisted state: {exc}")
    return {"version": 1, "sources": {}}


def apply_cooldowns(sites: list, state: dict) -> None:
    """Temporarily skip sources after repeated failures; probe them again after cooldown."""
    now = _now()
    records = state.setdefault("sources", {})
    for site in sites or []:
        if getattr(site, "discovered", False):
            continue
        record = records.get(site.name, {})
        until = _parse_time(record.get("disabled_until", ""))
        if until and until > now:
            site.enable = False
            logger.warning(
                f"[SourceHealth] source={site.name} skipped until={until.isoformat()} "
                f"fail_streak={record.get('fail_streak', 0)}"
            )


def update(state: dict, tasks: list, fetched: dict, qualified: dict, managed_names: set[str]) -> None:
    """Update consecutive failure streaks from final post-speed-test source results."""
    now = _now()
    records = state.setdefault("sources", {})
    for task in tasks or []:
        name = str(getattr(task, "name", "")).strip().lower()
        if name not in managed_names:
            continue

        got = int(fetched.get(task.taskid, 0) or 0)
        passed = int(qualified.get(task.taskid, 0) or 0)
        record = records.setdefault(name, {"fail_streak": 0, "disabled_until": ""})
        if got > 0 and passed > 0:
            record["fail_streak"] = 0
            record["disabled_until"] = ""
            record["last_status"] = "healthy"
        else:
            streak = int(record.get("fail_streak", 0) or 0) + 1
            record["fail_streak"] = streak
            record["last_status"] = "no_qualified_nodes"
            if streak >= FAILURE_LIMIT:
                until = now + timedelta(hours=COOLDOWN_HOURS)
                record["disabled_until"] = until.isoformat()
                logger.warning(
                    f"[SourceHealth] source={name} disabled for {COOLDOWN_HOURS}h "
                    f"after {streak} consecutive failed runs"
                )
        record["last_checked"] = now.isoformat()
        record["fetched"] = got
        record["qualified"] = passed
        logger.info(
            f"[SourceHealth] source={name} fetched={got} qualified={passed} "
            f"fail_streak={record['fail_streak']}"
        )


def save(push, item, state: dict) -> None:
    if not item or not push.validate(item):
        logger.warning("[SourceHealth] persistence is not configured; failure streaks will not survive runs")
        return
    content = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    if not push.push_to(content=content, item=item, group="source-health"):
        logger.error("[SourceHealth] failed to persist source health state")
