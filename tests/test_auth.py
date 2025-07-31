"""
認証ヘルパーユーティリティの単体テスト
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidTokenError
import requests

from utils.auth import (
    TokenValidator,
    extract_token_from_header,
    extract_token_from_event,
    validate_and_extract_user_info,
    require_authentication,
    create_auth_error_response,
    create_success_response
)
from utils.cognito import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ServiceError
)


class TestTokenValidator:
    """TokenValidatorクラスのテスト"""
    
    def setup_method(self):
        """テストメソッドの初期化"""
        self.user_pool_id = 'ap-northeast-1_test123'
        self.region = 'ap-northeast-1'
        self.validator = TokenValidator(self.user_pool_id, self.region)
    
    def test_initialization(self):
        """初期化のテスト"""
        assert self.validator.user_pool_id == self.user_pool_id
        assert self.validator.region == self.region
        assert self.validator.jwks_url == f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        assert self.validator._jwks_cache is None
    
    @patch('utils.auth.jwt.get_unverified_header')
    @patch.object(TokenValidator, '_get_public_key')
    @patch('utils.auth.jwt.decode')
    def test_validate_token_success(self, mock_jwt_decode, mock_get_public_key, mock_get_header):
        """有効なトークンの検証成功をテスト"""
        # モックの設定
        mock_get_header.return_value = {'kid': 'test_kid'}
        mock_get_public_key.return_value = 'mock_public_key'
        mock_payload = {
            'sub': 'user123',
            'username': 'testuser',
            'token_use': 'access',
            'client_id': 'test_client',
            'scope': 'openid profile',
            'auth_time': 1234567890,
            'iat': 1234567890,
            'exp': 1234571490
        }
        mock_jwt_decode.return_value = mock_payload
        
        token = 'valid.jwt.token'
        result = self.validator.validate_token(token)
        
        # 検証
        assert result == mock_payload
        mock_get_header.assert_called_once_with(token)
        mock_get_public_key.assert_called_once_with('test_kid')
        mock_jwt_decode.assert_called_once()
    
    def test_validate_token_empty_token(self):
        """空のトークンでValidationErrorが発生することをテスト"""
        with pytest.raises(ValidationError, match="Token is required"):
            self.validator.validate_token("")
    
    @patch('utils.auth.jwt.get_unverified_header')
    def test_validate_token_no_kid(self, mock_get_header):
        """key idがないトークンでAuthorizationErrorが発生することをテスト"""
        mock_get_header.return_value = {}
        
        with pytest.raises(AuthorizationError, match="トークンが無効です"):
            self.validator.validate_token("invalid.jwt.token")
    
    @patch('utils.auth.jwt.get_unverified_header')
    @patch.object(TokenValidator, '_get_public_key')
    @patch('utils.auth.jwt.decode')
    def test_validate_token_expired(self, mock_jwt_decode, mock_get_public_key, mock_get_header):
        """期限切れトークンでAuthorizationErrorが発生することをテスト"""
        mock_get_header.return_value = {'kid': 'test_kid'}
        mock_get_public_key.return_value = 'mock_public_key'
        mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired")
        
        with pytest.raises(AuthorizationError, match="トークンの有効期限が切れています"):
            self.validator.validate_token("expired.jwt.token")
    
    @patch('utils.auth.jwt.get_unverified_header')
    @patch.object(TokenValidator, '_get_public_key')
    @patch('utils.auth.jwt.decode')
    def test_validate_token_invalid_format(self, mock_jwt_decode, mock_get_public_key, mock_get_header):
        """無効な形式のトークンでAuthorizationErrorが発生することをテスト"""
        mock_get_header.return_value = {'kid': 'test_kid'}
        mock_get_public_key.return_value = 'mock_public_key'
        mock_jwt_decode.side_effect = DecodeError("Invalid token")
        
        with pytest.raises(AuthorizationError, match="トークンが無効です"):
            self.validator.validate_token("invalid.jwt.token")
    
    @patch('utils.auth.jwt.get_unverified_header')
    @patch.object(TokenValidator, '_get_public_key')
    @patch('utils.auth.jwt.decode')
    def test_validate_token_wrong_token_use(self, mock_jwt_decode, mock_get_public_key, mock_get_header):
        """トークンタイプが間違っている場合のテスト"""
        mock_get_header.return_value = {'kid': 'test_kid'}
        mock_get_public_key.return_value = 'mock_public_key'
        mock_jwt_decode.return_value = {'token_use': 'id'}  # access ではない
        
        with pytest.raises(AuthorizationError, match="トークンが無効です"):
            self.validator.validate_token("wrong_type.jwt.token")
    
    @patch('utils.auth.requests.get')
    def test_get_public_key_success(self, mock_requests_get):
        """JWKS取得成功のテスト"""
        # モックの設定
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'keys': [
                {'kid': 'test_kid', 'kty': 'RSA', 'n': 'test_n', 'e': 'AQAB'}
            ]
        }
        mock_requests_get.return_value = mock_response
        
        # JWT.algorithms.RSAAlgorithm.from_jwkのモック
        with patch('utils.auth.jwt.algorithms.RSAAlgorithm.from_jwk') as mock_from_jwk:
            mock_from_jwk.return_value = 'mock_public_key'
            
            result = self.validator._get_public_key('test_kid')
            
            assert result == 'mock_public_key'
            mock_requests_get.assert_called_once()
            mock_from_jwk.assert_called_once()
    
    @patch('utils.auth.requests.get')
    def test_get_public_key_request_error(self, mock_requests_get):
        """JWKS取得失敗のテスト"""
        mock_requests_get.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(ServiceError, match="JWKS取得に失敗しました"):
            self.validator._get_public_key('test_kid')
    
    @patch('utils.auth.requests.get')
    def test_get_public_key_kid_not_found(self, mock_requests_get):
        """指定されたkey idが見つからない場合のテスト"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'keys': [
                {'kid': 'other_kid', 'kty': 'RSA', 'n': 'test_n', 'e': 'AQAB'}
            ]
        }
        mock_requests_get.return_value = mock_response
        
        with pytest.raises(AuthorizationError, match="トークンが無効です"):
            self.validator._get_public_key('nonexistent_kid')


