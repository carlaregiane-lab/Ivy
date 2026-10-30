# Ivy Lab

Ivy é uma assistente de trabalho e engenharia em desenvolvimento. Ao ser
aberta, ela mantém uma conversa contínua, guarda tarefas e notas localmente e
pode chamar o módulo de engenharia para transformar uma ideia em um **briefing
de requisitos rastreável**.

## Estado atual

- [x] Contrato de requisitos de engenharia
- [x] Interpretador demonstrativo local
- [x] Integração opcional com a API da OpenAI
- [x] Verificação de riscos antes da análise
- [x] Testes automatizados do primeiro cenário
- [x] Conversa contínua em vez de pergunta única
- [x] Reconhecimento da apresentação do criador
- [x] Tarefas e notas persistentes no computador
- [x] Ações de trabalho e modo de projeto por linguagem natural
- [x] Conversação online opcional com modelo de IA
- [x] Extração contextual de faixas, movimento, cadência, tensão e orçamento
- [x] Cálculos preliminares rastreáveis para o benchmark da garra
- [x] Perguntas adaptativas que não repetem dados já fornecidos
- [x] Alerta de risco para operação próxima a pessoas
- [x] Projetos persistentes com códigos PRJ-001, PRJ-002 e seguintes
- [x] Projeto ativo recuperado depois de fechar e reabrir a Ivy
- [x] Respostas numeradas ligadas às perguntas do briefing
- [x] Lista e troca entre projetos guardados
- [x] Calculadora de engenharia com fórmulas, unidades e fontes de entrada
- [x] Memória de cálculo persistente e controle de revisão desatualizada
- [x] Comparação rastreável de fuso, cremalheira e correia
- [x] Estimativas preliminares de torque, rotação e potência por conceito
- [x] Comparação persistente acionada por linguagem natural
- [x] Histórico versionado de mudanças, cálculos e comparações
- [x] Registro persistente de decisões do projeto
- [x] Verificador independente de valores, unidades, hipóteses e dependências
- [x] Modelo CAD paramétrico preliminar com OpenSCAD, STL, SVG e manifesto
- [x] Verificação independente dos parâmetros e arquivos CAD
- [ ] Simulação estrutural e cinemática
- [ ] Voz, visão e robótica

## Primeiro teste

O pedido de referência é:

> Projete uma garra robótica capaz de levantar um objeto de 500 gramas.

O programa identifica o objetivo e a carga, mas não inventa dimensões,
materiais, velocidade, orçamento ou fator de segurança. Em vez disso, ele
gera perguntas para completar o projeto.

## Benchmark avançado da versão 0.3

A pergunta com garra elétrica de dois dedos, caixas de 40 a 90 mm, carga de
1,5 kg, elevação de 30 cm em 2 s, 12 ciclos/min, alimentação de 12 V, PETG,
orçamento de R$ 600 e trabalho próximo a pessoas é usada como teste de
regressão. A Ivy deve reconhecer todas as restrições, não perguntar novamente
por elas, calcular valores diretamente deriváveis e listar os dimensionamentos
que ainda dependem de dados ausentes.

## Passo 2 concluído na versão 0.4

Cada novo briefing agora é salvo como um projeto identificado. A Ivy mantém um
projeto ativo, registra respostas pelo número original da pergunta e mostra o
progresso da coleta. Essas informações permanecem no computador depois que a
assistente é fechada. Respostas guardadas continuam sendo dados informados pelo
usuário; elas ainda precisam de revisão antes dos cálculos ou de qualquer
conclusão de segurança.

## Passo 3 concluído na versão 0.5

O comando `/calcular` usa somente requisitos e respostas ligados ao projeto
ativo. Cada resultado apresenta identificador, fórmula, substituição, valor,
unidade, classificação e fontes de entrada. No benchmark da garra, a Ivy calcula
peso, cinemática, força normal de aperto, potência mecânica ideal, capacidade
nominal da fonte, cadência e intervalos de vida útil. Torque do atuador,
resistência do PETG, limite de contato humano e custo permanecem bloqueados
enquanto faltarem geometria, ensaios e cotações.

A memória de cálculo fica guardada no projeto. Se uma resposta mudar, a Ivy
marca a revisão anterior como desatualizada e pede um novo cálculo.

