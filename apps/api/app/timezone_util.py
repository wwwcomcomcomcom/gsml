from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import settings

TZ = ZoneInfo(settings.APP_TIMEZONE)


def today_local() -> date:
    return datetime.now(TZ).date()


def next_midnight_local() -> datetime:
    now = datetime.now(TZ)
    tomorrow = (now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=TZ)
