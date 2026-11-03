# db/views/ — Views

`VIEWS_DIR`. One file per view, named after the view: `vw_<Name>.sql` (for example `vw_FooSummary.sql`).

## Rules

- Written only by `db-developer`.
- Use `CREATE OR ALTER VIEW dbo.vw_...`; schema-qualified names; explicit column lists (no `SELECT *`).
- Header comment: purpose, columns/types, requirement ID (`DB-n`). A change to the column list changes the contract → it goes back to `db-developer` as a fix.
- Do not put `ORDER BY` in a view unless it is required by `TOP`/`OFFSET`; ordering belongs in the consuming query.
- Runs unchanged in SSMS (`GO` separators).
