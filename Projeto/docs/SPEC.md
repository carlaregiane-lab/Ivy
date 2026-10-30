# Especificação — Ivy v0.9.0

## Conversa orientada por intenção

A linguagem natural é a interface principal. Os atalhos iniciados por `/`
continuam aceitos, mas nenhuma ação cotidiana deve depender de o usuário
memorizar um comando.

A Ivy deve reconhecer, no mínimo:

1. Criação de projeto: “preciso desenvolver...”, “crie um projeto...” ou
   “projete...”.
2. Consulta e troca: “como está o projeto?”, “mostre meus projetos” e “use o
   projeto 2”.
3. Respostas: “a resposta 1 é ...; a resposta 2 é ...”.
4. Cálculo e recuperação: “faça os cálculos” e “mostre o último cálculo”.
5. Comparação: “compare os mecanismos” e “mostre os conceitos”.
6. Histórico e decisões: “mostre o histórico”, “o que mudou no projeto?”,
   “registre a decisão de...” e “mostre as decisões”.
7. Verificação independente: “verifique o projeto”, “confira os cálculos” e
   “mostre a última verificação”.
8. CAD paramétrico: “crie o modelo CAD”, “gere o modelo 3D” e “mostre o último
   CAD”.
9. Notas e tarefas: “anote que...”, “crie uma tarefa...” e “mostre minhas
   tarefas”.

Perguntar pelo projeto atual não pode criar um projeto duplicado. Pedidos para
mostrar cálculos não podem gerar uma nova revisão; apenas pedidos para calcular
ou recalcular podem fazê-lo.

## Passo 4: Comparação de conceitos

A comparação deve consumir uma memória de cálculo atual e produzir estimativas
repetíveis para três arquiteturas da garra:

1. Fuso único com roscas opostas.
2. Pinhão central com duas cremalheiras.
3. Correia sincronizadora com carros opostos.

Cada conceito deve registrar princípio, hipóteses geométricas, fórmula e
substituição de torque, rotação para fechar, velocidade, potência mecânica,
pontuação, vantagens e limitações. Todos esses resultados devem ser classificados
como estimados por hipótese.

### Benchmark de conceitos

Com abertura útil de 40 a 90 mm, força normal de referência de aproximadamente
47,37 N por dedo e hipótese de fechamento em 1 s, a comparação deve estimar:

- fuso de 8 mm/volta e eficiência 0,35: cerca de 0,345 N·m, 187,5 rpm e 6,77 W;
- pinhão de raio 10 mm e eficiência 0,85: cerca de 1,115 N·m, 23,87 rpm e 2,79 W;
- polia de raio 12 mm e eficiência 0,90: cerca de 1,263 N·m, 19,89 rpm e 2,63 W.

O fuso pode ser recomendado para detalhamento preliminar, mas a Ivy não pode
selecionar motor, componente comercial ou declarar o projeto seguro. A escolha
deve continuar bloqueada até validar geometria, eficiência, folga, desgaste,
temperatura, PETG, curva torque-velocidade, corrente, custo e análise de risco.

### Persistência da comparação

Um pedido para comparar cria uma revisão ligada ao projeto. Um pedido para
mostrar os conceitos recupera a revisão existente. Alterações em respostas ou
em cálculos devem marcar a comparação como desatualizada.

## Passo 5: Memória versionada

Cada projeto deve possuir uma revisão geral crescente e uma linha do tempo
persistente. Os eventos obrigatórios são criação do projeto, alteração de
respostas, cálculo guardado, comparação guardada, verificação guardada, modelo
CAD guardado e decisão registrada.

### Contrato dos eventos

Cada evento deve registrar identificador, revisão do projeto, data e hora, tipo,
resumo e detalhes estruturados. Revisões não podem diminuir nem ser reutilizadas.
Repetir uma resposta sem alterar seu conteúdo não deve criar uma mudança falsa.

### Preservação de artefatos

Uma nova memória de cálculo, comparação, verificação ou geometria CAD não pode
apagar a anterior. Cada versão deve guardar seu número, a revisão do projeto
correspondente, data e hora e o relatório completo. O projeto mantém também um
ponteiro para a versão atual.

### Projetos anteriores à versão 0.7

O carregamento deve aceitar projetos sem os campos novos. Cálculos e comparações
já existentes são preservados como fotografias legadas. Nenhum evento anterior
pode ser inventado; a linha do tempo detalhada começa quando o histórico é
ativado no projeto existente.

### Decisões

