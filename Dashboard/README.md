# Ivy — Assistente de Engenharia

Experiência conversacional da Ivy para estruturar e acompanhar qualquer projeto
de engenharia descrito pela pessoa usuária.

## Versão publicada

- Endereço: https://ivy-engineering-command-center.vercel.app
- Plataforma: Vercel
- Framework: Next.js App Router
- Acesso: público, sem login do ChatGPT

## Recursos atuais

- conversa em linguagem natural como tela inicial;
- atalhos para iniciar projetos, planejar cálculos e analisar riscos;
- contexto dinâmico criado somente a partir da conversa atual;
- memória de até 60 mensagens no mesmo navegador e dispositivo;
- chat transmitido em tempo real pelo Vercel AI Gateway;
- montagem virtual da garra de referência em cinco etapas;
- visualização tridimensional com rotação;
- vista CAD para aberturas de 40 e 90 mm;
- parâmetros, verificações, alertas e andamento do projeto;
- aviso permanente de que simulação e validação exigem evidências;
- bloqueio explícito contra declarações prematuras de segurança ou fabricação.

O PRJ-001 permanece somente como exemplo visual do workspace CAD. Ele não é
injetado automaticamente nas respostas. Cada nova conversa usa o projeto que a
pessoa descreve e não reaproveita requisitos de exemplos anteriores.

## Uso local

Requer Node.js 22 ou superior.

```bash
npm install
npm run dev
```

Para validar uma alteração antes da publicação:

```bash
npm run build
npm run lint
```

## Publicação e atualizações

A aplicação foi convertida do ambiente Sites/vinext para Next.js nativo e pode
ser publicada diretamente na Vercel. O código do dashboard e da agente de IA
está em https://github.com/carlaregiane-lab/Ivy, na pasta `Dashboard/`.
O projeto da Vercel usa essa pasta como diretório raiz e `main` como branch
de produção. Com a integração Git conectada, cada atualização enviada à branch
principal inicia uma nova publicação automaticamente.

Para continuar em outro computador, leia [o guia de configuração](../docs/OTHER-COMPUTER.md).
As instruções e o modelo da agente ficam em `lib/agents/ivy-agent.ts`; as
ferramentas ficam em `lib/tools/`. A memória do navegador e as credenciais não
são transferidas pelo repositório.

## Limite de engenharia

O dashboard representa um modelo conceitual e uma interface de acompanhamento.
Ele não substitui análise estrutural, simulação cinemática, revisão humana,
ensaios físicos ou validação formal de segurança.
