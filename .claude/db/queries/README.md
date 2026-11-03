# db/queries/ — Ad-hoc and Report Queries

`QUERIES_DIR`. Queries that are not part of the schema: investigation queries, report queries, tuning experiments, data checks.

## Rules

- Written only by `db-developer`.
- **Read-only by default:** `SELECT` and catalog/DMV queries only. A script that changes data or schema belongs in `../migrations/`, not here.
- Name files by purpose: `report_<name>.sql`, `check_<name>.sql`, `tune_<name>.sql`.
- Header comment: purpose, target database, parameters, requirement ID (`DB-n`) if it backs a feature.
- Parameterize with declared variables; never concatenate input into dynamic SQL (use `sp_executesql` with parameters).
- Measure tuning work with `SET STATISTICS IO, TIME ON` and record before/after in your final report.
- Runs unchanged in SSMS.
