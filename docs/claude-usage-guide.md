# Efficient Claude Usage Guide

Practical strategies for using Claude models across different task types. Derived from real workflows in this project (refactoring, design, planning, debugging).

---

## Model Selection by Task

| Task Type | Best Model | Why |
|-----------|-----------|-----|
| Architecture planning | Opus | Needs deep reasoning about dependencies, risk assessment, phase ordering |
| Multi-file refactoring | Opus | Must hold full project context, understand import chains |
| Bug investigation | Opus | Requires hypothesis generation, cross-file analysis |
| Code review / analysis | Opus or Sonnet | Sonnet handles straightforward reviews; Opus for subtle issues |
| Single-file feature | Sonnet | Fast, sufficient context, cheaper |
| Boilerplate / scaffolding | Sonnet or Haiku | Mechanical generation, low reasoning needed |
| Commit messages / docs | Haiku | Cheapest, fast, good enough for formulaic output |
| Explaining code | Sonnet | Good at clear explanations without overthinking |
| Config / YAML / env changes | Haiku | Minimal reasoning, pattern matching |
| Design system prompts | Opus | Creative + precise constraint satisfaction (like miniapp-design-prompt.md) |

**Rule of thumb:** Use the cheapest model that won't make you redo the work.

---

## Task Type Strategies

### 1. Planning & Architecture (like refactor-plan.md)

**What worked in this project:** The 5-phase layered architecture refactor was planned upfront with clear phases, rollback strategies, and "working version guarantee" after each phase. Total execution: 1.5 hours for ~3400 lines.

**Token-efficient approach:**
- Give Claude the full project tree + key files in ONE prompt
- Ask for the complete plan in one shot rather than iterating
- Include constraints upfront ("each phase must result in working app", "files under 150 lines")
- Request structured output (tables, checklists) -- easier to execute later

**Prompt template:**
```
Here is my project structure: [tree output]
Here are the key files: [paste 2-3 most relevant files]

I need a plan to [goal]. Constraints:
- [constraint 1]
- [constraint 2]

Output format: phases with steps, effort estimates, rollback plan, and verification checklist.
```

**Anti-pattern:** Don't ask Claude to plan iteratively ("what should I do first?" then "ok what next?"). Each round-trip costs context. Get the full plan in one shot, then execute.

### 2. Analysis & Audit (like structure-deadcode-refactoring.md)

**What worked:** Claude analyzed the entire codebase and found dead code, inconsistent imports, broken scripts, and backward-compat issues in one pass.

**Token-efficient approach:**
- Use `grep`/`glob` to gather data BEFORE sending to Claude
- Send focused context: "here are all imports of X" rather than "read every file"
- Ask Claude to output findings as a table with file:line references
- Combine analysis + fix plan in one request

**Prompt template:**
```
I want to find [dead code / inconsistent imports / etc] in this project.

Here's the project structure: [tree]
Here are the relevant grep results: [paste grep output]

List all findings as a table: | Item | Location | Issue | Fix |
Then write a phased fix plan.
```

**Anti-pattern:** Don't ask Claude to "look at each file" one by one. Feed it aggregated data and let it reason across the whole set.

### 3. Multi-File Refactoring (like the decomposition-plan.md execution)

**What worked:** The state.py decomposition (531 lines -> 6 files) was planned with explicit import-site tracking.

**Token-efficient approach:**
- Plan first (cheap), execute second (unavoidable token cost)
- Track import sites in the plan so you don't rediscover them during execution
- Use Claude Code's parallel tool calls -- move independent files simultaneously
- After each step, verify with `ruff check .` not full manual testing
- Commit atomically per logical unit, not per file

**Key insight from this project:** The refactor used `cp` instead of `mv`, creating 23 dead duplicate files that required Phase 3.5 cleanup. Ask Claude to include cleanup steps in the original plan.

**Prompt template:**
```
Split [file.py] (N lines) into these modules: [list targets]

For each target module, specify:
1. What functions/classes move there
2. What imports they need
3. What callers need updating (grep for current import paths)
4. Estimated line count

Then give me the execution steps with verification after each.
```

