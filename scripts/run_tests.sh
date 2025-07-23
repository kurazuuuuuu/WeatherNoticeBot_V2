#!/bin/bash

# Discord Weather Bot テスト実行スクリプト

set -e

echo "=== Discord Weather Bot テスト実行 ==="

# 仮想環境の確認
if [ ! -d ".venv" ]; then
    echo "仮想環境が見つかりません。uvを使用してセットアップしてください。"
    echo "実行: uv sync --dev"
    exit 1
fi

# 環境変数の設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# テストタイプの選択
TEST_TYPE=${1:-"unit"}

case $TEST_TYPE in
    "unit")
        echo "ユニットテストを実行します..."
        uv run pytest tests/unit/ -v -m "not slow" --cov=src --cov-report=html --cov-report=term
        ;;
    "integration")
        echo "統合テストを実行します..."
        echo "注意: 統合テストは実際のAPIとデータベースを使用します"
        uv run pytest tests/integration/ -v -m "integration"
        ;;
    "all")
        echo "全てのテストを実行します..."
        uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term
        ;;
    "enhanced")
        echo "拡張ユニットテストを実行します..."
        uv run pytest tests/unit/test_*_enhanced.py -v
        ;;
    "fast")
        echo "高速テスト（スローテストを除く）を実行します..."
        uv run pytest tests/ -v -m "not slow and not integration"
        ;;
    "slow")
        echo "スローテストを実行します..."
        uv run pytest tests/ -v -m "slow"
        ;;
    "api")
        echo "API関連テストを実行します..."
        echo "注意: 実際のAPIキーが必要です"
        uv run pytest tests/ -v -m "api or integration"
        ;;
    *)
        echo "使用方法: $0 [unit|integration|all|enhanced|fast|slow|api]"
        echo ""
        echo "テストタイプ:"
        echo "  unit        - ユニットテストのみ（デフォルト）"
        echo "  integration - 統合テストのみ"
        echo "  all         - 全てのテスト"
        echo "  enhanced    - 拡張ユニットテスト"
        echo "  fast        - 高速テスト（スローテストを除く）"
        echo "  slow        - スローテストのみ"
        echo "  api         - API関連テスト"
        exit 1
        ;;
esac

echo ""
echo "テスト実行完了！"

# カバレッジレポートの場所を表示
if [ -f "htmlcov/index.html" ]; then
    echo "カバレッジレポート: htmlcov/index.html"
fi