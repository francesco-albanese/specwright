# Fixture — malformed override

The block below opens a fence but never closes it before EOF. The whole
section should be ignored and discovery should fall through to the npm
defaults from `package.json`.

## Specwright — Verify Commands

```yaml
test: this-should-be-ignored
lint: this-too