### 4. Feature Implementation (like Mini App backend + frontend)

**What worked:** The miniapp was implemented as a complete vertical slice: backend API, React SPA, Docker setup, and Caddy config in one session.

**Token-efficient approach:**
- Start with a comparison/decision doc if multiple approaches exist (like miniapp-comparison.md)
- Once decided, give Claude the full spec in one prompt, not piece by piece
- Let Claude scaffold the whole feature, then iterate on specific parts
- For frontend: describe the UI with ASCII mockups or reference screenshots rather than verbose descriptions

**Model selection within this task:**
- Opus for the initial architecture decision + API design
- Sonnet for implementing individual components/routes
- Haiku for generating boilerplate (schemas, Docker configs)

### 5. Bug Fixing & Async Migration (like async-fix-plan.md)

**What worked:** The async fix plan tracked a ripple effect across 14 files with explicit TODO/DONE status per file.

**Token-efficient approach:**
- Describe the symptom + root cause, let Claude map the blast radius
- Ask for the full dependency chain upfront ("what else breaks if I change X?")
- Fix in topological order (deepest dependency first)
- Group related changes: if 5 files all need the same `await` addition, do them in one prompt

**Prompt template:**
```
I changed [function] from sync to async. This ripples through callers.

Here are the current callers: [grep output]

Map the full dependency chain and give me a fix order (deepest first).
For each file: what line changes, and what to verify.
```

### 6. Design Docs & System Prompts (like miniapp-design-prompt.md)

**What worked:** The design prompt was highly structured with explicit visual specs (spacing, colors, typography tables, ASCII mockups).

**Token-efficient approach:**
- Be extremely specific in constraints -- ambiguity costs iteration tokens
- Include reference screenshots/mockups
- Specify output format explicitly ("produce full-page mockup", "use these exact CSS variables")
- For LLM system prompts: test with cheap model (Haiku) first, refine with Opus only if needed

### 7. CI/CD & Deployment (like deploy-notifications-plan.md)

**Token-efficient approach:**
- These are usually small, well-scoped changes -- use Sonnet or Haiku
- Paste the existing workflow file + describe desired change
- Ask for the diff, not a full rewrite
- Include required secrets/env vars in the plan

---

## General Token-Saving Techniques

### Context Management

1. **Front-load context, don't drip-feed.** One prompt with tree + key files + constraints beats 5 rounds of Q&A.

2. **Use grep/glob results as context.** Instead of "read all handlers", paste `grep -rn "from state import" --include="*.py"` output. Claude reasons on search results faster than on raw files.

3. **Reference files by path, don't paste contents.** In Claude Code, say "read file X" and let it use tools. In API, paste only the relevant sections with line numbers.

4. **Kill stale context.** Long conversations accumulate irrelevant history. For a new task, start a new conversation rather than continuing one from hours ago.

### Prompt Engineering

5. **Specify output format.** "Output as a markdown table with columns: File | Change | Verification" saves back-and-forth.

6. **Include negative constraints.** "Don't add docstrings to unchanged code" / "Don't create abstractions for one-off operations" prevents over-engineering that you'll have to undo.

7. **Use CLAUDE.md as persistent context.** The project's CLAUDE.md file is auto-loaded in every Claude Code session. Put architecture decisions, code conventions, and common pitfalls there instead of repeating them in prompts.

8. **Ask for plans before execution.** Plans are cheap (few output tokens). Wrong execution is expensive (many output tokens + undo work). Use `/plan` mode for non-trivial tasks.

### Workflow Patterns

9. **Batch related changes.** Don't make 10 separate requests to add `await` to 10 files. Show Claude the pattern once, list all sites, and let it fix them all.

10. **Use subagents for parallel research.** In Claude Code, the Agent tool runs independent searches in parallel without polluting the main context window.

11. **Checkpoint with git.** Commit after each phase. If Claude goes wrong, `git diff` shows exactly what happened. Cheaper than re-reading and explaining the problem.

