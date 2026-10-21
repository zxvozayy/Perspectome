"""Perspectome web site (Track D): intro page, sign-in and the analysis panel.

Standard library only. Run from the repo root:

    python -m src.ui.server             # http://localhost:8501
"""

from __future__ import annotations

import html
import json
import mimetypes
import os
import uuid
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.ui import answers, auth, render
from src.ui.data import load

WEB = Path(__file__).parent / "web"
COOKIE = "pt_session"
STATIC_TYPES = {".css", ".js", ".svg", ".woff2", ".png", ".webp", ".ico", ".jpg", ".mp4", ".webm"}
VIDEO = WEB / "media" / "tanitim.mp4"  # the hero video (Mixkit, free licence); a still shows if it's missing


def video() -> str:
    if VIDEO.is_file():
        poster = f' poster="/static/media/{VIDEO.stem}.jpg"' if VIDEO.with_suffix(".jpg").is_file() else ""
        return f'<video src="/static/media/{VIDEO.name}"{poster} muted loop playsinline preload="auto"></video>'
    return '<div class="hero__still"></div>'


def counts(bundle) -> dict:
    """How much there is to look at — file counts for the welcome cards, not metrics."""
    probes = (bundle.comparison or {}).get("probes") or []
    models = {m for p in probes for m in (p.get("models") or {})}
    models = models or {r["model_snapshot"] for r in bundle.results.values() if r.get("model_snapshot")}
    return {"scenarios": len(bundle.runs("scenario")), "probes": len(probes), "models": len(models)}


def page(file: str, **values: str) -> bytes:
    text = (WEB / file).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text.encode()


class Handler(BaseHTTPRequestHandler):
    server_version = "Perspectome"

    # ------------------------------------------------------------ helpers

    def user(self) -> str | None:
        jar = SimpleCookie(self.headers.get("Cookie", ""))
        return auth.verify(jar[COOKIE].value) if COOKIE in jar else None

    def send(self, body: bytes, ctype: str = "text/html; charset=utf-8", status: int = 200, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        if ctype.startswith("text/html") or ctype.startswith("application/json"):
            self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def json(self, data, status: int = 200) -> None:
        self.send(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

    def redirect(self, to: str, cookie: str | None = None) -> None:
        headers = {"Location": to}
        if cookie is not None:
            age = auth.SESSION_SECONDS if cookie else 0
            headers["Set-Cookie"] = f"{COOKIE}={cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age={age}"
        self.send(b"", status=HTTPStatus.SEE_OTHER, headers=headers)

    def body(self) -> bytes:
        size = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(min(size, 64_000))

    def form(self) -> dict[str, str]:
        return {k: v[0] for k, v in parse_qs(self.body().decode(errors="replace")).items()}

    def login_page(self, mode: str = "giris", error: str = "", name: str = "", status: int = 200) -> None:
        msg = f'<p class="form-error" role="alert">{html.escape(error)}</p>' if error else ""
        current = 'aria-current="page"'
        tabs = {"tab_giris": current if mode == "giris" else "", "tab_kayit": current if mode == "kayit" else ""}
        self.send(page("giris.html", video=video(), mode=mode, error=msg, name=html.escape(name), **tabs), status=status)

    def log_message(self, fmt: str, *args) -> None:  # quiet console
        pass

    # ------------------------------------------------------------- routes

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        url = urlparse(self.path)
        path = url.path
        if path in ("/", "/index.html"):
            return self.send(page("index.html", video=video()))
        if path == "/giris":
            if self.user():
                return self.redirect("/panel")
            mode = "kayit" if parse_qs(url.query).get("mod") == ["kayit"] else "giris"
            return self.login_page(mode)
        if path == "/cikis":
            return self.redirect("/", cookie="")
        if path == "/panel":
            user = self.user()
            if not user:
                return self.redirect("/giris")
            badge = '<span class="badge">Fixture verisi</span>' if load().is_fixture else ""
            return self.send(page("panel.html", user=html.escape(user), initial=html.escape(user[:1].upper()), badge=badge))
        if path.startswith("/api/"):
            return self.api_get(path, parse_qs(url.query))
        if path.startswith("/static/"):
            return self.static(path[len("/static/"):])
        self.send(page("404.html"), status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/giris":
            f = self.form()
            name, password = f.get("ad", "").strip(), f.get("sifre", "")
            if auth.check(name, password):
                return self.redirect("/panel", cookie=auth.issue(name))
            return self.login_page("giris", "Kullanıcı adı ya da şifre hatalı.", name, status=401)
        if path == "/kayit":
            f = self.form()
            name, password = f.get("ad", "").strip(), f.get("sifre", "")
            if password != f.get("sifre2", ""):
                return self.login_page("kayit", "Şifreler aynı değil.", name, status=400)
            error = auth.register(name, password)
            if error:
                return self.login_page("kayit", error, name, status=400)
            return self.redirect("/panel", cookie=auth.issue(name))
        if path == "/api/ask":
            return self.api_ask()
        self.send(page("404.html"), status=404)

    def static(self, rel: str) -> None:
        target = (WEB / rel).resolve()
        if WEB.resolve() not in target.parents or target.suffix not in STATIC_TYPES or not target.is_file():
            return self.send(page("404.html"), status=404)
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".woff2":
            ctype = "font/woff2"
        headers = {"Cache-Control": "public, max-age=3600", "Accept-Ranges": "bytes"}
        data = target.read_bytes()
        # Safari only plays video that it can fetch in byte ranges.
        span = self.headers.get("Range", "")
        if span.startswith("bytes=") and "," not in span:
            first, _, end = span[6:].partition("-")
            try:
                a = int(first) if first else max(len(data) - int(end), 0)
                b = min(int(end), len(data) - 1) if first and end else len(data) - 1
            except ValueError:
                a, b = 0, -1
            if a > b or a >= len(data):
                return self.send(b"", ctype, HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, {"Content-Range": f"bytes */{len(data)}"})
            headers["Content-Range"] = f"bytes {a}-{b}/{len(data)}"
            return self.send(data[a:b + 1], ctype, HTTPStatus.PARTIAL_CONTENT, headers)
        self.send(data, ctype, headers=headers)

    # ---------------------------------------------------------------- api

    def api_get(self, path: str, query: dict) -> None:
        user = self.user()
        if not user:
            return self.json({"error": "Oturum kapalı."}, 401)
        bundle = load()
        if path == "/api/state":
            return self.json({"counts": counts(bundle)})
        self.json({"error": "Bilinmeyen adres."}, 404)

    def api_ask(self) -> None:
        user = self.user()
        if not user:
            return self.json({"error": "Oturum kapalı."}, 401)
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.json({"error": "JSON bekleniyor."}, 415)
        try:
            req = json.loads(self.body() or b"{}")
        except ValueError:
            return self.json({"error": "Geçersiz istek."}, 400)
        question = str(req.get("q") or "").strip()[:500]
        if not question:
            return self.json({"error": "Soru boş."}, 400)
        bundle = load()
        chat = {"id": uuid.uuid4().hex, "messages": [
            {"role": "user", "text": question},
            {"role": "assistant", **answers.route(question, bundle)},
        ]}
        self.json({"html": render.chat(chat, bundle)})


def main() -> None:
    port = int(os.environ.get("PORT", "8501"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Perspectome: http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
