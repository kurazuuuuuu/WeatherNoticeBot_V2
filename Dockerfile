# Discord Weather Bot Dockerfile
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール
RUN pip install uv

# アプリケーションコードをコピー（pyproject.tomlがREADME.mdを参照するため）
COPY . .

# 依存関係をインストール
RUN uv sync --frozen

# データベースディレクトリを作成
RUN mkdir -p /app/data

# ログディレクトリを作成
RUN mkdir -p /app/logs

# 非rootユーザーを作成してディレクトリの所有権を変更
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app && \
    chmod -R 755 /app/logs /app/data

USER botuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import aiohttp; print('Bot is healthy')" || exit 1

# ボットを起動
CMD ["uv", "run", "python", "src/bot.py"]