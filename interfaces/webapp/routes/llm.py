"""
LLM-related API endpoints: model listing, connectivity testing.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from infrastructure.database.database import Database
from interfaces.webapp.dependencies import get_current_user_id, get_database
from interfaces.webapp.schemas import LLMModel, LLMModelsResponse
from shared.config import LLM_API_KEY, LLM_BASE_URL

router = APIRouter(tags=["llm"])
logger = logging.getLogger(__name__)


@router.get("/llm/models", response_model=LLMModelsResponse)
async def list_llm_models(
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> LLMModelsResponse:
    """
    Fetch available LLM models from OpenRouter (or configured LLM_BASE_URL).

    Returns a list of models with their metadata, prioritizing free models.
    """
    # Get user's API key or use default
    user_api_key = await db.get_setting(user_id, "llm_api_key")
    api_key = user_api_key or LLM_API_KEY

    if not api_key:
        raise HTTPException(status_code=400, detail="No LLM API key configured")

    # Get user's base URL or use default
    base_url = await db.get_setting(user_id, "llm_base_url")
    base_url = base_url or LLM_BASE_URL

    try:
        # OpenRouter models endpoint
        models_url = (
            base_url.replace("/v1", "") + "/api/v1/models" if "openrouter" in base_url else f"{base_url}/models"
        )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                models_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://github.com/tg-voice-bot",
                    "X-Title": "TG Voice Bot",
                },
            )

            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid LLM API key")
            if response.status_code == 403:
                raise HTTPException(status_code=403, detail="LLM API key lacks permission to list models")
            if response.status_code != 200:
                logger.warning("Failed to fetch models: %d - %s", response.status_code, response.text[:200])
                # Fallback: return a default list of known free models
                return _get_fallback_models()

            data = response.json()

    except httpx.RequestError as e:
        logger.exception("Failed to fetch LLM models: %s", e)
        # Return fallback models on network error
        return _get_fallback_models()

    # Parse OpenRouter response
    models = []
    raw_models = data.get("data", [])

    for model in raw_models:
        model_id = model.get("id", "")
        name = model.get("name", model_id)
        description = model.get("description")
        context_length = model.get("context_length")
        pricing = model.get("pricing", {})

        # Check if it's a free model
        is_free = ":free" in model_id or (pricing and pricing.get("prompt") == "0")

        models.append(
            LLMModel(
                id=model_id,
                name=name,
                description=description,
                context_length=context_length,
                pricing=pricing,
                is_free=is_free,
            )
        )

    # Sort: free models first, then by name
    models.sort(key=lambda m: (not m.is_free, m.name.lower()))

    return LLMModelsResponse(models=models, total=len(models))


def _get_fallback_models() -> LLMModelsResponse:
    """Return a fallback list of known free models when API is unavailable."""
    fallback = [
        LLMModel(
            id="qwen/qwen3-235b-a22b:free",
            name="Qwen3 235B A22B (Free)",
            description="High-quality multilingual model from Alibaba",
            is_free=True,
        ),
        LLMModel(
            id="meta-llama/llama-3-8b-instruct:free",
            name="Llama 3 8B Instruct (Free)",
            description="Meta's efficient 8B parameter model",
            is_free=True,
        ),
        LLMModel(
            id="google/gemma-2-9b-it:free",
            name="Gemma 2 9B IT (Free)",
            description="Google's instruction-tuned 9B model",
            is_free=True,
        ),
        LLMModel(
            id="mistralai/mistral-7b-instruct:free",
            name="Mistral 7B Instruct (Free)",
            description="Popular open-weight 7B model",
            is_free=True,
        ),
        LLMModel(
            id="nvidia/nemotron-4-340b-instruct:free",
            name="Nemotron 4 340B (Free)",
            description="NVIDIA's large instruction model",
            is_free=True,
        ),
    ]
    return LLMModelsResponse(models=fallback, total=len(fallback))


@router.post("/llm/ping")
async def ping_llm_endpoint(
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    """
    Test LLM API connectivity with the user's configured credentials.

    Returns the model name on success.
    """
    from infrastructure.external_api.llm_client import ping_llm

    try:
        model = await ping_llm()
        return {"status": "ok", "model": model}
    except Exception as e:
        logger.exception("LLM ping failed for user_id=%d", user_id)
        raise HTTPException(status_code=503, detail=f"LLM connectivity test failed: {str(e)}") from e


class ModelSelectRequest(BaseModel):
    """Request body for selecting an LLM model."""

    model_id: str


@router.put("/llm/model")
async def select_llm_model(
    body: ModelSelectRequest,
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    """
    Save the user's selected LLM model to their settings.

    The model_id is stored in the 'llm_model' setting.
    """
    # Validate model_id is not empty
    if not body.model_id or not body.model_id.strip():
        raise HTTPException(status_code=400, detail="Model ID cannot be empty")

    model_id = body.model_id.strip()

    # Optional: Validate model exists by checking against the API
    # For now, we just save it - validation happens on first use

    await db.set_setting(user_id, "llm_model", model_id, encrypt_value=False)
    logger.info("LLM model selected: user_id=%d model=%s", user_id, model_id)

    return {"model_id": model_id, "saved": True}


@router.get("/llm/model")
async def get_llm_model(
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    """
    Get the user's currently selected LLM model.

    Returns the model_id from user settings, or the default from env if not set.
    """
    from shared.config import LLM_MODEL

    user_model = await db.get_setting(user_id, "llm_model")
    model_id = user_model or LLM_MODEL

    return {"model_id": model_id, "is_default": user_model is None}
