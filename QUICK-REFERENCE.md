# 🚀 Agent Quick Reference

One-page cheat sheet for agent orchestration.

---

## ❌ When NOT to Use Agents

**Use direct tools for simple tasks** - agents add overhead:

- **Reading specific files** → Use Read tool directly
- **Finding files by pattern** → Use Glob tool directly
- **Searching code in 1-3 files** → Use Read tool directly
- **Quick grep/search** → Use Grep tool directly

**Use agents for:**
- Complex multi-step tasks
- Analysis requiring expertise
- Code generation/modification
- Debugging mysterious issues

---

## Single Agent Tasks

**Common Agents:**
```text
python-code-reviewer          # Review code for bugs, style, design issues
type-system-expert           # Add/fix type annotations, resolve type errors
test-development-master      # Write tests, TDD, coverage analysis
deep-debugger               # Investigate mysterious/complex bugs
threading-debugger          # Fix deadlocks, race conditions, threading bugs
performance-profiler        # Find bottlenecks, optimize performance
code-refactoring-expert     # Improve code structure, remove duplication
python-expert-architect     # Design architecture, async/concurrency patterns
python-implementation-specialist  # Implement features, write code
qt-concurrency-architect    # Qt threading, signals/slots across threads
qt-ui-modernizer           # Modernize Qt UI/UX
qt-modelview-painter       # Custom Qt widgets, Model/View patterns
ui-ux-validator            # Validate Qt UI for usability/accessibility
venv-keeper                # Manage venv, dependencies, ruff, basedpyright
```

**Specialized Agents:**
```text
api-documentation-specialist     # API design, documentation generation
coverage-gap-analyzer           # Identify capability gaps in codebase
best-practices-checker          # Verify modern Python/Qt best practices
agent-audit-orchestrator        # Coordinate comprehensive code audits
test-type-safety-specialist     # Type-safe test code and fixtures
```

---

## Common Workflows (Copy-Paste)

**User Prompts** - Copy these to your chat with Claude:

### Development
```text
# TDD new feature
"Use TDD: test-development-master writes tests, python-implementation-specialist implements, python-code-reviewer reviews"

# Quick implementation
"Use python-implementation-specialist to implement [feature], then python-code-reviewer to review"

# Qt application
"Use python-expert-architect to design, python-implementation-specialist to implement, qt-ui-modernizer for UI"
```

### Debugging
```text
# Fix bug
"Use deep-debugger to find root cause of [bug], then python-implementation-specialist to fix"

# Threading issue
"Use threading-debugger to analyze [concurrency bug]"
# OR for Qt: "Use qt-concurrency-architect to fix Qt threading in [component]"
```

### Quality
```text
# Parallel review (60% FASTER!)
"Use python-code-reviewer and type-system-expert in parallel to analyze [file]"

# Comprehensive audit
"Use python-code-reviewer, type-system-expert, performance-profiler, test-development-master in parallel to audit [module]"

# Refactor safely
"Use test-development-master to add tests, code-refactoring-expert to refactor, python-code-reviewer to verify"
```

### Performance
```text
"Use performance-profiler to find bottlenecks, python-expert-architect to design optimizations, python-implementation-specialist to implement"
```

### Types
```text
# Add types
"Use type-system-expert to add comprehensive type annotations to [module]"

# Fix type errors
"Use type-system-expert to fix basedpyright errors in [file]"

# Python 3.13+ modernization
"Use type-system-expert to update [module] with TypeIs and ReadOnly TypedDict"
```

### Environment
```text
# Setup
"Use venv-keeper to setup Python 3.13 environment with ruff, basedpyright, pytest"

# Update deps
"Use venv-keeper to update dependencies and check for vulnerabilities"
```

---

## Decision Matrix

