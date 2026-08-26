# Specification: Mesh Measurement And Verification

## Purpose

Establish what it means to have proven something about geometry. Every claim
about a mesh - that a generation succeeded, that a canonicalization matched,
that a rig deforms - is backed by recorded numbers.

## The Rule

Proof is measurement, never appearance. A screenshot, a render, or a viewer
impression is never sufficient evidence that a mesh artifact is correct.

Every mesh artifact the pipeline produces or consumes is re-loaded from disk
and measured. Measuring reads; it never modifies the artifact.

## Measured Facts

A measurement of any mesh artifact records:

| Field | Meaning |
| --- | --- |
| `source`, `file_size_bytes`, `file_format` | The artifact identity on disk |
| `geometries` | Sub-meshes in the source scene |
| `vertices`, `faces` | Counts after combining all sub-meshes |
| `bounds_min`, `bounds_max`, `extents`, `centroid` | Position and size |
| `surface_area` | Total area |
| `volume` | Present only when the mesh is watertight; otherwise absent, because the number is meaningless |
| `watertight` | Whether the surface is closed |
| `connected_components` | Disconnected pieces; always available, never degraded to "unknown" |
| `degenerate_faces` | Zero-area faces - a repair signal and a fitting hazard |
| `all_finite` | No NaN or infinite coordinate |
| `textured` | Whether material information is present |
| `sampled_points` | Surface samples taken, confirming the mesh can be sampled |
| `measured_at` | When it was measured |
| `backend`, `seed`, `request_name` | Provenance, when the artifact came from a generation |

A measurement is *plausible* when it has non-zero vertices and faces, finite
coordinates, non-zero surface area, and non-zero extent. Plausibility is a
floor, not a quality judgement.

## Sidecars

Measurements are written beside the artifact as
`<stem>.measurements.json`, atomically. A sidecar re-reads into the same
contract it was written from.

Writing a sidecar is an explicit act. Measuring never writes one on its own.

## Formats

Measurement works on any mesh artifact the pipeline touches - GLB, glTF, OBJ,
PLY, STL - so verification is possible without a provider call, on any local
fixture.

## Verification Levels

Beyond the metrics above, each pipeline stage carries its own obligations:

- **Raw generated meshes** carry untrusted topology: arbitrary vertex counts
  and ordering, unclosed surfaces, and many disconnected components are
  expected, not defects. The floor is plausibility.
- **Canonical meshes** match the template's exact vertex and face counts and
  vertex ordering, carry every required semantic region, and contain no NaN
  vertices and no degenerate faces.
- **Rigs** contain every bone of the template hierarchy, with approximately
  unit-sum skin weights and no unweighted vertices.
- **Deformation claims** are proven by deterministic test poses producing
  recorded metrics.

## Failure Reporting

An artifact that cannot be loaded, or that holds no triangle geometry,
produces a clear error naming the file. A missing metric is never silently
omitted or replaced with a placeholder.

## Acceptance Criteria

- Measuring a mesh of known construction reproduces its known properties.
- A non-watertight mesh reports no volume.
- Connected components are reported for every mesh.
- Measuring writes nothing; the sidecar round-trips.
- An unloadable file produces an error, not a partial measurement.

## Non-Goals

- Quality, aesthetic, or anatomical judgement.
- Automatic repair: measurement reports, it does not fix.
- Comparing two meshes for similarity - that belongs to the canonicalization
  contract.
