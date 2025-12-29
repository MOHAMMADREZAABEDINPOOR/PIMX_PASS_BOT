from __future__ import annotations

import contextlib
import hashlib
import io
import time
import re
from datetime import datetime, timezone
from dataclasses import dataclass
from html import escape
from typing import Any

from telegram import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ChatAction, InlineKeyboardButtonLimit, ParseMode
from telegram.error import BadRequest, Conflict, Forbidden
import asyncio
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings, load_settings
from .db import (
    connect,
    count_active,
    count_selected_active,
    count_total,
    init_db,
    upsert_user,
    count_users_since,
    count_users_total,
    list_users,
)
from .providers import ApiProvider, DataProvider, DbProvider
from .scanner import Scanner
from .web_server import WebServer

logger = logging.getLogger(__name__)
_last_conflict_log_at: float = 0.0
_SUPPORT_HANDLE = "@Pleasechangetheworld"
_ADMIN_USER_ID = 5675632554
_ADMIN_USERNAME = "@Pleasechangetheworld"


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    if int(user.id) == int(_ADMIN_USER_ID):
        return True
    username = (user.username or "").strip()
    return username.lower() == _ADMIN_USERNAME.lstrip("@").lower()


def _is_admin_chat_id(chat_id: int) -> bool:
    return int(chat_id) == int(_ADMIN_USER_ID)


def _extract_username_from_link(link: str | None) -> str | None:
    raw = (link or "").strip()
    if not raw:
        return None
    if "t.me/" in raw:
        return raw.split("t.me/", 1)[-1].strip().lstrip("@")
    return raw.lstrip("@") if raw.startswith("@") else None


async def _resolve_channel_id(context: ContextTypes.DEFAULT_TYPE, settings: Settings) -> int | None:
    cached_id = context.application.bot_data.get("channel_id_override")
    if cached_id:
        return int(cached_id)
    if settings.channel_id is not None:
        return int(settings.channel_id)
    candidates: list[str] = []
    if settings.channel_username:
        candidates.append(settings.channel_username)
    link_username = _extract_username_from_link(settings.channel_link)
    if link_username:
        candidates.append(link_username)
    for handle in candidates:
        try:
            chat = await context.bot.get_chat(handle)
            channel_id = int(chat.id)
            context.application.bot_data["channel_id_override"] = channel_id
            return channel_id
        except Exception:
            continue
    return None


async def _track_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_chat:
        return
    user = update.effective_user
    chat = update.effective_chat
    now = int(time.time())
    bio: str | None = None
    photo_file_id: str | None = None

    if chat.type == "private":
        cache = context.application.bot_data.setdefault("user_profile_cache", {})
        last_fetch = int(cache.get(user.id) or 0)
        if (now - last_fetch) >= 6 * 3600:
            with contextlib.suppress(Exception):
                chat_info = await context.bot.get_chat(chat.id)
                bio = getattr(chat_info, "bio", None)
            with contextlib.suppress(Exception):
                photos = await context.bot.get_user_profile_photos(user.id, limit=1)
                if photos.total_count > 0 and photos.photos:
                    photo_file_id = photos.photos[0][-1].file_id
            cache[user.id] = now

    write_db = context.application.bot_data.get("write_db")
    if write_db is None:
        return
    await upsert_user(
        write_db,
        {
            "user_id": int(user.id),
            "chat_id": int(chat.id),
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language_code": user.language_code,
            "is_premium": getattr(user, "is_premium", False),
            "is_bot": bool(user.is_bot),
            "bio": bio,
            "photo_file_id": photo_file_id,
            "first_seen_at": now,
            "last_seen_at": now,
        },
    )


@dataclass(slots=True)
class Session:
    chat_id: int
    user_id: int
    message_id: int
    page: int
    last_hash: str | None = None
    last_interaction_at: float = 0.0


def _webapp_url(settings: Settings) -> str | None:
    base = settings.public_base_url or settings.website_url
    if not base and settings.web_port is not None:
        host = settings.web_host or 'localhost'
        base = f'http://{host}:{int(settings.web_port)}'
    if not base:
        return None
    return f"{base.rstrip('/')}/webapp"


def _webapp_button(settings: Settings) -> InlineKeyboardButton | None:
    url = _webapp_url(settings)
    if not url:
        return None
    return InlineKeyboardButton("مینی‌اپ", web_app=WebAppInfo(url=url))


def _support_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("پشتیبانی", url=f"https://t.me/{_SUPPORT_HANDLE.lstrip('@')}")


