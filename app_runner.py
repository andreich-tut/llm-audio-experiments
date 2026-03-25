"""Run the Mini App FastAPI server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "interfaces.webapp.app:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )
