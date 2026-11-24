#!/usr/bin/env python3
"""
interview_walkthrough.py - scripted walkthrough of the anyam closed loop:
interview -> draft constraints -> human confirmation -> scenarios -> checks
-> plain-language evidence.

A FICTIONAL, SCRIPTED demo on one invented feature (a weekly digest email
for a team-planning tool). It exists to make the pipeline inspectable:

  * every draft constraint and scenario links back to the exact interview
    answer it came from (provenance);
  * every draft carries an explicit state: PROPOSED, CONFIRMED, or
    ADJUDICATED (a human resolved an apparent contradiction);
  * checks run against a tiny toy implementation and report failures in
    language the original contributor could read.

Honest limits, stated plainly:
  * The "extraction" here is AI-written for the script. A real system
    would need an AI interviewer whose elicitation quality is itself
    unevaluated - this demo says nothing about that working.
  * Confirmed-by-a-human is a state, not a guarantee: a confirmed
    constraint can still be wrong.
  * The checks are AI-written assertions against a toy implementation,
    NOT automatically generated integration tests. No claim is made that
    narrative answers can be reliably compiled into test code.

Python 3.9+, no third-party dependency. --viz needs matplotlib.

Usage:
    python3 interview_walkthrough.py                 # full walkthrough
    python3 interview_walkthrough.py --viz walkthrough.png
"""

import argparse

# --- 1. The scripted interview (fictional people, fictional product) --------
INTERVIEW = [
    ("Q1", "interviewer", "What should the weekly digest do?",
     "operations lead",
     "It should give the team one summary email of the week's open items, "
     "so people stop asking for status in chat."),
    ("Q2", "interviewer", "How often should it send?",
     "operations lead",
     "Once a week is enough. More email and people will ignore it."),
    ("Q3", "interviewer", "When should it go out?",
     "operations lead",
     "Monday morning, before the week starts. Never on weekends - people "
     "should not get work email on their days off."),
    ("Q4", "interviewer", "Any exceptions?",
     "product lead",
     "If something urgent happens - like an incident - the team needs to "
     "know immediately, even on a weekend."),
    ("Q5", "interviewer", "What must never happen?",
     "product lead",
     "Never email a person about items that are already closed. That "
     "destroys trust in the digest fast."),
]

# --- 2. Draft constraints extracted from answers (AI-written for the demo) -
# state: PROPOSED until a human confirms; ADJUDICATED when a human resolves
# an apparent contradiction.
CONSTRAINTS = [
    {"id": "C1", "state": "CONFIRMED", "source": "Q1",
     "text": "The digest summarizes the week's open items in one email."},
    {"id": "C2", "state": "CONFIRMED", "source": "Q2",
     "text": "The digest sends at most once per week."},
    {"id": "C3", "state": "ADJUDICATED", "source": "Q3",
     "text": "The digest sends on Monday morning and not on weekends."},
    {"id": "C4", "state": "ADJUDICATED", "source": "Q4",
     "text": "Urgent incident items may notify immediately, including "
            "weekends."},
    {"id": "C5", "state": "CONFIRMED", "source": "Q5",
     "text": "No email may include closed items."},
    {"id": "C6", "state": "PROPOSED", "source": "Q1",
     "text": "The digest replaces all other status reporting. "
             "(Not confirmed - the interviewer inferred more than the "
             "answer says.)"},
]

# The human adjudication that resolved the apparent C3/C4 contradiction.
ADJUDICATION = (
    "C3 and C4 look contradictory (never on weekends vs. urgent items on "
    "weekends). Human decision: they apply to different message types - the "
    "regular digest never goes out on weekends; a separate urgent-incident "
    "notification may. Both kept, scoped accordingly."
)

# --- 3. Draft scenarios (Gherkin-style), each linked to a constraint --------
SCENARIOS = [
    {"id": "S1", "constraint": "C2", "state": "CONFIRMED",
     "given": "a user with open items this week",
     "when": "the digest job runs twice in the same week",
     "then": "the user receives exactly one digest email"},
    {"id": "S2", "constraint": "C3", "state": "CONFIRMED",
     "given": "a Saturday with open non-urgent items",
     "when": "the digest job runs",
     "then": "no digest email is sent"},
    {"id": "S3", "constraint": "C4", "state": "CONFIRMED",
     "given": "a Saturday with an urgent incident item",
     "when": "the digest job runs",
     "then": "an urgent notification is sent for the incident item only"},
    {"id": "S4", "constraint": "C5", "state": "CONFIRMED",
     "given": "a user whose items are all closed",
     "when": "the digest job runs",
     "then": "no email is sent"},
    {"id": "S5", "constraint": "C6", "state": "PROPOSED",
     "given": "any week",
     "when": "status is needed",
     "then": "no other reporting channel is used "
             "(not confirmed - excluded from checks)"},
]


# --- 4. A tiny toy implementation with one planted mistake ------------------
def toy_digest_decisions(day, items, sent_this_week):
    """Toy 'feature under test': decide what emails go out today.

    day: 'Monday'..'Sunday'; items: list of (title, status, urgent).
    Returns a list of sent emails. Planted bug: the weekend guard only
    checks Sunday, so a Saturday digest for non-urgent items slips through.
    """
    sent = []
    open_items = [i for i in items if i[1] == "open"]
    urgent = [i for i in open_items if i[2]]
    if urgent:
        sent.append(("urgent", [t for t, _, _ in urgent]))
    if day != "Sunday" and open_items and not sent_this_week:
        sent.append(("digest", [t for t, _, _ in open_items]))
    return sent