def _menu_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row1: list[InlineKeyboardButton] = []
    if settings.channel_link:
        row1.append(InlineKeyboardButton("کانال", url=settings.channel_link))
    if settings.website_url:
        row1.append(InlineKeyboardButton("وب‌سایت", url=settings.website_url))
    webapp_btn = _webapp_button(settings)
    if webapp_btn:
        row1.append(webapp_btn)
    if row1:
        rows.append(row1)
    rows.append([_support_button()])
    rows.append(
        [
            InlineKeyboardButton("لیست سرورها", callback_data="menu:list"),
            InlineKeyboardButton("درباره", callback_data="menu:about"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _about_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row1: list[InlineKeyboardButton] = []
    if settings.channel_link:
        row1.append(InlineKeyboardButton("کانال", url=settings.channel_link))
    if settings.website_url:
        row1.append(InlineKeyboardButton("وب‌سایت", url=settings.website_url))
    webapp_btn = _webapp_button(settings)
    if webapp_btn:
        row1.append(webapp_btn)
    if row1:
        rows.append(row1)
    rows.append([_support_button()])
    rows.append([InlineKeyboardButton("بازگشت به منو", callback_data="menu:start")])
    return InlineKeyboardMarkup(rows)


def _join_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if settings.channel_link:
        rows.append([InlineKeyboardButton("عضویت در کانال", url=settings.channel_link)])
    rows.append([InlineKeyboardButton("بررسی عضویت", callback_data="menu:check")])
    webapp_btn = _webapp_button(settings)
    if webapp_btn:
        rows.append([webapp_btn])
    return InlineKeyboardMarkup(rows)


async def _is_member(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: Settings) -> bool:
    ok, _reason = await _check_membership(update, context, settings)
    return ok


def _membership_required_text(reason: str | None, *, with_check: bool) -> str:
    msg = (
        "🔒 **عضویت در کانال الزامی است**\n\n"
        "برای دسترسی به لیست سرورها، لطفاً ابتدا در کانال ما عضو شوید.\n"
    )
    if with_check:
        msg += "بعد از عضویت، دکمه «🔎 بررسی عضویت» را بزنید."
    else:
        msg += "بعد از عضویت، دوباره تلاش کنید."
    if reason:
        msg = f"{msg}\n\n⚠️ {reason}"
    return msg


async def _check_membership_by_id(
    user_id: int | None, context: ContextTypes.DEFAULT_TYPE, settings: Settings
) -> tuple[bool, str | None]:
    channel_id = await _resolve_channel_id(context, settings)
    if channel_id is None:
        return True, None
    if not user_id:
        return False, "❓ کاربر مشخص نیست."
    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
    except Forbidden:
        return True, None
    except BadRequest as e:
        msg = (e.message or "").lower()
        if "chat not found" in msg or "not found" in msg:
            channel_id = await _resolve_channel_id(context, settings)
            if channel_id is not None:
                try:
                    member = await context.bot.get_chat_member(channel_id, user_id)
                    status = getattr(member, "status", None)
                    if status in ("creator", "administrator", "member"):
                        return True, None
                    if status == "restricted":
                        return bool(getattr(member, "is_member", False)), None
                    return False, "❌ عضو کانال نیستید."
                except Exception:
                    pass
        if "bot was kicked" in msg or "not a member" in msg:
            return True, None
        return False, "⚠️ خطا در چک عضویت. بات به کانال دسترسی ندارد."

    status = getattr(member, "status", None)
    if status in ("creator", "administrator", "member"):
        return True, None
    if status == "restricted":
        return bool(getattr(member, "is_member", False)), None
    return False, "❌ عضو کانال نیستید."


async def _check_membership(
    update: Update, context: ContextTypes.DEFAULT_TYPE, settings: Settings
) -> tuple[bool, str | None]:
    if not update.effective_user:
        return False, "❓ کاربر مشخص نیست."
    return await _check_membership_by_id(update.effective_user.id, context, settings)


def _servers_keyboard(
    servers: list[dict[str, Any]],
    *,
    page: int,
    total: int,
    per_page: int,
    public_base_url: str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    bulk_text, fits_copy, _parts = _bulk_copy_payload(servers, public_base_url)
    for s in servers:
        flag, clean_name = _flag_and_clean_name(s.get("name"), s.get("country"))
        title = f"{flag} {clean_name}".strip()
        cfg = _normalize_config_for_share(
            str(s.get("config_string") or ""),
            country=s.get("country"),
            name=s.get("name"),
        )
        if InlineKeyboardButtonLimit.MIN_COPY_TEXT <= len(cfg) <= InlineKeyboardButtonLimit.MAX_COPY_TEXT:
            rows.append([InlineKeyboardButton(title[:60], copy_text=CopyTextButton(cfg))])
            continue

        if public_base_url:
            link = f"{public_base_url.rstrip('/')}/c/{int(s['id'])}"
            if InlineKeyboardButtonLimit.MIN_COPY_TEXT <= len(link) <= InlineKeyboardButtonLimit.MAX_COPY_TEXT:
                rows.append([InlineKeyboardButton(title[:60], copy_text=CopyTextButton(link))])
                continue

        # Long configs are filtered at provider level when no public URL is configured.

    nav: list[InlineKeyboardButton] = []
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton("⬅️ بعدی", callback_data=f"page:{page+1}"))
    if page > 0:
        nav.append(InlineKeyboardButton("قبلی ➡️", callback_data=f"page:{page-1}"))
    if nav:
        rows.append(nav)

    row_tools: list[InlineKeyboardButton] = []
    if bulk_text:
        if fits_copy:
            row_tools.append(InlineKeyboardButton("📋 کپی همه این صفحه", copy_text=CopyTextButton(bulk_text)))
        else:
            row_tools.append(InlineKeyboardButton("📋 کپی همه این صفحه", callback_data=f"copyall:{page}"))
    row_tools.append(InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"page:{page}"))
    rows.append(row_tools)
    rows.append([InlineKeyboardButton("منو 🏠", callback_data="menu:start")])
    return InlineKeyboardMarkup(rows)


def _hash_render(text: str, markup: InlineKeyboardMarkup | None) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    if markup:
        h.update(str(markup.to_dict()).encode("utf-8"))
    return h.hexdigest()


def _list_reply_keyboard(settings: Settings, *, is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton("لیست سرورها"), KeyboardButton("درباره")]]
    row2: list[KeyboardButton] = []
    if settings.channel_link:
        row2.append(KeyboardButton("کانال"))
    if settings.website_url:
        row2.append(KeyboardButton("وب‌سایت"))
    webapp_url = _webapp_url(settings)
    if webapp_url:
        row2.append(KeyboardButton("مینی‌اپ", web_app=WebAppInfo(url=webapp_url)))
    if row2:
        buttons.append(row2)
    buttons.append([KeyboardButton("پشتیبانی")])
    if is_admin:
        buttons.append([KeyboardButton("آمار کاربران"), KeyboardButton("لیست کاربران")])
    return ReplyKeyboardMarkup(
        buttons, 
        resize_keyboard=True, 
        one_time_keyboard=False, 
        input_field_placeholder="✨ از دکمه‌های زیر استفاده کنید"
    )

def _format_iso(dt_str: str) -> str:
    raw = (dt_str or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def _gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def _format_jalali(dt_str: str) -> str:
    raw = (dt_str or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_dt = parsed.astimezone()
        jy, jm, jd = _gregorian_to_jalali(local_dt.year, local_dt.month, local_dt.day)
        return f"{jy:04d}-{jm:02d}-{jd:02d} {local_dt.strftime('%H:%M')}"
    except Exception:
        return ""


def _format_iso_time_first(dt_str: str) -> str:
    raw = (dt_str or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_dt = parsed.astimezone()
        return f"{local_dt.strftime('%H:%M')} {local_dt.strftime('%Y-%m-%d')}"
    except Exception:
        return ""


def _format_jalali_time_first(dt_str: str) -> str:
    raw = (dt_str or "").strip()
    if not raw:
        return ""


def _start_of_today_ts() -> int:
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp())


async def _send_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    db = context.application.bot_data.get("write_db")
    if db is None:
        return
    now = int(time.time())
    one_hour = now - 3600
    three_hours = now - 3 * 3600
    day = now - 24 * 3600
    month = now - 30 * 24 * 3600
    three_months = now - 90 * 24 * 3600
    three_years = now - 3 * 365 * 24 * 3600
    today_start = _start_of_today_ts()

    counts = {
        "today": await count_users_since(db, since_ts=today_start),
        "1h": await count_users_since(db, since_ts=one_hour),
        "3h": await count_users_since(db, since_ts=three_hours),
        "24h": await count_users_since(db, since_ts=day),
        "1m": await count_users_since(db, since_ts=month),
        "3m": await count_users_since(db, since_ts=three_months),
        "3y": await count_users_since(db, since_ts=three_years),
    }
    total_users = await count_users_total(db)

    msg = (
        "📊 آمار کاربران\n"
        "────────────────\n"
        f"👥 کل کاربران: {total_users}\n"
        "────────────────\n"
        f"🗓️ امروز: {counts['today']}\n"
        f"⏱️ ۱ ساعت اخیر: {counts['1h']}\n"
        f"⏱️ ۳ ساعت اخیر: {counts['3h']}\n"
        f"🕘 ۲۴ ساعت اخیر: {counts['24h']}\n"
        f"🗓️ ۱ ماه اخیر: {counts['1m']}\n"
        f"🗓️ ۳ ماه اخیر: {counts['3m']}\n"
        f"🗓️ ۳ سال اخیر: {counts['3y']}"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        reply_markup=_list_reply_keyboard(
            context.application.bot_data["settings"], is_admin=True
        ),
    )


def _format_user_line(u: dict[str, Any]) -> str:
    name = " ".join([p for p in [u.get("first_name"), u.get("last_name")] if p]) or "-"
    username = f"@{u['username']}" if u.get("username") else "@-"
    last_seen_raw = datetime.fromtimestamp(int(u.get("last_seen_at") or 0)).isoformat()
    last_seen = _format_jalali_time_first(last_seen_raw) or "-"
    uses = int(u.get("usage_count") or 0)
    return f"👤 {name} | 🆔 {username} | 🔁 {uses} | 🕒 {last_seen}"


async def _send_admin_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    db = context.application.bot_data.get("write_db")
    if db is None:
        return
    users = await list_users(db)
    if not users:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="هیچ کاربری ثبت نشده است.",
        )
        return

    lines = [_format_user_line(u) for u in users]
    buf: list[str] = []
    size = 0
    for line in lines:
        if size + len(line) + 1 > 3500 and buf:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(buf))
            buf = [line]
            size = len(line) + 1
        else:
            buf.append(line)
            size += len(line) + 1
    if buf:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(buf))
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_dt = parsed.astimezone()
        jy, jm, jd = _gregorian_to_jalali(local_dt.year, local_dt.month, local_dt.day)
        return f"{local_dt.strftime('%H:%M')} {jy:04d}-{jm:02d}-{jd:02d}"
    except Exception:
        return ""


