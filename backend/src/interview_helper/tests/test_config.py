import pytest
from unittest.mock import patch
from typing import cast
from pydantic import SecretStr, ValidationError

from interview_helper.config import Settings


def test_settings_from_environment():
    """Test environment variable loading"""
    env_vars = {
        "SERVER_HOST": "127.0.0.1",
        "SERVER_PORT": "8000",
        "CORS_ALLOW_ORIGINS": "https://localhost:3000,https://example.com",
        "OIDC_AUTHORITY": "https://cognito-idp.us-east-1.amazonaws.com",
        "OIDC_CLIENT_ID": "AWS-clientID",
        "OPENAI_API_ENDPOINT": "https://endpoint.com",
        "OPENAI_API_KEY": "sample_openai_api_key",
        "AZURE_DEPLOYMENT": "gpt-5",
        "AZURE_EVAL_DEPLOYMENT": "gpt-4o-mini",
    }

    with patch.dict("os.environ", env_vars, clear=True):
        # type: ignore (we are testing environment)
        settings = Settings()

        assert settings.server_host == "127.0.0.1"
        assert settings.server_port == 8000
        assert settings.cors_allow_origins == [
            "https://localhost:3000",
            "https://example.com",
        ]


def test_cors_origins_list_string_parsing():
    """Test that CORS origins list is passed through unchanged"""

    origin1 = "https://localhost:3000"
    origin2 = "https://localhost:3001"

    # Required since it will turn into a list[str] via validation
    origins_list = cast(list[str], f"{origin1},{origin2}")

    with patch.dict("os.environ", {}, clear=True):
        settings = Settings(
            CORS_ALLOW_ORIGINS=origins_list,
            OIDC_AUTHORITY="test",
            OIDC_CLIENT_ID="client_id",
            OPENAI_API_ENDPOINT="https://endpoint.com",
            OPENAI_API_KEY=SecretStr("sample_openai_api_key"),
            AZURE_DEPLOYMENT="gpt-5",
            AZURE_EVAL_DEPLOYMENT="gpt-4o-mini",
        )
        assert settings.cors_allow_origins == [origin1, origin2]


def test_empty_cors_origins_raises_error():
    """Test that empty CORS_ALLOW_ORIGINS raises ValueError"""
    with patch.dict("os.environ", {"CORS_ALLOW_ORIGINS": ""}, clear=True):
        with pytest.raises(ValueError, match="Missing.*CORS_ALLOW_ORIGINS"):
            _ = Settings(
                OIDC_AUTHORITY="",
                OIDC_CLIENT_ID="",
                OPENAI_API_ENDPOINT="",
                OPENAI_API_KEY=SecretStr(""),
                AZURE_DEPLOYMENT="",
                AZURE_EVAL_DEPLOYMENT="gpt-4o-mini",
            )


def test_split_origins_splits_comma_separated_string():
    """Test that split_origins splits comma-separated string"""

    result = Settings.split_origins("https://localhost:3000,https://example.com")
    assert result == ["https://localhost:3000", "https://example.com"]


def test_split_origins_accepts_list():
    """Test that split_origins passes through list input"""

    origins_list = ["https://localhost:3000", "https://example.com"]
    result = Settings.split_origins(origins_list)
    assert result == origins_list


def test_split_origins_cleans_bracketed_string():
    """Test that split_origins cleans bracketed string"""

    result = Settings.split_origins("[https://localhost:3000,https://example.com]")
    assert result == ["https://localhost:3000", "https://example.com"]


def test_split_origins_removes_empty_strings():
    """Test that split_origins does not include empty strings"""

    result = Settings.split_origins("[https://localhost:3000,https://example.com,]")
    assert result == ["https://localhost:3000", "https://example.com"]


def test_split_origins_empty_string_results_in_empty_list():
    """Test that split_origins returns empty list for empty string"""

    result = Settings.split_origins("")
    assert result == []


def test_settings_immutability():
    """Test that settings can't be modified"""
    with patch.dict(
        "os.environ",
        {
            "CORS_ALLOW_ORIGINS": "https://localhost:3000",
            "OIDC_AUTHORITY": "https://cognito-idp.us-east-1.amazonaws.com",
            "OIDC_CLIENT_ID": "AWS-clientID",
            "OPENAI_API_ENDPOINT": "https://endpoint.com",
            "OPENAI_API_KEY": "sample_openai_api_key",
            "AZURE_DEPLOYMENT": "gpt-5",
        },
        clear=True,
    ):
        # type: ignore (using mocked environment)
        instance = Settings()

        with pytest.raises(ValidationError, match="frozen"):
            instance.cors_allow_origins = []

        with pytest.raises(ValidationError, match="frozen"):
            instance.server_host = "127.0.0.1"
