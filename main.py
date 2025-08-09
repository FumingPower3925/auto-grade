import os
import uvicorn
from dotenv import load_dotenv
from config.config import get_config

load_dotenv()

if __name__ == "__main__":
    config = get_config()
    
    host = os.getenv("UVICORN_HOST", str(config.server.host))
    port = int(os.getenv("UVICORN_PORT", str(config.server.port)))
    
    uvicorn.run(
        "src.controller.api.api:app", 
        host=host, 
        port=port, 
        reload=False
    )