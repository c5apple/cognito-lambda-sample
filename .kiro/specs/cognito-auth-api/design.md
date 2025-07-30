# 設計書

## 概要

このシステムは、AWS Lambda、Python、Amazon Cognitoを使用したサーバーレス認証APIです。JWT トークンベースの認証を提供し、ログイン/ログアウト機能、保護されたユーザー情報取得、およびテストユーザー管理のためのCLIユーティリティを実装します。

## アーキテクチャ

### システム構成

```
Client Application
       ↓
   API Gateway
       ↓
   Lambda Functions
       ↓
   Amazon Cognito
```

### 設計決定

- **サーバーレスアーキテクチャ**: 自動スケーリングと運用オーバーヘッドの最小化のため
- **個別Lambda関数**: 各APIエンドポイントを独立した関数として実装し、責任分離を実現
- **Amazon Cognito**: JWT トークン管理とユーザー認証の標準化されたソリューション
- **API Gateway統合**: RESTful APIエンドポイントの統一されたルーティング
- **Docker開発環境**: 一貫した開発環境とPython依存関係の管理のため

## コンポーネントとインターフェース

### Lambda関数

#### 1. ログイン関数 (`login.py`)
- **目的**: ユーザー認証とトークン発行
- **入力**: メールアドレス、パスワード
- **出力**: JWTアクセストークン、リフレッシュトークン
- **Cognitoサービス**: `InitiateAuth` API使用

#### 2. ログアウト関数 (`logout.py`)
- **目的**: ユーザーセッション終了とトークン無効化
- **入力**: アクセストークン
- **出力**: 成功確認メッセージ
- **Cognitoサービス**: `GlobalSignOut` API使用

#### 3. ユーザー情報取得関数 (`user_info.py`)
- **目的**: 認証されたユーザーのプロファイル情報取得
- **入力**: アクセストークン
- **出力**: ユーザープロファイル（メール、ユーザーID、属性）
- **Cognitoサービス**: `GetUser` API使用

### 共通ユーティリティ

#### 認証ヘルパー (`utils/auth.py`)
- トークン検証機能
- HTTPヘッダーからのトークン抽出
- 認証エラーハンドリング

#### Cognitoクライアントラッパー (`utils/cognito.py`)
- Cognito API呼び出しの抽象化
- エラーハンドリングとレスポンス正規化
- 環境変数からの設定読み込み

### CLIユーティリティ

#### テストユーザー作成 (`cli/create_user.py`)
- **機能**: Cognitoユーザープールにテストユーザーを作成
- **パラメータ**: メールアドレス、パスワード、属性（オプション）
- **Cognitoサービス**: `AdminCreateUser` API使用
- **使用例**: 
  ```bash
  python cli/create_user.py --email test@example.com --password TempPass123!
  ```

#### テストユーザー削除 (`cli/delete_user.py`)
- **機能**: Cognitoユーザープールからテストユーザーを削除
- **パラメータ**: ユーザー識別子（メールまたはユーザーID）
- **Cognitoサービス**: `AdminDeleteUser` API使用
- **使用例**: 
  ```bash
  python cli/delete_user.py --email test@example.com
  ```

### 開発用スクリプト

プロジェクトルートに `package.json` を配置し、npm scriptsでCLIユーティリティを簡単に実行できるようにします：

```json
{
  "scripts": {
    "create-user": "python cli/create_user.py",
    "delete-user": "python cli/delete_user.py",
    "test": "python -m pytest tests/",
    "deploy": "serverless deploy"
  }
}
```

**使用例:**
```bash
# テストユーザー作成
npm run create-user -- --email test@example.com --password TempPass123!

# テストユーザー削除
npm run delete-user -- --email test@example.com

# テスト実行
npm run test

# デプロイ
npm run deploy
```

### Docker開発環境

開発環境の一貫性を保つため、Dockerコンテナを使用します：

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "pytest"]
```

#### docker-compose.yml
```yaml
version: '3.8'
services:
  cognito-auth-api:
    build: .
    volumes:
      - .:/app
    environment:
      - COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
      - COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
      - AWS_REGION=${AWS_REGION}
    command: tail -f /dev/null
