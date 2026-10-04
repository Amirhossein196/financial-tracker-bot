from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData


# استفاده از این کلاس‌ها به جای رشته‌های متنی خام، جلوی باگ‌های تایپی را می‌گیرد
# و اطلاعات را به صورت ساختاریافته بین سرور و تلگرام رد و بدل می‌کند.

class MenuCallback(CallbackData, prefix="menu"):
    action: str


class AssetCallback(CallbackData, prefix="asset"):
    symbol: str
    action: str


class AlertConditionCallback(CallbackData, prefix="cond"):
    condition: str  # 'above' or 'below'


class AlertActionCallback(CallbackData, prefix="alrt"):
    alert_id: int
    action: str  # مثلا 'delete'


class HistoryActionCallback(CallbackData, prefix="hist"):
    action: str


def get_main_menu() -> InlineKeyboardMarkup:
    """
    ساخت کیبورد اصلی ربات که در زمان ارسال /start به کاربر نمایش داده می‌شود.
    """
    builder = InlineKeyboardBuilder()

    # اضافه کردن دکمه‌ها با استفاده از کلاس‌های کالبک
    builder.button(text="💰 استعلام قیمت لحظه‌ای", callback_data=MenuCallback(action="prices").pack())
    builder.button(text="🔔 ثبت هشدار قیمت", callback_data=MenuCallback(action="new_alert").pack())
    builder.button(text="📋 مدیریت هشدارهای من", callback_data=MenuCallback(action="my_alerts").pack())
    builder.button(text="🕒 تاریخچه استعلام‌های من", callback_data=MenuCallback(action="history").pack())

    # تنظیم چینش دکمه‌ها: ۲ تا بالا، ۲ تا پایین
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def get_assets_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    کیبورد انتخاب ارز. از این کیبورد هم برای "دیدن قیمت" و هم "ثبت هشدار" استفاده می‌کنیم.
    ورودی action مشخص می‌کند که بعد از انتخاب، چه اتفاقی بیفتد.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="💵 تتر (دلار آزاد)", callback_data=AssetCallback(symbol="usd", action=action).pack())
    builder.button(text="🪙 بیت‌کوین (BTC)", callback_data=AssetCallback(symbol="btc", action=action).pack())
    builder.button(text="💠 اتریوم (ETH)", callback_data=AssetCallback(symbol="eth", action=action).pack())
    builder.button(text="🥇 طلا ۱۸ عیار", callback_data=AssetCallback(symbol="gold", action=action).pack())

    builder.button(text="🔙 بازگشت به منو", callback_data=MenuCallback(action="main").pack())

    # چینش دکمه‌ها
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def get_price_message_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    کیبورد زیر پیام نمایش قیمت که دکمه به‌روزرسانی (رفرش) دارد.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 به‌روزرسانی قیمت", callback_data=AssetCallback(symbol=symbol, action="price_check").pack())
    builder.button(text="🔙 بازگشت به لیست ارزها", callback_data=MenuCallback(action="prices").pack())
    builder.adjust(1, 1)
    return builder.as_markup()


def get_history_keyboard() -> InlineKeyboardMarkup:
    """
    کیبورد زیر پیام تاریخچه برای امکان پاکسازی آن.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 پاک کردن تاریخچه", callback_data=HistoryActionCallback(action="clear").pack())
    builder.button(text="🏠 بازگشت به منوی اصلی", callback_data=MenuCallback(action="main").pack())
    builder.adjust(1, 1)
    return builder.as_markup()


def get_alert_conditions_keyboard() -> InlineKeyboardMarkup:
    """
    کیبورد انتخاب شرط هشدار (بالاتر از قیمت X یا پایین‌تر از قیمت X).
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="📈 بالاتر رفت", callback_data=AlertConditionCallback(condition="above").pack())
    builder.button(text="📉 پایین‌تر آمد", callback_data=AlertConditionCallback(condition="below").pack())
    builder.button(text="❌ انصراف", callback_data=MenuCallback(action="main").pack())

    builder.adjust(2, 1)
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    یک دکمه ساده برای انصراف از عملیات (مثلا وقتی ربات منتظر تایپ قیمت است).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ انصراف و بازگشت", callback_data=MenuCallback(action="main").pack())
    return builder.as_markup()
