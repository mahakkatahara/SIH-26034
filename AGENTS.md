# AGENTS.md — SIH-26034

## Prime directive
NEVER write a stub, placeholder, mock, or `pass` body and describe it as
done. If you cannot implement something fully, stop and say so explicitly.
Do not edit the phase table in README.md to mark anything ✅ unless a real
test proves it works.

## Definition of done
A task is done only when ALL of these hold:
1. The code runs without import errors.
2. A pytest test exists in backend/tests/ and passes.
3. `curl` against the real endpoint returns real data, not a DEV_STUB marker.
4. No TODO/FIXME left in the code you just wrote.

## Architecture rules (non-negotiable)
- The rule engine is DETERMINISTIC. An LLM must never decide COMPLIANT or
  NON_COMPLIANT. LLMs extract text only; rules/engine.py decides.
- Every compliance finding must carry: rule_id, observed value, legal
  reference, and a confidence score.
- If confidence < AI_CONFIDENCE_THRESHOLD, downgrade to NEEDS_REVIEW.
- A missing declaration is NEEDS_REVIEW, not NON_COMPLIANT, unless the
  image clearly shows the whole panel. We may only be seeing one side.

## Legal accuracy
- Every rule in rule-engine/rules/rules.json needs a `citation_verified`
  boolean. Default false. Never set it true yourself.
- Never invent a legal citation. If unsure of the sub-clause, write
  "Rule 6(1) — sub-clause to verify" and flag it.

## Code conventions
- Backend: FastAPI, Python 3.11, SQLAlchemy 2, Pydantic v2, type hints on
  all public functions.
- Frontend: React 18 + TypeScript strict, Tailwind, Zustand.
- No new dependencies without listing them in the summary.
- Secrets only from .env via app/core/config.py. Never hardcode keys.

## Commits
Conventional commits. One logical change per commit.
