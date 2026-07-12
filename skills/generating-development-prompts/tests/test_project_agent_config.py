import json
import re
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and earlier
    tomllib = None


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SKILL_ROOT.parents[1]
CONFIG_PATH = PROJECT_ROOT / ".codex" / "agents" / "final-reviewer.toml"
ASSET_PATH = SKILL_ROOT / "assets" / "final-reviewer.toml"


def parse_toml(text):
    if tomllib is not None:
        return tomllib.loads(text)
    return parse_controlled_agent_toml(text)


def parse_controlled_agent_toml(text):
    """Parse only the flat string syntax used by this controlled role fixture."""
    result = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip():
            continue

        if line == 'developer_instructions = """':
            if "developer_instructions" in result:
                raise ValueError("duplicate developer_instructions")
            body = []
            while index < len(lines) and lines[index] != '"""':
                body.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError("unclosed developer_instructions")
            index += 1
            result["developer_instructions"] = "\n".join(body) + ("\n" if body else "")
            continue

        assignment = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.+)", line)
        if assignment is None:
            raise ValueError(f"unsupported TOML line: {line!r}")
        key, raw_value = assignment.groups()
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError as error:
            raise ValueError(f"unsupported value for {key}") from error
        if not (
            isinstance(value, str)
            or (isinstance(value, list) and all(isinstance(item, str) for item in value))
        ):
            raise ValueError(f"unsupported value type for {key}")
        result[key] = value
    return result


def nested_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from nested_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_keys(child)


class ProjectFinalReviewerConfigTests(unittest.TestCase):
    def test_controlled_fallback_parser_consumes_supported_role_syntax(self):
        config = parse_controlled_agent_toml(
            'name = "final-reviewer"\n'
            'tools = ["read", "review"]\n'
            'developer_instructions = """\n'
            "line one\n"
            "line two\n"
            '"""\n'
        )

        self.assertEqual("final-reviewer", config["name"])
        self.assertEqual(["read", "review"], config["tools"])
        self.assertEqual("line one\nline two\n", config["developer_instructions"])

    def test_controlled_fallback_parser_rejects_unknown_or_unconsumed_syntax(self):
        invalid_documents = (
            'name = "final-reviewer"\nenabled = true\n',
            'name = "final-reviewer"\n[agent]\n',
            'developer_instructions = """\nunclosed\n',
        )
        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    parse_controlled_agent_toml(document)

    def test_bundled_final_reviewer_asset_is_parseable_read_only_and_generic(self):
        self.assertTrue(ASSET_PATH.is_file(), f"missing bundled agent asset: {ASSET_PATH}")
        text = ASSET_PATH.read_text(encoding="utf-8")
        config = parse_toml(text)

        self.assertEqual("final-reviewer", config["name"])
        self.assertIn("final full review", config["description"].lower())
        self.assertEqual("read-only", config["sandbox_mode"])

        instructions = config["developer_instructions"]
        for phrase in (
            "只读",
            "候选范围",
            "验证证据",
            "权限边界",
            "无 task/thread 副作用",
            "APPROVED",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, instructions)

        for project_specific in ("TASK6_APPROVED_HEAD", "case 7", "07-real-tools-trial.json"):
            with self.subTest(project_specific=project_specific):
                self.assertNotIn(project_specific, text)

    def test_bundled_final_reviewer_does_not_pin_model_or_effort(self):
        config = parse_toml(ASSET_PATH.read_text(encoding="utf-8"))
        keys = set(nested_keys(config))
        self.assertNotIn("model", keys)
        self.assertNotIn("model_reasoning_effort", keys)

    def test_project_config_is_byte_identical_to_bundled_asset(self):
        if not CONFIG_PATH.is_file():
            self.skipTest("installed or isolated skill copy has no enclosing project config")
        self.assertEqual(ASSET_PATH.read_bytes(), CONFIG_PATH.read_bytes())


if __name__ == "__main__":
    unittest.main()
