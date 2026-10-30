# Ivy

Ivy's web interface, AI agent, engineering tools, and original Python assistant.

- **Code:** https://github.com/carlaregiane-lab/Ivy
- **Website:** https://ivy-beta.vercel.app
- **Vercel:** https://vercel.com/evy4/ivy
- **Continue on another computer:** [setup guide](docs/OTHER-COMPUTER.md)

## What to edit

| Folder or file | Purpose |
| --- | --- |
| `Dashboard/app/` | Website, layout and chat endpoint |
| `Dashboard/lib/agents/ivy-agent.ts` | AI instructions, model and tools |
| `Dashboard/lib/tools/` | Tools the AI can call |
| `Dashboard/lib/engineering/` | Engineering calculations and verification |
| `Dashboard/components/` | Interface components |
| `Projeto/src/ivy_lab/` | Independent Python assistant |

## Run the website

Install Git and Node.js 24, then:

```powershell
git clone https://github.com/carlaregiane-lab/Ivy.git
cd Ivy/Dashboard
npm ci
npm run dev
```

Open http://localhost:3000. Without Vercel AI Gateway credentials the app uses
its local engineering test mode. See the setup guide to enable live AI locally.

## Validate

From `Dashboard/`:

```powershell
npm run test:unit
npm run lint
npm run build
```

The Python assistant has its own [instructions](Projeto/README.md).

## Publication and saved data

The Vercel project `ivy` is connected to this repository, with production branch
`main` and root directory `Dashboard`. Pushing to `main` starts a production
build automatically. Feature branches get preview deployments.

Git transfers code. Browser conversations and locally saved Python projects do
not synchronize through GitHub or your ChatGPT account. Credentials, local
memory, caches and generated outputs are deliberately excluded.
