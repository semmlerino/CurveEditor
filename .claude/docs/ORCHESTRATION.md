# 🎯 Agent Orchestration: Prompts & Recipes

A comprehensive guide to orchestrating multiple agents for maximum efficiency.

---

## ⚠️ Important Notes

**These are USER PROMPTS** - Copy them to your chat with Claude.

**Agent Basics:**
- Agents work on complex, multi-step tasks
- Each agent is stateless (no memory between runs)
- Results are summarized by Claude (not raw output shown to user)
- Parallel execution is 50-70% faster when tasks are independent

**For simple tasks, use direct tools:**
- Reading files → Read tool
- Finding files → Glob tool
- Searching code → Grep tool

---

## 📋 Quick Reference - Common Workflows

### Single Agent Tasks

**User Prompts:**
```text
# Code Review
"Use python-code-reviewer to analyze [file/module]"

# Add Type Hints
"Use type-system-expert to add comprehensive type annotations to [file]"

# Write Tests
"Use test-development-master to create pytest tests for [function/class]"

# Debug Issue
"Use deep-debugger to investigate: [bug description]"

# Performance Analysis
"Use performance-profiler to analyze [slow component]"

# Refactor Code
"Use code-refactoring-expert to refactor [messy module/function]"

# Fix Threading
"Use threading-debugger to analyze this deadlock/race condition: [description]"

# Setup Environment
"Use venv-keeper to setup virtual environment with [dependencies]"
```

### Two-Agent Workflows

**User Prompts:**
```text
# Implement + Review
"Use python-implementation-specialist to implement [feature], then python-code-reviewer to review"

# Debug + Fix
"Use deep-debugger to find root cause of [bug], then python-implementation-specialist to fix"

# Optimize + Verify
"Use performance-profiler to identify bottlenecks, then python-expert-architect to design optimizations"

# Type + Verify
"Use type-system-expert to add types, then verify with basedpyright"

# Refactor + Test
"Use code-refactoring-expert to improve [code], then test-development-master to ensure coverage"
```

### Parallel Execution (60% Faster!)

**User Prompts:**
```text
# Comprehensive Code Analysis
"Use python-code-reviewer and type-system-expert agents in parallel to analyze [file]"

# Multi-aspect Review
"Use python-code-reviewer, performance-profiler, and type-system-expert agents in parallel to audit [module]"

# Complete Quality Check
"Use python-code-reviewer and test-development-master agents in parallel to verify [implementation]"
```

---

## 🔍 Agent Selector - "I Need To..."

### Development Tasks
- **Add new feature (TDD)** → test-development-master → python-implementation-specialist → python-code-reviewer
- **Add new feature (direct)** → python-expert-architect (design) → python-implementation-specialist → test-development-master
- **Build Qt UI** → qt-ui-modernizer OR python-expert-architect (architecture)
- **Custom Qt widgets** → qt-modelview-painter → ui-ux-validator

### Problem Solving
- **Fix a bug** → deep-debugger → python-implementation-specialist → test-development-master (regression)
- **Threading/deadlock issues** → threading-debugger OR qt-concurrency-architect (if Qt)
- **Performance problems** → performance-profiler → python-expert-architect → python-implementation-specialist
- **Memory leaks** → performance-profiler (memory analysis) → code-refactoring-expert

### Code Quality
- **Review code** → python-code-reviewer
- **Improve types** → type-system-expert
- **Refactor messy code** → code-refactoring-expert
- **Add missing tests** → test-development-master
- **Fix style issues** → python-code-reviewer → code-refactoring-expert

### Environment & Setup
- **Setup project** → venv-keeper
- **Update dependencies** → venv-keeper → test-development-master (verify)
- **Configure linting** → venv-keeper
- **Fix type checking** → type-system-expert + venv-keeper (config)

---

## 📚 Detailed Workflow Recipes

### Recipe 1: TDD New Feature Development

