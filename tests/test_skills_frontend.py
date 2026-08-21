"""技能工作台前端回归测试。"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SKILLS_JS = ROOT / "static" / "js" / "skills.js"


def test_skills_renderer_defines_and_invokes_render_all():
    source = SKILLS_JS.read_text(encoding="utf-8")
    assert re.search(r"function\s+renderAll\s*\(\)\s*\{", source)
    assert "renderAll();" in source
    assert "renderStats();" in source
    assert "renderChips();" in source
    assert "renderGrid();" in source


def test_skills_workbench_has_direct_call_and_grouped_rendering():
    source = SKILLS_JS.read_text(encoding="utf-8")
    assert "const grouped = new Map();" in source
    assert "textContent = '调用技能';" in source
    assert "function openCallPanel" in source
    assert "AbortController" in source