12. **Track progress in docs, not conversation.** This project used refactor-progress.md to track state across sessions. The conversation context is ephemeral; the docs persist.

---

## Cost Comparison (Approximate)

| Model | Input ($/1M tokens) | Output ($/1M tokens) | Best For |
|-------|---------------------|----------------------|----------|
| Opus 4.6 | $15 | $75 | Complex reasoning, multi-file refactors, architecture |
| Sonnet 4.6 | $3 | $15 | Single-file features, code review, explanations |
| Haiku 4.5 | $0.80 | $4 | Boilerplate, commit messages, config changes, docs |

**Example savings:** A commit message generation task uses ~500 input + ~100 output tokens.
- Opus: $0.015 per message
- Haiku: $0.0008 per message (~19x cheaper)

For 100 commits/month, that's $1.50 vs $0.08. Small per-task, but compounds.

---

## Claude Code-Specific Tips

1. **Use `/compact` when context gets large.** It summarizes the conversation, freeing space for more work.

2. **CLAUDE.md is your leverage point.** Every rule there saves you from repeating instructions. This project's CLAUDE.md is 200+ lines and pays for itself every session.

3. **Use Plan mode (`/plan`) for risky changes.** Claude proposes, you approve, then it executes. Catches wrong approaches before they cost output tokens.

4. **Prefer dedicated tools over Bash.** `Read` instead of `cat`, `Edit` instead of `sed`, `Grep` instead of `grep`. They're shown to the user with better formatting and are safer.

5. **Let Claude mark todos.** TodoWrite tracks progress across tool calls. When Claude resumes after context compression, the todo list persists.

6. **Memory for cross-session knowledge.** Save user preferences, project decisions, and non-obvious patterns to memory. Saves re-explaining in future sessions.

---

## Anti-Patterns (Things That Waste Tokens)

| Anti-Pattern | Why It Wastes Tokens | Better Approach |
|-------------|---------------------|-----------------|
| "Read every file in src/" | Floods context with irrelevant code | Grep for specific patterns, read only hits |
| Iterative planning ("what next?") | Each round-trip costs input+output | Get full plan in one shot |
| Pasting entire files for small changes | 90% of tokens are wasted context | Paste only relevant section with line numbers |
| Asking Claude to "improve" without specifics | Generates unwanted refactoring | Specify exact changes needed |
| Re-explaining project context each session | Repeats hundreds of tokens | Put it in CLAUDE.md or memory |
| Not committing between phases | Can't diff or rollback, must re-explain | `git commit` after each logical unit |
| Using Opus for "add a comment" | Overkill for trivial tasks | Use Haiku or just do it yourself |
| Asking for explanations you won't use | Output tokens with no value | Ask only what affects your next action |

---

## Task-Specific Checklists

### Before Starting a Refactor
- [ ] Run `tree` and `wc -l` to size the scope
- [ ] Grep for all imports/callers of code being moved
- [ ] Commit current state (clean baseline)
- [ ] Ask Claude for plan FIRST (plan mode)
- [ ] Review plan, then switch to execution

### Before Starting a Feature
- [ ] Check if similar patterns exist in the codebase
- [ ] Decide: new file or extend existing?
- [ ] List all files that will need changes
- [ ] Define the API/interface before implementation
- [ ] Have Claude scaffold everything, then refine

### Before Asking Claude to Fix a Bug
- [ ] Reproduce the error (paste exact traceback)
- [ ] Grep for the function/variable involved
- [ ] Check git blame for recent changes to that area
- [ ] Send Claude: error + relevant code + recent changes

---

## Summary

The biggest token savings come from:
1. **Choosing the right model** (Haiku for trivial, Opus for complex)
2. **Front-loading context** (one rich prompt > five shallow ones)
3. **Planning before executing** (plans are cheap, wrong code is expensive)
4. **Using CLAUDE.md** (persistent context saves repetition)
5. **Batching related changes** (one prompt for 10 similar fixes)
