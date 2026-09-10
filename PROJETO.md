# BioMS Zaku — projeto do framework (v0, 10/09/2026)

Licença MIT. Nome público **BioMS Zaku**; pacote `bioms-zaku` (livre no PyPI, verificado 10/09/2026; `zaku` sozinho já existe); módulo `bioms_zaku`.

**Atribuição do nome.** *zaku* é verbo da língua Juruna (Yudjá), família Tupi, Xingu, Mato Grosso: "ver / cuidar / esperar" (item 290 da lista de 302 verbos em Lima, Suzi. *A estrutura argumental dos verbos na língua Juruna (Yudjá): da formação dos verbos para a análise das estruturas sintáticas*. Dissertação de mestrado, USP, 2008). Escolhido porque o método olha o índice antes de aceitá-lo, cuida da sua validade e espera o resultado fora da amostra; e porque os Yudjá são nativos da região de origem do autor. A nota de atribuição vai no README, no CITATION.cff e no artigo. Recomendado: contato com a comunidade ou associação Yudjá antes do lançamento. Repositório: GitHub → release → DOI no Zenodo → PyPI → imagem de container.

## 1. Objetivo e escopo

**Objetivo.** Implementar, como pacote Python reprodutível, o método em duas partes do artigo MBEC:
(a) decomposição algébrica de índices e equações em vetores de expoentes, com previsão analítica da
correlação entre índices pela matriz Σ dos logaritmos; (b) auditoria preditiva fora da amostra com
controle negativo, utilidade sobre covariáveis básicas e ganho por combinação de eixos.

**Dentro do escopo (v1.0, a versão citada no artigo):** entrada tabular; catálogo de índices em JSON;
os quatro blocos que já existem (B controle negativo, C redundância/precedência, D previsão por Σ e
transferência, E utilidade) + F triagem; regressão (R²) e classificação (AUROC); manifesto de
reprodutibilidade; testes; documentação mínima; container.

**Fora do escopo (v1.0):** interface gráfica; ajuste automático de hiperparâmetros; seleção de modelo
pelo resultado; qualquer coisa que o artigo não use. (Justificativa: o MBEC não é periódico de
software; o pacote existe para tornar o método reprodutível e aplicável, não para competir com
ferramentas.)

## 2. Princípios (regras que o código impõe, não só recomenda)

1. **Tudo fora da amostra.** Nenhum número reportado vem de dado visto no ajuste.
2. **Pareado.** Alvo e controle, configuração A e B, modelo 1 e 2: sempre nos mesmos sorteios.
3. **Regras declaradas antes dos dados.** Limiar de redundância, vereditos, margem de utilidade,
   modelo e semente ficam no manifesto; o pacote não permite escolher depois de ver o resultado
   (não há função "melhor modelo").
4. **Sem vazamento.** Imputação e padronização dentro do pipeline, ajustadas só no treino.
5. **Reprodutível byte a byte.** Sementes fixas, versões gravadas, hash da entrada.
6. **Avaliação segura de expressões.** Sem `eval`; parser restrito (aritmética, potências,
   funções matemáticas, nomes de variáveis mapeadas).

## 3. Arquitetura (módulos)

| módulo | responsabilidade | origem no código atual |
|---|---|---|
| `io` | ler CSV/DataFrame; detectar separador e decimal; mapear colunas; validar (positividade, faltantes, n mínimo) | novo |
| `catalog` | carregar/validar catálogo JSON de índices; parser seguro de expressões; calcular índices | `metodos_bia.json`, `evaluate`, `build_methods` |
| `algebra` | vetor de expoentes (definição ou ajuste log-linear + R²); Σ; ρ previsto; conversão Spearman; IC de Fisher; transferência de Σ entre estratos | `loglin`, `rho_log`, `rho_sp`, `fisher_ci`, bloco D |
| `audit` | pipeline de modelo; CV repetida; bootstrap OOB pareado; controle negativo; utilidade; combinação de eixos; vereditos | `_pipe`, `cv_point`, `boot_oob`, blocos B e E |
| `screen` | matriz de triagem (redundante × específico × útil) com precedência por ano | bloco C + F |
| `report` | tabelas CSV por bloco + manifesto JSON + resumo em Markdown | saídas atuais |
| `plots` | as 5 figuras-assinatura + 2 de apoio, a partir das tabelas de saída | novo (figuras do KDMiLe como ponto de partida) |
| `cli` | `bioms-zaku run config.yaml` para quem não programa (o caso do container) | novo |

