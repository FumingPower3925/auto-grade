import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from config.config import get_config
from src.controller.api.api import app as api_app
from src.controller.web.web import app as web_app

load_dotenv()


def create_app():
    main_app = FastAPI()

    main_app.mount("/api", api_app)

    main_app.mount("/", web_app)

    return main_app


if __name__ == "__main__":
    config = get_config()

    host = os.getenv("UVICORN_HOST", str(config.server.host))
    port = int(os.getenv("UVICORN_PORT", str(config.server.port)))

    app = create_app()

    uvicorn.run(app, host=host, port=port, reload=False)
