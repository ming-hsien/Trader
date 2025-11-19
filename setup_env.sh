#!/usr/bin/env bash

# """ 
# run "source setup_env.sh" to setup and activate conda env 
# """

set -euo pipefail  # Exit on error, undefined variable, or pipe failure

# === 可以依需求修改的參數 ===
ENV_NAME="trade"            # conda 環境名稱
PYTHON_VERSION="3.12"       # 建環境時的 Python 版本
REQ_FILE="requirements.txt" # 要安裝的 requirements 檔案

# === 初始化 conda（讓 conda activate 在 bash 裡可用） ===
if ! command -v conda &>/dev/null; then
  echo "[ERROR] conda 指令不存在，請先安裝 Anaconda 或 Miniconda。"
  exit 1
fi

# 這一行會載入 conda 的 shell hook（比寫死 path 安全）
eval "$(conda shell.bash hook)"

# === 檢查環境是否已存在 ===
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "[INFO] Conda env '$ENV_NAME' 已存在。"
else
  echo "[INFO] 找不到 env '$ENV_NAME'，正在建立..."
  conda create -y -n "$ENV_NAME" "python=${PYTHON_VERSION}"
fi

# === 安裝 requirements ===
if [[ -f "$REQ_FILE" ]]; then
  echo "[INFO] 在 '$ENV_NAME' 裡安裝套件..."
  conda run -n "$ENV_NAME" pip install -r "$REQ_FILE"
fi

# === 啟動環境 ===
echo "[INFO] 啟動 env '$ENV_NAME'..."
conda activate "$ENV_NAME"

# python run_trade_bot.py
