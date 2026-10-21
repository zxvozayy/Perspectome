"""The web site: accounts, sessions, routes and the rendered answers."""

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from src.ui import auth, render, server
from src.ui.data import load


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CACHE", tmp_path)
    monkeypatch.setattr(auth, "USERS", tmp_path / "users.json")
    monkeypatch.setattr(auth, "SECRET", tmp_path / "secret")
    monkeypatch.setattr(auth, "ITERATIONS", 1000)
    return tmp_path


@pytest.fixture
def site(cache):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


def call(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request(method, path, body, headers or {})
    res = conn.getresponse()
    return res.status, dict(res.getheaders()), res.read().decode()


def test_register_then_login(cache):
    assert auth.register("ezgi", "kisa") is not None
    assert auth.register("../x", "uzun-bir-sifre") is not None
    assert auth.register("ezgi", "uzun-bir-sifre") is None
    assert auth.register("EZGI", "uzun-bir-sifre") is not None  # names are unique regardless of case
    assert auth.check("ezgi", "uzun-bir-sifre")
    assert not auth.check("ezgi", "yanlis-sifre")
    assert "uzun-bir-sifre" not in (cache / "users.json").read_text()


def test_sessions_cannot_be_forged(cache):
    auth.register("ezgi", "uzun-bir-sifre")
    token = auth.issue("ezgi")
    assert auth.verify(token) == "ezgi"
    name, expires, sig = token.split("|")
    assert auth.verify(f"baska|{expires}|{sig}") is None
    assert auth.verify(f"ezgi|{int(expires) + 999}|{sig}") is None
    assert auth.verify("ezgi|1|" + sig) is None
    assert auth.verify("") is None


def test_pages_and_guards(site):
    assert call(site, "GET", "/")[0] == 200
    assert call(site, "GET", "/giris")[0] == 200
    status, headers, _ = call(site, "GET", "/panel")
    assert status == 303 and headers["Location"] == "/giris"
    assert call(site, "GET", "/api/state")[0] == 401
    assert call(site, "GET", "/static/../server.py")[0] == 404
    assert call(site, "GET", "/static/site.css")[0] == 200


def test_sign_up_and_ask(site):
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    status, headers, _ = call(site, "POST", "/kayit", "ad=ezgi&sifre=uzun-bir-sifre&sifre2=uzun-bir-sifre", form)
    assert status == 303
    cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
    assert "HttpOnly" in headers["Set-Cookie"]

    status, _, body = call(site, "POST", "/api/ask", json.dumps({"q": "İşsizlik artarsa?"}),
                           {**cookie, "Content-Type": "application/json"})
    assert status == 200
    answer = json.loads(body)
    assert set(answer) == {"html"} and "pt-user" in answer["html"] and "Etki" in answer["html"]

    state = json.loads(call(site, "GET", "/api/state", headers=cookie)[2])
    assert set(state) == {"counts"}
    assert call(site, "GET", "/api/chat?id=x", headers=cookie)[0] == 404
    assert call(site, "POST", "/giris", "ad=ezgi&sifre=yanlis", form)[0] == 401


def test_ask_is_stateless(site, cache):
    """Nothing about a question is written to disk: the panel keeps no history."""
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    _, headers, _ = call(site, "POST", "/kayit", "ad=ayse&sifre=uzun-bir-sifre&sifre2=uzun-bir-sifre", form)
    cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
    before = sorted(p.name for p in cache.rglob("*"))
    for q in ("İşsizlik artarsa?", "Doğrulama nasıl?"):
        status, _, _ = call(site, "POST", "/api/ask", json.dumps({"q": q}), {**cookie, "Content-Type": "application/json"})
        assert status == 200
    assert sorted(p.name for p in cache.rglob("*")) == before


def test_answer_text_is_escaped():
    out = render.prose("**<b>x</b>** ve *y*")
    assert "<b>&lt;b&gt;x&lt;/b&gt;</b>" in out and "<i>y</i>" in out


def test_chart_tabs_hold_all_four_views():
    bundle = load()
    run = bundle.runs("scenario")[0]
    html = render.chart_tabs("k", run, bundle.scored(run["scenario_id"]))
    assert html.count('class="tab-panel"') == 4 and html.count(" hidden") == 3
