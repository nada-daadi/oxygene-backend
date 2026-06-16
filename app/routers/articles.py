from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def auth_test():
    return {"message": "Articles router working"}