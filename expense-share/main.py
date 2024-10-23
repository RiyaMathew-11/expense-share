from fastapi import FastAPI
from config import get_settings

settings = get_settings()

app = FastAPI(
    title="Expense Sharing App (FastAPI)",
    description="API for managing shared expenses between users",
)


## Health check Todo: can remove this
@app.get("/health-check")
async def health_check():
    return {"status": "healthy"}