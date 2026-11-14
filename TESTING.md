# Testing and dependencies

Python 3.9+. Analysis: standard library only. Charts: matplotlib.

Commands run and verified (2026-11-15, Python 3.10):

    python3 context_engine.py
    python3 context_engine.py --input team.json        # valid custom input
    python3 context_engine.py --input bad.json         # rejected cleanly
    python3 context_engine.py --viz context.png
    python3 interview_walkthrough.py
    python3 interview_walkthrough.py --viz walkthrough.png

Verified behavior:

- context_engine.py flags the two planted contradictions in the fictional
  example (offline-only vs real-time sync; weekday-only fixes vs weekend
  fixes) and a negation-only pair in a custom input. Routing reports raw
  keyword-match scores, not confidence; ties between roles and items with no
  keyword match are reported as tie/unrouted, never silently assigned.
  Stakeholders without a domains list are accepted and simply match nothing.
  Known limit: shared vocabulary with the same polarity passes silently, and
  contradictions of meaning (rather than of modal markers) are beyond this
  keyword heuristic.
- interview_walkthrough.py prints the scripted interview, six constraints
  with proposed/confirmed/adjudicated states and per-answer provenance, five
  scenarios, and check results: S1 and S4 pass; S2 and S3 fail, catching the
  planted Saturday bug, with evidence traced to the source answers; S5 is
  skipped because its constraint is only proposed.

The Pages site (docs/) was rendered headless and inspected at 1280px and
390px widths.
Input validation (all produce a clean one-line error, exit 1): non-object JSON
(e.g. []), null/non-object stakeholder entries, missing or non-string role,
non-string entries in assumptions/domains, non-string review_items, and
duplicate roles. An empty review_items list renders an explicit
"no review items to route" panel instead of an exception.
