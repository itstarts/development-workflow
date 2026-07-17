# Product Requirements Document Contract

Use `assets/prd-template.md`. Replace every angle-bracket slot with current evidence and remove instructional slot text from the finished document.

Write the user-facing document title, section headings, explanatory prose, and template-derived content in Chinese by default. Keep YAML frontmatter keys, allowed values, paths, commands, API names, field names, protocols, filenames, and other technical identifiers in their established technical form.

The `topic` value is the same non-reserved lowercase ASCII kebab-case topic confirmed in the current requirements-understanding summary and emitted in the handoff. Do not translate, localize, title-case, or independently rename it when writing the PRD.

## Required Product Content

State the product problem, goals, non-goals, success measures, target users, user scenarios, scope, observable product requirements, business rules, product-visible error behavior, acceptance criteria, dependencies, risks, and assumptions. Add performance, compatibility, privacy, accessibility, or other non-functional requirements only when they affect product behavior.

Record product-visible constraints without choosing a technical solution. Keep architecture, component design, API definitions, database schemas, migration design, code files, and implementation tasks out of the PRD. Move those concerns to the downstream technical specification.

## Frontmatter and Approval States

Write flat YAML frontmatter from byte zero. A new PRD can exist only after confidence is at least 95 and the current requirements-understanding summary is confirmed, so it begins with that confirmation approved while document approvals remain pending.

`understanding_user_confirmation` records confirmation of the pre-document summary; it is not PRD approval. `independent_review` records a fresh reviewer verdict. `user_approval` records the user's explicit approval of the independently reviewed current file.

Use repository-relative paths inside the PRD and an absolute path in the handoff.
