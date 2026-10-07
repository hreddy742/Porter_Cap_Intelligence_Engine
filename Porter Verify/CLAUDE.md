# Claude Working Rules

## Finish active work before stopping

- Do not end the turn while a background task, workflow, agent, command, or monitor required by the user's request is still running.
- After launching background work, wait for it and check its status until it completes or fails, then report the actual result in the same turn.
- Do not say "I'll report once it completes" and stop. Continue supervising the work unless the user explicitly asked to start it and return immediately.
- If work cannot continue without user input or approval, state the specific blocker and ask for it. Otherwise, keep working to a terminal result.
- When parallel workers are used, collect every worker's terminal result before synthesizing the final answer.

