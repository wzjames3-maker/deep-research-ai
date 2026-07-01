from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    http_status: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, http_status: int | None = None, headers: dict[str, str] | None = None):
        self.message = message
        if http_status is not None:
            self.http_status = http_status
        self.headers = headers or {}
        super().__init__(message)


class InvalidCredentialsError(AppException):
    http_status = 401
    code = "INVALID_CREDENTIALS"


class TokenInvalidError(AppException):
    http_status = 401
    code = "TOKEN_INVALID"


class AccountLockedError(AppException):
    http_status = 423
    code = "ACCOUNT_LOCKED"


class UsernameExistsError(AppException):
    http_status = 409
    code = "USERNAME_EXISTS"


class InvalidUsernameError(AppException):
    http_status = 400
    code = "INVALID_USERNAME"


class InvalidPasswordError(AppException):
    http_status = 400
    code = "INVALID_PASSWORD"


class RateLimitedError(AppException):
    http_status = 429
    code = "RATE_LIMITED"


class NotFoundError(AppException):
    http_status = 404
    code = "NOT_FOUND"


class ForbiddenError(AppException):
    http_status = 403
    code = "FORBIDDEN"


class InvalidStatusError(AppException):
    http_status = 400
    code = "INVALID_STATUS"


class ResearchInProgressError(AppException):
    http_status = 409
    code = "RESEARCH_IN_PROGRESS"


class TooManyRevisionsError(AppException):
    http_status = 400
    code = "TOO_MANY_REVISIONS"


class ReportNotReadyError(AppException):
    http_status = 400
    code = "REPORT_NOT_READY"


class PlanGenerationFailedError(AppException):
    http_status = 500
    code = "PLAN_GENERATION_FAILED"


class PlanGenerationTimeoutError(AppException):
    http_status = 504
    code = "PLAN_GENERATION_TIMEOUT"


class InvalidTopicError(AppException):
    http_status = 400
    code = "INVALID_TOPIC"


class InvalidTemplateError(AppException):
    http_status = 400
    code = "INVALID_TEMPLATE"


class ServiceUnavailableError(AppException):
    http_status = 503
    code = "SERVICE_UNAVAILABLE"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message},
        headers=exc.headers,
    )
