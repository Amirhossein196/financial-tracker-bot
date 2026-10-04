<div align="center">

# 📊 Financial Market Tracker Bot

An asynchronous, modular, and production-grade Telegram bot developed in **Python** using **Aiogram 3**. Engineered to track real-time market quotes for 18K Gold, USD (Tether), Bitcoin, and Ethereum with persistent query logging, target price alerts, and automated background evaluations.

---

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Aiogram%203.x-2CA5E0.svg?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Database](https://img.shields.io/badge/database-SQLite%20(aiosqlite)-003B57.svg?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Concurrency](https://img.shields.io/badge/concurrency-asyncio%20%7C%20APScheduler-orange.svg)](#architecture)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## 📌 Project Overview

**Financial Market Tracker Bot** provides instant financial market data and threshold-based automated monitoring for currency and commodity traders. It is architected to handle rate-limiting, strict network firewalls, and network flakiness through an intelligent multi-layer fallback pipeline and in-memory TTL caching.

---

## ✨ Key Features

- **Real-Time Market Tracking:** Immediate pricing queries for 18K Gold (per gram), USDT/TMN, Bitcoin (BTC), and Ethereum (ETH).
- **Multi-Layer Resilient Fallback:** Automatically switches data retrieval pipelines to crypto-backed commodities (PAXG/TMN) when public gold scrapers encounter rate-limits or IP bans.
- **Automated Price Alerts:** Configure custom threshold targets (`above` or `below` baseline prices) via an interactive Finite State Machine (FSM).
- **Concurrent Task Scheduling:** Managed by `APScheduler` to periodically poll active market feeds and concurrently dispatch notifications without blocking user interactions.
- **In-Memory TTL Caching:** Minimizes external API overhead, mitigates redundant I/O requests, and secures against sudden upstream rate limits.
- **Query History & Localization:** Maintains an async SQLite history log with inline management (view/clear) and timestamps mapped to Iran Standard Time (`jdatetime`).
- **High Concurrency Database:** Employs **Write-Ahead Logging (WAL)** mode in `aiosqlite` for non-blocking concurrent read/write operations.

---

## 🏗 System Architecture

The project follows a clean, modular structure isolating domain logic, infrastructure layers, and presentation handlers:

```text
financial_tracker_bot/
├── bot/
│   ├── handlers/          # Interaction routers (common, alerts, errors)
│   ├── keyboards/         # Inline keyboard layouts and CallbackData schemas
│   └── states/            # FSM models governing multi-step user prompts
├── database/              # Async database operations, connection pool, migrations
├── services/              # Price providers, fallbacks, and scraping routines
├── config.py              # Centralized environment variable validation (pydantic-settings)
├── main.py                # Bot lifecycle, router mounting, and scheduler dispatch
├── requirements.txt       # Production dependencies
└── README.md
