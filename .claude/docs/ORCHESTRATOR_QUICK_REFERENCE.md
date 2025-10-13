# Orchestrator Quick Reference

_Last updated: 2025-10-05_

## How Orchestration Works

**You (the main agent) are the orchestrator.** Specialized agents:
- **Cannot communicate with each other** - they are isolated
- **Return a single report to you** - one message per agent
- **Are stateless** - no memory between launches
- **Don't see other agents' outputs** - unless you pass them context

**Your orchestration responsibilities:**
- Launch agents with specific, detailed task prompts
- Receive and synthesize agent reports
- Pass relevant findings between agents as context
- Decide sequencing, parallelization, and next steps
- Integrate all outputs into a coherent solution

**"Parallel" vs "Sequential" execution:**
- **Parallel**: You launch multiple agents in a single message (they run concurrently but independently)
- **Sequential**: You wait for an agent's report before launching the next one
- Agents never interact directly - you synthesize their outputs

## Quick Start Example

**User request:** "Add authentication to the API"

**Your orchestration flow:**

1. **Launch** python-expert-architect
   - → You receive: Design for auth system

2. **Pass design to** python-implementation-specialist
   - → You receive: Implementation code

3. **Launch in parallel** (single message):
   - python-code-reviewer
   - type-system-expert
   - → You receive: Two separate reports

4. **Synthesize** review findings

5. **Launch** test-development-master with context
   - → You receive: Test suite

6. **Integrate** everything and present to user

## Agent Capabilities Matrix

| Agent | Complexity | Primary Use | Parallelization |
|-------|-----------|-------------|-----------------|
| python-code-reviewer | Standard | Code review | ✅ Safe (read-only) |
| code-refactoring-expert | Advanced | Refactoring | ❌ Must run alone |
| python-expert-architect | Advanced | Complex patterns, async, frameworks | ⚠️ If separate files |
| python-implementation-specialist | Standard | Standard implementation | ⚠️ If separate files |
| test-development-master | Standard | Testing + TDD + Coverage + Qt | ⚠️ If separate files |
| test-type-safety-specialist | Standard | Type-safe tests | ⚠️ If separate files |
| type-system-expert | Standard | Types + protocols | ⚠️ If separate files |
| qt-ui-modernizer | Advanced | UI/UX + QML + Implementation | ⚠️ If separate files |
| ui-ux-validator | Standard | UI validation from user perspective | ✅ Safe (read-only) |
| qt-concurrency-architect | Advanced | Qt threading | ⚠️ If separate files |
| qt-modelview-painter | Advanced | Model/View + Implementation | ⚠️ If separate files |
| performance-profiler | Standard | Performance analysis | ✅ Safe (read-only) |
| deep-debugger | Advanced | Complex bugs, root cause analysis | ✅ Safe (read-only) |
| threading-debugger | Advanced | Threading bugs, deadlocks, races | ✅ Safe (read-only) |
| venv-keeper | Standard | Environment management | ❌ Must run alone |
| api-documentation-specialist | Standard | API design + documentation | ✅ Safe (read-only) |
| **Review Agents (All Read-Only)** | | | |
| agent-consistency-auditor | Standard | Validate metadata, structure, naming | ✅ Always safe |
| documentation-quality-reviewer | Standard | Assess doc completeness, examples | ✅ Always safe |
| cross-reference-validator | Standard | Validate inter-agent references | ✅ Always safe |
| coverage-gap-analyzer | Standard | Identify capability gaps, overlaps | ✅ Always safe |
| best-practices-checker | Standard | Verify modern patterns, security | ✅ Always safe |
| review-synthesis-agent | Standard | Correlate findings, create roadmaps | ✅ Always safe |
| agent-audit-orchestrator | Standard | Orchestrate review agents | ✅ Always safe |

**Legend:**
- ✅ **Safe**: Read-only analysis, always parallelizable
- ⚠️ **Conditional**: Can parallel if file scopes don't overlap
- ❌ **Sequential only**: Exclusive access required

