import argparse
import os

import uvicorn


def run_app(reload: bool = False):
    port = int(os.environ.get("KAGIAPI_PORT", 8000))

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the KagiAPI app.")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    args = parser.parse_args()

    run_app(reload=args.reload)
