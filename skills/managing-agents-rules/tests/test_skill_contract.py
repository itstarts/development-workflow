import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    path = ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def assert_terms(
    testcase: unittest.TestCase, text: str, terms: tuple[str, ...]
) -> None:
    folded = text.casefold()
    for term in terms:
        with testcase.subTest(term=term):
            testcase.assertIn(term, folded)


def has_non_trigger_contract(text: str, activity: str) -> bool:
    folded = text.casefold()
    governance = r"(this governance skill|\$?managing-agents-rules( governance)? skill)"
    for sentence in re.split(r"[.\n]", folded):
        if re.search(
            rf"{activity}[^,;]{{0,80}}(does not|must not|never)\s+trigger\s+{governance}",
            sentence,
        ) or re.search(
            rf"{governance}[^,;]{{0,80}}(is not|must not be|is never)\s+triggered\s+by\s+{activity}",
            sentence,
        ):
            return True
    return False


def has_review_revalidation_contract(text: str) -> bool:
    folded = text.casefold()
    invalidation = re.search(
        r"(after[^.\n]{0,100}review[^.\n]{0,100}project rule changes|project rule changes[^.\n]{0,100}after[^.\n]{0,100}review)[^.\n]{0,180}invalidat[^.\n]{0,100}(prior|original) review",
        folded,
    )
    affected_validation = re.search(
        r"(re-run|rerun|repeat)[^.\n]{0,100}affected validation", folded
    )
    rereview = any(
        "same review channel" in sentence
        and "latest complete diff" in sentence
        and re.search(r"(re-review|review again)", sentence)
        and not re.search(
            r"(do not|does not|must not|not|never|without( requesting)?)\s+(re-review|review again)",
            sentence,
        )
        for sentence in re.split(r"[.\n]", folded)
    )
    return bool(invalidation and affected_validation and rereview)


def has_outside_workspace_permission_contract(text: str) -> bool:
    folded = text.casefold()
    outside_permission = (
        r"(outside (the )?workspace[^.\n]{0,80}permission|"
        r"permission[^.\n]{0,80}outside (the )?workspace|workspace-external permission)"
    )
    approved_diff = (
        r"((the user|user)\s+approv(e|es|ed)[^.\n]{0,50}"
        r"(specific|displayed|concrete)[^.\n]{0,20}diff|"
        r"(specific|displayed|concrete)[^.\n]{0,20}diff[^.\n]{0,40}"
        r"(is|was|has been)\s+(explicitly\s+)?approved\s+by\s+(the user|user))"
    )
    return bool(
        re.search(
            rf"{outside_permission}[^.\n]{{0,140}}only after[^.\n]{{0,120}}{approved_diff}",
            folded,
        )
        or re.search(
            rf"{approved_diff}[^.\n]{{0,140}}before[^.\n]{{0,120}}{outside_permission}[^.\n]{{0,80}}(request|ask)",
            folded,
        )
    )