Cada decisão deve receber identificador `DEC-001` e seguintes, revisão do
projeto, data e hora, texto, motivo opcional e estado ativo. A Ivy deve aceitar
linguagem natural e recuperar as decisões depois de reiniciada.

## Passo 6: Verificador independente

O verificador deve ser um módulo determinístico separado da calculadora e da
comparação de conceitos. Ele não pode simplesmente confiar nos valores guardados:
deve reproduzir os resultados por uma segunda rotina e comparar o esperado com o
encontrado usando tolerância numérica explícita.

### Verificações obrigatórias

1. Validar os contratos estruturados do briefing, da memória de cálculo e da
   comparação de conceitos.
2. Recalcular valores conhecidos e conferir suas unidades e classificações.
3. Confirmar que fórmulas, substituições e fontes estão presentes.
4. Detectar identificadores duplicados, resultados sem entradas suficientes e
   artefatos marcados como desatualizados.
5. Conferir que a revisão atual possui uma fotografia idêntica no histórico.
6. Recalcular torque, rotação, velocidade, potência, pontuação, ranking e
   recomendação dos três conceitos do benchmark.
7. Confirmar que bloqueios de torque, PETG, contato com pessoas e custo continuam
   explícitos na memória de cálculo.
8. Impedir declarações de motor selecionado, segurança validada ou fabricação
   aprovada.

### Estados e bloqueios

O relatório pode ficar `sem_artefatos`, `consistente_com_alertas` ou
`inconsistente`. Qualquer erro deve bloquear o uso técnico e a recomendação até
que o artefato seja corrigido e verificado novamente. Mesmo sem erros, a saída
deve declarar que coerência interna não equivale a segurança física, conformidade
normativa ou autorização para fabricação.

### Persistência e execução automática

Cada verificação recebe revisão própria e é preservada integralmente. Cálculos e
comparações novos executam uma verificação automática. Mudanças nas respostas ou
nos artefatos de origem tornam a verificação anterior desatualizada. Pedidos para
mostrar a última verificação não criam uma revisão nova.

## Passo 7: CAD paramétrico preliminar

O gerador CAD deve consumir uma memória de cálculo atual e uma comparação de
conceitos atual. A versão 0.9 modela somente `CONCEPT-SCREW-001`, porque esse é o
conceito recomendado no benchmark. A geração representa detalhamento virtual;
ela não seleciona fuso, motor, guia, mancal, fixador, sensor ou fornecedor.

### Contrato dos parâmetros

Cada dimensão deve registrar identificador, símbolo, descrição, valor, unidade,
classificação e fonte. A classificação pode ser `requisito`, `derivado` ou
`hipotese`. Para a faixa de 40 a 90 mm, o contrato deve produzir vinte
parâmetros, incluindo:

1. abertura mínima de 40 mm e máxima de 90 mm, vindas de `REQ-GEOM-001`;
2. curso simétrico de 25 mm por dedo, derivado da faixa;
3. abertura de visualização de 90 mm;
4. base preliminar de 150 × 60 × 10 mm;
5. carros de 24 × 44 × 12 mm;
6. dedos de 12 × 20 × 50 mm;
7. parede mínima hipotética de 6 mm;
8. fuso geométrico de 8 mm de diâmetro, 8 mm/volta e 140 mm de comprimento;
9. duas guias geométricas de 8 mm separadas por 32 mm;
10. folga visual hipotética de 0,5 mm.

Todas as dimensões que não venham diretamente do briefing devem permanecer
visíveis como derivações ou hipóteses. A assinatura SHA-256 dos parâmetros deve
incorporar projeto, conceito, revisões de origem e conteúdo integral dos vinte
parâmetros.

### Arquivos obrigatórios

Cada revisão aprovada pelas verificações geométricas deve produzir, em uma pasta
exclusiva:

1. `.scad`: modelo paramétrico autônomo, sem dependências externas;
2. `.stl`: visualização tridimensional ASCII na abertura máxima;
3. `.svg`: prancha vetorial das aberturas mínima e máxima;
4. `.json`: manifesto com parâmetros, verificações, assinatura e bloqueios.

Nome, caminho, tamanho e SHA-256 de cada arquivo devem ser registrados no
relatório. Uma nova revisão usa outra pasta e preserva os arquivos anteriores.

### Verificações geométricas

