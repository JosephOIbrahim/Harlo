# Key rotation — `ANTHROPIC_API_KEY`

Harlo's only cloud credential is `ANTHROPIC_API_KEY` (the daemon reads it from
the environment — `provider/claude.py`). Rotate it whenever it may have been
exposed.

## One command

```bash
make rotate-key            # or: bash scripts/rotate_anthropic_key.sh
```

Paste the new key when prompted (input is hidden). The script:

1. **Validates** the key against the Anthropic API *before* changing anything.
2. Sets it for the current login session (`launchctl setenv`).
3. **Persists** it across reboots via a `chmod 600` login agent.
4. Bounces the Harlo daemon so it picks up the new key.

The key is **never** printed, logged, or passed as a shell argument.

## Then, in the Anthropic console

`console.anthropic.com → Settings → API Keys` → **delete the old key**. That is
the step that actually neutralizes the old credential; the script only swaps in
the new one locally.

## Note

The Harlo MCP server (the default coaching surface) uses **no** Claude
credential at all — only the `twin ask` CLI path calls the API. So rotating the
key never disrupts the MCP coaching path.
