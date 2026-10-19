from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_redirects_to_app():
    """Kiểm tra route gốc / tự động redirect (302) sang /app/."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/app/"


def test_home_with_json_format_returns_200():
    """Kiểm tra route gốc / hỗ trợ trả về JSON định danh khi có ?format=json."""
    response = client.get("/?format=json")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home_follow_redirects_returns_200():
    """Kiểm tra khi client tự động theo dõi chuyển hướng thì đến /app/ thành công."""
    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200


def test_health_returns_200():
    """Kiểm tra endpoint /health giữ nguyên HTTP 200 cho Docker & CI/CD."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_app_interface_returns_200():
    """Kiểm tra giao diện web /app/ trả về HTTP 200."""
    response = client.get("/app/")

    assert response.status_code == 200
