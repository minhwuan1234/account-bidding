"""HTTP presentation layer: serves frontend assets and maps requests to business functions."""

from __future__ import annotations

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from business.analysis_jobs import get as get_analysis_job, submit as submit_analysis_job
from business.bid_history import create_bid, delete_bid, get_bid, list_bids, update_bid
from business.bid_report import generate_report
from business.document_matching import compare_requirement
from business.checklist_jobs import get as get_checklist_job, submit as submit_checklist_job
from database.library_checklists import checklist_revision, get_checklist, save_checklist
from business.chunker import chunk_file
from business.library_service import add_document, delete_document, list_documents, update_document_description
from business.llm_tag_match import MODEL, has_api_key, match_one_tag
from business.report_jobs import get as get_report_job, submit as submit_report_job
from business.system_service import database_status
from business.upload_service import receive_rfp, summarize_rfp

MAX_UPLOAD = 30 * 1024 * 1024
ASSETS = Path(__file__).resolve().parent
STATIC_ASSETS = {"/app.js": "text/javascript; charset=utf-8", "/styles.css": "text/css; charset=utf-8"}


class Handler(BaseHTTPRequestHandler):
    def do_DELETE(self):
        url = urlparse(self.path)
        if url.path == "/api/bids":
            bid_id = parse_qs(url.query).get("id", [""])[0]
            if not bid_id:
                self.respond_json(400, {"error": "Thiếu ID bid"})
                return
            try:
                if delete_bid(bid_id):
                    self.respond_json(200, {"ok": True})
                else:
                    self.respond_json(404, {"error": "Không tìm thấy bid"})
            except Exception as exc:
                self.respond_json(503, {"error": str(exc)})
            return
        if url.path != "/api/library":
            self.send_error(404)
            return
        file_id = parse_qs(url.query).get("id", [""])[0]
        if not file_id:
            self.respond(400, json.dumps({"error": "Thiếu ID tài liệu"}).encode("utf-8"), "application/json; charset=utf-8")
        elif delete_document(file_id):
            self.respond(200, b'{"ok":true}', "application/json; charset=utf-8")
        else:
            self.respond(404, json.dumps({"error": "Không tìm thấy tài liệu"}).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/library-checklist-job":
            job = get_checklist_job(parse_qs(url.query).get("id", [""])[0])
            self.respond_json(200, job) if job else self.respond_json(404, {"error": "Phiên tạo checklist không còn; hãy thử lại"})
            return
        if url.path == "/api/library-checklist":
            file_id = parse_qs(url.query).get("id", [""])[0]
            if not file_id:
                self.respond_json(400, {"error": "Thiếu ID tài liệu"})
                return
            try:
                items = get_checklist(file_id)
                self.respond_json(200, {"items": items, "revision": checklist_revision(items)})
            except Exception as exc:
                self.respond_json(503, {"error": str(exc)})
            return
        if url.path == "/api/bids":
            try:
                bid_id = parse_qs(url.query).get("id", [""])[0]
                result = get_bid(bid_id) if bid_id else list_bids()
                if bid_id and result is None:
                    self.respond_json(404, {"error": "Không tìm thấy bid"})
                else:
                    self.respond_json(200, {"bid": result} if bid_id else {"bids": result})
            except Exception as exc:
                self.respond_json(503, {"error": str(exc)})
            return
        if url.path == "/favicon.svg":
            self.respond(200, (ASSETS / "favicon.svg").read_bytes(), "image/svg+xml")
            return
        if url.path == "/api/chunk-job":
            job_id = parse_qs(url.query).get("id", [""])[0]
            job = get_analysis_job(job_id)
            if job is None:
                self.respond(404, json.dumps({"error": "Phiên xử lý không còn. Hãy phân tích lại file."}, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            else:
                self.respond(200, json.dumps(job, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            return
        if url.path == "/api/bid-report-job":
            job_id = parse_qs(url.query).get("id", [""])[0]
            job = get_report_job(job_id)
            if job is None:
                self.respond_json(404, {"error": "Phiên tạo báo cáo không còn. Hãy chạy lại."})
            else:
                self.respond_json(200, job)
            return
        if url.path == "/api/database-status":
            self.respond(200, json.dumps(database_status()).encode(), "application/json; charset=utf-8")
            return
        if url.path in STATIC_ASSETS:
            self.respond(200, (ASSETS / url.path.lstrip("/")).read_bytes(), STATIC_ASSETS[url.path])
            return
        if self.path == "/api/llm-status":
            ready = has_api_key()
            self.respond(200, json.dumps({"ready": ready, "model": MODEL}).encode(), "application/json; charset=utf-8")
            return
        if self.path == "/api/library":
            try:
                self.respond_json(200, {"files": list_documents()})
            except Exception as exc:
                self.respond_json(503, {"error": str(exc)})
            return
        if self.path != "/":
            self.send_error(404)
            return
        self.respond(200, (ASSETS / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        url = urlparse(self.path)
        routes = {
            "/api/chunk-job": self.post_chunk_job,
            "/api/chunk": self.post_chunk,
            "/api/library": self.post_library,
            "/api/library-description": self.post_library_description,
            "/api/library-checklist": self.post_library_checklist,
            "/api/library-checklist-generate": self.post_library_checklist_generate,
            "/api/llm-match-tag": self.post_match_tag,
            "/api/document-match": self.post_document_match,
            "/api/bid-report": self.post_bid_report,
            "/api/bid-report-job": self.post_bid_report_job,
            "/api/bids": self.post_bid,
        }
        handler = routes.get(url.path)
        if handler is None:
            self.send_error(404)
            return
        try:
            handler(url)
        except RuntimeError as exc:
            code = 503 if url.path == "/api/chunk-job" else 400
            self.respond_json(code, {"error": str(exc)})
        except Exception as exc:
            self.respond_json(400, {"error": str(exc)})

    def read_body(self, limit: int = MAX_UPLOAD) -> bytes:
        size = int(self.headers.get("Content-Length", "0"))
        if size <= 0 or size > limit:
            raise ValueError("Dữ liệu rỗng hoặc vượt quá giới hạn")
        return self.rfile.read(size)

    def file_options(self, url):
        params = parse_qs(url.query)
        filename = Path(params.get("filename", [""])[0]).name
        if Path(filename).suffix.lower() not in (".pdf", ".docx"):
            raise ValueError("Chỉ hỗ trợ PDF và DOCX")
        semantic = params.get("semantic", ["false"])[0].lower() == "true"
        threshold = float(params.get("threshold", ["0.85"])[0])
        if not 0.5 <= threshold <= 0.95:
            raise ValueError("Ngưỡng ngữ nghĩa phải nằm trong khoảng 0.50–0.95")
        return filename, semantic, threshold

    def post_chunk_job(self, url):
        filename, semantic, threshold = self.file_options(url)
        job_id = submit_analysis_job(filename, self.read_body(), semantic, threshold)
        self.respond_json(202, {"id": job_id})

    def post_chunk(self, url):
        filename, semantic, threshold = self.file_options(url)
        body = self.read_body()
        stored = receive_rfp(filename, body)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / filename
            path.write_bytes(body)
            summarize_rfp(stored["id"], path)
            result = chunk_file(path, semantic=semantic, threshold=threshold)
        result["stored_document_id"] = stored["id"]
        self.respond_json(200, result)

    def post_library(self, url):
        filename = Path(parse_qs(url.query).get("filename", [""])[0]).name
        self.respond_json(200, {"file": add_document(filename, self.read_body())})

    def post_library_description(self, url):
        payload = json.loads(self.read_body(8192))
        if not update_document_description(payload["id"], payload["description_md"]):
            raise ValueError("Không tìm thấy file trong thư viện")
        self.respond_json(200, {"ok": True})

    def post_document_match(self, url):
        payload = json.loads(self.read_body(65536))
        self.respond_json(200, compare_requirement(payload.get("title"), payload.get("detail"), payload.get("file_ids")))

    def post_library_checklist(self, url):
        payload = json.loads(self.read_body(1024 * 1024))
        if not save_checklist(str(payload.get("id", "")), payload.get("items")):
            raise ValueError("Không tìm thấy file trong thư viện")
        self.respond_json(200, {"ok": True})

    def post_library_checklist_generate(self, url):
        payload = json.loads(self.read_body(8192))
        self.respond_json(202, {"id": submit_checklist_job(str(payload.get("id", "")))})

    def post_match_tag(self, url):
        payload = json.loads(self.read_body())
        self.respond_json(200, match_one_tag(payload["chunks"]))

    def post_bid_report(self, url):
        payload = json.loads(self.read_body())
        if not isinstance(payload.get("documents"), list) or not isinstance(payload.get("matches"), list):
            raise ValueError("Thiếu tài liệu hoặc dữ liệu báo cáo")
        self.respond_json(200, generate_report(payload["documents"], payload["matches"]))

    def post_bid_report_job(self, url):
        payload = json.loads(self.read_body())
        if not isinstance(payload.get("documents"), list) or not isinstance(payload.get("matches", []), list):
            raise ValueError("Thiếu tài liệu hoặc dữ liệu báo cáo")
        job_id = submit_report_job(payload["documents"], payload.get("matches", []))
        self.respond_json(202, {"id": job_id})

    def post_bid(self, url):
        payload = json.loads(self.read_body(4096))
        self.respond_json(201, {"bid": create_bid(str(payload.get("title", "")))})

    def do_PUT(self):
        url = urlparse(self.path)
        if url.path != "/api/bids":
            self.send_error(404)
            return
        try:
            bid_id = parse_qs(url.query).get("id", [""])[0]
            if not bid_id:
                raise ValueError("Thiếu ID bid")
            payload = json.loads(self.read_body(60 * 1024 * 1024))
            bid = update_bid(bid_id, payload)
            self.respond_json(200, {"bid": bid}) if bid else self.respond_json(404, {"error": "Không tìm thấy bid"})
        except Exception as exc:
            self.respond_json(400, {"error": str(exc)})

    def respond_json(self, code: int, data) -> None:
        self.respond(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def respond(self, code: int, data: bytes, mime: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        if mime.startswith(("text/html", "text/javascript", "text/css")):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    railway_port = os.environ.get("PORT")
    port = int(railway_port or os.environ.get("STRUCTURAL_CHUNKER_PORT", "8765"))
    host = "0.0.0.0" if railway_port else "127.0.0.1"
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Listening on {host}:{port} (Ctrl+C to stop)", flush=True)
    server.serve_forever()
