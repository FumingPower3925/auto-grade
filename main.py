import uvicorn
from dotenv import load_dotenv
from config.config import get_config

load_dotenv()

if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "src.controller.api.api:app", 
        host=config.server.host, 
        port=config.server.port, 
        reload=True
    )
