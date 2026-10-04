from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import jdatetime

# وارد کردن کلاس‌های کیبورد و توابع سازنده کیبورد
from bot.keyboards.inline import (
    get_main_menu,
    get_assets_keyboard,
    get_price_message_keyboard,
    get_history_keyboard,
    MenuCallback,
    AssetCallback,
    HistoryActionCallback
)

# وارد کردن توابع دیتابیس
from database.db import add_price_history, get_user_history, clear_user_history
# وارد کردن سرویس قیمت‌ها
from services.price_service import fetch_nobitex_stats

router = Router()

# نگاشت نام‌های انگلیسی به فارسی برای نمایش زیباتر
ASSET_NAMES = {
    "usd": "تتر (دلار آزاد) 💵",
    "btc": "بیت‌کوین (BTC) 🪙",
    "eth": "اتریوم (ETH) 💠",
    "gold": "طلا ۱۸ عیار (گرم) 🥇"
}


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    پاسخ به دستور /start و نمایش منوی اصلی به کاربر.
    """
    welcome_text = (
        "<b>به ربات هوشمند دستیار مالی خوش آمدید! 📊</b>\n\n"
        "این ربات به شما کمک می‌کند تا قیمت لحظه‌ای ارزها را رصد کنید و "
        "در صورت تغییرات مهم، هشدار دریافت نمایید.\n\n"
        "👇 <i>لطفاً از منوی زیر یک گزینه را انتخاب کنید:</i>"
    )
    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(MenuCallback.filter(F.action == "main"))
async def back_to_main_menu(callback: CallbackQuery):
    """
    مدیریت دکمه بازگشت به منوی اصلی از صفحات مختلف.
    """
    text = "🏠 <b>منوی اصلی:</b>\nلطفاً یک گزینه را انتخاب کنید:"
    # ویرایش پیام قبلی به جای ارسال پیام جدید (جلوگیری از شلوغ شدن چت)
    await callback.message.edit_text(
        text=text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    # بستن پاپ‌آپ لودینگ دکمه شیشه‌ای
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "prices"))
async def show_price_menu(callback: CallbackQuery):
    """
    نمایش لیست ارزها وقتی کاربر روی 'استعلام قیمت لحظه‌ای' کلیک می‌کند.
    """
    text = "💰 <b>استعلام قیمت لحظه‌ای</b>\n\nلطفاً ارز مورد نظر خود را برای مشاهده قیمت انتخاب کنید:"

    # اینجا اکشن را 'price_check' می‌فرستیم تا کیبورد بداند هدف دیدن قیمت است نه ثبت هشدار
    await callback.message.edit_text(
        text=text,
        reply_markup=get_assets_keyboard(action="price_check"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(AssetCallback.filter(F.action == "price_check"))
async def check_asset_price(callback: CallbackQuery, callback_data: AssetCallback):
    """
    زمانی که کاربر روی یک ارز خاص کلیک می‌کند، قیمت لحظه‌ای را از API می‌‌‌‌گیرد و نمایش می‌دهد.
    """
    # نمایش لودینگ کوتاه به کاربر
    await callback.answer("در حال دریافت جدیدترین قیمت‌ها... ⏳")

    # فراخوانی سرویس قیمت (که کشینگ داخلی دارد)
    stats = await fetch_nobitex_stats()

    if not stats:
        await callback.message.edit_text(
            "❌ متاسفانه در ارتباط با سرور قیمت‌ها مشکلی رخ داده است. لطفاً چند دقیقه دیگر تلاش کنید.",
            reply_markup=get_main_menu()
        )
        return

    symbol = callback_data.symbol
    if symbol not in stats:
        await callback.message.edit_text(
            "❌ اطلاعات این ارز در حال حاضر در دسترس نیست.",
            reply_markup=get_main_menu()
        )
        return

    asset_data = stats[symbol]
    asset_name_fa = ASSET_NAMES.get(symbol, symbol.upper())

    latest_price_int = asset_data['latest']

    # ۱. ثبت در دیتابیس تاریخچه
    await add_price_history(
        user_id=callback.from_user.id,
        asset=symbol,
        price=latest_price_int
    )

    # ۲. تولید تاریخ و ساعت به وقت تهران
    now = jdatetime.datetime.now()
    iran_time_str = now.strftime("%Y/%m/%d - %H:%M:%S")

    # جدا کردن سه رقم سه رقم اعداد برای خوانایی بهتر با f-string format
    latest_price = f"{latest_price_int:,}"
    change = asset_data.get('change', 0)

    # تعیین ایموجی تغییر قیمت (سبز برای سود، قرمز برای ضرر)
    trend_emoji = "🟢" if change >= 0 else "🔴"

    # ساخت متن نهایی با دیزاین زیبا
    result_text = (
        f"📊 <b>نرخ لحظه‌ای {asset_name_fa}</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"قیمت فعلی: <code>{latest_price}</code> تومان\n"
    )

    # اگر تغییرات داشتیم (برای ارزها)، نمایش دهیم
    if change != 0:
        result_text += f"تغییرات ۲۴ ساعته: % {change} {trend_emoji}\n"

    # اضافه کردن بالاترین و پایین‌ترین قیمت اگر در داده‌ها موجود باشد (مثل تتر)
    if 'high' in asset_data and 'low' in asset_data:
        high_price = f"{asset_data['high']:,}"
        low_price = f"{asset_data['low']:,}"
        result_text += (
            f"بیشترین در روز: <code>{high_price}</code> تومان\n"
            f"کمترین در روز: <code>{low_price}</code> تومان\n"
        )

    result_text += f"➖➖➖➖➖➖➖➖➖➖\n🕒 <i>تاریخ استعلام: {iran_time_str}</i>"

    # اضافه کردن دکمه بازگشت و دکمه رفرش به زیر پیام قیمت
    await callback.message.edit_text(
        text=result_text,
        reply_markup=get_price_message_keyboard(symbol),
        parse_mode="HTML"
    )


@router.callback_query(MenuCallback.filter(F.action == "history"))
async def show_query_history(callback: CallbackQuery):
    """
    نمایش ۵ استعلام آخر کاربر از دیتابیس
    """
    history_records = await get_user_history(callback.from_user.id)

    if not history_records:
        await callback.message.edit_text(
            "🤷‍♂️ شما تا به حال هیچ استعلام قیمتی نداشته‌اید.",
            reply_markup=get_main_menu()
        )
        return

    text = "🕒 <b>تاریخچه استعلام‌های اخیر شما:</b>\n\n"

    for record in history_records:
        asset_name = ASSET_NAMES.get(record['asset'], record['asset'])
        price_str = f"{int(record['price']):,}"

        # استخراج ساعت و تاریخ از دیتابیس و تبدیل به تاریخ شمسی
        try:
            # دیتابیس زمان را به صورت 'YYYY-MM-DD HH:MM:SS' ذخیره می‌کند
            dt_obj = datetime.strptime(record['checked_at'], "%Y-%m-%d %H:%M:%S")
            jdate = jdatetime.datetime.fromgregorian(datetime=dt_obj)
            date_str = jdate.strftime("%Y/%m/%d - %H:%M:%S")
        except Exception:
            date_str = record['checked_at']

        text += (
            f"🔹 <b>{asset_name}</b>: <code>{price_str}</code> تومان\n"
            f"⏱ <i>زمان استعلام: {date_str}</i>\n"
            f"➖➖➖➖➖➖\n"
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_history_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(HistoryActionCallback.filter(F.action == "clear"))
async def clear_history_handler(callback: CallbackQuery):
    """
    هندلر دکمه پاک کردن تاریخچه
    """
    success = await clear_user_history(callback.from_user.id)
    if success:
        await callback.answer("✅ تاریخچه شما با موفقیت پاک شد.", show_alert=True)
        await callback.message.edit_text(
            text="🏠 <b>منوی اصلی:</b>\nلطفاً یک گزینه را انتخاب کنید:",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ در پاک کردن تاریخچه مشکلی پیش آمد.", show_alert=True)

