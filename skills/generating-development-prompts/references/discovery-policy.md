# Discovery Policy

Apply these rules while resolving repository, rule, specification, plan, and review context. Return paths and structured facts; do not interpret the contents of rule files.

## Resolve Paths

1. Resolve explicit `workdir` against the directory in which the skill started; otherwise use the current working directory.
2. Resolve relative explicit `spec` and `plan` paths against the resolved absolute `workdir`, not against the repository root or skill directory.
3. Convert selected paths to absolute normalized paths. Do not resolve symlinks for nonexistent paths.
4. Accept an explicit path only when it exists, is a regular readable file, and remains the requested document. If it is invalid, return an error and stop; never fall back to automatic discovery.

## Discover Repository and Rules

- Run read-only Git commands to collect the repository root, branch or detached state, HEAD, `git status --short --branch`, Git directory, common Git directory, and main-versus-linked worktree kind.
- When the working directory is not in a Git repository, set `repository.status` to `not-a-repository` and leave unavailable branch, HEAD, and root values as JSON `null`.
- Include rule files already exposed by the session as session rules.
- Search for `AGENTS.md` only along the directory path from repository root through the working directory. Return applicable filesystem rules from outermost to innermost with increasing precedence; a deeper rule wins when scopes overlap.
- Reject automatically discovered symlinks or paths that escape the repository. An explicit readable file may be used as explicitly requested.

## Select Specification and Plan

Search these directories in order when a side is not explicit:

1. `<repo>/docs/specs/`
2. `<repo>/docs/plans/`

Pass the development request through the discovery CLI's `--request` argument. Derive safe topic tokens from explicit `--topic`, or from `--request` when no topic is explicit; explicit topic always wins. Treat both as single inert process arguments, never shell fragments. For every candidate compute independent `exact`, token `coverage`, filename ISO `date`, and `mtime_ns` values.

- When both paths are explicit, validate and keep them. Record warnings for internal references to different documents; never replace an explicit value.
- When one side is explicit, rank each candidate for the other side by `(exact, coverage, reference_strength, date, mtime_ns)` in descending order. Use `reference_strength = 2` for bidirectional references, `1` for either one-way reference, and `0` for no reference.
- When neither side is explicit, rank the Cartesian product of specification and plan candidates by `(min_exact, sum_exact, min_coverage, sum_coverage, reference_strength, newest_date, oldest_date, newest_mtime_ns, oldest_mtime_ns)` in descending order.
- Sort a missing date after every valid ISO date.
- Define a tie only when the complete ranking tuple is equal for multiple candidates or pairs. Return those candidates as one ambiguity; ask one concise disambiguation question and do not select arbitrarily.

## Determine Plan Review State

Return exactly `approved`, `not-approved`, or `unknown`.

Accept only one of these forms:

1. YAML frontmatter beginning at byte zero that is either a complete chinese-current plan or a compatible english-legacy frontmatter record; or
2. When no frontmatter exists, one ASCII-only legacy header using column-zero `Review-Status`, `Reviewer`, and `Reviewed-At` fields within the first 20 non-empty metadata lines before the first Markdown heading, code fence, or body paragraph.

For every frontmatter, parse only simple flat `key: scalar` entries. Accept an ASCII key matching the legacy key grammar or an exact Chinese key from this fixed plan set: `文档类型`, `主题`, `技术规格`, `技术规格用户批准`, `计划评审状态`, `计划评审角色`, and `计划评审日期`. Classify the schema before reading status. A mixed schema, semantic duplicate, unknown Unicode key, malformed line, nested value, multiline scalar, unrecognized quoting, or unclosed frontmatter is `unknown`. Do not fall back to the header form when frontmatter exists.

An english-legacy plan keeps the existing review-only contract: require one `review_status` to classify review, map case-insensitive `approved` to `approved`, map another explicit scalar state to `not-approved`, and preserve optional unique `reviewer` and `reviewed_at` values. Do not add document type, topic, or spec-path requirements to this legacy schema.

A complete Chinese plan requires exactly one `文档类型: 实施计划`, a non-reserved kebab-case `主题`, a non-empty `技术规格`, `技术规格用户批准: 已批准`, and one supported plan-review state. Map `计划评审状态: 已通过` to `approved` only when unique non-empty `计划评审角色` and ISO `计划评审日期` fields are present; preserve those two technical values. Map `计划评审状态: 待评审` to `not-approved` only when reviewer and date are absent. A missing required field, stale lifecycle field, invalid date, or unsupported localized value is `unknown`; reviewer or date never substitutes for approval.

Keep the header parser separate and ASCII-only. Do not accept Chinese metadata in the legacy header. Treat duplicate or conflicting header fields and markers inside examples or code fences as `unknown`.

Allow prompt generation for all three states. Require the rendered prompt to block implementation before modification whenever the state is not `approved`.
