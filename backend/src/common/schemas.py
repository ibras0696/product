from pydantic import BaseModel


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ResponseMeta(BaseModel):
    request_id: str | None = None


class ApiResponse[T](BaseModel):
    ok: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ResponseMeta | None = None

    @classmethod
    def success(cls, data: T, request_id: str | None = None) -> "ApiResponse[T]":
        return cls(ok=True, data=data, meta=ResponseMeta(request_id=request_id))