def _country_flag(country: str | None) -> str:
    code = (country or "").strip().upper()
    if not code or code == "UNKNOWN":
        return ""
    code = code.split("-")[0].split("_")[0]
    if len(code) == 2 and code.isalpha():
        base = 0x1F1E6
        return chr(base + (ord(code[0]) - ord("A"))) + chr(base + (ord(code[1]) - ord("A")))
    return ""


def _flag_and_clean_name(name: str | None, country: str | None) -> tuple[str, str]:
    raw = (name or "Server").strip()
    flag_from_country = _country_flag(country)
    stripped = re.sub(r'[\U0001F1E6-\U0001F1FF]{2}', ' ', raw)
    stripped = re.sub(r'^[\s\-\|_]+|[\s\-\|_]+$', '', stripped).strip()
    flags_in_name = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', raw)
    flag_from_name = flags_in_name[-1] if flags_in_name else ""
    flag = flag_from_country or flag_from_name or "🌐"
    # تغییر نام همه سرورها به PIMXPASS
    return flag, "PIMXPASS"

def _normalize_config_for_share(cfg: str, *, country: str | None, name: str | None) -> str:
    base = str(cfg or "").strip()
    if not base:
        return ""
    marker = "&type=tcp#"
    if marker in base:
        base = base.split(marker, 1)[0] + marker
    elif "#" in base:
        base = base.split("#", 1)[0] + "#"
    else:
        base = base + "#"
    flag, clean_name = _flag_and_clean_name(name, country)
    if flag:
        return f"{base}{flag} {clean_name}".strip()
    return f"{base}{clean_name}".strip()