class TestExtractTokenFromHeader:
    """extract_token_from_header関数のテスト"""
    
    def test_extract_valid_bearer_token(self):
        """有効なBearerトークンの抽出をテスト"""
        header = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        token = extract_token_from_header(header)
        assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    def test_extract_bearer_token_case_insensitive(self):
        """大文字小文字を区別しないBearerトークンの抽出をテスト"""
        header = "bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        token = extract_token_from_header(header)
        assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    def test_extract_token_with_extra_spaces(self):
        """余分な空白があるヘッダーからのトークン抽出をテスト"""
        header = "  Bearer   eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...  "
        token = extract_token_from_header(header)
        assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    def test_extract_token_empty_header(self):
        """空のヘッダーでValidationErrorが発生することをテスト"""
        with pytest.raises(ValidationError, match="認証が必要です"):
            extract_token_from_header("")
    
    def test_extract_token_none_header(self):
        """NoneヘッダーでValidationErrorが発生することをテスト"""
        with pytest.raises(ValidationError, match="認証が必要です"):
            extract_token_from_header(None)
    
    def test_extract_token_invalid_format(self):
        """無効な形式のヘッダーでAuthorizationErrorが発生することをテスト"""
        with pytest.raises(AuthorizationError, match="認証ヘッダーが無効です"):
            extract_token_from_header("InvalidToken")
    
    def test_extract_token_basic_auth(self):
        """Basic認証ヘッダーでAuthorizationErrorが発生することをテスト"""
        with pytest.raises(AuthorizationError, match="認証ヘッダーが無効です"):
            extract_token_from_header("Basic dXNlcjpwYXNzd29yZA==")
    
    def test_extract_token_bearer_no_token(self):
        """Bearerキーワードのみでトークンがない場合のテスト"""
        with pytest.raises(AuthorizationError, match="認証ヘッダーが無効です"):
            extract_token_from_header("Bearer ")


