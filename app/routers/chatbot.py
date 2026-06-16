from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def chatbot_test():
    return {"message": "Chatbot router working"}