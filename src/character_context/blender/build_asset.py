"""Inspect, export, and render one asset inside Blender.

This file is executed by Blender's bundled Python, not the workspace Python.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

NAME_SIGNAL_TERMS = (
    "spine",
    "neck",
    "head",
    "jaw",
    "tail",
    "wing",
    "finger",
    "thigh",
    "shin",
    "foot",
    "toe",
    "eye",
)


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source")
    return parser.parse_args(argv)


def import_source(source: Path) -> None:
    # Blender's factory-startup scene contains a cube, camera, and light.
    # Imported donor formats must start from an empty scene so those defaults
    # cannot leak into the measured/exported browser derivative.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    extension = source.suffix.lower()
    if extension == ".fbx":
        if hasattr(bpy.ops.wm, "fbx_import"):
            bpy.ops.wm.fbx_import(filepath=str(source))
        else:
            bpy.ops.import_scene.fbx(filepath=str(source))
    elif extension in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(source))
    elif extension == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(source))
        else:
            bpy.ops.import_scene.obj(filepath=str(source))
    else:
        raise RuntimeError(f"Unsupported Blender import format: {extension}")


def mesh_bounds() -> tuple[Vector, Vector]:
    points: list[Vector] = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        obj.hide_render = False
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("The scene contains no mesh objects.")
    minimum = Vector(min(point[i] for point in points) for i in range(3))
    maximum = Vector(max(point[i] for point in points) for i in range(3))
    return minimum, maximum


def matrix_rows(matrix) -> list[list[float]]:
    return [[float(matrix[row][column]) for column in range(4)] for row in range(4)]


def viewer_point(point: Vector) -> list[float]:
    """Convert Blender world coordinates to exported glTF model coordinates."""
    return [float(point.x), float(point.z), float(-point.y)]


def bone_depth(bone) -> int:
    depth = 0
    parent = bone.parent
    while parent is not None:
        depth += 1
        parent = parent.parent
    return depth


def extract_skeleton(asset_id: str, source_model: str) -> dict | None:
    armatures = []
    for obj in sorted(
        (item for item in bpy.data.objects if item.type == "ARMATURE"),
        key=lambda item: item.name,
    ):
        bones = []
        endpoints = []
        for bone in obj.data.bones:
            head_world = obj.matrix_world @ bone.head_local
            tail_world = obj.matrix_world @ bone.tail_local
            head = viewer_point(head_world)
            tail = viewer_point(tail_world)
            endpoints.extend((head, tail))
            bones.append(
                {
                    "name": bone.name,
                    "parent": bone.parent.name if bone.parent else None,
                    "deform": bool(bone.use_deform),
                    "connected": bool(bone.use_connect),
                    "depth": bone_depth(bone),
                    "head": head,
                    "tail": tail,
                    "head_local": [float(value) for value in bone.head_local],
                    "tail_local": [float(value) for value in bone.tail_local],
                    "length": float((tail_world - head_world).length),
                    "roll": float(bone.matrix_local.to_euler("XYZ").y),
                    "matrix_local": matrix_rows(bone.matrix_local),
                }
            )
        if not bones:
            continue
        names = [bone["name"] for bone in bones]
        lowered = [name.lower() for name in names]
        bounds_min = [min(point[axis] for point in endpoints) for axis in range(3)]
        bounds_max = [max(point[axis] for point in endpoints) for axis in range(3)]
        parent_names = {bone["parent"] for bone in bones if bone["parent"]}
        armatures.append(
            {
                "name": obj.name,
                "pose_position": obj.data.pose_position,
                "object_matrix": matrix_rows(obj.matrix_world),
                "bones": bones,
                "roots": [bone["name"] for bone in bones if bone["parent"] is None],
                "leaves": [name for name in names if name not in parent_names],
                "max_depth": max(bone["depth"] for bone in bones),
                "bounds_min": bounds_min,
                "bounds_max": bounds_max,
                "total_length": sum(bone["length"] for bone in bones),
                "deform_total_length": sum(
                    bone["length"] for bone in bones if bone["deform"]
                ),
                "name_signals": {
                    term: sum(term in name for name in lowered)
                    for term in NAME_SIGNAL_TERMS
                },
            }
        )
    if not armatures:
        return None
    all_bones = [bone for armature in armatures for bone in armature["bones"]]
    return {
        "schema": "charctx.skeleton/v1",
        "asset_id": asset_id,
        "blender_version": bpy.app.version_string,
        "source_model": source_model,
        "coordinate_system": {
            "viewer_space": "right-handed, +Y up, -Z forward",
            "source_space": "Blender armature-local and Blender world",
            "blender_world_to_viewer": "[x, z, -y]",
            "scale": "source scene units; no normalization",
            "pose": "armature rest pose",
        },
        "armatures": armatures,
        "summary": {
            "armatures": len(armatures),
            "bones": len(all_bones),
            "deform_bones": sum(bone["deform"] for bone in all_bones),
            "roots": sum(len(armature["roots"]) for armature in armatures),
            "leaves": sum(len(armature["leaves"]) for armature in armatures),
            "max_depth": max(armature["max_depth"] for armature in armatures),
        },
    }


def extract_skin_weights(asset_id: str, source_model: str) -> dict | None:
    bindings = []
    for obj in sorted(
        (item for item in bpy.data.objects if item.type == "MESH"),
        key=lambda item: item.name,
    ):
        armature = next(
            (
                modifier.object
                for modifier in obj.modifiers
                if modifier.type == "ARMATURE"
                and modifier.object is not None
                and modifier.object.type == "ARMATURE"
            ),
            None,
        )
        if armature is None:
            continue
        bone_names = [bone.name for bone in armature.data.bones]
        bone_lookup = {name: index for index, name in enumerate(bone_names)}
        group_to_bone = {
            group.index: bone_lookup[group.name]
            for group in obj.vertex_groups
            if group.name in bone_lookup
        }
        vertex_offsets = [0]
        bone_indices = []
        weights = []
        weighted_vertices = 0
        max_influences = 0
        max_weight_sum_error = 0.0
        non_bone_assignments = 0
        for vertex in obj.data.vertices:
            influences = []
            for assignment in vertex.groups:
                bone_index = group_to_bone.get(assignment.group)
                if bone_index is None:
                    non_bone_assignments += 1
                    continue
                weight = float(assignment.weight)
                if weight > 0 and math.isfinite(weight):
                    influences.append((bone_index, weight))
            influences.sort(key=lambda item: item[0])
            if influences:
                weighted_vertices += 1
                max_weight_sum_error = max(
                    max_weight_sum_error,
                    abs(sum(weight for _, weight in influences) - 1.0),
                )
            max_influences = max(max_influences, len(influences))
            bone_indices.extend(index for index, _ in influences)
            weights.extend(weight for _, weight in influences)
            vertex_offsets.append(len(bone_indices))
        bindings.append(
            {
                "mesh": obj.name,
                "armature": armature.name,
                "vertices": len(obj.data.vertices),
                "bone_names": bone_names,
                "vertex_offsets": vertex_offsets,
                "bone_indices": bone_indices,
                "weights": weights,
                "weighted_vertices": weighted_vertices,
                "unweighted_vertices": len(obj.data.vertices) - weighted_vertices,
                "influence_count": len(weights),
                "max_influences": max_influences,
                "max_weight_sum_error": max_weight_sum_error,
                "non_bone_assignments": non_bone_assignments,
            }
        )
    if not bindings:
        return None
    return {
        "schema": "charctx.skin-weights/v1",
        "asset_id": asset_id,
        "source_model": source_model,
        "encoding": "csr-per-vertex",
        "bindings": bindings,
        "summary": {
            "bindings": len(bindings),
            "vertices": sum(binding["vertices"] for binding in bindings),
            "weighted_vertices": sum(
                binding["weighted_vertices"] for binding in bindings
            ),
            "unweighted_vertices": sum(
                binding["unweighted_vertices"] for binding in bindings
            ),
            "influences": sum(binding["influence_count"] for binding in bindings),
            "max_influences": max(binding["max_influences"] for binding in bindings),
            "max_weight_sum_error": max(
                binding["max_weight_sum_error"] for binding in bindings
            ),
            "non_bone_assignments": sum(
                binding["non_bone_assignments"] for binding in bindings
            ),
        },
    }


def inspect_scene() -> dict:
    meshes = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        weighted = sum(
            1
            for vertex in obj.data.vertices
            if any(group.weight > 0 for group in vertex.groups)
        )
        meshes.append(
            {
                "name": obj.name,
                "data": obj.data.name,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "materials": [
                    material.name for material in obj.data.materials if material
                ],
                "vertex_groups": len(obj.vertex_groups),
                "weighted_vertices": weighted,
                "armature_modifiers": [
                    modifier.object.name if modifier.object else None
                    for modifier in obj.modifiers
                    if modifier.type == "ARMATURE"
                ],
            }
        )
    armatures = [
        {
            "name": obj.name,
            "bones": len(obj.data.bones),
            "deform_bones": sum(1 for bone in obj.data.bones if bone.use_deform),
            "bone_names": [bone.name for bone in obj.data.bones],
        }
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
    ]
    actions = [
        {
            "name": action.name,
            "frame_range": [float(action.frame_range[0]), float(action.frame_range[1])],
        }
        for action in bpy.data.actions
        if float(action.frame_range[1]) > float(action.frame_range[0])
    ]
    images = []
    warnings = []
    for image in bpy.data.images:
        if image.source == "VIEWER":
            continue
        absolute = bpy.path.abspath(image.filepath) if image.filepath else ""
        exists = bool(image.packed_file) or (
            bool(absolute) and Path(absolute).is_file()
        )
        images.append(
            {
                "name": image.name,
                "source": image.source,
                "filepath": image.filepath,
                "packed": image.packed_file is not None,
                "exists": exists,
                "size": [int(image.size[0]), int(image.size[1])],
            }
        )
        if image.filepath and not exists:
            warnings.append(f"Missing external image: {image.filepath}")
    minimum, maximum = mesh_bounds()
    return {
        "blender_version": bpy.app.version_string,
        "objects": {
            "total": len(bpy.data.objects),
            "types": {
                object_type: sum(
                    1 for obj in bpy.data.objects if obj.type == object_type
                )
                for object_type in sorted({obj.type for obj in bpy.data.objects})
            },
        },
        "meshes": meshes,
        "armatures": armatures,
        "actions": actions,
        "materials": [material.name for material in bpy.data.materials],
        "images": images,
        "bounds": {
            "min": list(minimum),
            "max": list(maximum),
            "extents": list(maximum - minimum),
        },
        "warnings": sorted(set(warnings)),
    }


def add_area(
    name: str,
    position: Vector,
    energy: float,
    size: float,
    color: tuple[float, float, float],
):
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (
        (Vector((0, 0, 0)) - position).to_track_quat("-Z", "Y").to_euler()
    )
    return obj


def setup_studio(center: Vector, radius: float):
    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            obj.hide_render = True
    world = bpy.data.worlds.new("charctx_studio_world")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.012, 0.018, 0.03, 1.0)
    background.inputs["Strength"].default_value = 0.35
    bpy.context.scene.world = world
    offset = max(radius, 1.0)
    add_area(
        "charctx_key",
        center + Vector((2.2, -2.5, 2.8)) * offset,
        1400 * offset * offset,
        2.5 * offset,
        (1.0, 0.84, 0.7),
    )
    add_area(
        "charctx_fill",
        center + Vector((-2.5, -0.5, 1.4)) * offset,
        850 * offset * offset,
        3.0 * offset,
        (0.45, 0.65, 1.0),
    )
    add_area(
        "charctx_rim",
        center + Vector((0.4, 2.7, 2.0)) * offset,
        1100 * offset * offset,
        2.0 * offset,
        (0.6, 0.78, 1.0),
    )
    camera_data = bpy.data.cameras.new("charctx_camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("charctx_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def render_views(output: Path) -> None:
    minimum, maximum = mesh_bounds()
    center = (minimum + maximum) * 0.5
    extents = maximum - minimum
    radius = max(float(extents.length) * 0.5, 0.1)
    camera = setup_studio(center, radius)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.image_settings.quality = 92
    scene.render.filepath = ""
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    preview_material = bpy.data.materials.new("charctx_preview_material")
    preview_material.diffuse_color = (0.32, 0.38, 0.48, 1.0)
    preview_material.use_nodes = True
    principled = preview_material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = (0.18, 0.24, 0.34, 1.0)
        principled.inputs["Metallic"].default_value = 0.08
        principled.inputs["Roughness"].default_value = 0.62
    bpy.context.view_layer.material_override = preview_material
    for look in ("Medium High Contrast", "AgX - Medium High Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
    views = {
        "hero": Vector((1.35, -1.55, 0.9)),
        "front": Vector((0.0, -1.0, 0.08)),
        "left": Vector((-1.0, 0.0, 0.08)),
        "rear": Vector((0.0, 1.0, 0.08)),
        "top": Vector((0.0, 0.001, 1.0)),
    }
    preview_dir = output / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for name, direction in views.items():
        direction.normalize()
        distance = radius * 3.0
        camera.location = center + direction * distance
        camera.rotation_euler = (
            (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        camera.data.ortho_scale = max(float(extents.length) * 1.12, 0.5)
        camera.data.clip_start = max(radius / 1000.0, 0.001)
        camera.data.clip_end = radius * 20.0
        scene.render.filepath = str(preview_dir / f"{name}.webp")
        bpy.ops.render.render(write_still=True)


def export_glb(output: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    for obj in bpy.data.objects:
        if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
            obj.select_set(True)
            selected.append(obj)
    if not selected:
        raise RuntimeError("Nothing selectable for GLB export.")
    bpy.context.view_layer.objects.active = selected[0]
    bpy.ops.export_scene.gltf(
        filepath=str(output / "model.glb"),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
    )


def main() -> None:
    args = arguments()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if args.source:
        import_source(Path(args.source))
    source_model = (
        Path(args.source).name if args.source else Path(bpy.data.filepath).name
    )
    report = inspect_scene()
    skeleton = extract_skeleton(args.asset_id, source_model)
    skin_weights = extract_skin_weights(args.asset_id, source_model)
    if skeleton:
        (output / "skeleton.json").write_text(
            json.dumps(skeleton, indent=2), encoding="utf-8"
        )
    if skin_weights:
        (output / "skin-weights.json").write_text(
            json.dumps(skin_weights, separators=(",", ":")), encoding="utf-8"
        )
    export_glb(output)
    render_views(output)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        "CHARCTX_ASSET_BUILD="
        + json.dumps({"asset_id": args.asset_id, "output": str(output)})
    )


if __name__ == "__main__":
    main()