O gerador deve conferir faixa crescente, curso por dedo, envelope da base,
comprimento do fuso, acomodação dos dedos nos carros, profundidades, parede
conceitual, espaço para fuso e espaço transversal das guias. Também deve manter
dois alertas formais: a geometria não comprova resistência ou segurança e o STL
não contém os detalhes necessários para fabricação.

O verificador independente deve repetir a derivação dos vinte parâmetros,
conferir a fotografia histórica, as revisões de origem, a assinatura, o conjunto
de quatro arquivos e seus hashes, além de validar o conteúdo mínimo de OpenSCAD,
STL, SVG e manifesto. Qualquer alteração posterior deve produzir estado
`inconsistente` e bloquear o uso técnico.

### Limites obrigatórios

O relatório CAD deve manter `component_selected`, `safety_validated` e
`fabrication_approved` como falsos. Análise estrutural, interferências,
tolerâncias, simulação do mecanismo, análise de risco e revisão profissional
continuam bloqueadas. O modelo não é um arquivo pronto para impressão 3D.

## Passo 3: Calculadora de Engenharia

A calculadora deve transformar apenas dados rastreáveis do projeto em
resultados determinísticos. Um modelo de linguagem pode ajudar a interpretar
texto, mas não pode substituir a execução das fórmulas.

### Contrato de cada resultado

Cada cálculo deve registrar:

1. Identificador único.
2. Nome da grandeza.
3. Fórmula utilizada.
4. Substituição numérica.
5. Valor e unidade.
6. Classificação como calculado ou estimado por hipótese.
7. Requisitos, respostas ou hipóteses usados como fontes.

### Benchmark da garra

Com massa de 1,5 kg, elevação de 0,3 m em 2 s, 12 ciclos/min, fonte de
12 V com 10 A contínuos e 15 A de pico, jornada de 8 h/dia, coeficiente de
atrito provisório 0,4 e fator de segurança provisório 2,5, o sistema deve
calcular aproximadamente:

- peso estático: 14,71 N;
- velocidade média: 0,15 m/s;
- aceleração estimada no perfil triangular: 0,30 m/s²;
- força normal estimada: 47,37 N por dedo e 94,75 N no total;
- potência mecânica ideal média: 2,21 W;
- potência mecânica ideal de pico: 4,55 W;
- capacidade nominal da fonte: 120 W contínuos e 180 W de pico;
- período: 5 s/ciclo e 5.760 ciclos/dia;
- manutenção a cada 100.000 ciclos: aproximadamente 17,36 dias de operação;
- vida de 1.000.000 de ciclos: aproximadamente 173,61 dias de operação.

### Bloqueios obrigatórios

A calculadora não pode selecionar motor nem declarar segurança. Devem
permanecer bloqueados, enquanto faltarem dados, o torque e a rotação do
atuador, a verificação estrutural do PETG, o limite de força perto de pessoas
e o custo total.

### Persistência

Um pedido para calcular cria uma revisão da memória de cálculo. Um pedido para
mostrar o último cálculo recupera a revisão existente. Qualquer alteração
posterior nas respostas deve marcar o resultado como desatualizado até que um
novo cálculo seja solicitado.

## Continuidade de projetos

O Passo 2 transforma cada briefing em um projeto persistente. A coleta de dados
deve continuar entre sessões sem depender apenas do histórico temporário da
conversa.

### Capacidades obrigatórias

1. Atribuir a cada novo projeto um identificador sequencial, como `PRJ-001`.
2. Manter um projeto ativo e recuperá-lo depois que a Ivy for reiniciada.
3. Aceitar uma ou várias respostas no formato numerado.
4. Relacionar cada resposta à pergunta original, sem renumerar as pendentes.
5. Mostrar quantas perguntas foram respondidas e quais continuam pendentes.
6. Listar projetos e permitir a troca do projeto ativo.
7. Preservar a separação entre resposta informada, cálculo e evidência de
   segurança.

### Intenções reconhecidas

- “crie um projeto...” cria e ativa um projeto.
- “como está o projeto?” mostra o estado do projeto ativo.
- “mostre meus projetos” lista os projetos persistidos.
- “use o projeto número” seleciona outro projeto.
- “a resposta 1 é ...; a resposta 2 é ...” registra respostas por número.

Os atalhos `/projeto`, `/projeto atual`, `/projetos`, `/usar projeto` e
`/responder` permanecem como alternativas opcionais.

## Analisador contextual de engenharia

O analisador deve extrair todos os limites explicitamente informados, incluindo
faixas dimensionais, massa, deslocamento, tempo, frequência, tensão, material,
processo de fabricação, orçamento e condições de contato com pessoas.

