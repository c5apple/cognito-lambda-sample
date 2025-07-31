"""
Cognitoクライアントラッパーの単体テスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import os

from utils.cognito import (
    CognitoClient, 
    CognitoError,
    AuthenticationError,
    AuthorizationError, 
    ValidationError,
    ServiceError,
    get_cognito_client
)


class TestCognitoClient:
    """CognitoClientクラスのテスト"""
    
    @patch.dict(os.environ, {
        'COGNITO_USER_POOL_ID': 'ap-northeast-1_test123',
        'COGNITO_CLIENT_ID': 'test_client_id',
        'AWS_REGION': 'ap-northeast-1'
    })
    @patch('utils.cognito.boto3.client')
    def test_initialization_with_env_vars(self, mock_boto_client):
        """環境変数からの初期化をテスト"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        client = CognitoClient()
        
        assert client.user_pool_id == 'ap-northeast-1_test123'
        assert client.client_id == 'test_client_id'
        assert client.region == 'ap-northeast-1'
        mock_boto_client.assert_called_once_with('cognito-idp', region_name='ap-northeast-1')
    
    @patch('utils.cognito.boto3.client')
    def test_initialization_with_parameters(self, mock_boto_client):
        """パラメータからの初期化をテスト"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        client = CognitoClient(
            user_pool_id='custom_pool',
            client_id='custom_client',
            region='us-west-2'
        )
        
        assert client.user_pool_id == 'custom_pool'
        assert client.client_id == 'custom_client'
        assert client.region == 'us-west-2'
    
    def test_initialization_missing_user_pool_id(self):
        """user_pool_idが不足している場合のテスト"""
        with pytest.raises(ValidationError, match="COGNITO_USER_POOL_ID is required"):
            CognitoClient(client_id='test_client')
    
    def test_initialization_missing_client_id(self):
        """client_idが不足している場合のテスト"""
        with pytest.raises(ValidationError, match="COGNITO_CLIENT_ID is required"):
            CognitoClient(user_pool_id='test_pool')
    
    @patch('utils.cognito.boto3.client')
    def test_initialization_boto3_error(self, mock_boto_client):
        """boto3初期化エラーのテスト"""
        mock_boto_client.side_effect = Exception("AWS client error")
        
        with pytest.raises(ServiceError, match="Failed to initialize Cognito client"):
            CognitoClient(user_pool_id='test_pool', client_id='test_client')


class TestAuthenticate:
    """authenticate メソッドのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_cognito_client = Mock()
        with patch('utils.cognito.boto3.client', return_value=self.mock_cognito_client):
            self.client = CognitoClient(
                user_pool_id='test_pool',
                client_id='test_client'
            )
    
    def test_authenticate_success(self):
        """正常な認証のテスト"""
        mock_response = {
            'AuthenticationResult': {
                'AccessToken': 'access_token_123',
                'RefreshToken': 'refresh_token_123',
                'IdToken': 'id_token_123',
                'TokenType': 'Bearer',
                'ExpiresIn': 3600
            }
        }
        self.mock_cognito_client.initiate_auth.return_value = mock_response
        
        result = self.client.authenticate('test@example.com', 'password123')
        
        assert result['access_token'] == 'access_token_123'
        assert result['refresh_token'] == 'refresh_token_123'
        assert result['token_type'] == 'Bearer'
        assert result['expires_in'] == 3600
        
        self.mock_cognito_client.initiate_auth.assert_called_once_with(
            ClientId='test_client',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': 'test@example.com',
                'PASSWORD': 'password123'
            }
        )
    
    def test_authenticate_missing_email(self):
        """メールアドレス不足のテスト"""
        with pytest.raises(ValidationError, match="Email and password are required"):
            self.client.authenticate('', 'password123')
    
    def test_authenticate_missing_password(self):
        """パスワード不足のテスト"""
        with pytest.raises(ValidationError, match="Email and password are required"):
            self.client.authenticate('test@example.com', '')
    
    def test_authenticate_not_authorized(self):
        """認証失敗のテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'NotAuthorizedException',
                    'Message': 'Incorrect username or password.'
                }
            },
            operation_name='InitiateAuth'
        )
        self.mock_cognito_client.initiate_auth.side_effect = error
        
        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.client.authenticate('test@example.com', 'wrong_password')
    
    def test_authenticate_user_not_found(self):
        """ユーザーが存在しない場合のテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UserNotFoundException',
                    'Message': 'User does not exist.'
                }
            },
            operation_name='InitiateAuth'
        )
        self.mock_cognito_client.initiate_auth.side_effect = error
        
        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.client.authenticate('nonexistent@example.com', 'password123')


