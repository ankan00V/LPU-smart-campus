from __future__ import annotations
def _remedial_now() -> datetime:
    # Remedial schedules are expressed in campus local time, not the host OS timezone.
    # CI/tests can force UTC to keep time-window logic deterministic.
    if str(os.getenv("REMEDIAL_USE_UTC_NOW", "")).strip().lower() in {"1", "true", "yes", "on"}:
        return _utcnow_naive()

    zone_name = (os.getenv("APP_TIMEZONE", REMEDIAL_TIMEZONE_DEFAULT) or "").strip() or REMEDIAL_TIMEZONE_DEFAULT
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(REMEDIAL_TIMEZONE_DEFAULT)
    return datetime.now(zone).replace(tzinfo=None)
