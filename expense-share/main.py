from fastapi import FastAPI
from api import users
from config import get_settings

settings = get_settings()

app = FastAPI(
    title="Expense Sharing App (FastAPI)",
    description="API for managing shared expenses between users",
)

app.include_router(users.router)

## Health check Todo: can remove this
@app.get("/health-check")
async def health_check():
    return {"status": "healthy"}