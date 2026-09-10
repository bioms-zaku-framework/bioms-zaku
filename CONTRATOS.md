# BioMS Zaku — Etapa 1: contratos (v0.3, 10/09/2026)

Princípio da v1.0: **a versão mais simples possível, sem erros**. Cobre o método; não cobre todos os
contextos. O que fica de fora está listado na seção 0 e é decisão de escopo, não esquecimento.
Cinco contratos: entrada, catálogo, configuração, saídas, reprodutibilidade. Cada um termina em **Justificativa**.

---

## 0. Escopo da v1.0 (decisões de 10/09/2026)
- **O desfecho é do pesquisador.** O framework não define alvo, controle nem critério de referência;
  exige apenas que existam colunas rotuladas. Vale para massa magra, gordura, sprint, sentar-e-levantar,
  qualquer rótulo contínuo ou categórico.
- **Reatância obrigatória.** Aparelhos que não entregam Xc não entram.
- **Frequência declarada, mínima.** O usuário declara a frequência de cada par R/Xc; pode mapear
  mais de uma frequência se tiver (cada uma vira variável própria: `R50`, `Xc50`, `R5`…). Sem
  comparação com o catálogo, sem flags de aparelho.
- **Fora:** metadados do critério de referência (marca do DXA etc.); índices pré-calculados pelo
  aparelho; variáveis segmentares; peso amostral e desenho de pesquisa (decompomos sinal dentro de um
  grupo, para aquele grupo; não estimamos população); Excel de entrada.
- **Duas regras transversais:** toda execução imprime progresso e estimativa de término; nenhuma
  saída contém dado de linha individual, só agregados.

---

## 1. Contrato de ENTRADA

### 1.1 Forma
Uma tabela, uma linha por medição. Com `id` repetido, bootstrap e validação cruzada agrupam por `id`.
CSV/TSV (`encoding` utf-8 padrão; `latin-1`/`cp1252` por parâmetro; falha de decodificação → erro) ou `pandas.DataFrame`.

### 1.2 Separador e decimal
Ordem fixa de tentativa: `(",", ".")`, `(";", ",")`, `(";", ".")`, `("\t", ".")`, `("\t", ",")`.
Par válido = mesmo nº de colunas em todas as linhas **e** todas as colunas mapeadas numéricas convertem.
Exatamente um válido → usa e grava no manifesto; zero ou mais de um → erro pedindo `sep`/`decimal`.
Nomes duplicados → erro.

### 1.3 Mapeamento
| papel | obrig. | exigência |
|---|---|---|
| `variables` | sim, ≥ 2 | numéricas, estritamente positivas (logaritmo). Para BIA: `R<f>`, `Xc<f>`, `H`, `W`; `<f>` = kHz declarado; `R`/`Xc` sem sufixo = 50 kHz |
| `units` | sim para `H`, `W` | `{H: cm|m, W: kg|g}`; só estas conversões |
| `targets` | sim | contínuo (regressão) ou categórico com 2..k classes (classificação); tipo detectado e gravado |
| `controls` | sim | mesmo tipo do alvo pareado |
| `pairing` | não | alvo → controle; padrão: cada alvo × primeiro controle |
| `covariates` | não | numéricas; base da utilidade (se ausente, utilidade não roda) |
| `strata` | não | categórica; Σ, redundância e auditoria por estrato |
| `groups` | não | colunas usadas por `group_coding` do catálogo (ex.: sexo) |
| `id` | não | identificador |

Derivadas automáticas quando existem as canônicas: `H_m`, `PhA = atan(Xc/R)·180/π`, `II = H_cm²/R`, `Z = sqrt(R²+Xc²)`.

Exemplo:
```yaml
columns:
  variables: {R: resistencia_ohm, Xc: reatancia_ohm, H: estatura_cm, W: massa_kg}
  frequency_khz: {R: 50, Xc: 50}
  units: {H: cm, W: kg}
  targets:  {LMI_DXA: lmi_dxa}
  controls: {FMI_DXA: fmi_dxa}
  covariates: [massa_kg, estatura_cm]
  strata: sexo
  groups: {sexo: sexo}
  id: seqn
```

