from __future__ import annotations

import json
import runpy
import tempfile
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "superworkflows",
    "init",
    "status",
    "run",
    "review",
    "release",
    "learn",
}


class PluginContractTests(unittest.TestCase):
    def test_manifest_and_explicit_skill_surface(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("0.2.0", manifest["version"].split("+", 1)[0])
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertLessEqual(len(prompts), 3)
        self.assertTrue(all(len(prompt) <= 128 for prompt in prompts))
        skill_dirs = {path.name for path in (PLUGIN / "skills").iterdir() if (path / "SKILL.md").is_file()}
        self.assertEqual(EXPECTED_SKILLS, skill_dirs)
        for name in EXPECTED_SKILLS:
            metadata = (PLUGIN / "skills" / name / "agents" / "openai.yaml").read_text(encoding="utf-8")
            self.assertIn("allow_implicit_invocation: false", metadata)
            self.assertIn(f"${name}", metadata)

    def test_router_has_no_recursive_or_external_authority(self) -> None:
        router = (PLUGIN / "skills" / "superworkflows" / "SKILL.md").read_text(encoding="utf-8")
        for name in EXPECTED_SKILLS - {"superworkflows"}:
            self.assertIn(f"../{name}/SKILL.md", router)
        self.assertIn("does not authorize external actions", router)
        self.assertFalse((PLUGIN / "skills" / "superworkflows" / "scripts").exists())
        self.assertFalse((PLUGIN / "skills" / "superworkflows" / "assets").exists())

    def test_plugin_workflow_is_sole_protocol_and_codegraph_is_required(self) -> None:
        skills = "\n".join(path.read_text(encoding="utf-8") for path in (PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertNotIn("read repository instructions, `.ai/workflow.md`", skills)
        self.assertIn("do not look for, generate, or require a project `.ai/workflow.md`", skills)
        self.assertIn("scripts/codegraphctl.py", skills)
        self.assertIn("codegraph impact", skills)
        self.assertIn("codegraph affected", skills)
        loopctl = (PLUGIN / "scripts" / "loopctl.py").read_text(encoding="utf-8")
        self.assertNotIn('".ai/workflow.md", ".ai/project-profile.json"', loopctl)
        self.assertIn('":(exclude).codegraph"', loopctl)
        self.assertIn('".codegraph" not in p.parts', loopctl)
        controller = (PLUGIN / "scripts" / "codegraphctl.py").read_text(encoding="utf-8")
        for command in ("status", "init", "sync", "index"):
            self.assertIn(f'"{command}"', controller)

    def test_plugin_runtime_hash_ignores_codegraph_index(self) -> None:
        hash_tree = runpy.run_path(str(PLUGIN / "scripts" / "loopctl.py"))["hash_tree"]
        with tempfile.TemporaryDirectory(prefix="superworkflows-plugin-hash-") as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_text("before\n", encoding="utf-8")
            before = hash_tree(root)
            index = root / ".codegraph"
            index.mkdir()
            (index / "index.db").write_text("first\n", encoding="utf-8")
            self.assertEqual(before, hash_tree(root))
            (index / "index.db").write_text("second\n", encoding="utf-8")
            self.assertEqual(before, hash_tree(root))
            source.write_text("after\n", encoding="utf-8")
            self.assertNotEqual(before, hash_tree(root))

    def test_workflow_spec_is_closed_and_namespaced_agents_are_valid(self) -> None:
        spec = json.loads(
            (PLUGIN / "assets" / "loop-engineering" / "workflow-spec.json").read_text(encoding="utf-8")
        )
        states = set(spec["states"])
        self.assertEqual(states, set(spec["transitions"]))
        for source, targets in spec["transitions"].items():
            self.assertIn(source, states)
            self.assertTrue(set(targets) <= states)
        agents = list((PLUGIN / "assets" / "agents").glob("*.toml"))
        self.assertEqual(10, len(agents))
        for path in agents:
            self.assertTrue(path.stem.startswith("sw-"))
            text = path.read_text(encoding="utf-8")
            self.assertIn(f'name = "{path.stem}"', text, msg=path.name)
            self.assertIn("do not spawn or delegate", text.lower())
        for read_only in (
            "sw-explorer",
            "sw-robot-system-architect",
            "sw-robot-safety-reviewer",
            "sw-robot-sim2real-validator",
            "sw-robot-release-engineer",
        ):
            text = (PLUGIN / "assets" / "agents" / f"{read_only}.toml").read_text(encoding="utf-8")
            self.assertIn('sandbox_mode = "read-only"', text)


if __name__ == "__main__":
    unittest.main()
