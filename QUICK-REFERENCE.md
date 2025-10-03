# 🚀 Agent Quick Reference

One-page cheat sheet for agent orchestration.

---

## Single Agent Tasks

```bash
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

---

## Common Workflows (Copy-Paste)

### Development
```bash
# TDD new feature
"Use TDD: test-development-master writes tests, python-implementation-specialist implements, python-code-reviewer reviews"

# Quick implementation
"Use python-implementation-specialist to implement [feature], then python-code-reviewer to review"

# Qt application
"Use python-expert-architect to design, python-implementation-specialist to implement, qt-ui-modernizer for UI"
```

### Debugging
```bash
# Fix bug
"Use deep-debugger to find root cause of [bug], then python-implementation-specialist to fix"

# Threading issue
"Use threading-debugger to analyze [concurrency bug]"
# OR for Qt: "Use qt-concurrency-architect to fix Qt threading in [component]"
```

### Quality
```bash
# Parallel review (FASTER)
"Use python-code-reviewer and type-system-expert in parallel to analyze [file]"

# Comprehensive audit
"Use python-code-reviewer, type-system-expert, performance-profiler, test-development-master in parallel to audit [module]"

# Refactor safely
"Use test-development-master to add tests, code-refactoring-expert to refactor, python-code-reviewer to verify"
```

### Performance
```bash
"Use performance-profiler to find bottlenecks, python-expert-architect to design optimizations, python-implementation-specialist to implement"
```

### Types
```bash
# Add types
"Use type-system-expert to add comprehensive type annotations to [module]"

# Fix type errors
"Use type-system-expert to fix basedpyright errors in [file]"

# Python 3.13+ modernization
"Use type-system-expert to update [module] with TypeIs and ReadOnly TypedDict"
```

### Environment
```bash
# Setup
"Use venv-keeper to setup Python 3.13 environment with ruff, basedpyright, pytest"

# Update deps
"Use venv-keeper to update dependencies and check for vulnerabilities"
```

---

## Decision Matrix

| I need to...                    | Use this agent                              |
|---------------------------------|---------------------------------------------|
| Fix a bug                       | deep-debugger                               |
| Threading/deadlock              | threading-debugger (or qt-concurrency-architect for Qt) |
| Add feature (TDD)               | test-development-master → python-implementation-specialist |
| Add feature (direct)            | python-implementation-specialist            |
| Review code                     | python-code-reviewer                        |
| Add/fix types                   | type-system-expert                          |
| Refactor messy code             | code-refactoring-expert                     |
| Optimize performance            | performance-profiler                        |
| Design architecture             | python-expert-architect                     |
| Build Qt UI                     | qt-ui-modernizer                            |
| Custom Qt widget                | qt-modelview-painter                        |
| Qt threading issues             | qt-concurrency-architect                    |
| Setup/update environment        | venv-keeper                                 |
| Write/improve tests             | test-development-master                     |
| Modernize to Python 3.13+       | type-system-expert + test-development-master |

---

## Parallel Patterns (Run Faster!)

```bash
# Code analysis
"Use python-code-reviewer and type-system-expert in parallel to analyze [file]"

# Complete audit
"Use python-code-reviewer, type-system-expert, performance-profiler in parallel to audit [module]"

# Qt review
"Use qt-concurrency-architect and ui-ux-validator in parallel to review [Qt app]"
```

---

## Python 3.13+ Quick Wins

```bash
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
✅ **Use parallel**: Run independent agents together for speed
✅ **Chain logically**: Feed output from one agent to the next
✅ **Verify changes**: Always run tests after modifications
✅ **Choose right agent**: Qt issues need Qt agents, not general Python agents

❌ **Avoid vague prompts**: "Fix the code" → Which file? Which agent?
❌ **Don't skip verification**: Changes without tests = risky
❌ **Don't mix concerns**: Use specialized agents for specialized tasks

---

## Emergency Commands

```bash
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
