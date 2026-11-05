# Reference Atlas Implementation Plan

> For agentic workers: execute through independent implementers and a separate final reviewer.

**Goal:** Publish a visually compelling, evidence-bound research catalog and make
future duplicate-reference checks reusable.

**Architecture:** One audited JSON registry feeds a static ES-module site and an
offline Python checker. Public citation snapshots pin both plugin commits.

**Tech Stack:** HTML/CSS/ES modules, Canvas, Node standard library, Python standard
library, GitHub Actions/Pages, Aside CLI browser verification.

**Spec:** `docs/SPEC.md`.

## Global constraints

- GitHub Pages only; do not register, save or publish a Site.
- Public plugin sources only; no vault/company data or secrets in the public repo.
- Keep strict, background and unresolved reference categories visible.
- Unknown registry match does not establish novelty; permit explicit new-version deltas.
- Preserve working input during version checks; next clean navigation reloads the target.
- Public launch is authorized; source plugin changes/releases are out of scope.

## Review focus

1. A paper PDF/version or GitHub subpath must match its known canonical source.
2. Similar names and unknown identifiers must not be falsely labeled known/new.
3. Counts and shared-source connections must come from actual cited uses.
4. Deep links/history/390px/reduced motion and load errors must work on Pages.
5. A changed build must preserve check-input drafts until a safe navigation.

## Tasks

- [x] Extract semantic-crosscheck sources; reconcile with the audited agentic-vault inventory.
- [x] Write failing identity/merge/checker tests, implement one registry pipeline and CLI.
- [x] Build the extreme visual hero, catalog/detail/filter views and duplicate-check UI.
- [x] Build hashed assets/version identity and GitHub Actions Pages deployment.
- [x] Run tests, independent data/code review, and actual Aside local acceptance checks.
- [x] Publish the concrete reviewed site; cross-check published artifacts/behavior.
- [x] Connect persistent research guidance to the registry, save evidence, commit owned work.

## Verified release

- Build `206d3aeb59426f4c`; 102 distinct records and 165 pinned public citations.
- Node 50/50 and Python 19/19; separate source/evidence/asset and visual review.
- Actual Aside browser checks: local 14, public 14, built A/B update/rollback 9.
- The published-registry CLI distinguishes known identifiers and repository aliases
  from tentative names, registry misses and invalid inputs.
- Live: https://technoetic.github.io/reference-atlas/
