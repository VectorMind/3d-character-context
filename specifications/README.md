# Specifications

Use this directory for durable, spec-driven requirements.

Create one folder per specification:

```text
specifications/<slug>/spec.md
```

Specifications should describe the problem, intended behavior, constraints,
interfaces, acceptance criteria, and non-goals. Keep implementation schedules
and running notes in `plans/` instead.

## Current Specifications

None yet. The initial bringup packet
(`plans/2026-08/25-initial-bringup/plan.md`) is expected to fold its accepted
decisions into first specs covering, at minimum:

- workspace layout and output locations;
- the agent interface (single documented CLI plus side-effect-free Python
  API);
- the generator-backend contract (request/response models, registry,
  isolation of provider-native responses);
- mesh measurement and verification rules;
- canonical asset conventions (coordinate system, scale, orientation,
  naming, landmark and skeleton schemas) — required before any non-rigid
  fitting work begins.
