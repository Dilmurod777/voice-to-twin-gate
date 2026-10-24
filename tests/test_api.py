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
    client.cookies.clear()


def head(text):
    return client.post("/api/command", json={"text": text}).json()


def arms():
    return [client.post(f"/api/arm/{index}").json() for index in range(3)]


def test_a_command_returns_the_parse_and_not_the_verdicts():
    body = head("open the fuel valve")

    assert body["parse"]["verb"] == "open_valve"
    assert body["parse"]["part"] == "fuel_valve"
    assert "arms" not in body
    assert body["timings"]["parse_ms"] >= 0


def test_each_arm_answers_on_its_own():
    head("open the fuel valve")

    answers = arms()

    assert [answer["arm"]["name"] for answer in answers] == [
        "LLM only",
        "Manual check · 2023",
        "Context gate · 2026",
    ]
    assert answers[0]["arm"]["status"] == Status.ADMIT
    assert answers[2]["arm"]["status"] == Status.REFUSE


def test_an_arm_without_a_command_is_refused():
    assert client.post("/api/arm/0").status_code == 409


def test_the_twin_only_moves_when_the_gate_admits():
    head("open the fuel valve")
    arms()

    state = client.get("/api/state").json()

    assert state["step"] == 1
    assert state["state"] == []


def test_an_admitted_step_advances_the_procedure():
    head("remove the access panel")
    answers = arms()

    assert answers[2]["arm"]["status"] == Status.ADMIT
    assert answers[2]["twin"]["step"] == 2
    assert "access_panel_open" in answers[2]["twin"]["state"]
    assert answers[2]["twin"]["steps"][0]["done"] is True


def test_a_read_only_view_leaves_state_alone():
    head("show me the landing gear")
    answers = arms()

    assert answers[2]["arm"]["status"] == Status.ADMIT
    assert answers[2]["arm"]["code"] == "READ_ONLY_OK"
    assert answers[2]["twin"]["state"] == []
    assert answers[2]["twin"]["step"] == 1


def test_every_arm_reads_the_state_the_command_arrived_in():
    head("remove the access panel")
    last = client.post("/api/arm/2").json()
    first = client.post("/api/arm/0").json()

    assert last["twin"]["step"] == 2
    assert first["arm"]["trace"][0]["value"] == "open_panel · access_panel"
    assert first["twin"]["step"] == 2


def test_reset_puts_the_aircraft_back():
    head("remove the access panel")
    arms()

    state = client.post("/api/reset").json()

    assert state["step"] == 1
    assert state["state"] == []
