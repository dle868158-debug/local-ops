"""技能工作台后端单元测试：frontmatter 解析、库扫描、去重合并、中文索引合并。"""
import json
import os
import tempfile
import unittest
from unittest import mock

import server


class FrontmatterParsingTests(unittest.TestCase):
    def test_plain_quoted_and_nested(self):
        text = (
            "---\n"
            'name: academic-paper\n'
            'description: "12-agent pipeline. Triggers: write paper."\n'
            'metadata:\n'
            '  version: "3.0.2"\n'
            '  last_updated: "2026-04-15"\n'
            "  related_skills:\n"
            "    - deep-research\n"
            "    - academic-pipeline\n"
            "---\n"
        )
        fm = server.parse_skill_frontmatter(text)
        self.assertEqual(fm["name"], "academic-paper")
        self.assertEqual(fm["description"], "12-agent pipeline. Triggers: write paper.")
        self.assertEqual(fm["metadata"]["version"], "3.0.2")
        self.assertEqual(fm["metadata"]["last_updated"], "2026-04-15")
        self.assertEqual(fm["metadata"]["related_skills"],
                         ["deep-research", "academic-pipeline"])

    def test_block_scalar_and_lists(self):
        text = (
            "---\n"
            "name: gstack\n"
            "version: 1.1.0\n"
            "description: |\n"
            "  Fast headless browser.\n"
            "  Second line.\n"
            "triggers:\n"
            "  - browse this page\n"
            "  - take a screenshot\n"
            "allowed-tools:\n"
            "  - Bash\n"
            "  - Read\n"
            "---\n"
        )
        fm = server.parse_skill_frontmatter(text)
        self.assertEqual(fm["description"], "Fast headless browser.\nSecond line.")
        self.assertEqual(fm["triggers"], ["browse this page", "take a screenshot"])
        self.assertEqual(fm["allowed-tools"], ["Bash", "Read"])

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(server.parse_skill_frontmatter("just text\n"), {})
        self.assertEqual(server.parse_skill_frontmatter(""), {})

    def test_garbage_lines_are_skipped(self):
        text = "---\nname: x\n:broken : : :\n- orphan\nvalue: 1\n---\n"
        fm = server.parse_skill_frontmatter(text)
        self.assertEqual(fm["name"], "x")
        self.assertEqual(fm["value"], "1")

    def test_triggers_extracted_from_description_tail(self):
        fm = {"description": "Pipeline for papers. Triggers: write paper, guide paper"}
        self.assertEqual(server._skill_triggers(fm, fm["description"]),
                         ["write paper", "guide paper"])

    def test_related_from_metadata(self):
        fm = {"metadata": {"related_skills": ["a", "b"]}}
        self.assertEqual(server._skill_related(fm), ["a", "b"])


class SkillSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "skills")
        os.makedirs(self.root)
        self._write("alpha", (
            "---\n"
            "name: alpha\n"
            "description: English description A.\n"
            "metadata:\n"
            "  version: '1.0.0'\n"
            "  last_updated: '2026-01-01'\n"
            "---\n"
            "Body text.\n"
        ))
        self._write("beta", (
            "---\n"
            "name: beta\n"
            "description: English description B.\n"
            "triggers:\n"
            "  - do beta\n"
            "---\n"
        ))
        # 无 SKILL.md 的目录应被忽略
        os.makedirs(os.path.join(self.root, "no-skill"))
        # 点开头目录应被忽略
        self._write(".hidden", "---\nname: hidden\n---\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, content):
        d = os.path.join(self.root, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)

    def _write_in(self, parent, name, content):
        d = os.path.join(parent, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)

    def _snapshot(self, zh=None, lock=None, extra_roots=None):
        roots = [("agents", "AI 技能库", self.root)]
        if extra_roots:
            roots.extend(extra_roots)
        with mock.patch.object(server, "skill_roots", return_value=roots), \
                mock.patch.object(server, "read_skill_lock",
                                  return_value=lock or {}):
            if zh is None:
                with mock.patch.object(server, "load_skill_zh",
                                       return_value={}):
                    return server.build_skills_snapshot()
            with mock.patch.object(server, "load_skill_zh",
                                   return_value=zh):
                return server.build_skills_snapshot()

    def test_scans_only_valid_skill_dirs(self):
        snap = self._snapshot()
        self.assertEqual(snap["count"], 2)
        self.assertEqual([s["id"] for s in snap["skills"]], ["alpha", "beta"])
        self.assertEqual(snap["roots"][0]["count"], 2)

    def test_zh_index_merge_and_fallback(self):
        zh = {
            "alpha": {
                "category": "测试分类",
                "summary": "阿尔法中文简介",
                "detail": "阿尔法中文详解",
                "usage": "什么时候用阿尔法",
            },
        }
        snap = self._snapshot(zh=zh)
        by_id = {s["id"]: s for s in snap["skills"]}
        self.assertTrue(by_id["alpha"]["hasZh"])
        self.assertEqual(by_id["alpha"]["category"], "测试分类")
        self.assertEqual(by_id["alpha"]["summary"], "阿尔法中文简介")
        self.assertEqual(by_id["alpha"]["detail"], "阿尔法中文详解")
        self.assertEqual(by_id["alpha"]["usage"], "什么时候用阿尔法")
        # 未收录中文 → hasZh=False、分类兜底“其他”、保留英文描述
        self.assertFalse(by_id["beta"]["hasZh"])
        self.assertEqual(by_id["beta"]["category"], "其他")
        self.assertEqual(by_id["beta"]["description"], "English description B.")

    def test_dedup_across_roots_and_merge_fields(self):
        second = os.path.join(self.tmp.name, "skills2")
        os.makedirs(second)
        self._write_in(second, "beta", "---\nname: beta\ndescription: B new.\n"
                                      "metadata:\n  version: '2.0.0'\n---\n")
        snap = self._snapshot(extra_roots=[("claude", "Claude 技能库", second)])
        self.assertEqual(snap["count"], 2)
        beta = next(s for s in snap["skills"] if s["id"] == "beta")
        # 两个库都收录 → roots 合并；description 以第一个提供者为准
        self.assertEqual(sorted(beta["roots"]), ["agents", "claude"])
        self.assertEqual(beta["description"], "English description B.")

    def test_lock_info_merged(self):
        lock = {"beta": {"source": "user/repo", "installedAt": "2026-02-02"}}
        snap = self._snapshot(lock=lock)
        beta = next(s for s in snap["skills"] if s["id"] == "beta")
        self.assertEqual(beta["source"], "user/repo")
        self.assertEqual(beta["installedAt"], "2026-02-02")

    def test_get_skills_snapshot_caches_by_fingerprint(self):
        with mock.patch.object(server, "skill_roots",
                               return_value=[("agents", "AI 技能库", self.root)]), \
                mock.patch.object(server, "read_skill_lock", return_value={}), \
                mock.patch.object(server, "load_skill_zh", return_value={}):
            first = server.get_skills_snapshot()
            second = server.get_skills_snapshot()
            self.assertIs(first, second)
            # 目录内容变化后指纹失效并重建
            self._write("gamma", "---\nname: gamma\ndescription: G.\n---\n")
            os.utime(self.root)
            third = server.get_skills_snapshot()
            self.assertIsNot(first, third)
            self.assertEqual(third["count"], 3)
