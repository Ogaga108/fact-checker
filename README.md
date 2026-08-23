# Fact Checker

LLM fact verification with optional source URL cross-check.

Built with [GenLayer](https://genlayer.com) intelligent contracts: deterministic
on-chain state plus nondeterministic LLM/web calls settled by validator
consensus (`gl.vm.run_nondet_unsafe`).

## Contract

- Main entry point: `check_claim()`
- Pinned runner: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (genvm v0.3.0-rc7)
- Storage: `TreeMap`/`DynArray`/`u256`; payouts via `emit_transfer(on="finalized")`
- All LLM/web access happens inside leader/validator closures; expected user
  errors use the `[EXPECTED]` prefix.

## Tests

Direct-mode tests mock all LLM/web nondeterminism (no network needed):

```
python -m pytest tests/direct -v
```

Requires the packages in `requirements.txt`.

## Layout

```
contracts/   intelligent contract source
tests/       direct-mode pytest suite
```

## Deployment

Deployed on GenLayer studionet as `FactChecker` at `0x84237Ce1D2e97C7cb77942120cEc3793E07cB912`.
See the root `DEPLOYMENTS.md` in the workspace bundle for the full registry.
