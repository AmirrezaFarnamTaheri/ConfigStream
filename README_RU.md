# ConfigStream — Отказоустойчивая платформа агрегации и валидации прокси

[![Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml)
[![CI](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml)
[![Pages Deploy](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml)

**[English](README.md) • [فارسی](README_FA.md) • [简体中文](README_ZH.md) • [Русский](README_RU.md)**

ConfigStream — это независимая платформа для автоматического сбора, многоуровневой проверки, очистки и дистрибуции прокси-конфигураций в условиях жесткой интернет-цензуры и сетевых блокировок.

---

## 🚀 Ссылки на подписки (автообновление каждые 15 минут)

Все потоки содержат встроенные метаданные заголовков (`#profile-title`, `#profile-update-interval`, `#subscription-userinfo`) и стандартную Base64 кодировку:

| Категория / Профиль | Формат URI (текст) | Подписка Base64 | Рекомендуемые клиенты |
| :--- | :--- | :--- | :--- |
| **Все узлы (All)** | [`configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/configs.txt) | [`configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/configs_base64.txt) | Все клиенты |
| **Проверенные и стабильные (Verified)** | [`verified/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/verified/configs.txt) | [`verified/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/verified/configs_base64.txt) | Hiddify, v2rayNG, Streisand |
| **Быстрые с низким пингом (Fast)** | [`fast/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/fast/configs.txt) | [`fast/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/fast/configs_base64.txt) | Онлайн-звонки, игры (< 800ms) |
| **Безопасные с PFS (Secure)** | [`secure/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/secure/configs.txt) | [`secure/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/secure/configs_base64.txt) | Reality, Hysteria2, TUIC |
| **Топ 100 узлов (Top 100)** | [`top100.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/top100.txt) | — | Быстрый выбор |

### Конфигурации для продвинутых клиентов (Clash / Sing-box)
- **Конфигурация Clash / Mihomo:** `https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/clash.yaml`
- **Конфигурация Sing-box (v1.13+):** `https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/singbox.json`

---

## 🛡 Многоуровневый каскад верификации

1. **Уровень L0/L1 (Синтаксическая фильтрация и дедупликация):**
   - Устранение дубликатов по ключу `(Host, Port, Protocol, UUID)`.
   - Проверка спецификации UUID (стандартный 36-значный, компактный 32-значный hex, пользовательские строки Xray < 30 байт).
   - Защита от SSRF (исключение приватных IP-адресов и служебных портов).
2. **Уровень L2 (Асинхронный TCP Handshake и DNS):**
   - Предварительное разрешение DNS через пул из 64 потоков во избежание блокировки event loop.
   - Ограничение конкурентности до 800 открытых сокетов (защита от лимитов `EMFILE`).
3. **Уровень L3 (Реальный тест передачи данных):**
   - Измерение реального HTTP 204 отклика через нативный встроенный движок Go.
   - Фильтрация нестабильных серверов по медианной задержке нескольких раундов.
4. **Уровень восстановления (Washer & Chains):**
   - Оборачивание заблокированных серверов в туннели Cloudflare WARP/Masque.

---

## 📱 Инструкция по настройке клиентов

### 1. Hiddify (Android, Windows, macOS, Linux, iOS)
1. Скопируйте ссылку на Base64 или Singbox подписку.
2. В приложении нажмите **+ (Новый профиль)** $\rightarrow$ **Добавить из буфера обмена**.

### 2. v2rayNG / v2rayN / Streisand / Shadowrocket
1. Скопируйте ссылку Base64.
2. В настройках подписок добавьте URL и нажмите **Обновить подписку**.

### 3. Clash Verge Rev / Mihomo Party
1. Перейдите в раздел **Profiles**.
2. Вставьте ссылку на `clash.yaml` в поле URL и нажмите **Import**.

---

## 🛠️ Локальный запуск и разработка

```bash
# Клонирование репозитория
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream

# Установка зависимостей
pip install -r requirements-dev.txt
pip install -e . --no-deps

# Запуск конвейера агрегации
python -m configstream.cli merge --sources sources/batch_1.txt --output output/

# Запуск тестов
pytest tests/unit/
```

---

## 📜 Лицензия
Проект распространяется под свободной лицензией **AGPL-3.0-or-later**.