**Goal**: Implement a new feature using Test-Driven Development

**When to use**: Starting a new feature from scratch, want high test coverage

**Agents**: test-development-master → python-implementation-specialist → python-code-reviewer

**Workflow**:
1. Write failing tests (RED)
2. Implement minimal code (GREEN)
3. Review and refactor (REFACTOR)

**Expected Deliverables:**
- Step 1: Complete test suite with clear test cases (failing initially)
- Step 2: Working implementation that passes all tests
- Step 3: Code review report with refactoring suggestions

**What You'll Get:**
- ✅ Fully tested feature with >90% coverage
- ✅ Clean, reviewable implementation
- ✅ Documented behavior via tests
- ✅ Confidence in correctness

#### Copy-Paste Prompts:

**User Prompts:**
```text
# Step 1: Write Tests (RED)
"I want to implement [feature description] using TDD. Use test-development-master to write failing tests that specify the behavior."

# Step 2: Implement (GREEN)
"Use python-implementation-specialist to implement the minimal code to pass these tests: [test file]"

# Step 3: Review (REFACTOR)
"Use python-code-reviewer to review the implementation and suggest refactoring improvements"

# Alternative: All-in-one
"Use TDD to implement [feature]: test-development-master writes tests, python-implementation-specialist implements, python-code-reviewer reviews"
```

---

### Recipe 2: Bug Investigation & Fix

**Goal**: Find and fix a mysterious bug

**When to use**: Bug is hard to reproduce, unclear root cause, or intermittent

**Agents**: deep-debugger → python-implementation-specialist → test-development-master

**Workflow**:
1. Deep analysis to find root cause
2. Implement fix
3. Add regression tests

**Expected Deliverables:**
- Step 1: Root cause analysis report with reproduction steps
- Step 2: Code fix with explanation
- Step 3: Regression test suite

**What You'll Get:**
- ✅ Clear understanding of bug root cause
- ✅ Targeted fix (not a band-aid)
- ✅ Protection against regression
- ✅ Documentation of the issue

#### Copy-Paste Prompts:

**User Prompts:**
```text
# Step 1: Investigate
"Use deep-debugger to investigate this bug: [description, steps to reproduce, error messages]"

# Step 2: Fix
"Based on the root cause analysis, use python-implementation-specialist to implement the fix"

# Step 3: Prevent Regression
"Use test-development-master to add regression tests that catch this bug if it reoccurs"

# For Threading Issues:
"Use threading-debugger to analyze this concurrency bug: [description]"
# OR for Qt threading:
"Use qt-concurrency-architect to fix this Qt threading issue: [description]"

# All-in-one
"Debug and fix: [bug description]. Use deep-debugger to find root cause, python-implementation-specialist to fix, test-development-master for regression tests"
```

---

### Recipe 3: Performance Optimization

**Goal**: Make slow code fast

**When to use**: Code is too slow, want to optimize hot paths

**Agents**: performance-profiler → python-expert-architect → python-implementation-specialist → test-development-master

**Workflow**:
1. Profile to identify bottlenecks
2. Design optimization strategy
3. Implement optimizations
4. Verify with benchmarks

#### Copy-Paste Prompts:

```bash
# Step 1: Profile
"Use performance-profiler to identify bottlenecks in [slow component/function]"

# Step 2: Design
"Use python-expert-architect to design optimization strategies for these bottlenecks: [profiler findings]"

# Step 3: Implement
"Use python-implementation-specialist to implement these optimizations: [optimization plan]"

# Step 4: Verify
"Use test-development-master to add performance benchmarks verifying the speedup"

# All-in-one
"Optimize [component]: performance-profiler finds bottlenecks, python-expert-architect designs fixes, python-implementation-specialist implements"
```

---

### Recipe 4: Code Quality Improvement

**Goal**: Improve existing code quality comprehensively

**When to use**: Legacy code, recent code needs polish, pre-deployment review

