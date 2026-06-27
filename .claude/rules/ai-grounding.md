# AI Grounding & Verification Rules

How an AI assistant must reason, ground itself, and self-verify when working in
this repository. These are behavioural rules for the assistant — complementary
to the architecture/style rules in this directory, not a substitute for them.

## Strict source fidelity
- You are restricted to the provided context. If an answer cannot be derived from
  the repository files, explicitly state: *"I do not have enough information to
  answer this based on the current codebase."*
- Do not hallucinate external configurations or framework features.

## Step-by-step reasoning
- For any code change or test generation, first output your logical plan, then the
  implementation.
- Verify the implementation against the architectural boundaries defined in
  `framework-rules.md`, `code-style.md`, and `testing-standards.md`.

## Verification protocol
- Before finalizing any code, self-critique:
  - Does it respect the `src/` vs `tests/` import boundaries?
  - Does it use the correct `Environment` objects and YAML configurations?
  - Does it adhere to the `BaseReporter` / `BaseValidator` contracts?

## Deterministic output
- Prioritize existing codebase patterns over generic solutions.
- If a requested task contradicts an established convention, flag the conflict
  before proceeding.
