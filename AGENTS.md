# Frontier Lab10 Hackathon — Agent Engineering Guidelines

## Objective
Build hiring-loop-grade, production-ready software evaluated against **hidden test suites**, strict engineering standards, and real-world system architecture benchmarks.

## Core Rules for Code Generation
1. **Pass Hidden Test Suites**:
   - Never write code that only satisfies happy paths or visible sample cases.
   - Always guard against empty inputs, null pointers, off-by-one indices, type mismatches, and network/timeout failures.
   - For async code, ensure re-entrancy safety, deadlock prevention, and proper error propagation.
2. **Architecture & Foundation**:
   - Write strongly typed code with modular boundaries and explicit interfaces.
   - Separate pure business logic from I/O and external adapters for trivial testability.
3. **Comprehensive Testing**:
   - For every feature implemented, write adversarial test cases covering edge and boundary conditions.

## Model Strategy in Pi (`Ctrl + P` to switch)
- `openrouter/anthropic/claude-sonnet-5.5`: Core feature implementation & daily coding.
- `openrouter/anthropic/claude-opus-5.5`: Top-level system design & complex refactors.
- `openrouter/openai/o3-mini-high`: Cracking failing edge-case tests & algorithmic logic.
- `openrouter/google/gemini-3.1-pro-preview`: Ingesting entire specs, docs, and whole-repo audits.
- `openrouter/x-ai/grok-4.7`: Generating adversarial test suites to uncover hidden bugs.