### 1.4 Validação (falha cedo; mensagem nomeia coluna e linhas)
| situação | ação |
|---|---|
| coluna mapeada ausente | erro |
| variável ≤ 0, não numérica ou infinita | erro com linhas; `drop_nonpositive=true` remove, avisa, conta no manifesto |
| faltante em `variables` ou índice não calculável | linha fora da parte algébrica **e** da auditoria daquele método (caso completo por método; `n` reportado). Imputação só se `impute=true`, explícita e gravada no manifesto |
| faltante em `targets`/`controls` | linha fora daquele alvo; contagem no manifesto |
| n por estrato < `min_n` (30) | estrato ignorado, aviso |
| classe com < `min_per_class` (20) casos no estrato | auditoria daquele alvo não roda no estrato, aviso |
| `id` repetido | modo cluster, aviso informativo |

### 1.5 Exemplo mínimo (sintético; `;` e `,`)
```
seqn;sexo;estatura_cm;massa_kg;resistencia_ohm;reatancia_ohm;lmi_dxa;fmi_dxa
1;1;178,3;92,5;467,7;54,9;19,44;9,19
2;0;162,0;63,4;513,0;58,1;15,10;9,02
3;1;171,2;70,1;520,4;61,0;17,02;5,33
4;0;158,7;55,0;601,2;66,3;14,05;6,90
5;1;182,0;105,3;409,8;48,2;20,10;11,80
6;0;165,4;71,9;540,0;60,2;15,60;10,10
7;1;175,0;64,0;560,1;68,9;16,80;4,10
8;0;160,2;80,5;470,3;51,0;16,00;13,50
9;1;169,8;78,4;488,0;57,7;18,20;7,70
10;0;170,5;58,3;575,6;70,4;14,90;5,20
```

**Justificativa.** Mapeamento explícito torna o framework genérico e elimina coluna trocada.
Positividade é exigência do logaritmo. Frequência como parte do nome da variável é o mínimo que
impede somar R a 5 kHz com R a 50 kHz. Detecção de separador com ordem fixa e "exatamente um
válido" falha em vez de ler errado. CV e bootstrap agrupados por `id` preservam independência
treino/teste.

---

## 2. Contrato de CATÁLOGO

### 2.1 Entrada (uma por método; variantes por grupo em `expr_by_group`)
| campo | obrig. | conteúdo |
|---|---|---|
| `id`, `label`, `authors`, `year`, `doi` | sim | DOI resolvível (testado na carga, cache; sem rede → aviso) |
| `kind` | sim | `index` \| `equation` |
| `target` | sim | o que o método declara medir (descritivo) |
| `form` | sim | `monomial` \| `affine` \| `other` (listado, não avaliado) |
| `vector` | se monomial | expoentes; **validado numericamente contra `expr`** (2.3) |
| `expr` / `expr_by_group` | sim | gramática 2.4; ramo só por colunas de `groups`, nunca por alvo/controle/covariável |
| `group_coding` | se usa grupo | ex.: `{sexo: {male: 1, female: 0}}` |
| `frequency_khz` | sim | frequência para a qual a fórmula foi derivada (informativo) |
| `validity` | sim | `{age, bmi, sex, population}`, `null` onde não informado; fora da faixa → flag, não bloqueio |
| `provenance` | sim | `{formula_source: pdf_table|pdf_text|pmc_text|abstract|review_table, source_detail, verified_by, verified_on, confidence}`; mapa padrão pdf/pmc → high, abstract → medium, review → low |
| `check_example` | obrig. para contribuições | `{inputs, expected, tol}` com valor publicado; testado na carga |
| `identity_of` | não | transformação exata de outro método → sai como `identity`, excluído das estatísticas de previsão |
| `n`, `r2`, `see`, `device`, `reference_method`, `notes` | não | `null` quando não informado; nunca inventado |

### 2.2 Precedência
`year` menor; empate → `date` (se informada) → DOI lexicográfico. Regra fixa.

### 2.3 Validação numérica na carga
`vector` de monômio: 1.000 vetores aleatórios positivos → avalia `expr` → ajuste log-linear →
coeficientes = `vector` com |erro| < `vector_tol` (padrão 1e-6; LMI declara 1e-2 por PhA = atan).
`check_example`: |expr(inputs) − expected| ≤ tol. Falha → erro na carga.

