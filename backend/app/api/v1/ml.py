from fastapi import APIRouter

from app.api.deps import ML, AppSettings, CurrentUser
from app.core.exceptions import ValidationFailed
from app.schemas.analysis import AnalysisResult, ModelInfo, PredictRequest

router = APIRouter(prefix="/ml", tags=["ML Prediction"])


@router.post("/predict", response_model=AnalysisResult)
async def predict(data: PredictRequest, _: CurrentUser, ml: ML, settings: AppSettings):
    """Stateless analysis of a sample window (nothing is stored)."""
    if len(data.samples) > settings.max_samples_per_session:
        raise ValidationFailed("Too many samples in one request", code="BATCH_TOO_LARGE")
    samples = [s.model_dump() for s in data.samples]
    return await ml.analyze(samples, data.exercise_id, mode="standalone", include_features=data.include_features)


@router.get("/model-info", response_model=ModelInfo)
async def model_info(_: CurrentUser, ml: ML):
    return ml.info()
