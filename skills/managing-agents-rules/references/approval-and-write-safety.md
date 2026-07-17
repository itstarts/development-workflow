# Approval and Write Safety

## Resolve the Selected Target

For a project candidate, use the normalized project root base `AGENTS.md`. For a global candidate, resolve the current Codex home from an explicit `CODEX_HOME`, otherwise from `$HOME/.codex`, and default to its base `AGENTS.md`. Never embed a machine-specific home path.

Check `AGENTS.override.md` in the same Codex home. If it is non-empty, explain that it temporarily shadows the base AGENTS.md and that a base-file update will not immediately control default discovery. Do not update the override unless the user explicitly selects it for this batch; that choice does not change the future default target.

Without an explicit target choice, the default remains the existing readable base AGENTS.md even when a non-empty override shadows it. If the user explicitly selects an existing readable AGENTS.override.md, validate only that selected override; the base file need not also exist or be readable.

If the default base AGENTS.md is missing or unreadable, do not create it or silently switch to the override; report the unknown target and ask for an explicit existing readable target. If the explicitly selected override is missing or unreadable, do not create or guess it. The selected global target must always already exist and be readable, and the Codex home must resolve uniquely.

## Build One Approval Snapshot

Read the current target, remove semantic duplicates, and show the target path, candidate text, evidence, classification reason, and minimal unified diff. Approval is valid only when it explicitly follows that displayed current diff. Blanket, standing, future, hypothetical, implementation, and pre-approval do not authorize a rule write. Approval covers only the displayed diff for that target and batch; project and global targets, later batches, later tasks, and later sessions require new approval.

Retain the full baseline content in the current execution context. After approval and immediately before writing, re-read the same target and compare it byte-for-byte with the baseline content. Do not use a fixed hash. A content change, read failure, path change, or target-identity change means the approval is invalid: rebuild the proposal from current state, show the new diff, and request approval again.

Request outside the workspace permission only after the user approves the specific diff. The approved diff is the only authorization for that permission request. If the permission is denied, report that the target was not updated; do not switch targets or weaken the gate.

## Apply and Verify

Apply only the approved minimal patch and preserve unrelated content and user changes. Re-read the target after writing and confirm the approved result. Inspect the actual diff where available and ensure there is no extra modification. Only then report the rule update as complete.

If sensitive content such as a secret, token, credential, or privacy data appears, stop that candidate: do not display the value and do not write it. Report only the category and the blocked action.

Do not inspect or operate agent-rules. Do not install anything, do not commit anything, and do not call sibling skills. Global writes remain subject to platform permission controls even after the user approves the concrete diff.
