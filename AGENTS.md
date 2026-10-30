# Ivy development handoff

This repository includes the Next.js web app in `Dashboard/` and the independent
Python assistant in `Projeto/`. Read each folder's README and applicable AGENTS.md.

## Web app

- Run commands from `Dashboard/` using Node.js 24 and `npm ci`.
- Validate changes with `npm run test:unit`, `npm run lint`, and `npm run build`.
- AI behavior: `Dashboard/lib/agents/ivy-agent.ts`.
- AI tools and engineering logic: `Dashboard/lib/tools/` and `Dashboard/lib/engineering/`.
- Chat endpoint: `Dashboard/app/api/chat/route.ts`.
- Keep engineering assumptions explicit. Never claim physical safety or readiness
  to manufacture without evidence, review and tests.

## Python assistant

- Requires Python 3.11+. Install with `python -m pip install -e ./Projeto`.
- Run tests from `Projeto/` with `python -m unittest discover -s tests`.
- Personal state is in `Projeto/data/` and must stay out of Git.

## GitHub and Vercel

- Repository: https://github.com/carlaregiane-lab/Ivy
- Production branch: `main`.
- Git-connected Vercel project: `ivy`, team `evy4`.
- Website: https://ivy-beta.vercel.app
- Vercel project ID: `prj_RZntc6EvkDHFeID8oePQYoBGdGm7`.
- Vercel builds from `Dashboard/` using the Next.js framework.
- Push only reviewed source and documentation. Never commit environment values,
  service authentication files, personal conversations or generated output.
- Do not change the production model or deployment access settings as a side
  effect of unrelated work.
- Read `docs/OTHER-COMPUTER.md` for setup and the daily synchronization workflow.
