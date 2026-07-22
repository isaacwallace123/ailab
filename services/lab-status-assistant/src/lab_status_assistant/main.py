import uvicorn


def run() -> None:
    uvicorn.run(
        "lab_status_assistant.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8088,
    )
