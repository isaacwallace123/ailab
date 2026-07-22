from lab_status_assistant.secrets import detect_secret


def test_detects_known_token_shapes_without_returning_secret() -> None:
    detector = detect_secret("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456")
    assert detector == "openai-key"


def test_detects_high_entropy_assignments() -> None:
    detector = detect_secret("password: 0NFyN7hZpQ2K4xJ8mT6vB3cL9sR5wA1d")
    assert detector == "high-entropy-assignment"


def test_allows_documented_placeholders_and_environment_references() -> None:
    assert detect_secret("api_key = replace-with-a-real-secret") is None
    assert detect_secret("api_key = ${OPENAI_API_KEY}") is None
