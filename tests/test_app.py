from fastapi.testclient import TestClient

from app.main import app


def test_home_page_renders_the_app_shell() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert f"<h1>{app.title}</h1>" in response.text
