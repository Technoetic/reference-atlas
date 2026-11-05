# Check existing references before new plugin research

This workflow applies to improvement research for Agentic Vault and Semantic
Crosscheck. It is a duplication check, not a prohibition on reading or revisiting research.

1. Check the [published registry](https://technoetic.github.io/reference-atlas/data/catalog.json)
   or an explicitly dated local snapshot before presenting a source as a new reference.
2. Normalize arXiv versions/PDF links, DOI case, GitHub file/ref paths and verified
   repository aliases. Use `scripts/check_references.py` rather than comparing raw URLs.
3. For a known source, read its existing plugin use and pinned evidence. Skip a
   repeated recommendation if it adds no new question or implementation difference.
4. A new paper version, new applicability question or unimplemented idea can be
   reviewed again. State the previous use, the new delta and the evidence to test.
5. Name matches are tentative. Resolve the actual identifier instead of merging
   unrelated works with similar names.
6. A missing match is not proof of novelty. Check earlier research notes and the
   official source as well; the public registry covers only its stated snapshots.
7. Update the registry only after verifying public citation evidence. Do not promote
   speculative titles, private documents or dependency lists into adopted research.

Record the snapshot used, candidate identifier, match status, previous use and
new delta in the research output. Do not claim that every recorded source's code
or benchmark has been reproduced. Runtime/CI-only tools are outside the current
research-reference scope; unresolved and background records are marked explicitly.

The visual site, JSON/CSV downloads and offline CLI use the same catalog. Checking
it is part of the research process; the catalog itself does not grant permission
to edit a plugin, deploy software, contact others or publish private information.
