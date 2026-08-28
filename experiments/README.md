# Experiments

Standing, re-runnable probes of external provider access. They exist because
provider availability is a moving target: every claim about what a hosted
backend offers must be re-provable on demand, not remembered from a document.

These are experiments, not product code. They are deliberately outside
`src/`: no package, no imports from the (future) `character_context` package,
and no shared state beyond `_common.py`. Once a backend is chosen and
implemented, the equivalent behavior lives behind the `charctx` CLI; these
scripts stay as access probes.

## Running

Each script is a self-contained [PEP 723](https://peps.python.org/pep-0723/)
script — no virtualenv, no `pyproject.toml`, no `uv sync` needed. `uv` reads
the dependency block in the file header and builds the environment on the fly:

```powershell
uv run --script experiments/hf_01_hello_inference.py
uv run --script experiments/hf_02_trellis_space.py
```

Credentials come from the git-ignored `.env` at the repository root
(`HF_TOKEN=...`); a shell environment variable overrides the file. Tokens are
masked in every report.

## Scripts

| Script | What it proves |
| --- | --- |
| `hf_01_hello_inference.py` | The `HF_TOKEN` authenticates; the Inference Providers router answers; a hello-world chat completion round-trips; the legacy `api-inference` host is gone; **no** `image-to-3d` model is served by REST inference. |
| `hf_02_trellis_space.py` | Which TRELLIS Spaces are up; their real Gradio API surface; a reference image goes in and a GLB comes back; the GLB re-loads and measures. |
| `hf_03_live_validation.py` | That `charctx generate` itself works end to end: it drives the real CLI, lands meshes in the project folder, and verifies each run slot. Quota-aware - it waits out a refusal using the provider's own reset time. |

`hf_03_live_validation.py` runs in the **project environment**, not as a
standalone script, because it drives the installed CLI:

```powershell
uv run python experiments/hf_03_live_validation.py --runs 3
```

| Flag | Effect |
| --- | --- |
| `--runs N` | How many generations to attempt |
| `--name`, `--seed` | Run slug and starting seed (each run increments the seed) |
| `--image PATH` | Reference image (default: the project's `inputs/references/trellis-example-dragon.png`) |
| `--no-wait` | Fail immediately on a quota refusal instead of waiting it out |

Useful flags for `hf_02_trellis_space.py`:

| Flag | Effect |
| --- | --- |
| `--probe-only` | Report Space runtime stages and fetch the input image; make no generation call (costs no GPU quota). |
| `--space <id>` | Use one specific Space instead of every running candidate. |
| `--image <path>` | Use your own reference image instead of the Space example dragon. |
| `--first-success` | Stop after the first Space that returns a GLB. |
| `--measure <path…>` | Re-measure GLB files or folders already downloaded; no Space call, no quota. |

The TRELLIS probe is currently a **monoview generation probe** even though its
API-surface report records every endpoint parameter. In particular, it records
original TRELLIS's `multiimages` and `multiimage_algo` parameters but submits
an empty multi-image gallery. It does not prove multiview generation. The
separate future work and provider candidates are tracked in
[`plans/2026-08/28-multiview-support/plan.md`](../plans/2026-08/28-multiview-support/plan.md).

## Output

Every run writes a timestamped folder — never overwriting an earlier run:

```text
.cache/results/<YYYY-MM-DD>/<HHMMSS>-<experiment>/
  <experiment>.md      # human-readable findings
  <experiment>.json    # the same run as structured probes
  *.glb, *.png         # artifacts the run downloaded
  *.measurements.json  # mesh metrics
```

`.cache/` is git-ignored. Generated meshes kept for the pipeline belong in the
project folder (`CHARCTX_PROJECT`), not here — what lands in `.cache/results/`
is experiment evidence.

## Quota

TRELLIS Spaces run on shared ZeroGPU hardware. A free account gets a few
minutes of GPU per day and **each TRELLIS call reserves 120 s of that budget
up front**, so roughly four generations exhaust the day; the Space then
refuses the call outright with a `Try again in HH:MM:SS` message. Use
`--probe-only` and `--measure` while iterating on the scripts, and spend the
quota only on real generation runs.
