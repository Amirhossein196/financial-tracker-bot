import aiohttp
import time
from typing import Dict, Any, Optional
from config import config

# کش در حافظه (In-Memory Cache) برای جلوگیری از اسپم درخواست‌ها
_cache: Dict[str, Any] = {}
_cache_expire_time: float = 0.0

async def fetch_nobitex_stats() -> Optional[Dict[str, Any]]:
    """
    دریافت قیمت تتر، بیت‌کوین، اتریوم و طلا با سیستم پشتیبان چندلایه
    """
    global _cache, _cache_expire_time

    # بازگرداندن داده‌های کش در صورت عدم انقضا
    if _cache and time.time() < _cache_expire_time:
        return _cache

    parsed_data = {}
    url = "https://api.wallex.ir/v1/markets"

    try:
        async with aiohttp.ClientSession() as session:
            # ۱. دریافت تتر، بیت‌کوین، اتریوم و توکن طلا (PAXG) از والکس
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        symbols = data.get("result", {}).get("symbols", {})

                        usdt_data = symbols.get("USDTTMN", {}).get("stats", {})
                        btc_data = symbols.get("BTCTMN", {}).get("stats", {})
                        eth_data = symbols.get("ETHTMN", {}).get("stats", {})
                        paxg_data = symbols.get("PAXGTMN", {}).get("stats", {})

                        parsed_data = {
                            "usd": {
                                "latest": int(float(usdt_data.get("lastPrice", 0))),
                                "change": float(usdt_data.get("24h_ch", 0)),
                            },
                            "btc": {
                                "latest": int(float(btc_data.get("lastPrice", 0))),
                                "change": float(btc_data.get("24h_ch", 0)),
                            },
                            "eth": {
                                "latest": int(float(eth_data.get("lastPrice", 0))),
                                "change": float(eth_data.get("24h_ch", 0)),
                            }
                        }

                        # لایه پشتیبان طلا: محاسبه قیمت ۱ گرم طلا ۱۸ عیار از توکن پکس‌گلد والکس
                        # ۱ اونس طلا = ۳۱.۱۰۳۵ گرم طلای ۲۴ عیار | عیار ۱۸ = ۷۵٪ خلوص
                        paxg_price = float(paxg_data.get("lastPrice", 0))
                        if paxg_price > 0:
                            gold_18k_from_paxg = int((paxg_price / 31.1034768) * 0.75)
                            parsed_data["gold"] = {
                                "latest": gold_18k_from_paxg,
                                "change": float(paxg_data.get("24h_ch", 0)),
                            }

            try:
                # تلاش برای گرفتن قیمت دقیق کف بازار طلا از وب‌سرویس عمومی بازار ایران
                gold_api_url = "https://brsapi.ir/FreeTsetmcBourseApi/Api_Free_Gold_Currency.json"
                async with session.get(gold_api_url, timeout=aiohttp.ClientTimeout(total=4)) as gold_resp:
                    if gold_resp.status == 200:
                        gold_json = await gold_resp.json()
                        for item in gold_json.get("gold", []):
                            # پیدا کردن آیتم طلای ۱۸ عیار
                            if "18" in item.get("name", "") or "طلا" in item.get("name", ""):
                                raw_price = int(item.get("price", 0))
                                # اگر قیمت به ریال بود، به تومان تبدیل می‌کنیم
                                price_in_toman = raw_price // 10 if raw_price > 30000000 else raw_price
                                if price_in_toman > 0:
                                    parsed_data["gold"] = {
                                        "latest": price_in_toman,
                                        "change": float(item.get("change_percent", 0)),
                                    }
                                    break
            except Exception as e:
                # اگر این وب‌سرویس در دسترس نبود، از همان لایه والکس که بالاتر پر شد استفاده می‌شود
                pass

            # اگر هر دوی این‌ها در شرایط خاصی خالی ماندند، با نرخ تتر محاسبه می‌کنیم
            if "gold" not in parsed_data and "usd" in parsed_data:
                usdt_price = parsed_data["usd"]["latest"]
                # تخمین دقیق بر مبنای انس جهانی استاندارد
                estimated_gold = int((2720 * usdt_price / 31.1034768) * 0.75)
                parsed_data["gold"] = {
                    "latest": estimated_gold,
                    "change": 0.0,
                }

            if parsed_data:
                _cache = parsed_data
                _cache_expire_time = time.time() + config.cache_ttl
                return parsed_data

    except Exception as e:
        print(f"Network error in price service: {e}")

    return _cache if _cache else None