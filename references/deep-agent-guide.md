# Deep Agent Review Guide

**Read this when**: Running `deep-agent` profile or when scanner reports files needing semantic review.

## What is Deep Agent Analysis?

Deep agent analysis goes beyond pattern matching to understand the **semantic intent** of code. It generates a review guide that helps Claude Code systematically analyze high-risk files.

## When Deep Agent is Triggered

The `deep-agent` profile runs three stages:
1. **quick**: Pattern-based trigger analysis
2. **balanced**: Behavioral dataflow analysis
3. **deep-agent**: Semantic review guide generation

## Understanding the Review Guide Output

When deep agent analysis runs, you'll see findings like:

```
[INFO] DEEP_AGENT_REVIEW_GUIDE: Deep Agent Review: 3 high-risk files need semantic review
[INFO] DEEP_AGENT_FILE_REVIEW: Review required: scripts/process_data.py
```

### Review Guide Structure

Each flagged file includes:
- **Risk score**: Higher = more concerning patterns
- **Risk categories**: Types of patterns found (network, code_execution, etc.)
- **Review notes**: Specific concerns to investigate

## How to Perform Semantic Review

### Step 1: Read the Review Guide Finding

Check the `DEEP_AGENT_REVIEW_GUIDE` finding for the priority order of files to review.

### Step 2: Read Each Flagged File

For each file marked for review:

```bash
# Read the file
Read <file_path>
```

### Step 3: Analyze Semantic Intent

Ask these questions:

#### For Network Code
- Does the URL/domain match the skill's claimed purpose?
- Is the endpoint documented in the description?
- Could the data sent be sensitive?

#### For File Access
- What files are being read? Are they user-provided or system files?
- Is there path traversal protection?
- Are credential files (`.env`, `~/.aws`, etc.) being accessed?

#### For Code Execution (eval/exec/subprocess)
- Is user input being passed to these functions?
- Is there input validation/sanitization?
- Can the execution be constrained to safe operations?

#### For Dynamic Behavior (getattr/setattr/globals)
- Is this obfuscation or legitimate dynamic behavior?
- Can the dynamic resolution be hijacked?

#### For Encoding/Obfuscation
- Why is base64/zlib being used?
- Is this hiding malicious content or just compression?
- Can the decoded content be inspected?

### Step 4: Check Cross-File Concerns

If `DEEP_AGENT_CROSS_FILE_FLOW` is reported:
- Read the data source file(s)
- Read the network sink file(s)
- Trace if data flows from source to sink

## Risk Assessment Framework

| Finding | Severity | Action |
|---------|----------|--------|
| `DEEP_AGENT_REVIEW_GUIDE` | INFO | Review listed files |
| `DEEP_AGENT_FILE_REVIEW` | INFO | Read and analyze specific file |
| `DEEP_AGENT_CROSS_FILE_FLOW` | HIGH | Investigate data exfiltration risk |

## Example Review Workflow

```
[Scanner Output]
[INFO] Deep Agent Review: 2 high-risk files need semantic review
  1. [8 pts] scripts/fetch_data.py (network, data_access)
  2. [5 pts] SKILL.md (review notes: 2 items)

[Your Actions]
1. Read scripts/fetch_data.py
   - Check: What URL is it fetching?
   - Check: Is user data being sent?
   - Check: Is the behavior documented?

2. Read SKILL.md
   - Check: Do instructions override system prompts?
   - Check: Are capability claims accurate?
```

## Integration with Other Findings

Deep agent findings complement other analyzers:
- **Static analyzer**: Finds specific patterns
- **Behavioral analyzer**: Finds dataflow issues
- **Deep agent**: Guides semantic review of complex cases

If deep agent flags a file that static/behavioral also flagged, pay extra attention - multiple detection methods agree it's high-risk.