# --- 5. Run confirmed scenarios as AI-written checks ----------------------
def check(scenario_id):
    """AI-written assertions per scenario. Returns (passed, evidence)."""
    if scenario_id == "S1":
        items = [("write report", "open", False)]
        first = toy_digest_decisions("Monday", items, sent_this_week=False)
        second = toy_digest_decisions("Wednesday", items,
                                      sent_this_week=bool(first))
        n = len([m for m in first + second if m[0] == "digest"])
        return n == 1, f"digest emails in one week: {n} (expected 1)"
    if scenario_id == "S2":
        items = [("write report", "open", False)]
        sent = toy_digest_decisions("Saturday", items, sent_this_week=False)
        return not sent, f"emails on Saturday with only non-urgent items: " \
                         f"{len(sent)} (expected 0)"
    if scenario_id == "S3":
        items = [("db down", "open", True), ("write report", "open", False)]
        sent = toy_digest_decisions("Saturday", items, sent_this_week=False)
        urgent_only = sent and all(m[0] == "urgent" for m in sent)
        titles = [t for _, ts in sent for t in ts]
        ok = urgent_only and "db down" in titles and "write report" not in titles
        return ok, f"Saturday emails: {sent} (expected urgent only: db down)"
    if scenario_id == "S4":
        items = [("write report", "closed", False)]
        sent = toy_digest_decisions("Monday", items, sent_this_week=False)
        return not sent, f"emails when all items closed: {len(sent)} (expected 0)"
    return None, "no check implemented"


def answer_text(qid):
    return next(a for q, _, _, _, a in INTERVIEW if q == qid)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--viz", metavar="PNG", help="write a state overview chart")
    args = ap.parse_args()

    print("SCRIPTED WALKTHROUGH - fictional feature, fictional people.")
    print("Extraction and checks are AI-written; nothing here shows an AI")
    print("interviewer or automatic test generation working.\n")

    print("1. INTERVIEW (scripted)")
    for qid, speaker, q, role, a in INTERVIEW:
        print(f"  {qid} {speaker}: {q}")
        print(f"      {role}: {a}\n")

    print("2. DRAFT CONSTRAINTS (state + provenance)")
    for c in CONSTRAINTS:
        print(f"  {c['id']} [{c['state']:11s}] from {c['source']}: {c['text']}")
    print(f"\n  Adjudication: {ADJUDICATION}\n")

    print("3. SCENARIOS (confirmed ones become checks)")
    for s in SCENARIOS:
        print(f"  {s['id']} [{s['state']:8s}] for {s['constraint']}: "
              f"Given {s['given']}, when {s['when']}, then {s['then']}")

    print("\n4. CHECKS AGAINST THE TOY IMPLEMENTATION (evidence in plain language)")
    for s in SCENARIOS:
        if s["state"] != "CONFIRMED":
            print(f"  {s['id']}: SKIPPED - constraint {s['constraint']} is "
                  f"{s['state'].lower()}, not confirmed")
            continue
        passed, evidence = check(s["id"])
        mark = "PASS" if passed else "FAIL"
        src = next(c["source"] for c in CONSTRAINTS if c["id"] == s["constraint"])
        print(f"  {s['id']}: {mark} - {evidence}")
        print(f"       traces to {s['constraint']} <- interview answer {src}")
        if not passed:
            print(f"       contributor-facing note: the answer they gave in "
                  f"{src} (\"{answer_text(src)[:60]}...\") is not what the "
                  f"code currently does.")
    print("\nReminder: CONFIRMED means a human reviewed the draft, not that the")
    print("constraint is right. The loop makes mistakes inspectable; it does")
    print("not eliminate them.")

    if args.viz:
        make_viz(args.viz)
        print(f"\nChart written to {args.viz}")


def make_viz(path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    states = ["PROPOSED", "CONFIRMED", "ADJUDICATED"]
    colors = {"PROPOSED": "#95a5a6", "CONFIRMED": "#27ae60",
              "ADJUDICATED": "#f39c12"}
    c_counts = [sum(1 for c in CONSTRAINTS if c["state"] == st) for st in states]
    s_counts = [sum(1 for s in SCENARIOS if s["state"] == st) for st in states]
    x = range(len(states))
    b1 = ax1.bar([i - 0.2 for i in x], c_counts, width=0.4,
                 label="constraints", color="#2980b9")
    b2 = ax1.bar([i + 0.2 for i in x], s_counts, width=0.4,
                 label="scenarios", color="#8e44ad")
    for bars in (b1, b2):
        for b in bars:
            ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05,
                     str(int(b.get_height())), ha="center", fontsize=10)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(states, fontsize=9)
    ax1.set_ylabel("count")
    ax1.set_ylim(0, max(c_counts + s_counts) + 1.5)
    ax1.legend(fontsize=9)
    ax1.set_title("Draft states: proposed vs confirmed vs adjudicated\n"
                  "(scripted fictional demo)", fontsize=10)

    results, labels = [], []
    for s in SCENARIOS:
        if s["state"] != "CONFIRMED":
            labels.append(f"{s['id']}\nskipped")
            results.append(0.5)
            continue
        passed, _ = check(s["id"])
        labels.append(f"{s['id']}\n{'PASS' if passed else 'FAIL'}")
        results.append(1 if passed else 0)
    bar_colors = ["#95a5a6" if r == 0.5 else "#27ae60" if r == 1 else "#c0392b"
                  for r in results]
    ax2.bar(labels, [1] * len(results), color=bar_colors, width=0.6)
    ax2.set_yticks([])
    ax2.set_title("Checks against the toy implementation\n"
                  "S2 + S3 fail: the planted Saturday bug is caught", fontsize=10)

    fig.tight_layout()
    fig.savefig(path, dpi=150)


if __name__ == "__main__":
    main()
