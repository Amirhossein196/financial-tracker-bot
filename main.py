import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# وارد کردن تنظیمات و ماژول‌هایی که در مراحل قبل ساختیم
from config import config
from database.db import init_db
from bot.handlers.common import router as common_router
from bot.handlers.alerts import router as alerts_router
from services.scheduler import setup_scheduler

# تنظیم لاگینگ برای اینکه بفهمیم در پشت صحنه چه می‌گذرد و ارورها را ببینیم
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    """
    این تابع اصلی برنامه است که تمام اجزا را راه‌اندازی و به هم متصل می‌کند.
    """
    logger.info("Initializing the Financial Tracker Bot...")

    # ۱. راه‌‌اندازی ربات با توکنی که از فایل env خوانده شده
    # تنظیم ParseMode.HTML باعث می‌شود در کل پروژه نیازی نباشد مدام نوع متن را مشخص کنیم
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # ۲. راه‌اندازی Dispatcher (مغز متفکر مسیریابی پیام‌های تلگرام)
    dp = Dispatcher()

    # ۳. متصل کردن روترها (Handlers) به دیسپچر
    dp.include_router(common_router)
    dp.include_router(alerts_router)

    # ۴. راه‌اندازی دیتابیس (ساخت جداول و ایندکس‌ها در صورت عدم وجود)
    logger.info("Connecting to Database...")
    await init_db()

    # ۵. راه‌اندازی و استارت سیستم مانیتورینگ پس‌زمینه (Scheduler)
    logger.info("Starting background scheduler...")
    scheduler = setup_scheduler(bot)
    scheduler.start()

    # ۶. پاک کردن آپدیت‌های قدیمی (جلوگیری از اسپم شدن ربات با پیام‌های زمان خاموشی)
    await bot.delete_webhook(drop_pending_updates=True)

    # ۷. روشن کردن ربات و شروع به گوش دادن برای پیام‌های جدید
    logger.info("Bot is up and running! 🚀")
    try:
        await dp.start_polling(bot)
    finally:
        # در صورت خاموش شدن ربات، ارتباط با سرور تلگرام به درستی بسته شود
        await bot.session.close()


if __name__ == "__main__":
    try:
        # اجرای تابع ناهمگام اصلی در Event Loop
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # مدیریت خروج امن با فشردن کلیدهای Ctrl+C در ترمینال
        logger.info("Bot stopped gracefully.")