**Agents**: python-code-reviewer + type-system-expert (parallel) → code-refactoring-expert → test-development-master

**Workflow**:
1. Parallel analysis (review + types) - 60% faster!
2. Refactor based on findings
3. Ensure test coverage

**Expected Deliverables:**
- Step 1: Bug report + type error report (in parallel)
- Step 2: Refactored code with improved structure
- Step 3: Comprehensive test suite with >90% coverage

**What You'll Get:**
- ✅ Multi-perspective code analysis (bugs, types, design)
- ✅ Actionable improvement list
- ✅ Cleaner, maintainable code
- ✅ Full test coverage
- ⚡ 60% faster than sequential review

#### Copy-Paste Prompts:

**User Prompts:**
```text
# Step 1: Parallel Analysis (60% FASTER!)
"Use python-code-reviewer and type-system-expert agents in parallel to comprehensively analyze [file/module]"

# Step 2: Refactor
"Use code-refactoring-expert to address the issues found: [list of issues from review]"

# Step 3: Test Coverage
"Use test-development-master to ensure >90% test coverage after refactoring"

# Alternative: Add performance check (3x faster than sequential!)
"Use python-code-reviewer, type-system-expert, and performance-profiler agents in parallel to audit [module]"
```

---

### Recipe 5: Qt Application Development

**Goal**: Build or improve Qt/PySide6 application

**When to use**: Qt GUI development, threading issues, custom widgets

**Agents**: python-expert-architect → python-implementation-specialist → qt-concurrency-architect/qt-ui-modernizer → ui-ux-validator

**Workflow**:
1. Design architecture
2. Implement core functionality
3. Fix Qt-specific issues
4. Validate UX

#### Copy-Paste Prompts:

```bash
# New Qt Application
"Use python-expert-architect to design Qt application architecture for [requirements]"
"Use python-implementation-specialist to implement the core Qt application structure"
"Use qt-ui-modernizer to create modern, user-friendly UI"
"Use ui-ux-validator to verify usability and accessibility"

# Qt Threading Issues
"Use qt-concurrency-architect to fix threading/signal issues in [Qt component]"

# Custom Qt Widget
"Use qt-modelview-painter to implement custom [widget type] with Model/View architecture"

# Qt Performance
"Use performance-profiler to identify UI freezing causes, then qt-concurrency-architect to fix thread blocking"
```

---

### Recipe 6: Type System Enhancement

**Goal**: Add comprehensive type annotations and fix type errors

**When to use**: No types, type errors, want strict type checking

**Agents**: type-system-expert → venv-keeper (verify) → python-code-reviewer

**Workflow**:
1. Add/fix type annotations
2. Verify with basedpyright
3. Review for quality

#### Copy-Paste Prompts:

```bash
# Add Types
"Use type-system-expert to add comprehensive type annotations to [module]"

# Fix Type Errors
"Use type-system-expert to fix these basedpyright errors: [error list or file]"

# Verify Configuration
"Use venv-keeper to ensure basedpyright is configured correctly for strict mode"

# Full Type Safety
"Use type-system-expert to add types, then verify with basedpyright in strict mode"

# Python 3.13+ Features
"Use type-system-expert to modernize types with TypeIs and ReadOnly TypedDict in [module]"
```

---

### Recipe 7: Refactoring Legacy Code

**Goal**: Safely refactor old, messy code

**When to use**: Technical debt, hard-to-maintain code, preparing for new features

**Agents**: test-development-master → code-refactoring-expert → python-code-reviewer → test-development-master

**Workflow**:
1. Add characterization tests (if missing)
2. Refactor with tests passing
3. Review refactored code
4. Ensure tests still pass

#### Copy-Paste Prompts:

