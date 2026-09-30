# Workspace browser tests

Runs the real Vue frontend in installed Google Chrome. The Playwright config starts a dedicated Vite server at `127.0.0.1:5176` with `--strictPort`; it never reuses the old frontend on 5173 or the main developer server on 5175.

Chrome is selected using Playwright's `chrome` channel; set `PLAYWRIGHT_EXECUTABLE_PATH` to override the browser executable. Vite uses the current Node `process.execPath`, quoted to support paths containing spaces. The absolute Node path below is only this Windows workspace's invocation example; other machines can use `npm run test:browser`.

From `frontend` in PowerShell:

```powershell
& 'C:/Program Files/nodejs/node.exe' node_modules/@playwright/test/cli.js test --config playwright.config.js
```

To also observe the actual backend login-options response through Vite's configured 28080 proxy:

```powershell
$env:WORKSPACE_LIVE = '1'
& 'C:/Program Files/nodejs/node.exe' node_modules/@playwright/test/cli.js test --config playwright.config.js
Remove-Item Env:WORKSPACE_LIVE
```

`workspace.fixture.js` intercepts only URL paths starting `/api/` using `page.route`. It records every request and rejects unconfigured endpoints. It never patches components, store state, router behavior or production APIs. Normal scenarios log in through the form; startup scenarios seed only a token plus deliberately stale legacy identity cache to verify `/users/me` is authoritative. Main API responses use `{ code: 0, data }`; consultation responses use `{ code: 'SUCCESS', data }`.

The opt-in live test uses no interception and performs only a GET of login options. It records either the actual HTTP response or `requestfailed` (including Axios timeout aborts), and verifies visible error/retry behavior for a real failure. An observation pass does not imply backend health. The separately named fixture failure test injects HTTP 500 and labels its screenshot accordingly.

Screenshots, failure traces and JSON results are in `frontend/test-results/workspace-browser*`. Output is refreshed on each run. Browser tests demonstrate rendered UI and request behavior against controlled responses. They do **not** verify real backend business writes, authorization enforcement or persistence.