### 2.4 Gramática (árvore sintática, lista branca)
Números; nomes canônicos das variáveis mapeadas e derivadas; nomes de `groups`; `+ - * / ** ( )`;
`log exp sqrt atan atan2 abs min max`; `pi`. Nada mais. Violação → erro na carga.

### 2.5 Regra do índice não positivo
Equação `affine` com valor ≤ 0 numa linha: linha fora da parte algébrica daquele método
(`n_nonpositive_pred` em `algebra.csv`); na auditoria a linha permanece.

### 2.6 Migração
`metodos_bia.json` → **31 entradas** (8 índices + 23 equações; metades por sexo unidas). Script testado.

### 2.7 Desenho de índices para um contexto (v0.4)
Um índice novo pode ser construído para um alvo (ex.: VO2máx): regressão de ln(alvo) em ln(variáveis) no conjunto
de **desenho**; os coeficientes são o vetor de expoentes do índice novo. Regra obrigatória: **desenho e auditoria em
conjuntos disjuntos**.
- `design.split`: `holdout` (padrão) com `fraction: 0.70` (opções declaradas 0.60, 0.75), `seed`, estratificado por
  `strata` e, em classificação, por classe; ou `by_stratum` (desenha num estrato, audita em outro; testa transferência).
- Os números reportados (Σ, redundância, auditoria, utilidade) vêm **só da partição de auditoria**.
- O vetor final para uso prático é reajustado em 100% dos dados e sai rotulado `refit_full=true`, com o vetor de
  desenho e o R² de ambos gravados no manifesto.
- Aviso no resumo quando a partição de auditoria tem n < 100 (intervalos largos).
- O índice desenhado entra no catálogo da execução como `user_entry` com `provenance.formula_source = "designed"`,
  `confidence = "low"` e o hash da partição de desenho — nunca vai para o catálogo embutido sem curadoria.
- Variáveis além da BIA (ex.: frequência cardíaca por estágio) entram como `variables` positivas e ampliam Σ;
  o índice desenhado pode combinar BIA e sinais funcionais.

**Justificativa.** Auditar no mesmo conjunto em que o índice foi ajustado mede ajuste, não validade. A partição é a
prática padrão de aprendizado de máquina e é o que permite dizer ao preparador físico "este índice prediz VO2máx em
pessoas que ele nunca viu". O reajuste final é o que se faz com qualquer modelo entregue.

**Justificativa.** Uma entrada por método é o que precedência e redundância exigem. `validity`
marca sem bloquear. `identity_of` impede que identidades inflem redundância e acurácia. Ramo só por
`groups` fecha o vazamento da Segal específica. Validação numérica e `check_example` fazem uma
fórmula errada falhar na carga, não no artigo. Lista branca substitui `eval`.

---

## 3. Contrato de CONFIGURAÇÃO

### 3.1 Exemplo completo (padrões = análise do artigo)
```yaml
run_name: nhanes_1999_2004
data: {path: nhanes_limpo.csv, encoding: utf-8, sep: auto, decimal: auto, columns: {…},
       drop_nonpositive: false, impute: false, max_missing_frac_warn: 0.10, min_n: 30, min_per_class: 20}
catalog: {path: builtin, include: all, exclude: [], user_entries: []}
strata: sexo
algebra:
  fit_affine: true
  extra_log_variables: []        # ex.: [idade] para incluir no ajuste log-linear (padrão: só variables)
  min_fit_r2: 0.90               # abaixo → poor_monomial
  redundancy_threshold: 0.95     # sobre |Spearman observado|
  min_pair_n: 30
  transfer: true
audit:
  task: auto                     # auto | regression | classification
  single:                        # índice isolado
    estimator: ridge             # ridge | logistic | "modulo:Classe"
    params: {alpha: 1.0}
  combination:                   # combinação de eixos (se combinations: true)
    estimator: hgb               # hgb (sklearn HistGradientBoosting) | xgboost (opcional) | "modulo:Classe"
    params: {max_depth: 3, learning_rate: 0.05, max_iter: 300}   # fixos, declarados antes
  sensitivity: {estimator: null, params: {}, nested_tuning: false}   # mesmo sorteio; reportado ao lado
  cv: {folds: 5, repeats: 50, stratified: auto}   # classificação: estratificada por classe
  bootstrap: {B: 2000, min_oob: 20, max_attempts_factor: 6}
  utility_margin: 0.03
  verdict: {p_specific: 0.95, p_control: 0.05, ci: 0.95}
  multiplicity: none             # none | bh  (bh = Benjamini–Hochberg entre métodos, como sensibilidade)
  combinations: false
seeds: {cv: 42, bootstrap: 42}
preset: article                  # quick (cv 5x5, B 200) | article
threads: 1
n_jobs: 1
output: {dir: ./zaku_out, figures: true}
```

