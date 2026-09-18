# BioMS Zaku — contratos (v0.5.2, 14/09/2026; changelog na seção 6)

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
Uma tabela, **uma linha por pessoa** (§3.2): `id` repetido é recusado na entrada, com a instrução de agregar antes.
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
| `id` repetido | erro, nomeando quantos ids têm mais de uma linha e pedindo agregação (§3.2) |

### 1.4b Exemplo real embarcado (v1.2, decisão de 16/09/2026)
`examples/nhanes_diabetes_400.csv`: 400 linhas REAIS dos arquivos públicos do NHANES 1999–2004 (CDC, domínio público; redistribuição
permitida), adultos 18–49 com DXA medida e BIA 50 kHz, casos completos, mais a resposta do questionário de diabetes
(`diabetes_1Y_0N`, diagnóstico médico). Amostra **enriquecida em casos** (todos os diabéticos com dados completos e sorteio de não
diabéticos com semente): não representa prevalência; existe para demonstrar a auditoria de classificação (≥ 20 por classe por
sexo) e a regressão em dados reais. Procedência, exclusões, semente e SHA-256 em `examples/nhanes_diabetes_400_provenance.json`;
gerador `tools/make_nhanes_example.py` (determinístico). Até esta versão todos os exemplos eram sintéticos; este é o único com
linhas reais, e continua valendo: nenhum resultado do framework depende dele (independência do piloto, §5).

### 1.4c Exemplos embarcados no pacote e saídas numeradas (v1.2, 16/09/2026)
`examples/` entra na roda como `bioms_zaku/examples` (nada é baixado). API `bioms_zaku.datasets` (`list_examples`, `example_path`,
`load_example`, `copy_examples`) e comando `bioms-zaku examples [--copy PASTA] [--name ...]`; cada exemplo é rotulado **sintético**
ou **real**; a cópia nunca altera uma pasta existente (`_2`, `_3`, …) e reescreve `data.path` dos YAML para a própria pasta.
**Base de exemplo única (decisão de 17/09/2026):** `zaku_exemplo.csv`, sintética, 200 por sexo, sorteada de log-normais cujos μ e Σ
foram estimados no NHANES 1999–2004 por célula sexo × diabetes (DIQ010 1 vs 2; n de origem 79/2696 mulheres, 60/2960 homens);
70 com diabetes por sexo (enriquecida, declarado); `label_synthetic` depende só de ln FMI e ln idade (gabarito). Validação: num
sorteio grande dos mesmos parâmetros, a matriz de correlação 12 × 12 (11 ln variáveis + diabetes) difere da do NHANES reponderado
a 35 % em no máximo 0,013. Gerador `tools/make_zaku_example.py` e parâmetros publicados (reprodução byte a byte, testada).
É o único arquivo copiado por padrão; os demais são técnicos (`--all`). **Saídas**: se `output.dir/run_name` já contém `manifest.json`, a execução vai para
`run_name_2`, `_3`, …; `output.overwrite: true` substitui e o aviso fica no manifesto; `manifest.output_folder` registra a pasta.

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
| `validity` | sim | aplicabilidade **afirmada ou testada pelo autor**: `{age, bmi, sex, population}`, `null` onde o autor não afirma nada (sem flag); fora da faixa → flag †, **nunca bloqueio** — o pesquisador pode aplicar qualquer método a qualquer contexto; a figura só avisa |
| `target_kind` | não | categoria do que o autor diz medir: `lean_mass` \| `fat_mass` \| `body_water` \| `hydration` \| `cell_mass` \| `other`. Comparada com `declarations.target_kinds` da configuração (§3.2): índice de gordura auditado contra alvo de massa magra recebe aviso "acompanha o controle por desenho; inverta alvo e controle" — aviso, nunca bloqueio |
| `derivation_sample` | não | quem foi usado para ajustar: `{n, sex, age, condition, country}`; descritivo, nunca gera flag. Distinto de `validity` (Hoffer 1969: derivado em 20 homens saudáveis, testado e proposto para pacientes de ambos os sexos, 18-77 anos) |
| `provenance` | sim | `{formula_source: pdf_table|pdf_text|pmc_text|abstract|review_table, source_detail, verified_by, verified_on, confidence}`; mapa padrão pdf/pmc → high, abstract → medium, review → low |
| `check_example` | obrig. para contribuições | `{inputs, expected, tol}` com valor publicado; testado na carga |
| `identity_of` | não | transformação exata de outro método → sai como `identity`, excluído das estatísticas de previsão |
| `curated`, `curation_record` | não (padrão `false`) | **curado** = a fonte primária foi lida criticamente, com registro em `catalogo/fontes_primarias_indices/LEITURAS.md`, e a entrada aprovada. Exige `confidence: high` e fórmula de PDF. **Só métodos curados entram na auditoria por padrão** (`catalog.include: curated`, §3.2). Confiança alta sozinha NÃO é curadoria: fórmula copiada certa de um PDF pode não ter passado pela leitura. Em 14/09/2026: 8 curados (Hoffer 1969, Lukaski 1985, Baumgartner 1988, Piccoli 1994 R/H e Xc/H, LMI, Rsp, Xcsp); as equações preditivas ficam no catálogo sem curadoria até serem lidas uma a uma |
| `n`, `r2`, `see`, `device`, `reference_method`, `notes` | não | `null` quando não informado; nunca inventado |

### 2.2 Precedência
`year` menor; empate → `date` (se informada) → DOI lexicográfico. Regra fixa.

### 2.3 Validação numérica na carga
`vector` de monômio: 1.000 vetores aleatórios positivos → avalia `expr` → ajuste log-linear →
coeficientes = `vector` com |erro| < `vector_tol` (padrão 1e-6; máximo 1e-4, folga numérica, não orçamento de aproximação).
**Regra de exatidão (v0.4.5):** o vetor do catálogo é exato ou não é vetor. Nomes derivados que não são monômios nas
variáveis base (`PhA` = atan(Xc/R); `Z` = √(R²+Xc²)) são aceitos em `expr`, nunca em `vector`; o método é `composite`,
recebe vetor ajustado por estrato e o `fit_r2` fica na tabela e na figura (o antigo "linearizar atan com tolerância 0,03"
foi removido: PhA e LMI passaram a `composite`). `II` e `H_m` continuam re-expressões exatas.
`check_example`: |expr(inputs) − expected| ≤ tol. Falha → erro na carga.
Versão e histórico: `catalog_version` (semântico) e `history` (uma linha por evento de curadoria: versão, data, autor,
mudança). A versão 1.0.0 nasceu da migração do catálogo do piloto (08/09/2026); desde então o catálogo evolui só por curadoria, registrada em `history`.

### 2.4 Gramática (árvore sintática, lista branca)
Números; nomes canônicos das variáveis mapeadas e derivadas; nomes de `groups`; `+ - * / ** ( )`;
`log exp sqrt atan atan2 abs min max`; `pi`, `e`. **Estatísticas amostrais (v0.9):** `mean(x)`, `median(x)`, `sd(x)` reduzem o
argumento sobre as linhas avaliadas (um estrato, os casos completos que entram na álgebra) a um único número, aplicado a
todas as linhas (`sd` com ddof=1; NaN ignorado). Um índice que as usa não é fórmula fixa: seus valores mudam em cada amostra.
Por isso: cada valor usado é registrado no manifesto (`sample_statistics[estrato][método]`), gera aviso na execução, aparece
no resumo e na seção de rigor do relatório; `algebra.uses_sample_stats` marca o método. Nunca usam o alvo nem o controle
(só variáveis mapeadas), logo não vazam informação do alvo para a validação cruzada. Nada mais. Violação → erro na carga.

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
- Os expoentes são derivados na amostra, nunca assumidos (princípio de Benn; Heymsfield 2007 mostra β ≈ 2 para a altura
  quando ela é o único preditor). Com W, R e Xc no mesmo ajuste, o expoente de H sai menor que 2 (ex.: 1,05–1,27 no NHANES),
  porque parte do tamanho é absorvida pelas outras variáveis; não contradiz Heymsfield, é o mesmo modelo com mais preditores.

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
run_name: my_study
data: {path: my_data.csv, encoding: utf-8, sep: auto, decimal: auto, columns: {…},
       drop_nonpositive: false, impute: false, max_missing_frac_warn: 0.10, min_n: 30, min_per_class: 20}