## Conversa natural na versão 0.5.1

Os comandos com `/` deixaram de ser obrigatórios. A Ivy agora reconhece pedidos
como “crie um projeto para uma garra”, “como está o projeto?”, “a resposta 1 é
...”, “faça os cálculos”, “mostre o último cálculo”, “anote que ...” e “mostre
minhas tarefas”. Os atalhos antigos continuam disponíveis para compatibilidade.

Perguntas sobre o projeto atual são diferenciadas de pedidos para criar um novo
projeto, evitando duplicações acidentais.

## Passo 4 concluído na versão 0.6

A Ivy agora compara três conceitos mecânicos para a garra: fuso único com
roscas opostas, pinhão com duas cremalheiras e correia sincronizadora com carros
opostos. A comparação usa a força de aperto da memória de cálculo e hipóteses
geométricas explícitas para estimar torque, rotação, velocidade e potência.

No benchmark atual, o fuso é recomendado apenas para detalhamento e teste
virtual. Isso não representa seleção de motor, validação estrutural do PETG ou
declaração de segurança. As conclusões mudam se curso, tempo, eficiência,
atrito, folga ou comportamento em falha forem diferentes das hipóteses.

Para usar essa etapa, diga “compare os mecanismos da garra”. Depois, “mostre os
conceitos” recupera a revisão guardada. Se respostas ou cálculos mudarem, a Ivy
marca a comparação anterior como desatualizada.

## Passo 5 concluído na versão 0.7

Cada projeto agora possui uma revisão geral e uma linha do tempo. Alterações em
respostas, novos cálculos, novas comparações e decisões registradas geram eventos
sequenciais. As versões antigas dos relatórios são preservadas em vez de serem
sobrescritas.

Projetos criados antes da versão 0.7 continuam funcionando. O estado anterior é
preservado como uma fotografia inicial, mas a Ivy não inventa eventos retroativos.
O histórico detalhado começa na primeira alteração feita com a versão nova.

Para consultar, diga “mostre o histórico do projeto” ou “o que mudou no projeto?”.
Para registrar uma escolha, diga por exemplo: “registre a decisão de detalhar o
conceito de fuso porque obteve a maior pontuação”. Depois, “mostre as decisões”
recupera o registro mesmo após fechar e reabrir a Ivy.

## Passo 6 concluído na versão 0.8

A Ivy agora possui um verificador determinístico separado da calculadora e do
comparador de conceitos. Ele recalcula os resultados por uma segunda rotina,
confere unidades, classificação de hipóteses, identificadores, fontes, bloqueios,
revisões e a correspondência entre cada artefato atual e sua fotografia histórica.

Depois de calcular ou comparar mecanismos, a verificação é executada e guardada
automaticamente. Se houver divergência, o uso técnico e a recomendação ficam
bloqueados até a correção. Alterar respostas, refazer cálculos ou criar uma nova
comparação marca a verificação anterior como desatualizada.

Para solicitar uma auditoria completa, diga “verifique o projeto”, “confira os
cálculos” ou “faça uma revisão independente”. Para recuperar a última revisão,
diga “mostre a verificação”. A verificação confirma coerência interna, mas nunca
declara segurança, conformidade normativa ou prontidão para fabricação.

## Passo 7 concluído na versão 0.9

A Ivy agora gera a primeira geometria paramétrica do conceito de fuso com roscas
opostas. O CAD consome somente uma memória de cálculo atual e uma comparação de
conceitos atual. Cada dimensão informa se veio de um requisito, de uma derivação
ou de uma hipótese ainda não confirmada.

Uma revisão produz quatro arquivos: um modelo editável em OpenSCAD (`.scad`),
uma visualização tridimensional em STL (`.stl`), uma prancha vetorial das
aberturas mínima e máxima (`.svg`) e um manifesto rastreável (`.json`). Todos os
arquivos recebem SHA-256 e ficam em uma pasta própria da revisão, sem apagar as
versões anteriores.

O verificador independente recalcula os vinte parâmetros, confere dez regras
geométricas, dois alertas obrigatórios, a origem das revisões, a assinatura dos
parâmetros e o conteúdo dos quatro arquivos. Alterar requisitos, respostas,
cálculos ou conceitos marca o CAD anterior como desatualizado.

