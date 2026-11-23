"""The README documents every hubs_sync flag and the new installer components."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HubsDocsTest(unittest.TestCase):
    def test_hubs_doc_names_every_flag(self):
        usage = re.search(r'usage: hubs_sync ([^"]+)"', (ROOT / "zsh/hubs.zsh").read_text()).group(1)
        flags = set(re.findall(r"--[a-z-]+", usage))
        self.assertEqual(flags, {"--dry-run", "--hubs", "--codex-home", "--tool"})
        readme = (ROOT / "README.md").read_text()
        for flag in flags:
            self.assertIn(flag, readme, flag)

    def test_readme_names_hubs_and_opencode_components(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("| `hubs` |", readme)
        self.assertIn("| `opencode` |", readme)
        self.assertIn("dotfiles/hubs", readme)
        self.assertNotIn("~/dotfiles-private/zsh", readme)

    def test_agents_readme_describes_hub_render(self):
        text = (ROOT / "agents/README.md").read_text()
        self.assertIn("render.py --hub", text)
        self.assertIn(".opencode/agents", text)


if __name__ == "__main__":
    unittest.main()