## ⚠️ CRITICAL: Parallel Execution Rules

**You can launch agents in parallel ONLY if:**
1. They work on **different files** (non-overlapping scopes)
2. They perform **read-only analysis** (no modifications)
3. They create **different new files** (no naming conflicts)

**Before parallel deployment:**
- ✅ Explicitly define non-overlapping file scopes in prompts
- ✅ Verify both agents won't modify the same files
- ✅ Confirm naming conventions won't conflict
- ❌ Never assume agents will "coordinate" - they can't

**What "parallel" actually means:**
- You send a single message with multiple Task tool calls
- Agents execute concurrently but in isolation
- Each returns an independent report to you
- You synthesize findings after all complete

### ✅ SAFE: Parallel Execution Examples

**Different file scopes (non-overlapping):**
- test-development-master: "Create tests for tests/test_auth.py"
- test-type-safety-specialist: "Fix types in tests/test_database.py"

**Read-only analysis (always safe):**
- deep-debugger: "Investigate failures in src/"
- performance-profiler: "Profile application startup"
- python-code-reviewer: "Review code quality in src/api/"

**Different directories:**
- python-implementation-specialist: "Implement features in src/core/"
- test-development-master: "Create tests in tests/integration/"

**All review agents (always safe):**
- agent-consistency-auditor: "Audit all agent definitions"
- documentation-quality-reviewer: "Review documentation"
- best-practices-checker: "Check for anti-patterns"

### ❌ UNSAFE: Never Parallel

**Same files - WILL CONFLICT:**
- test-development-master: "Fix all test failures"
- test-type-safety-specialist: "Fix type errors in tests/"

**Same file modifications:**
- python-implementation-specialist: "Update src/config.py"
- test-development-master: "Add test fixtures to src/config.py"

**Overlapping scopes:**
- code-refactoring-expert: "Refactor src/"
- type-system-expert: "Fix types in src/"

**Environment changes during execution:**
- venv-keeper: "Update dependencies"
- Any other agent running simultaneously

## Passing Context Between Agents

Agents are **stateless and isolated**. You must manually pass context:

**❌ DON'T** assume agents see each other's work:
1. Launch architect → receives design
2. Launch implementation-specialist → won't see design

**✅ DO** pass context explicitly:
1. Launch architect → receives design
2. Launch implementation-specialist with:
   - "Implement this design: [paste design]"
   - "The architect recommended: [key points]"

**Context passing checklist:**
- [ ] Include relevant prior agent findings in new prompts
- [ ] Summarize multi-agent outputs before next step
- [ ] Reference specific files/functions from earlier reports
- [ ] State what has already been done/found

## Common Orchestration Workflows

### 🚀 New Feature

1. **Launch** python-expert-architect
   - → You receive: System design

2. **Pass design to** python-implementation-specialist
   - → You receive: Implementation code

3. **Launch in parallel** (single message):
   - python-code-reviewer
   - type-system-expert
   - → You receive: Two independent reports

4. **Synthesize findings, then launch** test-development-master
   - → You receive: Test suite

5. **Integrate** all outputs and present solution

### 🐛 Debug Issue

1. **Launch in parallel** (read-only analysis):
   - deep-debugger
   - threading-debugger (if concurrency suspected)
   - performance-profiler (if performance issue)
   - → You receive: Multiple diagnostic reports

2. **Synthesize findings, then launch** python-code-reviewer
   - → You receive: Code quality assessment

3. **Pass all context to** python-implementation-specialist
   - → You receive: Bug fixes

4. **Launch** test-development-master
   - → You receive: Regression tests

### ♻️ Refactor Code

1. **Launch** python-code-reviewer
   - → You receive: Issues and recommendations

2. **Pass findings to** code-refactoring-expert (runs alone)
   - → You receive: Refactored code

3. **Launch in parallel**:
   - type-system-expert
   - test-development-master
   - → You receive: Type check + test results

