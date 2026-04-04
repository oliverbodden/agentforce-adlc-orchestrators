# Eval Config Changelog

## Utterances u1 (2026-03-28)
- Initial utterance set extracted from v21 baseline (850 rows)
- 102 unique utterances: 88 single-turn, 14 multi-turn follow-ups
- Multi-turn follow-ups identified by short length + confirmation patterns ("yes", "none", etc.)

## Scoring s1 (2026-03-28)
- Initial scoring scripts from v21 eval cycle
- `run_regression.py`: 15-dimension comparison (strategy mix, template adherence, formatting, consistency, etc.)
- `analyze_response.py`: Single-response quality checker with JSON parsing for sf CLI output
- Known limitation: EXPLAIN strategy detection requires "here's what I found" in response text
