"""
Buddha Bot Service - Main entry point

Run with: python -m buddha_bot_service
"""

import uvicorn
import os

from buddha_bot_service import app


def main():
    """Run the Buddha Bot service."""
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    
    print(f"Starting Little Bits of Buddha Bot Service...")
    print(f"Listening on http://{host}:{port}")
    print(f"Webhook endpoint: http://{host}:{port}/webhook")
    
    uvicorn.run(
        "buddha_bot_service:app",
        host=host,
        port=port,
        reload=False
    )


if __name__ == "__main__":
    main()
