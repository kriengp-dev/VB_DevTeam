# test/Frontend/

Test project of `vb-frontend-tester`: presenter (WinForms MVP), view model (WPF MVVM), and MVC 5 controller tests; optional UI automation (FlaUI) and browser tests for critical flows.

- Framework: MSTest (net48) + Moq unless the plan or an existing project says otherwise; ask before adding a NuGet package.
- Tag every test class `<TestCategory("Frontend")>` (`"E2E"` for automation).
- References the customer's projects by relative path; not part of the customer's solution.
