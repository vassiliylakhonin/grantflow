# Website to JSON

Claw0x skill starter for extracting structured JSON from public pages.

Files:
- `handler.ts`
- `server.mjs`
- `SKILL.md`
- `package.json`

Run locally:

```bash
npm install
npm run dev
```

Railway setup:

1. Create a new service from this folder.
2. Set the root directory to `skills/website-to-json`.
3. Use the start command `node --import tsx server.mjs`.
4. Set `NIXPACKS_PKGS=ca-certificates` in Railway Variables (required for TLS chain).
5. Add `SKILL_SHARED_SECRET` in Railway Variables if you want auth protection.
6. Add the Railway service URL as the Claw0x endpoint.

Source:
- https://github.com/vassiliylakhonin/grantflow/tree/main/skills/website-to-json
