import re
from datetime import datetime, time, timedelta
import pytz

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

# Các pattern nhận dạng thời gian
TIME_PATTERNS = [
    r"^(\d{1,2})h(\d{2})$",       # 10h30
    r"^(\d{1,2})h$",              # 10h
    r"^(\d{1,2}):(\d{2})$",       # 10:30
    r"^(\d{1,2})$",               # 10 (giờ nguyên)
]

DATE_ALIASES = {
    "today": 0,
    "hôm nay": 0,
    "yesterday": -1,
    "hôm qua": -1,
}


def parse_time_string(time_str: str) -> time | None:
    """
    Chuyển đổi chuỗi thời gian người dùng nhập vào thành object time.
    Hỗ trợ: '10h30', '10h', '10:30', '10'
    """
    time_str = time_str.strip().lower()

    # Pattern: 10h30 hoặc 10H30
    m = re.match(r"^(\d{1,2})h(\d{2})$", time_str, re.IGNORECASE)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)

    # Pattern: 10h (không có phút)
    m = re.match(r"^(\d{1,2})h$", time_str, re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return time(hour, 0)

    # Pattern: 10:30
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)

    # Pattern: chỉ giờ nguyên (10 → 10:00, 24 → 23:59:59)
    m = re.match(r"^(\d{1,2})$", time_str)
    if m:
        hour = int(m.group(1))
        if hour == 24:
            return time(23, 59, 59)
        if 0 <= hour <= 23:
            return time(hour, 0)

    return None


def parse_date_string(date_str: str | None) -> datetime:
    """
    Chuyển đổi chuỗi ngày thành datetime (local timezone).
    Hỗ trợ: 'today', 'yesterday', 'hôm nay', 'hôm qua', 'YYYY-MM-DD', 'DD/MM/YYYY'
    Mặc định trả về hôm nay nếu None.
    """
    now_local = datetime.now(TIMEZONE)

    if date_str is None:
        return now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    date_str = date_str.strip().lower()

    # Alias
    if date_str in DATE_ALIASES:
        delta = DATE_ALIASES[date_str]
        base = now_local + timedelta(days=delta)
        return base.replace(hour=0, minute=0, second=0, microsecond=0)

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_str)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return TIMEZONE.localize(datetime(y, mo, d, 0, 0, 0))

    # DD/MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_str)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return TIMEZONE.localize(datetime(y, mo, d, 0, 0, 0))

    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def build_datetime_range(
    start_str: str | None,
    end_str: str | None,
    date_str: str | None = None,
) -> tuple[datetime, datetime] | tuple[None, None]:
    """
    Kết hợp ngày + giờ bắt đầu/kết thúc thành 2 datetime UTC.
    Nếu start_str/end_str là None, mặc định là 00:00 -> 23:59.
    """
    # Xử lý giờ bắt đầu (Mặc định 00:00)
    if start_str:
        start_time = parse_time_string(start_str)
        if start_time is None: return None, None
    else:
        start_time = time(0, 0)

    # Xử lý giờ kết thúc (Mặc định: Bây giờ nếu không nhập)
    if end_str:
        end_time = parse_time_string(end_str)
        if end_time is None: return None, None
    else:
        # Lấy giờ hiện tại của hệ thống (local)
        now_local_time = datetime.now(TIMEZONE).time()
        end_time = now_local_time

    base_date = parse_date_string(date_str)

    start_local = base_date.replace(
        hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0
    )
    end_local = base_date.replace(
        hour=end_time.hour, minute=end_time.minute, second=end_time.second, microsecond=0
    )

    # Nếu người dùng nhập end < start (VD: 23h -> 01h sáng hôm sau)
    if end_local <= start_local:
        end_local += timedelta(days=1)

    # Giới hạn thời gian kết thúc không vượt quá "Bây giờ" nếu là ngày hôm nay
    now_local = datetime.now(TIMEZONE)
    if end_local > now_local:
        # Chỉ giới hạn nếu start_local vẫn ở quá khứ
        if start_local < now_local:
            end_local = now_local

    # Convert sang UTC
    start_utc = start_local.astimezone(pytz.utc)
    end_utc = end_local.astimezone(pytz.utc)

    return start_utc, end_utc


def format_local_time(dt_utc: datetime) -> str:
    """Chuyển UTC datetime thành chuỗi giờ local dễ đọc."""
    local = dt_utc.astimezone(TIMEZONE)
    return local.strftime("%H:%M %d/%m/%Y")
