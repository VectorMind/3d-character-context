# Workflow

This repository is spec-driven. It uses durable specifications for binding
contracts and dated plans for time-bounded implementation work.

`3d-character-context` is a workbench for generative-first 3D character
production: a hosted generative 3D model invents novel character geometry, and
a deterministic canonicalization layer transforms that arbitrary mesh into a
known topology with a known skeleton, producing predictable production assets
(GLB/FBX). V1 targets exactly one character family: the western quadruped
dragon.

## Guiding Principle: Replaceable Generators, Canonical Production

The generative 3D backend is deliberately replaceable infrastructure. The
valuable long-term layer is deterministic canonicalization: anatomical
interpretation, canonical topology fitting, canonical skeleton fitting, and
verified export. Backend-native responses must never leak past the generator
boundary; the rest of the pipeline operates on normalized mesh artifacts and
pydantic contracts.

> Use generative AI for invention. Use deterministic canonicalization for
> production.

## Spec Maintenance

Keep `specifications/` current as durable decisions emerge. Whenever the
maintainer states a strategy, policy, contract, or wisdom-level rule — or work
settles such a decision — fold it into the relevant spec in the same pass, not
just into a plan or a commit message. Plans are time-bounded and get abandoned
after implementation; the spec is what survives. Do not record case-level
implementation detail in the spec; capture the durable rule behind it.

## Data/Code Split

The code repository holds only code, contracts, and documentation. The
external project folder is the durable **data co-workspace**, not merely a
generation-output destination. It holds all input data (reference images),
append-only generated meshes, reusable collected donor/source assets and
their provenance, and canonical template assets (canonical mesh, skeleton,
landmarks, regions, and weights). Keeping these in the external project also
frees asset and base-model choices from redistribution licensing constraints.

The selected project uses three top-level data roots:

```text
<project>/
  inputs/       # supplied references and other run inputs
  generated/    # append-only provider/run results
  assets/       # collected reusable assets and verified canonical assets
```

New third-party assets enter through `<project>/assets/_inbox/` and, after
provenance and licensing are recorded, become self-contained packages under
`<project>/assets/collected/`. Canonical assets remain a separate, deliberate
promotion; collection alone never makes an asset canonical. The selected
project may be a cloud-synced collaboration workspace. If it contains its own
`AGENTS.md`, `README.md`, or `INDEX.md`, those files are authoritative for the
data present there, provenance handling, and navigation, while this repository
remains authoritative for software behavior and contracts.

Operational output (command results, reports, scratch, and transient
downloads) belongs under the repository's git-ignored `.cache/`. A valuable
download must not remain only in `.cache/`: move it into the selected project
through the documented intake flow without altering the original bytes.
Never commit `.cache/` content and never mix data or generated files into
`specifications/`, `plans/`, or `src/`.

The pipeline is fully automated: the workflow does not assume a skilled 3D
author/modeller, so asset production must be scripted, never dependent on
hand-sculpting.

## Git Ownership

The maintainer owns all git operations. Assistants and tools must not run
`git add`, `git commit`, `git push`, branch, or any other history-changing git
command. Leave finished work in the working tree and let the maintainer
review, stage, and commit it.

## Areas

### `specifications/`

Use `specifications/` for durable requirements that constrain implementation
across more than one pass.

Create a specification under:

```text
specifications/<slug>/spec.md
```

Specifications contain timeless binding rules and contracts:

- generator-backend capabilities, request/response contracts, and isolation
  rules;
- canonical asset conventions (topology, coordinate system, scale,
  orientation, naming, landmark and skeleton schemas);
- mesh measurement and verification contracts;
- accepted non-goals and unsupported behavior.

Specifications must not read like plans or history. Avoid wording such as
"planned", "future", "previously", or "we decided". Put implementation history
in `implementation.md` instead.

### `plans/`

Use `plans/` for dated planning packets tied to active work.

Each plan folder uses:

```text
plans/YYYY-MM/
  DD-<slug>/
    survey.md            # only when the maintainer explicitly requests one
    plan.md
    implementation.md    # created only after implementation work has happened
    test.md
```

Create `survey.md` only when the maintainer explicitly requests a survey. Do
not produce one as a default step; fold light discovery notes into `plan.md`
instead.

Two index files at the top of `plans/` track packet status: `closed.md` lists
completed packets with their proof, and `open.md` lists packets with work
still outstanding. Update these tables whenever a plan is finished or started
so the current state of all plans is visible at a glance.

## Plan Shape

`plan.md` must stay focused on the work package. It should contain:

- problem summary;
- resolution summary;
- goal and objectives;
- scope and non-goals;
- open points with resolution status;
- implementation phases;
- dependencies and risks;
- exit criteria.

Open points should be tracked across the discussion. Use stable IDs such as
`OP-001`, keep the current status visible, and record the resolution only when
the answer is accepted.

