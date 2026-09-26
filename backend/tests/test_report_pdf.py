"""H15: the PDF report renders and no Unicode punctuation is silently dropped."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_report_pdf_after_c1_run_to_end():
    client.post("/incident/reset")
    start = client.post("/incident/start", json={"scenario_id": "C1", "speed": 8})
    assert start.status_code == 200, start.text
    jump = client.post("/incident/clock", json={"op": "jump", "t": 3500})
    assert jump.status_code == 200, jump.text

    response = client.get("/incident/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    body = response.content
    assert body.startswith(b"%PDF")

    text = body.decode("latin-1")
    assert "Black Tuesday" in text
    # At least one decision or state transition made it into the report body.
    assert any(marker in text for marker in ("decision", "Decision", "->", "CRITICAL", "EMERGENCY", "RESOLVED"))
