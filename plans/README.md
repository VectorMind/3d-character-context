# Plans

Use this directory for dated planning packets.

Each plan folder uses this shape:

```text
plans/YYYY-MM/
  DD-<slug>/
    plan.md
    implementation.md
    test.md
```

Add `survey.md` before `plan.md` only when the maintainer explicitly requests
discovery or review before scope is approved. Keep `test.md` as proof of
working behavior, including the commands run, expected results, actual
results, and known gaps.

`open.md` and `closed.md` index the packets: update them whenever a plan is
started or finished.
