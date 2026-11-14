#!/usr/bin/env python3
"""
context_engine.py - a minimal, runnable sketch of the anyam "context-first"
orchestration idea (Option A in proposal-gemini.md).

Given short written submissions from several stakeholders (fictional example
included), it demonstrates three mechanics from the proposal:

  1. Tacit context capture: assumptions and constraints are collected
     per stakeholder as structured input, before any AI execution.
  2. Conflict detection: pairs of assumptions from different stakeholders
     that overlap in topic but use opposing modality markers are flagged
     into a decision matrix for humans to resolve.
  3. Review routing: each review item is routed to the stakeholder whose
     domain keywords match best - the "taste routing" sketch.

This is a HEURISTIC DEMO on a fictional example, not a validated system.
Keyword overlap and modal markers are crude proxies; the proposal itself is
unvalidated (see framing-and-limitations.md).

Python 3.9+, no third-party dependency for the analysis.
--viz needs matplotlib.

Usage:
    python3 context_engine.py                 # fictional example, text output
    python3 context_engine.py --input team.json
    python3 context_engine.py --viz context.png
"""

import argparse
import json
import math
import re
from collections import Counter

WORD_RE = re.compile(r"[a-z][a-z0-9]+")

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "with",
    "as", "by", "is", "be", "we", "our", "must", "should", "will", "can",
    "not", "no", "all", "it", "this", "that", "users", "user", "team",
}

POSITIVE_MARKERS = {"must", "always", "require", "required", "needs", "shall"}
NEGATIVE_MARKERS = {"never", "avoid", "without", "cannot", "can't", "only"}

# --- Fictional example: a team planning a generic team-planning product -----
EXAMPLE = {
    "stakeholders": [
        {
            "role": "engineering",
            "domains": ["architecture", "deployment", "performance", "security",
                        "offline", "cache", "sync", "backend"],
            "assumptions": [
                "The app must work fully offline; user data must never leave the device.",
                "The team can only ship fixes on weekdays.",
            ],
        },
        {
            "role": "product",
            "domains": ["roadmap", "pricing", "research", "scope", "copy",
                        "onboarding"],
            "assumptions": [
                "The app must sync user data across devices in real time.",
                "We should avoid a login screen to keep onboarding friction low.",
            ],
        },
        {
            "role": "support",
            "domains": ["incidents", "feedback", "documentation", "runbook",
                        "weekend", "response", "fixes"],
            "assumptions": [
                "Support must be able to ship fixes on weekends.",
                "We must never lose user data, even locally.",
            ],
        },
    ],
    "review_items": [
        "Check whether the offline cache eviction policy can drop unsynced entries.",
        "Review the pricing page copy for the free tier.",
        "Validate the weekend incident-response runbook.",
    ],
}


def stem(token):
    """Crude fold of plural/verb endings so 'devices' ~ 'device', 'fixes' ~ 'fix'."""
    if len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    if len(token) > 3 and token.endswith("e"):
        token = token[:-1]
    return token


def tokens(text):
    return [stem(t) for t in WORD_RE.findall(text.lower()) if t not in STOPWORDS]


