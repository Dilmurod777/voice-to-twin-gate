import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.llm import keyword_parse
from app.schema import Status

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No model in tests: the parse is deterministic, the arms are what is under test."""
    monkeypatch.setattr(
        main, "parse", lambda text, actions: (keyword_parse(text), "keyword")
    )
    main.session.reset()


def test_one_command_gets_three_answers_from_one_state():
    body = client.post("/api/command", json={"text": "open the fuel valve"}).json()

    assert [arm["name"] for arm in body["arms"]] == [
        "LLM only",
        "Manual check · 2023",
        "Context gate · 2026",
    ]
    assert body["arms"][0]["status"] == Status.ADMIT
    assert body["arms"][2]["status"] == Status.REFUSE


def test_the_twin_only_moves_when_the_gate_admits():
    client.post("/api/command", json={"text": "open the fuel valve"})
    state = client.get("/api/state").json()

    assert state["step"] == 1
    assert state["state"] == []


def test_an_admitted_step_advances_the_procedure():
    body = client.post("/api/command", json={"text": "remove the access panel"}).json()

    assert body["twin"]["step"] == 2
    assert "access_panel_open" in body["twin"]["state"]
    assert body["twin"]["steps"][0]["done"] is True


def test_a_read_only_view_leaves_state_alone():
    body = client.post("/api/command", json={"text": "show me the landing gear"}).json()

    assert body["arms"][2]["status"] == Status.ADMIT
    assert body["twin"]["state"] == []
    assert body["twin"]["step"] == 1


def test_reset_puts_the_aircraft_back():
    client.post("/api/command", json={"text": "remove the access panel"})
    state = client.post("/api/reset").json()

    assert state["step"] == 1
    assert state["state"] == []