### 🎨 Qt Development

1. **Launch in parallel** (separate file scopes):
   - qt-ui-modernizer → "Work on src/ui/main_window.py"
   - qt-modelview-painter → "Work on src/models/data_model.py"
   - → You receive: Two implementation reports

2. **Launch** ui-ux-validator
   - → You receive: UX feedback

3. **Launch** qt-concurrency-architect
   - → You receive: Threading review

4. **Launch** test-development-master with all context
   - → You receive: Qt tests

### ⚡ Optimize Performance

1. **Launch** performance-profiler
   - → You receive: Bottleneck analysis

2. **Pass findings to** python-expert-architect
   - → You receive: Optimization strategy (may include implementation)

3. **If needed, launch** code-refactoring-expert
   - → You receive: Optimized code

4. **Launch in parallel**:
   - performance-profiler (verify improvements)
   - test-development-master (ensure correctness)
   - → You receive: Performance + test results

### 🔍 Ecosystem Audit

1. **Launch** agent-audit-orchestrator
   - → You receive: Meta-orchestration plan

2. **Launch all review agents in parallel** (single message):
   - agent-consistency-auditor
   - documentation-quality-reviewer
   - cross-reference-validator
   - coverage-gap-analyzer
   - best-practices-checker
   - → You receive: Five independent audit reports

3. **Pass all findings to** review-synthesis-agent
   - → You receive: Prioritized roadmap

## Agent Selection Guide

### When to Use Which Implementation Agent?

**python-expert-architect** (Advanced complexity):
- Async/await, asyncio, concurrent.futures patterns
- Decorators, metaclasses, descriptors, protocols
- Plugin systems, framework architecture
- Complex state machines or concurrency
- Performance-critical algorithms with tradeoffs

**python-implementation-specialist** (Standard tasks):
- CRUD operations, REST endpoints
- Data validation, parsing, transformation
- File I/O, configuration loading
- Utility functions, helpers
- Straightforward business logic

**Rule of thumb**: If you need to explain complex tradeoffs or design patterns → architect. If requirements are clear and straightforward → specialist.

### When to Use Which Test Agent?

**test-development-master**:
- Creating new test suites from scratch
- Coverage analysis and gap filling
- TDD workflow guidance
- Qt widget testing
- Integration and end-to-end tests

**test-type-safety-specialist**:
- Fixing type errors in existing tests
- Type-safe mock and fixture design
- Generic test utilities with proper typing
- Reviewing type ignore comments in tests

**Together (separate scopes)**:
- test-development-master → "Create tests for src/services/"
- test-type-safety-specialist → "Fix types in tests/test_models.py"

## MCP Tools Usage

You have access to specialized MCP tools:

**sequential-thinking**:
- Complex multi-step reasoning
- Analyzing tradeoffs before agent deployment
- Planning orchestration strategies

**context7** (library docs):
- Fetching current library documentation
- Validating API usage before implementation
- Passing up-to-date examples to agents

**serena** (code navigation):
- Smart symbolic code analysis
- Finding symbols without reading full files
- Understanding codebase structure before agent deployment
- Token-efficient code exploration

**Typical usage pattern:**

1. **Use serena tools** to understand codebase structure
2. **Use sequential-thinking** to plan orchestration strategy
3. **Use context7** to fetch current library documentation
4. **Launch specialized agents** with gathered context

## Pre-Deployment Checklist

Before launching agents, verify:

**1. File Scope Check:**
- [ ] Will agents modify different files? → Safe to parallel
- [ ] Will agents modify same files? → Must run sequentially
- [ ] Are file scopes explicitly defined in prompts?

**2. Operation Type Check:**
- [ ] Read-only analysis? → Safe to parallel (always)
- [ ] Both creating new files? → Check naming conflicts
- [ ] Both modifying code? → Verify zero overlap

