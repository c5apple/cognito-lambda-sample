# 技術スタック

## コア技術

- **ランタイム**: Python 3.9
- **クラウドプラットフォーム**: AWS (Lambda, API Gateway, Cognito)
- **認証**: JWTトークンを使用したAmazon Cognitoユーザープール
- **アーキテクチャ**: エンドポイントごとの個別Lambdaを使用したサーバーレス関数

## 開発環境

- **コンテナ化**: Python 3.9-slimベースイメージを使用したDocker
- **オーケストレーション**: ローカル開発用のdocker-compose
- **パッケージ管理**: requirements.txtを使用したpip
- **テスト**: 単体テストと統合テスト用のpytest

## AWSサービス

- **AWS Lambda**: ログイン、ログアウト、ユーザー情報エンドポイント用の個別関数
- **API Gateway**: RESTful APIルーティングとHTTP統合
- **Amazon Cognito**: ユーザープール管理とJWTトークン処理
- **IAM**: Lambda実行用の最小権限ロール

## 共通コマンド

### 開発環境セットアップ
```bash
# 開発環境を開始
docker-compose up -d

# 依存関係をインストール
pip install -r requirements.txt
```

### テスト
```bash
# 全テストを実行
python -m pytest

# Docker内でテストを実行
docker-compose exec cognito-auth-api python -m pytest
```

### ユーザー管理（CLI）
```bash
# テストユーザーを作成
python cli/create_user.py --email test@example.com --password TempPass123!

# テストユーザーを削除
python cli/delete_user.py --email test@example.com

# npmスクリプトを使用
npm run create-user -- --email test@example.com --password TempPass123!
npm run delete-user -- --email test@example.com
```

### デプロイ
```bash
# サーバーレス関数をデプロイ
serverless deploy
# または
npm run deploy
```

## 環境変数

必要な設定:
- `COGNITO_USER_POOL_ID`: Cognitoユーザープール識別子
- `COGNITO_CLIENT_ID`: CognitoアプリクライアントID
- `AWS_REGION`: CognitoサービスのAWSリージョン