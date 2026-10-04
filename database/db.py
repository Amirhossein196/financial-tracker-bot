import aiosqlite
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# تنظیمات لاگینگ برای ثبت خطاهای احتمالی دیتابیس
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# نام و مسیر فایل دیتابیس
DB_PATH = "tracker.db"


@asynccontextmanager
async def get_db_connection():
    """
    ایجاد اتصال امن و بهینه به دیتابیس.
    تبدیل شده به مدیر محتوای ناهمگام (Async Context Manager) برای جلوگیری از خطای هم‌زمانی.
    """
    conn = await aiosqlite.connect(DB_PATH, timeout=10.0)
    try:
        # فعال‌سازی حالت WAL برای پرفورمنس بسیار بالا در عملیات همزمان
        await conn.execute("PRAGMA journal_mode=WAL;")
        # فعال‌سازی کلیدهای خارجی
        await conn.execute("PRAGMA foreign_keys=ON;")
        # دسترسی به ستون‌ها با نام (مثل دیکشنری)
        conn.row_factory = aiosqlite.Row
        yield conn
    finally:
        # همیشه پس از اتمام کار، اتصال به صورت خودکار و امن بسته می‌شود
        await conn.close()


async def init_db():
    """
    ساخت جداول اولیه و ایندکس‌های دیتابیس.
    """
    try:
        async with get_db_connection() as db:
            # ایجاد جدول هشدارها
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS alerts
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 user_id
                                 INTEGER
                                 NOT
                                 NULL,
                                 asset
                                 TEXT
                                 NOT
                                 NULL,
                                 target_price
                                 REAL
                                 NOT
                                 NULL,
                                 condition
                                 TEXT
                                 NOT
                                 NULL
                                 CHECK (
                                 condition
                                 IN
                             (
                                 'above',
                                 'below'
                             )),
                                 is_active BOOLEAN NOT NULL DEFAULT 1,
                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                 )
                             """)

            # ایجاد جدول تاریخچه قیمت‌ها
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS price_history
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 user_id
                                 INTEGER
                                 NOT
                                 NULL,
                                 asset
                                 TEXT
                                 NOT
                                 NULL,
                                 price
                                 REAL
                                 NOT
                                 NULL,
                                 checked_at
                                 TIMESTAMP
                                 DEFAULT (
                                 datetime
                             (
                                 'now',
                                 'localtime'
                             ))
                                 )
                             """)

            # ایجاد ایندکس‌ها برای افزایش سرعت جستجو
            await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_is_active ON alerts(is_active);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_history_user_id ON price_history(user_id);")

            await db.commit()
            logger.info("Database initialized successfully with WAL mode and Indexes.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def add_alert(user_id: int, asset: str, target_price: float, condition: str) -> bool:
    """
    ثبت یک هشدار قیمت جدید برای کاربر.
    """
    try:
        async with get_db_connection() as db:
            await db.execute(
                "INSERT INTO alerts (user_id, asset, target_price, condition) VALUES (?, ?, ?, ?)",
                (user_id, asset, target_price, condition)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error adding alert for user {user_id}: {e}")
        return False


async def get_active_alerts() -> List[Dict[str, Any]]:
    """
    دریافت تمام هشدارهای فعال برای سیستم مانیتورینگ پس‌زمینه.
    """
    try:
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM alerts WHERE is_active = 1")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching active alerts: {e}")
        return []


async def get_user_alerts(user_id: int) -> List[Dict[str, Any]]:
    """
    دریافت لیست تمام هشدارهای یک کاربر.
    """
    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching alerts for user {user_id}: {e}")
        return []


async def deactivate_alert(alert_id: int) -> bool:
    """
    غیرفعال کردن یک هشدار (پس از رسیدن قیمت به هدف).
    """
    try:
        async with get_db_connection() as db:
            await db.execute("UPDATE alerts SET is_active = 0 WHERE id = ?", (alert_id,))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error deactivating alert {alert_id}: {e}")
        return False


async def delete_alert(alert_id: int, user_id: int) -> bool:
    """
    حذف دائمی یک هشدار توسط خود کاربر (جهت امنیت، user_id هم چک می‌شود).
    """
    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                "DELETE FROM alerts WHERE id = ? AND user_id = ?",
                (alert_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {e}")
        return False


async def add_price_history(user_id: int, asset: str, price: float) -> bool:
    """
    ثبت یک رکورد در تاریخچه استعلام‌های کاربر.
    """
    try:
        async with get_db_connection() as db:
            await db.execute(
                "INSERT INTO price_history (user_id, asset, price) VALUES (?, ?, ?)",
                (user_id, asset, price)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error adding history for user {user_id}: {e}")
        return False


async def get_user_history(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    دریافت ۵ استعلام آخر کاربر.
    """
    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM price_history WHERE user_id = ? ORDER BY checked_at DESC LIMIT ?",
                (user_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching history for user {user_id}: {e}")
        return []


async def clear_user_history(user_id: int) -> bool:
    """
    پاک کردن کل تاریخچه استعلام‌های یک کاربر.
    """
    try:
        async with get_db_connection() as db:
            await db.execute("DELETE FROM price_history WHERE user_id = ?", (user_id,))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error clearing history for user {user_id}: {e}")
        return False