# Implementation — Donor Skeleton Extraction And Viewer

## Progress

`▰▱▱▱▱▱ Phase 1/6` — contracts are folded; Blender/Python extraction is in progress.

## 2026-08-28 — Extraction Contract

- Opened the packet after the maintainer requested faithful extraction and
  browser inspection before any skeleton creation work.
- Settled separate `charctx.skeleton/v1` and `charctx.skin-weights/v1` JSON
  artifacts, dual coordinate spaces, declared web serving, and strict
  non-goals around normalization, interpolation, and canonical design.
- Folded the durable artifact, CLI, and viewer behavior into the binding specs
  and documented `charctx assets build` as the explicit production command.
