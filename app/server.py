from fastapi import FastAPI

from app.api.v1 import scrap


app = FastAPI()

@app.get("/")
def check_health():
    return {
        "status":"Success",
        "message":"Api Is Online"
    }

app.include_router(scrap.router)