#!/bin/bash

# Cron実行用のラッパースクリプト
# 環境変数、パス、カレントディレクトリを明示的に設定

# ログディレクトリとファイル
LOG_DIR="/home/ubuntu/operations/mochi-bot-twitter/.log"
CRON_LOG="$LOG_DIR/cron_$(date +\%Y-\%m-\%d).log"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 実行開始ログ
echo "========================================" >> "$CRON_LOG" 2>&1
echo "Cron execution started at $(date)" >> "$CRON_LOG" 2>&1
echo "========================================" >> "$CRON_LOG" 2>&1

# カレントディレクトリを変更
cd /home/ubuntu/operations/mochi-bot-twitter || {
    echo "ERROR: Failed to change directory" >> "$CRON_LOG" 2>&1
    exit 1
}

# .envファイルが存在するか確認
if [ ! -f .env ]; then
    echo "ERROR: .env file not found" >> "$CRON_LOG" 2>&1
    exit 1
fi

# 仮想環境のPythonを使用してmain.pyを実行
# nomoltbook: Moltbookアカウント問題が解決するまで無効化 (2026-02-12)
/home/ubuntu/operations/mochi-bot-twitter/venv/bin/python3 /home/ubuntu/operations/mochi-bot-twitter/main.py nomoltbook >> "$CRON_LOG" 2>&1

# 実行結果を記録
EXIT_CODE=$?
echo "========================================" >> "$CRON_LOG" 2>&1
echo "Cron execution finished at $(date)" >> "$CRON_LOG" 2>&1
echo "Exit code: $EXIT_CODE" >> "$CRON_LOG" 2>&1
echo "========================================" >> "$CRON_LOG" 2>&1

exit $EXIT_CODE
