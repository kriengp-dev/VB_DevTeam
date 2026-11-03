# Target Environment

Single source of truth for the stack every agent works against. If a repo contradicts this file, trust the repo (read the `.vbproj` and config files) and tell the user.

---

## Stack

| Item | Value |
|------|-------|
| Language | **Visual Basic .NET** (`.vb`, `.vbproj`; Razor views `.vbhtml`) |
| Framework | **.NET Framework 4.8** (`net48`, `TargetFrameworkVersion v4.8`) |
| IDE | **Visual Studio 2026 Community** |
| Database | **SQL Server 2025 Express edition** |
| DB management | **SQL Server Management Studio (SSMS)** |
| DB CLI | `sqlcmd` |

Assumed default instance: `.\SQLEXPRESS`. Confirm the server, instance, and database name with the user before connecting.

---

## What this means for code

**.NET Framework 4.8.** NuGet packages must support `net48` or `netstandard2.0`. Check a package's supported frameworks before adding it, and ask before adding any new package.

**Application type is detected, not assumed.** Read the `.vbproj` (`ProjectTypeGuids`, `OutputType`, references to `System.Windows.Forms`, `PresentationFramework`, `System.Web`, `System.Web.Http`, `System.Web.Mvc`) and classify each project:

| Detected | Kind |
|----------|------|
| `System.Windows.Forms`, `*.Designer.vb` | WinForms |
| `PresentationFramework`, `*.xaml` | WPF |
| `System.Web.Http` / `ApiController` | ASP.NET Web API 2 |
| `System.Web.Mvc`, `*.vbhtml` | ASP.NET MVC 5 |
| `*.aspx`, `*.aspx.vb` | ASP.NET WebForms |
| `System.ServiceModel` | WCF |
| `OutputType=Library` | Class library (business / data layer) |

**Data access is detected too:** ADO.NET (`System.Data.SqlClient` or `Microsoft.Data.SqlClient`), Entity Framework 6 (`EntityFramework` package, `DbContext`), or Dapper. Use whatever the repo already uses; never mix a second approach in without asking.

**SQL Server 2025 Express.**
- Express edition limits apply (database size cap, buffer-pool memory cap, CPU cap) and **there is no SQL Server Agent** — schedule jobs with Windows Task Scheduler or the application. Check Microsoft's current edition limits before designing for volume.
- Use the database's actual compatibility level; check with `SELECT name, compatibility_level FROM sys.databases`. Do not rely on SQL Server 2025-only features unless the compatibility level and the user's intent allow it.
- All SQL must run unchanged in SSMS (use `GO` batch separators; no `sqlcmd`-only variables unless the script says so).
- `sqlcmd` (ODBC 18+) encrypts by default; for a local Express instance with a self-signed certificate add `-C` (trust server certificate) in dev only.
- Connection strings: prefer Windows Integrated Security; never commit passwords. Keep real connection strings out of source control (`configSource`, environment-specific transforms, or environment variables).

---

## VB.NET conventions

- Every project and file: `Option Strict On`, `Option Explicit On` (verify in the `.vbproj`); never turn them off to silence an error.
- Use short-circuit `AndAlso` / `OrElse`, never `And` / `Or`, for conditions.
- `Is Nothing` / `IsNot Nothing` for null checks; `String.IsNullOrWhiteSpace` for strings.
- `Using` for every `IDisposable` (connections, commands, readers, streams, forms shown with `ShowDialog`).
- `Await` all async I/O; never `.Result` / `.Wait()` (deadlocks on UI and ASP.NET synchronization contexts). Use `.ConfigureAwait(False)` in library code. `Async Sub` only for event handlers.
- Rethrow with `Throw`, never `Throw ex` (loses the stack trace).
- No `On Error` statements, no late binding, no `Module`-level mutable global state.
- Parameterized SQL only (`cmd.Parameters.Add(name, SqlDbType).Value = x`); avoid `AddWithValue`; never concatenate input into SQL.
- XML doc comments with `'''` on public members; names in PascalCase, private fields `_camelCase`.
- Use `NameOf(...)` instead of magic strings.

---

## Build, test, and format commands

Visual Studio 2026 is the IDE, so use **MSBuild** for legacy (non-SDK-style) `.vbproj` files. First identify the project style: SDK-style has `<Project Sdk="Microsoft.NET.Sdk">`; legacy has `<Project ToolsVersion=...>` and usually `packages.config`.

```powershell
# Locate MSBuild from Visual Studio 2026
$msbuild = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" | Select-Object -First 1

# Restore NuGet packages (legacy / packages.config)
nuget restore <GIT_REPO>\<Solution>.sln          # or: & $msbuild <sln> -t:Restore

# Build
& $msbuild <GIT_REPO>\<Solution>.sln /p:Configuration=Debug /m /v:minimal

# Run tests (VSTest; path from vswhere, TestWindow\vstest.console.exe)
vstest.console.exe <TestProject>\bin\Debug\<TestProject>.dll /TestCaseFilter:"TestCategory=Backend"
```

- Tests of the program live under `<TEST_DIR>` (`.claude\test\`), not in the customer's solution: build and run the test project's own `.vbproj` (it references the customer's projects by relative path).
- SDK-style test projects targeting `net48` can also use `dotnet test --filter "TestCategory=Backend"`.
- `dotnet format` works only for SDK-style projects; for legacy projects follow `.editorconfig` and Visual Studio's *Format Document* / code cleanup, and say so in the report instead of claiming a format check ran.
- If `nuget`, `vstest.console.exe`, or `sqlcmd` is not on `PATH`, locate it (vswhere, SQL Server install folder) before reporting it missing.
- Report build and test results from actual runs only.