def _server_copy_text(server: dict[str, Any], public_base_url: str | None) -> str | None:
    cfg = str(server.get("config_string") or "")
    cfg = _normalize_config_for_share(cfg, country=server.get("country"), name=server.get("name"))
    if InlineKeyboardButtonLimit.MIN_COPY_TEXT <= len(cfg) <= InlineKeyboardButtonLimit.MAX_COPY_TEXT:
        return cfg
    if public_base_url:
        link = f"{public_base_url.rstrip('/')}/c/{int(server['id'])}"
        if InlineKeyboardButtonLimit.MIN_COPY_TEXT <= len(link) <= InlineKeyboardButtonLimit.MAX_COPY_TEXT:
            return link
    return None


def _bulk_copy_payload(servers: list[dict[str, Any]], public_base_url: str | None) -> tuple[str, bool, list[str]]:
    parts: list[str] = []
    for s in servers:
        text = _server_copy_text(s, public_base_url)
        if text:
            parts.append(text)
    if not parts:
        return "", False, []
    joined = "\n".join(parts)
    return joined, len(joined) <= InlineKeyboardButtonLimit.MAX_COPY_TEXT, parts


def _server_line_with_name(server: dict[str, Any], public_base_url: str | None) -> str | None:
    base = server.get("config_string") or ""
    if not base:
        base = _server_copy_text(server, public_base_url) or ""
    base = str(base).strip()
    if not base:
        return None
    return _normalize_config_for_share(base, country=server.get("country"), name=server.get("name"))


def _chunk_lines(text: str, max_len: int = 3500) -> list[str]:
    lines = text.splitlines()
    chunks: list[str] = []
    buf: list[str] = []
    current = 0
    for line in lines:
        line_len = len(line) + 1  # include newline
        if current + line_len > max_len and buf:
            chunks.append("\n".join(buf))
            buf = [line]
            current = line_len
        else:
            buf.append(line)
            current += line_len
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def _format_until(dt_str: str) -> str:
    raw = (dt_str or "").strip()
    if not raw:
        return ""
    try:
        target = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        secs = int((target - now).total_seconds())
        if secs <= 0:
            return "0 ثانیه"
        mins, seconds = divmod(secs, 60)
        if mins == 0:
            return f"{seconds} ثانیه"
        hours, mins = divmod(mins, 60)
        if hours == 0:
            return f"{mins} دقیقه و {seconds:02d} ثانیه"
        return f"{hours} ساعت {mins:02d} دقیقه {seconds:02d} ثانیه"
    except Exception:
        return ""


async def _render_list(
    provider: DataProvider,
    *,
    page: int,
    per_page: int,
    public_base_url: str | None,
) -> tuple[str, InlineKeyboardMarkup]:
    status = await provider.get_scan_status()
    max_config_len = None if public_base_url else InlineKeyboardButtonLimit.MAX_COPY_TEXT
    paged = await provider.get_servers_page(page=page, per_page=per_page, max_config_len=max_config_len)
    total = paged.total

    servers = [
        {
            "id": s.id,
            "name": s.name,
            "latency": s.latency,
            "country": getattr(s, "country", None),
            "config_string": s.config_string,
        }
        for s in paged.servers
    ]

    header_lines: list[str] = []
    if status.is_scanning:
        total_to_show = status.total or 1000
        header_lines.append("🔬 در حال تست سرورها...")
        header_lines.append(f"📊 تست شده: {status.tested}/{total_to_show}")
        header_lines.append(f"✅ فعال پیدا شده: {status.active}")
    else:
        header_lines.append("📋 لیست سرورهای فعال")
        header_lines.append(f"✅ تعداد سرورهای فعال: {total}")

    if status.scan_completed_at:
        iso = _format_iso_time_first(status.scan_completed_at)
        jalali = _format_jalali_time_first(status.scan_completed_at)
        if jalali:
            header_lines.append(f"🕒 آخرین اسکن: {iso} | {jalali}")
        else:
            header_lines.append(f"🕒 آخرین اسکن: {iso}")
    if status.next_scan_at:
        until = _format_until(status.next_scan_at)
        suffix = f"⏳ {until}" if until else ""
        iso = _format_iso_time_first(status.next_scan_at)
        jalali = _format_jalali_time_first(status.next_scan_at)
        if jalali:
            header_lines.append(f"⏭️ اسکن بعدی: {iso} | {jalali}")
        else:
            header_lines.append(f"⏭️ اسکن بعدی: {iso}")
        if suffix:
            header_lines.append(suffix)

    header = "\n".join(header_lines) + "\n\n"

    if total <= 0:
        body = (
            "⏳ هنوز سرور فعالی پیدا نشده\n\n"
            "لطفاً چند لحظه صبر کنید تا تست سرورها کامل شود."
        )
        keyboard = _servers_keyboard([], page=0, total=0, per_page=per_page, public_base_url=public_base_url)
        return header + body, keyboard

    total_pages = (total + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))

    body = (
        f"📄 صفحه {page + 1} از {total_pages}\n\n"
        "👆 نحوه استفاده:\n"
        "• روی هر سرور بزنید تا کانفیگ آن کپی شود\n"
        "• اگر کانفیگ طولانی باشد، لینک کوتاه کپی می‌شود\n"
        "• از دکمه «📋 کپی همه این صفحه» برای کپی همه سرورها استفاده کنید"
    )
    keyboard = _servers_keyboard(
        servers,
        page=page,
        total=total,
        per_page=per_page,
        public_base_url=public_base_url,
    )
    return header + body, keyboard


