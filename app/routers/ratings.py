from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def ratings_test():
    return {"message": "Ratings router working"}