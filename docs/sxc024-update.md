# Preparing the Semantic Crosscheck v0.24.0 snapshot

`scripts/update_sxc024_references.py` is an offline, dry-run-by-default updater.
It reads immutable Git blobs from an exact annotated `v0.24.0` tag. The caller
must first independently verify that the tag, peeled commit and published release
are publicly available. The helper does not publish, fetch, modify plugin source,
create artwork, or establish that release evidence passed.

Supply the final verified public commit, rather than a branch name, candidate
commit or placeholder hash:

```text
python scripts/update_sxc024_references.py --plugin-root <published-checkout> --sxc-commit <full-public-sxc-commit> --pending-artwork docs/sxc024-card-artwork.pending.json
```

Inspect the dry-run result before repeating with `--apply`. Apply updates
`data/registry.source.json` and current citation mappings in
`docs/card-artwork-unique-prompts.json`, using the existing helper with rollback
on ordinary errors. This is not a crash-atomic transaction across both files.
It never rewrites image files, prompts, hashes, dimensions or generation history.
The original 149 canonical identities, all raw curation rows, aliases, roles and
notes survive, including the Agentic Vault snapshot and cited uses.

The four identities are StrykerJS (project), Mutation Testing Elements report
schema (format), SPES paper (paper), and SPES repository (background project).
They are previously researched references with the new applications recorded in
their notes, rather than newly discovered works. Canonical identity collisions
require a reviewed merge. No unimplemented source is added.

Each identity requires exactly one canonical citation line in `THIRD_PARTY.md`
and one in its feature document. StrykerJS and Mutation Testing Elements use
`docs/mutation-matrix.md`; both SPES identities use
`docs/join-aggregate-fixtures.md`. At least one of the two lines must contain
the exact upstream pin declared in `SPECS`, including arXiv v2 for the paper.
Current repository evidence uses the final SXC commit and exact 1-based line
number, with `strip()[:220]` excerpts. Every existing SXC citation is repinned by
a unique exact excerpt match; ambiguous or missing excerpts stop preparation.

Changed existing wording requires `--reviewed-excerpts <review-json>`. Its
`sxc_commit` must equal the final commit. Each item of `reviews` needs
`source_id`, `file`, `old_excerpt`, `new_excerpt` and a nonempty `reason` recording
the public wording review. Duplicate, unused, ineffective or unbound reviews
are rejected. Applying the same reviewed change again at its bound commit is
idempotent. Review the returned `reviewedExcerptChanges` with the public blobs.

The prepared coverage contract is 153 identities, 277 citations and 66 SXC
citations: the prior 149/269 and 58 SXC citations plus four identities and eight
feature citations. Agentic Vault coverage is unchanged. A repeat at the same
commit adds no identity or citation, preserves the timestamp and curation, and
reports zero repins. Changed public citation structure requires a reviewed helper
and test update rather than silently broadening these counts.

Four separately commissioned raster card images are prepared in
`docs/sxc024-card-artwork.pending.json`, with exact prompts, public upstream
generation evidence, source-image hashes and delivery metadata. They are stored
as distinct versioned files under `media/cards/`. Each original 1536x1024 PNG was
converted full-frame to RGB and resized to 960x640 with LANCZOS, then encoded as
WebP quality 90/method 6 using the recorded Pillow/WebP versions. No crop or
content edit was performed. This is a delivery transcode with its toolchain
recorded, rather than a claim of cross-version binary reproducibility.

Attaching the four records to the current main artwork manifest remains a
publication requirement. `--pending-artwork` verifies every actual image hash,
byte count and WebP signature before any apply. Its pinned upstream generation
citations remain fixed; current SXC evidence URLs derive from the final public
source rows. Repeating the same attachment is idempotent.
The existing build copies WebP/PNG and the artwork contract checks WebP bytes;
SVG cards would bypass that contract. The updater reports
`pendingArtworkSourceIds` until assignments are attached. It accepts and
preserves those new assignments on reapplication, including their generation
evidence. Keep source-specific prompts, paths, actual hashes and visual concepts
distinct; assign no borrowed or renamed image. The final node suite requires all
153 cards to have their own image in both card and detail views.

After applying the real final update and commissioning its images:

```text
python scripts/build_catalog.py
python -m unittest discover -s tests -p "test_*.py"
node --test
node scripts/build.mjs
git diff --check
```

The test suite exercises annotated-tag blob reads, a changed worktree, leading
blank lines, dry-run preservation, repeated apply, aliases, all original
identities, explicit excerpt reviews and commissioned-artwork reapplication.
Use independent public evidence verification and the normal GitHub Pages review
and publication process after these checks. No Sites hosting is involved.
