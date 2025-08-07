import pytest
from unittest.mock import patch
from typing import cast
from interview_helper.config import Settings
from pydantic import ValidationError


def test_settings_from_environment():
    """Test environment variable loading"""
    env_vars = {
        "SERVER_HOST": "127.0.0.1",
        "SERVER_PORT": "8000",
        "CORS_ALLOW_ORIGINS": "https://localhost:3000,https://example.com",
    }

    with patch.dict("os.environ", env_vars, clear=True):
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
        settings = Settings(CORS_ALLOW_ORIGINS=origins_list)
        assert settings.cors_allow_origins == [origin1, origin2]


def test_empty_cors_origins_raises_error():
    """Test that empty CORS_ALLOW_ORIGINS raises ValueError"""
    with patch.dict("os.environ", {"CORS_ALLOW_ORIGINS": ""}, clear=True):
        with pytest.raises(ValueError, match="Missing.*CORS_ALLOW_ORIGINS"):
            Settings()


def test_split_origins_splits_comma_separated_string():
    """Test that split_origins splits comma-separated string"""
    from interview_helper.config import Settings

    result = Settings.split_origins("https://localhost:3000,https://example.com")
    assert result == ["https://localhost:3000", "https://example.com"]


def test_split_origins_accepts_list():
    """Test that split_origins passes through list input"""
    from interview_helper.config import Settings

    origins_list = ["https://localhost:3000", "https://example.com"]
    result = Settings.split_origins(origins_list)
    assert result == origins_list


def test_split_origins_cleans_bracketed_string():
    """Test that split_origins cleans bracketed string"""
    from interview_helper.config import Settings

    result = Settings.split_origins("[https://localhost:3000,https://example.com]")
    assert result == ["https://localhost:3000", "https://example.com"]


def test_split_origins_removes_empty_strings():
    """Test that split_origins does not include empty strings"""
    from interview_helper.config import Settings

    result = Settings.split_origins("[https://localhost:3000,https://example.com,]")
    assert result == ["https://localhost:3000", "https://example.com"]


def test_split_origins_empty_string_results_in_empty_list():
    """Test that split_origins returns empty list for empty string"""
    from interview_helper.config import Settings

    result = Settings.split_origins("")
    assert result == []


def test_settings_immutability():
    """Test that settings can't be modified"""
    with patch.dict(
        "os.environ", {"CORS_ALLOW_ORIGINS": "https://localhost:3000"}, clear=True
    ):
        instance = Settings()

        with pytest.raises(ValidationError, match="frozen"):
            instance.cors_allow_origins = []

        with pytest.raises(ValidationError, match="frozen"):
            instance.server_host = "127.0.0.1"