### 3.2 Regras
- Estimador declarado antes; sem seleção pelo resultado. `sensitivity` roda nos mesmos sorteios e
  vai para `sensitivity.csv`; `nested_tuning: true` (Optuna, opcional) só nesse modo, com aviso de custo.
- Pipeline: `StandardScaler` → estimador, sobre **caso completo**: na auditoria de um índice, as linhas em que o índice
  e o alvo/controle existem; na utilidade e na combinação, as linhas completas na **união** das colunas das duas
  configurações comparadas (mesmas pessoas nos dois lados do contraste). `impute: true` insere `SimpleImputer(median)`
  antes da padronização e fica registrado no manifesto. Regressão padrão `Ridge`;
  classificação padrão `LogisticRegression(l2, C=1, lbfgs, max_iter=1000)`; multiclasse: um-contra-todos.
- Métricas: regressão `r2_score`; classificação binária `roc_auc_score`; multiclasse AUROC
  um-contra-todos macro + acurácia balanceada. OOB com uma só classe → reamostra descartada (`B_dropped`).
- **Reamostras compartilhadas por estrato**: `default_rng(seeds.bootstrap)`, `integers(0, n, n)` até
  B reamostras com OOB ≥ `min_oob`; usadas por todos os métodos, alvos, controles, configurações e
  estimadores. CV `RepeatedKFold`/`RepeatedStratifiedKFold(random_state=seeds.cv)`; com `id`, por grupos.
  `n_jobs` não altera nenhum número.
- `threads: 1` fixa OMP/OpenBLAS/MKL antes de importar numpy.
- Vereditos são **descritivos**: P do bootstrap não é valor-p; `multiplicity: bh` é sensibilidade.

**Justificativa.** Com um índice (uma coluna), um modelo flexível só pode capturar não linearidade
monótona e paga em variância, inflando o escore do controle em parte das reamostras; o contraste
pareado quer um estimador conservador dos dois lados. Otimizar hiperparâmetros por resultado dentro
do bootstrap quebraria o pareamento (escolhas diferentes para alvo e controle) e custaria dias;
por isso é modo de sensibilidade, aninhado, declarado. Na combinação de eixos (várias colunas,
interações) o boosting se justifica, com hiperparâmetros fixos e declarados. Reamostras
compartilhadas = comportamento da referência + condição de pareamento.

---

## 4. Contrato de SAÍDAS

### 4.1 Tabelas (CSV UTF-8, `,` e `.`, precisão completa, ordenação determinística; **só agregados**)
| arquivo | linha por | colunas |
|---|---|---|
| `algebra.csv` | método × estrato | `method_id, label, year, kind, form, stratum, n, n_nonpositive_pred, fit_r2, poor_monomial, e_<var>…, vector_source, out_of_validity_frac, provenance_confidence` |
| `sigma.csv` | estrato × par de variáveis | `stratum, n, var_i, var_j, cov_log` |
| `pairs.csv` | par × estrato | `a_id, b_id, stratum, n_pair, r_log_predicted, r_log_observed (Pearson nos logs; identidade exata), rho_sp_observed, rho_sp_converted, identity` |
| `redundancy.csv` | método × estrato | `method_id, stratum, rho_sp_max, predecessor_id, predecessor_year, redundant, identity_of` |
| `sigma_transfer.csv` | origem × destino | `sigma_from, observed_in, type, pairs, median_abs_err, max_abs_err` |
| `audit.csv` | método × estrato × alvo | `method_id, stratum, target, control, task, metric, estimator, n, B, B_eff, B_dropped, score_cv_target, score_cv_control, disc_mean, disc_lo, disc_hi, p_disc, verdict, out_of_validity_frac, provenance_confidence` |
| `utility.csv` | método × estrato × alvo | `…, covariates, score_base, score_with, delta_mean, delta_lo, delta_hi, p_delta, margin, useful` |
| `combinations.csv` | par ordenado × estrato × alvo | `host_id, added_id, rho_sp_predicted, score_host, score_pair, gain_mean, gain_lo, gain_hi, p_gain` |
| `sensitivity.csv` | como `audit.csv` | + `estimator_primary, disc_primary, disc_delta` |
| `screening.csv` | método × estrato | `method_id, stratum, redundant, specific, useful, identity, class` |

