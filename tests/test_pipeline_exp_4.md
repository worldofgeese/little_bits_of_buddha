# Pipeline Experiment 4

## Objective
Test ACP worker detection with ~5 minute work duration

## Setup
- Branch: test/pipeline-exp-4
- Simulated work time: 5 minutes (300 seconds)
- Commit bypass: --no-verify flag used

## Timeline
- Start: 18:50 GMT+1
- Work duration: ~5 minutes
- Expected completion: ~18:55 GMT+1

## Expected Behavior
ACP worker should detect this branch activity after the 5-minute work period and trigger the commit pipeline.

## Notes
This experiment tests the worker's ability to detect sustained work activity on a branch with a realistic time window.