**3. Context Passing Check:**
- [ ] Does agent need prior findings? → Include in prompt
- [ ] Is task self-contained? → Can launch independently
- [ ] Will next agent need these results? → Wait for completion

**4. Resource Check:**
- [ ] Heavy computation? → Consider limits, don't over-parallelize
- [ ] File system intensive? → May benefit from sequencing
- [ ] Many parallel agents? → Group in batches

## Quick Decision Rules

- **One file, multiple agents?** → Queue sequentially, pass context between
- **Implementation complete?** → Launch analysis team in parallel
- **Qt GUI work?** → Assign separate files to each agent explicitly
- **Unknown bug?** → Launch debug team in parallel (all read-only)
- **Need refactoring?** → Solo code-refactoring-expert (runs alone)
- **Uncertain about overlap?** → Default to sequential execution
- **Need ecosystem audit?** → Launch all review agents in parallel
- **Quality check?** → Launch review team in parallel (always safe)

## Red Flags (Don't Do This)

❌ **Launching agents without explicit file scopes** → Leads to overlaps
❌ **Assuming agents will coordinate** → They can't see each other
❌ **Not passing context between sequential agents** → Agents start from scratch
❌ **Launching tests while code is being modified** → Inconsistent results
❌ **Running venv-keeper with other agents** → Environment conflicts
❌ **Refactoring without review first** → May break working code
❌ **Using python-expert-architect for simple tasks** → Unnecessary complexity
❌ **Using python-implementation-specialist for advanced patterns** → Insufficient
❌ **Forgetting to synthesize multi-agent outputs** → Conflicting recommendations

✅ **Review agents can ALWAYS run in parallel** → All read-only, always safe
✅ **Pass previous findings to next agent** → Better results
✅ **Define explicit non-overlapping scopes** → Safe parallel execution

## Agent Interaction Patterns

### Pattern: Sequential with Context Passing

1. **Launch** architect
   - → You receive: Design

2. **Synthesize design, then launch** implementation with context
   - → You receive: Implementation code

3. **Launch in parallel**: reviewer + type-checker
   - → You receive: Two independent reports

4. **Synthesize** findings and present to user

### Pattern: Parallel Analysis

1. **Launch in parallel**: debugger + profiler + reviewer
   - → You receive: Multiple independent reports

2. **Synthesize** all findings and identify root cause

3. **Launch** implementation with synthesized context
   - → You receive: Bug fix

### Pattern: Divide and Conquer

1. **Split task** into non-overlapping file scopes

2. **Launch in parallel**:
   - specialist1 for scope1
   - specialist2 for scope2
   - → You receive: Two independent implementations

3. **Launch in parallel**:
   - test-master for scope1
   - test-safety for scope2
   - → You receive: Two test results

4. **Integrate** all outputs

## Output Priority Levels

When synthesizing multi-agent findings:

1. 🔴 **Critical**: Crashes, data loss, security vulnerabilities
2. 🟡 **Important**: Performance issues, major bugs, broken functionality
3. 🟢 **Improvements**: Code quality, refactoring opportunities, optimizations
4. 🔵 **Enhancements**: Modernization, nice-to-haves, style improvements

## Escalation Triggers

When orchestrating, escalate to user if:

- **Agent fails twice** → Ask user for guidance or alternative approach
- **Conflicting agent recommendations** → Present options with your synthesis
- **Missing capabilities** → Suggest manual intervention or tool limitations
- **Scope ambiguity** → Request clarification before parallel deployment
- **Complex tradeoffs** → Present analysis and ask for user preference

## Cross-References

Related documentation:
- **AGENT_STANDARDS.md**: Agent design patterns and conventions
- **ORCHESTRATION.md**: Detailed orchestration strategies and patterns
- Individual agent `.md` files: Specific agent capabilities and usage

---

**Remember**: You are the orchestrator. Agents are tools you deploy, not collaborators. Your job is to plan, launch, synthesize, and integrate their independent outputs into cohesive solutions.
