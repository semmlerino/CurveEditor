# 🎯 Agent Orchestration Guide

**Audience:** Claude Code (orchestrator)
**Purpose:** Plan and execute agent workflows based on user requests

---

## Task Classification

Match user requests to task types and workflows.

| User Keywords/Phrases | Task Type | Characteristics | Primary Agents |
|----------------------|-----------|-----------------|----------------|
| refactor, clean up, messy, improve structure, technical debt | **Code Quality** | Improve existing code | python-code-reviewer + type-system-expert → code-refactoring-expert |
| bug, broken, not working, fails, error, crash | **Bug Investigation** | Find root cause | deep-debugger → python-implementation-specialist → test-development-master |
| add feature, implement, create, build | **Feature Implementation** | New functionality | python-expert-architect (if complex) → python-implementation-specialist → test-development-master |
| slow, performance, optimize, bottleneck | **Performance** | Speed improvement | performance-profiler → python-expert-architect → python-implementation-specialist |
| type errors, annotations, basedpyright, mypy | **Type System** | Type safety | type-system-expert |
| tests, coverage, TDD | **Testing** | Test creation | test-development-master |
| review, audit, check, analyze | **Code Review** | Quality analysis | python-code-reviewer (+ type-system-expert and/or performance-profiler in parallel) |

### Domain Indicators

| Keywords in Request | Domain | Specialized Agents |
|---------------------|--------|--------------------|
| PyQt, PySide, QWidget, signal, slot, QThread, Qt | **Qt/GUI** | qt-concurrency-architect, qt-ui-modernizer, qt-modelview-painter, ui-ux-validator |
| threading, deadlock, race condition, concurrent | **Threading** | threading-debugger (general) or qt-concurrency-architect (Qt) |
| async, asyncio, await | **Async** | python-expert-architect |
| venv, dependencies, requirements, ruff, basedpyright | **Environment** | venv-keeper |

---

## Agent Selection Criteria

### By Complexity

**Complex Tasks (Architecture/Design):**
- python-expert-architect - Complex architectures, async/concurrency, advanced patterns
- code-refactoring-expert - Major refactoring, pattern application

**Implementation:**
- python-implementation-specialist - Feature implementation, bug fixes

**Debugging:**
- deep-debugger - Complex bugs, intermittent issues, root cause analysis
- threading-debugger - Deadlocks, race conditions, threading issues
- performance-profiler - Bottleneck identification

**Qt-Specific:**
- qt-concurrency-architect - Qt threading, cross-thread signals
- qt-modelview-painter - Model/View architecture, custom widgets
- qt-ui-modernizer - UI/UX design and modernization
- ui-ux-validator - Usability validation

**Quality & Testing:**
- python-code-reviewer - Code review, bugs, design issues
- type-system-expert - Type annotations, type error fixing
- test-development-master - Test creation, TDD

**Infrastructure:**
- venv-keeper - Virtual environments, dependencies

**Note:** All agents currently use Sonnet model.

### Bug Investigation Decision Tree

```
Bug reported
├─ Intermittent/mysterious/hard to reproduce?
│  └─ deep-debugger
│
├─ Threading/concurrency issue?
│  ├─ Qt application? → qt-concurrency-architect
│  └─ General Python? → threading-debugger
│
└─ Simple/obvious cause?
   └─ python-implementation-specialist
```

### Feature Implementation Decision Tree

```
New feature requested
├─ Complex architecture needed?
│  ├─ Async/concurrent patterns? → python-expert-architect
│  ├─ Advanced Python features? → python-expert-architect
│  └─ Framework design? → python-expert-architect
│
└─ Straightforward implementation?
   └─ python-implementation-specialist
```

---

## Workflow Patterns by Task Type

### Pattern 1: Bug Investigation & Fix

**Trigger:** User reports bug, broken functionality, error

**Decision:** Is root cause obvious?

**Workflow A (Investigation Needed):**
1. **Investigate:** deep-debugger (or threading-debugger/qt-concurrency-architect)
   - Identifies root cause
2. **Fix:** python-implementation-specialist
   - Implements fix based on findings
3. **Test:** test-development-master
   - Adds regression test
4. **Validate:** pytest