**Verificação primária da álgebra = Pearson nos logaritmos**, previsto × observado: identidade
algébrica, sem suposição distribucional. **Redundância = Spearman observado** (não paramétrico).
A conversão Σ→Spearman fica como coluna secundária, com a suposição declarada.

### 4.2 Manifesto (`manifest.json`)
`package_version, catalog_version, catalog_sha256, config_sha256, config_resolved, preset, seeds_used,
resampling_scheme, versions {python, numpy, pandas, scipy, sklearn, matplotlib}, platform, threads, n_jobs,
started_at, finished_at, wall_seconds, input_sha256, input_rows, sep_used, decimal_used, encoding_used,
rows_dropped {…}, strata_used {…}, methods_evaluated, methods_skipped {id: motivo}, warnings, outputs_sha256 {…}, schema_version`.

### 4.3 Resumo (`summary.md`)
Preset (aviso se `quick`); por estrato: n, métodos, redundantes com antecessor, específicos / medem
controle / inconclusivos, úteis; flags; 10 pares de maior erro previsto×observado; 3 casas só aqui.
Correlação alvo↔controle por estrato, com aviso acima de 0,8 (controle quase colinear com o alvo).

### 4.4 Figuras (`figures/`, PNG 300 dpi + PDF; a partir das tabelas; semente fixa em jitter)
1 `compass` (setas no espaço de expoentes) · 2 `predicted_observed` (Pearson nos logs; identidades
excluídas) · 3 `precedence_tree` · 4 `specificity_quadrant` (escore controle × alvo; qualquer métrica)
· 5 `screening_map` (assinatura) · 6 `sigma_transfer` · 7 `combination_gain`.
**Portão:** inspeção de cada figura pelo Thalles antes do fechamento da v1.0.

### 4.5 Progresso
CLI e API imprimem, por estrato e método, contagem, tempo decorrido e estimativa de término, desde o
primeiro método.

**Justificativa.** Precisão completa permite equivalência a 1e-9. Pearson nos logs como verificação
primária remove a única suposição da parte algébrica. Só agregados nas saídas é o que permite rodar
em dados que não podem sair (container em parceiros). Figuras das tabelas garantem concordância.

---

## 5. Contrato de REPRODUTIBILIDADE
- Determinismo: mesma entrada + configuração + versões ⇒ mesmos `outputs_sha256`, para qualquer `n_jobs`.
- Equivalência com o **motor anterior** (scripts de 08–09/09/2026), onde o método não mudou: com `preset: article`,
  sementes 42/42, `threads: 1`, Python 3.11.13, numpy 2.3.5, pandas 2.3.3, scipy 1.16.2, scikit-learn 1.4.2, o pacote
  reproduz os CSVs do NHANES (09/09/2026) e do piloto v2 com tolerância **1e-9 na mesma máquina** e **1e-6 entre
  máquinas** para estatísticas não baseadas em postos (expoentes ajustados, R², Pearson dos logs, escores de
  validação cruzada e bootstrap). Estatísticas de posto (Spearman) a **1e-6** e contagens discretas (pares dentro do IC)
  com **±1 par**: verificado em 10/09/2026 que o CSV de referência carrega diferenças de 1 ulp nas colunas derivadas
  (H_m, II) que desfazem empates nos postos e deslocam o Spearman em ~3e-7.
