# test/Backend/

Test project of `vb-backend-tester`: unit tests (services, validators, domain), repository integration tests against the SQL Server Express **test** database, and Web API 2 endpoint tests (in-memory `HttpServer`).

- Framework: MSTest (net48) + Moq unless the plan or an existing project says otherwise; ask before adding a NuGet package.
- Tag every test class `<TestCategory("Backend")>` (`"Integration"` for database tests).
- References the customer's projects by relative path; not part of the customer's solution.
