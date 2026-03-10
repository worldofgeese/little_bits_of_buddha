# Ralph Agent Instructions — LBOB CI Fix

You are an autonomous coding agent fixing CI failures in the `little_bits_of_buddha` Python project.

## Your Task

1. Read the PRD at `scripts/ralph/prd.json`
2. Read the progress log at `scripts/ralph/progress.txt` (check Codebase Patterns section first)
3. Pick the **highest priority** user story where `passes: false`
4. Fix that single issue
5. Run quality checks: `sh scripts/run-tests.sh` and `sh scripts/run-lint.sh`
6. If checks pass locally, commit with: `fix: [Story ID] - [Story Title]`
7. Update prd.json to set `passes: true` for the completed story
8. Append your progress to `scripts/ralph/progress.txt`
9. Push to origin main: `git push origin main`

## Critical Context

### The Bug
`pytest` fails with `ModuleNotFoundError: No module named 'dapr.actor'; 'dapr' is not a package` during test collection. But the SAME import works fine outside pytest (proven by diagnostic in run-tests.sh).

### Root Cause Hypothesis
`pyproject.toml` has `[tool.pytest.ini_options] pythonpath = ["src"]` which adds `src/` to `sys.path` during test collection. The project uses `pdm-backend` as build-backend. When `pip install ".[test]"` installs the project, pdm-backend may create a package that interferes with dapr's implicit namespace package resolution. The `src/` directory contains service packages (seeker_actor_service, wisdom_service, etc.) but NO `dapr` directory — so the shadowing is indirect.

### Investigation Steps
1. Check what pdm-backend actually installs: `pip show little-bits-of-buddha` and check its installed files
2. Check if removing `pythonpath = ["src"]` and adjusting imports fixes the issue
3. Check if `pip install --no-build-isolation ".[test]"` changes behavior  
4. Check if adding a conftest.py that pre-imports dapr before pytest collection helps
5. Try: `python -c "import sys; sys.path.insert(0,'src'); from dapr.actor import ActorId"` — does it reproduce?

### CI Verification
After pushing, verify CI passes by checking the Forgejo API or waiting for the CI run.
The CI workflow is at `.forgejo/workflows/ci.yaml` and runs 3 jobs:
1. Run Tests (python:3.12 container)
2. Lint (python:3.12 container)  
3. Build Container Image (quay.io/podman/stable)

### Constraints
- Do NOT modify dapr source code
- Do NOT remove tests — fix the import mechanism
- Do NOT add unnecessary dependencies
- Keep changes minimal and focused
- Pre-commit hooks (ruff + ty) must pass

## Quality Requirements
- ALL commits must pass pre-commit hooks (ruff check, ruff format, ty check)
- Run `sh scripts/run-tests.sh` to verify test fix
- Run `sh scripts/run-lint.sh` to verify lint fix  

## Stop Condition
After completing a user story, check if ALL stories have `passes: true`.
If ALL stories are complete, reply with: <promise>COMPLETE</promise>
