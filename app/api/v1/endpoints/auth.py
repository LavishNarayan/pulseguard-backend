from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token

router = APIRouter()

ENGINEER_USERS = {
    "admin": "pulseguard2026",
    "lead_eng": "turbine_ops",
}


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    expected_pw = ENGINEER_USERS.get(form_data.username)
    if not expected_pw or form_data.password != expected_pw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect engineer username or password",
        )
    token = create_access_token(subject=form_data.username)
    return {"access_token": token, "token_type": "bearer"}