- Exceções declaradas (o motor anterior fazia diferente e o framework é mais rigoroso): Segal específica selecionada
  por %gordura do DXA (vazamento; o framework só seleciona por `groups`); IMC como método (fora do catálogo);
  identidades por escala contadas como redundância (o framework as separa); precedência só por ano (o framework usa
  ano > data > DOI). Nos testes, esses casos são reproduzidos por entradas só-de-teste ou excluídos, com o motivo escrito.
- Teste rápido em CI: recorte fixo (400 linhas, 5 métodos, `quick`), referência congelada, < 60 s.

**Justificativa.** O artigo será produzido pelo framework. A equivalência com o motor anterior é verificação de
implementação onde o método não mudou; não amarra decisões de rigor. Declarar as exceções agora evita "ajustar" o
teste depois para passar.

---

## 6. Changelog
- **v0.4.2 (10/09/2026)** — decisão: o framework tem **três figuras oficiais** (mapa de expoentes; previsto × observado; quadro de vereditos). Faixas de precedência, transferência de Σ, ganho por combinação e bússola são suplementares, geradas só com `output.supplementary_figures: true`.
- **v0.4.1 (10/09/2026)** — catálogo: campo `status` (`active` | `excluded` com `exclusion_reason` obrigatória; excluído nunca é avaliado e sai em `methods_skipped`); `strata` tem fonte única (topo da configuração; conflito com `columns.strata` → erro); figuras revistas após inspeção (§4.4): quadro de vereditos (`board`, assinatura) substitui quadrante e mapa; mapa de calor de expoentes substitui a bússola acima de 10 métodos; árvore de precedência em faixas por linhagem, sem aleatoriedade; paleta validada (2 cores: azul específico, laranja mede-controle; cinza = desênfase; identidade = forma/rótulo; procedência ≠ alta = marcador vazado).
- **v0.4 (10/09/2026)** — §2.7 desenho de índices com partição obrigatória (holdout 70:30 padrão, `by_stratum` opcional), reajuste final rotulado, aviso de n<100, entrada `designed` no catálogo da execução.
- **v0.3.2 (10/09/2026)** — sem imputação por padrão (decisão do Thalles): caso completo por método; utilidade e
  combinação em caso completo na união das colunas; `max_missing_frac_warn` no resumo; `impute` só explícito. Na
  referência NHANES o imputador nunca agiu (linhas sem índice eram removidas antes do modelo), logo a equivalência não muda.
- **v0.3.1 (10/09/2026)** — §5: tolerâncias separadas para estatísticas de posto (1e-6) e contagens (±1 par), com a causa
  verificada; `form` ∈ {monomial, composite, closed} (o antigo "affine" é caso de composite; a BIVA específica não é
  soma nem produto e recebe o mesmo ajuste log-linear); `doi` pode ser `null` só com `pmid` (obras sem DOI); `frequency_khz`
  aceita lista (multifrequência).
- **v0.3** — simplificação (decisões do Thalles): desfecho do pesquisador; Xc obrigatória; frequência
  declarada e mínima, várias permitidas; fora: critério/DXA, pré-calculados, segmentares, peso amostral,
  Excel. Dois estimadores padrão por papel (isolado: Ridge/logística; combinação: HistGradientBoosting
  fixo; XGBoost opcional); Optuna só em sensibilidade aninhada; multiclasse (AUROC OvR macro + acurácia
  balanceada); CV estratificada em classificação; vereditos descritivos + BH opcional; **Pearson nos logs
  como verificação primária** (exata) e Spearman como redundância (não paramétrico); progresso obrigatório;
  só agregados nas saídas; `extra_log_variables` para idade; diagnóstico alvo↔controle no resumo.
- v0.2 — revisão de rigor (CV por id, separador determinístico, units, pairing, validação numérica
  de vector, check_example, reamostras compartilhadas, threads=1, precisão completa, hashes, 31 entradas).
- v0.1 — primeira versão.

## 7. Aprovação
Thalles lê, marca discordâncias, responde "aprovado" ou lista de mudanças. Só então começa a etapa 2.