class ManagingAgentsRulesContractTests(unittest.TestCase):
    def test_required_publishable_files_exist(self):
        required = (
            "SKILL.md",
            "references/task-lifecycle-and-session-state.md",
            "references/rule-candidates-and-scope.md",
            "references/approval-and-write-safety.md",
            "agents/openai.yaml",
        )
        self.assertEqual(
            [],
            [relative for relative in required if not (ROOT / relative).is_file()],
        )

    def test_frontmatter_names_the_skill_and_both_trigger_phases(self):
        metadata = parse_frontmatter(read("SKILL.md"))
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertEqual("managing-agents-rules", metadata.get("name"))
        description = metadata.get("description", "")
        self.assertTrue(description.startswith("Use when"))
        assert_terms(
            self,
            description,
            ("substantive development", "first production write", "completion", "agents"),
        )

    def test_skill_links_exactly_the_three_approved_references(self):
        skill = read("SKILL.md")
        expected = {
            "references/task-lifecycle-and-session-state.md",
            "references/rule-candidates-and-scope.md",
            "references/approval-and-write-safety.md",
        }
        linked = set(re.findall(r"references/[a-z0-9-]+\.md", skill))
        self.assertEqual(expected, linked)

    def test_skill_keeps_governance_separate_from_implementation_and_siblings(self):
        skill = read("SKILL.md").casefold()
        assert_terms(
            self,
            skill,
            (
                "before the first production write",
                "completion scan",
                "do not call sibling skills",
                "do not implement the target feature",
                "do not persist session state",
                "do not treat one approval as standing authorization",
            ),
        )

    def test_publishable_skill_does_not_forbid_agent_rules_repository(self):
        publishable = "\n".join(
            (
                read("SKILL.md"),
                read("references/approval-and-write-safety.md"),
            )
        ).casefold()

        self.assertNotIn("do not inspect or operate agent-rules", publishable)
        self.assertNotIn(
            "do not make that repository a dependency or success condition",
            publishable,
        )

    def test_review_wait_uses_the_available_interface_and_observed_identity(self):
        skill = read("SKILL.md").casefold()
        assert_terms(
            self,
            skill,
            (
                "use the available collaboration wait interface exactly as exposed",
                "do not invent a receiver parameter",
                "subsequent observed reviewer message",
                "matches the identifier returned by the spawn",
                "explicit verdict",
            ),
        )
        self.assertNotIn("wait with that reviewer as a non-empty receiver", skill)
        self.assertNotIn("wait with no reviewer receiver", skill)

    def test_ui_metadata_is_specific_without_promising_automatic_writes(self):
        metadata = read("agents/openai.yaml").casefold()
        assert_terms(
            self,
            metadata,
            (
                "managing agents rules",
                "project and global agents rules",
                "$managing-agents-rules",
                "explicit approval",
            ),
        )
        self.assertNotIn("automatically update", metadata)

    def test_lifecycle_reference_owns_trigger_and_non_trigger_classification(self):
        lifecycle = read("references/task-lifecycle-and-session-state.md")
        assert_terms(
            self,
            lifecycle,
            (
                "feature implementation",
                "bug fix",
                "refactor",
                "test",
                "configuration",
                "engineering documentation",
                "read-only analysis",
                "explanation",
                "review",
                "status query",
                "log inspection",
                "branch creation",
                "git operation",
            ),
        )
        folded = lifecycle.casefold()
        for excluded in ("read-only analysis", "explanation", "review"):
            with self.subTest(excluded=excluded):
                self.assertTrue(has_non_trigger_contract(folded, excluded))

    def test_lifecycle_reference_owns_project_root_rule_states_and_write_gate(self):
        lifecycle = read("references/task-lifecycle-and-session-state.md")
        assert_terms(
            self,
            lifecycle,
            (
                "git rev-parse --show-toplevel",
                "workspace root",
                "project root",
                "agents.md",
                "subdirectory",
                "unreadable",
                "production write",
                "agents.override.md",
                "base agents.md",
            ),
        )
        self.assertRegex(lifecycle.casefold(), r"unreadable[\s\S]{0,240}(block|stop)")

    def test_lifecycle_reference_owns_in_memory_project_and_task_state(self):
        lifecycle = read("references/task-lifecycle-and-session-state.md")
        assert_terms(
            self,
            lifecycle,
            (
                "normalized project root",
                "project_rules_check",
                "git_init_prompt",
                "taskcompletionstate",
                "completion_scan",
                "logical development task",
                "new session",
                "disk",
                "task/thread identifiers",
            ),
        )
        self.assertRegex(lifecycle.casefold(), r"(do not|never)[^\n]{0,120}persist")

    def test_lifecycle_reference_separates_git_init_from_rule_creation(self):
        lifecycle = read("references/task-lifecycle-and-session-state.md")
        assert_terms(
            self,
            lifecycle,
            ("git init", "project rule", "separate", "explicit approval", "declined"),
        )
        self.assertRegex(lifecycle.casefold(), r"(do not|never)[^\n]{0,120}(retry|repeat)")

    def test_lifecycle_reference_recommends_git_init_once_for_non_git_projects(self):
        lifecycle = read("references/task-lifecycle-and-session-state.md").casefold()
        self.assertIn("recommend initializing git", lifecycle)
        self.assertIn("first check", lifecycle)
        self.assertIn("even when the requested change is small", lifecycle)
        self.assertIn("present both decisions in the same preflight response", lifecycle)

    def test_candidate_reference_owns_evidence_scope_and_zero_prompt(self):
        candidates = read("references/rule-candidates-and-scope.md")
        assert_terms(
            self,
            candidates,
            (
                "current task evidence",
                "reusable",
                "temporary",
                "reduce",
                "project",
                "global",
                "classification",
                "declined",
                "final review",
                "no candidate",
                "silent",
            ),
        )
        self.assertIn("do not explain the omission", candidates.casefold())

    def test_project_validation_mapping_candidate_stays_optional_and_evidence_backed(self):
        candidates = read("references/rule-candidates-and-scope.md")
        approval = read("references/approval-and-write-safety.md")

        assert_terms(
            self,
            candidates,
            (
                "current task evidence",
                "evidence-backed",
                "validation cost",
                "project-specific validation",
                "project candidate",
            ),
        )
        assert_terms(
            self,
            approval,
            (
                "target path",
                "candidate text",
                "evidence",
                "classification reason",
                "minimal unified diff",
                "approval is valid only when it explicitly follows",
            ),
        )

    def test_candidate_reference_invalidates_review_after_project_rule_change(self):
        candidates = read("references/rule-candidates-and-scope.md").casefold()
        assert_terms(
            self,
            candidates,
            ("project rule", "review", "invalid", "validation", "same review channel"),
        )
        self.assertRegex(candidates, r"project[^\n]{0,160}before[^\n]{0,80}final review")
        self.assertRegex(candidates, r"global[^\n]{0,160}after[^\n]{0,80}final review")
        self.assertTrue(has_review_revalidation_contract(candidates))

    def test_approval_reference_owns_global_base_and_override_selection(self):
        approval = read("references/approval-and-write-safety.md")
        assert_terms(
            self,
            approval,
            (
                "codex_home",
                "$home/.codex",
                "base agents.md",
                "agents.override.md",
                "shadow",
                "explicit",
                "exist",
                "readable",
                "do not create",
            ),
        )
        folded = approval.casefold()
        for phrase in (
            "default remains the existing readable base agents.md",
            "explicitly selects an existing readable agents.override.md",
            "base agents.md is missing or unreadable",
            "explicitly selected override is missing or unreadable",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, folded)

    def test_approval_reference_owns_per_diff_invalidation_and_verification(self):
        approval = read("references/approval-and-write-safety.md")
        assert_terms(
            self,
            approval,
            (
                "unified diff",
                "target path",
                "evidence",
                "classification",
                "baseline content",
                "byte-for-byte",
                "invalid",
                "minimal patch",
                "re-read",
                "extra modification",
                "fixed hash",
            ),
        )

    def test_approval_reference_requires_ui_safe_complete_diff_rendering(self):
        approval = read("references/approval-and-write-safety.md").casefold()
        assert_terms(
            self,
            approval,
            (
                "dynamic markdown fence",
                "longest consecutive backtick run",
                "complete unified diff",
                "exactly once",
                "approval request after the closing fence",
                "do not use html disclosure",
                "<details>",
                "<summary>",
            ),
        )

    def test_approval_reference_delays_permissions_and_stops_sensitive_candidates(self):
        approval = read("references/approval-and-write-safety.md").casefold()
        assert_terms(
            self,
            approval,
            (
                "workspace",
                "permission",
                "approved diff",
                "secret",
                "token",
                "credential",
                "privacy",
                "do not display",
                "do not write",
            ),
        )
        self.assertTrue(has_outside_workspace_permission_contract(approval))
        self.assertRegex(
            approval,
            r"(sensitive|secret|token|credential|privacy)[^.\n]{0,220}(stop|discard|reject)[^.\n]{0,180}(do not|never)[^.\n]{0,100}(display|show)[^.\n]{0,180}(do not|never)[^.\n]{0,100}writ",
        )

    def test_relationship_matchers_accept_reordering_and_reject_counterexamples(self):
        self.assertTrue(
            has_non_trigger_contract(
                "Read-only analysis does not trigger this governance skill.",
                "read-only analysis",
            )
        )
        self.assertTrue(
            has_non_trigger_contract(
                "This governance skill is not triggered by explanation.",
                "explanation",
            )
        )
        self.assertFalse(
            has_non_trigger_contract(
                "Review triggers governance. Other work does not trigger the skill.",
                "review",
            )
        )
        self.assertFalse(
            has_non_trigger_contract(
                "Review triggers this governance skill. Review does not trigger a sibling skill.",
                "review",
            )
        )
        self.assertFalse(
            has_non_trigger_contract(
                "Review does not trigger a sibling skill but does trigger this governance skill.",
                "review",
            )
        )

        self.assertTrue(
            has_review_revalidation_contract(
                "Project rule changes after final review invalidate the prior review. "
                "Re-run the affected validation. The same review channel must re-review "
                "the latest complete diff."
            )
        )
        self.assertTrue(
            has_review_revalidation_contract(
                "After review, project rule changes invalidate the original review. "
                "Repeat the affected validation. Re-review the latest complete diff through "
                "the same review channel."
            )
        )
        self.assertFalse(
            has_review_revalidation_contract(
                "Project rule changes after review invalidate the prior review. "
                "Re-run unrelated validation. The same review channel must re-review "
                "the latest complete diff."
            )
        )
        self.assertFalse(
            has_review_revalidation_contract(
                "Project rule changes after review invalidate the prior review. "
                "Re-run the affected validation. Notify the same review channel to not "
                "re-review the latest complete diff."
            )
        )
        self.assertFalse(
            has_review_revalidation_contract(
                "Project rule changes after review invalidate the prior review. "
                "Re-run the affected validation and notify the same review channel about "
                "the latest complete diff without requesting re-review."
            )
        )

        self.assertTrue(
            has_outside_workspace_permission_contract(
                "Request outside the workspace permission only after the user approves "
                "the specific diff."
            )
        )
        self.assertTrue(
            has_outside_workspace_permission_contract(
                "The user approves the displayed diff before outside workspace permission "
                "is requested."
            )
        )
        self.assertFalse(
            has_outside_workspace_permission_contract(
                "An approved diff exists. Request outside workspace permission after task approval."
            )
        )
        self.assertFalse(
            has_outside_workspace_permission_contract(
                "Obtain task approval for the specific diff before outside workspace "
                "permission is requested."
            )
        )
        self.assertFalse(
            has_outside_workspace_permission_contract(
                "Do not approve the specific diff before outside workspace permission "
                "is requested."
            )
        )
        self.assertFalse(
            has_outside_workspace_permission_contract(
                "Task approval approves the specific diff before outside workspace "
                "permission is requested."
            )
        )

    def test_approval_reference_forbids_implicit_actions(self):
        approval = read("references/approval-and-write-safety.md")
        assert_terms(
            self,
            approval,
            (
                "do not install",
                "do not commit",
                "do not call sibling skills",
            ),
        )


if __name__ == "__main__":
    unittest.main()