async def _clear_chat_sessions(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    skip_message_id: int | None = None,
) -> None:
    sessions: dict[tuple[int, int], Session] = context.application.bot_data.get("sessions", {})
    keys = [key for key in sessions if key[0] == chat_id]
    for key in keys:
        session = sessions.pop(key, None)
        if not session:
            continue
        if skip_message_id is not None and session.message_id == skip_message_id:
            continue
        with contextlib.suppress(BadRequest):
            await context.bot.delete_message(chat_id=session.chat_id, message_id=session.message_id)


async def update_sessions_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    provider: DataProvider = context.application.bot_data["provider"]

    sessions: dict[tuple[int, int], Session] = context.application.bot_data.get("sessions", {})
    if not sessions:
        return

    ttl = int(settings.session_ttl_seconds)
    now = time.time()

    # Rate-limit edits per tick to avoid hitting Telegram limits when many users are active.
    max_edits = int(context.application.bot_data.get("max_session_edits_per_tick", 25))
    cursor = int(context.application.bot_data.get("session_cursor", 0))
    keys = list(sessions.keys())
    if not keys:
        return
    cursor %= len(keys)

    per_page = int(settings.servers_per_page)
    edits = 0
    scanned = 0

    for _ in range(len(keys)):
        key = keys[cursor]
        cursor = (cursor + 1) % len(keys)
        scanned += 1
        session = sessions.get(key)
        if not session:
            continue
        ok, reason = await _check_membership_by_id(session.user_id, context, settings)
        if not ok:
            sessions.pop(key, None)
            with contextlib.suppress(BadRequest):
                await context.bot.delete_message(chat_id=session.chat_id, message_id=session.message_id)
            await context.bot.send_message(
                chat_id=session.chat_id,
                text=_membership_required_text(reason, with_check=True),
                reply_markup=_join_keyboard(settings),
                parse_mode=ParseMode.MARKDOWN,
            )
            continue
        if (now - session.last_interaction_at) > ttl:
            sessions.pop(key, None)
            continue

        try:
            text, keyboard = await _render_list(
                provider,
                page=session.page,
                per_page=per_page,
                public_base_url=settings.public_base_url,
            )
        except Exception:
            continue

        new_hash = _hash_render(text, keyboard)
        if session.last_hash == new_hash:
            continue

        try:
            await context.bot.edit_message_text(
                chat_id=session.chat_id,
                message_id=session.message_id,
                text=text,
                reply_markup=keyboard,
            )
            session.last_hash = new_hash
            edits += 1
        except BadRequest:
            sessions.pop(key, None)

        if edits >= max_edits:
            break

    context.application.bot_data["session_cursor"] = cursor


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    settings: Settings = context.application.bot_data["settings"]
    if update.message:
        welcome_text = (
            "🌟 **به بات VPN خوش آمدید!**\n\n"
            "🚀 این بات به صورت خودکار بهترین سرورهای VPN را برای شما پیدا می‌کند.\n"
            "⚡ سرورها با پینگ زیر 250ms و کیفیت بالا انتخاب می‌شوند.\n\n"
            "👇 از دکمه‌های زیر استفاده کنید:\n\n"
            "💡 برای گرفتن لیست سرورها، دکمه مربوطه را از منو انتخاب کنید."
        )
        await update.message.reply_text(
            welcome_text, 
            reply_markup=_list_reply_keyboard(settings, is_admin=_is_admin(update)),
            parse_mode=ParseMode.MARKDOWN
        )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    settings: Settings = context.application.bot_data["settings"]
    provider: DataProvider = context.application.bot_data["provider"]

    scan = await provider.get_scan_status()
    msg = [
        f"🧩 DATA_PROVIDER={settings.data_provider}",
        f"🧪 scan: is_scanning={scan.is_scanning} tested={scan.tested}/{scan.total} active_found={scan.active}",
    ]

    if settings.data_provider == "db":
        read_dbs = context.application.bot_data.get("read_dbs") or []
        if read_dbs:
            total = await count_total(read_dbs[0])
            active = await count_active(read_dbs[0])
            selected = await count_selected_active(read_dbs[0])
            msg.append(f"🗄️ db: total={total} active={active} selected_active={selected}")

    if update.message:
        await update.message.reply_text("\n".join(msg))


async def menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer("🏠")
    settings: Settings = context.application.bot_data["settings"]
    if not query.message:
        return

    await _clear_chat_sessions(query.message.chat_id, context, skip_message_id=query.message.message_id)
    job_name = f"session:{query.message.chat_id}:{query.message.message_id}"
    for job in context.job_queue.jobs():
        if job.name == job_name:
            job.schedule_removal()

    with contextlib.suppress(BadRequest):
        await query.message.delete()
    welcome_text = (
        "🌟 **به منو اصلی خوش آمدید!**\n\n"
        "🎯 **دسترسی سریع:**\n"
        "• 📑 لیست سرورها - مشاهده سرورهای فعال\n"
        "• 📢 کانال - عضویت در کانال ما\n"
        "• ℹ️ درباره - اطلاعات بیشتر\n\n"
        "💡 می‌توانید از دکمه‌های زیر باکس چت هم استفاده کنید!"
    )
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=welcome_text,
        reply_markup=_list_reply_keyboard(settings, is_admin=_is_admin(update)),
        parse_mode=ParseMode.MARKDOWN
    )


