"""自启 / 守护 / 开机自启相关单元测试。"""

import unittest
from unittest import mock

import server


class LifecycleFieldValidationTests(unittest.TestCase):
    def test_autostart_keepalive_booleans_accepted(self):
        fields, err = server.validate_app_fields(
            {"name": "S", "command": "echo hi", "kind": "service",
             "autoStart": True, "keepAlive": True},
            partial=False)
        self.assertIsNone(err)
        self.assertTrue(fields["autoStart"])
        self.assertTrue(fields["keepAlive"])

    def test_autostart_rejects_non_bool(self):
        _, err = server.validate_app_fields(
            {"name": "S", "command": "echo hi", "autoStart": "yes"},
            partial=False)
        self.assertIsNotNone(err)

    def test_partial_update_only_toggles(self):
        fields, err = server.validate_app_fields(
            {"keepAlive": False}, partial=True)
        self.assertIsNone(err)
        self.assertFalse(fields["keepAlive"])
        self.assertNotIn("command", fields)


class KeepAliveDecisionTests(unittest.TestCase):
    def _app(self, **overrides):
        app = {"id": "a1b2c3d4", "kind": "service", "command": "",
               "cwd": None, "keepAlive": False, "keepAliveSuspended": False}
        app.update(overrides)
        return app

    def test_not_keepalive_skipped(self):
        self.assertFalse(server._keepalive_should_start(self._app()))

    def test_suspended_skipped(self):
        self.assertFalse(server._keepalive_should_start(
            self._app(keepAlive=True, keepAliveSuspended=True)))

    def test_task_skipped(self):
        self.assertFalse(server._keepalive_should_start(
            self._app(keepAlive=True, kind="task")))

    def test_alive_skipped(self):
        with mock.patch.object(server, "app_alive_sign", return_value=True):
            self.assertFalse(server._keepalive_should_start(
                self._app(keepAlive=True)))

    def test_healthy_service_wanted(self):
        self.assertTrue(server._keepalive_should_start(
            self._app(keepAlive=True)))

    def test_port_blocked_by_foreign_pid(self):
        app = self._app(keepAlive=True, port=8080)
        with mock.patch.object(
                server, "scan_listeners",
                return_value=[(123, 8080), (124, 9090)]):
            self.assertTrue(server._keepalive_port_blocked(app, set()))
            self.assertFalse(server._keepalive_port_blocked(app, {123}))

    def test_no_port_never_blocked(self):
        self.assertFalse(server._keepalive_port_blocked(
            self._app(keepAlive=True), set()))


class ConsoleAutostartTests(unittest.TestCase):
    @unittest.skipUnless(server.IS_WIN, "注册表逻辑仅 Windows")
    def test_autostart_command_dev_form(self):
        value = server._autostart_command()
        self.assertIn(sys_executable_quoted(), value)

    @unittest.skipUnless(server.IS_WIN, "注册表逻辑仅 Windows")
    def test_get_console_autostart_matches_exact_value(self):
        with mock.patch.object(server, "winreg") as fake:
            fake.HKEY_CURRENT_USER = "HKCU"
            fake.OpenKey.return_value.__enter__.return_value = "key"
            fake.QueryValueEx.return_value = (server._autostart_command(), 1)
            self.assertTrue(server.get_console_autostart())
            fake.QueryValueEx.return_value = ("别的路径", 1)
            self.assertFalse(server.get_console_autostart())

    @unittest.skipUnless(server.IS_WIN, "注册表逻辑仅 Windows")
    def test_set_console_autostart_disable_missing_value_ok(self):
        with mock.patch.object(server, "winreg") as fake:
            fake.HKEY_CURRENT_USER = "HKCU"
            fake.REG_SZ = 1
            fake.OpenKey.return_value.__enter__.return_value = "key"
            fake.DeleteValue.side_effect = FileNotFoundError()
            self.assertEqual(server.set_console_autostart(False), (True, None))


def sys_executable_quoted():
    import sys
    return '"%s"' % sys.executable


if __name__ == "__main__":
    unittest.main()
