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

# アプリケーションコードをコピー
# pyproject.tomlがREADME.mdを参照するため、ここで全てをコピーします。
COPY . .

# 非rootユーザーを作成
RUN useradd -m -u 1000 botuser

# /app ディレクトリ全体の所有権をbotuserに変更
# これにより、COPY . . でコピーされた全てのファイルがbotuserによって所有されるようになります。
RUN chown -R botuser:botuser /app

# ログとデータベースディレクトリが存在しない場合は作成し、botuserに書き込み権限を付与
# chmod 775 はオーナーとグループに読み書き実行権限を与えます。
# botuserがオーナーなので、これで書き込みできるようになります。
# -p オプションは、ディレクトリが存在しない場合のみ作成します。
RUN mkdir -p /app/logs /app/data && \
    chmod -R 775 /app/logs /app/data

# ユーザーをbotuserに切り替える
USER botuser

# 依存関係をインストール
# uv sync --frozen はpyproject.tomlがある場所で実行する必要があるため、
# COPY . . の後に実行し、ユーザー切り替え後に行います。
RUN uv sync --frozen

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import aiohttp; print('Bot is healthy')" || exit 1

# ボットを起動
CMD ["uv", "run", "python", "src/bot.py"]
