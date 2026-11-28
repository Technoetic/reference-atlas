"""Add the semantic-crosscheck v0.37.0 primary references, cross-axis links, card-269..276 artwork, and repin earlier uses."""
import argparse
from datetime import datetime, timezone
from functools import cache
import hashlib
import json
from pathlib import Path
import re
import subprocess

from build_catalog import merge_sources
from reference_identity import canonical_key, validate_catalog
from update_av048_references import excerpt_of
from update_av0521_references import ARTWORK, CATALOG_CSV, CATALOG_JSON, REGISTRY, built_catalog, encode, write_files
from update_sxc027_references import PLUGIN, PREFIX, repin


ROOT = Path(__file__).resolve().parents[1]
TAG = 'v0.37.0'
PRIOR_VERSION = 'v0.36.0'
PRIOR_COMMIT = '0cebbe4257fbe7e2f10fa184c25cde8e92831066'
AV_VERSION = 'v0.60.0'
NPD_VERSION = 'v0.3.0'

RELEASE = 'docs/releases/v0.37.0.md'
THIRD_PARTY = 'THIRD_PARTY.md'
PAIRED = 'docs/paired-release.md'

EXISTING_UPDATES = [
    dict(
        id='url:https://www.postgresql.org/docs/17/catalog-pg-index.html',
        note=(
            'PostgreSQL 17 system catalog documentation for pg_index (indisunique, indisvalid, indisready, '
            'indpred, indexprs and indnullsnotdistinct). Semantic Crosscheck v0.32.0 first recorded '
            'unique_nulls_not_distinct catalog facts in doctor and grain, v0.34.0 tightened the predicate '
            'in doctor._privileges_sql() and grain.evaluate() to require indisunique AND indisvalid AND '
            'indisready AND indpred IS NULL AND indexprs IS NULL AND indnullsnotdistinct, and v0.37.0 '
            'adds zero-extra-round-trip invalid/unready index counts (NOT indisvalid OR NOT indisready) '
            'on parent relations and recursive pg_inherits child partitions (invalid_indexes, '
            'child_invalid_indexes) with explicit not_proven disclosures and report hygiene parity '
            '(verified against live PostgreSQL 17 failed CREATE UNIQUE INDEX CONCURRENTLY in '
            'tests/test_rls_catalog_pg.py).'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-index.html'),
            (THIRD_PARTY, 'NOT indisvalid OR NOT indisready'),
        ],
    ),
]

SHARED_UPDATES = [
    dict(
        id='url:https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai',
        note_append=(
            'Semantic Crosscheck v0.37.0 applies this crash-consistency ordering to Result.write() in '
            'result.py by flushing and calling os.fsync() on temporary .result-*.part descriptors before '
            'closing and atomically replacing result.json, followed by a best-effort POSIX O_DIRECTORY '
            'parent-directory fsync (verified via unit tests in tests/test_result_contract.py).'
        ),
        cites=[
            (RELEASE, 'presentation/pillai'),
            (THIRD_PARTY, 'presentation/pillai'),
        ],
    ),
    dict(
        id='github:madthanu/alice',
        note_append=(
            'Semantic Crosscheck v0.37.0 references ALICE conceptually alongside Pillai et al. (OSDI 2014) '
            'for temp-file os.fsync() before os.replace() and best-effort POSIX parent-directory fsync '
            'ordering in result.py; no ALICE code or dependency is copied.'
        ),
        cites=[
            (RELEASE, 'github.com/madthanu/alice'),
            (THIRD_PARTY, 'github.com/madthanu/alice'),
        ],
    ),
    dict(
        id='doi:10.2307/4615733',
        new_url='https://www.jstor.org/stable/4615733',
        extra_keys=['url:https://www.jstor.org/stable/4615733'],
        note_append=(
            'Semantic Crosscheck v0.37.0 reuses this procedure in pure-stdlib holm_bonferroni_adjust() '
            'and build_multiplicity_diagnostics() inside tools/paired_release.py (schema '
            'semantic-crosscheck/holm-bonferroni/v1, diagnostic_only=true), emitting step-down FWER '
            'adjusted exact and Mid-P McNemar p-values across simultaneously evaluated (exposure, '
            'detections/false_positives) endpoints without changing existing groups, pairs, claim checks, '
            'or exit codes (cited via the live JSTOR record https://www.jstor.org/stable/4615733).'
        ),
        cites=[
            (RELEASE, 'jstor.org/stable/4615733'),
            (THIRD_PARTY, 'jstor.org/stable/4615733'),
            (PAIRED, 'jstor.org/stable/4615733'),
        ],
    ),
]