async def menu_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer("ℹ️ درباره ما")

    settings: Settings = context.application.bot_data["settings"]
    if not query.message:
        return

    text = (
        "ℹ️ درباره بات\n\n"
        "🤖 این بات به صورت خودکار سرورها را تست می‌کند و بهترین‌ها را نمایش می‌دهد.\n"
        "🧪 تست سرورها هر ۱ ساعت انجام می‌شود.\n"
        "🌐 سایت ما در حال ساخته.\n"
    )
    with contextlib.suppress(BadRequest):
        await query.edit_message_text(
            text,
            disable_web_page_preview=True,
        )


async def menu_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer("⏳ در حال آماده‌سازی لیست...")

    settings: Settings = context.application.bot_data["settings"]
    ok, reason = await _check_membership(update, context, settings)
    if not ok:
        await query.edit_message_text(
            _membership_required_text(reason, with_check=True),
            reply_markup=_join_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    provider: DataProvider = context.application.bot_data["provider"]
    per_page = int(settings.servers_per_page)
    if not query.message:
        return

    try:
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        text, keyboard = await _render_list(
            provider,
            page=0,
            per_page=per_page,
            public_base_url=settings.public_base_url,
        )
        msg = await query.message.reply_text(text, reply_markup=keyboard)
        with contextlib.suppress(BadRequest):
            await query.message.delete()
    except Exception:
        logger.exception("Failed to render server list")
        await query.message.reply_text("⚠️ خطا در دریافت لیست سرورها. چند ثانیه بعد دوباره تلاش کنید.")
        return
    session = Session(
        chat_id=msg.chat_id,
        user_id=update.effective_user.id if update.effective_user else 0,
        message_id=msg.message_id,
        page=0,
        last_interaction_at=time.time(),
    )
    context.application.bot_data.setdefault("sessions", {})[(session.chat_id, session.message_id)] = session
    session.last_hash = _hash_render(text, keyboard)

async def _send_menu_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    await _clear_chat_sessions(chat_id, context)
    menu_text = (
        "🌟 **منو اصلی**\n\n"
        "🎯 دسترسی سریع به تمام امکانات بات\n"
        "👇 از دکمه‌های زیر استفاده کنید:"
    )
    await context.bot.send_message(
        chat_id=chat_id, 
        text=menu_text, 
        reply_markup=_list_reply_keyboard(settings, is_admin=_is_admin_chat_id(chat_id)),
        parse_mode=ParseMode.MARKDOWN
    )


async def _send_server_list_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int,
    user_id: int,
) -> None:
    await _track_user(update, context)
    settings: Settings = context.application.bot_data["settings"]
    ok, reason = await _check_membership(update, context, settings)
    if not ok:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=_membership_required_text(reason, with_check=False), 
            reply_markup=_join_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    provider: DataProvider = context.application.bot_data["provider"]
    per_page = int(settings.servers_per_page)
    await _clear_chat_sessions(chat_id, context)
    text, keyboard = await _render_list(
        provider,
        page=0,
        per_page=per_page,
        public_base_url=settings.public_base_url,
    )
    msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    session = Session(
        chat_id=msg.chat_id,
        user_id=user_id,
        message_id=msg.message_id,
        page=0,
        last_interaction_at=time.time(),
    )
    context.application.bot_data.setdefault("sessions", {})[(session.chat_id, session.message_id)] = session
    session.last_hash = _hash_render(text, keyboard)


async def _send_about_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    text = (
        "🌟 **درباره بات VPN**\n\n"
        "🤖 **سیستم هوشمند تست سرور:**\n"
        "• تست خودکار سرورها هر 1 ساعت\n"
        "• انتخاب سرورهای با پینگ زیر 250ms\n"
        "• به‌روزرسانی لحظه‌ای لیست سرورها\n"
        "• پشتیبانی از پروتکل‌های مختلف (VLESS, VMESS, Trojan)\n\n"
        "⚡ **ویژگی‌ها:**\n"
        "• 🎯 انتخاب هوشمند بهترین سرورها\n"
        "• 🔄 به‌روزرسانی خودکار\n"
        "• 📊 نمایش پینگ و وضعیت سرورها\n"
        "• 🚀 دسترسی سریع و آسان\n\n"
        "🌐 **وب‌سایت:** در حال ساخت..."
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=_list_reply_keyboard(settings, is_admin=_is_admin_chat_id(chat_id)),
        disable_web_page_preview=True,
        parse_mode=ParseMode.MARKDOWN
    )


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    text = (update.message.text or "").strip()
    if not text:
        return

    settings: Settings = context.application.bot_data["settings"]
    norm = text.replace("‌", " ").strip()
    norm = re.sub(r"[\U0001f4d1\U0001f4e2]+", "", norm).strip()
    if _is_admin(update) and norm in {"آمار کاربران", "user stats", "stats"}:
        await _send_admin_stats(update, context)
        return
    if _is_admin(update) and norm in {"لیست کاربران", "user list", "users"}:
        await _send_admin_user_list(update, context)
        return
    if norm in {"منو", "menu"}:
        await _send_menu_message(update.effective_chat.id, context)
        return
    if norm in {"لیست سرورها", "لیست سرور", "servers"}:
        await _send_server_list_message(
            update,
            context,
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
        )
        return
    if norm in {"درباره ما", "درباره", "about"}:
        await _send_about_message(update.effective_chat.id, context)
        return
    if norm in {"کانال", "channel"} and settings.channel_link:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📢 **کانال ما**\n\n"
                "برای عضویت در کانال و دریافت آخرین اخبار و به‌روزرسانی‌ها، روی لینک زیر کلیک کنید:"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 عضویت در کانال", url=settings.channel_link)]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if norm in {"وب‌سایت", "وب سایت", "website"} and settings.website_url:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "🌐 **وب‌سایت ما**\n\n"
                "برای مشاهده وب‌سایت، از لینک زیر استفاده کنید:"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 وب‌سایت", url=settings.website_url)]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if norm in {"پشتیبانی", "support"}:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🧩 برای ارتباط با پشتیبانی، روی دکمه زیر بزنید:",
            reply_markup=InlineKeyboardMarkup([
                [_support_button()]
            ]),
        )
        return
    if norm in {"مینی‌اپ", "مینی اپ", "miniapp", "webapp"}:
        webapp_url = _webapp_url(settings)
        if webapp_url:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🧩 **مینی‌اپ**\n\nبرای باز کردن مینی‌اپ، روی دکمه زیر بزنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("مینی‌اپ", web_app=WebAppInfo(url=webapp_url))]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        return


