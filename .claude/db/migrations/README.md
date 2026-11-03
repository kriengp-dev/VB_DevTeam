# db/migrations/ — Ordered Schema Changes

`MIGRATIONS_DIR`. One file per schema or data change, applied in order.

## Naming

```
V<NNN>__<short_name>.sql          forward script        V001__create_foos.sql
V<NNN>__<short_name>.down.sql     reverse script        V001__create_foos.down.sql
```

`<NNN>` is a zero-padded sequence number; take the next free number, never reuse or renumber one.

## Rules

- Written only by `db-developer`.
- **Never edit a migration that was already applied** — add a new `V<NNN+1>` file instead.
- Every forward script has a reverse (`.down.sql`) script.
- Idempotent where possible (`IF OBJECT_ID(...) IS NULL`, `COL_LENGTH(...)`, `IF NOT EXISTS`); data changes in a transaction with `TRY…CATCH` and `SET XACT_ABORT ON`.
- Header comment: purpose, target database, requirement ID (`DB-n`).
- Runs unchanged in SSMS (`GO` separators).