### Benchmark avançado obrigatório

Para a pergunta da garra elétrica de dois dedos com caixas de 40 a 90 mm,
carga máxima de 1,5 kg, elevação de 30 cm em até 2 s, 12 ciclos/min, 12 V,
estrutura impressa em PETG, orçamento de R$ 600 e operação próxima a pessoas,
o sistema deve:

1. Registrar as nove restrições sem omissões.
2. Não perguntar novamente por abertura, atuação, frequência, alimentação,
   material, fabricação, orçamento ou proximidade de pessoas.
3. Classificar o risco como médio e emitir alerta de esmagamento e parada segura.
4. Calcular deterministicamente o peso estático aproximado, a velocidade média
   mínima e a frequência equivalente.
5. Listar os cálculos ainda necessários para força de aperto, torque, velocidade,
   potência, corrente, resistência do PETG, regime térmico, segurança e custo.
6. Não escolher motor nem declarar o projeto seguro.

## Assistente de trabalho

Ao ser iniciada sem um pedido na linha de comando, a Ivy deve abrir uma
conversa contínua e mostrar o marcador `Você >`. Uma apresentação pessoal não
pode ser tratada como projeto de engenharia.

### Capacidades locais obrigatórias

- Cumprimentar e responder a frases sociais simples.
- Reconhecer frases como “eu sou seu criador” sem gerar um briefing.
- Guardar localmente o nome informado, notas e tarefas.
- Listar e concluir tarefas por número.
- Chamar o interpretador quando a fala expressar intenção de criar ou
  desenvolver um projeto.
- Distinguir consultas sobre o projeto atual de pedidos para criar um novo.
- Mostrar com clareza se a Ivy está local ou online.
- Encerrar somente quando o usuário pedir.

### Conversa online

No modo `auto`, a Ivy usa um modelo online apenas quando `OPENAI_API_KEY` está
configurada. Sem a chave, continua no modo local. A assistente deve ser honesta
sobre ferramentas que ainda não possui e não pode afirmar que executou ações,
pesquisas, cálculos ou testes inexistentes.

### Memória local

A memória fica em `data/ivy_memory.json` dentro do projeto. Ela guarda apenas
identidade informada, notas, tarefas, projetos, briefings, respostas, memórias
de cálculo, comparações, verificações, modelos CAD, histórico e decisões. Um pedido para limpar o histórico
temporário da conversa preserva todos esses dados persistentes.

## Interpretador de Requisitos v0.1

## Missão

Converter uma descrição informal de um projeto de engenharia em um documento
estruturado que possa ser validado antes de cálculos, CAD, simulação ou compra
de componentes.

## Entrada

Texto livre em português descrevendo um objetivo de engenharia.

## Saída obrigatória

- Nome e objetivo do projeto.
- Áreas de engenharia envolvidas.
- Requisitos explícitos e sua origem.
- Valores e unidades exatamente como informados.
- Valores convertidos para SI por código determinístico, quando aplicável.
- Hipóteses claramente identificadas.
- Informações ausentes.
- Perguntas prioritárias para o usuário.
- Nível de risco preliminar e alertas.
- Estado de prontidão do projeto.

## Regras de confiança

- Não realizar dimensionamento nesta etapa.
- Não inventar propriedades de materiais, dimensões ou fatores de segurança.
- Não confundir uma sugestão com um requisito confirmado.
- Não declarar que um projeto é seguro ou funcional sem evidência.
- Bloquear avanço automático quando houver risco crítico.

## Critérios de aceitação do cenário inicial

Para o pedido “Projete uma garra robótica capaz de levantar um objeto de 500
gramas”, o sistema deve:

1. Classificar o projeto como mecânico e mecatrônico.
2. Registrar a capacidade de levantar 500 g como requisito explícito.
3. Converter 500 g para 0,5 kg sem usar o modelo de linguagem.
4. Perguntar ao menos sobre geometria do objeto, curso da garra, alimentação,
   frequência de uso e processo de fabricação.
5. Marcar o projeto como necessitando esclarecimentos.
6. Não escolher motor, material ou mecanismo nesta etapa.

## Próximo módulo

O próximo módulo será a simulação estrutural e cinemática preliminar do modelo
CAD. Ele deverá consumir uma geometria atual e verificada, calcular movimentos e
casos de carga sem inventar propriedades do PETG e manter fabricação e segurança
bloqueadas até revisão profissional e ensaios.