```

**Docker使用例:**
```bash
# 開発環境起動
docker-compose up -d

# コンテナ内でCLIユーティリティ実行
docker-compose exec cognito-auth-api python cli/create_user.py --email test@example.com --password TempPass123!

# テスト実行
docker-compose exec cognito-auth-api python -m pytest

# 環境停止
docker-compose down
```

## データモデル

### リクエスト/レスポンス形式

#### ログインリクエスト
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### ログインレスポンス（成功）
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJjdHkiOiJKV1QiLCJlbmMi...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### ユーザー情報レスポンス
```json
{
  "user_id": "12345678-1234-1234-1234-123456789012",
  "email": "user@example.com",
  "attributes": {
    "email_verified": true,
    "given_name": "John",
    "family_name": "Doe"
  }
}
```

#### エラーレスポンス
```json
{
  "error": "AuthenticationFailed",
  "message": "認証に失敗しました"
}
```

### 環境変数

```
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=1234567890abcdefghijklmnop
AWS_REGION=us-east-1
```

## エラーハンドリング

### エラー分類と対応

#### 認証エラー（セキュリティ考慮）
- **AuthenticationFailed**: 認証に失敗しました
  - 内部的には以下を区別するが、クライアントには統一メッセージを返す：
    - 無効な認証情報
    - ユーザーが存在しない
    - ユーザーが確認されていない
    - ユーザーアカウントが無効化されている

#### 認可エラー
- **Unauthorized**: 認証が必要です
  - トークンが提供されていない場合
- **Forbidden**: アクセスが拒否されました
  - 無効なトークン、期限切れトークンの場合

#### バリデーションエラー
- **BadRequest**: リクエストが不正です
  - 必須パラメータが不足
  - 不正な形式のリクエスト

#### サービスエラー
- **ServiceUnavailable**: サービスが一時的に利用できません
- **InternalServerError**: 内部サーバーエラーが発生しました

### HTTPステータスコード

- `200`: 成功
- `400`: バリデーションエラー
- `401`: 認証エラー
- `404`: リソースが見つからない
- `500`: 内部サーバーエラー
- `503`: サービス利用不可

## テスト戦略

### 単体テスト
- 各Lambda関数の個別テスト
- ユーティリティ関数のテスト
- モックを使用したCognito API呼び出しのテスト

### 統合テスト
- API Gateway + Lambda統合のテスト
- 実際のCognitoサービスとの統合テスト
- エンドツーエンドの認証フローテスト

### テストデータ管理
- テスト専用のCognitoユーザープール使用
- CLIユーティリティを使用したテストユーザーの作成/削除
- テスト後のクリーンアップ自動化

### テストケース

#### ログイン機能
- 有効な認証情報でのログイン成功
- 無効な認証情報でのログイン失敗
- 存在しないユーザーでのログイン失敗
- 無効化されたユーザーでのログイン失敗

#### ログアウト機能
- 有効なトークンでのログアウト成功
- 無効なトークンでのログアウト失敗
- 期限切れトークンでのログアウト失敗

#### ユーザー情報取得
- 有効なトークンでの情報取得成功
- 無効なトークンでの情報取得失敗
- トークンなしでの情報取得失敗

#### CLIユーティリティ
- テストユーザー作成の成功/失敗シナリオ
- テストユーザー削除の成功/失敗シナリオ
- パラメータ不足時のエラーハンドリング

## セキュリティ考慮事項

### トークンセキュリティ
- JWT署名検証の実装
- トークン有効期限の適切な設定
- リフレッシュトークンの安全な管理

### 入力検証
- すべてのAPIエンドポイントでの入力検証
- SQLインジェクション対策（該当する場合）
- XSS対策のためのデータサニタイゼーション

### 環境設定
- 機密情報の環境変数による管理
- IAMロールによる最小権限の原則
- VPC設定（必要に応じて）

### ログとモニタリング
- 必要最小限のエラーログのみ記録（DoS攻撃による課金リスク回避）
- 重要なセキュリティイベントのみアラート対象
- パフォーマンスメトリクスは基本的なLambdaメトリクスのみ使用