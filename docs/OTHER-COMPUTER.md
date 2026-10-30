# Continue working on Ivy from another computer

## Connected services

- Code: https://github.com/carlaregiane-lab/Ivy
- Browser editor: https://github.dev/carlaregiane-lab/Ivy
- Website: https://ivy-beta.vercel.app
- Vercel project: https://vercel.com/evy4/ivy
- Build root: `Dashboard`; production branch: `main`; Node.js: `24.x`.

GitHub and Vercel are connected. Commits pushed to `main` automatically build
and publish the website. Use a feature branch for a preview before production.

## One-time setup

1. Install the ChatGPT/Codex desktop app and sign in with the same ChatGPT account.
2. Sign in to GitHub as `carlaregiane-lab`, and to the Vercel team `evy4`.
3. Install Git and Node.js 24. Python 3.11+ is needed only for `Projeto/`.
4. Clone https://github.com/carlaregiane-lab/Ivy.git using GitHub Desktop, or run:

   ```powershell
   git clone https://github.com/carlaregiane-lab/Ivy.git
   cd Ivy
   ```

5. Open the cloned `Ivy` folder as a project in Codex. Ask Codex to read
   `AGENTS.md` and this guide before continuing development.
6. In `Dashboard/`, run `npm ci`, then `npm run dev`. Open http://localhost:3000.

Signing in with the same ChatGPT account does not copy a local folder to the
new computer. Clone this repository to get the code and development handoff.

## Edit from a browser

For a small change, open https://github.com/carlaregiane-lab/Ivy, sign in to
GitHub, open the source file and choose Edit. Review and commit the change.
For changes spanning multiple files, open https://github.dev/carlaregiane-lab/Ivy
to browse and edit the repository, then commit and push from its Source Control
panel. The browser editor does not run the app or its tests; use the local setup
above or a Vercel preview to validate changes. These commits publish automatically through the connected Vercel project.

## Live AI on the development computer

The web app uses Vercel AI Gateway, not the desktop ChatGPT login. The deployed
website uses the Vercel project's authentication and environment settings.

Vercel OIDC is enabled for the Git-connected project `ivy`. Ivy reads its trusted request
credential at runtime, so no Gateway key needs to be committed or copied between
production deployments. At the transfer check on October 30, 2026, Vercel reached
the Gateway but required account activation with a valid payment method before
serving AI requests. Complete that step directly in the Vercel dashboard if the
same activation message is still shown. Local engineering test mode and the
website's interface can be used independently of that activation.

To run with the existing Vercel configuration locally, run these commands from
`Dashboard/` and complete Vercel's sign-in in your browser:

```powershell
npx vercel login
npx vercel link --project ivy --scope evy4
npx vercel env pull .env.local --environment development --scope evy4
npm run dev
```

If AI credentials are unavailable, the app uses its local engineering test mode.
`GET /api/chat` reports `gateway` or `local`. A `gateway` result means credentials
are present; a successful chat response is the actual AI connectivity check.
For a standalone Gateway key, use `Dashboard/.env.example` as the template and
enter your key only in the ignored `Dashboard/.env.local` file. Never put a key
in chat, source code, GitHub or a screenshot.

The optional Python assistant uses `OPENAI_API_KEY` and `IVY_MODEL` in the
computer's environment, independently of the web app's Gateway credentials.
Its default model and commands are documented in `Projeto/README.md`.

## Each time you change computers

Before editing, open the repository folder and download the latest code:

```powershell
git pull --ff-only
```

After editing, validate the dashboard from `Dashboard/`:

```powershell
npm run test:unit
npm run lint
npm run build
```

Then return to the repository root, review the files and save your changes:

```powershell
git status
git add <the-files-you-reviewed>
git commit -m "Describe the Ivy change"
git push
```

GitHub Desktop provides Fetch/Pull, file review, Commit, and Push controls for
the same workflow. Push completed work before switching computers. If you have
unfinished changes on the other computer, save them to a branch and push that
branch. Do not force-push to resolve a synchronization problem.

Pushes to `main` publish on Vercel; other
branches create previews. Check the Vercel build result before assuming a change
is live. The build root must remain `Dashboard`, with framework `Next.js`.

## Where the AI lives

- Instructions, model, tool selection: `Dashboard/lib/agents/ivy-agent.ts`.
- Tools: `Dashboard/lib/tools/`.
- Chat validation and streaming: `Dashboard/app/api/chat/route.ts`.
- Calculations and checks: `Dashboard/lib/engineering/`.
- Original Python AI: `Projeto/src/ivy_lab/assistant.py` and `interpreter.py`.

## Saved conversations and projects

The dashboard stores conversations and projects in the browser on each device.
The Python assistant stores its memory in `Projeto/data/ivy_memory.json`.
Those records are not included in this public code repository. A separate,
private export or a future authenticated database is needed to transfer them.