catalog: {path: builtin, include: curated, exclude: [], user_entries: []}   # curated (padrão) | all | [ids]
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
geometry:                        # v0.6 — diagnóstico alvo↔controle no espaço das variáveis mapeadas
  enabled: true
  parallel_to_control: 0.90      # |cos_Σ(índice, controle^)| ≥ → PARALLEL_TO_CONTROL
  coupled_target_control: 0.80   # |cos_Σ(alvo^, controle^)| ≥ → COUPLED_TARGET_CONTROL
  min_fit_r2: 0.50               # projeção com R² abaixo → cossenos reportados, bandeiras NÃO acendem (poor_projection)
seeds: {cv: 42, bootstrap: 42}
preset: full                     # quick (cv 5x5, B 200) | full
threads: 1
n_jobs: auto                   # auto = núcleos − 1 (v1.2); qualquer inteiro ≥ 1; nunca altera um número
output: {dir: ./zaku_out, figures: true}
```

### 3.2 Regras
- **Bootstrap válido ou recusado (v1.0, 15/09/2026; caso: CrossFit, 107 homens, desenho deixou 33 para auditar → 1 reamostra válida em
  2.000 → intervalos de largura zero e vereditos espúrios).** (a) A auditoria de um método é recusada, com aviso no manifesto, quando
  o número de reamostras válidas (≥ `min_oob` fora da bolsa) fica abaixo de `max(20, 10 % de B)`, nunca acima de B; nenhum intervalo
  degenerado é jamais publicado. (b) `check` e `start` avaliam `min_n` e a viabilidade do bootstrap **na partição de auditoria** de
  cada estrato quando há desenho (`(1 − fraction) · n`), com rótulos, e bloqueiam com a saída (mais linhas ou sem estrato; a rodada
  padrão não é afetada). Consequência prática: desenhar índices com auditoria válida exige ≈ 55 pessoas auditadas por estrato
  (≈ 185 por estrato a 70/30). (c) Aviso no manifesto quando mais da metade das reamostras foi descartada num estrato. Testes.
- **`run` valida antes de rodar (14/09/2026).** A mesma verificação de `check` roda no início de `run` (CLI e API); problema
  bloqueante para a execução com as mensagens do `check` e código de saída 2. Nunca se produz relatório com todas as auditorias
  puladas. `init` grava `data.encoding` e, se não conseguir decodificar, diz qual `--encoding` tentar (sem traceback).
- **Catálogo por padrão = só curados (decisão de desenho, 10/09, reafirmada 14/09).** `catalog.include: curated` é o padrão do pacote e
  do `init`; `all` é escolha explícita do usuário e marca com * toda saída de método não curado; lista de ids é escolha explícita.
  Registro do erro: em 14/09 o padrão foi trocado para `all` dentro de uma correção de bug, sem consulta; revertido no mesmo dia e
  travado por teste (`tests/test_catalog.py`, `tests/test_init_check.py`). Regra de trabalho: decisão de desenho nunca muda dentro
  de correção.
- **Controle negativo condicional (v0.5).** Além de escore(alvo | índice) e escore(controle | índice), a auditoria ajusta,
  nas MESMAS reamostras, o controle como preditor do alvo (com e sem o índice) e o alvo como preditor do controle (com e
  sem o índice). Dois incrementos pareados: **S1** = escore(alvo | controle + índice) − escore(alvo | controle), o sinal
  sobre o alvo que o controle não carrega; **S2** = escore(controle | alvo + índice) − escore(controle | alvo), o sinal
  sobre o controle que o alvo não explica. Um incremento está *presente* quando média > `verdict.margin` (0,03), IC 95 %
  exclui 0 e P(d>0) ≥ `p_specific`. Vereditos: `SPECIFIC` (S1 presente, S2 ausente) · `TRACKS_CONTROL` (S2 presente, S1
  ausente) · `BOTH` (os dois: o índice carrega informação que nem alvo nem controle explicam, p. ex. tamanho corporal)
  · `NEITHER` (nenhum). A regra anterior (diferença marginal `disc`) fica em `verdict_marginal`, descritiva, para
  comparação lado a lado com o condicional. Justificativa: alvo e controle correlacionam (0,7 no NHANES); a diferença marginal
  dava crédito ao índice pela parte do alvo que o controle também carrega; o condicional pergunta o que o índice acrescenta.
- **Amostra de conveniência.** O framework não estima parâmetros populacionais: pesos amostrais são ignorados por
  desenho e os vereditos descrevem a amostra analisada. O resumo declara isso.
- `declarations.target_kinds` (opcional): `{coluna: lean_mass|fat_mass|body_water|hydration|cell_mass|other}` para alvos e
  controles. Quando o `target_kind` de um método coincide com o tipo do controle e difere do tipo do alvo, o resumo e
  o relatório recebem um aviso de orientação (v0.4.6). Sem declaração, nada muda.
- Estimador declarado antes; sem seleção pelo resultado. `sensitivity` roda nos mesmos sorteios e
  vai para `sensitivity.csv`; `nested_tuning: true` (Optuna, opcional) só nesse modo, com aviso de custo.
- Pipeline: `StandardScaler` → estimador, sobre **caso completo**: na auditoria de um índice, as linhas em que o índice
  e o alvo/controle existem; na utilidade e na combinação, as linhas completas na **união** das colunas das duas
  configurações comparadas (mesmas pessoas nos dois lados do contraste). `impute: true` insere `SimpleImputer(median)`
  antes da padronização e fica registrado no manifesto. Regressão padrão `Ridge`;
  classificação padrão `LogisticRegression(l2, C=1, lbfgs, max_iter=1000)`; multiclasse: um-contra-todos.
- Métricas (v1.2, revisão de citações de 16/09/2026): regressão `r2_score`; classificação **D de Tjur** = média de p̂ nos casos −
  média nos não casos (Tjur 2009; a grandeza que o IDI de Pencina 2008 compara), assintoticamente fração de variação explicada,
  por isso os ganhos ΔD compartilham a margem 0,03 do R² por analogia declarada; multiclasse: D macro um-contra-todos (extensão
  desta ferramenta, declarada). ΔAUROC NÃO é ganho (insensível mesmo a marcadores fortes, Pencina 2008); a AUROC (Hanley & McNeil
  1982) é reportada como descritiva (`auroc_cv_target_full`, `auroc_cv_control_full`, `auroc_cv_with`); no multiclasse, AUROC macro
  um-contra-todos é a única descritiva (a acurácia balanceada, antes prometida e nunca implementada, foi retirada em 16/09/2026:
  depende de um corte de probabilidade, como F1; Brodersen 2010 lido e julgado dispensável). **Tipos mistos**: alvo de
  classe com controle contínuo (e vice-versa) é permitido — tarefa e estimador por coluna (logística L2 para classe, ridge para
  contínuo) nas mesmas reamostras; S1 em ΔD e S2 em ΔR², mesma margem; `control_task` e `metric_control` na `audit.csv`.
  Estimador declarado com parâmetros ou `modulo:Classe` vale para todas as colunas.
  Com penalidade L2 as probabilidades previstas encolhem para a taxa-base e o D sai menor do que sem penalidade; como os ganhos
  são diferenças pareadas sob o mesmo encolhimento, a comparação entre modelos é justa (declarado; Tjur 2009, Le Cessie 1992). OOB com uma só classe → reamostra descartada
  (`B_dropped`). `check` recusa rótulo constante ou com classe < `min_per_class` dentro de um estrato (um rótulo usado como
  controle não pode ser também o estrato).
- **Eventos por variável (Peduzzi 1996), declarados e nunca barreira** (decisão de 16/09/2026): para cada modelo de classificação,
  `events_min_class` (classe menor nas linhas completas) e `epv_train` = 0,632 × classe menor ÷ preditores (2 na auditoria,
  covariáveis + 1 na utilidade; 0,632 = fração distinta de uma reamostra bootstrap, Efron 1983); `epv_low` abaixo de 10.
  `check` avisa; o relatório marca; o veredito sai. O mínimo por classe fica em 20 (operacional). Um segundo classificador
  (hgb/xgboost) entra só como `sensitivity`, ao lado, nunca escolhido — boosting precisa de mais dados que a logística.
- **Reamostras compartilhadas por estrato**: `default_rng(seeds.bootstrap)`, `integers(0, n, n)` até
  B reamostras com OOB ≥ `min_oob`; usadas por todos os métodos, alvos, controles, configurações e
  estimadores. CV `RepeatedKFold`/`RepeatedStratifiedKFold(random_state=seeds.cv)`; com `id`, por grupos.
  `n_jobs` não altera nenhum número.
- **Uma linha por pessoa (v1.2, decisão de 16/09/2026).** `id` repetido é recusado na entrada com a instrução de agregar antes
  (média por pessoa ou uma visita). Razão: as reamostras bootstrap sorteiam linhas como pessoas independentes; medidas repetidas
  dariam intervalos estreitos demais e vereditos otimistas. **Trabalho futuro, a repensar**: bootstrap por conglomerado (sortear
  pessoas e levar todas as suas linhas; fora da bolsa = pessoas não sorteadas), referência Field & Welsh 2007, JRSS B 69(3):369–390,
  10.1111/j.1467-9868.2007.00593.x — abriria o caso pré/pós, comum em BIA.
- **O que o bootstrap fora da bolsa é, e o que não é**: as reamostras também são dependentes entre si; o intervalo percentil
  não é um estimador não viesado da variância. É um procedimento sem hipótese distribucional que reamostra o pipeline inteiro
  por pessoa (Efron 1979). Pontuar cada reamostra nas pessoas não sorteadas é o estimador ε₀ de Efron 1983 (JASA 78:316–331):
  pessimista para um escore absoluto (daí o .632 dele), aqui usado só em diferenças pareadas de modelos aninhados nas mesmas
  linhas, onde o pessimismo cancela; a correção .632 não se aplica. A dispersão entre dobras da validação cruzada nunca entra na inferência, porque não existe estimador
  não viesado da sua variância (Bengio & Grandvalet 2004).
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

### 3.3 Geometria alvo↔controle (v0.6 — aprovado pelo Thalles em 14/09/2026)

**Problema que resolve.** Alvo e controle costumam vir da mesma medida de referência e da mesma normalização (ex.: massa
magra/H² e massa gorda/H² do mesmo scan DXA; magro + gordo + osso = peso, com H e W mapeadas). No espaço das variáveis
mapeadas eles podem apontar quase na mesma direção. Nesse caso um índice próximo dessa direção (ex.: W/H²) prediz os
dois por aritmética, e o veredito do controle negativo é correto pela razão errada. A v0.6 mede isso e imprime ao lado
do veredito. **Nunca altera um veredito**: o veredito é empírico (fora da amostra); a geometria explica por quê.

**Definições (por estrato, caso completo, mesmas variáveis do espaço dos índices: `variables` + `extra_log_variables`).**
1. *Vetor implícito* de um alvo ou controle y: coeficientes da regressão linear de ln y nas log-variáveis, com
   intercepto (`fit_log_linear`, a mesma função dos métodos `composite` e do desenho §2.7). Registra-se o R² do ajuste.
   É a melhor aproximação monomial de y no espaço medido; não é y.
2. *Cosseno sob Σ* de dois vetores a, b: cos_Σ(a, b) = aᵀΣb / √(aᵀΣa · bᵀΣb) — a mesma fórmula de `r_log_predicted`
   (§4.1). É a correlação de Pearson (nos logs) entre as duas combinações lineares.
3. Para cada índice i, alvo t e controle c (pares declarados em `pairing`): cos_Σ(i, t^), cos_Σ(i, c^) e cos_Σ(t^, c^).
4. **Identidade de verificação (exata, in-sample):** como um índice MONOMIAL pertence ao subespaço gerado pelas
   log-variáveis e o resíduo ln y − ln y^ é ortogonal a esse subespaço, r_log(i, y) = cos_Σ(i, y^) · √R²_y. A tabela grava
   r_log(i, y) observado, o produto previsto e a lacuna; para índices de vetor exato (`vector_source = catalog`) a lacuna
   tem de ser < 1e-9 (teste; no exemplo sai ~1e-15). Para índices compostos (PhA, LMI, Rsp, Xcsp: vetor ajustado) a
   lacuna é o resíduo da projeção do próprio índice e é reportada, não testada. Tudo para um índice é calculado nas
   linhas completas de (índice > 0, alvo > 0, controle > 0, variáveis), para a identidade ser exata por construção.

**Bandeiras (nomes fixos; limiares declarados no YAML e gravados no manifesto).**
- `PARALLEL_TO_CONTROL`: |cos_Σ(i, c^)| ≥ `parallel_to_control` (padrão 0,90 = 81 % de variância compartilhada com a
  projeção do controle). Leitura: o índice aponta para onde o controle aponta; "acompanha o controle" ou "ambos" era
  esperado pela geometria.
- `COUPLED_TARGET_CONTROL`: |cos_Σ(t^, c^)| ≥ `coupled_target_control` (padrão 0,80 = 64 %). Leitura: o contraste
  inteiro é fraco por construção; acende ANTES do outro porque a consequência é maior (vale para todos os índices).
- `poor_projection`: R² da projeção < `min_fit_r2` (padrão 0,50) para t ou c. Cossenos continuam na tabela; bandeiras
  não acendem, porque o cosseno entre projeções pobres fala de ruído.
- Os limiares são auxílios de leitura, não testes de hipótese: os cossenos vão sempre na tabela, com precisão completa.

**Onde aparece.** `implicit_vectors.csv` e `geometry.csv` (§4.1); bloco "Geometria" no resumo (§4.3: cos alvo–controle
por estrato, lista dos índices com bandeira); marcador ‡ no scorecard e contorno tracejado no mapa alvo×controle (§4.4);
`report.html` herda as tabelas. Zero computação nova: são reutilizadas `fit_log_linear`, `log_covariance` e
`predicted_pearson_log`.

**Alvos em quilogramas (opção, não regra).** Um alvo em kg (massa magra absoluta) em vez de índice (massa/H²) remove a
altura dos dois lados e reduz cos_Σ(t^, c^); NÃO remove o acoplamento por W (magro + gordo + osso = peso) e torna o alvo
mais "tamanho", o que favorece índices de volume (H²/R). É escolha declarada do pesquisador; o framework aceita qualquer
coluna e imprime a geometria de cada escolha. O exemplo embarcado passa a trazer `lean_kg`, `alm_kg` e `fat_kg`, derivados
por índice × (H/100)² no gerador (colunas registradas em `example_data_params.json` como derivadas; sem sorteio novo).

**Justificativa.** A crítica "alvo e controle são aritmética sobre a medida de referência" é a que um revisor faria. A
resposta científica não é negá-la nem tentar "desacoplar tudo": é medir o acoplamento com a álgebra que o método já usa
e imprimi-lo ao lado do veredito, para o pesquisador decidir com o número na mão. O eixo de utilidade (§3.2, ganho
sobre W e H) continua sendo o que condiciona no tamanho; a geometria diz quanto do veredito é geometria.

**Verdades conhecidas exigidas (portão):** lição 12 do caderno (cosseno sob Σ à mão, 1e-9); alvo construído como
monômio ⇒ vetor implícito recupera os expoentes exatos e cos = 1 (1e-9); controle construído paralelo ao alvo ⇒ bandeira
acende, ortogonal ⇒ apagada; identidade do item 4 no exemplo embarcado (1e-9); os cossenos do exemplo (F: alvo–controle
0,90; Rsp–controle 0,93 · M: 0,86; 0,91, calculados à mão em 14/09) reproduzidos pela tabela; determinismo e hash.

---

### 3.4 Idioma (v0.7, 14/09/2026)
- Um único catálogo de mensagens (`i18n.py`), quatro línguas: `en`, `es`, `pt`, `it`. Teste exige as mesmas chaves e os mesmos campos de
  formato nas quatro; nenhuma mensagem fica sem tradução em silêncio.
- Escolha em um só lugar: `--lang` na CLI (vale para `init`, `check`, `run`) ou `language:` no YAML (o `init` pergunta o idioma primeiro e
  grava). `figures.language` segue `language` salvo se declarado. A API (`run(cfg)`) lê `language` do YAML.
- Traduzido: perguntas do `init`, mensagens do `check` e do `run`, `summary.md`, cabeçalhos do `report.html`, textos das figuras e
  legendas do `figures/README.md`. NÃO traduzido, por reprodutibilidade entre usuários: nomes de colunas dos CSVs, chaves do YAML,
  ids de métodos, vereditos (`SPECIFIC`, `TRACKS_CONTROL`, `BOTH`, `NEITHER`) e nomes das bandeiras.
- Justificativa: a ferramenta é para pesquisadores; a leitura na própria língua é parte de ser intuitiva. O que é para máquina fica
  estável.

---

### 3.6 Pressupostos declarados e limiares com origem (v1.1, 16/09/2026)
Todo relatório traz a seção **Pressupostos e limiares**, gerada da execução: cada procedimento com o pressuposto que carrega e o
seu estado naquela execução (por construção · verificado, com o número · limitação declarada), e cada limiar com valor, origem e
sustentação. Os ajustes de pressuposto desta versão:
- **Pares:** intervalo bootstrap de pessoas para a correlação de Pearson dos logs (`r_log_lo`, `r_log_hi`, nível `pair_ci_level`),
  sem pressuposto de distribuição; o intervalo de Fisher (normalidade bivariada, rejeitada no NHANES) foi removido. Teste de cobertura.
- **Escala da auditoria:** `audit.scale: log` por padrão — índice, alvos/controles contínuos e covariáveis entram como logaritmos, a
  escala da álgebra; rótulos de classificação nunca são transformados; valor não positivo em alvo/controle/covariável faz o estrato
  cair para a escala bruta com aviso (`audit.scale` registrado por linha). A outra escala é auditada e reportada em
  `sensitivity_scale.csv` (`audit.sensitivity.scale`, ligado no preset `full`), nunca escolhida.
- **k métodos, uma regra:** a regra do veredito é por método, sem correção, e o relatório o diz; nas mesmas reamostras calcula-se o
  intervalo ao nível de família 1 − 0,05/k (`ci_family`, `verdict_family`, colunas `*_fam`) e a sensibilidade de limiares ganha uma
  linha por método com `ci_level` = nível de família; com k = 1 é idêntico ao padrão. Reportado, nunca escolhido.
- **Valores faltantes:** linhas com valor faltante nas colunas mapeadas são excluídas e contadas por motivo; os resultados descrevem
  as pessoas que ficaram; sem imputação e sem comparação com as excluídas (o framework descreve a amostra analisada, não estima
  população — decisão de 16/09/2026).
- **Expoentes desenhados:** intervalo bootstrap de pessoas por expoente (`vector_lo`, `vector_hi`, B = `transfer_B`) no manifesto,
  no resumo e na tela de sugestões; o vetor usado continua sendo o ajuste da partição inteira.

| limiar | valor | origem | sustentação |
|---|---|---|---|
| redundância, \|Spearman\| ≥ | 0,95 | ancorado na literatura | o 0,95 fica abaixo da repetibilidade intra-sessão das variáveis brutas: ICC(2,1) a 50 kHz de 0,986 a 1,00 para R, Xc e PhA em quatro aparelhos, dez segundos de intervalo (Lafontant 2026, 10.2478/joeb-2026-0010), e PhA entre dois modelos da mesma fabricante, três posturas e dois eletrodos ICC 0,993, com deslocamento sistemático de nível de até 1° (Yang 2023, 10.3390/life13051119: a ordem se preserva, o nível se desloca — razão dos postos); dois índices a 0,95 diferem mais do que a medida repetida — piso conservador; confiabilidade vale por marca e modelo (bases de aparelhos diferentes nunca se juntam); a concordância observável entre dois índices da mesma medida é limitada por √(ICC_a·ICC_b) (atenuação, Spearman 1904, 10.2307/1412159) — âncora por analogia, declarada como tal; sensibilidade fixa |
| margem do veredito, ganho em R² (regressão) ou em D de Tjur (classificação) | 0,03 | ancorado na literatura | Caso 1 do cap. 9 de Cohen 1988 (2ª ed.; DOI da reimpressão 10.4324/9780203771587): f² = ΔR²/(1 − R²_total), A = controle (ou W e H), B = índice; pequeno f² = 0,02 ⇒ ΔR² ≤ 0,02 para qualquer base, logo 0,03 fica acima; valores de Cohen são populacionais e o ganho aqui é fora da amostra (margem conservadora); Cohen chama a convenção de compromisso a rejeitar quando não servir — grade de sensibilidade; classificação: ganho em D de Tjur, assintoticamente fração de variação explicada (relações exatas com os R² quadráticos, Tjur 2009, 10.1198/tast.2009.08210), mesma margem por analogia declarada; ΔAUROC seria insensível (Pencina 2008, 10.1002/sim.2929) |
| P(ganho > 0) ≥ | 0,95 | convenção | espelho do 5 % unilateral |
| nível do intervalo | 95 % | convenção | universal; nível de família 1 − 0,05/k reportado |
| margem do valor acrescentado | 0,03 | ancorado | mesma âncora da margem do veredito |
| cos paralelo / acoplado / R² projeção | 0,90 / 0,80 / 0,50 | decisão do framework | bandeiras descritivas; cossenos e R² publicados por inteiro |
| tolerância da transferência de Σ | 0,05 | decisão do framework | tolerância fixa em r, justa com n |
| B do bootstrap | 2 000 | convenção | percentis estáveis (Efron 1979) |
| validação cruzada | 5 × 50 | convenção | CV repetida para a estimativa pontual (Stone 1974), estratificada por classe na classificação (Kohavi 1995); dispersão entre dobras nunca usada para inferência, sem estimador não viesado da variância (Bengio & Grandvalet 2004); intervalos do bootstrap de pessoas (Efron 1979) |
| partição de desenho | 70/30 | convenção | opções declaradas 60 e 75 |
| n mínimo / fora da bolsa / reamostras válidas | 30 / 20 / máx(20, 10 % de B) | decisão do framework | mínimos operacionais (ridge com um preditor; reamostra pontuável; intervalo não degenerado) |

## 4. Contrato de SAÍDAS

### 4.1 Tabelas (CSV UTF-8, `,` e `.`, precisão completa, ordenação determinística; **só agregados**)
| arquivo | linha por | colunas |
|---|---|---|
| `algebra.csv` | método × estrato | `method_id, label, year, kind, form, stratum, n, n_nonpositive_pred, fit_r2, poor_monomial, e_<var>…, vector_source, out_of_validity_frac, provenance_confidence` |
| `sigma.csv` | estrato × par de variáveis | `stratum, n, var_i, var_j, cov_log` |
| `pairs.csv` | par × estrato | `a_id, b_id, stratum, n_pair, r_log_predicted, r_log_observed (Pearson nos logs; identidade exata), rho_sp_observed, rho_sp_converted, identity` |
| `redundancy.csv` | método × estrato | `method_id, stratum, rho_sp_max, predecessor_id, predecessor_year, redundant, identity_of` |
| `sigma_transfer.csv` | origem × destino | `sigma_from, observed_in, type, pairs, median_abs_err, p90_abs_err, max_abs_err, frac_within_tol, tol, own_median_abs_err, excess_median, median_abs_err_lo, median_abs_err_hi, excess_lo, excess_hi, boot_B` — erro em Pearson dos logs; `own` = Σ do próprio estrato (0 exato para monômios, pela identidade); `excess` = transferido − próprio, par a par; IC por bootstrap das PESSOAS do estrato observado (`algebra.transfer_B`, semente `seeds.bootstrap`); `frac_within_tol` com tolerância fixa `algebra.transfer_tol` (0,05), independente de n. A fração "dentro do IC de Fisher" e a conversão Σ→Spearman saíram das saídas oficiais (v0.5; legado só no teste de equivalência, §5) |
| `audit.csv` | método × estrato × alvo | `method_id, stratum, target, control, task, metric, estimator, n, B, B_eff, B_dropped, score_cv_target, score_cv_control, score_oob_target_mean, score_oob_control_mean, disc_mean, disc_lo, disc_hi, p_disc, verdict` (condicional, v0.5), `verdict_marginal, score_oob_control_to_target, score_oob_idx_control_to_target, score_oob_target_to_control, score_oob_idx_target_to_control, s1_mean, s1_lo, s1_hi, p_s1, s2_mean, s2_lo, s2_hi, p_s2` |
| `utility.csv` | método × estrato × alvo | `…, covariates, score_base, score_with, delta_mean, delta_lo, delta_hi, p_delta, margin, useful` |
| `combinations.csv` | par ordenado × estrato × alvo | `host_id, added_id, r_log_predicted, score_host, score_pair, gain_mean, gain_lo, gain_hi, p_gain` |
| `sensitivity.csv` | como `audit.csv` | + `estimator_primary, verdict_primary, verdict_changed, s1_primary, s1_delta, s2_primary, s2_delta, disc_primary, disc_delta` |
| `threshold_sensitivity.csv` | método × estrato × alvo × margem × P | `verdict, verdict_default, changed` (reclassificação, sem reajuste) |
| `screening.csv` | método × estrato | `method_id, stratum, redundant, specific, useful, identity, class`; `class` = {original\|redundant}-{specific\|tracks-control\|both\|no-signal}-{useful\|notuseful}, `identity`, ou `inconclusive` SÓ quando a auditoria não deu veredito (15/09: BOTH e NEITHER são conclusivos, antes caíam em inconclusive) |
| `implicit_vectors.csv` (v0.6) | estrato × papel × nome | `stratum, role (target/control), name, n, fit_r2, poor_projection, e_<var>…` |
| `geometry.csv` (v0.6) | método × estrato × alvo | `method_id, stratum, target, control, n, vector_source, cos_target, cos_control, cos_target_control, r_log_target_observed, r_log_target_identity, r_log_target_gap, r_log_control_observed, r_log_control_identity, r_log_control_gap, fit_r2_target, fit_r2_control, poor_projection, flag_parallel_to_control, flag_coupled_target_control, thresholds` |

**Verificação primária da álgebra = Pearson nos logaritmos**, previsto × observado: identidade
algébrica, sem suposição distribucional (nos logs, um monômio é combinação linear exata; a linearidade está garantida por
construção). **Redundância = Spearman observado** (de postos, invariante a transformações monótonas; não exige
linearidade). A conversão Σ→Spearman por (6/π)·asin(ρ/2) exige normalidade bivariada dos logs, rejeitada no NHANES
(Stage P), e **não aparece em nenhuma saída oficial** desde v0.5.

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

### 4.6 Relatório (`report.html`, v0.8 — plano aprovado em 14/09/2026; v0.9 — estrutura e referências, 15/09/2026)
- **É a saída principal.** Um único arquivo, autocontido (figuras e tabelas embutidas), abre do disco sem servidor. Terminal:
  a última linha do `run` é o caminho do relatório e como abri-lo. Notebook: `run()` mostra o relatório inline.
- **Seções, nesta ordem:** cabeçalho (título, preset, aviso se `quick`); resumo; para cada bloco de resultado — entrada e amostra,
  redundância e precedência, especificidade (controle condicional), utilidade, geometria alvo↔controle, transferência de Σ,
  sensibilidade, triagem — três parágrafos fixos **como foi calculado · como ler · rigor aplicado**, cujos números (folds,
  repetições, B, margens, limiares, sementes, estimador) vêm da configuração resolvida e do manifesto, nunca de texto fixo;
  figuras com legenda; tabelas com botões **CSV** (embutido em base64, funciona offline) e **Excel** (arquivo `tables.xlsx`
  ao lado, uma aba por tabela, gerado só se `openpyxl` estiver instalado — extra `bioms-zaku[excel]`; sem ele, aviso e CSV);
  seção **Rigor desta execução** (preset, sementes, versões, hash da entrada, hash de cada saída, tempo, avisos, declaração
  de independência); manifesto.
- **O relatório não recalcula nada:** lê tabelas, manifesto e configuração. Uma fonte de verdade. Consequência: `bioms-zaku --lang xx
  render <pasta>` (ou `render(pasta, lang)` na API) regrava resumo, figuras e relatório de uma execução concluída em outro idioma,
  sem tocar tabelas nem manifesto (teste: hashes das tabelas inalterados). Os AVISOS gravados no manifesto são registro do
  momento da execução e ficam no idioma daquela execução, também dentro de um relatório re-renderizado.
- **Determinismo:** `report.html` carrega data/hora e NÃO entra em `outputs_sha256`; os CSV embutidos são byte a byte os
  arquivos hasheados (teste). Fora: gráficos interativos, filtros, troca de idioma dentro da página (o `render` resolve o idioma).
- **Estrutura (v0.9, 15/09/2026).** Oito seções numeradas, nesta ordem, com índice fixo no topo: 1 Sobre (texto, citação, atribuição do
  nome, e o **diagrama Zaku** — SVG fixo do método em quatro colunas: variáveis medidas → decomposição (vetores de exemplo exatos
  H²/R, Xc/H, R/H; Σ esquemática; identidade r = aᵀΣb/√(aᵀΣa·bᵀΣb)) → auditoria fora da amostra → vereditos; gravado também em
  `figures/zaku_method.svg`, no idioma da execução); 2 Números-chave (pessoas, estratos, métodos e curados, vereditos do alvo
  primário como selos coloridos, valor acrescentado k de n, acoplamento alvo↔controle por estrato — todos lidos das tabelas, testado);
  3 Resumo em texto (`summary.md`, dobrado); 4 Figuras, agrupadas por família (ficha de vereditos aberta; as outras fechadas; uma
  aberta por vez; título humano traduzido, legenda uma vez por família, clique amplia); 5 Resultados, um bloco dobrável por
  bloco de resultado, **um aberto por vez** (`<details name>` nativo, sem biblioteca), com o texto de método e as tabelas
  (numéricos alinhados à direita; no máximo 1000 linhas mostradas, o CSV embutido é sempre completo); 6 Rigor; 7 Referências;
  8 Manifesto. Cores dos vereditos idênticas às figuras. Impressão abre todas as seções (folha de impressão + `beforeprint`).
  Nenhum recurso externo: CSS, JS e imagens embutidos.
- **Referências (v0.9).** Seção fixa, em três partes: (a) métodos de bioimpedância avaliados NESTA execução, uma linha por fonte
  (entradas do catálogo agrupadas por DOI; ano e autores do catálogo, título e periódico do registro verificado); (b) métodos
  estatísticos e algébricos, lista fixa etiquetada com o bloco a que dá suporte — Kronmal 1993 (índices que compartilham componentes se correlacionam por construção; só no bloco de redundância) e Atchley 1976 (a correlação induzida cresce com a variabilidade da variável compartilhada, a diagonal de Σ; dividir por tamanho não remove o tamanho, razão de a utilidade ser medida sobre as covariáveis; blocos de redundância e utilidade),
  Nevill & Holder 1995 (o ajuste log-linear dos expoentes é o modelo alométrico que fornece o padrão por razão apropriado ao alvo; blocos de desenho e redundância), Heymsfield 2007 (massa magra e gordura escalam com a altura com potências ≈ 2, logo alvos massa/altura² são independentes da estatura; a potência é derivada na população, princípio de Benn; blocos de desenho e utilidade), Spearman 1904 (correlação de postos: invariante a transformações monótonas, insensível a extremos; atenuação por erro de medida como sustentação do 0,95), Lipsitch 2010 (desfecho de controle negativo: compartilha com o alvo as fontes de associação espúria e é analisado pelo mesmo procedimento; por analogia — a forma condicional e recíproca S1/S2 e a regra quantitativa são extensão desta ferramenta), Hoerl &
  Kennard 1970 (ridge sobre preditores padronizados, forma de correlação; α = 1 fixo e igual para todos os índices, não ajustado por desenho — os autores afirmam não haver escolha automática de k; age só quando índice e controle são quase colineares), Stone 1974 (avaliação cruzada, aqui em K partes, de uma prescrição fixa: nada é escolhido pelos dados na auditoria, logo sem validação aninhada; a escolha dos expoentes desenhados é feita em partição nunca usada na avaliação), Bengio & Grandvalet 2004 (erros das K partes são dependentes; sem estimador não viesado da variância; por que a dispersão entre dobras nunca entra na inferência),
  Efron 1979 (princípio do bootstrap: reamostrar pessoas da distribuição empírica, Monte Carlo com B réplicas; não estabelece o intervalo percentil nem a pontuação fora da bolsa — resumos por percentis são descritivos), Efron 1983 (ε₀: pontuação nas pessoas não sorteadas, fora da bolsa; só em diferenças pareadas, sem .632), Kohavi 1995 (validação cruzada estratificada por classe: menos viés e variância; 10 dobras é para seleção de modelo, que não há; mesmos blocos), Le Cessie & van Houwelingen 1992 (logística com penalidade L2: coeficientes finitos e estáveis com poucos eventos ou preditores correlacionados; intercepto livre; penalidade fixa; escolha por erro de classificação é instável — sem métricas de corte; blocos de especificidade e utilidade), Peduzzi 1996 (abaixo de 10 eventos por variável a logística é viesada e instável; EPV calculado por modelo e marcado, nunca barreira; blocos de especificidade e utilidade), Tjur 2009 (coeficiente de discriminação D; ganhos de classificação em ΔD; blocos de especificidade e utilidade), Pencina 2008 (ΔAUROC insensível; IDI = ΔD; bootstrap para testar; mesmos blocos), Hanley & McNeil 1982 (AUROC = probabilidade de um caso sorteado superar um não caso sorteado = Wilcoxon, sem hipótese distribucional; erro padrão depende das duas classes; comparação pareada nas mesmas pessoas; frase só em classificação; blocos de especificidade e utilidade), Cover 1974 (o melhor par não é o par dos dois melhores, mesmo sem redundância: classes da triagem são por índice, combinações nunca inferidas delas, pares julgados só quando auditados como pares); (c) software executado (NumPy, SciPy, pandas, scikit-learn, Matplotlib).
  Regra: **nenhum DOI entra sem resolver no Crossref**; os registros (`references.py`) foram gerados dos metadados do Crossref em
  15/09/2026, não digitados; entradas listadas como publicadas, sem tradução. Na verificação, dois candidatos foram recusados: o DOI
  10.1097/ede.0b013e3181e4bfd7 (é a errata de Lipsitch 2010; o artigo é 10.1097/ede.0b013e3181d61eeb) e 10.1111/sms.12780 (artigo de
  cintura, não referência geral de alometria). Teste: todo DOI do catálogo tem registro; a errata não entra; as referências do
  relatório são exatamente as dos métodos da execução.

### 4.5 Progresso
CLI e API imprimem, por estrato e método, contagem, tempo decorrido e estimativa de término, desde o
primeiro método.

**Justificativa.** Precisão completa permite equivalência a 1e-9. Pearson nos logs como verificação
primária remove a única suposição da parte algébrica. Só agregados nas saídas é o que permite rodar
em dados que não podem sair (container em parceiros). Figuras das tabelas garantem concordância.

---

## 5. Contrato de REPRODUTIBILIDADE (v0.5.2, 14/09/2026)
- **Determinismo:** mesma entrada + configuração + versões ⇒ mesmos `outputs_sha256`, para qualquer `n_jobs`.
- **Autonomia:** todo critério de qualidade roda a partir do repositório sozinho. Nenhum teste lê arquivo fora dele; nada
  é pulado por "dado ausente". A comunidade roda a suíte inteira em ~2 min e vê o mesmo resultado.
- **Verdades conhecidas (o que substitui qualquer "igual ao piloto"):**
  1. contas à mão do caderno (`caderno/licoes_metodo_bioms_a_mao.md`): Var, Cov, Σ, aᵀΣa, aᵀΣb, ρ, R² fora da amostra,
     bootstrap, controle condicional — tolerância 1e-9;
  2. identidades algébricas exatas em dados aleatórios (Pearson dos logs previsto por Σ = observado, 1e-12; invariâncias
     de escala e potência);
  3. dados sintéticos com resposta construída: índice específico × índice de tamanho, ganho por combinação só com
     informação nova, partição do desenho recupera o vetor gerador;
  4. **exemplo embarcado com parâmetros publicados:** `examples/example_data.csv` é reproduzível byte a byte a partir de
     `examples/example_data_params.json` (o sorteio usa μ e Σ ARREDONDADOS, exatamente os publicados); μ e Σ dos logs
     batem dentro do erro amostral; a Σ publicada prevê a correlação observada entre índices monomiais (< 0,02);
  5. exemplos numéricos das fontes primárias no catálogo (`check_example`), conferidos na carga;
  6. determinismo dos exemplos (hashes iguais em duas execuções, verificado no CI).
- **O motor anterior (scripts de 08–09/09/2026) foi PILOTO.** O artigo é produzido pelo framework; os CSVs do NHANES de
  09/09 não são referência de nada. A equivalência a 1e-9 verificada em 10/09 foi um portão de transição, cumprido e
  retirado em 14/09 (v0.5.2), junto com a função legada `sigma_transfer_table_legacy` e o marcador `slow`.
- Presets: `quick` (5×5, B 200) para desenvolvimento e demonstração; `full` (5×50, B 2000) para reportar. No exemplo
  embarcado os dois dão os mesmos 28 vereditos (mediana |ΔS1| 0,0005).

**Justificativa.** Um critério que só roda numa máquina não é critério científico: ninguém pode contestá-lo. Verdades
conhecidas (conta à mão, identidade, parâmetro publicado) são contestáveis por qualquer leitor com lápis. Simples e
rápido é condição para outros pesquisadores usarem e aprimorarem.

---

## 6. Changelog
- **v1.1.0-rc1 (16/09/2026)** — §3.6 pressupostos declarados e limiares com origem: intervalo bootstrap nos pares (Fisher removido),
  auditoria na escala logarítmica com a escala bruta em sensibilidade, nível de família 1 − 0,05/k reportado, regra de valores
  faltantes declarada, intervalos bootstrap dos expoentes desenhados, seção "Pressupostos e limiares" no relatório (4 línguas),
  três registros verificados no Crossref para as âncoras (Lafontant 2026, Yang 2023, Cohen 1988). Efron 1983 acrescentado em 16/09/2026 após leitura do original (auditoria de citações). Testes de propriedade
  (cobertura, escala, k = 1, determinismo). Classificação: revisão própria pendente.
- **v1.0.0-rc1 (15/09/2026)** — §3.5 caminho guiado `start` (PLANO_v1.0_fluxo.md): cinco telas, navegação (`<`, `?`, resumo,
  corrigir linha), sugestões sem veredito antes do aceite, aceitar/editar/não, índice próprio, rodada final nas linhas nunca vistas;
  YAML gravado por tela e reprodutível com `run`; `--map --yes`; Ctrl+C 130. `init` deixa de perguntar `design`. Rigor acrescentado
  pela simulação de usuário: auditoria nunca pula método em silêncio; `check` bloqueia desenho com partição de auditoria < `min_n`
  por estrato; `propose` recusa fórmula sem valor auditável, constante, id de catálogo, e avisa repetição de método publicado;
  segunda sessão sobre o mesmo arquivo reaproveita respostas e pergunta antes de descartar índices próprios; resposta inválida
  em sim/não é repetida. Estágio de desenho compartilhado (`design_all`). Guia de 10 minutos em português.
- **v0.9.0 (15/09/2026)** — §4.6 estrutura do relatório: índice fixo, oito seções numeradas, números-chave, figuras por família e
  blocos de resultado como sanfona (um aberto por vez), diagrama Zaku do método (SVG fixo, 4 línguas, também em `figures/`),
  seção de Referências com registros verificados no Crossref (métodos da execução + métodos estatísticos + software), tabelas com
  numéricos alinhados, impressão e ampliação de figuras sem recurso externo.
  Boas-vindas no terminal (`banner.py`): só em `bioms-zaku` sem comando, `--version` e no início do `init` interativo; nunca em
  `run`/`check`/`render`/`init --map`; cor só em terminal (NO_COLOR, TERM=dumb respeitados). Teste.
  Garantia de margens do diagrama: todo texto declara a caixa que o contém; estimativa conservadora de largura reduz a fonte e
  prende `textLength` quando preciso (teste unitário) e `tools/audit_diagram.py` mede cada texto no Chrome em 4 línguas × 8 fontes.
  Cabeçalho do relatório em cinza-claro, logo centralizada, nome em degradê, título "Dados: <nome>" e "Pesquisador: <nome>";
  `check` termina com o comando `run` pronto para colar. Identidade do estudo (`study.data_name`, `study.researcher`): perguntada
  no `init`, gravada no YAML (portanto no SHA-256 da configuração) e no manifesto; muda o hash da configuração, nunca as tabelas.
- **Índices propostos (v0.9, aprovado em 15/09/2026).** Entrada de `user_entries` com `provenance.formula_source: proposed`: o índice
  do próprio pesquisador. Dispensa DOI, ano, validade e frequência (padrões explícitos: ano corrente, 50 kHz, validade nula,
  confiança alta porque a fórmula é o texto do autor, verificador = autor, data = execução); exige `id`, `authors`, `target`, `expr`.
  Nunca curado (erro se `curated: true`); nunca ganha precedência de método publicado, seja qual for o ano (chave de ordenação
  `(proposto, ano, data, DOI)`); marcado ◇ em tabelas (`algebra.proposed`), figuras e legendas, resumo, números-chave e referências
  ("índice proposto pelo pesquisador, não publicado"). Só entra na auditoria quando listado em `catalog.include` (lista pode
  conter `curated` = curados ∪ ids); `check` avisa quando declarado e não incluído. Forma: `monomial` se `vector` for dado
  (verificado exato), senão `composite` (vetor ajustado + R²). Circularidade: `expr` só aceita variáveis mapeadas. Testes.
  Os oito índices BioMS do autor (Mota 2026: 1, 2, 4, 5, 6R, 7, 8, 9; recuperados dos notebooks de junho/agosto) estão em
  `examples/bioms_mota_proposed.yaml` como entradas propostas; BioMS_2 usa `mean(PhA)` (média amostral, registrada). Teste.
  Comando `bioms-zaku propose <yaml>` (§3, v0.9): acrescenta índices próprios pergunta a pergunta; cada fórmula passa pela mesma
  validação do catálogo e é avaliada nos dados do YAML antes de ser aceita (contagem de finitos/positivos, mín/mediana/máx,
  estatísticas amostrais usadas); id inválido ou repetido e fórmula recusada são pedidos de novo; nada é adivinhado.
  `--lang` na CLI sobrepõe `language` do YAML em `check` e `run` escrevendo-o na configuração (o manifesto registra o idioma usado).
- **Desenho de vários índices e ortogonalidade (v0.9, aprovado em 15/09/2026; ver §2.7).** `design` aceita uma lista de blocos
  `{target, id, orthogonal_to?}`; UMA partição (semente do primeiro bloco, linhas com todos os alvos/controles finitos, estratificada)
  vale para todos os índices desenhados, que são auditados nas mesmas linhas nunca vistas; manifesto `design.indices[id].per_stratum`
  (chaves = rótulos dos estratos) com vetor, R² de desenho, e, se ortogonal, vetor do controle, cos_Σ e R² sem restrição. Marca △ em
  tabelas (`algebra.designed`), figuras, resumo, números-chave e referências; nunca precedência sobre método publicado.
  **Teorema registrado e testado:** o vetor de MQO do alvo, t̂, satisfaz t̂ᵀΣ(ĉ − βt̂) = 0 com β = t̂ᵀΣĉ/t̂ᵀΣt̂ — o melhor preditor do alvo é,
  por construção, condicionalmente não informativo sobre a projeção do controle. Logo o **desenho simples é o índice "limpo"** no
  sentido do controle negativo condicional (S2 ≈ 0 fora da amostra no caso construído, veredito SPECIFIC). `orthogonal_to` impõe
  cos_Σ = 0 **marginal** com uma coluna (forma fechada: a = a_MQO − (ĉᵀΣa_MQO/ĉᵀΣĉ)·ĉ); serve para incômodos (tamanho corporal), e
  condicionado ao alvo esse índice tende a acompanhar a coluna (S2 sobe no caso construído) — o relatório diz isso. O `init`
  pergunta `design: none | target | control | both` e escreve desenhos simples; `orthogonal_to` só por YAML. Com `control` ou
  `both`, o `init` escreve o pareamento nas duas direções (controle vira alvo também): todo método é auditado nos dois sentidos e o
  índice desenhado para o controle é auditado contra o seu próprio alvo; a triagem mantém o primeiro alvo como primário.
- **v0.8.0 (14/09/2026)** — §4.6 relatório como produto: textos de método por bloco (4 línguas, números da configuração),
  botões CSV/Excel, seção de rigor, inline no notebook; logo passa a ir dentro do pacote.
- **v0.7.0 (14/09/2026)** — §3.4 idioma: catálogo único em en/es/pt/it, `--lang` e `language:`; figuras e legendas em italiano.
- **v0.6.1 (14/09/2026)** — simulação de usuário externo no Colab: catálogo passa a ir DENTRO do pacote (instalação por wheel não o
  encontrava); CI instala o wheel (nunca editável) e roda um passo de usuário externo fora do repositório, Python 3.10–3.13; `init`
  mapeia sexo/idade/perímetros (papéis `sex`, `age`, `arm`, `waist`, `calf`; sugeridos, impressos com origem, `none` recusa) e escreve
  `catalog.include: curated` às claras; `check` nomeia cada entrada faltante e como mapear, e diz quantos não curados existem sem rodar.
  Catálogo 1.4.0: campo `curated` + `curation_record` nos 8 lidos. Erro de desenho cometido e revertido no mesmo dia (§3.2).
- **v0.6.0 (14/09/2026, aprovado)** — §3.3 geometria alvo↔controle: vetores implícitos, cossenos sob Σ, identidade
  r_log = cos·√R², bandeiras `PARALLEL_TO_CONTROL` / `COUPLED_TARGET_CONTROL` / `poor_projection`, tabelas
  `implicit_vectors.csv` e `geometry.csv`, marcadores nas figuras; alvos em kg como opção documentada; colunas em kg no
  exemplo (derivadas). Motivação: feedback externo sobre acoplamento definicional (magro + gordo + osso = peso; ambos /H²).
- **v0.5.2 (14/09/2026)** — decisão do Thalles: o motor anterior era PILOTO; o framework não depende de nenhum dado local.
  §5 reescrito em torno de verdades conhecidas; removidos os testes de equivalência com o NHANES local, o teste de migração
  e a fixture do catálogo do piloto, a ferramenta de migração e `sigma_transfer_table_legacy`; marcador `slow` retirado.
  Gerador do exemplo sorteia a partir dos parâmetros ARREDONDADOS (os publicados) e ganha `--from-params`: o CSV
  embarcado é reproduzível byte a byte pelo JSON; três testes de verdade conhecida sobre o exemplo. Preset `article`
  renomeado `full`; exemplos renomeados (`example_data`, `example_quick`, `example_full`, `minimal`).
- **v0.5.1 — verificação quick × full (13/09/2026, exemplo sintético, 7 índices, 2 estratos, 2 alvos):** 28 vereditos
  idênticos; mediana |ΔS1| 0,0005 (máx 0,0015); largura mediana do IC de S1 0,032 (quick) vs 0,033 (full); redundância
  idêntica; utilidade idêntica. Conclusão: `quick` serve para desenvolvimento e demonstração; `full` para reportar, como
  o contrato já dizia; os intervalos de 200 reamostras já são estáveis neste n (8 000).
- **v0.5.1 (13/09/2026)** — modo de sensibilidade **implementado** (antes só declarado): `audit.sensitivity.estimator`
  roda o segundo estimador nas mesmas reamostras e grava `sensitivity.csv` (S1/S2/veredito primário e alternativo,
  deltas; nunca seleciona); `nested_tuning` continua não implementado e gera aviso. Sensibilidade aos limiares
  (`threshold_sensitivity.csv`): reclassificação dos S1/S2 gravados sob a grade `verdict.sensitivity_margins` ×
  `verdict.sensitivity_p` (padrão 0,02/0,03/0,05 × 0,90/0,95/0,99), sem reajuste; o resumo lista os vereditos que
  mudam em algum ponto da grade. Ambas entram em `summary.md`.
- **v0.5.0 (13/09/2026)** — decisões do Thalles: (1) **controle negativo condicional** (§3.2): S1/S2 com o controle e o
  alvo como preditores nas mesmas reamostras; vereditos `SPECIFIC` · `TRACKS_CONTROL` · `BOTH` · `NEITHER`; regra
  marginal preservada em `verdict_marginal`; mapa alvo × controle passa a S2 × S1 com margem; ficha mostra S1 e S2.
  (2) **Transferência de Σ em métrica justa quanto a n** (§4.1): erro próprio × transferido, excesso par a par, IC por
  bootstrap de pessoas, fração dentro de tolerância fixa; fração no IC de Fisher e conversão Σ→Spearman fora das saídas
  oficiais (legado só no teste de equivalência). (3) Amostra de conveniência declarada. (4) Desenho de índices e
  combinações permanecem como capacidades, marcadas experimentais até validação em uso.
- **v0.4.7 (11/09/2026)** — figuras oficiais redefinidas (decisão do Thalles): `lineage` (árvore genealógica: raiz por ano, redundantes pendurados com ρ, cor = veredito, tipo declarado ao lado da raiz), `target_control` (mapa do controle negativo: escore no controle × escore no alvo, diagonal, barra do IC), `exponents` (matriz agrupada por linhagem + tipo declarado/R² + Σ do estrato), `scorecard`. `predicted_observed` passa a suplementar. Paleta padrão = cores da logo (verde específico, violeta controle); `classic` = azul/laranja. Coluna `target_kind` em `algebra.csv`.
- **v0.4.6 (11/09/2026)** — `target_kind` no catálogo e `declarations.target_kinds` na configuração: aviso de orientação
  quando um índice declarado para um tipo (ex.: gordura) é auditado contra alvo de outro tipo (ex.: massa magra); catálogo
  1.2.x com `derivation_sample` separado de `validity` (v1.2.0), PhA/LMI reverificados, Piccoli como componentes BIVA,
  Rsp/Xcsp na escala publicada (Ω·cm, L = 1,1·H).
- **v0.4.5 (11/09/2026)** — catálogo 1.1.0 (curadoria por fonte primária): regra de exatidão do vetor (§2.3; PhA e Z
  proibidos em `vector`; `vector_tol` ≤ 1e-4); PhA (Baumgartner 1988) e LMI (Levi Micheli 2022) passam a `composite`
  com vetor ajustado e R²; entrada `Hoffer1969_H2Z` (H²/|Z| a 100 kHz, fonte primária lida, exemplo numérico da
  Tabela 1) como antecessor de Lukaski 1985; `Z100` nas variáveis extra; `history` no catálogo; teste de migração
  contra fixture congelada.
- **v0.4.4 (10/09/2026)** — experiência do usuário: `bioms-zaku init` (constrói o YAML a partir do CSV; sugere colunas por nome só quando não há ambiguidade e exige confirmação; nunca adivinha em silêncio) e `bioms-zaku check` (valida dados + configuração sem rodar: linhas, estratos, classes, pareamento, colinearidade alvo↔controle, métodos avaliáveis/pulados, viabilidade do bootstrap, partição do desenho, declaração de circularidade; código de saída ≠ 0 bloqueia). Bloco `declarations.targets_independent_of_variables` obrigatório `true` para `design`.
- **v0.4.3 (10/09/2026)** — regra de entrada (§1.3): **o alvo não pode ser calculado a partir de nenhuma variável mapeada** (circularidade). O controle negativo detecta confundimento, não circularidade; a responsabilidade é do pesquisador e a declaração vai no manifesto (`targets_independent_of_variables: true`, campo obrigatório no YAML quando há `design`). Caso que motivou: VO2máx estimado do NHANES é calculado pelo CDC a partir das FC de estágio; a FC de recuperação correlaciona 0,92 com a FC do estágio 2 e produziu um índice "específico" por circularidade; com FC de aquecimento (0,39) o índice volta a "medir o controle".
- **v0.4.2 (10/09/2026)** — decisão: o framework tem **três figuras oficiais** (mapa de expoentes; previsto × observado; quadro de vereditos). Faixas de precedência, transferência de Σ, ganho por combinação e bússola são suplementares, geradas só com `output.supplementary_figures: true`.
- **v0.4.1 (10/09/2026)** — catálogo: campo `status` (`active` | `excluded` com `exclusion_reason` obrigatória; excluído nunca é avaliado e sai em `methods_skipped`); `strata` tem fonte única (topo da configuração; conflito com `columns.strata` → erro); figuras revistas após inspeção (§4.4): quadro de vereditos (`board`, assinatura) substitui quadrante e mapa; mapa de calor de expoentes substitui a bússola acima de 10 métodos; árvore de precedência em faixas por linhagem, sem aleatoriedade; paleta validada (2 cores: azul específico, laranja mede-controle; cinza = desênfase; identidade = forma/rótulo; não curado (§2.1) = marcador vazado / *).
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
