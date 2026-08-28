# Porter Discovery Instructions

This folder contains Porter Discovery, a separate system for discovering new staffing and PEO companies from state registration data, researching intent signals, supporting human review, and eventually sending approved leads to Salesforce or another sales workflow.

Porter Discovery is not Porter Verify. Do not change Porter Verify behavior unless the current task explicitly asks for it. You may inspect Porter Verify and reuse useful patterns, but do not depend on it blindly.

For every task in this folder:

- Use Ponytail full mode.
- Follow the repository `AGENTS.md` Karpathy Coding Guidelines.
- Write code like a senior human engineer maintaining a company-grade product.
- Inspect the existing flow before editing.
- Make the smallest correct change.
- Keep names clear and code boring.
- Reuse existing patterns when they are actually useful.
- Do not add generic interfaces, factories, placeholder services, empty layers, or future scaffolding.
- Do not add a new dependency unless this exact task clearly requires it.
- Add the smallest useful test or check when the task adds non-trivial behavior.
- Every changed line must directly support the current task.

At the end of each task, report:

- What changed.
- How it was checked.
- What was intentionally not built.
