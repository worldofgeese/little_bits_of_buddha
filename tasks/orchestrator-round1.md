# LBOB Phase 1 Orchestrator — Round 1

You are an orchestrator agent managing three parallel Claude Code workers for the Little Bits of Buddha project.

## Your Job
1. Dispatch 3 ACP sessions in parallel (WP1, WP2, WP5)
2. Monitor their completion via git state
3. After each completes: verify (git log, run tests, check TDD compliance)
4. After ALL three complete: merge each branch to main in order, resolve conflicts
5. Write a deliverable report and announce completion

## Project Location
`/home/node/.openclaw/workspace/projects/little_bits_of_buddha`

## Task Briefs (already written)
- WP1: `tasks/wp1-state-store.md`
- WP2: `tasks/wp2-sutta-vectors.md`
- WP5: `tasks/wp5-rate-limiting.md`

## Dispatch (use sessions_spawn for each)
```
sessions_spawn(
  runtime: "acp",
  agentId: "claude",
  task: <contents of each task brief>,
  mode: "run",
  cwd: "/home/node/.openclaw/workspace/projects/little_bits_of_buddha"
)
```

Read each task file and pass its full contents as the `task` parameter.

## Verification per worker (after completion detected)
```bash
cd /home/node/.openclaw/workspace/projects/little_bits_of_buddha
git checkout <branch>
git log --oneline main..<branch>  # Verify TDD: test commit before impl commit
cd /home/node/.openclaw/devbox-env && devbox run -- bash -c "cd /home/node/.openclaw/workspace/projects/little_bits_of_buddha && python -m pytest tests/ -x -v"
```

## Merge Strategy
After all 3 verified:
1. `git checkout main`
2. Merge WP1 first (state store — least likely to conflict)
3. Merge WP5 next (rate limiting — touches __main__.py)
4. Merge WP2 last (sutta vectors — touches compose.yaml + new deps)
5. Run full test suite after each merge
6. Push main after all merges clean

## On Failure
- If a worker produces no commits after 10 min: kill and re-dispatch
- If tests fail after merge: fix the conflict yourself or dispatch a fix worker
- If 3 attempts fail: report to Tao with evidence

## Deliverable Report
When done, return a plain text report with:
- Status of each WP (done/partial/failed)
- Files changed per WP
- Test results (count, pass/fail)
- TDD compliance (test commit before impl commit? yes/no)
- Any self-review concerns from workers
- Final test suite result on main after all merges

Do NOT use message(action: "send"). Return the report as your final output.

## Graceful Exit
If running long or approaching limits: commit/push partial progress, list what remains, and report what's done.