**Workflow B (Simple/Obvious):**
1. **Fix:** python-implementation-specialist
   - Implements fix directly
2. **Test:** test-development-master
   - Adds test
3. **Validate:** pytest

**Plan Template:**
```
"I'll investigate the root cause with [debugger-agent], implement the fix with python-implementation-specialist, and add a regression test with test-development-master to prevent recurrence."
```

---

### Pattern 2: Feature Implementation

**Trigger:** Add, implement, create, build new functionality

**Decision:** Does this require architectural design?

**Indicators of Complexity:**
- Async/concurrent patterns
- Multiple components/modules
- Framework-level changes
- Advanced Python features (decorators, metaclasses, protocols)
- User explicitly asks for "architecture" or "design"

**Workflow A (Complex - Needs Design):**
1. **Design:** python-expert-architect
   - Designs architecture
   - User reviews/approves design
2. **Implement:** python-implementation-specialist
   - Implements based on design
3. **Test:** test-development-master
   - Writes comprehensive tests
4. **Review:** python-code-reviewer
   - Security/quality review (if feature is security-sensitive or user requests)
5. **Validate:** pytest && basedpyright

**Workflow B (Simple - Direct Implementation):**
1. **Implement:** python-implementation-specialist
   - Implements feature
2. **Test:** test-development-master
   - Writes tests
3. **Validate:** pytest

**Plan Template (Complex):**
```
"I'll use python-expert-architect to design the architecture first, then python-implementation-specialist to implement, test-development-master to write comprehensive tests, and python-code-reviewer for a final security review."
```

**Plan Template (Simple):**
```
"I'll use python-implementation-specialist to implement [feature] and test-development-master to write tests."
```

---

### Pattern 3: Code Quality Improvement

**Trigger:** Refactor, clean up, improve, messy code, technical debt

**Workflow:**
1. **Analyze (PARALLEL):** python-code-reviewer + type-system-expert
   - Both agents analyze same code simultaneously (read-only, safe)
   - Findings: bugs, design issues, type errors, style issues
2. **Deduplicate & Prioritize:**
   - Merge findings
   - Remove duplicates
   - Priority: Bugs > Types > Design > Style
3. **Fix (SEQUENTIAL):**
   - **Bugs first:** python-implementation-specialist
   - **Structure:** code-refactoring-expert
   - **Types:** type-system-expert
4. **Validate after each:** pytest && basedpyright

**Why Parallel is Safe:**
- Both python-code-reviewer and type-system-expert are read-only
- No file conflicts possible
- Faster results

**Plan Template:**
```
"I'll analyze [module] with python-code-reviewer and type-system-expert in parallel to identify all issues comprehensively. Then I'll systematically address them: critical bugs first with python-implementation-specialist, structural improvements with code-refactoring-expert, and type safety with type-system-expert. I'll validate with tests after each change."
```

---

### Pattern 4: Performance Optimization

**Trigger:** Slow, performance issues, bottlenecks, optimize

**Workflow:**
1. **Profile:** performance-profiler
   - Identifies bottlenecks with data
2. **Design:** python-expert-architect
   - Designs optimization strategy
3. **Implement:** python-implementation-specialist
   - Implements optimizations
4. **Benchmark:** test-development-master
   - Adds performance benchmarks
5. **Validate:** pytest + benchmark comparison

**Plan Template:**
```
"I'll use performance-profiler to identify bottlenecks, python-expert-architect to design optimization strategies, python-implementation-specialist to implement them, and test-development-master to add benchmarks verifying the improvements."
```

---

### Pattern 5: Code Review/Analysis

**Trigger:** Review, audit, check, analyze (without changes)

**Workflow:**
1. **Comprehensive Analysis (PARALLEL):**
   - python-code-reviewer (bugs, design, style)
   - type-system-expert (type issues)
   - performance-profiler (if performance mentioned)
2. **Consolidate Findings:**
   - Deduplicate
   - Prioritize
   - Present to user

**Why Parallel:**
- All read-only
- Multiple perspectives
- Faster

**Plan Template:**
```
"I'll analyze [module] with python-code-reviewer, type-system-expert, and performance-profiler in parallel to provide a comprehensive quality assessment."
```

