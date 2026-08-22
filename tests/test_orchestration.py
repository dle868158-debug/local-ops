"""配置迁移、依赖编排、健康检查与便携备份测试。"""

import http.server
import socketserver
import threading
import time
import unittest
from unittest import mock

import server


def service(app_id, name, depends=None, **overrides):
    app = {
        "id": app_id,
        "name": name,
        "command": "python -m http.server",
        "cwd": None,
        "port": None,
        "emoji": None,
        "glyph": None,
        "kind": "service",
        "url": None,
        "group": None,
        "tags": [],
        "dependsOn": list(depends or []),
        "healthCheck": {
            "type": "none", "url": None, "port": None,
            "timeoutSec": 2, "intervalSec": 10, "failureThreshold": 3,
        },
        "restartPolicy": "never",
        "maxRestarts": 3,
        "restartDelaySec": 3,
        "restartSuspended": False,
        "autoStart": False,
        "keepAlive": False,
    }
    app.update(overrides)
    return app


class SchemaV2Tests(unittest.TestCase):
    def test_v1_migration_adds_orchestration_defaults(self):
        raw = {"schemaVersion": 1, "apps": [{"id": "aaaabbbb", "name": "A"}]}
        migrated = server.migrate_config_v1_to_v2(raw)
        self.assertEqual(migrated["schemaVersion"], 2)
        app = migrated["apps"][0]
        self.assertEqual(app["dependsOn"], [])
        self.assertEqual(app["healthCheck"]["type"], "none")
        self.assertEqual(app["restartPolicy"], "never")

    def test_full_validation_accepts_new_fields(self):
        payload = service(
            "aaaabbbb", "API", ["ccccdddd"], group="开发",
            tags=["Python", "API"],
            healthCheck={
                "type": "http", "url": "http://127.0.0.1:8000/health",
                "port": None, "timeoutSec": 3, "intervalSec": 15,
                "failureThreshold": 2,
            },
            restartPolicy="on-unhealthy", maxRestarts=5, restartDelaySec=4,
        )
        fields, error = server.validate_app_fields(payload, partial=False)
        self.assertIsNone(error)
        self.assertEqual(fields["group"], "开发")
        self.assertEqual(fields["dependsOn"], ["ccccdddd"])
        self.assertTrue(fields["keepAlive"])

    def test_remote_http_health_url_is_rejected(self):
        payload = service("aaaabbbb", "API")
        payload["healthCheck"] = {
            "type": "http", "url": "https://example.com/health", "port": None,
            "timeoutSec": 2, "intervalSec": 10, "failureThreshold": 3,
        }
        _, error = server.validate_app_fields(payload, partial=False)
        self.assertIn("仅允许本机", error)


class DependencyGraphTests(unittest.TestCase):
    def test_topological_order_contains_transitive_dependencies(self):
        apps = [
            service("aaaabbbb", "Web", ["ccccdddd"]),
            service("ccccdddd", "API", ["eeeeffff"]),
            service("eeeeffff", "DB"),
        ]
        order = server.dependency_start_order({"apps": apps}, "aaaabbbb")
        self.assertEqual([app["id"] for app in order], ["eeeeffff", "ccccdddd"])

    def test_missing_and_cycle_are_rejected(self):
        missing = server.validate_dependency_graph([
            service("aaaabbbb", "Web", ["ccccdddd"]),
        ])
        self.assertIn("不存在", missing)
        cycle = server.validate_dependency_graph([
            service("aaaabbbb", "Web", ["ccccdddd"]),
            service("ccccdddd", "API", ["aaaabbbb"]),
        ])
        self.assertIn("循环依赖", cycle)


