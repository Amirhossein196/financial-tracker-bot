# Financial Market Tracker Bot

An asynchronous, modular Telegram bot built with Python 3 and Aiogram 3 to track real-time prices for 18K Gold, USD (Tether), Bitcoin, and Ethereum. Features target price alerts, background job scheduling, and user query logs.

## Features

- Real-Time Market Data: Instant prices for 18K Gold, USDT, BTC, and ETH.
- Multi-Layer Fallback: Automated failover to crypto-backed gold assets (PAXG) if primary web scrapers are rate-limited.
- Custom Price Alerts: Threshold alerts (above/below target price) handled via Aiogram FSM.
- Task Scheduler: Automated background checks and non-blocking notifications powered by APScheduler.
- In-Memory Caching: TTL cache to prevent redundant requests and reduce external API limits.
- Query History: SQLite-backed query tracking localized with Persian Solar calendar (jdatetime) and Iran Standard Time.
- Concurrency Safe: Uses SQLite Write-Ahead Logging (WAL) mode for parallel operations.

## Architecture

financial_tracker_bot/
│
├── .env
├── requirements.txt
├── config.py
├── main.py
│
├── bot/
│   ├── __init__.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   └── alerts.py
│   └── keyboards/
│       ├── __init__.py
│       └── inline.py
│
├── database/
│   ├── __init__.py
│   └── db.py
│
└── services/
    ├── __init__.py
    ├── price_service.py
    └── scheduler.py
    
## Tech Stack

- Python 3.10+
- Aiogram 3
- aiosqlite (Async SQLite with WAL)
- APScheduler
- aiohttp
- jdatetime

## Getting Started

1. Clone the repository:
git clone https://github.com/Amirhossein196/financial-tracker-bot.git
cd financial-tracker-bot

2. Create and activate a virtual environment:
python -m venv .venv
source .venv/bin/activate

3. Install dependencies:
pip install -r requirements.txt

4. Configure environment variables in a .env file:
BOT_TOKEN=your_telegram_bot_token_here
CACHE_TTL=60

5. Run the bot:
python main.py

## Author

- GitHub: @Amirhossein196

## License

This project is licensed under the MIT License.