async def menu_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer("🔎")

    settings: Settings = context.application.bot_data["settings"]
    ok, reason = await _check_membership(update, context, settings)
    if not ok:
        msg = (
            "❌ **عضویت تایید نشد**\n\n"
            "لطفاً ابتدا در کانال ما عضو شوید، سپس دوباره دکمه «🔎 بررسی عضویت» را بزنید."
        )
        if reason and "عضو کانال نیستید" not in reason:
            msg = f"{msg}\n\n⚠️ {reason}"
        with contextlib.suppress(BadRequest):
            await query.edit_message_text(
                msg,
                reply_markup=_join_keyboard(settings),
                parse_mode=ParseMode.MARKDOWN
            )
        return

    provider: DataProvider = context.application.bot_data["provider"]
    per_page = int(settings.servers_per_page)
    if not query.message:
        return

    try:
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        text, keyboard = await _render_list(
            provider,
            page=0,
            per_page=per_page,
            public_base_url=settings.public_base_url,
        )
        msg = await query.message.reply_text(text, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to render server list after membership check")
        await query.message.reply_text("⚠️ خطا در دریافت لیست سرورها. چند ثانیه بعد دوباره تلاش کنید.")
        return

    session = Session(
        chat_id=msg.chat_id,
        user_id=update.effective_user.id if update.effective_user else 0,
        message_id=msg.message_id,
        page=0,
        last_interaction_at=time.time(),
    )
    context.application.bot_data.setdefault("sessions", {})[(session.chat_id, session.message_id)] = session
    session.last_hash = _hash_render(text, keyboard)


async def page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer("📄")

    settings: Settings = context.application.bot_data["settings"]
    provider: DataProvider = context.application.bot_data["provider"]
    ok, reason = await _check_membership(update, context, settings)
    if not ok:
        sessions: dict[tuple[int, int], Session] = context.application.bot_data.setdefault("sessions", {})
        if query.message:
            sessions.pop((query.message.chat_id, query.message.message_id), None)
        with contextlib.suppress(BadRequest):
            await query.edit_message_text(
                _membership_required_text(reason, with_check=True),
                reply_markup=_join_keyboard(settings),
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    try:
        _, raw_page = (query.data or "").split(":", 1)
        page = int(raw_page)
    except Exception:
        return

    per_page = int(settings.servers_per_page)
    text, keyboard = await _render_list(
        provider,
        page=page,
        per_page=per_page,
        public_base_url=settings.public_base_url,
    )
    try:
        msg = await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest as exc:
        # When content/markup is identical, ignore the error and keep the current message
        if "Message is not modified" in str(exc):
            msg = query.message or await query.get_message()
        else:
            raise

    sessions: dict[tuple[int, int], Session] = context.application.bot_data.setdefault("sessions", {})
    key = (msg.chat_id, msg.message_id)
    session = sessions.get(key)
    if not session:
        session = Session(
            chat_id=msg.chat_id,
            user_id=update.effective_user.id if update.effective_user else 0,
            message_id=msg.message_id,
            page=page,
        )
        sessions[key] = session
    session.page = page
    session.last_interaction_at = time.time()
    # global updater job will refresh it


async def copy_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _track_user(update, context)
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer("📋")

    settings: Settings = context.application.bot_data["settings"]
    provider: DataProvider = context.application.bot_data["provider"]
    ok, reason = await _check_membership(update, context, settings)
    if not ok:
        sessions: dict[tuple[int, int], Session] = context.application.bot_data.setdefault("sessions", {})
        if query.message:
            sessions.pop((query.message.chat_id, query.message.message_id), None)
        with contextlib.suppress(BadRequest):
            await query.edit_message_text(
                _membership_required_text(reason, with_check=True),
                reply_markup=_join_keyboard(settings),
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    try:
        _, raw_page = (query.data or "").split(":", 1)
        page = int(raw_page)
    except Exception:
        return

    per_page = int(settings.servers_per_page)
    paged = await provider.get_servers_page(
        page=page,
        per_page=per_page,
        max_config_len=None if settings.public_base_url else InlineKeyboardButtonLimit.MAX_COPY_TEXT,
    )
    servers = [
        {
            "id": s.id,
            "name": s.name,
            "latency": s.latency,
            "country": getattr(s, "country", None),
            "config_string": s.config_string,
        }
        for s in paged.servers
    ]
    bulk_text, fits_copy, _ = _bulk_copy_payload(servers, settings.public_base_url)
    lines: list[str] = []
    for srv in servers:
        line = _server_line_with_name(srv, settings.public_base_url)
        if line:
            lines.append(line)
    combined = "\n".join(lines).strip()

    if not combined:
        await query.message.reply_text("⚠️ موردی برای کپی وجود ندارد.")
        return

    # دکمه کپی یکجا اگر در محدودۀ Telegram باشد
    buttons: list[list[InlineKeyboardButton]] = []
    if InlineKeyboardButtonLimit.MIN_COPY_TEXT <= len(combined) <= InlineKeyboardButtonLimit.MAX_COPY_TEXT:
        buttons.append([InlineKeyboardButton("📋 کپی همه این صفحه", copy_text=CopyTextButton(combined))])
    if buttons:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="برای کپی همه سرورها دکمه زیر را بزنید:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ارسال متن کامل سرورها (با نام/پرچم) در پیام‌های جدا اگر طول زیاد بود
    for chunk in _chunk_lines(combined):
        await context.bot.send_message(chat_id=query.message.chat_id, text=chunk)

    # فایل متنی همه آیتم‌ها
    buffer = io.BytesIO(combined.encode("utf-8"))
    buffer.name = f"PIMXPASS-page-{page+1}.txt"
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=buffer,
        caption="📄 همه سرورهای این صفحه در یک فایل برای کپی کردن",
    )
    # پس از ارسال خروجی‌ها، دوباره لیست را نشان می‌دهیم تا پیمایش ادامه پیدا کند
    text, keyboard = await _render_list(
        provider,
        page=page,
        per_page=per_page,
        public_base_url=settings.public_base_url,
    )
    await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=keyboard)


async def server_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(BadRequest):
        await query.answer()

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, Conflict):
        global _last_conflict_log_at
        now = time.time()
        if (now - _last_conflict_log_at) >= 10:
            _last_conflict_log_at = now
            logger.warning(
                "Polling conflict (409): یک جای دیگر با همین BOT_TOKEN دارد getUpdates می‌گیرد. "
                "فقط یک نمونه از بات باید اجرا شود."
            )
        return
    logger.exception("Unhandled error", exc_info=err)