NEW_SOURCES = [
    dict(
        url='https://www.postgresql.org/docs/17/xfunc-volatility.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 36.7. Function Volatility Categories',
        year=2026,
        aliases=['PostgreSQL 17 Function Volatility', 'VOLATILE function', 'xfunc-volatility'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 documentation defining IMMUTABLE, STABLE, and VOLATILE function volatility '
            'categories and explaining that VOLATILE functions can observe data changes even within a '
            'REPEATABLE READ snapshot. Semantic Crosscheck v0.37.0 cites it for disclosing unpinned '
            'VOLATILE functions referenced transitively by source views (view_volatile_functions) in '
            'doctor.py and report.py.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/xfunc-volatility.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/xfunc-volatility.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-proc.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 51.39. pg_proc',
        year=2026,
        aliases=['PostgreSQL 17 pg_proc', 'provolatile'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_proc (provolatile function volatility '
            'classification). Semantic Crosscheck v0.37.0 joins pg_proc inside doctor._privileges_sql() '
            'with zero extra per-entity SQL round trips to count unpinned provolatile=\'v\' functions '
            'referenced by source views (view_volatile_functions) and disclose them in not_proven.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-proc.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-proc.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-rewrite.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 51.45. pg_rewrite',
        year=2026,
        aliases=['PostgreSQL 17 pg_rewrite', 'ev_class', 'ev_type'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_rewrite (rewrite rules backing views, '
            'ev_class and ev_type=\'1\' SELECT rules). Semantic Crosscheck v0.37.0 traverses SELECT '
            'rewrite rules recursively inside doctor._privileges_sql() (LEFT JOIN LATERAL on '
            'relkind=\'v\') to uncover transitive base-table and function dependencies hidden behind '
            'source views.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-rewrite.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-rewrite.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-depend.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 51.18. pg_depend',
        year=2026,
        aliases=['PostgreSQL 17 pg_depend', 'deptype', 'view dependency graph'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_depend (normal object dependencies '
            'deptype=\'n\' and pinned built-in pg_catalog omissions). Semantic Crosscheck v0.37.0 '
            'uses pg_depend alongside pg_rewrite and pg_inherits inside doctor._privileges_sql() to '
            'detect transitive view dependencies on RLS tables, UNLOGGED tables, foreign tables, and '
            'unpinned VOLATILE functions, explicitly documenting the pinned pg_catalog boundary.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-depend.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-depend.html'),
        ],
    ),
    dict(
        url='https://www.postgresql.org/docs/17/catalog-pg-attribute.html',
        other_urls=[],
        kind='article',
        title='PostgreSQL 17 Documentation — 51.7. pg_attribute',
        year=2026,
        aliases=['PostgreSQL 17 pg_attribute', 'attgenerated', 'generated columns'],
        tags=['SQL', '신뢰성'],
        note=(
            'PostgreSQL 17 system catalog documentation for pg_attribute (attgenerated for stored '
            'generated columns). Semantic Crosscheck v0.37.0 inspects attgenerated <> \'\' with zero '
            'extra round trips in doctor._privileges_sql() and grain.evaluate() (preserving grain\'s '
            'five-statement budget), recording generated_columns and surfacing explicit not_proven '
            'disclosures without leaking column names.'
        ),
        cites=[
            (RELEASE, 'postgresql.org/docs/17/catalog-pg-attribute.html'),
            (THIRD_PARTY, 'postgresql.org/docs/17/catalog-pg-attribute.html'),
        ],
    ),
    dict(
        url='https://github.com/mfvanek/pg-index-health',
        other_urls=[],
        kind='project',
        title='mfvanek/pg-index-health — PostgreSQL Index and Schema Health Checks',
        year=2026,
        aliases=['pg-index-health', 'mfvanek/pg-index-health'],
        tags=['SQL', '신뢰성', '검증'],
        note=(
            'Ivan Vakhrushev (Apache-2.0). Open-source Java/SQL diagnostic suite checking PostgreSQL '
            'index and schema health including invalid indexes left behind by failed CONCURRENTLY '
            'builds. Referenced conceptually in Semantic Crosscheck v0.37.0 for invalid/unready index '
            'catalog checks (NOT indisvalid OR NOT indisready) across parent relations and recursive '
            'pg_inherits child partitions in doctor.py and grain.py; no Java/JVM library or external '
            'SQL code is copied or bundled.'
        ),
        cites=[
            (RELEASE, 'github.com/mfvanek/pg-index-health'),
            (THIRD_PARTY, 'github.com/mfvanek/pg-index-health'),
        ],
    ),
    dict(
        url='https://doi.org/10.1109/32.988498',
        other_urls=[],
        kind='paper',
        title='Simplifying and Isolating Failure-Inducing Input',
        year=2002,
        aliases=['Zeller & Hildebrandt (IEEE TSE 2002)', 'Delta Debugging', 'ddmin'],
        tags=['검증', '평가·테스트'],
        note=(
            'Andreas Zeller & Ralf Hildebrandt (IEEE Transactions on Software Engineering, 2002, '
            'doi:10.1109/32.988498). Introduces the ddmin binary-partition delta debugging algorithm '
            'for minimizing failure-inducing inputs. Semantic Crosscheck v0.37.0 implements a bounded, '
            'deterministic DDMIN binary-chunk deletion prelude (chunk_deletion) in reduction.py for '
            'FK-free tables with len(rows) >= 4 ahead of the existing 1-minimal single-row pass, '
            'preserving trial budgets, replay trace validation, and TLP reduction compatibility.'
        ),
        cites=[
            (RELEASE, '10.1109/32.988498'),
            (THIRD_PARTY, '10.1109/32.988498'),
        ],
    ),
    dict(
        url='https://arxiv.org/abs/2601.04689',
        other_urls=[],
        kind='paper',
        title='Extending Delta Debugging Minimization for Spectrum-Based Fault Localization',
        year=2026,
        aliases=['DDMIN-LOC', 'Kapugama (2026)', 'arXiv:2601.04689'],
        tags=['검증', '평가·테스트'],
        note=(
            'Kapugama (2026, arXiv:2601.04689). Examines structured extensions to ddmin chunk-based '
            'minimization for fault isolation. Referenced in Semantic Crosscheck v0.37.0 alongside '
            'Zeller & Hildebrandt (2002) for the pure-stdlib bounded DDMIN binary-chunk deletion '
            'prelude (chunk_deletion) in reduction.py; no external artifact or solver plugin is copied.'
        ),
        cites=[
            (RELEASE, 'arxiv.org/abs/2601.04689'),
            (THIRD_PARTY, 'arxiv.org/abs/2601.04689'),
        ],
    ),
]

CARD_SPECS = [
    dict(
        index=269,
        sourceId='url:https://www.postgresql.org/docs/17/xfunc-volatility.html',
        title='PostgreSQL 17 Documentation — 36.7. Function Volatility Categories',
        kind='article',
        label='VOLATILITY CATEGORIES',
        factualConcept=(
            'PostgreSQL 17 classifies functions as IMMUTABLE, STABLE, or VOLATILE; VOLATILE functions can '
            'observe data changes inside REPEATABLE READ snapshots, which Semantic Crosscheck v0.37.0 '
            'discloses for source views in doctor.py.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite three-chamber optical stability comparator representing function '
            'volatility tiers: in the left chamber rests a solid faceted luminous-lime (#d3fc70) crystal block locked '
            'flat in a calibrated silver vise; in the center chamber sits a translucent frosted-lavender (#c3b0f6) '
            'glass prism suspended gently above a level silver mirror plate; in the right chamber hovers an irregular '
            'warm-amber faceted glass crystal refracting two noticeably offset light beams across a split brushed-silver '
            'optical gauge inside a single clear glass dome; refined tactile machined metal and optical glass materials, '
            'dramatic soft studio rim lighting, shallow depth of field, centered crop-safe composition with generous '
            'dark olive margins, zero text, zero letters, zero digits, zero mathematical symbols, zero icons, zero '
            'logos, zero borders.'
        ),
        refinementPrompts=[
            (
                'Edit this studio product photograph only to remove all tiny digits, numbers, and character-like '
                'markings from the circular brushed-silver optical gauge inside the right glass dome, leaving only '
                'clean unnumbered machined tick lines on the split silver plate. Keep the rest of the three-chamber '
                'brushed-graphite optical stability comparator, the luminous-lime crystal in the left vise, the '
                'frosted-lavender prism in the center chamber, the hovering warm-amber crystal refracting two offset '
                'light beams inside the clear glass dome, the dark olive tabletop (#10130f), lighting, and framing '
                'identical, with zero text, zero letters, zero digits, zero symbols, zero logos, and zero borders '
                'anywhere in the image.'
            ),
        ],
        output='media/cards/card-269-postgres-xfunc-volatility.webp',
        sourceSha256='06cc3da3c57b03d33a469414e6b619cee5fc0a013897770a76dccb63fdece327',
        sourceDimensions=[1264, 848],
        refUrl='https://www.postgresql.org/docs/17/xfunc-volatility.html',
    ),
    dict(
        index=270,
        sourceId='url:https://www.postgresql.org/docs/17/catalog-pg-proc.html',
        title='PostgreSQL 17 Documentation — 51.39. pg_proc',
        kind='article',
        label='PROCEDURE CATALOG STATE',
        factualConcept=(
            'PostgreSQL 17 pg_proc stores provolatile classification for every registered function; '
            'Semantic Crosscheck v0.37.0 joins pg_proc in doctor._privileges_sql() to detect unpinned '
            'VOLATILE functions behind source views.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite cylindrical function catalog turret resting on a chamfered silver '
            'plinth: arranged evenly at 30-degree radial intervals around the dark machined drum are exactly twelve '
            'slim translucent optical glass index blades with zero overlap—eleven seated flush and glowing calmly with '
            'cool luminous-lime (#d3fc70) and frosted-lavender (#c3b0f6) edges, while one single blade at the upper '
            'right is slightly raised in its slot and glows warm-amber along its crisp beveled edge and top V-notch as '
            'a delicate brushed-silver optical pointer arm extending from the center spindle pauses directly over its '
            'notch; ultra-clean scientific laboratory exhibit aesthetic, tactile anodized metal and optical glass '
            'refraction, soft studio key and rim lighting, shallow depth of field, centered crop-safe composition with '
            'generous dark olive margins, zero text, zero letters, zero digits, zero icons, zero logos, zero borders.'
        ),
        refinementPrompts=[
            (
                'Edit this studio product photograph minimally: raise the brushed-silver optical pointer arm\'s spindle '
                'height slightly and lengthen the delicate brushed-silver pointer arm so its fine tip passes cleanly '
                'above the inner edge of the raised warm-amber glass blade and pauses directly over the center of its '
                'top V-notch without touching the glass. Keep the brushed-graphite cylindrical turret, chamfered silver '
                'plinth, all twelve radial translucent optical blades (eleven flush luminous-lime and frosted-lavender '
                'blades plus the single raised warm-amber blade at 2 o\'clock), lighting, dark olive seamless tabletop '
                '(#10130f), and zero text/borders completely unchanged.'
            ),
        ],
        output='media/cards/card-270-postgres-pg-proc.webp',
        sourceSha256='3c807f4ec241a4e95a065daee71538f6e5ff1dda80b243120fdb16438543fa0f',
        sourceDimensions=[1264, 848],
        refUrl='https://www.postgresql.org/docs/17/catalog-pg-proc.html',
    ),
    dict(
        index=271,
        sourceId='url:https://www.postgresql.org/docs/17/catalog-pg-rewrite.html',
        title='PostgreSQL 17 Documentation — 51.45. pg_rewrite',
        kind='article',
        label='VIEW REWRITE RULES',
        factualConcept=(
            'PostgreSQL 17 pg_rewrite records the SELECT rewrite rules (ev_type=\'1\') that define SQL views; '
            'Semantic Crosscheck v0.37.0 starts recursive view-dependency traversal from pg_rewrite in '
            'doctor._privileges_sql().'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite optical query-rewrite bench: a single luminous-lime (#d3fc70) glass '
            'beam block enters a sleek multi-faceted clear glass prism assembly mounted on a machined silver bridge '
            'and emerges cleanly redirected into two aligned translucent frosted-lavender (#c3b0f6) projection rails '
            'below, while an uncoupled secondary dark-graphite side rail sits gated off behind a thin brushed-silver '
            'shutter plate; tactile brushed metal and optical glass refraction, dramatic controlled studio rim '
            'lighting, shallow depth of field, centered crop-safe composition with generous dark olive margins, zero '
            'text, zero letters, zero digits, zero icons, zero logos, zero borders.'
        ),
        output='media/cards/card-271-postgres-pg-rewrite.webp',
        sourceSha256='26cb63a5fb027eb58854a51a8e9560cd1ccc0384141b96a6dbe6689b6517c3b8',
        sourceDimensions=[1264, 848],
        refUrl='https://www.postgresql.org/docs/17/catalog-pg-rewrite.html',
    ),
    dict(
        index=272,
        sourceId='url:https://www.postgresql.org/docs/17/catalog-pg-depend.html',
        title='PostgreSQL 17 Documentation — 51.18. pg_depend',
        kind='article',
        label='CATALOG DEPENDENCY GRAPH',
        factualConcept=(
            'PostgreSQL 17 pg_depend stores normal dependency edges (deptype=\'n\') between catalog objects; '
            'Semantic Crosscheck v0.37.0 follows pg_rewrite -> pg_depend -> pg_inherits recursively to '
            'surface RLS, UNLOGGED, foreign, and VOLATILE-function dependencies behind views.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite stepped dependency trace matrix: an upper translucent '
            'frosted-lavender (#c3b0f6) viewing lens connects via fine machined-silver optical tension rods down to a '
            'middle frosted glass relay block and outward to three distinct lower plinth sockets holding a '
            'luminous-lime (#d3fc70) faceted cube, a matte-graphite hollow cylinder, and a warm-amber beveled glass '
            'prism, making the multi-hop structural lineage visibly traceable in one crisp angle; refined tactile '
            'metal and optical glass materials, dramatic soft studio rim lighting, shallow depth of field, centered '
            'crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, zero icons, '
            'zero logos, zero borders.'
        ),
        output='media/cards/card-272-postgres-pg-depend.webp',
        sourceSha256='c3b8aab752e4ca7d1d8f4853ded77a3905e50304ae363661d3ad7772a3d32b18',
        sourceDimensions=[1264, 848],
        refUrl='https://www.postgresql.org/docs/17/catalog-pg-depend.html',
    ),
    dict(
        index=273,
        sourceId='url:https://www.postgresql.org/docs/17/catalog-pg-attribute.html',
        title='PostgreSQL 17 Documentation — 51.7. pg_attribute',
        kind='article',
        label='GENERATED COLUMN ATTRIBUTES',
        factualConcept=(
            'PostgreSQL 17 pg_attribute marks stored generated columns via attgenerated <> \'\'; Semantic '
            'Crosscheck v0.37.0 counts generated_columns in doctor.py and grain.py with zero extra SQL '
            'round trips and discloses them in not_proven.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f), '
            'framed with generous dark olive margins on all sides for a centered crop-safe composition, showing a '
            'precision brushed-graphite column-attribute rack holding six vertical machined-silver and frosted-glass '
            'column pillars standing in a neat row: the first five pillars on the left each hold a solid '
            'matte-graphite base and luminous-lime (#d3fc70) stored crystal core inside a machined-silver and '
            'frosted-glass housing; the sixth pillar position on the right has a machined-silver base and open frame '
            'formed by two thin diagonal frosted-lavender (#c3b0f6) optical light-guide rods angling upward from the '
            'two neighboring pillars (pillars four and five) and converging into a faceted luminous fused amber-lime '
            'crystal crown suspended at the top of the sixth pillar, representing a generated column; refined tactile '
            'machined metal and optical glass refraction, soft studio key and rim lighting, shallow depth of field, '
            'zero text, zero letters, zero digits, zero icons, zero logos, zero borders.'
        ),
        refinementPrompts=[
            (
                'Edit this studio product photograph while preserving the exact near-black olive seamless tabletop '
                '(#10130f), generous dark olive margins, lighting, brushed-graphite rack, and the first five vertical '
                'machined-silver and frosted-glass pillars with matte-graphite bases and luminous-lime (#d3fc70) '
                'crystal cores. Modify only the sixth pillar on the right: remove the four lavender tubes inside the '
                'sixth pillar and instead give the sixth pillar a sleek machined-silver and clear frosted-glass open '
                'support column holding the faceted luminous fused amber-lime crystal crown at the top, with exactly '
                'two thin diagonal frosted-lavender (#c3b0f6) optical light-guide rods extending diagonally upward '
                'from the fourth and fifth neighboring pillars and converging cleanly into the luminous amber-lime '
                'crystal crown at the top of the sixth pillar to represent a generated column. Keep zero text, zero '
                'letters, zero digits, zero icons, zero logos, zero borders.'
            ),
        ],
        output='media/cards/card-273-postgres-pg-attribute.webp',
        sourceSha256='70e65dd8d0a5bad0c2416e8dd78c4cfadd082c634f992808fe18a758a7998570',
        sourceDimensions=[1264, 848],
        refUrl='https://www.postgresql.org/docs/17/catalog-pg-attribute.html',
    ),
    dict(
        index=274,
        sourceId='github:mfvanek/pg-index-health',
        title='mfvanek/pg-index-health — PostgreSQL Index and Schema Health Checks',
        kind='project',
        label='INVALID INDEX HYGIENE',
        factualConcept=(
            'mfvanek/pg-index-health catalogs PostgreSQL index hygiene diagnostics including invalid indexes '
            'from failed CONCURRENTLY builds; Semantic Crosscheck v0.37.0 adapts parent and child-partition '
            'invalid/unready index counting in pure SQL and Python.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite index-health diagnostic tray containing five parallel machined-silver '
            'optical lookup rails arranged side by side: the first four parallel rails (rails 1, 2, 3, and 4) each '
            'hold neatly aligned luminous-lime (#d3fc70) glass key teeth seated smoothly in their grooves, while the '
            'fifth parallel rail beside them displays a slightly fractured frosted-lavender (#c3b0f6) and warm-amber '
            'unfinished crystal bar sitting unseated above its track, accompanied by a fine silver optical caliper arm '
            'positioned right next to the fifth rail; ultra-clean scientific instrument exhibit aesthetic, tactile '
            'brushed metal and optical glass refraction, dramatic controlled studio rim lighting, shallow depth of '
            'field, centered crop-safe composition with generous dark olive margins, zero text, zero letters, zero '
            'digits, zero icons, zero logos, zero borders.'
        ),
        refinementPrompts=[
            (
                'Edit this photograph while keeping the exact same brushed-graphite tray, five parallel machined-silver '
                'rails, lighting, angle, and dark olive (#10130f) background: change the three brownish-amber cubes on '
                'the fourth rail into matching luminous-lime (#d3fc70) optical glass key teeth so all four first rails '
                'hold uniform aligned luminous-lime glass key teeth seated smoothly in their grooves (extending cleanly '
                'down the fourth rail like the others); and adjust the slightly fractured frosted-lavender (#c3b0f6) '
                'and warm-amber unfinished crystal bar on the fifth rail so it rests unseated and slightly elevated on '
                'the upper rims above its track beside the fine silver optical caliper arm; preserve zero text, zero '
                'letters, zero digits, zero logos, and zero borders.'
            ),
        ],
        output='media/cards/card-274-pg-index-health.webp',
        sourceSha256='db8501701dbc6639574024089a8d67b54ad1498151885c1736f6a19c89ee9537',
        sourceDimensions=[1264, 848],
        refUrl='https://github.com/mfvanek/pg-index-health',
    ),
    dict(
        index=275,
        sourceId='doi:10.1109/32.988498',
        title='Simplifying and Isolating Failure-Inducing Input',
        kind='paper',
        label='DELTA DEBUGGING CHUNKS',
        factualConcept=(
            'Zeller & Hildebrandt (2002) formulate ddmin binary-partition input minimization; Semantic '
            'Crosscheck v0.37.0 adds a bounded deterministic DDMIN chunk_deletion prelude for FK-free tables '
            'in reduction.py ahead of 1-minimal single-row simplification.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite binary-halving reduction jig: a long horizontal sequence of '
            'matte-graphite and frosted-lavender (#c3b0f6) modular glass blocks rests along a calibrated silver track '
            'divided cleanly at midpoints by stepped brushed-silver guillotine calipers, with larger discarded '
            'dark-graphite halves resting neatly off to the rear tray while just two crisp luminous-lime (#d3fc70) '
            'minimal witness blocks sit side-by-side centered together directly underneath a focused silver optical '
            'bridge with twin precision lenses in the foreground; tactile machined metal and optical glass materials, '
            'dramatic soft studio rim lighting, shallow depth of field, centered crop-safe composition with generous '
            'dark olive margins, zero text, zero letters, zero digits, zero icons, zero logos, zero borders, no '
            'numbers on the calibrated track.'
        ),
        refinementPrompts=[
            (
                'Edit this studio product photograph while preserving the exact near-black olive tabletop (#10130f), '
                'crop-safe centered composition with generous dark margins, rear tray of dark-graphite blocks, and the '
                'calibrated silver track with matte-graphite and frosted-lavender blocks divided by stepped '
                'brushed-silver guillotine calipers. Move the second luminous-lime block from the right end of the '
                'track so that both crisp luminous-lime (#d3fc70) minimal cube witness blocks sit side-by-side '
                'together directly centered underneath the silver optical bridge lens assembly in the foreground '
                '(widening the optical bridge slightly so its lens/frame cleanly spans over both lime witness blocks '
                'together). Keep the right end of the track clean empty brushed silver after the final caliper. Keep '
                'zero text, zero letters, zero digits, zero icons, zero logos, zero borders.'
            ),
        ],
        output='media/cards/card-275-zeller-delta-debugging.webp',
        sourceSha256='fbddec806e0d808cdab08e95aaed06e83c86222dc87afe3525d300ff254e1ac4',
        sourceDimensions=[1264, 848],
        refUrl='https://doi.org/10.1109/32.988498',
    ),
    dict(
        index=276,
        sourceId='arxiv:2601.04689',
        title='Extending Delta Debugging Minimization for Spectrum-Based Fault Localization',
        kind='paper',
        label='SPECTRUM DELTA REDUCTION',
        factualConcept=(
            'Kapugama (2026) studies structured extensions to ddmin chunk minimization for fault '
            'localization (DDMIN-LOC); Semantic Crosscheck v0.37.0 cites it alongside Zeller & Hildebrandt '
            '(2002) for bounded DDMIN chunk_deletion witness reduction in reduction.py.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f), '
            'showing the entire self-contained precision brushed-graphite spectrum-weighted reduction prism rail '
            'cleanly centered inside the frame with generous dark olive margins on all four sides: alternating '
            'clusters of dark-slate and translucent frosted-lavender (#c3b0f6) glass tiles sit in stepped, tiered '
            'binary-split trays descending symmetrically toward the foreground, where a delicate graduated band of '
            'luminous-lime (#d3fc70) to warm-amber internal edge illumination highlights two decisive fault-inducing '
            'crystal tiles isolated at the apex of a slender machined-silver calibration cradle; ultra-clean '
            'scientific laboratory exhibit aesthetic, tactile brushed metal and glass refraction, soft studio key and '
            'rim lighting, shallow depth of field, zero text, zero letters, zero digits, zero icons, zero logos, zero '
            'borders.'
        ),
        output='media/cards/card-276-ddmin-loc.webp',
        sourceSha256='1fa9ac440fecc80fc180183546157d55b947532750c106e42b879f59b20569dc',
        sourceDimensions=[1264, 848],
        refUrl='https://arxiv.org/abs/2601.04689',
    ),
]


def _find_single_line(read_lines, file, commit, needle, label):
    lines = read_lines(file)
    matches = [(i, line) for i, line in enumerate(lines, 1) if needle in line]
    if len(matches) != 1:
        raise ValueError(f'Expected one citation of {label} in {file}, found {len(matches)}')
    number, line = matches[0]
    excerpt = excerpt_of(line)
    if sum(excerpt_of(other) == excerpt for other in lines) != 1:
        raise ValueError(f'Ambiguous evidence excerpt for {label} in {file}')
    return dict(file=file, line=number, url=f'{PREFIX}{commit}/{file}#L{number}', excerpt=excerpt)


def prepare(registry, artwork, commit, read_lines, root=ROOT):
    sxc_snap = registry['snapshots'][PLUGIN]
    av_snap = registry['snapshots']['agentic-vault']
    npd_snap = registry['snapshots']['node-pg-defense']
    if av_snap['version'] != AV_VERSION:
        raise ValueError(f'Expected agentic-vault {AV_VERSION}, got {av_snap["version"]}')
    if npd_snap['version'] != NPD_VERSION:
        raise ValueError(f'Expected node-pg-defense {NPD_VERSION}, got {npd_snap["version"]}')
    if (sxc_snap['version'], sxc_snap['commit']) != (PRIOR_VERSION, PRIOR_COMMIT):
        raise ValueError(f'Expected published {PRIOR_VERSION} baseline ({PRIOR_COMMIT})')

    remapped, prior_rows, moved = repin(registry, read_lines, commit)
    for asset in artwork['assets']:
        for field in ('evidenceUrls', 'currentEvidenceUrls'):
            asset[field] = [remapped[url] if url.startswith(PREFIX) else url for url in asset[field]]

    by_id = {s['id']: s for s in registry['sources']}
    asset_by_id = {a['sourceId']: a for a in artwork['assets']}

    updated_existing = {}
    for spec in EXISTING_UPDATES:
        sid = spec['id']
        if sid not in by_id:
            raise ValueError(f'Expected existing source {sid}')
        source = by_id[sid]
        sxc_use = next((u for u in source['uses'] if u['plugin'] == PLUGIN), None)
        if sxc_use is None:
            raise ValueError(f'Expected existing {PLUGIN} use on {sid}')
        extra = [
            _find_single_line(read_lines, file, commit, needle, sid)
            for file, needle in spec['cites']
        ]
        existing_urls = {row['url'] for row in sxc_use['evidence']}
        for row in extra:
            if row['url'] in existing_urls:
                raise ValueError(f'Duplicate citation URL for {sid}: {row["url"]}')
        sxc_use['evidence'].extend(extra)
        source['note'] = spec['note']
        if sid in asset_by_id:
            all_urls = [row['url'] for u in source['uses'] for row in u['evidence']]
            asset_by_id[sid]['evidenceUrls'] = list(all_urls)
            asset_by_id[sid]['currentEvidenceUrls'] = list(all_urls)
        updated_existing[sid] = len(extra)

    shared_added = {}
    for spec in SHARED_UPDATES:
        sid = spec['id']
        if sid not in by_id:
            raise ValueError(f'Expected existing source {sid} for shared cross-plugin update')
        source = by_id[sid]
        if any(use['plugin'] == PLUGIN for use in source['uses']):
            raise ValueError(f'{sid} already has a {PLUGIN} use')
        evidence = [
            _find_single_line(read_lines, file, commit, needle, sid)
            for file, needle in spec['cites']
        ]
        source['uses'].append(dict(plugin=PLUGIN, role='reference', evidence=evidence))
        if spec.get('new_url'):
            source['url'] = spec['new_url']
        for extra_key in spec.get('extra_keys', []):
            if extra_key not in source['keys']:
                source['keys'].append(extra_key)
        note_append = spec['note_append']
        if note_append not in source['note']:
            sep = '' if not source['note'] or source['note'].endswith(' ') else ' '
            source['note'] = source['note'] + sep + note_append
        if sid in asset_by_id:
            all_urls = [row['url'] for u in source['uses'] for row in u['evidence']]
            asset_by_id[sid]['evidenceUrls'] = list(all_urls)
            asset_by_id[sid]['currentEvidenceUrls'] = list(all_urls)
        shared_added[sid] = len(evidence)

    existing_ids = {s['id'] for s in registry['sources']}
    existing_keys = {k for s in registry['sources'] for k in s.get('keys', [s['id']])}
    added = {}
    evidence_by_id = {}
    for spec in NEW_SOURCES:
        keys = []
        for address in [spec['url'], *spec['other_urls']]:
            ident = canonical_key(address)
            if ident is None:
                raise ValueError(f'No canonical key for {address}')
            if ident['key'] not in keys:
                keys.append(ident['key'])
        sid = keys[0]
        if sid in existing_ids or any(k in existing_keys for k in keys):
            raise ValueError(f'Source or key already exists: {keys}')
        evidence = [
            _find_single_line(read_lines, file, commit, needle, sid)
            for file, needle in spec['cites']
        ]
        evidence_by_id[sid] = [row['url'] for row in evidence]
        registry['sources'].append(dict(
            id=sid,
            kind=spec['kind'],
            title=spec['title'],
            url=spec['url'],
            year=spec['year'],
            keys=keys,
            aliases=spec['aliases'],
            tags=spec['tags'],
            note=spec['note'],
            uses=[dict(plugin=PLUGIN, role='reference', evidence=evidence)],
        ))
        existing_ids.add(sid)
        existing_keys.update(keys)
        added[sid] = len(evidence)

    card_digests = {}
    for spec in CARD_SPECS:
        card_path = root / spec['output']
        if not card_path.is_file():
            raise ValueError(f'Missing rendered card image: {card_path}')
        card_bytes = card_path.read_bytes()
        card_sha = hashlib.sha256(card_bytes).hexdigest()
        ev_urls = list(evidence_by_id[spec['sourceId']])
        entry = dict(
            index=spec['index'],
            sourceId=spec['sourceId'],
            title=spec['title'],
            kind=spec['kind'],
            label=spec['label'],
            factualConcept=spec['factualConcept'],
            prompt=spec['prompt'],
            output=spec['output'],
            sha256=card_sha,
            bytes=len(card_bytes),
            dimensions=[960, 640],
            evidenceUrls=list(ev_urls),
            generationEvidenceUrls=list(ev_urls),
            currentEvidenceUrls=list(ev_urls),
            delivery=dict(
                sourceSha256=spec['sourceSha256'],
                sourceDimensions=list(spec['sourceDimensions']),
                operation='Full-frame Lanczos resize and WebP encoding only; no crop, compositing or semantic edit',
                tool='Pillow 12.3.0 (Python WebP encoder)',
                quality=90,
                compressionLevel=6,
                commandTemplate=(
                    "python -c \"from PIL import Image; Image.open('INPUT').convert('RGB')"
                    ".resize((960, 640), Image.Resampling.LANCZOS)"
                    ".save('OUTPUT.webp', format='WEBP', quality=90, method=6)\""
                ),
            ),
            generationReferenceUrls=[spec['refUrl']],
        )
        if spec.get('refinementPrompts'):
            entry['refinementPrompts'] = list(spec['refinementPrompts'])
        artwork['assets'].append(entry)
        card_digests[spec['sourceId']] = dict(sha256=card_sha, bytes=len(card_bytes))
    artwork['count'] = len(artwork['assets'])

    sxc_snap.update(version=TAG, commit=commit, url=f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}')
    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    validate_catalog({**registry, 'sources': merge_sources(registry['sources'])})
    return dict(
        rebound=prior_rows,
        moved=moved,
        updated_existing=updated_existing,
        shared_added=shared_added,
        added=added,
        cards=card_digests,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plugin', type=Path, help='Checkout containing the cited public commit')
    parser.add_argument('commit', help='Full plugin commit ID')
    parser.add_argument('--public-ref', default=f'refs/tags/{TAG}',
                        help='Ref already confirmed on the public plugin repository (defaults to the release tag)')
    parser.add_argument('--apply', action='store_true', help='Write the catalog from the verified public ref')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.commit):
        parser.error('Expected a full Git commit ID')

    def git(*parts):
        return subprocess.check_output(['git', '-C', str(args.plugin), *parts]).decode('utf-8')

    if args.apply and git('rev-parse', '--verify', '--end-of-options', f'{args.public_ref}^{{commit}}').strip() != args.commit:
        parser.error('The verified public ref must resolve to the supplied commit')

    @cache
    def read_lines(file):
        return git('show', f'{args.commit}:{file}').split('\n')

    registry = json.loads((ROOT / REGISTRY).read_text(encoding='utf-8'))
    artwork = json.loads((ROOT / ARTWORK).read_text(encoding='utf-8'))
    report = prepare(registry, artwork, args.commit, read_lines, ROOT)
    encoded = encode(registry)
    catalog_json, catalog_csv = built_catalog(encoded)
    if args.apply:
        write_files({ROOT / REGISTRY: encoded, ROOT / ARTWORK: encode(artwork),
                     ROOT / CATALOG_JSON: catalog_json, ROOT / CATALOG_CSV: catalog_csv})
    print(json.dumps(dict(**report, applied=args.apply), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
