# Plano v0.8 — o relatório como produto (proposta, 14/09/2026; aguarda aval do Thalles)

## 0. Problema
O pesquisador roda o framework (terminal, notebook, Colab) e recebe tabelas soltas e um HTML que ninguém abre. Ele precisa
de UM documento que (a) mostre os resultados, (b) explique como cada número foi calculado, (c) diga como interpretá-lo,
(d) declare o rigor aplicado, e (e) permita levar as tabelas para Excel/CSV com um clique. Sem servidor, sem internet.

## 1. Fatos verificados antes de planejar (14/09)
- `report.html` já existe em toda execução e já é autocontido: as figuras vão embutidas em base64 (2,2 MB numa execução real).
- As tabelas de uma execução real somam 76 KB. Embutir todas em base64 acrescenta ~100 KB ao arquivo: irrelevante.
- `openpyxl` (escrita de Excel pelo pandas) NÃO está instalado em nenhum ambiente → Excel tem de ser opcional.
- `IPython` existe nos kernels de notebook → é possível mostrar o relatório inline detectando o ambiente.
- O contrato §4 não define o conteúdo do relatório HTML (só tabelas, manifesto, resumo, figuras).

## 2. Escopo
**Entra:** (1) relatório como saída principal (caminho impresso; inline no notebook); (2) botões CSV por tabela, embutidos;
(3) arquivo Excel com uma aba por tabela, opcional; (4) texto de método por bloco, nas 4 línguas, com os números vindos da
configuração real; (5) seção "Rigor desta execução" a partir do manifesto; (6) contrato §4.6.
**Não entra:** interatividade (filtros, gráficos dinâmicos), servidor, PDF, editor. É framework, não software industrial.

## 3. Pressupostos a verificar (cada um com a sua checagem)
| # | pressuposto | como verificar | se falhar |
|---|---|---|---|
| P1 | `<a download href="data:text/csv;base64,…">` funciona com o HTML aberto do disco (file://), em Firefox e Chrome | teste automático: extrair os links do HTML, decodificar, comparar byte a byte com o CSV em disco; teste MANUAL do Thalles nos dois navegadores | trocar por `Blob` via JavaScript inline (ainda sem servidor) |
| P2 | tamanho dos links não ultrapassa limites de navegador | teste: cada link < 1 MB; total do HTML < 5 MB numa execução de 300 pessoas | gravar CSVs ao lado e linkar por caminho relativo |
| P3 | `pandas.to_excel` exige `openpyxl`; sem ele o relatório continua íntegro | teste com e sem `openpyxl` (simulando ausência): com → `tables.xlsx` com N abas; sem → aviso "instale bioms-zaku[excel]" e links CSV intactos | — |
| P4 | todo número no texto de método vem de `cfg`/`manifest`/tabelas, nunca de texto fixo | teste: mudar B para 500 e CV para 3×7 na configuração → o texto muda junto; mudar preset → o aviso muda | — |
| P5 | mostrar inline só em notebook, sem quebrar o terminal | teste: `run()` com e sem `get_ipython` simulado; CLI continua imprimindo o caminho | — |
| P6 | HTML íntegro com tudo embutido | teste de tags balanceadas (como na página de docs) | — |
| P7 | texto e tabelas concordam | teste: contagens de vereditos citadas no texto = contagens em `audit.csv`; nº de métodos = linhas de `algebra.csv` | — |
| P8 | quatro línguas completas | teste de paridade já existente (chaves e campos) cobre as chaves novas; teste extra: relatório em pt sem as frases inglesas dos blocos novos | — |
| P9 | determinismo | `report.html` carrega data/hora, logo NÃO entra nos hashes; os CSVs embutidos são os mesmos arquivos hasheados no manifesto (teste: bytes iguais) | — |

## 4. Decisões de desenho e justificativa
- **D1. O relatório é a saída principal.** Terminal: última linha = caminho do `report.html` e comando para abrir. Notebook:
  `run()` mostra o relatório inline (iframe) e devolve o mesmo objeto de sempre. *Por quê:* foi o que faltou hoje; tabela
  solta não é leitura para pesquisador.
- **D2. CSV embutido, não linkado.** *Por quê:* um único arquivo que abre offline e pode ser enviado por e-mail; o custo é
  ~100 KB.
- **D3. Excel opcional (`pip install bioms-zaku[excel]`).** *Por quê:* `openpyxl` é dependência pesada e não é do método;
  o núcleo fica leve; quem quer Excel instala o extra. Um único `tables.xlsx`, uma aba por tabela, ao lado do relatório.
- **D4. Texto de método por bloco = três parágrafos: como foi calculado · como ler · rigor aplicado.** Blocos: entrada e
  amostra; redundância e precedência; especificidade (controle condicional); utilidade; geometria alvo↔controle;
  transferência de Σ; sensibilidade (limiares e estimador); triagem. *Por quê:* é o que um revisor pergunta; e os
  números (folds, repetições, B, margens, limiares, sementes) saem da configuração resolvida, então o texto nunca mente.
- **D5. Seção "Rigor desta execução".** preset, sementes, versões (Python, numpy, pandas, scikit-learn, pacote, catálogo),
  hash da entrada, hash de cada saída, tempo, avisos, declaração de independência do alvo. *Por quê:* já está no
  manifesto em JSON; passa a ser legível e citável.
- **D6. Nada é recalculado no relatório.** Ele só lê tabelas, manifesto e configuração. *Por quê:* uma fonte de verdade.
- **D7. Contrato §4.6** descreve seções, botões, extra `[excel]`, e a regra D6.

## 5. Garantias (testes que travam o comportamento)
T1 links CSV = arquivos (P1/P9) · T2 tamanhos (P2) · T3 Excel com/sem openpyxl (P3) · T4 texto segue a configuração (P4) ·
T5 inline só em notebook (P5) · T6 HTML íntegro (P6) · T7 texto = tabelas (P7) · T8 paridade + relatório pt sem inglês (P8)
· T9 suíte inteira verde · T10 CI nos 4 Pythons com o passo de usuário externo abrindo o relatório e checando um link.

## 6. Etapas, em ordem, com parada para revisão
1. Contrato §4.6 (texto) → aval.
2. Catálogo de mensagens: chaves dos textos de método e da seção de rigor, 4 línguas.
3. `html.py`: seções, botões CSV, Excel opcional, rigor. `run.py`/`cli.py`: caminho impresso, inline no notebook.
4. Testes T1–T8; suíte; build; CI.
5. Documentação: README (extra `[excel]`, o que o relatório contém), página de docs, CHANGELOG.
6. **Rodada de testes do Thalles** (seção 7).

## 7. Rodada final de testes (o que o Thalles verifica, com o pacote novo)
- Terminal: `run` na amostra de 300; abrir o `report.html`; clicar em CSV de `audit` e de `geometry`; abrir no LibreOffice;
  conferir que os números batem com o resumo. Se instalou `[excel]`: abrir `tables.xlsx`, contar as abas.
- JupyterLab: `run` mostra o relatório inline; os mesmos botões funcionam a partir do iframe.
- Colab: subir o wheel novo, `run` em `quick`; baixar o `report.html` e abrir localmente; botões funcionam offline.
- Leitura: para dois blocos à escolha, ler "como foi calculado · como ler · rigor" e dizer se um pesquisador de fora
  entenderia. Conferir que os números do texto (B, CV, margens) são os do YAML usado.
- Idioma: repetir o `run` com `--lang en` e conferir que o relatório inteiro muda.
Critério de aceite: tudo acima sem defeito; qualquer defeito volta para correção com teste antes de nova rodada.
