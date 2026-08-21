"""网址卡片（kind=link）相关单元测试。"""

import http.server
import threading
import unittest

import server


class LinkFieldValidationTests(unittest.TestCase):
    def test_link_create_fields_normalized(self):
        fields, err = server.validate_app_fields(
            {"name": "Harness", "url": "http://127.0.0.1:3080/",
             "kind": "link"},
            partial=False)
        self.assertIsNone(err)
        self.assertEqual(fields["kind"], "link")
        self.assertEqual(fields["url"], "http://127.0.0.1:3080/")
        self.assertIsNone(fields["port"])
        self.assertIsNone(fields["cwd"])
        self.assertEqual(fields["command"], "")

    def test_link_url_required_enforced_by_handlers(self):
        # 校验器不强制 url（部分更新需要合并现有值），由创建/更新处理层强制。
        fields, err = server.validate_app_fields(
            {"name": "X", "kind": "link"}, partial=False)
        self.assertIsNone(err)
        self.assertIsNone(fields["url"])

    def test_link_rejects_invalid_url(self):
        _, err = server.validate_app_fields(
            {"name": "X", "url": "ftp://host", "kind": "link"},
            partial=False)
        self.assertIsNotNone(err)

    def test_non_link_rejects_url(self):
        _, err = server.validate_app_fields(
            {"name": "X", "command": "echo hi", "url": "http://a/"},
            partial=False)
        self.assertIsNotNone(err)

    def test_partial_kind_switch_to_link(self):
        fields, err = server.validate_app_fields(
            {"kind": "link"}, partial=True)
        self.assertIsNone(err)
        self.assertEqual(fields["kind"], "link")
        self.assertIsNone(fields["port"])
        self.assertEqual(fields["command"], "")

    def test_task_still_forces_port_none(self):
        fields, err = server.validate_app_fields(
            {"name": "T", "command": "echo hi", "kind": "task",
             "port": 8080},
            partial=False)
        self.assertIsNone(err)
        self.assertIsNone(fields["port"])

    def test_link_ignores_port(self):
        fields, err = server.validate_app_fields(
            {"name": "L", "url": "http://127.0.0.1:1/", "kind": "link",
             "port": 8080},
            partial=False)
        self.assertIsNone(err)
        self.assertIsNone(fields["port"])


class LinkHealthTests(unittest.TestCase):
    def test_link_health_always_ok(self):
        health = server.inspect_app_health(
            {"kind": "link", "command": "", "cwd": None})
        self.assertEqual(health["status"], "ok")
        self.assertFalse(health["blocking"])
        self.assertEqual(health["issues"], [])

    def test_public_last_exit_untouched_for_link(self):
        value = {"status": "failed", "code": 1, "at": 123}
        self.assertEqual(
            server.public_last_exit({"kind": "link", "lastExit": value}),
            value)


class RemoteFaviconTests(unittest.TestCase):
    def test_fetch_remote_favicon_from_link_tag(self):
        page = (b"<html><head><link rel=\"icon\" "
                b"href=\"/static/logo.png\"></head><body></body></html>")
        icon_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 32

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/static/logo.png":
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.end_headers()
                    self.wfile.write(icon_bytes)
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(page)

            def log_message(self, *args):
                pass

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            data, ext = server.fetch_remote_favicon(
                "http://127.0.0.1:%d/" % httpd.server_address[1])
        finally:
            httpd.shutdown()
            thread.join(timeout=3)
        self.assertEqual(data, icon_bytes)
        self.assertEqual(ext, "png")

    def test_fetch_remote_favicon_rejects_non_http(self):
        self.assertEqual(
            server.fetch_remote_favicon("file:///x"), (None, None))

    def test_fetch_remote_favicon_handles_dead_host(self):
        self.assertEqual(
            server.fetch_remote_favicon("http://127.0.0.1:1/"),
            (None, None))


if __name__ == "__main__":
    unittest.main()
