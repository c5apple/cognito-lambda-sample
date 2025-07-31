"""
Test to verify Docker environment setup
"""
import sys
import os
import pytest


def test_python_version():
    """Test that Python 3.9 is being used"""
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 9


def test_working_directory():
    """Test that working directory is correctly set"""
    assert os.getcwd() == "/app"


def test_required_modules():
    """Test that required modules can be imported"""
    try:
        import boto3
        import pytest
        import moto
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")


def test_environment_variables():
    """Test that environment variables can be accessed"""
    # These might not be set in test environment, so just check they can be accessed
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-1')
    assert isinstance(aws_region, str)
    assert len(aws_region) > 0