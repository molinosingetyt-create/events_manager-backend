from fastapi import HTTPException, status


class AppException(HTTPException):
    pass


def not_found(detail: str = "Recurso no encontrado") -> AppException:
    return AppException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def forbidden(detail: str = "Acceso denegado") -> AppException:
    return AppException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def bad_request(detail: str = "Solicitud incorrecta") -> AppException:
    return AppException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def unauthorized(detail: str = "No autenticado") -> AppException:
    return AppException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
