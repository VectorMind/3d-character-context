"""Voxelization dissolves shell soup, and the flood respects the volume.

The packet's central claim is that disconnected shells stop mattering once the
substrate is a grid. That is asserted here against a mesh built to be soup on
purpose, rather than asserted in prose.
"""

from __future__ import annotations

import numpy as np
import pytest
import trimesh

from character_context import voxels
from character_context.config import ConfigError


def sphere_scene(radius: float = 1.0) -> trimesh.Scene:
    ball = trimesh.creation.icosphere(subdivisions=3, radius=radius)
    return trimesh.Scene({"ball": ball})


def soup_scene() -> trimesh.Scene:
    """Two boxes that touch, exported as separate disconnected geometries.

    A surface method sees two objects with no shared edge. A grid sees one
    solid, which is the whole point.
    """
    left = trimesh.creation.box(extents=(2, 1, 1))
    right = trimesh.creation.box(extents=(2, 1, 1))
    right.apply_translation((1.9, 0, 0))
    return trimesh.Scene({"left": left, "right": right})


def test_a_closed_surface_is_filled_not_merely_outlined() -> None:
    grid, report = voxels.voxelize(sphere_scene(), resolution=48)

    # A hollow shell would leave the centre empty; a filled sphere does not.
    centre = grid.resolution // 2
    assert grid.solid[centre, centre, centre]
    assert report["solid_voxels"] > report["shell_voxels_closed"]
    assert report["solid_components"] == 1


def test_disconnected_shells_become_one_solid_component() -> None:
    """The claim the whole packet rests on."""
    scene = soup_scene()
    assert len(scene.geometry) == 2

    _, report = voxels.voxelize(scene, resolution=48)

    assert report["solid_components"] == 1


def test_world_and_index_coordinates_round_trip() -> None:
    grid, _ = voxels.voxelize(sphere_scene(), resolution=32)
    indices = np.argwhere(grid.solid)[:50]

    recovered = grid.to_index(grid.to_world(indices))

    assert np.array_equal(recovered, indices)


def test_the_flood_claims_every_solid_voxel_from_one_seed() -> None:
    grid, _ = voxels.voxelize(sphere_scene(), resolution=32)
    centre = grid.resolution // 2
    seeds = np.zeros(grid.solid.shape, dtype=np.int16)
    seeds[centre, centre, centre] = 7

    labels, rounds = voxels.watershed(grid, seeds)

    assert rounds > 0
    assert (labels[grid.solid] == 7).all()
    assert not labels[~grid.solid].any()


def test_the_flood_splits_a_volume_at_the_midpoint_between_two_seeds() -> None:
    """Each voxel takes its nearest seed measured through the solid."""
    grid, _ = voxels.voxelize(sphere_scene(), resolution=40)
    solid = np.argwhere(grid.solid)
    low = solid[solid[:, 0].argmin()]
    high = solid[solid[:, 0].argmax()]
    seeds = np.zeros(grid.solid.shape, dtype=np.int16)
    seeds[tuple(low)] = 1
    seeds[tuple(high)] = 2

    labels, _ = voxels.watershed(grid, seeds)

    assert (labels[grid.solid] > 0).all()
    one = np.argwhere(labels == 1)
    two = np.argwhere(labels == 2)
    # The seed nearer the low end owns the low end.
    assert one[:, 0].mean() < two[:, 0].mean()
    # Roughly balanced: a symmetric shape split by symmetric seeds.
    assert 0.35 < len(one) / (len(one) + len(two)) < 0.65


def test_a_seed_outside_the_solid_is_pushed_in_rather_than_dropped() -> None:
    """A landmark sits on the surface; rounding can put it just outside."""
    grid, _ = voxels.voxelize(sphere_scene(), resolution=32)
    outside = np.asarray([[10.0, 10.0, 10.0]])

    seeds = voxels.seed_labels(grid, outside, np.asarray([3]))

    assert (seeds == 3).sum() == 1
    assert grid.solid[tuple(np.argwhere(seeds == 3)[0])]


def test_a_split_part_is_counted_as_more_than_one_component() -> None:
    labels = np.zeros((8, 8, 8), dtype=np.int16)
    labels[1, 1, 1] = 4
    labels[6, 6, 6] = 4

    assert voxels.component_split(labels, 4) == 2
    assert voxels.component_split(labels, 9) == 0


def test_pooling_keeps_a_part_that_only_partly_fills_a_block() -> None:
    """A mostly-empty block that contains a part must still report it."""
    labels = np.zeros((4, 4, 4), dtype=np.int16)
    labels[0, 0, 0] = 5

    pooled, size = voxels.pool(labels, 2)

    assert size == 2
    assert pooled[0, 0, 0] == 5
    assert pooled.sum() == 5


def test_a_grid_too_coarse_to_mean_anything_is_refused() -> None:
    with pytest.raises(ConfigError, match="too coarse"):
        voxels.voxelize(sphere_scene(), resolution=4)


def test_a_flood_with_no_seed_inside_the_solid_is_refused() -> None:
    grid, _ = voxels.voxelize(sphere_scene(), resolution=32)

    with pytest.raises(ConfigError, match="No seed landed inside"):
        voxels.watershed(grid, np.zeros(grid.solid.shape, dtype=np.int16))