**Every open point names a proposal and carries a confidence.** This is not
limited to points that select a dependency, framework, provider, or tool: it
applies to any question the plan asks, including the anatomical and
methodological ones ("where is the elbow", "does the hierarchy come from the
taxonomy or from the geometry"). A question recorded without a proposal is a
question that stalls the work waiting for an answer, and a proposal recorded
without a confidence hides how much the maintainer is actually being asked to
weigh. So each open point lists:

- the candidate options with a short argument each, including the two easiest
  to forget: doing the simplest possible thing, and doing nothing;
- **a named proposal**, which the work proceeds on unless and until the
  maintainer overturns it;
- **a confidence** (`high` / `medium` / `low`) with a clause saying what would
  move it — a measurement, a second donor, a look at the picture.

Confidence is about the evidence, not about enthusiasm. A proposal that has
been measured against real data is `high` even when the measurement is
unflattering; a proposal that is merely reasonable is `medium` at best.

The resolution summary, placed directly after the problem summary, carries a
**one-glance table of every open point, design decision and dependency** with
columns for id, topic, proposal (the accepted resolution once decided),
confidence, and status. The table is the at-a-glance state of the plan's decisions and is
updated in the same pass whenever an open point changes status; the full
candidate options and arguments stay in the detailed Open Points section
below it.

### The Global Decision Table

A decision the maintainer has not taken yet must never be reachable only by
opening the plan that raised it. `plans/open.md` therefore carries a
**Decisions And Open Points** table spanning every packet, in the same spirit
as its Dependencies table: one row per open point, design decision, question or
request for feedback that is still awaiting the maintainer, with columns for
id, packet, topic, proposal, confidence and status.

The rules that keep it useful:

- **It is the queue, not the archive.** A row leaves the table once the
  maintainer has accepted, rejected or deferred it; the packet's own resolution
  summary keeps the full history. An empty table means nothing is waiting.
- **Ids stay packet-local** (`OP-201` in the packet that raised it), and the
  global row names the packet, so a row and its argument are one click apart.
- **It is updated in the same pass** as the packet's own table. A packet that
  raises an open point and does not add it here has not raised it.
- **Dependencies keep their own table** below it, because a dependency request
  has a different shape — a ceiling, alternatives, a probe, a blast radius —
  and mixing the two would flatten both.

### Dependencies

Adding a runtime dependency is a maintainer decision, and the point of writing
it down is that **needing approval must never be what stops the work**. A
dependency is therefore an open point like any other selection: it gets a
stable `DEP-00n` id, it appears in the resolution summary table with its
status, and the case for it lives in the plan rather than in a conversation.

Each dependency open point carries:

- **the ceiling without it** — what the packet cannot do, or can only do
  worse, in one line;
- **the alternatives**, including the two that are easy to forget: writing the
  routine out by hand, and doing without;
- **a probe, not a citation.** Run the exact calls the packet would make,
  against real project data, on this platform, and record the timings and
  outputs. A package that *resolves* is not a package that *installs*: a
  source-only distribution will resolve happily and then fail for want of a
  compiler. A dependency that has not been exercised here is a proposal, not
  a finding;
- **the blast radius** — what it pulls in transitively, and what stops working
  if it is later removed.

Work does not wait on the answer. The packet proceeds down the path that needs
no new dependency, records the ceiling that path actually hit, and leaves the
open point standing at `awaiting approval`. That way an unanswered request
costs a measurement rather than a stall, and the measurement is what makes the
case when the question is finally put.

A rejected dependency stays in the table with its reason. The next packet that
wants it should find out why it lost without re-running the probe.

`plans/open.md` carries a **Dependencies** table spanning every packet, next to
the Decisions And Open Points table above, so a request is never buried inside
one plan the maintainer is not reading.

`plan.md` does not need detailed rewrites for every implementation deviation.
Once implementation starts, facts about what actually landed belong in
`implementation.md`.

## Implementation Log

Create `implementation.md` only once implementation work has actually
happened; it logs facts really implemented, never planned intent. A packet
that is still in planning or review has no `implementation.md`.

Every `implementation.md` opens with a **Progress** section — the first
section after the title — and it is updated on every change to the file. It is
a one-glance progress bar, not prose:

- one line with a bar of filled/empty blocks plus the current phase, e.g.
  `` `▰▰▰▱▱▱ Phase 3/6` ``, using the plan's own phase or milestone names;
- one short clause naming the phase in progress and what comes next;
- when the packet is fully implemented and proven, the bar is full and the
  line reads `Done`, e.g. `` `▰▰▰▰▰▰ Done` `` with a one-clause summary and
  any non-blocking follow-ups.

Keep the Progress section to two lines at most; the running detail belongs in
the log below. Use the rest of the file as the running trace of work:

- files changed;
- implementation facts;
- decisions made during development;
- deviations from the plan;
- follow-up risks;
- important commands or migrations.

The implementation log should describe what happened, not restate the whole
plan.

## Test Proof

Use `test.md` as proof of behavior:

- commands run;
- fixtures used;
- expected results;
- actual results;
- known gaps;
- environment or dependency notes that affect reproducibility.

For planning-only changes, `test.md` may record document review and
consistency checks instead of runtime proof.

For mesh and rig work, proof means measurement, never appearance alone:

- a downloaded or generated GLB/OBJ must re-load through a mesh library and
  report non-zero vertex/face counts, finite coordinates, reasonable bounds,
  and connected-component structure;
- a canonicalized mesh must match the template's exact vertex/face counts and
  vertex ordering, carry the required semantic regions, and contain no NaN
  vertices or degenerate faces;
- a fitted rig must contain every required bone in the template hierarchy
  with valid, approximately unit-sum skin weights and no unweighted vertices;
- deformation claims are proven by deterministic test poses producing
  recorded mesh metrics or renders.

## Scope Ownership

`3d-character-context` owns the generator-backend abstraction, the canonical
character-family contracts (topology, landmarks, skeleton, regions), the
canonicalization and rig-fitting pipeline, verification, and export. It does
not compete with the hosted generative models themselves, with DCC tools
(Blender is an optional downstream geometry/rigging engine behind a service
boundary, never the generative AI), or with game-engine import pipelines —
where an external tool is better for a job, plans should say so and integrate
rather than rebuild.
