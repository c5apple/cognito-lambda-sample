"""
認証ヘルパーユーティリティ

JWT トークン検証、HTTPヘッダーからのトークン抽出、認証エラーハンドリングを提供する
"""
import re
import logging
from typing import Dict, Any, Optional, Tuple
import jwt
from jwt.exceptions import (
    DecodeError, 
    ExpiredSignatureError, 
    InvalidTokenError,
    InvalidSignatureError
)
import requests
from requests.exceptions import RequestException

from utils.cognito import AuthenticationError, AuthorizationError, ValidationError, ServiceError

logger = logging.getLogger(__name__)


class TokenValidator:
    """
    JWT トークン検証クラス
    
    Cognito JWT トークンの検証を行い、トークンの有効性とユーザー情報を確認する
    """
    
    def __init__(self, user_pool_id: str, region: str = 'us-east-1'):
        """
        トークン検証の初期化
        
        Args:
            user_pool_id: CognitoユーザープールID
            region: AWSリージョン
        """
        self.user_pool_id = user_pool_id
        self.region = region
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        self._jwks_cache = None
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        JWT トークンを検証
        
        Args:
            token: 検証するJWT トークン
            
        Returns:
            トークンのペイロード情報
            
        Raises:
            AuthorizationError: トークンが無効または期限切れの場合
            ValidationError: トークンが不正な形式の場合
            ServiceError: JWKS取得などのサービスエラーの場合
        """
        if not token:
            raise ValidationError("Token is required")
        
        try:
            # JWTヘッダーを取得してkey idを確認
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise AuthorizationError("トークンが無効です")
            
            # JWKSから公開鍵を取得
            public_key = self._get_public_key(kid)
            
            # トークンを検証
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=None,  # Cognitoのアクセストークンは audience claim を持たない場合がある
                options={
                    "verify_aud": False,  # audience検証を無効化
                    "verify_exp": True,   # 有効期限は検証
                    "verify_signature": True
                }
            )
            
            # トークンタイプを確認（access_token であることを確認）
            token_use = payload.get('token_use')
            if token_use != 'access':
                raise AuthorizationError("トークンが無効です")
            
            return payload
            
        except ExpiredSignatureError:
            raise AuthorizationError("トークンの有効期限が切れています")
        except (DecodeError, InvalidTokenError, InvalidSignatureError):
            raise AuthorizationError("トークンが無効です")
        except (AuthorizationError, ValidationError, ServiceError):
            # 既に適切な例外型なので再発生
            raise
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise ServiceError(f"トークン検証中にエラーが発生しました: {str(e)}")
    
    def _get_public_key(self, kid: str) -> str:
        """
        JWKS から公開鍵を取得
        
        Args:
            kid: Key ID
            
        Returns:
            公開鍵
            
        Raises:
            ServiceError: JWKS取得に失敗した場合
            AuthorizationError: 指定されたkey idが見つからない場合
        """
        if not self._jwks_cache:
            try:
                response = requests.get(self.jwks_url, timeout=10)
                response.raise_for_status()
                self._jwks_cache = response.json()
            except RequestException as e:
                raise ServiceError(f"JWKS取得に失敗しました: {str(e)}")
        
        # 指定されたkey idを検索
        for key in self._jwks_cache.get('keys', []):
            if key.get('kid') == kid:
                # JWK形式からPEM形式に変換
                return jwt.algorithms.RSAAlgorithm.from_jwk(key)
        
        raise AuthorizationError("トークンが無効です")


def extract_token_from_header(authorization_header: str) -> str:
    """
    Authorization ヘッダーから Bearer トークンを抽出
    
    Args:
        authorization_header: HTTP Authorization ヘッダーの値
        
    Returns:
        抽出されたトークン
        
    Raises:
        AuthorizationError: ヘッダーが無効な形式の場合
        ValidationError: ヘッダーが提供されていない場合
    """
    if not authorization_header:
        raise ValidationError("認証が必要です")
    
    # Bearer トークンの形式を確認
    bearer_pattern = re.compile(r'^Bearer\s+(.+)$', re.IGNORECASE)
    match = bearer_pattern.match(authorization_header.strip())
    
    if not match:
        raise AuthorizationError("認証ヘッダーが無効です")
    
    token = match.group(1)
    if not token:
        raise AuthorizationError("認証ヘッダーが無効です")
    
    return token


def extract_token_from_event(event: Dict[str, Any]) -> str:
    """
    Lambda イベントから認証トークンを抽出
    
    Args:
        event: Lambda イベントオブジェクト
        
    Returns:
        抽出されたトークン
        
    Raises:
        AuthorizationError: トークンが無効な形式の場合
        ValidationError: トークンが提供されていない場合
    """
    headers = event.get('headers', {})
    
    # Authorization ヘッダーを検索（大文字小文字を区別しない）
    auth_header = None
    for key, value in headers.items():
        if key.lower() == 'authorization':
            auth_header = value
            break
    
    if not auth_header:
        raise ValidationError("認証が必要です")
    
    return extract_token_from_header(auth_header)


def validate_and_extract_user_info(token: str, user_pool_id: str, region: str = 'us-east-1') -> Dict[str, Any]:
    """
    トークンを検証してユーザー情報を抽出
    
    Args:
        token: JWT アクセストークン
        user_pool_id: CognitoユーザープールID
        region: AWSリージョン
        
    Returns:
        ユーザー情報
        
    Raises:
        AuthorizationError: トークンが無効または期限切れの場合
        ValidationError: パラメータが不正な場合
        ServiceError: サービスエラーの場合
    """
    if not token:
        raise ValidationError("認証が必要です")
    
    if not user_pool_id:
        raise ValidationError("User pool ID is required")
    
    validator = TokenValidator(user_pool_id, region)
    payload = validator.validate_token(token)
    
    # ユーザー情報を抽出
    return {
        "user_id": payload.get('sub'),
        "username": payload.get('username'),
        "client_id": payload.get('client_id'),
        "token_use": payload.get('token_use'),
        "scope": payload.get('scope', '').split() if payload.get('scope') else [],
        "auth_time": payload.get('auth_time'),
        "iat": payload.get('iat'),
        "exp": payload.get('exp')
    }


def require_authentication(event: Dict[str, Any], user_pool_id: str, region: str = 'us-east-1') -> Dict[str, Any]:
    """
    認証が必要なエンドポイント用のデコレータ関数
    
    Lambda イベントから認証トークンを抽出・検証し、ユーザー情報を返す
    
    Args:
        event: Lambda イベントオブジェクト
        user_pool_id: CognitoユーザープールID
        region: AWSリージョン
        
    Returns:
        検証されたユーザー情報
        
    Raises:
        AuthorizationError: 認証に失敗した場合
        ValidationError: 認証が必要な場合
        ServiceError: サービスエラーの場合
    """
    # イベントからトークンを抽出
    token = extract_token_from_event(event)
    
    # トークンを検証してユーザー情報を取得
    return validate_and_extract_user_info(token, user_pool_id, region)


def create_auth_error_response(error: Exception, status_code: int = None) -> Dict[str, Any]:
    """
    認証エラー用のHTTPレスポンスを作成
    
    Args:
        error: 発生したエラー
        status_code: HTTPステータスコード（指定されない場合はエラータイプから自動決定）
        
    Returns:
        Lambda関数用のHTTPレスポンス
    """
    if isinstance(error, ValidationError):
        default_status = 400
        error_type = "BadRequest"
    elif isinstance(error, AuthenticationError):
        default_status = 401
        error_type = "AuthenticationFailed"
    elif isinstance(error, AuthorizationError):
        default_status = 401
        error_type = "Unauthorized"
    elif isinstance(error, ServiceError):
        default_status = 503
        error_type = "ServiceUnavailable"
    else:
        default_status = 500
        error_type = "InternalServerError"
    
    response_status = status_code or default_status
    
    return {
        "statusCode": response_status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": {
            "error": error_type,
            "message": str(error)
        }
    }


def create_success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """
    成功レスポンス用のHTTPレスポンスを作成
    
    Args:
        data: レスポンスデータ
        status_code: HTTPステータスコード
        
    Returns:
        Lambda関数用のHTTPレスポンス
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": data
    }