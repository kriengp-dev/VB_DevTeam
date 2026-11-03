# test/ — Test Code (Claude area)

`TEST_DIR` (declared in `.claude/rules/PATH.md`). All test projects and test files written by the testers live here, **not in the customer area**, so no test content is mixed into the customer's program:

```text
test/
├── README.md          (this file)
├── .gitignore         ignores bin/, obj/, TestResults/, packages/
├── Backend/           test project of vb-backend-tester (unit + integration + Web API 2 tests)
└── Frontend/          test project of vb-frontend-tester (presenter / view model / controller tests, UI automation)
```

## Rules

- **Only the testers write here** (`vb-backend-tester` → `Backend\`, `vb-frontend-tester` → `Frontend\`): one test project each, so parallel testers never edit the same project file.
- A test project references the customer's projects **by relative path** (`<ProjectReference Include="..\..\..\<path>\Customer.vbproj" />`) or by the built assembly. It is **never added to the customer's `.sln`**, and nothing in the customer area is created or changed.
- Build and run the test project's own `.vbproj` with MSBuild and VSTest (see `ENVIRONMENT.md`); results are quoted from real runs.
- Tests the customer already has in the customer area are read-only reference.
- If a test needs something the customer's code does not expose (`InternalsVisibleTo`, a seam, an `AutomationId`), report it under **Issues** so the orchestrator routes a fix to the developer agent — never edit the customer area from here.
- Integration tests use a dedicated test database (connection string from the `VB_TEST_DB` environment variable); never put passwords or real connection strings in a test file.
- Commit test code as `test:` (Claude area), separate from customer-area commits.
