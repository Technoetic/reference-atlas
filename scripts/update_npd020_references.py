"""Add the 21 node-pg-defense v0.2.0+docs references (4 shared + 17 new) and register card-252..268 artwork."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from build_catalog import build, merge_sources
from reference_identity import canonical_key, validate_catalog

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'node-pg-defense'
PLUGIN_NAME = 'Node PG Defense'
VERSION = 'v0.2.0+docs'
REF_FILE = 'docs/references.md'

SHARED_URLS = [
    'https://www.postgresql.org/docs/17/rules-privileges.html',
    'https://www.postgresql.org/docs/17/ddl-rowsecurity.html',
    'https://www.postgresql.org/docs/17/sql-createview.html',
    'https://www.postgresql.org/support/versioning/',
]

NEW_SOURCES = [
    dict(
        index=252,
        id='doi:10.1145/1111037.1111070',
        kind='paper',
        title='The Essence of Command Injection Attacks in Web Applications',
        url='https://doi.org/10.1145/1111037.1111070',
        year=2006,
        keys=['doi:10.1145/1111037.1111070'],
        aliases=['Su and Wassermann 2006', 'POPL 2006 Command Injection'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'Zhendong Su and Gary Wassermann (POPL 2006). Formalizes SQL and command injection as untrusted '
            'input altering syntactic grammar structure. Referenced by Node PG Defense (controls 01, 04-06) as '
            'the theoretical basis for separating fixed SQL query text from bound parameter values.'
        ),
        label='SYNTACTIC VALUE ISOLATION',
        slug='su-wassermann-sqli',
        factualConcept=(
            'Su and Wassermann (POPL 2006) formalize command and SQL injection as untrusted input altering '
            'syntactic grammar structure; Node PG Defense grounds controls 01 and 04-06 in isolating fixed SQL '
            'query text from bound parameter arrays.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision machined brushed-graphite and crystal syntax bridge: an unbroken clear optical-glass '
            'structural arch spans the upper rail cleanly untouched, while three smooth warm-amber (#ffbf83) glass '
            'parameter capsules travel inside sealed recessed titanium slots underneath so data capsules stay '
            'physically isolated from the upper crystal grammar rail; museum-grade architectural still-life '
            'photography, crisp glass refraction, dramatic soft studio rim lighting, shallow depth of field, '
            'centered crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, '
            'zero logos, zero icons, zero borders.'
        ),
        sourceSha256='c7cd00e2b8ecd119f9d4330c5f1fb4415447b538493dfca859d69371c08771d6',
    ),
    dict(
        index=253,
        id='arxiv:2604.01131',
        kind='paper',
        title='Obfuscating Code Vulnerabilities against Static Analysis in JavaScript Code',
        url='https://arxiv.org/abs/2604.01131',
        year=2026,
        keys=['arxiv:2604.01131'],
        aliases=['arXiv:2604.01131', 'JavaScript Static Analysis Obfuscation'],
        tags=['보안·안전', '평가·테스트', '신뢰성'],
        note=(
            'Examines how obfuscation and indirect constructs evade standalone JavaScript static analysis. '
            'Referenced by Node PG Defense (controls 23-26) to justify pairing static linting with custom '
            'dataflow rules, fixed-SQL mock regression tests, and real PostgreSQL integration checks.'
        ),
        label='STATIC BLIND SPOT AUDIT',
        slug='js-obfuscation-static-analysis',
        factualConcept=(
            'arXiv:2604.01131 shows how obfuscated JavaScript constructs evade standalone static analysis; '
            'Node PG Defense controls 23-26 pair static lint rules with service-specific taint modeling, '
            'fixed-SQL regression tests, and ephemeral PostgreSQL integration checks.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision optical prism inspection rig: a shallow pale-silver surface light glides smoothly '
            'across a frosted smoked-glass prism shell, while a deeper angled warm-amber (#ffbf83) and soft-lavender '
            '(#c3b0f6) cross-beam illuminates a hidden tangled dark-steel fault coil suspended inside the translucent '
            'prism core; refined scientific miniature still-life photography, realistic refraction and dark matte '
            'metal texture, dramatic soft studio rim lighting, shallow depth of field, centered crop-safe composition '
            'with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='bb7a3493b4752b52d6fd6b0b7048fefb4158be3618138178fe7d8e2199d9aa57',
    ),
    dict(
        index=254,
        id='github:owasp/asvs',
        kind='project',
        title='OWASP Application Security Verification Standard (ASVS)',
        url='https://github.com/OWASP/ASVS',
        year=None,
        keys=['github:owasp/asvs'],
        aliases=['OWASP ASVS', 'Application Security Verification Standard'],
        tags=['보안·안전', '검증', '신뢰성'],
        note=(
            'Public OWASP verification standard repository covering input validation, parameterized database queries, '
            'access control, error handling, and security logging. Referenced across Node PG Defense controls 01-30 '
            'for verifiable application-level security review criteria.'
        ),
        label='VERIFICATION STANDARD TIERS',
        slug='owasp-asvs',
        factualConcept=(
            'OWASP ASVS defines tiered application security verification requirements across input validation, '
            'parameterized queries, access control, and logging; Node PG Defense maps controls 01-30 to concrete '
            'Node.js and PostgreSQL review and verification steps.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing three concentric stepped architectural verification rings crafted from matte brushed graphite '
            'and optical glass rising like a precision terraced calibration monument, each ascending tier edged with '
            'a slender luminous warm-amber (#ffbf83) and subtle lime (#d3fc70) glass verification band marking '
            'progressive assurance depth; museum-grade studio product photography, tactile machined metal and crisp '
            'glass edges, soft cinematic rim lighting, shallow depth of field, centered crop-safe composition with '
            'generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='6e551ec3850d1d2edda7b7af06eb60a56e900b5b86d77ce5e6a2f34f1ceb34c8',
    ),
    dict(
        index=255,
        id='github:brianc/node-postgres',
        kind='project',
        title='node-postgres (pg)',
        url='https://github.com/brianc/node-postgres',
        year=None,
        keys=['github:brianc/node-postgres'],
        aliases=['node-postgres', 'pg'],
        tags=['SQL', '보안·안전'],
        note=(
            'Official Node.js PostgreSQL driver (pg.Pool and pg.Client) supporting positional $1 parameterized '
            'queries and dedicated transaction clients. Referenced by Node PG Defense (controls 01, 02, 15) as '
            'the primary target API for bounded automatic query parameterization and transaction-local settings.'
        ),
        label='PARAMETERIZED WIRE CLIENT',
        slug='node-postgres',
        factualConcept=(
            'brianc/node-postgres provides pg.Pool and pg.Client positional $1 query binding and dedicated '
            'transaction clients; Node PG Defense controls 01, 02, and 15 target verified pg calls for bounded '
            'parameterization and transaction-scoped session cleanup.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision twin-conduit brushed-aluminum and optical-glass bridge connecting a matte-graphite '
            'manifold block to a tall translucent cylindrical crystal vessel: the upper clear glass tube holds a '
            'rigid unbroken optical query rod, while a distinct lower conduit carries evenly spaced warm-amber '
            '(#ffbf83) glass parameter spheres in strict alignment; refined industrial design miniature still-life, '
            'crisp glass refraction, dramatic soft studio rim lighting, shallow depth of field, centered crop-safe '
            'composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='96923fefff11306d31071ea1bf0f1ab2aca2d30d82ff345456085bc1e59fa88d',
    ),
    dict(
        index=256,
        id='github:pgbouncer/pgbouncer',
        kind='project',
        title='PgBouncer',
        url='https://github.com/pgbouncer/pgbouncer',
        year=None,
        keys=['github:pgbouncer/pgbouncer'],
        aliases=['PgBouncer', 'pgbouncer'],
        tags=['SQL', '신뢰성'],
        note=(
            'Lightweight PostgreSQL connection pooler whose transaction pooling mode interacts with prepared '
            'statements (max_prepared_statements) and session-scoped state. Referenced by Node PG Defense '
            '(control 03) for verifying pooler mode and driver compatibility.'
        ),
        label='TRANSACTION POOL RELAY',
        slug='pgbouncer',
        factualConcept=(
            'PgBouncer transaction pooling multiplexes client sessions across backend PostgreSQL connections, '
            'governing prepared-statement compatibility (max_prepared_statements) and session-state isolation; '
            'Node PG Defense control 03 requires verifying pooler mode and driver settings against a real pooler.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision mechanical rotary pooling valve crafted from dark anodized graphite, satin steel, '
            'and optical glass: nine slender incoming glass fibers converge gracefully into a central circular '
            'warm-amber (#ffbf83) rotary shutter ring that routes pulses cleanly into three wider backend crystal '
            'conduits with crisp resettable gate blades; museum-grade engineering still-life photography, realistic '
            'metallic sheen and glass refraction, soft studio rim lighting, shallow depth of field, centered '
            'crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='f344ceba7a175ce1ab3e8a6ed55422e9f35c5c347f7184605fbbfae5154c6a14',
    ),
    dict(
        index=257,
        id='github:ts-safeql/safeql',
        kind='project',
        title='SafeQL',
        url='https://github.com/ts-safeql/safeql',
        year=None,
        keys=['github:ts-safeql/safeql'],
        aliases=['SafeQL', 'ts-safeql'],
        tags=['SQL·데이터 검증', '평가·테스트'],
        note=(
            'Open-source tool that validates raw SQL queries and generates TypeScript types against a live '
            'PostgreSQL schema during linting and CI. Referenced by Node PG Defense (control 22) for checking '
            'application SQL against migrated database schemas before deployment.'
        ),
        label='SCHEMA-CHECKED SQL TYPES',
        slug='ts-safeql',
        factualConcept=(
            'ts-safeql/safeql validates raw SQL queries and column types against an actual PostgreSQL schema; '
            'Node PG Defense control 22 uses schema-backed query type checking in CI alongside an ephemeral '
            'migrated PostgreSQL instance.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision machined graphite vernier template gauge: three smooth warm-amber (#ffbf83) optical '
            'glass column blocks lock seamlessly into exact milled notches on a slim luminous-lime (#d3fc70) '
            'reference schema comb, while one mismatched oversized smoked-glass block is stopped cleanly at the '
            'brushed-steel inspection threshold; refined studio product still-life photography, crisp glass '
            'refraction, dramatic soft rim lighting, shallow depth of field, centered crop-safe composition with '
            'generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='28c1764f2954ef6c28b2307f0820c5589e0627527ef3781268534fc681f6f721',
    ),
    dict(
        index=258,
        id='github:pgaudit/pgaudit',
        kind='project',
        title='pgAudit — PostgreSQL Audit Extension',
        url='https://github.com/pgaudit/pgaudit',
        year=None,
        keys=['github:pgaudit/pgaudit'],
        aliases=['pgAudit', 'pgaudit'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'Official PostgreSQL session and object audit logging extension. Referenced by Node PG Defense '
            '(control 28) for establishing auditable database operation scope, retention, and sensitive-value '
            'exclusion policies.'
        ),
        label='SESSION AUDIT LEDGER',
        slug='pgaudit',
        factualConcept=(
            'pgaudit/pgaudit provides detailed session and object audit logging for PostgreSQL; Node PG Defense '
            'control 28 checks audit collection scope, log retention, access controls, and exclusion of sensitive '
            'bound data.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing an architectural miniature optical audit tape instrument crafted from matte charcoal anodized '
            'aluminum: a smooth continuous ribbon of smoked optical glass glides beneath a warm-amber (#ffbf83) '
            'precision crystal stylus lens that etches delicate luminous hairline grooves onto an immaculate sealed '
            'glass archive spool; museum-grade studio still-life photography, crisp optical glass and brushed steel '
            'detail, dramatic soft rim lighting, shallow depth of field, centered crop-safe composition with '
            'generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='9288de8876b9fcf405dea4fdef969dd21deff8e318033508fedaf24404eb7079',
    ),
    dict(
        index=259,
        id='url:https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html',
        kind='article',
        title='OWASP SQL Injection Prevention Cheat Sheet',
        url='https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html',
        year=None,
        keys=['url:https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html'],
        aliases=['OWASP SQL Injection Prevention Cheat Sheet', 'OWASP SQLi Cheat Sheet'],
        tags=['SQL', '보안·안전'],
        note=(
            'OWASP defense-in-depth guide covering parameterized queries, allowlist validation for dynamic SQL '
            'identifiers, safe LIKE escaping, and least-privilege database roles. Referenced across Node PG Defense '
            'controls 01-16.'
        ),
        label='DEFENSE-IN-DEPTH LAYERS',
        slug='owasp-sqli-cheatsheet',
        factualConcept=(
            'The OWASP SQL Injection Prevention Cheat Sheet specifies defense-in-depth controls including '
            'parameterized queries, allowlists for dynamic identifiers, safe pattern escaping, and least privilege; '
            'Node PG Defense maps these principles across controls 01-16.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing four parallel vertical optical-glass defense baffle plates standing in precision machined '
            'graphite rails, each glass shield rimmed with a fine warm-amber (#ffbf83) edge bevel and brushed-silver '
            'alignment pins as a single calibrated luminous beam passes cleanly straight through the aligned central '
            'apertures while stray amber light reflections are stopped at the outer plates; minimalist architectural '
            'still-life photography, crisp refraction, soft studio rim lighting, shallow depth of field, centered '
            'crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='5d1206338d0d4771eae3cb7df9b2515290d8cf611c3a9639ab6e4f088cf56240',
    ),
    dict(
        index=260,
        id='url:https://www.postgresql.org/docs/17/protocol-flow.html',
        kind='article',
        title='PostgreSQL 17 Documentation — 53.2. Message Flow (Extended Query Protocol)',
        url='https://www.postgresql.org/docs/17/protocol-flow.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/protocol-flow.html'],
        aliases=['PostgreSQL 17 Message Flow', 'PostgreSQL Extended Query Protocol'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 wire-protocol reference detailing the Extended Query cycle (Parse, Bind, Execute) that '
            'transmits SQL templates and parameter values in separate protocol messages. Referenced by Node PG '
            'Defense (controls 01-02).'
        ),
        label='EXTENDED QUERY PROTOCOL',
        slug='postgres-protocol-flow',
        factualConcept=(
            'PostgreSQL 17 section 53.2 documents the Extended Query wire protocol separating Parse, Bind, and '
            'Execute phases; Node PG Defense controls 01-02 rely on server-side parameter binding rather than '
            'client-side string interpolation.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing three sequential crystal optical chambers mounted along a slender brushed-graphite optical '
            'bench—a clear faceted triangular parsing prism, a warm-amber (#ffbf83) cylindrical binding coupler '
            'chamber, and a luminous-lime (#d3fc70) plano-convex execution lens—separated by crisp satin-steel '
            'framing bulkheads illustrating three distinct wire-protocol stages; museum-grade scientific still-life '
            'photography, crisp glass refraction, soft studio rim lighting, shallow depth of field, centered '
            'crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='ce4703cb23b715601f9723923f49ddf41f2bf444bc1465b06872aca4557fddae',
    ),
    dict(
        index=261,
        id='url:https://www.postgresql.org/docs/17/plpgsql-statements.html',
        kind='article',
        title='PostgreSQL 17 Documentation — 41.5. Basic Statements (Executing Dynamic Commands)',
        url='https://www.postgresql.org/docs/17/plpgsql-statements.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/plpgsql-statements.html'],
        aliases=['PostgreSQL 17 PL/pgSQL Basic Statements', 'EXECUTE USING format %I'],
        tags=['SQL', '보안·안전'],
        note=(
            'PostgreSQL 17 PL/pgSQL reference specifying safe dynamic SQL construction with format(%I) for '
            'allowlisted identifiers and EXECUTE ... USING for parameter values. Referenced by Node PG Defense '
            '(control 16).'
        ),
        label='DYNAMIC FORMAT BINDING',
        slug='postgres-plpgsql-dynamic',
        factualConcept=(
            'PostgreSQL 17 section 41.5 specifies constructing dynamic PL/pgSQL statements safely with format(%I) '
            'for identifiers and EXECUTE ... USING for values; Node PG Defense control 16 checks stored functions '
            'for safe dynamic SQL composition.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision machined brushed-graphite modular assembly rail: two crisp faceted clear-crystal '
            'identifier blocks sit firmly locked inside beveled titanium sockets on top, while a smooth warm-amber '
            '(#ffbf83) optical glass value capsule glides cleanly underneath along a physically isolated brushed-steel '
            'carriage track; museum-grade architectural still-life photography, realistic glass refraction, dramatic '
            'soft studio rim lighting, shallow depth of field, centered crop-safe composition with generous dark olive '
            'margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='57ac05112d16c246fda343738c43e25f0c12e80ec6d7f8a56f5a0fd0a3ac811d',
    ),
    dict(
        index=262,
        id='url:https://www.postgresql.org/docs/17/sql-createfunction.html',
        kind='article',
        title='PostgreSQL 17 Documentation — CREATE FUNCTION (SECURITY DEFINER)',
        url='https://www.postgresql.org/docs/17/sql-createfunction.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/sql-createfunction.html'],
        aliases=['PostgreSQL 17 CREATE FUNCTION', 'SECURITY DEFINER search_path'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 SQL reference documenting how to write SECURITY DEFINER functions safely by pinning '
            'SET search_path to trusted schemas (with pg_temp last) and revoking PUBLIC EXECUTE privileges. '
            'Referenced by Node PG Defense (control 16).'
        ),
        label='DEFINER SEARCH PATH LOCK',
        slug='postgres-create-function',
        factualConcept=(
            'PostgreSQL 17 CREATE FUNCTION documentation explains hardening SECURITY DEFINER functions by pinning '
            'SET search_path with pg_temp last and revoking PUBLIC EXECUTE within the creating transaction; '
            'Node PG Defense control 16 enforces this review checklist.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision cylindrical dark-graphite vault chamber: a luminous warm-amber (#ffbf83) optical '
            'glass core is encircled by two locked concentric satin-titanium alignment collars and a closed outer '
            'brushed-steel mechanical iris aperture sealing off stray exterior paths; refined engineering miniature '
            'still-life photography, crisp metal and translucent glass detail, dramatic soft studio rim lighting, '
            'shallow depth of field, centered crop-safe composition with generous dark olive margins, zero text, '
            'zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='82f995f71246a9498be76e76e905f3e8184d93b9214f6a8942378b9b06fa507b',
    ),
    dict(
        index=263,
        id='url:https://www.postgresql.org/support/security/CVE-2024-4317',
        kind='article',
        title='PostgreSQL Security Information — CVE-2024-4317 (pg_stats_ext / pg_stats_ext_exprs)',
        url='https://www.postgresql.org/support/security/CVE-2024-4317/',
        year=2024,
        keys=['url:https://www.postgresql.org/support/security/CVE-2024-4317'],
        aliases=['CVE-2024-4317', 'PostgreSQL CVE-2024-4317'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL security advisory illustrating an authorization bug where installing minor binaries alone '
            'is insufficient: administrators must also run post-upgrade remediation SQL across all existing '
            'databases including template0 and template1. Referenced by Node PG Defense (control 30).'
        ),
        label='POST-UPGRADE SQL REMEDIATION',
        slug='postgres-cve-2024-4317',
        factualConcept=(
            'PostgreSQL CVE-2024-4317 requires running post-upgrade SQL remediation across all databases plus '
            'template0 and template1 after installing patched binaries; Node PG Defense control 30 requires '
            'verifying both binary versions and post-patch SQL remediation.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision brushed-graphite specimen plinth holding two frosted crystal catalog trays beside a '
            'pair of smaller matching template glass vessels: an upper silver lid rests lifted, while a crisp '
            'warm-amber (#ffbf83) optical shutter strip slides directly across all four glass chambers to veil their '
            'recessed interiors completely; museum-grade architectural still-life photography, crisp glass refraction, '
            'dramatic soft studio rim lighting, shallow depth of field, centered crop-safe composition with generous '
            'dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='88c9345bc16f1f611e3ba20bcd0166ce675258b0125289a47d9208de53852683',
    ),
    dict(
        index=264,
        id='url:https://www.postgresql.org/docs/17/sql-copy.html',
        kind='article',
        title='PostgreSQL 17 Documentation — COPY (Server File Access & COPY ... PROGRAM)',
        url='https://www.postgresql.org/docs/17/sql-copy.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/sql-copy.html'],
        aliases=['PostgreSQL 17 COPY', 'COPY TO PROGRAM', 'COPY FROM PROGRAM'],
        tags=['SQL', '보안·안전'],
        note=(
            'PostgreSQL 17 SQL reference detailing server-side file paths and shell command execution via '
            'COPY ... PROGRAM versus safe client-side STDIN/STDOUT streaming. Referenced by Node PG Defense '
            '(control 31).'
        ),
        label='SERVER FILE & PROGRAM GATE',
        slug='postgres-copy-program',
        factualConcept=(
            'PostgreSQL 17 COPY documentation distinguishes privileged server-side filesystem paths and COPY ... '
            'PROGRAM shell execution from safe client-side FROM STDIN streaming; Node PG Defense control 31 flags '
            'server-side file and program execution SQL for removal and runtime denial checks.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a thick machined dark-graphite bulkhead wall separating a glowing crystal database chamber on '
            'the left from a matte dark-titanium host rack on the right: a heavy warm-amber (#ffbf83) optical glass '
            'locking bolt seals the interior server conduit completely shut, while a slender clear-glass client '
            'stream tube smoothly feeds into the left chamber from the foreground; museum-grade industrial still-life '
            'photography, crisp refraction, soft studio rim lighting, shallow depth of field, centered crop-safe '
            'composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='96d76ca0c94f3bc99e7bb7978b9543f9f2e5da60d5801203ce719cda18d43e4d',
    ),
    dict(
        index=265,
        id='url:https://www.postgresql.org/docs/17/dblink.html',
        kind='article',
        title='PostgreSQL 17 Documentation — F.11. dblink',
        url='https://www.postgresql.org/docs/17/dblink.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/dblink.html'],
        aliases=['PostgreSQL 17 dblink', 'dblink_connect_u'],
        tags=['SQL', '보안·안전'],
        note=(
            'PostgreSQL 17 extension documentation covering outbound database connections, dblink_connect_u, and '
            'remote credential handling. Referenced by Node PG Defense (control 32) for inventorying and restricting '
            'extensions and untrusted languages that reach outside the database server.'
        ),
        label='OUTBOUND EXTENSION BOUNDARY',
        slug='postgres-dblink',
        factualConcept=(
            'PostgreSQL 17 dblink documentation details outbound database connectivity and dblink_connect_u '
            'privilege risks; Node PG Defense control 32 audits outbound extensions, untrusted procedural languages, '
            'and PUBLIC user mappings against an explicit approval list.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing two separate cylindrical brushed-graphite database towers standing across a dark empty channel: '
            'a delicate curved smoked-glass outbound bridge arch spanning toward the distant tower is cleanly '
            'intercepted at midpoint by an upright warm-amber (#ffbf83) optical isolation shutter blade anchored in '
            'a satin-steel socket; refined architectural miniature still-life photography, crisp glass and brushed '
            'metal textures, soft studio rim lighting, shallow depth of field, centered crop-safe composition with '
            'generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='8958365cc0ccfbdf5129b6f1aaa127627ab57c253886eee36ce6fa65bc8f2f5e',
    ),
    dict(
        index=266,
        id='url:https://www.postgresql.org/docs/17/role-attributes.html',
        kind='article',
        title='PostgreSQL 17 Documentation — 21.2. Role Attributes',
        url='https://www.postgresql.org/docs/17/role-attributes.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/role-attributes.html'],
        aliases=['PostgreSQL 17 Role Attributes', 'SUPERUSER BYPASSRLS CREATEROLE'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 documentation covering high-impact role attributes (SUPERUSER, BYPASSRLS, CREATEROLE, '
            'REPLICATION, LOGIN, VALID UNTIL). Referenced by Node PG Defense (controls 17 and 33) to audit '
            'effective role privileges and dormant login accounts.'
        ),
        label='PRIVILEGED ROLE ATTRIBUTES',
        slug='postgres-role-attributes',
        factualConcept=(
            'PostgreSQL 17 section 21.2 specifies high-impact role attributes (SUPERUSER, BYPASSRLS, CREATEROLE, '
            'REPLICATION, VALID UNTIL); Node PG Defense controls 17 and 33 flag privileged role attributes and '
            'require checking effective login role counts against an approved baseline.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a precision machined matte-graphite tumbler lock block: four tall smoked-glass privilege pins '
            'ringed with restrained warm-amber (#ffbf83) metal collars sit locked down flush beneath a solid clear '
            'optical-glass retainer bar, while one compact luminous-lime (#d3fc70) low-privilege glass pin rests '
            'cleanly active in a separate front channel; museum-grade studio product photography, tactile metal and '
            'crystal refraction, soft rim lighting, shallow depth of field, centered crop-safe composition with '
            'generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='8f1117d1e0e4089d46e945e3aac3b11c303539238e52563259045f1bd0ad3e23',
    ),
    dict(
        index=267,
        id='url:https://www.postgresql.org/docs/17/predefined-roles.html',
        kind='article',
        title='PostgreSQL 17 Documentation — 21.5. Predefined Roles',
        url='https://www.postgresql.org/docs/17/predefined-roles.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/predefined-roles.html'],
        aliases=['PostgreSQL 17 Predefined Roles', 'pg_execute_server_program', 'pg_read_server_files'],
        tags=['SQL', '보안·안전', '신뢰성'],
        note=(
            'PostgreSQL 17 documentation enumerating predefined server-access and global-data roles '
            '(pg_read_server_files, pg_write_server_files, pg_execute_server_program, pg_read_all_data, '
            'pg_write_all_data). Referenced by Node PG Defense (controls 18 and 33).'
        ),
        label='PREDEFINED ROLE CAPABILITIES',
        slug='postgres-predefined-roles',
        factualConcept=(
            'PostgreSQL 17 section 21.5 defines server-access and global-data predefined roles including '
            'pg_read_server_files, pg_write_server_files, pg_execute_server_program, and pg_read/write_all_data; '
            'Node PG Defense controls 18 and 33 audit direct and inherited memberships in these roles.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a radial constellation of five faceted smoked-glass capability discs arranged around a '
            'brushed-graphite central hub linked by hairline silver spokes: the high-impact outer glass discs sit '
            'cleanly partitioned behind curved warm-amber (#ffbf83) optical shield arcs so elevated server '
            'capabilities stay bounded from the quiet central glass lens; refined scientific still-life photography, '
            'crisp glass refraction, dramatic soft studio rim lighting, shallow depth of field, centered crop-safe '
            'composition with generous dark olive margins, zero text, zero letters, zero digits, zero logos, zero icons, zero borders.'
        ),
        sourceSha256='267fba0b9c35404aa1f75d565c138584ec8a6020ccf617fecc381724f78f21e7',
    ),
    dict(
        index=268,
        id='url:https://www.postgresql.org/docs/17/sql-altersystem.html',
        kind='article',
        title='PostgreSQL 17 Documentation — ALTER SYSTEM',
        url='https://www.postgresql.org/docs/17/sql-altersystem.html',
        year=2026,
        keys=['url:https://www.postgresql.org/docs/17/sql-altersystem.html'],
        aliases=['PostgreSQL 17 ALTER SYSTEM', 'GRANT ALTER SYSTEM ON PARAMETER'],
        tags=['SQL', '보안·안전'],
        note=(
            'PostgreSQL 17 SQL reference for server configuration changes via ALTER SYSTEM and parameter-level '
            'privilege delegation. Referenced by Node PG Defense (control 34) to block ALTER SYSTEM in app code '
            'and restrict parameter delegation on command-executing or library-loading parameters.'
        ),
        label='PARAMETER DELEGATION LOCK',
        slug='postgres-alter-system',
        factualConcept=(
            'PostgreSQL 17 ALTER SYSTEM documentation covers persistent server parameter modification and '
            'parameter privilege delegation; Node PG Defense control 34 flags ALTER SYSTEM and GRANT ... ON '
            'PARAMETER to protect command-executing and shared-library parameters.'
        ),
        prompt=(
            'Macro isometric three-quarter studio product photograph on a near-black olive seamless tabletop (#10130f) '
            'showing a miniature architectural precision control console milled from matte dark graphite: three '
            'critical system rotary dials on the left sit completely sealed beneath a thick clear optical-glass '
            'safety hood edged in luminous warm amber (#ffbf83), while two modest tuning micro-dials on the right '
            'rest accessible inside an approved brushed-silver recess; museum-grade industrial design still-life '
            'photography, crisp glass refraction, dramatic soft studio rim lighting, shallow depth of field, '
            'centered crop-safe composition with generous dark olive margins, zero text, zero letters, zero digits, '
            'zero logos, zero icons, zero borders.'
        ),
        sourceSha256='dfd659933a7d7e4826e11c79554137611074ef7a8e012074d116d0946e8fe602',
    ),
]


def read_blob_lines(plugin_root: Path, commit: str, rel_file: str) -> list[str]:
    out = subprocess.check_output(
        ['git', '-C', str(plugin_root), 'show', f'{commit}:{rel_file}'],
        stderr=subprocess.PIPE,
    )
    return out.decode('utf8').splitlines()


def find_unique_line(lines: list[str], url: str) -> tuple[int, str]:
    matches = [(idx + 1, line) for idx, line in enumerate(lines) if url in line]
    if len(matches) != 1:
        raise ValueError(f'Expected 1 match for {url!r} in {REF_FILE}, found {len(matches)}')
    line_no, text = matches[0]
    excerpt = text.strip()
    if len(excerpt) > 220:
        raise ValueError(f'Excerpt exceeds 220 chars on line {line_no}: {len(excerpt)}')
    return line_no, excerpt


def make_evidence(commit: str, line_no: int, excerpt: str) -> dict:
    return {
        'file': REF_FILE,
        'line': line_no,
        'url': f'https://github.com/Technoetic/{PLUGIN}/blob/{commit}/{REF_FILE}#L{line_no}',
        'excerpt': excerpt,
    }


def apply_update(plugin_root: Path, commit: str, apply: bool) -> dict:
    lines = read_blob_lines(plugin_root, commit, REF_FILE)
    reg_path = ROOT / 'data/registry.source.json'
    art_path = ROOT / 'docs/card-artwork-unique-prompts.json'
    idx_path = ROOT / 'src/screens/artwork-index.mjs'

    registry = json.loads(reg_path.read_text(encoding='utf8'))
    manifest = json.loads(art_path.read_text(encoding='utf8'))

    registry['snapshots'][PLUGIN] = {
        'name': PLUGIN_NAME,
        'version': VERSION,
        'commit': commit,
        'url': f'https://github.com/Technoetic/{PLUGIN}/tree/{commit}',
    }

    by_id = {source['id']: source for source in registry['sources']}

    # 1. Attach node-pg-defense use to the 4 existing shared PostgreSQL articles
    shared_added = 0
    for raw_url in SHARED_URLS:
        cid = canonical_key(raw_url)['key']
        if cid not in by_id:
            raise ValueError(f'Expected shared source missing from registry: {cid}')
        line_no, excerpt = find_unique_line(lines, raw_url)
        ev = make_evidence(commit, line_no, excerpt)
        src = by_id[cid]
        src['uses'] = [u for u in src['uses'] if u['plugin'] != PLUGIN]
        src['uses'].append({'plugin': PLUGIN, 'role': 'reference', 'evidence': [ev]})
        shared_added += 1

    # 2. Add or replace the 17 new node-pg-defense sources
    new_added = 0
    new_evidence_by_id = {}
    for spec in NEW_SOURCES:
        line_no, excerpt = find_unique_line(lines, spec['url'])
        ev = make_evidence(commit, line_no, excerpt)
        new_evidence_by_id[spec['id']] = [ev['url']]
        record = {
            'id': spec['id'],
            'kind': spec['kind'],
            'title': spec['title'],
            'url': spec['url'],
            'year': spec['year'],
            'keys': spec['keys'],
            'aliases': spec['aliases'],
            'tags': spec['tags'],
            'note': spec['note'],
            'uses': [{'plugin': PLUGIN, 'role': 'reference', 'evidence': [ev]}],
        }
        if spec['id'] in by_id:
            existing = by_id[spec['id']]
            existing.update(record)
        else:
            registry['sources'].append(record)
            by_id[spec['id']] = record
        new_added += 1

    registry['updatedAt'] = datetime.now(timezone.utc).isoformat()
    audited = merge_sources(registry['sources'])
    validate_catalog({'schemaVersion': 1, 'snapshots': registry['snapshots'], 'sources': audited})
    audited_by_id = {s['id']: s for s in audited}

    # 3. Sync artwork manifest currentEvidenceUrls/evidenceUrls for existing records (preserving generationEvidenceUrls!)
    existing_assets_by_id = {a['sourceId']: a for a in manifest['assets']}
    for asset in manifest['assets']:
        src = audited_by_id.get(asset['sourceId'])
        if src:
            urls = [row['url'] for use in src['uses'] for row in use['evidence']]
            asset['evidenceUrls'] = urls
            asset['currentEvidenceUrls'] = urls

    # 4. Append 17 new artwork records (card-252..268)
    for spec in NEW_SOURCES:
        output = f"media/cards/card-{spec['index']}-{spec['slug']}.webp"
        webp_path = ROOT / output
        if not webp_path.is_file():
            raise FileNotFoundError(f'Missing WebP artwork: {webp_path}')
        wb = webp_path.read_bytes()
        webp_sha = hashlib.sha256(wb).hexdigest()
        ev_urls = new_evidence_by_id[spec['id']]
        art_entry = {
            'index': spec['index'],
            'sourceId': spec['id'],
            'title': spec['title'],
            'kind': spec['kind'],
            'label': spec['label'],
            'factualConcept': spec['factualConcept'],
            'prompt': spec['prompt'],
            'output': output,
            'sha256': webp_sha,
            'bytes': len(wb),
            'dimensions': [960, 640],
            'evidenceUrls': ev_urls,
            'generationEvidenceUrls': list(ev_urls),
            'currentEvidenceUrls': list(ev_urls),
            'delivery': {
                'sourceSha256': spec['sourceSha256'],
                'sourceDimensions': [1264, 848],
                'operation': 'Full-frame Lanczos resize and WebP encoding only; no crop, compositing or semantic edit',
                'tool': 'Pillow 12.3.0 (Python WebP encoder)',
                'quality': 90,
                'compressionLevel': 6,
                'commandTemplate': (
                    "python -c \"from PIL import Image; Image.open('INPUT').convert('RGB')."
                    "resize((960, 640), Image.Resampling.LANCZOS).save('OUTPUT.webp', format='WEBP', quality=90, method=6)\""
                ),
            },
            'generationReferenceUrls': [spec['url']],
        }
        if spec['id'] in existing_assets_by_id:
            prev_gen = existing_assets_by_id[spec['id']].get('generationEvidenceUrls')
            existing_assets_by_id[spec['id']].update(art_entry)
            if prev_gen:
                existing_assets_by_id[spec['id']]['generationEvidenceUrls'] = prev_gen
        else:
            manifest['assets'].append(art_entry)
            existing_assets_by_id[spec['id']] = art_entry

    manifest['count'] = len(manifest['assets'])

    # 5. Update src/screens/artwork-index.mjs cleanly
    idx_lines = idx_path.read_text(encoding='utf8').splitlines()
    if idx_lines[-1].strip() != '});':
        raise ValueError('Unexpected artwork-index.mjs closing line')
    existing_idx_text = '\n'.join(idx_lines)
    append_lines = []
    for spec in NEW_SOURCES:
        key_token = json.dumps(spec['id'])
        if f'  {key_token}:' in existing_idx_text:
            continue
        card_key = f"card-{spec['index']}-{spec['slug']}"
        append_lines.append(
            f'  {key_token}: Object.freeze({{key: {json.dumps(card_key)}, '
            f'src: new URL("../../media/cards/{card_key}.webp", import.meta.url).href, '
            f'label: {json.dumps(spec["label"])}, word: {json.dumps(spec["label"])}}}),'
        )
    new_idx_text = '\n'.join(idx_lines[:-1] + append_lines + ['});']) + '\n'

    summary = {
        'apply': apply,
        'commit': commit,
        'shared_added': shared_added,
        'new_added': new_added,
        'audited_sources': len(audited),
        'artwork_count': manifest['count'],
    }
    if apply:
        reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
        art_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
        idx_path.write_text(new_idx_text, encoding='utf8', newline='\n')
        catalog = build(ROOT)
        summary['counts'] = catalog['counts']
        summary['countsByPlugin'] = catalog['countsByPlugin']
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = apply_update(args.plugin_root, args.commit, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
