"""Integration tests for the web dashboard and admin area (tasks 4.1-4.6, 5.2)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from grocery_agent.store import normalize
from grocery_agent.store.schema import connect
from grocery_agent.webapp.app import create_app
from grocery_agent.webapp.bot_config import BotConfigProvider
from tests.fixtures import RAW_TXN_OTHER_ACCOUNT, RAW_TXN_PLAIN


def build_store(path):
    conn = connect(str(path))
    normalize.ingest_raw(conn, "member-a", dict(RAW_TXN_PLAIN))
    normalize.ingest_raw(conn, "member-b", dict(RAW_TXN_OTHER_ACCOUNT))
    conn.close()
    return path


@pytest.fixture
def client(tmp_path, monkeypatch):
    grocery = build_store(tmp_path / "grocery.db")
    admin = str(tmp_path / "admin.db")
    monkeypatch.setenv("GROCERY_DB", str(grocery))
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
    provider = BotConfigProvider(admin, ttl_seconds=0)
    app = create_app(admin_db_path=admin, config_provider=provider)
    return TestClient(app)


@pytest.fixture
def no_password(tmp_path, monkeypatch):
    monkeypatch.setenv("GROCERY_DB", str(tmp_path / "grocery.db"))
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    return TestClient(
        create_app(admin_db_path=str(tmp_path / "admin.db"))
    )


def login(client, password="test-password"):
    return client.post("/login", data={"password": password}, follow_redirects=False)


class TestAuth:
    def test_unauthenticated_redirects_and_serves_no_data(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        # The login page itself carries no dashboard data.
        assert "Total spend" not in client.get("/login").text

    def test_wrong_password_refused(self, client):
        response = login(client, password="wrong")
        assert response.status_code == 200  # re-rendered login page
        assert "Incorrect password" in response.text

    def test_correct_password_grants_access(self, client):
        response = login(client)
        assert response.status_code == 303
        assert "Total spend" in client.get("/").text

    def test_unset_password_fails_closed(self, no_password):
        response = no_password.post(
            "/login", data={"password": "anything"}, follow_redirects=False
        )
        assert "Incorrect password" in response.text
        follow = no_password.get("/", follow_redirects=False)
        assert follow.headers["location"] == "/login"


class TestDashboard:
    def test_renders_aggregates_from_query_layer(self, client):
        login(client)
        page = client.get("/").text
        assert "Spend by month" in page
        assert "Spend by account" in page
        assert "Top products" in page
        assert "chart.umd.js" in page

    def test_empty_store_renders_empty_state(self, tmp_path, monkeypatch):
        from grocery_agent.store.schema import connect

        empty = connect(str(tmp_path / "empty.db"))  # schema, no rows
        empty.close()
        monkeypatch.setenv("GROCERY_DB", str(tmp_path / "empty.db"))
        monkeypatch.setenv("ADMIN_PASSWORD", "pw")
        c = TestClient(
            create_app(admin_db_path=str(tmp_path / "admin.db"))
        )
        c.post("/login", data={"password": "pw"})
        page = c.get("/").text
        assert "Total spend" in page
        assert '"by_month": []' in page

    def test_missing_store_shows_message_without_creating_it(self, tmp_path, monkeypatch):
        missing = tmp_path / "subdir" / "grocery.db"
        monkeypatch.setenv("GROCERY_DB", str(missing))
        monkeypatch.setenv("ADMIN_PASSWORD", "pw")
        c = TestClient(create_app(admin_db_path=str(tmp_path / "admin.db")))
        c.post("/login", data={"password": "pw"})
        page = c.get("/").text
        assert "Cannot read the grocery store" in page
        assert not missing.exists()

    def test_account_filter_narrows_views(self, client):
        login(client)
        unfiltered = client.get("/").text
        filtered = client.get("/", params={"account": "member-a"}).text
        assert '"by_account": [{' in unfiltered or "member-b" in unfiltered
        assert "member-b" not in filtered
        assert "member-a" in filtered

    def test_date_filter_matching_nothing_renders_empty(self, client):
        login(client)
        page = client.get(
            "/", params={"start": "2030-01-01", "end": "2030-12-31"}
        ).text
        assert '"by_month": []' in page


class TestCoverage:
    def test_coverage_rows_and_no_ingest_control(self, client):
        login(client)
        page = client.get("/coverage").text
        assert "member-a" in page
        assert "member-b" in page
        assert "/ingest" not in page


class TestAdmin:
    def test_edit_command_question_applies_to_provider(self, tmp_path, monkeypatch):
        admin = str(tmp_path / "admin.db")
        monkeypatch.setenv("GROCERY_DB", str(tmp_path / "grocery.db"))
        monkeypatch.setenv("ADMIN_PASSWORD", "pw")
        provider = BotConfigProvider(admin, ttl_seconds=0)
        c = TestClient(create_app(admin_db_path=admin, config_provider=provider))
        c.post("/login", data={"password": "pw"})

        response = c.post(
            "/admin/commands",
            data={"name": "spend", "question": "edited question"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert provider.questions()["spend"] == "edited question"

    def test_empty_question_rejected_with_previous_kept(self, client):
        login(client)
        response = client.post(
            "/admin/commands", data={"name": "spend", "question": "   "}
        )
        assert "must not be empty" in response.text

    def test_suggestions_saved(self, tmp_path, monkeypatch):
        admin = str(tmp_path / "admin.db")
        monkeypatch.setenv("GROCERY_DB", str(tmp_path / "grocery.db"))
        monkeypatch.setenv("ADMIN_PASSWORD", "pw")
        provider = BotConfigProvider(admin, ttl_seconds=0)
        c = TestClient(create_app(admin_db_path=admin, config_provider=provider))
        c.post("/login", data={"password": "pw"})
        c.post("/admin/suggestions", data={"suggestions": "one?\ntwo?\n"})
        assert provider.suggestions() == ["one?", "two?"]

    def test_settings_page_is_removed(self, client):
        # The settings view was removed: no credential or config exposure.
        assert client.get("/settings").status_code == 404


class TestHealthAndFavicon:
    def test_health_is_open_and_unauthenticated(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_favicon_is_served(self, client):
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert "svg" in response.headers["content-type"]


class TestSingleApp:
    def test_app_builds_without_bot(self, tmp_path):
        app = create_app(admin_db_path=str(tmp_path / "admin.db"))
        client = TestClient(app)
        assert client.get("/login").status_code == 200

    def test_webapp_serves_pages_and_provider_resolves(
        self, tmp_path, monkeypatch
    ):
        admin = str(tmp_path / "admin.db")
        monkeypatch.setenv("GROCERY_DB", str(tmp_path / "grocery.db"))
        monkeypatch.setenv("ADMIN_PASSWORD", "pw")
        provider = BotConfigProvider(admin, ttl_seconds=0)
        c = TestClient(create_app(admin_db_path=admin, config_provider=provider))

        assert c.get("/login").status_code == 200
        c.post("/login", data={"password": "pw"})
        assert c.get("/").status_code == 200
        c.post(
            "/admin/commands",
            data={"name": "top", "question": "runtime question"},
            follow_redirects=False,
        )
        assert provider.questions()["top"] == "runtime question"
