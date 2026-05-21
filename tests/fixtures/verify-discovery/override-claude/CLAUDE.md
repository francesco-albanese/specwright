# Fixture project — explicit verify override

## Specwright — Verify Commands

```yaml
test: make test-ci
lint: make lint-ci
format: make fmt-check
typecheck: make types
build: make release
```

## Other notes

Override section above should beat both the package.json and any ecosystem default.