```bash
# Step 1: Safety Net
"Use test-development-master to add characterization tests for [legacy module] before refactoring"

# Step 2: Refactor
"Use code-refactoring-expert to refactor [module] while keeping all tests green"

# Step 3: Review
"Use python-code-reviewer to verify refactoring improves code quality"

# Step 4: Final Verification
"Use test-development-master to ensure test coverage is maintained after refactoring"

# All-in-one
"Safely refactor [legacy code]: test-development-master adds tests, code-refactoring-expert refactors, python-code-reviewer verifies"
```

---

### Recipe 8: Environment Setup & Maintenance

**Goal**: Setup or update development environment

**When to use**: New project, dependency updates, linting setup, CI/CD configuration

**Agents**: venv-keeper → test-development-master

**Workflow**:
1. Setup/update environment
2. Verify everything works

#### Copy-Paste Prompts:

```bash
# New Project Setup
"Use venv-keeper to setup Python virtual environment with ruff, basedpyright, pytest for new project"

# Dependency Update
"Use venv-keeper to update dependencies and check for security vulnerabilities"

# Configure Quality Tools
"Use venv-keeper to configure ruff and basedpyright with strict settings"

# Verify After Changes
"Use test-development-master to run full test suite after environment changes"

# Python 3.13 Setup
"Use venv-keeper to setup Python 3.13 environment with latest ruff, basedpyright, and pytest"
```

---

### Recipe 9: Python 3.13+ Modernization

**Goal**: Modernize codebase with Python 3.13+ features

**When to use**: Moving to Python 3.13+, want to use latest type system features

**Agents**: type-system-expert → test-development-master → venv-keeper

**Workflow**:
1. Update type system with modern features
2. Fix pytest async fixture deprecations
3. Verify environment compatibility

#### Copy-Paste Prompts:

```bash
# Modernize Type System
"Use type-system-expert to update [module] with Python 3.13 features: TypeIs instead of TypeGuard, ReadOnly TypedDict for immutable fields"

# Fix Pytest 8.4+ Async Fixtures
"Use test-development-master to fix pytest 8.4+ async fixture deprecation warnings by wrapping async fixtures in sync fixtures"

# Update Environment
"Use venv-keeper to ensure Python 3.13 compatibility and update basedpyright/ruff to latest versions"

# Full Modernization
"Modernize codebase for Python 3.13+: type-system-expert updates types with TypeIs and ReadOnly, test-development-master fixes async fixtures, venv-keeper updates tools"

# Specific Feature Updates:
"Use type-system-expert to replace TypeGuard with TypeIs for better type narrowing in [module]"
"Use type-system-expert to add ReadOnly to TypedDict fields that shouldn't be modified in [config/model file]"
"Use test-development-master to wrap async fixtures for pytest 8.4+ compatibility"
```

---

## ⚡ Parallel Execution Patterns

**When to run agents in parallel:**
- Agents don't depend on each other's output
- Want faster analysis/review
- Multiple perspectives on same code

### Pattern 1: Comprehensive Code Analysis
```bash
"Use python-code-reviewer, type-system-expert, and performance-profiler agents in parallel to analyze [file]"
```
**Benefit**: Get bugs, type issues, and performance problems all at once

### Pattern 2: Multi-Aspect Quality Check
```bash
"Use python-code-reviewer and test-development-master agents in parallel to verify [implementation]"
```
**Benefit**: Check code quality and test coverage simultaneously

### Pattern 3: Qt Application Review
```bash
"Use qt-concurrency-architect and ui-ux-validator agents in parallel to review [Qt application]"
```
**Benefit**: Check threading safety and UX issues together

### Pattern 4: Full Stack Analysis
```bash
"Use python-code-reviewer, type-system-expert, performance-profiler, and test-development-master agents in parallel for complete audit of [module]"
```
**Benefit**: Maximum coverage in minimum time

---

## ⚠️ Agent Limitations & Expectations

**What agents CAN'T do:**
- ❌ Agents can't interact with each other directly
- ❌ Each invocation is stateless (no memory between runs)
- ❌ Can't ask follow-up questions during execution
- ❌ Can't see intermediate work from other agents

