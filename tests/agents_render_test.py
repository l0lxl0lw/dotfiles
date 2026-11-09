"""Canonical workflow agents render identically for Claude and Codex."""
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ai/shared/agents"
spec = importlib.util.spec_from_file_location("render", SOURCE / "render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def frontmatter(text):
    return dict(line.split(": ", 1) for line in text.split("---")[1].strip().splitlines()
                if not line.startswith("#") and ": " in line)


class RenderTest(unittest.TestCase):
    def test_committed_outputs_match_sources(self):
        wanted, drift = render.stale()
        self.assertEqual(drift, [], "run python3 ai/shared/agents/render.py")
        self.assertEqual(len(wanted), 20)

    def test_every_host_gets_the_same_roles_and_bodies(self):
        tiers = json.loads((SOURCE / "tiers.json").read_text())
        for path in sorted(p for p in SOURCE.glob("*.md") if p.name != "README.md"):
            meta = render.parse(path)
            name = meta["name"]
            claude = (ROOT / "ai/claude/agents/workflow" / (name + ".md")).read_text()
            codex = tomllib.loads((ROOT / "ai/codex/agents" / (name + ".toml")).read_text())
            self.assertTrue(claude.endswith(meta["body"]), name)
            self.assertEqual(codex["developer_instructions"], meta["body"])
            self.assertEqual((codex["name"], frontmatter(claude)["name"]), (name, name))

            mapped = {} if meta["tier"] == "inherit" else tiers["claude"].get(meta["tier"], {})
            self.assertEqual(frontmatter(claude).get("model"), mapped.get("model"), name)
            mapped = {} if meta["tier"] == "inherit" else tiers["codex"].get(meta["tier"], {})
            self.assertEqual(codex.get("model"), mapped.get("model"), name)
            self.assertEqual(codex.get("sandbox_mode"),
                             "read-only" if meta["access"] in ("research", "draft") else None, name)
            writes = "Edit" not in frontmatter(claude).get("disallowedTools", "")
            self.assertEqual(writes, meta["access"] == "write", name)

    def test_workers_named_by_the_develop_skills_exist_everywhere(self):
        method = (ROOT / "ai/shared/skills/develop/_lib/prepare-workers.md").read_text()
        names = {"develop-plan", "develop-scope-review", "develop-execute", "develop-review"}
        names |= {line.split("|")[1].strip() for line in method.splitlines()
                  if line.startswith("| ") and line.split("|")[1].strip()[:1].islower()}
        self.assertGreaterEqual(len(names), 10)
        for name in names:
            self.assertTrue((ROOT / "ai/claude/agents/workflow" / (name + ".md")).is_file(), name)
            self.assertTrue((ROOT / "ai/codex/agents" / (name + ".toml")).is_file(), name)

    def test_inherit_tier_and_unknown_values(self):
        source = "---\nname: probe\ndescription: d\ntier: {}\naccess: {}\n---\n\nBody.\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.md"
            path.write_text(source.format("inherit", "draft"))
            meta = render.parse(path)
            tiers = {"claude": {"fast": {"model": "haiku"}}, "codex": {}}
            self.assertNotIn("model", render.claude(meta, tiers))
            self.assertNotIn("model", render.codex(meta, tiers))
            for tier, access in (("huge", "draft"), ("inherit", "root")):
                path.write_text(source.format(tier, access))
                with self.assertRaises(SystemExit):
                    render.parse(path)


if __name__ == "__main__":
    unittest.main()
