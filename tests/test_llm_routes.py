"""
Tests for the LLM model selection REST API endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from interfaces.webapp.app import app
from interfaces.webapp.dependencies import get_current_user_id, get_database


@pytest.fixture
def client():
    """Create test client for the FastAPI app with user settings."""
    mock_db = AsyncMock()
    mock_db.get_setting = AsyncMock(return_value=None)
    mock_db.set_setting = AsyncMock()

    with TestClient(app) as test_client:
        test_client.app.dependency_overrides[get_current_user_id] = lambda: 123456789  # type: ignore[attr-defined]
        test_client.app.dependency_overrides[get_database] = lambda: mock_db  # type: ignore[attr-defined]
        yield test_client
        test_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
def client_with_custom_settings():
    """Create test client with custom user settings."""

    async def get_setting(user_id: int, key: str, default=None):
        settings = {
            "llm_api_key": "sk-or-test-key-12345",
            "llm_base_url": "https://openrouter.ai/api/v1",
            "llm_model": "qwen/qwen3-235b-a22b:free",
        }
        return settings.get(key, default)

    mock_db = AsyncMock()
    mock_db.get_setting = AsyncMock(side_effect=get_setting)
    mock_db.set_setting = AsyncMock()

    with TestClient(app) as test_client:
        test_client.app.dependency_overrides[get_current_user_id] = lambda: 123456789  # type: ignore[attr-defined]
        test_client.app.dependency_overrides[get_database] = lambda: mock_db  # type: ignore[attr-defined]
        yield test_client
        test_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


class TestListLLMModels:
    """Tests for GET /api/v1/llm/models endpoint."""

    def test_list_models_success(self, client_with_custom_settings):
        """Test successful listing of LLM models from OpenRouter."""
        mock_models_response = {
            "data": [
                {
                    "id": "qwen/qwen3-235b-a22b:free",
                    "name": "Qwen3 235B A22B (Free)",
                    "description": "High-quality multilingual model",
                    "context_length": 32768,
                    "pricing": {"prompt": "0", "completion": "0"},
                },
                {
                    "id": "meta-llama/llama-3-8b-instruct:free",
                    "name": "Llama 3 8B Instruct (Free)",
                    "description": "Meta's efficient 8B model",
                    "context_length": 8192,
                    "pricing": {"prompt": "0", "completion": "0"},
                },
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models_response
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert "total" in data
            assert data["total"] == 2
            # Models are sorted: free first, then alphabetically by name
            # "Llama" comes before "Qwen" alphabetically
            assert data["models"][0]["id"] == "meta-llama/llama-3-8b-instruct:free"
            assert data["models"][0]["is_free"] is True

    def test_list_models_free_flag_detection(self, client_with_custom_settings):
        """Test that free models are correctly flagged."""
        mock_models_response = {
            "data": [
                {
                    "id": "some/model:free",
                    "name": "Free Model",
                    "pricing": {"prompt": "0.0001", "completion": "0.0002"},
                },
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models_response
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            # Should be free because of :free suffix
            assert data["models"][0]["is_free"] is True

    def test_list_models_free_pricing_detection(self, client_with_custom_settings):
        """Test that models with zero pricing are flagged as free."""
        mock_models_response = {
            "data": [
                {
                    "id": "some/model",
                    "name": "Free by Pricing",
                    "pricing": {"prompt": "0", "completion": "0"},
                },
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models_response
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            # Should be free because pricing is 0
            assert data["models"][0]["is_free"] is True

    def test_list_models_sorting(self, client_with_custom_settings):
        """Test that free models are sorted first."""
        mock_models_response = {
            "data": [
                {"id": "paid/model", "name": "Paid Model", "pricing": {"prompt": "0.001"}},
                {"id": "free/model:free", "name": "Free Model", "pricing": {"prompt": "0"}},
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models_response
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            # Free model should be first
            assert data["models"][0]["id"] == "free/model:free"
            assert data["models"][0]["is_free"] is True

    def test_list_models_401_invalid_key(self, client_with_custom_settings):
        """Test error when API key is invalid."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 401
            assert "Invalid LLM API key" in response.json()["detail"]

    def test_list_models_403_permission_denied(self, client_with_custom_settings):
        """Test error when API key lacks permissions."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 403
            assert "LLM API key lacks permission" in response.json()["detail"]

    def test_list_models_fallback_on_network_error(self, client_with_custom_settings):
        """Test that fallback models are returned on network error."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert data["total"] > 0
            # Should contain known free models
            model_ids = [m["id"] for m in data["models"]]
            assert any(":free" in mid for mid in model_ids)

    def test_list_models_fallback_on_http_error(self, client_with_custom_settings):
        """Test that fallback models are returned on HTTP error."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            response = client_with_custom_settings.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] > 0

    def test_list_models_no_api_key(self, client):
        """Test that fallback models are returned when no API key is configured."""
        # When no API key is set, the endpoint returns fallback models
        response = client.get("/api/v1/llm/models")

        # Should return 200 with fallback models (not 400)
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert data["total"] > 0

    def test_list_models_custom_base_url(self, client):
        """Test listing models with custom base URL."""

        async def get_setting(user_id: int, key: str, default=None):
            settings = {
                "llm_api_key": "test-key",
                "llm_base_url": "https://custom-llm-api.com/v1",
            }
            return settings.get(key, default)

        mock_db = AsyncMock()
        mock_db.get_setting = AsyncMock(side_effect=get_setting)
        mock_db.set_setting = AsyncMock()

        client.app.dependency_overrides[get_database] = lambda: mock_db  # type: ignore[attr-defined]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            mock_get.return_value = mock_response

            response = client.get("/api/v1/llm/models")

            assert response.status_code == 200
            # Verify the URL was constructed with custom base URL
            # The code replaces "/v1" and adds "/api/v1/models" for OpenRouter
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            # For non-OpenRouter URLs, it just appends /models
            assert "custom-llm-api.com" in call_url or call_url.endswith("/models")


class TestSelectLLMModel:
    """Tests for PUT /api/v1/llm/model endpoint."""

    def test_select_model_success(self, client):
        """Test successful model selection."""
        payload = {"model_id": "meta-llama/llama-3-8b-instruct:free"}

        response = client.put("/api/v1/llm/model", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "meta-llama/llama-3-8b-instruct:free"
        assert data["saved"] is True

    def test_select_model_strips_whitespace(self, client):
        """Test that model_id is trimmed."""
        payload = {"model_id": "  qwen/qwen3-235b-a22b:free  "}

        response = client.put("/api/v1/llm/model", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "qwen/qwen3-235b-a22b:free"

    def test_select_model_empty_id(self, client):
        """Test error when model_id is empty."""
        payload = {"model_id": ""}

        response = client.put("/api/v1/llm/model", json=payload)

        assert response.status_code == 400
        assert "Model ID cannot be empty" in response.json()["detail"]

    def test_select_model_whitespace_only(self, client):
        """Test error when model_id is whitespace only."""
        payload = {"model_id": "   "}

        response = client.put("/api/v1/llm/model", json=payload)

        assert response.status_code == 400
        assert "Model ID cannot be empty" in response.json()["detail"]

    def test_select_model_saves_to_database(self, client):
        """Test that model is saved to database."""
        payload = {"model_id": "google/gemma-2-9b-it:free"}

        response = client.put("/api/v1/llm/model", json=payload)

        assert response.status_code == 200
        # Verify set_setting was called
        mock_db = client.app.dependency_overrides[get_database]()  # type: ignore[attr-defined]
        mock_db.set_setting.assert_called_once_with(
            123456789,
            "llm_model",
            "google/gemma-2-9b-it:free",
            encrypt_value=False,
        )


class TestGetLLMModel:
    """Tests for GET /api/v1/llm/model endpoint."""

    def test_get_model_user_setting(self, client_with_custom_settings):
        """Test getting user's selected model."""
        response = client_with_custom_settings.get("/api/v1/llm/model")

        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "qwen/qwen3-235b-a22b:free"
        assert data["is_default"] is False

    def test_get_model_default(self, client):
        """Test getting default model when user has no setting."""
        response = client.get("/api/v1/llm/model")

        assert response.status_code == 200
        data = response.json()
        # Should return default from env
        assert "model_id" in data
        assert data["is_default"] is True

    def test_get_model_returns_configured_default(self, client):
        """Test that the configured default model is returned."""
        response = client.get("/api/v1/llm/model")

        assert response.status_code == 200
        data = response.json()
        # Default from .env (may vary based on configuration)
        assert "model_id" in data
        assert isinstance(data["model_id"], str)
        assert len(data["model_id"]) > 0


class TestPingLLMEndpoint:
    """Tests for POST /api/v1/llm/ping endpoint."""

    def test_ping_success(self, client):
        """Test successful ping."""
        with patch("infrastructure.external_api.llm_client.ping_llm") as mock_ping:
            mock_ping.return_value = "qwen/qwen3-235b-a22b:free"

            response = client.post("/api/v1/llm/ping")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["model"] == "qwen/qwen3-235b-a22b:free"

    def test_ping_failure(self, client):
        """Test ping failure."""
        with patch("infrastructure.external_api.llm_client.ping_llm") as mock_ping:
            mock_ping.side_effect = Exception("Connection refused")

            response = client.post("/api/v1/llm/ping")

            assert response.status_code == 503
            assert "LLM connectivity test failed" in response.json()["detail"]
