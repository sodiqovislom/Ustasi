#!/usr/bin/env bash
set -o errexit

# 1. Telegram Botni fonda ishga tushirish (agar to'xtasa avto-restart bo'ladi)
(
    while true; do
        echo "========================================="
        echo "Ustasi Telegram Bot fonda ishga tushmoqda..."
        echo "========================================="
        python bot.py || true
        echo "Telegram bot to'xtadi. 5 soniyadan so'ng qayta ishga tushiriladi..."
        sleep 5
    done
) &

# 2. Gunicorn asosiy veb-serverini ishga tushirish
PORT="${PORT:-8000}"
echo "Gunicorn ishga tushmoqda: port $PORT"
exec gunicorn ustasi_core.wsgi:application --bind "0.0.0.0:$PORT" --workers 2 --timeout 120