async def _scan_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if settings.data_provider != "db":
        return
    scanner: Scanner = context.application.bot_data["scanner"]
    await scanner.scan_once()


def _schedule_scans(app: Application) -> None:
    settings: Settings = app.bot_data["settings"]
    if settings.data_provider != "db":
        return

    app.job_queue.run_once(_scan_job, when=0, name="initial-scan")
    app.job_queue.run_repeating(
        _scan_job,
        interval=int(settings.scan_interval_seconds),
        first=int(settings.scan_interval_seconds),
        name="hourly-scan",
    )


async def _post_init(app: Application) -> None:
    settings: Settings = app.bot_data["settings"]

    write_db = await connect(settings.db_path)
    await init_db(write_db)
    read_dbs = [await connect(settings.db_path) for _ in range(max(1, int(settings.read_db_pool_size)))]

    scanner = Scanner(db=write_db, settings=settings)
    if settings.data_provider == "api":
        provider: DataProvider = ApiProvider(api_base_url=settings.api_base_url or "")
    else:
        provider = DbProvider(dbs=read_dbs, scanner=scanner)

    app.bot_data["read_dbs"] = read_dbs
    app.bot_data["write_db"] = write_db
    app.bot_data["scanner"] = scanner
    app.bot_data["provider"] = provider
    app.bot_data.setdefault("sessions", {})
    app.bot_data.setdefault("max_session_edits_per_tick", 25)

    _schedule_scans(app)

    # Single global updater for all active sessions (more scalable than one job per message).
    app.job_queue.run_repeating(
        update_sessions_job,
        interval=int(settings.list_update_interval_seconds),
        first=int(settings.list_update_interval_seconds),
        name="sessions-updater",
    )

    if settings.web_port is not None:
        web = WebServer(
            host=settings.web_host,
            port=int(settings.web_port),
            dbs=read_dbs,
            provider=provider,
            default_per_page=int(settings.servers_per_page),
            public_base_url=settings.public_base_url,
        )
        await web.start()
        app.bot_data["web_server"] = web
        base = settings.public_base_url or settings.website_url or f"http://{settings.web_host}:{int(settings.web_port)}"
        logger.info("Web server started at %s/webapp", base.rstrip("/"))


async def _post_shutdown(app: Application) -> None:
    write_db = app.bot_data.get("write_db")
    read_dbs = app.bot_data.get("read_dbs") or []
    for db in read_dbs:
        await db.close()
    if write_db is not None:
        await write_db.close()
    web = app.bot_data.get("web_server")
    if web is not None:
        await web.stop()


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = load_settings()

    asyncio.set_event_loop(asyncio.new_event_loop())

    while True:
        builder = Application.builder().token(settings.bot_token)
        builder.post_init(_post_init)
        builder.post_shutdown(_post_shutdown)
        app = builder.build()

        app.bot_data["settings"] = settings
        app.bot_data["sessions"] = {}

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status_cmd))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
        app.add_handler(CallbackQueryHandler(menu_start, pattern=r"^menu:start$"))
        app.add_handler(CallbackQueryHandler(menu_list, pattern=r"^menu:list$"))
        app.add_handler(CallbackQueryHandler(menu_check, pattern=r"^menu:check$"))
        app.add_handler(CallbackQueryHandler(menu_about, pattern=r"^menu:about$"))
        app.add_handler(CallbackQueryHandler(page_nav, pattern=r"^page:-?\d+$"))
        app.add_handler(CallbackQueryHandler(copy_all, pattern=r"^copyall:-?\d+$"))
        app.add_handler(CallbackQueryHandler(server_pick, pattern=r"^srv:\d+$"))
        app.add_error_handler(on_error)

        try:
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                timeout=20,
                connect_timeout=15,
                read_timeout=30,
                write_timeout=30,
                pool_timeout=30,
            )
        except Exception:
            logger.exception("Bot crashed, restarting in 5 seconds")
            time.sleep(5)
            continue
        break
