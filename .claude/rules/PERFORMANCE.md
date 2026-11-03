# Claude Tool Strategy

> How to select Claude models and manage context effectively in this repo.
> For application performance guidelines (ADO.NET/EF6 queries, SQL Server Express limits, caching, pagination), see `vb-reviewer` (MEDIUM — Performance) and `db-developer` (Step 4 — Query Writing and Tuning).

## Model Selection Strategy

**Haiku** (cost-efficient, lightweight):
- Frequently invoked helper agents
- Simple code generation and formatting tasks
- Worker agents in multi-agent pipelines

**Sonnet** (best coding model — default):
- Research: `vb-researcher`
- Main development work: `vb-backend-developer`, `vb-frontend-developer`, `db-developer`
- Test writing: `vb-backend-tester`, `vb-frontend-tester`
- Review and analysis: `vb-reviewer`, `vb-analyzer`
- Orchestrating multi-agent workflows

**Opus** (deepest reasoning):
- `vb-planner` — architecture, schema, and API contract decisions
- `vb-requirement-analysis` — requirement-to-code traceability judgments
- Maximum reasoning requirements (e.g., concurrency or transaction-isolation analysis)

The model for each agent is set in its frontmatter (`model:`) in `<AGENTS_DIR>/`; change it there, not per call.

## Context Window Management

Avoid the last 20% of the context window for:
- Large-scale refactoring spanning multiple projects in a solution
- Feature implementation across many files and layers
- Debugging complex interactions (auth + EF + UI state)

Lower context sensitivity tasks (safe in any context):
- Single-file edits
- Independent utility or helper creation
- Documentation updates
- Simple bug fixes

## Extended Thinking + Plan Mode

Extended thinking is enabled by default, reserving up to 31,999 tokens for internal reasoning.

Control extended thinking via:
- **Toggle**: Option+T (macOS) / Alt+T (Windows/Linux)
- **Config**: Set `alwaysThinkingEnabled` in `~/.claude/settings.json`
- **Budget cap**: `export MAX_THINKING_TOKENS=10000`
- **Verbose mode**: Ctrl+O to see thinking output

For complex tasks requiring deep reasoning:
1. Ensure extended thinking is enabled (on by default)
2. Enable **Plan Mode** for a structured approach
3. Use multiple critique rounds for thorough analysis
4. Use split-role sub-agents for diverse perspectives
