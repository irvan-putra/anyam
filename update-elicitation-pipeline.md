# Update: elicitation pipeline with Socratic interviewer agents

This is a follow-up concept note that extends `proposal-gemini.md`. Like the original, it is idea-stage: the pipeline below has not been built, measured, or tested end to end. It is adapted from a Gemini follow-up concept note; review additions made during packaging are marked as such.

Read `framing-and-limitations.md` first. Everything there still applies.

## Motivation: skill asymmetry

The update identifies a specific gap this concept aims to bridge: not everyone on a team has end-to-end engineering skills (automated testing, architecture, deployment) to steer AI directly. The concept's concern is that when team members without those skills are forced to drive AI on their own, the resulting systems risk becoming brittle.

The proposed bridge: instead of asking non-technical staff or partial specialists to write prompts or test suites, the system places an Interviewer Agent upfront that translates their lived experience into technical artifacts that downstream builder agents can execute against.

## Proposed pipeline

| Stage | Actor | Function and output artifact |
| --- | --- | --- |
| 0. Domain input | Domain expert / team member | Shares lived operational experience, business constraints, and real-world edge cases in natural language. |
| 1. Elicitation | Socratic Interviewer Agent | Probes blind spots and hidden assumptions through adaptive, role-aware dialogue. |
| 2. Formalization | Structured context and spec graph | Compiles narrative answers into acceptance criteria, edge cases, and system constraints. |
| 3a. Execution | Builder / test agent | Generates code plus tests grounded in the interview. |
| 3b. Verification | Adversarial validator | Tests generated output against trap scenarios and edge cases drawn from the interview. |

## Mechanism 1: skill-aware adaptive interviewing

The interviewer adapts its questioning strategy to each contributor's technical profile:

- For end-to-end engineers, it probes architectural decisions, performance trade-offs, and system-level edge cases.
- For business or operations specialists, it interviews through everyday operational scenarios (for example, "If a user submits duplicate data while their mobile connection drops, what usually happens in the field?"). Narrative answers are then compiled into structured scenarios and test specifications, so domain experts can contribute tests without knowing testing framework syntax.

Adaptation should be keyed to declared role and the content of the interview itself, not to inferred personal traits. (Review guardrail.)

## Mechanism 2: cross-interview conflict and gap detection

When multiple stakeholders are interviewed independently (Product, Operations, Senior Engineering, and so on):

- The system maps overlapping answers and flags apparent contradictions before any code is written (for example, Operations assuming a manual approval step while Engineering assumes full automation).
- It then facilitates a short, targeted clarification session focused strictly on those flagged points.

Flagged contradictions are candidates, not verdicts. Two statements can look contradictory and both be correct in different scopes (manual approval for some flows, automation for others). Humans adjudicate every flagged conflict; the system proposes and never resolves on its own. (Review guardrail.)

## Mechanism 3: closed-loop verification

Interview insights are not discarded after the initial prompt. Key constraints and edge cases persist as an evaluation rubric. When a coding agent completes an implementation, an evaluator checks the result against every constraint stated during the interviews and translates the outcome back into plain language for the original contributor to confirm.

Two guardrails apply here (review additions):

- Every rubric entry must carry provenance: which interview answer it came from, and whether it is proposed or confirmed by the contributor. Unconfirmed entries stay visibly draft.
- Verification results must cite evidence (which scenario, which test, what happened), not only a reassuring summary. A plain-language translation can itself be unfaithful and invite rubber-stamping.

## Human confirmation checkpoints (review addition)

The closed loop only works if two human checkpoints are explicit:

1. Contributors confirm that formalized constraints and scenarios reflect what they actually meant before those entries govern any build.
2. Contributors resolve flagged contradictions themselves, with the system presenting options and scopes rather than picking a winner.

## Proposed research and product framing

- Research (HCI / software engineering): "From prompting to elicitation: bridging asymmetric technical skills in human-AI software teams via adaptive Socratic agents." A possible experiment would measure whether a skill-asymmetric team (for example, a non-coding domain expert paired with a junior developer), bridged by an interviewer agent, produces software with test coverage and edge-case resilience comparable to a senior engineer working alone. This is a study design idea only; no study, data collection, or recruitment has been planned or carried out.
- Product / open source: a CLI utility or web application (for example, a spec-interview step or pre-commit context collector) that runs before code generation in AI-assisted workflows, so features are governed by specifications and tests rooted in human interviews rather than AI-assumed defaults.

## What this update does not claim

- The end-to-end adaptive pipeline above has no implementation, benchmark, or study behind it. The repository does contain a small fictional demo of three Option-A mechanics (capture, conflict flagging, review routing), which is limited and unvalidated and does not implement this pipeline.
- The automatic compilation of narrative answers into reliable executable tests is the hard open problem here, not a solved step. Treat it as the main thing to validate first.
- A formalized rubric can create false confidence: a bad elicitation, once versioned and authoritative-looking, may be worse than no spec. The provenance and confirmation guardrails above exist to keep mistakes inspectable.
- Novelty has not been assessed. A literature review of requirements-elicitation agents and knowledge-elicitation methods is required before treating any part of this as new.
- Interviewing people and persisting their statements as a durable rubric collects their words. Any real use needs consent, ownership, and a way for contributors to edit or withdraw their statements.
