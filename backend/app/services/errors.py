from fastapi import HTTPException, status


def not_found(what: str, key: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} '{key}' not found")
