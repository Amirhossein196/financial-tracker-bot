from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline import (
    MenuCallback,
    AssetCallback,
    AlertConditionCallback,
    AlertActionCallback,
    get_assets_keyboard,
    get_alert_conditions_keyboard,
    get_cancel_keyboard,
    get_main_menu
)
from database.db import add_alert, get_user_alerts, delete_alert

router = Router()

# نگاشت نام‌های زیبا برای نمایش
ASSET_NAMES = {"usd": "تتر", "btc": "بیت‌کوین", "eth": "اتریوم"}
COND_NAMES = {"above": "بالاتر 📈", "below": "پایین‌تر 📉"}


class AlertState(StatesGroup):
    waiting_for_asset = State()
    waiting_for_condition = State()
    waiting_for_price = State()


@router.callback_query(MenuCallback.filter(F.action == "new_alert"))
async def new_alert_start(callback: CallbackQuery, state: FSMContext):
    """
    وقتی کاربر دکمه 'ثبت هشدار' را از منوی اصلی می‌زند.
    """
    await state.clear()  # پاک کردن State های قبلی برای اطمینان
    text = "🔔 <b>ثبت هشدار قیمت جدید</b>\n\nابتدا ارز مورد نظر خود را انتخاب کنید:"

    # اکشن set_alert را می‌فرستیم تا کیبورد بداند هدف ثبت هشدار است
    await callback.message.edit_text(
        text=text,
        reply_markup=get_assets_keyboard(action="set_alert"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(AssetCallback.filter(F.action == "set_alert"))
async def process_alert_asset(callback: CallbackQuery, callback_data: AssetCallback, state: FSMContext):
    """
    کاربر ارز را انتخاب کرده، حالا می‌پرسیم قیمت بالاتر رفت خبر دهم یا پایین‌تر؟
    """
    # ذخیره ارز انتخاب شده در حافظه موقت (FSM Memory)
    await state.update_data(asset=callback_data.symbol)

    asset_name = ASSET_NAMES.get(callback_data.symbol, callback_data.symbol)
    text = (
        f"انتخاب شما: <b>{asset_name}</b>\n\n"
        f"به من بگویید می‌خواهید اگر قیمت از چه حدی <b>بالاتر</b> رفت یا <b>پایین‌تر</b> آمد به شما اطلاع دهم؟"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_alert_conditions_keyboard(),
        parse_mode="HTML"
    )
    # تنظیم وضعیت به انتظار برای دریافت شرط
    await state.set_state(AlertState.waiting_for_condition)
    await callback.answer()


@router.callback_query(AlertConditionCallback.filter(), AlertState.waiting_for_condition)
async def process_alert_condition(callback: CallbackQuery, callback_data: AlertConditionCallback, state: FSMContext):
    """
    کاربر شرط (بالا یا پایین) را انتخاب کرده. حالا ربات منتظر تایپ قیمت است.
    """
    await state.update_data(condition=callback_data.condition)

    # واکشی داده‌ها از FSM برای نمایش به کاربر
    data = await state.get_data()
    asset_name = ASSET_NAMES.get(data['asset'], data['asset'])
    cond_text = "بیشتر" if callback_data.condition == "above" else "کمتر"

    text = (
        f"تنظیم هشدار برای <b>{asset_name}</b> در صورت رفتن به <b>{cond_text}</b> از قیمت دلخواه شما.\n\n"
        f"✍️ <i>لطفاً قیمت مورد نظر خود را (به تومان و به صورت عدد انگلیسی) در چت ارسال کنید:</i>\n\n"
        f"مثال: <code>65000</code>"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    # تنظیم وضعیت به دریافت قیمت متنی
    await state.set_state(AlertState.waiting_for_price)
    await callback.answer()


@router.message(AlertState.waiting_for_price)
async def process_alert_price(message: Message, state: FSMContext):
    """
    گرفتن قیمت وارد شده، بررسی صحت آن و ثبت نهایی در دیتابیس.
    """
    # بررسی اینکه کاربر واقعا عدد وارد کرده باشد
    try:
        # حذف ویرگول‌های احتمالی در صورت تایپ کاربر
        clean_price_str = message.text.replace(",", "").strip()
        target_price = float(clean_price_str)
        if target_price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ لطفاً فقط یک عدد معتبر وارد کنید (مثلا 65000).\nدوباره تلاش کنید:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # واکشی داده‌های قبلی از State
    data = await state.get_data()
    asset = data['asset']
    condition = data['condition']

    # ثبت در دیتابیس
    success = await add_alert(
        user_id=message.from_user.id,
        asset=asset,
        target_price=target_price,
        condition=condition
    )

    # خروج از ماشین وضعیت
    await state.clear()

    if success:
        asset_name = ASSET_NAMES.get(asset, asset)
        cond_text = "بالاتر 📈" if condition == "above" else "پایین‌تر 📉"

        success_text = (
            f"✅ <b>هشدار با موفقیت ثبت شد!</b>\n\n"
            f"📌 ارز: {asset_name}\n"
            f"🎯 هدف: {cond_text} از <code>{target_price:,}</code> تومان\n\n"
            f"هر زمان که قیمت به این محدوده برسد، به شما پیام خواهم داد."
        )
        await message.answer(text=success_text, reply_markup=get_main_menu(), parse_mode="HTML")
    else:
        await message.answer(
            "❌ متاسفانه در ثبت هشدار مشکلی پیش آمد. لطفا دوباره تلاش کنید.",
            reply_markup=get_main_menu()
        )


@router.callback_query(MenuCallback.filter(F.action == "my_alerts"))
async def show_my_alerts(callback: CallbackQuery):
    """
    نمایش تمام هشدارهای فعال و غیرفعال کاربر.
    """
    alerts = await get_user_alerts(callback.from_user.id)

    if not alerts:
        await callback.message.edit_text(
            "🤷‍♂️ شما هیچ هشداری ثبت نکرده‌اید.",
            reply_markup=get_main_menu()
        )
        return

    text = "📋 <b>لیست هشدارهای شما:</b>\n\n"
    builder = InlineKeyboardBuilder()

    # تولید پویای متن و دکمه حذف برای هر هشدار
    for index, alert in enumerate(alerts, start=1):
        asset_name = ASSET_NAMES.get(alert['asset'], alert['asset'])
        cond_name = COND_NAMES.get(alert['condition'], alert['condition'])
        status = "🟢 فعال" if alert['is_active'] else "⚪️ غیرفعال (انجام شده)"

        text += (
            f"<b>{index}.</b> {asset_name} | {cond_name} <code>{alert['target_price']:,}</code>\n"
            f"وضعیت: {status}\n"
            f"➖➖➖➖➖➖\n"
        )

        # دکمه حذف برای هر ردیف
        builder.button(
            text=f"❌ حذف هشدار {index}",
            callback_data=AlertActionCallback(alert_id=alert['id'], action="delete").pack()
        )

    # دکمه بازگشت به منو
    builder.button(text="🏠 بازگشت به منوی اصلی", callback_data=MenuCallback(action="main").pack())
    builder.adjust(1)  # همه دکمه‌ها زیر هم قرار بگیرند

    await callback.message.edit_text(text=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AlertActionCallback.filter(F.action == "delete"))
async def handle_delete_alert(callback: CallbackQuery, callback_data: AlertActionCallback):
    """
    مدیریت کلیک روی دکمه حذف یک هشدار مشخص.
    """
    success = await delete_alert(alert_id=callback_data.alert_id, user_id=callback.from_user.id)

    if success:
        await callback.answer("✅ هشدار با موفقیت حذف شد.", show_alert=True)
        # فراخوانی مجدد تابع نمایش هشدارها برای رفرش شدن لیست
        await show_my_alerts(callback)
    else:
        await callback.answer("❌ خطا در حذف هشدار! شاید قبلاً حذف شده باشد.", show_alert=True)