# cognito-lambda-sample

AWS Lambda、Python、Amazon Cognitoを使用して構築されたサーバーレス認証APIです。このシステムは、ログイン/ログアウト機能、保護されたユーザー情報取得、テストユーザー管理のためのCLIユーティリティを備えた安全なJWTトークンベースの認証を提供します。

## 🚀 特徴

- **サーバーレスアーキテクチャ**: 各APIエンドポイント用の個別Lambda関数と自動スケーリング
- **安全なJWT認証**: Amazon Cognitoを使用したトークンベース認証
- **RESTful API**: API Gatewayを通じた標準化されたエンドポイント
- **開発ツール**: テストユーザー管理用のCLIユーティリティ
- **Docker対応**: 一貫した開発環境

## 📋 要件

- Python 3.9+
- AWS アカウント
- Docker（開発環境用）
- Node.js（npm scriptsの実行用）

## 🏗️ プロジェクト構造

```
cognito-lambda-sample/
├── handlers/           # Lambda関数ハンドラー
│   ├── login.py       # ユーザー認証エンドポイント
│   ├── logout.py      # セッション終了エンドポイント
│   └── user_info.py   # 保護されたユーザープロファイルエンドポイント
├── utils/             # 共有ユーティリティ
│   ├── auth.py        # トークン検証と抽出
│   └── cognito.py     # Cognito APIクライアントラッパー
├── cli/               # コマンドラインユーティリティ
│   ├── create_user.py # テストユーザー作成ツール
│   └── delete_user.py # テストユーザー削除ツール
├── scripts/           # セットアップスクリプト
│   └── setup-env.sh   # 環境変数自動生成スクリプト
├── tests/             # テストスイート
│   ├── unit/          # 個別コンポーネントの単体テスト
│   └── integration/   # エンドツーエンドAPIテスト
├── requirements.txt   # Python依存関係
├── package.json       # 開発ワークフロー用npmスクリプト
├── Dockerfile         # コンテナ定義
├── docker-compose.yml # 開発環境
├── serverless.yml     # デプロイ設定（Cognito定義含む）
└── .env.example       # 環境変数テンプレート
```

## ⚙️ セットアップ

### 🚀 クイックスタート（推奨）

AWS認証情報が設定済みの場合、以下のコマンド一発でセットアップ完了：

```bash
# Cognito作成、デプロイ、環境変数設定を自動実行
npm run deploy-and-setup
```

### 📋 段階的セットアップ

#### 1. 前提条件

- AWS CLI設定済み（`aws configure`完了）
- Node.js（npm scripts用）
- Python 3.9+
- Docker（開発環境用、オプション）

#### 2. プロジェクトのセットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd cognito-lambda-sample

# 依存関係をインストール
pip install -r requirements.txt
```

#### 3. AWS リソースのデプロイ

```bash
# Cognito User Pool、Lambda関数、API Gatewayを自動作成
serverless deploy

# または
npm run deploy
```

#### 4. 環境変数の自動設定

```bash
# デプロイ結果から環境変数を自動生成
npm run setup-env
```

これで`.env`ファイルが自動生成されます：
```env
COGNITO_USER_POOL_ID=us-east-1_AbCd1234Ef  # 自動設定
COGNITO_CLIENT_ID=1a2b3c4d5e6f7g8h9i0j    # 自動設定
AWS_REGION=us-east-1                       # AWSプロファイルから取得
```

#### 5. 開発環境のセットアップ（オプション）

##### Docker環境（推奨）
```bash
# 開発環境を開始
docker-compose up -d

# 依存関係をインストール（コンテナ内）
docker-compose exec cognito-auth-api pip install -r requirements.txt
```

##### ローカルPython環境
```bash
# 既にステップ2で完了済み
pip install -r requirements.txt
```

### 🔄 リソースの削除

開発完了後、AWSリソースを削除：

```bash
# 全AWSリソースを削除
serverless remove

# または
npm run remove
```

## 🔧 使用方法

### API エンドポイント

#### 1. ログイン
```http
POST /login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**レスポンス (成功):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJjdHkiOiJKV1QiLCJlbmMi...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### 2. ユーザー情報取得
```http
GET /user
Authorization: Bearer {access_token}
```

**レスポンス:**
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

#### 3. ログアウト
```http
POST /logout
Authorization: Bearer {access_token}
```

### CLIユーティリティ

プロジェクトにはテストユーザー管理用のCLIツールが含まれています。

```bash
# テストユーザーの作成
npm run create-user -- --email test@example.com --password TempPass123!

# テストユーザーの削除
npm run delete-user -- --email test@example.com
```

詳細な使用方法とすべてのnpmスクリプトについては、📚 **[NPMスクリプト使用ガイド](docs/npm-scripts.md)** を参照してください。

## 🧪 テスト

```bash
# 基本的なテスト実行
npm run test

# Docker環境でのテスト
npm run docker-test
```

詳細なテストオプションについては、📚 **[NPMスクリプト使用ガイド](docs/npm-scripts.md)** を参照してください。

## 🚀 デプロイ

### サーバーレス関数のデプロイ
```bash
# serverlessを使用
serverless deploy

# npm scriptを使用
npm run deploy
```

## 📚 API 仕様

### エラーレスポンス形式

すべてのAPIエラーは以下の形式で返されます：

```json
{
  "error": "ErrorType",
  "message": "エラーの詳細メッセージ"
}
```

### HTTPステータスコード

- `200`: 成功
- `400`: バリデーションエラー
- `401`: 認証エラー
- `403`: 認可エラー
- `404`: リソースが見つからない
- `500`: 内部サーバーエラー
- `503`: サービス利用不可

## 🔒 セキュリティ

### 認証フロー
1. クライアントがメール/パスワードでログイン
2. システムがJWTアクセストークンとリフレッシュトークンを発行
3. クライアントが保護されたエンドポイントにアクセストークンを送信
4. システムがトークンを検証してリソースへのアクセスを許可

### セキュリティ考慮事項
- JWT署名検証の実装
- トークン有効期限の適切な設定
- 入力検証とサニタイゼーション
- 機密情報の環境変数による管理
- IAMロールによる最小権限の原則

## 🛠️ 開発

### 主要なnpm scripts

- `npm run deploy` - AWSリソースをデプロイ
- `npm run test` - テストを実行
- `npm run create-user` - テストユーザーを作成
- `npm run delete-user` - テストユーザーを削除

すべてのnpmスクリプトとDocker統合コマンドについては、📚 **[NPMスクリプト使用ガイド](docs/npm-scripts.md)** を参照してください。

### 開発ワークフロー

1. **機能開発**: 各Lambda関数とユーティリティを実装
2. **単体テスト**: 個別コンポーネントのテスト
3. **統合テスト**: エンドツーエンドのAPIテスト
4. **デプロイ**: サーバーレス環境へのデプロイ

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチをプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## 📞 サポート

質問や問題がある場合は、GitHubのIssuesページで報告してください。

---

**注意**: このプロジェクトは開発およびテスト目的で設計されています。本番環境での使用前に、適切なセキュリティ監査を実施してください。