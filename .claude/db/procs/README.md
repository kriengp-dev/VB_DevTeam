# db/procs/ — Stored Procedures

`PROCS_DIR`. One file per stored procedure, named after the procedure: `usp_<Verb><Noun>.sql` (for example `usp_GetFooSummary.sql`).

## Rules

- Written only by `db-developer`. The backend calls these procedures (`CommandType.StoredProcedure`) but never edits them.
- Use `CREATE OR ALTER PROCEDURE dbo.usp_...` so the script is re-runnable; `SET NOCOUNT ON`; schema-qualified names; explicit column lists (no `SELECT *`).
- Header comment with the **Query Contract**: parameters, result columns/types, ordering, performance target, requirement ID (`DB-n`). The consuming backend step receives the contract from the `db-developer` step's final report (passed by the orchestrator).
- A change to parameters or result columns changes the contract → it goes back to `db-developer` as a fix, and the dependent backend and test steps are re-run.
- Runs unchanged in SSMS (`GO` separators).