---

## Execution Strategy

### When to Use Parallel Execution

**Safe Scenarios (Read-Only):**
- python-code-reviewer + type-system-expert
- python-code-reviewer + performance-profiler
- type-system-expert + performance-profiler
- Any combination of review/* agents
- ui-ux-validator + qt-concurrency-architect (both in review mode)

**Benefits:**
- 2-3x faster analysis
- Multiple perspectives simultaneously
- Comprehensive findings

**Post-Parallel Process:**
1. Collect all findings from all agents
2. Deduplicate (same file:line = duplicate, keep most specific)
3. Prioritize: Critical (bugs) > Important (types, performance) > Style
4. Present consolidated report to user

### When Sequential is Required

**Same-File Modifications:**
- **NEVER** parallelize write agents on same file
- Example: code-refactoring-expert + type-system-expert both modifying auth.py = CONFLICT

**Dependencies:**
- Agent B needs Agent A's output
- Examples:
  - deep-debugger findings → python-implementation-specialist fix
  - python-expert-architect design → python-implementation-specialist implementation
  - Analysis → Fix → Test (sequential chain)

**Major Changes:**
- Architectural refactors
- Database migrations
- API contract changes
- Renaming across codebase

### File Coordination Rules

**Default Protocol:**
- Let agents discover files using Glob/Grep/Read tools
- Agents are excellent at finding relevant code
- Don't ask user for file paths unless necessary

**When to Ask User for Location:**
- Ambiguous location ("auth code" could be in multiple places)
- Non-standard project structure
- Previous search found nothing relevant
- User mentioned location is "weird" or "non-obvious"

**How to Ask:**
```
"I need to locate [X]. Could you provide the file path or directory? For example: 'src/auth/' or 'legacy/old_auth.py'"
```

**When User Provides Location:**
- Use as starting point
- Agents can still discover related files from there
- Don't limit scope to only provided files

---

## Planning & Communication

### When to Present Plan to User

**Always Present Plan For:**
- Multi-step workflows (3+ steps)
- Before making any code changes
- When using complex agents (python-expert-architect, code-refactoring-expert, deep-debugger)
- When user intent might be ambiguous
- Before parallel execution involving multiple agents

**No Plan Needed For:**
- Simple single-agent analysis
- User explicitly said "just do it" or similar
- Obvious, straightforward task

### Plan Format

```
**Task Understanding:**
[Restate what user wants]

**Approach:**
1. [Agent/step] - [Purpose]
2. [Agent/step] - [Purpose]
3. [Agent/step] - [Purpose]

**Expected Outcome:**
[What will be delivered]

**Validation:**
[How we'll confirm success]
```

**Example:**
```
**Task Understanding:**
You want to refactor the messy utils module for better maintainability.

**Approach:**
1. python-code-reviewer + type-system-expert (parallel) - Comprehensive analysis
2. python-implementation-specialist - Fix critical bugs
3. code-refactoring-expert - Improve structure
4. type-system-expert - Fix type errors

**Expected Outcome:**
Clean, well-structured utils module with proper types and no bugs.

**Validation:**
pytest && basedpyright after each change.
```

### When to Ask for Clarification

**Ask When:**
- Ambiguous requirements ("improve the code" - improve what aspect?)
- Multiple valid interpretations
- Location is unclear
- Scope is unclear (whole codebase vs specific module?)
- Risk of wrong assumptions

**How to Ask:**
```
"I can help with [task]. Could you clarify:
- Which module/file should I focus on?
- Are you most concerned about [A] or [B]?
- Should I [X] or [Y]?"
```

**Don't Ask When:**
- Request is clear
- Standard workflow applies
- You can make reasonable assumptions and state them in the plan

---

## Quick Reference: Common Requests

| User Request | Task Type | Agents & Pattern |
|--------------|-----------|------------------|
| "Refactor this messy code" | Code Quality | python-code-reviewer + type-system-expert ‖ → code-refactoring-expert |
| "Fix bug: [symptom]" | Bug (investigate) | deep-debugger → python-implementation-specialist → test-development-master |
| "Fix this [obvious issue]" | Bug (simple) | python-implementation-specialist → test-development-master |
| "Add [simple feature]" | Feature (direct) | python-implementation-specialist → test-development-master |
| "Add [complex feature]" | Feature (design) | python-expert-architect → python-implementation-specialist → test-development-master |
| "Review code for security" | Review | python-code-reviewer (focus: security) |
| "Add type hints" | Type annotation | type-system-expert |
| "Fix type errors" | Type correction | type-system-expert |
| "Performance is slow in [X]" | Performance | performance-profiler → python-expert-architect → python-implementation-specialist |
| "Write tests for [X]" | Testing | test-development-master |
| "Qt threading issue" | Qt concurrency | qt-concurrency-architect |
| "Modernize this UI" | Qt UI | qt-ui-modernizer |
| "Complete code audit" | Comprehensive review | python-code-reviewer + type-system-expert + performance-profiler ‖ |

**Legend:** `‖` = parallel, `→` = sequential

---

## Orchestration Best Practices

### Do This:
- ✅ Use parallel for read-only analysis (faster, comprehensive)
- ✅ Present plans for multi-step workflows
- ✅ Let agents discover files (they have Glob/Grep)
- ✅ Validate after every code change (pytest, basedpyright)
- ✅ Chain agents logically (Analysis → Design → Implementation → Testing)
- ✅ Deduplicate findings from parallel agents
- ✅ Prioritize: Bugs > Types > Performance > Style

### Avoid This:
- ❌ Parallelize write agents on same file (conflicts guaranteed)
- ❌ Skip validation steps
- ❌ Ask user for file paths unless necessary (agents can discover)
- ❌ Use complex agents (python-expert-architect) for simple tasks
- ❌ Use simple agents (python-implementation-specialist) for complex architecture
- ❌ Present overly detailed plans for simple tasks

---

## Example Orchestration Flows

### Example 1: User Says "Refactor the auth module"

**Classification:** Code Quality improvement

**Agents:** python-code-reviewer + type-system-expert → code-refactoring-expert

**Plan Presented:**
```
I'll refactor the auth module for better maintainability:
1. python-code-reviewer + type-system-expert (parallel) - Analyze for issues
2. python-implementation-specialist - Fix critical bugs
3. code-refactoring-expert - Improve structure
4. type-system-expert - Fix type errors

Validation: pytest && basedpyright after each step.
```

**Execution:**
1. Launch python-code-reviewer and type-system-expert in parallel
2. Deduplicate findings, prioritize
3. Fix bugs sequentially
4. Refactor structure
5. Fix types
6. Validate after each

---

### Example 2: User Says "I have a deadlock in my Qt app"

**Classification:** Bug (Qt threading)

**Domain:** Qt concurrency

**Agent:** qt-concurrency-architect (Qt-specific)

**Plan Presented:**
```
I'll investigate the Qt deadlock:
1. qt-concurrency-architect - Analyze threading and signal/slot issues
2. python-implementation-specialist - Implement the fix
3. test-development-master - Add test to prevent regression

Validation: Manual testing + pytest
```

**Execution:**
1. qt-concurrency-architect investigates
2. Findings presented to user
3. Fix applied
4. Test added

---

### Example 3: User Says "Add OAuth2 authentication"

**Classification:** Feature (Complex - architecture needed)

**Agents:** python-expert-architect → python-implementation-specialist → test-development-master → python-code-reviewer

**Plan Presented:**
```
I'll implement OAuth2 authentication:
1. python-expert-architect - Design OAuth2 integration architecture
   [User reviews design]
2. python-implementation-specialist - Implement OAuth2 client
3. test-development-master - Write comprehensive tests
4. python-code-reviewer - Security review

Validation: pytest + manual OAuth flow testing
```

**Execution:**
1. Design architecture
2. Present to user, get approval
3. Implement
4. Test
5. Security review
6. Validate

---

## Related Documentation

- **[ORCHESTRATION.md](ORCHESTRATION.md)** - Detailed workflow recipes, parallel execution safety
- **[QUICK-REFERENCE.md](QUICK-REFERENCE.md)** - Agent capabilities, decision matrix
- **[AGENT_STANDARDS.md](docs/AGENT_STANDARDS.md)** - Agent scope boundaries, responsibilities
