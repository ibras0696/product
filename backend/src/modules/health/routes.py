from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import ApiResponse
from infrastructure.broker_probe import BrokerHealthProbe
from infrastructure.database import get_session
from infrastructure.redis_client import RedisHealthProbe
from modules.health.repository import HealthRepository
from modules.health.schemas import HealthStatus
from modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_health_service(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthService:
    return HealthService(
        repository=HealthRepository(session),
        redis_probe=RedisHealthProbe().ping,
        broker_probe=BrokerHealthProbe().ping,
    )


@router.get("/live", response_model=ApiResponse[HealthStatus])
async def liveness(request: Request) -> ApiResponse[HealthStatus]:
    return ApiResponse[HealthStatus].success(
        HealthStatus(status="alive"), request_id=request.state.request_id
    )


@router.get("/ready", response_model=ApiResponse[HealthStatus])
async def readiness(
    request: Request,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> ApiResponse[HealthStatus]:
    result = await service.readiness()
    return ApiResponse[HealthStatus].success(result, request_id=request.state.request_id)