class TestExtractTokenFromEvent:
    """extract_token_from_event関数のテスト"""
    
    def test_extract_token_from_event_success(self):
        """Lambda イベントからのトークン抽出成功をテスト"""
        event = {
            'headers': {
                'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
            }
        }
        token = extract_token_from_event(event)
        assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    def test_extract_token_case_insensitive_header(self):
        """大文字小文字を区別しないヘッダー名でのトークン抽出をテスト"""
        event = {
            'headers': {
                'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
            }
        }
        token = extract_token_from_event(event)
        assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    def test_extract_token_mixed_case_header(self):
        """混合ケースのヘッダー名でのトークン抽出をテスト"""
        event = {
            'headers': {
                'AuThOrIzAtIoN': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
            }
        }
        token = extract_token_from_event(event)
        assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    def test_extract_token_no_headers(self):
        """ヘッダーがないイベントでValidationErrorが発生することをテスト"""
        event = {}
        with pytest.raises(ValidationError, match="認証が必要です"):
            extract_token_from_event(event)
    
    def test_extract_token_empty_headers(self):
        """空のヘッダーでValidationErrorが発生することをテスト"""
        event = {'headers': {}}
        with pytest.raises(ValidationError, match="認証が必要です"):
            extract_token_from_event(event)
    
    def test_extract_token_no_auth_header(self):
        """Authorizationヘッダーがない場合のテスト"""
        event = {
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        with pytest.raises(ValidationError, match="認証が必要です"):
            extract_token_from_event(event)


class TestValidateAndExtractUserInfo:
    """validate_and_extract_user_info関数のテスト"""
    
    @patch.object(TokenValidator, 'validate_token')
    def test_validate_and_extract_user_info_success(self, mock_validate_token):
        """ユーザー情報の抽出成功をテスト"""
        mock_payload = {
            'sub': 'user123',
            'username': 'testuser',
            'client_id': 'test_client',
            'token_use': 'access',
            'scope': 'openid profile email',
            'auth_time': 1234567890,
            'iat': 1234567890,
            'exp': 1234571490
        }
        mock_validate_token.return_value = mock_payload
        
        result = validate_and_extract_user_info('test_token', 'ap-northeast-1_test123')
        
        expected = {
            'user_id': 'user123',
            'username': 'testuser',
            'client_id': 'test_client',
            'token_use': 'access',
            'scope': ['openid', 'profile', 'email'],
            'auth_time': 1234567890,
            'iat': 1234567890,
            'exp': 1234571490
        }
        assert result == expected
    
    def test_validate_and_extract_user_info_empty_token(self):
        """空のトークンでValidationErrorが発生することをテスト"""
        with pytest.raises(ValidationError, match="認証が必要です"):
            validate_and_extract_user_info('', 'ap-northeast-1_test123')
    
    def test_validate_and_extract_user_info_empty_pool_id(self):
        """空のユーザープールIDでValidationErrorが発生することをテスト"""
        with pytest.raises(ValidationError, match="User pool ID is required"):
            validate_and_extract_user_info('test_token', '')
    
    @patch.object(TokenValidator, 'validate_token')
    def test_validate_and_extract_user_info_no_scope(self, mock_validate_token):
        """scopeがない場合の処理をテスト"""
        mock_payload = {
            'sub': 'user123',
            'username': 'testuser'
        }
        mock_validate_token.return_value = mock_payload
        
        result = validate_and_extract_user_info('test_token', 'ap-northeast-1_test123')
        
        assert result['scope'] == []


class TestRequireAuthentication:
    """require_authentication関数のテスト"""
    
    @patch('utils.auth.extract_token_from_event')
    @patch('utils.auth.validate_and_extract_user_info')
    def test_require_authentication_success(self, mock_validate, mock_extract):
        """認証成功のテスト"""
        mock_extract.return_value = 'test_token'
        mock_user_info = {'user_id': 'user123', 'username': 'testuser'}
        mock_validate.return_value = mock_user_info
        
        event = {'headers': {'Authorization': 'Bearer test_token'}}
        result = require_authentication(event, 'ap-northeast-1_test123')
        
        assert result == mock_user_info
        mock_extract.assert_called_once_with(event)
        mock_validate.assert_called_once_with('test_token', 'ap-northeast-1_test123', 'ap-northeast-1')


class TestCreateAuthErrorResponse:
    """create_auth_error_response関数のテスト"""
    
    def test_create_validation_error_response(self):
        """ValidationErrorレスポンスの作成をテスト"""
        error = ValidationError("必須パラメータが不足しています")
        response = create_auth_error_response(error)
        
        assert response['statusCode'] == 400
        assert response['body']['error'] == 'BadRequest'
        assert response['body']['message'] == "必須パラメータが不足しています"
        assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_create_authentication_error_response(self):
        """AuthenticationErrorレスポンスの作成をテスト"""
        error = AuthenticationError("認証に失敗しました")
        response = create_auth_error_response(error)
        
        assert response['statusCode'] == 401
        assert response['body']['error'] == 'AuthenticationFailed'
        assert response['body']['message'] == "認証に失敗しました"
    
    def test_create_authorization_error_response(self):
        """AuthorizationErrorレスポンスの作成をテスト"""
        error = AuthorizationError("アクセスが拒否されました")
        response = create_auth_error_response(error)
        
        assert response['statusCode'] == 401
        assert response['body']['error'] == 'Unauthorized'
        assert response['body']['message'] == "アクセスが拒否されました"
    
    def test_create_service_error_response(self):
        """ServiceErrorレスポンスの作成をテスト"""
        error = ServiceError("サービスが利用できません")
        response = create_auth_error_response(error)
        
        assert response['statusCode'] == 503
        assert response['body']['error'] == 'ServiceUnavailable'
        assert response['body']['message'] == "サービスが利用できません"
    
    def test_create_generic_error_response(self):
        """一般的なエラーレスポンスの作成をテスト"""
        error = Exception("予期しないエラー")
        response = create_auth_error_response(error)
        
        assert response['statusCode'] == 500
        assert response['body']['error'] == 'InternalServerError'
        assert response['body']['message'] == "予期しないエラー"
    
    def test_create_error_response_custom_status_code(self):
        """カスタムステータスコードでのエラーレスポンス作成をテスト"""
        error = ValidationError("カスタムエラー")
        response = create_auth_error_response(error, status_code=422)
        
        assert response['statusCode'] == 422
        assert response['body']['error'] == 'BadRequest'


class TestCreateSuccessResponse:
    """create_success_response関数のテスト"""
    
    def test_create_success_response_default(self):
        """デフォルトの成功レスポンス作成をテスト"""
        data = {'message': '成功しました', 'user_id': 'user123'}
        response = create_success_response(data)
        
        assert response['statusCode'] == 200
        assert response['body'] == data
        assert response['headers']['Content-Type'] == 'application/json'
        assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_create_success_response_custom_status(self):
        """カスタムステータスコードの成功レスポンス作成をテスト"""
        data = {'message': '作成されました'}
        response = create_success_response(data, status_code=201)
        
        assert response['statusCode'] == 201
        assert response['body'] == data
    
    def test_create_success_response_cors_headers(self):
        """CORSヘッダーが正しく設定されることをテスト"""
        data = {}
        response = create_success_response(data)
        
        headers = response['headers']
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'Authorization' in headers['Access-Control-Allow-Headers']
        assert 'GET,POST,PUT,DELETE,OPTIONS' in headers['Access-Control-Allow-Methods']