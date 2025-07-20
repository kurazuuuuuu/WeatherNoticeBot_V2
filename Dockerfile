# Discord Weather Bot Dockerfile (マルチステージビルド)

# --- ステージ1: ビルダー ---
# このステージでは、依存関係をインストールした仮想環境を構築します。
FROM python:3.12-slim as builder

# 作業ディレクトリを設定
WORKDIR /app

# uvをインストール
RUN pip install uv

# 依存関係の定義ファイルのみをコピー
# これにより、依存関係に変更がない限り、この後のステップはキャッシュが利用されます
COPY pyproject.toml ./

# uvを使って仮想環境を/opt/venvに作成
# --systemオプションは、uvが管理するPythonではなく、ベースイメージのPythonを使うことを意味します
RUN uv pip install --system --no-cache -r pyproject.toml

# --- ステージ2: 最終イメージ ---
# このステージでは、ビルドツールや不要なファイルが含まれない、軽量な最終イメージが完成します。
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# ログとデータベースディレクトリを作成
RUN mkdir -p /app/logs /app/data

# 非rootユーザーを作成し、/app ディレクトリ全体の所有権をまとめて変更
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# ビルダーステージから、依存関係がインストールされた仮想環境をコピー
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

# アプリケーションコードをコピー
COPY . .

# ユーザーをbotuserに切り替える
USER botuser

# ボットを起動
# -m オプションでsrc.botをモジュールとして実行することで、Pythonのパス問題を解決します
CMD ["python", "-m", "src.bot"]