Estimadores: qualquer objeto com `fit`/`predict` (regressão) ou `fit`/`predict_proba` (classificação)
no padrão scikit-learn. Padrões: Ridge(α=1) e LogisticRegression. Modo de sensibilidade: um segundo
estimador nos mesmos sorteios, reportado, nunca usado para selecionar.

## 4. Contratos de dados

**Entrada.** Uma tabela, uma linha por indivíduo. Colunas mapeadas pelo usuário:
variáveis medidas (≥2, positivas), alvo(s), controle(s) negativo(s), covariáveis básicas (p. ex.
peso e altura), estrato (opcional), identificador (opcional). Aceita CSV (UTF-8; `,`/`;`;
decimal `.`/`,`; detecção automática com parâmetro para forçar) ou `pandas.DataFrame`.

**Catálogo.** JSON com lista de índices: `id`, `autor`, `ano`, `doi`, `alvo`, `forma`
(`monomio` | `afim` | `outro`), `expr` (na sintaxe do parser), `vetor` (opcional, se monômio),
`sex_coding`, `verificacao`. É o `metodos_bia.json` atual com o parser novo.

**Configuração.** YAML com: caminho dos dados, mapeamento, catálogo, alvos, controles, covariáveis,
estratos, estimador, sementes, B (bootstrap), n_rep (CV), limiares. O manifesto é a configuração
resolvida + versões + hash.

**Saída.** `algebra.csv`, `redundancy.csv`, `sigma_transfer.csv`, `audit.csv`, `utility.csv`,
`screening.csv`, `manifest.json`, `summary.md`. Mesmos nomes sempre.

**Figuras (módulo `plots`, v1.0 — as figuras do artigo saem do pacote):** (1) bússola de índices (setas no espaço de expoentes, painéis R–Xc e H–W); (2) previsto × observado com faixa de Fisher, por estrato; (3) árvore de precedência (ano × índice, aresta ao antecessor redundante); (4) quadrante de especificidade (R² controle × R² alvo, nuvem bootstrap, diagonal); (5) mapa de triagem (redundância × especificidade, tamanho = utilidade, cor = veredito) — o gráfico-assinatura. Apoio: mapa de calor da transferência de Σ; ganho por combinação × ortogonalidade prevista. Uma paleta, uma tipografia, mesma família visual.

## 5. Regras de decisão (fixadas; valores da análise NHANES de 09/09/2026)

- Redundância: |ρ_s| ≥ 0,95 com antecessor publicado antes (ano; empate → o mais antigo DOI).
- Especificidade: d = R²(alvo) − R²(controle) por reamostra; ESPECÍFICO se média > 0, IC95% inferior > 0
  e P(d>0) ≥ 0,95; MEDE O CONTROLE se média < 0, IC superior < 0 e P ≤ 0,05; senão INCONCLUSIVO.
  Classificação: AUROC no lugar de R².
- Utilidade: ΔR² (ou ΔAUROC) sobre covariáveis básicas; ÚTIL se IC inferior > margem (0,03).
- Bootstrap: B = 2000 por padrão, OOB mínimo 20; CV 5×50.
- Σ: covariância amostral dos logs, por estrato quando informado; transferência = Σ de um estrato
  aplicada aos vetores e comparada ao observado em outro (proporção no IC de Fisher + erro mediano).

## 6. Qualidade (portões; nenhuma etapa avança sem passar)

1. **Testes de unidade com resposta à mão**: a tabela de 4 pessoas das lições (Var, Cov, Σ, aᵀΣa,
   aᵀΣb, ρ = −0,998) e a regressão de 3+2 pontos (R² = 0,72). Tolerância 1e-9.
2. **Testes de equivalência**: o pacote reproduz, bit a bit ou a 1e-9, os CSVs do NHANES de 09/09/2026
   e do piloto v2 do DRC, com as mesmas sementes.
3. **Testes de contrato**: CSV com `;` e vírgula decimal; coluna negativa → erro claro; faltante no
   alvo → linha removida com aviso; expressão maliciosa → rejeitada pelo parser.
4. **Determinismo**: duas execuções → saídas idênticas e mesmo hash no manifesto.
5. **CI**: os testes rodam no GitHub a cada commit em Linux, Python 3.10–3.12.
6. **Revisão humana** (Thalles) de cada módulo antes de seguir; **inspeção visual de cada uma das 7 figuras** pelo Thalles antes do fechamento da v1.0.

## 7. Publicação e citação

