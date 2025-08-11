````markdown
# ARC-3 OpenHands Orchestrator

This project uses [OpenHands](https://github.com/All-Hands-AI/OpenHands) to solve ARC Prize 3 tasks step-by-step using a **DSL-based agent orchestration** approach.

## Overview
- Each step is executed by a **fresh OpenHands agent**.
- Agent receives:
  - All previous grids/images in JSON
  - State/history from prior steps
- Agent produces:
  - Next DSL action
  - A short summary in `current_status.txt`
  - Validation results
- This continues until the test output is solved or max steps are reached.

---

## 1. Run Main Coordinator

```bash
python main.py -a=apiagent -g="ft09,vc33,ls20"
````

**Arguments**

* `-a=apiagent` — uses the API-based OpenHands agent.
* `-g="ft09,vc33,ls20"` — comma-separated ARC task IDs to solve.

This will:

1. Initialize `state.json` for each task.
2. Pass task data to OpenHands with the system prompt.
3. Wait for the agent to output `action_{STEP}.json`.
4. Execute and validate DSL actions.
5. Append summaries to `current_status.txt`.

---

## 2. Files Generated

| File                     | Description                                        |
| ------------------------ | -------------------------------------------------- |
| `state.json`             | Current orchestration state, history, and metadata |
| `current_status.txt`     | One-line log per step                              |
| `action_{STEP}.json`     | Agent's DSL program + rationale                    |
| `validation_{STEP}.json` | Train pair validation results                      |
| `solution.json`          | Final test solutions                               |

---

## 3. Workflow

1. **Coordinator** (`main.py`) reads ARC grids & state.
2. **OpenHands Agent** plans the next step.
3. **DSL Runner** applies the program.
4. **Validator** checks train outputs.
5. If passed → Apply to test inputs → Save `solution.json`.
6. If failed → Try next step until stop conditions.

---

## 4. Requirements

```bash
pip install -r requirements.txt
```

* Python 3.10+
* DSL runner (`run_dsl.py`) in `/workspace/`
* OpenHands API credentials/config

---

## 5. Notes

* `current_status.txt` is your quick tail log: `tail -f current_status.txt`
* Keep DSL programs general — avoid overfitting train pairs.
* Max steps & time limits are set in `state.json`.

---