def tfidf_sim(text_a, text_b, corpus):
    """Cosine similarity over TF-IDF vectors built from the small corpus."""
    docs = [tokens(t) for t in corpus]
    df = Counter()
    for d in docs:
        df.update(set(d))
    n = len(docs)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    def vec(text):
        tf = Counter(tokens(text))
        v = {t: (c / max(1, len(tokens(text)))) * idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    a, b = vec(text_a), vec(text_b)
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def opposing_markers(text_a, text_b):
    """True if one text asserts and the other negates (crude modality check)."""
    def polarity(t):
        words = set(WORD_RE.findall(t.lower()))
        has_neg = bool(words & NEGATIVE_MARKERS) or "must not" in t.lower()
        has_pos = bool(words & POSITIVE_MARKERS)
        # negation dominates: "must never leave" is a prohibition, not a duty
        if has_neg:
            return "neg"
        if has_pos:
            return "pos"
        return None

    pa, pb = polarity(text_a), polarity(text_b)
    return pa is not None and pb is not None and pa != pb


def shared_topic(text_a, text_b):
    """Shared content stems, displayed with original words from text_a."""
    raw_a = [t for t in WORD_RE.findall(text_a.lower()) if t not in STOPWORDS]
    tb = set(tokens(text_b))
    return {raw for raw in raw_a if stem(raw) in tb}


def detect_conflicts(stakeholders, sim_threshold=0.15):
    corpus = [a for s in stakeholders for a in s["assumptions"]]
    conflicts = []
    for i in range(len(stakeholders)):
        for j in range(i + 1, len(stakeholders)):
            for a in stakeholders[i]["assumptions"]:
                for b in stakeholders[j]["assumptions"]:
                    topic = shared_topic(a, b)
                    if not topic:
                        continue
                    sim = tfidf_sim(a, b, corpus)
                    if sim >= sim_threshold and opposing_markers(a, b):
                        conflicts.append({
                            "between": [stakeholders[i]["role"], stakeholders[j]["role"]],
                            "statement_a": a,
                            "statement_b": b,
                            "shared_terms": sorted(topic),
                            "similarity": round(sim, 3),
                        })
    return conflicts


def overlap_matrix(stakeholders):
    corpus = [a for s in stakeholders for a in s["assumptions"]]
    roles = [s["role"] for s in stakeholders]
    m = [[0.0] * len(roles) for _ in roles]
    for i in range(len(stakeholders)):
        for j in range(len(stakeholders)):
            if i == j:
                m[i][j] = 1.0
                continue
            best = 0.0
            for a in stakeholders[i]["assumptions"]:
                for b in stakeholders[j]["assumptions"]:
                    best = max(best, tfidf_sim(a, b, corpus))
            m[i][j] = best
    return roles, m


def route_reviews(stakeholders, items):
    """Route each item by domain-keyword match count.

    The score is a raw keyword-overlap count, not a confidence. Ties and
    zero matches are reported explicitly instead of picking silently.
    """
    routes = []
    for item in items:
        itok = set(tokens(item))
        scores = {}
        for s in stakeholders:
            domain_tokens = set(tokens(" ".join(s.get("domains", []))))
            scores[s["role"]] = len(itok & domain_tokens)
        top = max(scores.values()) if scores else 0
        winners = [r for r, sc in scores.items() if sc == top]
        if top == 0:
            routed = "unrouted (no domain keyword match)"
        elif len(winners) > 1:
            routed = f"tie between {', '.join(winners)} - needs human choice"
        else:
            routed = winners[0]
        routes.append({"item": item, "routed_to": routed, "scores": scores})
    return routes


def print_report(stakeholders, conflicts, routes):
    print("TACIT CONTEXT CAPTURED")
    for s in stakeholders:
        print(f"  {s['role']} ({len(s['assumptions'])} assumptions, "
              f"domains: {', '.join(s['domains']) or 'none'})")
    print("\nDECISION MATRIX - flagged contradictions for humans to resolve")
    print("(heuristic: shared topic + opposing modal markers; review by hand)")
    if not conflicts:
        print("  none flagged")
    for c in conflicts:
        print(f"  [{', '.join(c['between'])}] shared terms: {', '.join(c['shared_terms'])}")
        print(f"    A: {c['statement_a']}")
        print(f"    B: {c['statement_b']}")
    print("\nREVIEW ROUTING (keyword-match score = raw count of domain keyword")
    print("overlaps, not a confidence; ties and no-match items are NOT auto-routed)")
    for r in routes:
        score_str = ", ".join(f"{k}={v}" for k, v in r["scores"].items())
        print(f"  -> {r['routed_to']}: {r['item']}  [scores: {score_str}]")
    print("\nReminder: keyword overlap is a crude proxy. This demonstrates the")
    print("mechanics of the proposal; it is not a validated routing algorithm.")


def make_viz(stakeholders, roles, matrix, routes, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    data = np.array(matrix)
    im = ax1.imshow(data, cmap="viridis", vmin=0, vmax=1)
    ax1.set_xticks(range(len(roles)), roles, fontsize=9)
    ax1.set_yticks(range(len(roles)), roles, fontsize=9)
    for i in range(len(roles)):
        for j in range(len(roles)):
            if i != j and matrix[i][j] > 0:
                ax1.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center",
                         color="white", fontsize=9, weight="bold")
    ax1.set_title("Assumption overlap between stakeholders\n(max TF-IDF cosine - heuristic)",
                  fontsize=10)
    fig.colorbar(im, ax=ax1, fraction=0.046)

    all_roles = [s["role"] for s in stakeholders]
    width = 0.8 / len(all_roles)
    if routes:
        items = [r["item"] for r in routes]
        x = np.arange(len(items))
        for k, role in enumerate(all_roles):
            vals = [r["scores"].get(role, 0) for r in routes]
            ax2.bar(x + k * width, vals, width, label=role)
        short = [it[:28] + "..." if len(it) > 28 else it for it in items]
        ax2.set_xticks(x + width * (len(all_roles) - 1) / 2)
        ax2.set_xticklabels(short, fontsize=8, rotation=15, ha="right")
        ax2.set_yticks(range(0, max(max(r["scores"].values()) for r in routes) + 2))
    else:
        ax2.text(0.5, 0.5, "no review items to route", ha="center", va="center",
                 transform=ax2.transAxes, fontsize=10)
    ax2.set_ylabel("domain keyword matches")
    if routes:
        ax2.legend(fontsize=8)
    ax2.set_title("Review routing scores per item\n(fictional example - heuristic demo)", fontsize=10)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", help="JSON file with 'stakeholders' and 'review_items'")
    ap.add_argument("--viz", metavar="PNG", help="write charts to this path")
    args = ap.parse_args()

    data = EXAMPLE
    if args.input:
        try:
            with open(args.input, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot read input JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("input JSON must be an object with 'stakeholders' and optional 'review_items'")
    stakeholders = data.get("stakeholders")
    if not isinstance(stakeholders, list) or not stakeholders:
        raise SystemExit("input must contain a non-empty 'stakeholders' list")
    review_items = data.get("review_items", [])
    if not isinstance(review_items, list) or not all(isinstance(it, str) for it in review_items):
        raise SystemExit("'review_items' must be a list of strings (omit it or use [] for none)")
    seen_roles = set()
    for i, s in enumerate(stakeholders, 1):
        if not isinstance(s, dict):
            raise SystemExit(f"stakeholder #{i} must be an object")
        role = s.get("role")
        if not isinstance(role, str) or not role.strip():
            raise SystemExit(f"stakeholder #{i} needs a non-empty string 'role'")
        for field in ("assumptions", "domains"):
            v = s.get(field, [])
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise SystemExit(f"stakeholder '{role}': '{field}' must be a list of strings")
            s[field] = v
        if role in seen_roles:
            raise SystemExit(f"duplicate stakeholder role '{role}' - merge its lists into one entry")
        seen_roles.add(role)
        s.setdefault("domains", [])  # unknown-role stakeholders: no keywords
    conflicts = detect_conflicts(stakeholders)
    routes = route_reviews(stakeholders, review_items)
    print_report(stakeholders, conflicts, routes)
    if args.viz:
        roles, matrix = overlap_matrix(stakeholders)
        print(f"\nCharts written to {make_viz(stakeholders, roles, matrix, routes, args.viz)}")


if __name__ == "__main__":
    main()
