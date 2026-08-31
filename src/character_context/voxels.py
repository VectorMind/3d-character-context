"""Voxel substrate: turn shell soup into one connected solid, then label it.

This module exists because of a single fact about the generated meshes. Riyu is
203,745 vertices in **6,209 disconnected shells** and is not watertight, which
rules out every surface-based method: geodesic distance, connected-component
walks, surface parameterisation, and Blender's bone-heat weighting all need a
connected surface that is not there.

In an occupancy grid none of that is true. The 6,209 shells are one connected
solid, because shell soup is a property of the surface representation and does
not survive rasterisation. Everything downstream -- geodesic distance through
the body, region growing, and later weight diffusion -- becomes available in
one move.

Nothing here assumes watertightness. Inside is found by flood-filling the
*complement* from the grid boundary: whatever the outside air cannot reach is
solid. That works on a surface with thousands of holes, provided each hole is
smaller than a voxel after closing, and the occupancy ratio is reported so that
assumption stays checkable rather than implied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import ConfigError

# Six-connected: parts should not leak diagonally across a one-voxel contact.
NEIGHBOURS = (
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
)


@dataclass(frozen=True)
class Grid:
    """An occupancy grid and the affine mapping back to world space."""

    solid: Any  # bool array, shape (n, n, n)
    origin: tuple[float, float, float]
    pitch: float
    resolution: int

    @property
    def count(self) -> int:
        return int(self.solid.sum())

    def to_world(self, indices: Any) -> Any:
        """Voxel centres for an (m, 3) integer index array."""
        import numpy as np

        return (
            np.asarray(indices, dtype=float) + 0.5
        ) * self.pitch + np.asarray(self.origin)

    def to_index(self, points: Any) -> Any:
        """Nearest voxel index for an (m, 3) world-space point array, clamped."""
        import numpy as np

        raw = (np.asarray(points, dtype=float) - np.asarray(self.origin)) / self.pitch
        return np.clip(
            np.floor(raw).astype(int), 0, self.resolution - 1
        )


def _geometries(mesh: Any) -> list[Any]:
    parts = [
        geometry
        for geometry in (mesh.dump() if hasattr(mesh, "dump") else [mesh])
        if getattr(geometry, "vertices", None) is not None and len(geometry.vertices)
    ]
    if not parts:
        raise ConfigError("Mesh has no vertices to voxelize.")
    return parts


# Surface sampling is random. Seeded, so two runs on the same mesh produce the
# same grid: an unseeded run moved part counts by a few voxels between
# invocations, which is small but enough to make a recorded number
# irreproducible.
SAMPLE_SEED = 0


def _surface_points(
    geometries: list[Any], samples: int, seed: int = SAMPLE_SEED
) -> Any:
    """Vertices plus area-weighted surface samples.

    Vertices alone leave holes wherever the mesh has large faces, and samples
    alone miss sharp features. Both together close the shell.
    """
    import numpy as np
    import trimesh

    total = sum(float(getattr(geometry, "area", 0.0)) for geometry in geometries)
    parts = []
    for index, geometry in enumerate(geometries):
        parts.append(np.asarray(geometry.vertices, dtype=float))
        faces = getattr(geometry, "faces", None)
        area = float(getattr(geometry, "area", 0.0))
        if faces is None or not len(faces) or area <= 0 or total <= 0:
            continue
        share = max(int(samples * area / total), 1)
        try:
            # Per-geometry offset, so two meshes of equal area do not draw
            # the identical point pattern.
            points, _ = trimesh.sample.sample_surface(
                geometry, share, seed=seed + index
            )
            parts.append(np.asarray(points, dtype=float))
        except Exception:  # pragma: no cover - degenerate geometry
            pass
    return np.vstack(parts)


def voxelize(
    mesh: Any,
    resolution: int = 128,
    oversample: float = 24.0,
    closing: int = 1,
    max_samples: int = 8_000_000,
    seed: int = SAMPLE_SEED,
) -> tuple[Grid, dict[str, Any]]:
    """Rasterize a mesh into a filled occupancy grid.

    Three steps, none of which needs a watertight surface:

    1. splat surface points into the grid;
    2. morphologically close, so sub-voxel gaps between shells seal;
    3. flood-fill the complement from the grid boundary -- everything the
       outside air cannot reach is solid.

    Sample density is derived from the pitch rather than fixed, and that is
    load-bearing. Random surface sampling leaves pinholes by the coupon
    collector's problem, and a *single* missing voxel lets the exterior flood
    straight into the interior, so the fill silently returns a hollow shell.
    Drawing `oversample` points per voxel of surface area drives the chance of
    a hole to nothing, and `filled` reports whether the fill actually found an
    interior so a leak is visible rather than assumed away.
    """
    import numpy as np
    from scipy import ndimage

    if resolution < 8:
        raise ConfigError(f"Grid resolution {resolution} is too coarse to be useful.")

    geometries = _geometries(mesh)
    vertices = np.vstack(
        [np.asarray(geometry.vertices, dtype=float) for geometry in geometries]
    )
    minimum = vertices.min(axis=0)
    maximum = vertices.max(axis=0)
    extent = float(np.max(maximum - minimum))
    if extent <= 0:
        raise ConfigError("Mesh is degenerate: it has no extent.")

    # Pad every side, so the flood fill always has an exterior to start from
    # even when the mesh touches its own bounding box.
    padding = closing + 1
    pitch = extent / (resolution - 2 * padding)
    box_min = (minimum + maximum) / 2 - extent / 2
    origin = tuple(float(value) - pitch * padding for value in box_min)

    area = sum(float(getattr(geometry, "area", 0.0)) for geometry in geometries)
    samples = int(min(max_samples, max(20_000.0, area / (pitch * pitch) * oversample)))
    points = _surface_points(geometries, samples, seed)

    grid = Grid(
        solid=np.zeros((resolution,) * 3, dtype=bool),
        origin=origin,  # type: ignore[arg-type]
        pitch=pitch,
        resolution=resolution,
    )
    indices = grid.to_index(points)
    shell = np.zeros((resolution,) * 3, dtype=bool)
    shell[indices[:, 0], indices[:, 1], indices[:, 2]] = True
    raw_shell = int(shell.sum())

    if closing > 0:
        structure = ndimage.generate_binary_structure(3, 1)
        shell = ndimage.binary_closing(shell, structure=structure, iterations=closing)
    closed_shell = int(shell.sum())

    # Outside is whatever the border can reach through empty space.
    empty = ~shell
    labels, _ = ndimage.label(empty, structure=ndimage.generate_binary_structure(3, 1))
    border = set(labels[0, :, :].ravel()) | set(labels[-1, :, :].ravel())
    border |= set(labels[:, 0, :].ravel()) | set(labels[:, -1, :].ravel())
    border |= set(labels[:, :, 0].ravel()) | set(labels[:, :, -1].ravel())
    border.discard(0)
    outside = np.isin(labels, list(border)) if border else np.zeros_like(shell)

    solid = ~outside
    components, count = ndimage.label(
        solid, structure=ndimage.generate_binary_structure(3, 1)
    )

    report = {
        "resolution": resolution,
        "pitch": pitch,
        "origin": list(origin),
        "surface_area": round(area, 6),
        "samples": samples,
        "sample_seed": seed,
        "surface_points": int(len(points)),
        "shell_voxels": raw_shell,
        "shell_voxels_closed": closed_shell,
        "solid_voxels": int(solid.sum()),
        "interior_voxels": int(solid.sum()) - closed_shell,
        # False means the exterior reached the interior through a pinhole and
        # the result is a hollow shell, not a solid.
        "filled": bool(int(solid.sum()) > closed_shell),
        "occupancy": round(float(solid.sum()) / solid.size, 6),
        "solid_components": int(count),
        "closing_iterations": closing,
    }
    if count > 1:
        sizes = ndimage.sum_labels(
            solid, components, index=range(1, count + 1)
        ).astype(int)
        report["largest_component_fraction"] = round(
            float(sizes.max()) / float(sizes.sum()), 6
        )

    return Grid(solid, origin, pitch, resolution), report  # type: ignore[arg-type]


def seed_labels(grid: Grid, points: Any, labels: Any) -> Any:
    """Stamp labelled world points into a label array, restricted to solid.

    A seed that lands in empty space is pushed to the nearest solid voxel: a
    landmark sits on the surface and rounding can put it just outside, and
    dropping it would silently lose a part.
    """
    import numpy as np
    from scipy import ndimage

    result = np.zeros(grid.solid.shape, dtype=np.int16)
    indices = grid.to_index(points)
    values = np.asarray(labels, dtype=np.int16)

    inside = grid.solid[indices[:, 0], indices[:, 1], indices[:, 2]]
    if (~inside).any():
        # Nearest solid voxel, by Euclidean distance transform of the void.
        _, nearest = ndimage.distance_transform_edt(~grid.solid, return_indices=True)
        stray = indices[~inside]
        moved = nearest[:, stray[:, 0], stray[:, 1], stray[:, 2]].T
        indices = indices.copy()
        indices[~inside] = moved

    result[indices[:, 0], indices[:, 1], indices[:, 2]] = values
    result[~grid.solid] = 0
    return result


def watershed(grid: Grid, seeds: Any, max_rounds: int = 4096) -> tuple[Any, int]:
    """Grow every seed label through the solid until the volume is claimed.

    A uniform-cost multi-source flood, so each voxel takes the label of the
    nearest seed measured *through the body* rather than through the air. That
    distinction is the entire reason for working in a volume: a wing tip is far
    from the torso by way of the wing, and close to it in a straight line.

    Vectorised as repeated one-voxel dilations of the whole label field. Each
    round is six array shifts, so a 128 grid converges in well under a second
    where a per-voxel queue would take seconds.
    """
    import numpy as np

    labels = np.where(grid.solid, seeds, 0).astype(np.int16)
    if not labels.any():
        raise ConfigError("No seed landed inside the solid volume.")

    for rounds in range(1, max_rounds + 1):
        frontier = grid.solid & (labels == 0)
        if not frontier.any():
            return labels, rounds - 1
        # Propagate from labelled neighbours. Ties resolve by axis order,
        # which is arbitrary but deterministic.
        grown = labels
        for axis, delta in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
            shifted = np.roll(labels, delta, axis=axis)
            # A roll wraps; blank the wrapped face so parts cannot teleport
            # across the grid.
            index = 0 if delta > 0 else -1
            view = [slice(None)] * 3
            view[axis] = index
            shifted[tuple(view)] = 0
            grown = np.where((grown == 0) & (shifted != 0), shifted, grown)
        updated = np.where(frontier, grown, labels)
        if np.array_equal(updated, labels):
            # Unreachable solid remains: an isolated component with no seed.
            return labels, rounds
        labels = updated
    return labels, max_rounds


def component_split(labels: Any, index: int) -> int:
    """How many disconnected pieces one part's voxels fall into.

    One is healthy. More than one means the flood leaked across a contact --
    a wing folded onto a flank, a tail curled against a leg -- and that is
    exactly the failure mode worth reporting rather than averaging away.
    """
    from scipy import ndimage

    _, count = ndimage.label(
        labels == index, structure=ndimage.generate_binary_structure(3, 1)
    )
    return int(count)


def pool(labels: Any, factor: int) -> tuple[Any, int]:
    """Decimate a label grid by majority vote, for browser transport.

    The full grid is a computation artifact and is never served; the browser
    gets a few hundred kilobytes of pooled indices instead of tens of
    megabytes of box mesh.
    """
    import numpy as np

    if factor <= 1:
        return labels, labels.shape[0]
    size = labels.shape[0] // factor
    trimmed = labels[: size * factor, : size * factor, : size * factor]
    blocks = trimmed.reshape(size, factor, size, factor, size, factor)
    blocks = blocks.transpose(0, 2, 4, 1, 3, 5).reshape(size, size, size, -1)

    result = np.zeros((size, size, size), dtype=np.int16)
    # Majority vote ignoring empties, so a mostly-empty block that contains
    # any part still reports that part rather than vanishing.
    highest = int(labels.max())
    if highest > 0:
        counts = np.zeros((size, size, size, highest + 1), dtype=np.int16)
        for value in range(1, highest + 1):
            counts[..., value] = (blocks == value).sum(axis=-1)
        winner = counts.argmax(axis=-1).astype(np.int16)
        result = np.where(counts.max(axis=-1) > 0, winner, 0)
    return result, size


def geodesic(mask: Any, seed: Any) -> Any:
    """Hop distance from a seed set, measured *inside* a mask.

    Returns -1 where the mask cannot be reached from the seed. Unweighted
    6-connected hops rather than true Euclidean geodesics: what every caller
    here asks is "which voxel of this part is farthest from where it attaches",
    and an ordering is enough for that. The same array shift trick as
    `watershed`, for the same reason -- a per-voxel queue is seconds where this
    is milliseconds.
    """
    import numpy as np

    distance = np.full(mask.shape, -1, dtype=np.int32)
    current = mask & seed
    if not current.any():
        return distance
    distance[current] = 0
    step = 0
    while True:
        step += 1
        following = np.zeros_like(current)
        for axis, delta in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
            shifted = np.roll(current, delta, axis=axis)
            view = [slice(None)] * 3
            view[axis] = 0 if delta > 0 else -1
            shifted[tuple(view)] = False
            following |= shifted
        following &= mask & (distance < 0)
        if not following.any():
            return distance
        distance[following] = step
        current = following


def farthest(mask: Any, seed: Any) -> tuple[int, int, int]:
    """The voxel of `mask` at greatest hop distance from `seed`."""
    import numpy as np

    distance = geodesic(mask, seed)
    reached = np.where(distance < 0, -1, distance)
    return tuple(  # type: ignore[return-value]
        int(value) for value in np.unravel_index(int(reached.argmax()), mask.shape)
    )


def interfaces(labels: Any) -> dict[frozenset[int], Any]:
    """Every pair of touching parts, with the voxel face positions between them.

    A "contact" is a 6-connected face whose two voxels carry different non-zero
    labels. The returned position is the face centre in fractional voxel
    coordinates, so an interface is located between the two parts rather than
    inside one of them.
    """
    import numpy as np

    found: dict[frozenset[int], list[Any]] = {}
    for axis in (0, 1, 2):
        near = labels.take(range(labels.shape[axis] - 1), axis=axis)
        far = labels.take(range(1, labels.shape[axis]), axis=axis)
        touching = (near > 0) & (far > 0) & (near != far)
        if not touching.any():
            continue
        positions = np.argwhere(touching).astype(float)
        positions[:, axis] += 0.5
        keys = np.stack(
            [
                np.minimum(near[touching], far[touching]),
                np.maximum(near[touching], far[touching]),
            ],
            axis=1,
        )
        for pair in np.unique(keys, axis=0):
            selected = (keys == pair).all(axis=1)
            key = frozenset(int(value) for value in pair)
            found.setdefault(key, []).append(positions[selected])
    return {key: np.vstack(chunks) for key, chunks in found.items()}