class PortableConfigTests(unittest.TestCase):
    def test_export_strips_runtime_and_local_asset_fields(self):
        app = service("aaaabbbb", "API")
        app.update({
            "lastPid": 123, "lastPgid": 123, "runToken": "secret",
            "icon": "/icons/private.png", "favicon": "/icons/fav.png",
            "lastExit": {"code": 1}, "restartSuspended": True,
        })
        exported = server.export_portable_config({
            "apps": [app], "watchedKeywords": [], "uiTheme": "ops",
        })
        portable = exported["apps"][0]
        for field in ("lastPid", "lastPgid", "runToken", "icon", "favicon",
                      "lastExit", "restartSuspended"):
            self.assertNotIn(field, portable)

    def test_merge_preserves_existing_and_imports_new(self):
        current = {
            "apps": [service("aaaabbbb", "Old")],
            "watchedKeywords": ["python"], "uiTheme": "ops",
        }
        payload = server.export_portable_config({
            "apps": [service("ccccdddd", "New")],
            "watchedKeywords": ["node"], "uiTheme": "ops",
        })
        prepared, error = server.prepare_imported_config(payload, current, "merge")
        self.assertIsNone(error)
        self.assertEqual([app["name"] for app in prepared["apps"]], ["Old", "New"])
        self.assertEqual(prepared["watchedKeywords"], ["node"])


class RuntimeHealthTests(unittest.TestCase):
    def tearDown(self):
        with server._HEALTH_RUNTIME_LOCK:
            server._HEALTH_RUNTIME.clear()

    def test_tcp_probe_reports_healthy_local_listener(self):
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                return

        with socketserver.TCPServer(("127.0.0.1", 0), Handler) as listener:
            app = service("aaaabbbb", "TCP")
            app["healthCheck"] = {
                "type": "tcp", "url": None,
                "port": listener.server_address[1], "timeoutSec": 1,
                "intervalSec": 2, "failureThreshold": 1,
            }
            result = server.app_runtime_health(app, running=True, force=True)
        self.assertEqual(result["status"], "healthy")

    def test_http_probe_reports_healthy_loopback_endpoint(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(204)
                self.end_headers()

            def log_message(self, *_args):
                return

        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as listener:
            thread = threading.Thread(target=listener.serve_forever, daemon=True)
            thread.start()
            app = service("aaaabbbb", "HTTP")
            app["healthCheck"] = {
                "type": "http",
                "url": "http://127.0.0.1:%d/health" % listener.server_address[1],
                "port": None, "timeoutSec": 1, "intervalSec": 2,
                "failureThreshold": 1,
            }
            result = server.app_runtime_health(app, running=True, force=True)
            listener.shutdown()
            thread.join(2)
        self.assertEqual(result["status"], "healthy")

    def test_poll_path_does_not_wait_for_slow_network_probe(self):
        app = service("aaaabbbb", "Async")
        app["healthCheck"] = {
            "type": "tcp", "url": None, "port": 65534,
            "timeoutSec": 2, "intervalSec": 2, "failureThreshold": 1,
        }
        started = threading.Event()
        release = threading.Event()

        def slow_probe(_app):
            started.set()
            release.wait(2)
            return True, "完成"

        with mock.patch.object(server, "_probe_health_once", side_effect=slow_probe):
            before = time.monotonic()
            result = server.app_runtime_health(app, running=True)
            elapsed = time.monotonic() - before
            self.assertEqual(result["status"], "checking")
            self.assertLess(elapsed, 0.2)
            self.assertTrue(started.wait(1))
            release.set()
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                with server._HEALTH_RUNTIME_LOCK:
                    cached = server._HEALTH_RUNTIME.get(app["id"], {})
                    if cached.get("public", {}).get("status") == "healthy":
                        break
                time.sleep(0.01)
            self.assertEqual(cached["public"]["status"], "healthy")

    def test_restart_policy_requires_failure_for_on_failure(self):
        app = service("aaaabbbb", "Worker", restartPolicy="on-failure")
        with mock.patch.object(server, "app_alive_sign", return_value=False), \
                mock.patch.object(server, "inspect_app_health",
                                  return_value={"blocking": False}):
            self.assertFalse(server._keepalive_should_start(app))
            app["lastExit"] = {"code": 2}
            self.assertTrue(server._keepalive_should_start(app))


if __name__ == "__main__":
    unittest.main()