**What you GET from agents:**
- ✅ Results are summarized by Claude (not raw agent output)
- ✅ Actionable findings and recommendations
- ✅ Code changes, analysis reports, or test suites
- ✅ Clear explanation of what was done

**Best practice:** Provide complete context in your prompt. Include:
- Specific file/module paths
- What you want analyzed/changed
- Any constraints or requirements
- Context from previous agent runs (if chaining)

---

## 💡 Best Practices

### 1. Start Specific, Expand as Needed
**User Prompts:**
```text
# Good: Specific agent for specific task
"Use type-system-expert to fix type errors in ui/authentication.py"

# Less optimal: Too vague
"Fix the types" (which agent? which file?)
```

### 2. Default to Parallel (60% Faster!)
**User Prompts:**
```text
# Faster - saves 50-70% time
"Use python-code-reviewer and type-system-expert agents in parallel to analyze ui/main_window.py"

# Slower (sequential) - only use when agent2 needs agent1 output
"Use python-code-reviewer, then type-system-expert"
```

### 3. Chain Outputs Explicitly
**User Prompts:**
```text
# Good: Output feeds next step with context
"Use deep-debugger to find root cause of [bug], then python-implementation-specialist to fix based on the findings"

# Less optimal: Disconnected steps
"Use deep-debugger" (then forget to fix)
```

### 4. Choose the Right Specialist
**User Prompts:**
```text
# Threading issues in Qt
"Use qt-concurrency-architect to fix signal threading in ui/controllers/timeline_controller.py"

# General Python threading
"Use threading-debugger to analyze race condition in data/batch_edit.py"

# Complex async architecture
"Use python-expert-architect to design async architecture for services/"
```

### 5. Always Verify After Changes
**User Prompts:**
```text
# Good: Verification step
"Use python-implementation-specialist to implement feature, then test-development-master to verify with tests"

# Risky: No verification
"Use python-implementation-specialist to implement feature" (stop)
```

### 6. Use TDD for Critical Code
**User Prompts:**
```text
# High-quality approach
"Use test-development-master to write tests first, then python-implementation-specialist to implement"

# Faster but riskier
"Use python-implementation-specialist to implement quickly"
```

### 7. Provide File Paths
**User Prompts:**
```text
# Good: Specific path
"Use python-code-reviewer to analyze ui/curve_view_widget.py"

# Less optimal: Vague reference
"Use python-code-reviewer to analyze the main widget" (which widget?)
```

---

## 🔧 Troubleshooting

### "Agent didn't do what I expected"

**Problem**: Agent output doesn't match your needs

**Solution**:
```bash
# Be more specific about what you want
"Use type-system-expert to add TypeIs type guards (not TypeGuard) to narrow types in [function]"

# Provide context
"Use python-code-reviewer to review [file] focusing on security vulnerabilities and input validation"

# Specify the technology stack
"Use qt-concurrency-architect (not threading-debugger) for this Qt threading issue"
```

### "Too many agents, which one?"

**Problem**: Unclear which agent to use

**Solution**: Use the decision tree above, or:
```bash
# Ask for analysis first
"What's the best way to [achieve goal]?"

# Then use specific agent based on recommendation
```

### "Agent gave general advice, not code"

**Problem**: Agent analyzed but didn't implement

**Solution**:
```bash
# Use implementation-focused agents
"Use python-implementation-specialist to implement [specific feature with details]"

# Chain analysis to implementation
"Use deep-debugger to find root cause, then python-implementation-specialist to write the fix"
```

### "Tests are failing after changes"

**Problem**: Implementation broke existing tests

**Solution**:
```bash
# Run tests in parallel with review
"Use test-development-master and python-code-reviewer agents in parallel to verify [changes]"

# Add regression prevention
"Use test-development-master to add tests before making changes to [module]"
```

### "Type errors after modernization"

**Problem**: Python 3.13 features causing issues

