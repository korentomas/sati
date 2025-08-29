from fastapi import HTTPException, status


def invalid_credentials_error():
    """Return HTTP 401 for invalid credentials."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def user_not_found_error():
    """Return HTTP 404 for user not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


def api_key_not_found_error():
    """Return HTTP 404 for API key not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="API key not found"
    )


def api_key_creation_error():
    """Return HTTP 500 for API key creation failure."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create API key"
    )