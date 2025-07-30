# NPMスクリプト使用ガイド

このドキュメントは、Cognito Lambda Sampleプロジェクトで利用可能なnpmスクリプトの詳細なリファレンスです。基本的な情報については[README.md](../README.md)をご覧ください。

このプロジェクトでは、開発ワークフローを効率化するためのnpmスクリプトを提供しています。

## 📦 基本的なコマンド

### ユーザー管理
```bash
# テストユーザー作成
npm run create-user -- --email test@example.com --password TempPass123!

# テストユーザー削除
npm run delete-user -- --email test@example.com
```

### テスト実行
```bash
# 基本テスト
npm run test

# 詳細テスト（verbose）
npm run test-verbose

# カバレッジ付きテスト
npm run test-coverage
```

### デプロイメント
```bash
# 基本デプロイ
npm run deploy

# 開発環境デプロイ
npm run deploy-dev

# 本番環境デプロイ
npm run deploy-prod
```

## 🐳 Docker統合コマンド

### Docker環境管理
```bash
# Dockerイメージビルド
npm run docker-build

# 開発環境起動
npm run docker-up

# 開発環境停止
npm run docker-down

# ログ表示
npm run docker-logs
```

### Docker内でのコマンド実行
```bash
# Docker内でテスト実行
npm run docker-test

# Docker内でユーザー作成
npm run docker-create-user -- --email test@example.com --password TempPass123!

# Docker内でユーザー削除
npm run docker-delete-user -- --email test@example.com

# Dockerコンテナ内シェルアクセス
npm run docker-shell
```

## 🔧 開発支援コマンド

### コード品質
```bash
# コードリンター
npm run lint

# コードフォーマッター
npm run format

# 依存関係インストール
npm run install-deps

# キャッシュクリーンアップ
npm run clean
```

## 📋 使用例

### 完全な開発フロー
```bash
# 1. Docker環境を起動
npm run docker-up

# 2. テストユーザーを作成
npm run docker-create-user -- --email dev@example.com --password DevPass123!

# 3. テストを実行
npm run docker-test

# 4. ユーザーを削除
npm run docker-delete-user -- --email dev@example.com

# 5. 環境を停止
npm run docker-down
```

### ローカル開発（依存関係がインストール済みの場合）
```bash
# テスト実行
npm run test

# ユーザー管理
npm run create-user -- --email local@example.com --password LocalPass123!
npm run delete-user -- --email local@example.com
```

## ⚠️ 注意事項

1. **環境変数**: コマンド実行前に必要な環境変数（`COGNITO_USER_POOL_ID`、`COGNITO_CLIENT_ID`等）が設定されていることを確認してください。

2. **Docker**: Dockerコマンドを使用する場合は、Dockerが起動していることを確認してください。

3. **引数の渡し方**: npmスクリプトに引数を渡す場合は、`--`の後に引数を指定してください。
   ```bash
   npm run create-user -- --email test@example.com --password Test123!
   ```

4. **Python環境**: ローカルでPythonコマンドを実行する場合は、適切なPython環境と依存関係がインストールされている必要があります。