- GitHub público, MIT, README (instalação, exemplo de 5 linhas, saídas), CHANGELOG, CITATION.cff.
- Release `v1.0.0` no dia da submissão → Zenodo gera DOI → DOI vai em *Code availability* do artigo.
- PyPI: `pip install bioms-zaku` (mesma versão da release).
- Container: imagem com o pacote + CLI, para rodar `bioms-zaku run config.yaml` sem instalar Python
  (uso previsto: parceiros que não podem exportar dados, p. ex. UFRO).
- Dados de exemplo no repositório: apenas públicos e pequenos (subamostra sintética ou NHANES
  reduzido), nunca DRC/CrossFit sem checar licença.

## 8. Etapas, entregas e ponto de revisão

| etapa | entrega | revisão |
|---|---|---|
| 0 | verificação do ambiente e contas (git, gh, PyPI, Zenodo, Docker); decisões de nome/licença | ✔ 10/09: git/gh/Podman ok; PyPI+TestPyPI com token (rotacionar); Zenodo pendente. Ambiente conda `zaku` criado (Python 3.11.13; numpy 2.3.5, pandas 2.3.3, scipy 1.16.2, scikit-learn 1.4.2 = versões da referência; matplotlib 3.11.1, pyyaml, pytest 9, build, twine, hatchling) |
| 1 | contratos: formato de entrada, catálogo, configuração, saídas (documento + exemplos) | ✔ 10/09: CONTRATOS.md v0.3 aprovado ("faça") |
| 2 | `io` + `catalog` + parser seguro, com testes de contrato | ✔ 10/09: `src/bioms_zaku/{expr,catalog,io}.py`; `tools/migrate_catalog.py` (39→31, determinístico); `data/catalog_v1.json` validado (vetores conferidos numericamente, 2 check_examples); 42 testes passando; `python -m build` + `twine check` OK. Correções feitas pelos testes: detecção de separador exigia conversão numérica; `inputs` faltava o grupo de ramo. Lima 2008 ganhou DOI 10.37527/2008.58.4.010 (Crossref, resolve). Aguardando revisão do Thalles |
| 3 | `algebra` com testes das lições e equivalência com bloco D | ✔ 10/09: `algebra.py` (Σ ddof=1, vetor do catálogo ou ajuste log-linear, Pearson dos logs exato, Spearman observado, pares, redundância com precedência, transferência de Σ). Testes: 10 lições do caderno; exatidão em dados aleatórios (1e-12); equivalência NHANES: expoentes e R² a 1e-9 (26 métodos × 2 sexos), máximos de redundância a 1e-6, bloco D (34 linhas: pares, erro mediano/máximo a 1e-6, dentro-IC ±1 par). Causa dos 3e-7: 1 ulp em H_m/II no CSV de referência. Commit 2. Aguardando revisão |
| 4 | `audit` + `screen` com equivalência com blocos B/C/E do NHANES | revisão |
| 5 | `report` + manifesto + CLI + determinismo | revisão |
| 6 | README, CITATION, CHANGELOG, CI, licença | revisão |
| 7 | release v1.0.0 → Zenodo → PyPI → container | Thalles executa as publicações |

Regra de trabalho: uma etapa por vez; reportar; parar. Nada de encadear.

## 8b. Curadoria do catálogo (depois da infra)
O catálogo entra na v1.0 como está, com o campo `verificacao` (nível de confiança) propagado até as saídas. Pendências conhecidas (10/09/2026): 9 equações só de resumo PubMed; Heitmann 1990 sem PDF original (sinais inferidos); Lima 2008 'conferir no PDF'; Segal generalizada via tabela de Gray; 17 sem `sex_coding`; 12 sem n; índices sem `vetor` gravado no JSON; Segal específica selecionada por %gordura do DXA (vazamento — trocar por IMC ou estimativa só-BIA); Schifferli 2020 = 0,854×2011 (marcar como identidade por escala); faixa de validade (IMC, idade) como campo obrigatório. Contribuições futuras: uma a uma, por pull request com modelo (DOI resolvido + fórmula com origem + teste com valor publicado + revisão humana). Catálogo com versão própria.

## 9. Riscos e como estão tratados

- **Resultado diferente do artigo após refatorar** → portão 2 (equivalência) bloqueia.
- **Parser inseguro** → parser por árvore sintática com lista branca; teste de expressão maliciosa.
- **Dependência de versão do scikit-learn muda números** → versões fixadas no manifesto e no
  container; testes de equivalência com tolerância declarada.
- **Formato brasileiro de CSV** → detecção + parâmetro explícito + teste.
- **Escopo crescer** → seção 1 (fora do escopo) é contrato; v1.1 só depois da submissão.