**Solution**:
```bash
# Verify environment first
"Use venv-keeper to ensure Python 3.13+ and latest basedpyright are installed"

# Use typing_extensions for compatibility
"Use type-system-expert to add Python 3.13 features with typing_extensions fallback for older Python"
```

---

## 🎯 Decision Tree: Which Agent?

```
┌─ Fix bug ──────────────────────────┐
│                                     │
├─ Intermittent/mysterious? ────> deep-debugger
├─ Threading/concurrency? ─────> threading-debugger (or qt-concurrency-architect if Qt)
└─ Simple/obvious? ────────────> python-implementation-specialist

┌─ New feature ──────────────────────┐
│                                     │
├─ Want TDD? ───────────────────> test-development-master → python-implementation-specialist
├─ Complex architecture? ───────> python-expert-architect → python-implementation-specialist
└─ Simple addition? ────────────> python-implementation-specialist

┌─ Improve code quality ─────────────┐
│                                     │
├─ Type errors? ────────────────> type-system-expert
├─ Design issues? ──────────────> code-refactoring-expert (or python-expert-architect)
├─ Missing tests? ──────────────> test-development-master
├─ Performance? ────────────────> performance-profiler
└─ General review? ─────────────> python-code-reviewer

┌─ Qt/PySide6 work ──────────────────┐
│                                     │
├─ Threading/signals? ──────────> qt-concurrency-architect
├─ UI/UX issues? ───────────────> qt-ui-modernizer → ui-ux-validator
├─ Custom widgets? ─────────────> qt-modelview-painter
└─ Architecture? ───────────────> python-expert-architect

┌─ Environment/setup ────────────────┐
│                                     │
├─ Dependencies? ────────────────> venv-keeper
├─ Linting config? ─────────────> venv-keeper
└─ Type checking config? ───────> venv-keeper + type-system-expert

┌─ Python 3.13+ modernization ───────┐
│                                     │
├─ Type system (TypeIs, ReadOnly)? ──> type-system-expert
├─ Pytest async fixtures? ──────> test-development-master
├─ Performance features? ───────> python-expert-architect
└─ Environment setup? ──────────> venv-keeper
```

---

## 🚀 Quick Start Examples

Copy-paste these complete workflows:

```bash
# 1. Implement validated new feature
"Use TDD to implement [feature]: test-development-master writes tests, python-implementation-specialist implements, python-code-reviewer reviews"

# 2. Fix and prevent bug
"Debug [bug]: deep-debugger finds cause, python-implementation-specialist fixes, test-development-master adds regression tests"

# 3. Comprehensive code improvement
"Use python-code-reviewer and type-system-expert in parallel to analyze [file], then code-refactoring-expert to address issues"

# 4. Performance optimization
"Optimize [slow code]: performance-profiler identifies bottlenecks, python-expert-architect designs solution, python-implementation-specialist implements"

# 5. Qt application development
"Build Qt [feature]: python-expert-architect designs, python-implementation-specialist implements, qt-concurrency-architect fixes threading, ui-ux-validator verifies UX"

# 6. Complete quality audit
"Full audit of [module]: use python-code-reviewer, type-system-expert, performance-profiler, and test-development-master in parallel"

# 7. Python 3.13 modernization
"Modernize for Python 3.13+: type-system-expert updates to TypeIs and ReadOnly, test-development-master fixes async fixtures, venv-keeper updates environment"
```

---

## 📝 Template: Create Your Own Recipe

```bash
# Your Workflow Name
# Step 1: [What]
"Use [agent-name] to [specific task]: [context]"

# Step 2: [What]
"Use [agent-name] to [specific task based on step 1]"

# Step 3: [What]
"Use [agent-name] to [verification/final step]"

# Alternative: Parallel (if steps are independent)
"Use [agent1] and [agent2] agents in parallel to [achieve goal]"
```

---

**Pro Tip**: Save this document for quick reference. The more specific your prompts, the better the agent orchestration will work!