Para usar, diga “crie o modelo CAD da garra”. Se a comparação ainda não existir,
a Ivy explica que primeiro precisa ouvir “compare os mecanismos”. Depois, diga
“mostre o último CAD” para recuperar os parâmetros e caminhos dos arquivos.
Esse modelo é apenas virtual: não seleciona componentes e não aprova segurança
ou fabricação.

## Como executar

É necessário ter Python 3.11 ou mais recente.

### Maneira mais fácil no Windows

Abra a pasta `Ivy` na Área de Trabalho e dê dois cliques em
`Executar Ivy.bat`. Quando aparecer `Você >`, converse normalmente com a Ivy.

No primeiro uso, o iniciador cria um ambiente isolado para a Ivy e instala os
componentes necessários. Essa preparação exige internet e pode levar alguns
minutos; depois disso, a abertura será mais rápida.

### Como conversar com a assistente

Fale normalmente: “crie um projeto...”, “como está o projeto?”, “mostre meus
projetos”, “use o projeto 2”, “faça os cálculos”, “mostre o último cálculo”,
“compare os mecanismos”, “mostre os conceitos”, “crie o modelo CAD”,
“mostre o último CAD”, “crie uma tarefa...” ou “anote
que...”. Também é possível dizer “mostre o histórico”, “verifique o projeto” e
“registre a decisão de ... porque ...”. Para responder ao briefing, escreva por exemplo: “a resposta 1
é ...; a resposta 2 é ...”.

Os atalhos `/ajuda`, `/projeto`, `/responder`, `/calcular`, `/calculos`,
`/comparar conceitos`, `/conceitos`, `/verificar`, `/verificacao`, `/historico`, `/decisao`, `/decisoes`,
`/gerar cad`, `/cad`,
`/tarefas`, `/notas`, `/status` e `/sair` continuam funcionando, mas são opcionais.

Sem uma chave de API, a Ivy funciona em modo local: reconhece conversas
simples, tarefas, notas e projetos. A conversa livre e o raciocínio mais amplo
dependem da conexão online com um modelo de IA.

### Maneira manual pelo PowerShell

Os comandos abaixo devem ser digitados no PowerShell ou no Terminal do
Windows. Se a linha começar com `>>>`, você está dentro do modo interativo do
Python. Digite `exit()` e pressione Enter antes de executar os comandos.

Para abrir a assistente no PowerShell, dentro desta pasta:

```powershell
python ivy.py --assistant --mode auto
```

Para executar diretamente um único projeto:

```powershell
python ivy.py "Projete uma garra robótica capaz de levantar um objeto de 500 gramas"
```

O modo `auto` usa a API quando `OPENAI_API_KEY` está disponível; caso
contrário, mantém a assistente no modo local.

Para forçar o demonstrador local:

```powershell
python ivy.py --mode demo "Projete uma garra robótica capaz de levantar um objeto de 500 gramas"
```

Se o PowerShell não estiver aberto na pasta do projeto, use primeiro:

```powershell
cd "$env:USERPROFILE\OneDrive\Área de Trabalho\Ivy\Projeto"
```

Para obter JSON ou salvar o resultado:

```powershell
python ivy.py --mode demo --json --save projeto.json "Projete uma garra robótica capaz de levantar um objeto de 500 gramas"
```

## Ativando a IA pela API

Crie um ambiente virtual e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Configure `OPENAI_API_KEY` no ambiente e execute com `--mode api`. A chave não
deve ser escrita em arquivos do projeto ou enviada para um repositório.

O modelo pode ser alterado pela variável `IVY_MODEL`. O padrão inicial é
`gpt-5.6`.

## Princípios do projeto

1. A IA organiza requisitos; ferramentas determinísticas fazem os cálculos.
2. Valores não fornecidos pelo usuário nunca são apresentados como fatos.
3. Toda hipótese permanece visível e precisa de confirmação.
4. Projetos físicos passam por simulação, revisão humana e testes graduais.
5. Aplicações de alto risco não avançam automaticamente.

Leia também [SPEC.md](docs/SPEC.md) para entender o contrato da versão atual.