class TestLogout:
    """logout メソッドのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_cognito_client = Mock()
        with patch('utils.cognito.boto3.client', return_value=self.mock_cognito_client):
            self.client = CognitoClient(
                user_pool_id='test_pool',
                client_id='test_client'
            )
    
    def test_logout_success(self):
        """正常なログアウトのテスト"""
        self.mock_cognito_client.global_sign_out.return_value = {}
        
        result = self.client.logout('access_token_123')
        
        assert result['success'] is True
        assert result['message'] == "Successfully logged out"
        
        self.mock_cognito_client.global_sign_out.assert_called_once_with(
            AccessToken='access_token_123'
        )
    
    def test_logout_missing_token(self):
        """アクセストークン不足のテスト"""
        with pytest.raises(ValidationError, match="Access token is required"):
            self.client.logout('')
    
    def test_logout_invalid_token(self):
        """無効なトークンのテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'NotAuthorizedException',
                    'Message': 'Access Token has expired'
                }
            },
            operation_name='GlobalSignOut'
        )
        self.mock_cognito_client.global_sign_out.side_effect = error
        
        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.client.logout('expired_token')


class TestGetUserInfo:
    """get_user_info メソッドのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_cognito_client = Mock()
        with patch('utils.cognito.boto3.client', return_value=self.mock_cognito_client):
            self.client = CognitoClient(
                user_pool_id='test_pool',
                client_id='test_client'
            )
    
    def test_get_user_info_success(self):
        """正常なユーザー情報取得のテスト"""
        mock_response = {
            'Username': 'test@example.com',
            'UserAttributes': [
                {'Name': 'sub', 'Value': '12345678-1234-1234-1234-123456789012'},
                {'Name': 'email', 'Value': 'test@example.com'},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'given_name', 'Value': 'John'},
                {'Name': 'family_name', 'Value': 'Doe'}
            ]
        }
        self.mock_cognito_client.get_user.return_value = mock_response
        
        result = self.client.get_user_info('access_token_123')
        
        assert result['user_id'] == '12345678-1234-1234-1234-123456789012'
        assert result['username'] == 'test@example.com'
        assert result['email'] == 'test@example.com'
        assert result['attributes']['email_verified'] is True
        assert result['attributes']['given_name'] == 'John'
        assert result['attributes']['family_name'] == 'Doe'
        
        self.mock_cognito_client.get_user.assert_called_once_with(
            AccessToken='access_token_123'
        )
    
    def test_get_user_info_missing_token(self):
        """アクセストークン不足のテスト"""
        with pytest.raises(ValidationError, match="Access token is required"):
            self.client.get_user_info('')


class TestCreateUser:
    """create_user メソッドのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_cognito_client = Mock()
        with patch('utils.cognito.boto3.client', return_value=self.mock_cognito_client):
            self.client = CognitoClient(
                user_pool_id='test_pool',
                client_id='test_client'
            )
    
    def test_create_user_success(self):
        """正常なユーザー作成のテスト"""
        mock_response = {
            'User': {
                'Username': 'test@example.com',
                'UserStatus': 'FORCE_CHANGE_PASSWORD',
                'UserCreateDate': '2023-01-01T00:00:00Z'
            }
        }
        self.mock_cognito_client.admin_create_user.return_value = mock_response
        
        result = self.client.create_user('test@example.com', 'TempPass123!')
        
        assert result['success'] is True
        assert result['user_id'] == 'test@example.com'
        assert result['status'] == 'FORCE_CHANGE_PASSWORD'
        
        self.mock_cognito_client.admin_create_user.assert_called_once()
        call_args = self.mock_cognito_client.admin_create_user.call_args
        assert call_args[1]['UserPoolId'] == 'test_pool'
        assert call_args[1]['Username'] == 'test@example.com'
        assert call_args[1]['TemporaryPassword'] == 'TempPass123!'
    
    def test_create_user_with_attributes(self):
        """属性付きユーザー作成のテスト"""
        mock_response = {
            'User': {
                'Username': 'test@example.com',
                'UserStatus': 'FORCE_CHANGE_PASSWORD'
            }
        }
        self.mock_cognito_client.admin_create_user.return_value = mock_response
        
        attributes = {
            'given_name': 'John',
            'family_name': 'Doe'
        }
        
        result = self.client.create_user('test@example.com', 'TempPass123!', attributes)
        
        assert result['success'] is True
        
        call_args = self.mock_cognito_client.admin_create_user.call_args
        user_attributes = call_args[1]['UserAttributes']
        
        # 基本属性の確認
        email_attr = next(attr for attr in user_attributes if attr['Name'] == 'email')
        assert email_attr['Value'] == 'test@example.com'
        
        # 追加属性の確認
        given_name_attr = next(attr for attr in user_attributes if attr['Name'] == 'given_name')
        assert given_name_attr['Value'] == 'John'
    
    def test_create_user_missing_email(self):
        """メールアドレス不足のテスト"""
        with pytest.raises(ValidationError, match="Email and password are required"):
            self.client.create_user('', 'password123')
    
    def test_create_user_already_exists(self):
        """既存ユーザーのテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UsernameExistsException',
                    'Message': 'An account with the given email already exists.'
                }
            },
            operation_name='AdminCreateUser'
        )
        self.mock_cognito_client.admin_create_user.side_effect = error
        
        with pytest.raises(ValidationError, match="リクエストが不正です"):
            self.client.create_user('existing@example.com', 'password123')


class TestDeleteUser:
    """delete_user メソッドのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_cognito_client = Mock()
        with patch('utils.cognito.boto3.client', return_value=self.mock_cognito_client):
            self.client = CognitoClient(
                user_pool_id='test_pool',
                client_id='test_client'
            )
    
    def test_delete_user_success(self):
        """正常なユーザー削除のテスト"""
        self.mock_cognito_client.admin_delete_user.return_value = {}
        
        result = self.client.delete_user('test@example.com')
        
        assert result['success'] is True
        assert 'test@example.com' in result['message']
        
        self.mock_cognito_client.admin_delete_user.assert_called_once_with(
            UserPoolId='test_pool',
            Username='test@example.com'
        )
    
    def test_delete_user_missing_email(self):
        """メールアドレス不足のテスト"""
        with pytest.raises(ValidationError, match="Email is required"):
            self.client.delete_user('')
    
    def test_delete_user_not_found(self):
        """存在しないユーザーのテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UserNotFoundException',
                    'Message': 'User does not exist.'
                }
            },
            operation_name='AdminDeleteUser'
        )
        self.mock_cognito_client.admin_delete_user.side_effect = error
        
        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.client.delete_user('nonexistent@example.com')


class TestHelperFunctions:
    """ヘルパー関数のテスト"""
    
    @patch.dict(os.environ, {
        'COGNITO_USER_POOL_ID': 'ap-northeast-1_helper_test',
        'COGNITO_CLIENT_ID': 'helper_client_id'
    })
    @patch('utils.cognito.boto3.client')
    def test_get_cognito_client(self, mock_boto_client):
        """get_cognito_client関数のテスト"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        client = get_cognito_client()
        
        assert isinstance(client, CognitoClient)
        assert client.user_pool_id == 'ap-northeast-1_helper_test'
        assert client.client_id == 'helper_client_id'


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_cognito_client = Mock()
        with patch('utils.cognito.boto3.client', return_value=self.mock_cognito_client):
            self.client = CognitoClient(
                user_pool_id='test_pool',
                client_id='test_client'
            )
    
    def test_service_error_handling(self):
        """サービスエラーのハンドリングテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'InternalErrorException',
                    'Message': 'Internal server error.'
                }
            },
            operation_name='InitiateAuth'
        )
        self.mock_cognito_client.initiate_auth.side_effect = error
        
        with pytest.raises(ServiceError, match="サービスエラーが発生しました"):
            self.client.authenticate('test@example.com', 'password123')
    
    def test_validation_error_handling(self):
        """バリデーションエラーのハンドリングテスト"""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidParameterException',
                    'Message': 'Invalid parameter value.'
                }
            },
            operation_name='InitiateAuth'
        )
        self.mock_cognito_client.initiate_auth.side_effect = error
        
        with pytest.raises(ValidationError, match="リクエストが不正です"):
            self.client.authenticate('test@example.com', 'password123')
    
    def test_unexpected_error_handling(self):
        """予期しないエラーのハンドリングテスト"""
        self.mock_cognito_client.initiate_auth.side_effect = Exception("Unexpected error")
        
        with pytest.raises(ServiceError, match="Unexpected error during authentication"):
            self.client.authenticate('test@example.com', 'password123')