| I need to...                    | Use this agent                              | What you get                          |
|---------------------------------|---------------------------------------------|---------------------------------------|
| Fix a bug                       | deep-debugger                               | Root cause analysis + fix strategy    |
| Threading/deadlock              | threading-debugger (or qt-concurrency-architect for Qt) | Thread analysis + deadlock fix |
| Add feature (TDD)               | test-development-master → python-implementation-specialist | Tests + implementation + coverage |
| Add feature (direct)            | python-implementation-specialist            | Working code implementation           |
| Review code                     | python-code-reviewer                        | Bug/style/design issue report         |
| Add/fix types                   | type-system-expert                          | Type annotations + fixes              |
| Refactor messy code             | code-refactoring-expert                     | Improved code structure               |
| Optimize performance            | performance-profiler                        | Bottleneck analysis + metrics         |
| Design architecture             | python-expert-architect                     | Architecture design + patterns        |
| Build Qt UI                     | qt-ui-modernizer                            | Modern Qt UI code                     |
| Custom Qt widget                | qt-modelview-painter                        | Custom widget implementation          |
| Qt threading issues             | qt-concurrency-architect                    | Qt-safe threading solution            |
| Setup/update environment        | venv-keeper                                 | Configured venv + tools               |
| Write/improve tests             | test-development-master                     | Test suite + coverage report          |
| Modernize to Python 3.13+       | type-system-expert + test-development-master | Modern types + async fixture fixes   |

---

## Parallel Patterns (60% Faster!)

**Default to parallel when tasks are independent** - saves 50-70% time:

```text
# Code analysis (60% faster than sequential)
"Use python-code-reviewer and type-system-expert in parallel to analyze [file]"

# Complete audit (3-5x faster)
"Use python-code-reviewer, type-system-expert, performance-profiler in parallel to audit [module]"

# Qt review (parallel = 2x faster)
"Use qt-concurrency-architect and ui-ux-validator in parallel to review [Qt app]"
```

**When to use parallel:**
- ✅ Tasks don't depend on each other's output
- ✅ Analyzing same code from different perspectives
- ✅ Multiple verification/validation steps

**When to use sequential:**
- ⛔ Agent 2 needs Agent 1's findings
- ⛔ Implementation depends on design
- ⛔ Fix depends on debug analysis

---

## Python 3.13+ Quick Wins

**User Prompts:**
```text
# TypeIs (better than TypeGuard)
"Use type-system-expert to replace TypeGuard with TypeIs in [module]"

# ReadOnly TypedDict
"Use type-system-expert to add ReadOnly to immutable TypedDict fields in [config]"

# Pytest 8.4+ async fixtures
"Use test-development-master to fix async fixture deprecation warnings"

# Full modernization
"Modernize for Python 3.13+: type-system-expert updates types, test-development-master fixes async fixtures, venv-keeper updates tools"
```

---

## Pro Tips

✅ **Be specific**: Include file/module names and exact requirements
✅ **Default to parallel**: Run independent agents together - saves 60% time
✅ **Chain logically**: Feed output from one agent to the next explicitly
✅ **Include context**: "Based on [agent1] findings, use [agent2] to..."
✅ **Verify changes**: Always run tests after modifications
✅ **Choose right agent**: Qt issues need Qt agents, not general Python agents
✅ **Provide file paths**: "ui/main_window.py" not "the main file"

❌ **Avoid vague prompts**: "Fix the code" → Which file? Which agent?
❌ **Don't skip verification**: Changes without tests = risky
❌ **Don't mix concerns**: Use specialized agents for specialized tasks
❌ **Don't use agents for simple reads**: Use Read/Glob tools for file operations

---

## Emergency Commands

**User Prompts:**
```text
# Critical bug in production
"Use deep-debugger to analyze [production bug], python-implementation-specialist to hotfix, test-development-master to add regression test"

# Performance crisis
"Use performance-profiler to identify critical bottlenecks in [slow component]"

# Type errors blocking deployment
"Use type-system-expert to fix all basedpyright errors in [module] immediately"

# Tests failing before release
"Use test-development-master to diagnose and fix failing tests in [test suite]"
```

---

**See ORCHESTRATION.md for detailed recipes and explanations**
