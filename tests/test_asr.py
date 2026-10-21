from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_a_clip_too_short_to_be_speech_is_rejected():
    # 422 without touching whisper: the length check runs before the model is loaded.
    response = client.post("/api/transcribe", content=b"x")

    assert response.status_code == 422
