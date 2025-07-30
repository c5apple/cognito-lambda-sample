"""
Cognito API Client Wrapper

AWS Cognito API呼び出しの抽象化、エラーハンドリング、レスポンス正規化を提供する
"""
import os
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


# 環境変数の読み込み
load_dotenv()

logger = logging.getLogger(__name__)


class CognitoError(Exception):
    """Cognito操作のベース例外クラス"""
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)


class AuthenticationError(CognitoError):
    """認証エラー"""
    pass


class AuthorizationError(CognitoError):
    """認可エラー"""
    pass


class ValidationError(CognitoError):
    """バリデーションエラー"""
    pass


class ServiceError(CognitoError):
    """サービスエラー"""
    pass


class CognitoClient:
    """
    AWS Cognito API操作のためのクライアントラッパー
    
    機能:
    - 認証 (InitiateAuth)
    - ログアウト (GlobalSignOut)
    - ユーザー情報取得 (GetUser)
    - ユーザー作成 (AdminCreateUser)
    - ユーザー削除 (AdminDeleteUser)
    """
    
    def __init__(self, 
                 user_pool_id: Optional[str] = None,
                 client_id: Optional[str] = None,
                 region: Optional[str] = None):
        """
        Cognitoクライアントの初期化
        
        Args:
            user_pool_id: CognitoユーザープールID
            client_id: CognitoクライアントアプリケーションID
            region: AWSリージョン
        """
        self.user_pool_id = user_pool_id or os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = client_id or os.getenv('COGNITO_CLIENT_ID')
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        if not self.user_pool_id:
            raise ValidationError("COGNITO_USER_POOL_ID is required")
        if not self.client_id:
            raise ValidationError("COGNITO_CLIENT_ID is required")
        
        try:
            self.client = boto3.client('cognito-idp', region_name=self.region)
        except Exception as e:
            raise ServiceError(f"Failed to initialize Cognito client: {str(e)}", original_error=e)
    
    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        ユーザー認証を実行
        
        Args:
            email: ユーザーのメールアドレス
            password: パスワード
            
        Returns:
            認証結果（トークン情報）
            
        Raises:
            AuthenticationError: 認証に失敗した場合
            ValidationError: パラメータが不正な場合
            ServiceError: サービスエラーの場合
        """
        if not email or not password:
            raise ValidationError("Email and password are required")
        
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            return self._normalize_auth_response(response)
            
        except ClientError as e:
            self._handle_client_error(e, "Authentication failed")
        except Exception as e:
            raise ServiceError(f"Unexpected error during authentication: {str(e)}", original_error=e)
    
    def logout(self, access_token: str) -> Dict[str, Any]:
        """
        ユーザーログアウトを実行（全デバイスからのサインアウト）
        
        Args:
            access_token: JWTアクセストークン
            
        Returns:
            ログアウト結果
            
        Raises:
            AuthorizationError: トークンが無効な場合
            ValidationError: パラメータが不正な場合
            ServiceError: サービスエラーの場合
        """
        if not access_token:
            raise ValidationError("Access token is required")
        
        try:
            response = self.client.global_sign_out(
                AccessToken=access_token
            )
            
            return {
                "success": True,
                "message": "Successfully logged out"
            }
            
        except ClientError as e:
            self._handle_client_error(e, "Logout failed")
        except Exception as e:
            raise ServiceError(f"Unexpected error during logout: {str(e)}", original_error=e)
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        ユーザー情報を取得
        
        Args:
            access_token: JWTアクセストークン
            
        Returns:
            ユーザー情報
            
        Raises:
            AuthorizationError: トークンが無効な場合
            ValidationError: パラメータが不正な場合
            ServiceError: サービスエラーの場合
        """
        if not access_token:
            raise ValidationError("Access token is required")
        
        try:
            response = self.client.get_user(
                AccessToken=access_token
            )
            
            return self._normalize_user_response(response)
            
        except ClientError as e:
            self._handle_client_error(e, "Failed to get user info")
        except Exception as e:
            raise ServiceError(f"Unexpected error getting user info: {str(e)}", original_error=e)
    
    def create_user(self, email: str, password: str, 
                   attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        テストユーザーを作成（管理者権限が必要）
        
        Args:
            email: ユーザーのメールアドレス
            password: 一時パスワード
            attributes: ユーザー属性（オプション）
            
        Returns:
            ユーザー作成結果
            
        Raises:
            ValidationError: パラメータが不正な場合
            ServiceError: サービスエラーの場合
        """
        if not email or not password:
            raise ValidationError("Email and password are required")
        
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'true'}
        ]
        
        # 追加属性があれば追加
        if attributes:
            for key, value in attributes.items():
                user_attributes.append({'Name': key, 'Value': value})
        
        try:
            response = self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=user_attributes,
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # ウェルカムメールを送信しない
            )
            
            return self._normalize_create_user_response(response)
            
        except ClientError as e:
            self._handle_client_error(e, "Failed to create user")
        except Exception as e:
            raise ServiceError(f"Unexpected error creating user: {str(e)}", original_error=e)
    
    def delete_user(self, email: str) -> Dict[str, Any]:
        """
        テストユーザーを削除（管理者権限が必要）
        
        Args:
            email: 削除するユーザーのメールアドレス
            
        Returns:
            ユーザー削除結果
            
        Raises:
            ValidationError: パラメータが不正な場合
            ServiceError: サービスエラーの場合
        """
        if not email:
            raise ValidationError("Email is required")
        
        try:
            response = self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            
            return {
                "success": True,
                "message": f"User {email} successfully deleted"
            }
            
        except ClientError as e:
            self._handle_client_error(e, "Failed to delete user")
        except Exception as e:
            raise ServiceError(f"Unexpected error deleting user: {str(e)}", original_error=e)
    
    def _normalize_auth_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """認証レスポンスを正規化"""
        auth_result = response.get('AuthenticationResult', {})
        
        return {
            "access_token": auth_result.get('AccessToken'),
            "refresh_token": auth_result.get('RefreshToken'),
            "id_token": auth_result.get('IdToken'),
            "token_type": auth_result.get('TokenType', 'Bearer'),
            "expires_in": auth_result.get('ExpiresIn', 3600)
        }
    
    def _normalize_user_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザー情報レスポンスを正規化"""
        attributes = {}
        for attr in response.get('UserAttributes', []):
            attributes[attr['Name']] = attr['Value']
        
        return {
            "user_id": attributes.get('sub'),
            "username": response.get('Username'),
            "email": attributes.get('email'),
            "attributes": {
                "email_verified": attributes.get('email_verified') == 'true',
                "given_name": attributes.get('given_name'),
                "family_name": attributes.get('family_name'),
                "phone_number": attributes.get('phone_number'),
            }
        }
    
    def _normalize_create_user_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザー作成レスポンスを正規化"""
        user = response.get('User', {})
        
        return {
            "success": True,
            "user_id": user.get('Username'),
            "status": user.get('UserStatus'),
            "created": user.get('UserCreateDate'),
            "message": "User created successfully"
        }
    
    def _handle_client_error(self, error: ClientError, context: str):
        """Cognitoクライアントエラーのハンドリング"""
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        logger.warning(f"{context}: {error_code} - {error_message}")
        
        # 認証関連エラー
        if error_code in ['NotAuthorizedException', 'UserNotFoundException', 
                         'UserNotConfirmedException', 'PasswordResetRequiredException']:
            raise AuthenticationError("認証に失敗しました", error_code, error)
        
        # 認可関連エラー
        elif error_code in ['AccessDeniedException', 'UnauthorizedOperation']:
            raise AuthorizationError("アクセスが拒否されました", error_code, error)
        
        # バリデーションエラー
        elif error_code in ['InvalidParameterException', 'InvalidPasswordException',
                           'UsernameExistsException', 'AliasExistsException']:
            raise ValidationError(f"リクエストが不正です: {error_message}", error_code, error)
        
        # サービスエラー
        elif error_code in ['InternalErrorException', 'TooManyRequestsException',
                           'ResourceNotFoundException']:
            raise ServiceError(f"サービスエラーが発生しました: {error_message}", error_code, error)
        
        # その他のエラー
        else:
            raise ServiceError(f"予期しないエラーが発生しました: {error_message}", error_code, error)


# 便利関数
def get_cognito_client() -> CognitoClient:
    """
    環境変数から設定を読み込んでCognitoクライアントを作成
    
    Returns:
        CognitoClient: 設定済みのCognitoクライアント
    """
    return CognitoClient()