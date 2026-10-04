import logging
import asyncio
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.exceptions import TelegramAPIError

# وارد کردن سرویس‌ها و دیتابیس
from services.price_service import fetch_nobitex_stats
from database.db import get_active_alerts, deactivate_alert

logger = logging.getLogger(__name__)

# نگاشت نام‌ها برای زیبایی متن پیام ارسالی به کاربر
ASSET_NAMES = {"usd": "تتر (دلار آزاد)", "btc": "بیت‌کوین", "eth": "اتریوم"}


async def check_alerts_and_notify(bot: Bot):
    """
    این تابع توسط زمان‌بند (Scheduler) به صورت دوره‌ای فراخوانی می‌شود.
    سرعت اجرای این تابع به دلیل ناهمگام بودن فوق‌العاده بالا است.
    """
    try:
        # ۱. دریافت تمام هشدارهای فعال از دیتابیس
        active_alerts = await get_active_alerts()
        if not active_alerts:
            # اگر هشداری در سیستم نیست، پردازش را متوقف کن تا منابع سرور هدر نرود
            return

            # ۲. دریافت جدیدترین قیمت‌ها (با استفاده از کش داخلی جهت جلوگیری از مسدود شدن API)
        prices = await fetch_nobitex_stats()
        if not prices:
            logger.warning("Failed to fetch prices for background alert checking.")
            return

        tasks = []
        # ۳. بررسی شرط هشدار تک‌تک کاربران
        for alert in active_alerts:
            asset = alert['asset']
            target_price = alert['target_price']
            condition = alert['condition']

            # اگر ارز در لیست قیمت‌ها نبود، رد شو
            if asset not in prices:
                continue

            current_price = prices[asset]['latest']
            is_triggered = False

            # منطق اصلی بررسی هشدارها
            if condition == "above" and current_price >= target_price:
                is_triggered = True
            elif condition == "below" and current_price <= target_price:
                is_triggered = True

            # اگر شرط برقرار بود، آن را به عنوان یک وظیفه (Task) ثبت می‌کنیم
            # تا در مرحله بعدی همه را با هم (موازی) بفرستیم
            if is_triggered:
                tasks.append(process_triggered_alert(bot, alert, current_price))

        # ۴. اجرای همزمان (Concurrent Execution) تمامی پیام‌های هشدار
        # این خط باعث می‌شود اگر همزمان ۱۰۰ هشدار فعال شد، ربات بدون لگ در کسری از ثانیه همه را بفرستد
        if tasks:
            await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"Critical error in check_alerts_and_notify: {e}")


async def process_triggered_alert(bot: Bot, alert: dict, current_price: float):
    """
    ارسال پیام به کاربر و غیرفعال‌سازی وضعیت آن در دیتابیس.
    """
    alert_id = alert['id']
    user_id = alert['user_id']
    asset = alert['asset']
    target_price = alert['target_price']
    condition = alert['condition']

    asset_name = ASSET_NAMES.get(asset, asset.upper())
    trend_emoji = "📈" if condition == "above" else "📉"

    text = (
        f"🚨 <b>هشدار قیمت فعال شد!</b> 🚨\n\n"
        f"موجودی <b>{asset_name}</b> به هدف شما رسید!\n\n"
        f"🎯 هدف شما: <code>{target_price:,}</code> تومان\n"
        f"💲 قیمت لحظه‌ای: <code>{current_price:,}</code> تومان {trend_emoji}\n\n"
        f"<i>این هشدار اکنون غیرفعال شد.</i>"
    )

    try:
        # ارسال پیام به کاربر
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        # تغییر وضعیت هشدار به انجام‌شده (غیرفعال)
        await deactivate_alert(alert_id)
        logger.info(f"Alert {alert_id} successfully sent to user {user_id}.")

    except TelegramAPIError as e:
        # اگر کاربر ربات را متوقف (Block) کرده باشد یا اکانتش حذف شده باشد،
        # API تلگرام ارور می‌دهد. ما ارور را می‌گیریم و هشدار را غیرفعال می‌کنیم
        # تا در چرخه‌های بعدی ربات بی‌دلیل به این کاربر پیام نفرستد.
        logger.warning(f"Failed to send alert to {user_id} (maybe blocked). Disabling alert. Error: {e}")
        await deactivate_alert(alert_id)
    except Exception as e:
        logger.error(f"Unexpected error while processing alert {alert_id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    این تابع یک نمونه از زمان‌بند ایجاد می‌کند و وظیفه چک کردن
    قیمت‌ها را برای اجرای دوره‌ای برنامه‌ریزی می‌کند.
    """
    scheduler = AsyncIOScheduler()

    # تنظیم اجرای تابع بررسی قیمت هر ۱ دقیقه (۶۰ ثانیه)
    scheduler.add_job(
        check_alerts_and_notify,
        trigger='interval',
        minutes=1,
        kwargs={'bot': bot},
        id="price_monitor_job",
        replace_existing=True
    )

    return scheduler