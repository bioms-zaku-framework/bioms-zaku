# PLANO v1.1 — pressupostos declarados, escala da auditoria, limiares com origem

Data: 16/09/2026. Estado: PROPOSTA, aguardando correções do Thalles antes de qualquer código.
Escopo: auditoria de **regressão** (alvo contínuo positivo). A classificação (logística, AUROC) tem revisão própria depois.
Meta: um pesquisador de BIA em qualquer lugar usa os padrões sem escolher nada e lê, no relatório, cada pressuposto com o seu
estado e cada limiar com a sua origem. Nada de improviso escondido. A álgebra (Σ, vetores, identidade) não muda.

## 1. Quatro ajustes de pressuposto

| # | procedimento | pressuposto hoje | ajuste | onde aparece |
|---|---|---|---|---|
| A | intervalo da correlação observada (tabela de pares) | transformação de Fisher: normalidade bivariada dos logs, rejeitada no NHANES | intervalo **bootstrap de pessoas** (B = `transfer_B`, o mesmo da transferência de Σ); Fisher sai | `pairs.csv` (`r_lo`, `r_hi`), texto de método do bloco de redundância |
| B | escala da auditoria (ridge) | índice e alvo nas escalas brutas: relação curva vira ganho menor; R² dominado por extremos | **padrão: logs** de índice e alvo (ambos positivos por construção); R² em escala relativa, coerente com a álgebra; a escala bruta entra no bloco de **sensibilidade**, lado a lado, nunca escolhida | `audit.csv` ganha `scale`; `sensitivity_scale.csv`; texto de método; `audit.scale: log \| raw` no YAML |
| C | regra do veredito com k métodos | por método, sem correção: alguns "específicos" por acaso | o relatório diz k e que a regra é por método; **sensibilidade** ganha o intervalo ao nível 1 − 0,05/k (Bonferroni) e o veredito sob ele; nada é escolhido | `threshold_sensitivity.csv` ganha `ci_level`; resumo e relatório |
| D | casos completos | falta ao acaso, não declarada | comparar quem ficou com quem saiu em cada variável mapeada (diferença padronizada de médias); aviso acima de 0,20 DP; **sem imputação** (desenho) | `exclusions.csv` novo; aviso no manifesto; seção Pressupostos |

Consequência de B: todos os vereditos já vistos mudam de escala; as três bases de 15/09 são rodadas de novo e comparadas
(regressão nos logs vs bruta) antes de qualquer número ir para o artigo.

## 2. Intervalos para os expoentes desenhados (melhoramento)
Bootstrap de pessoas na partição de desenho (B = 200): intervalo por expoente em `design.indices[id].per_stratum` e na linha do
resumo. Diz se o vetor é estável ou se dança. Não muda o vetor usado (o ajuste completo da partição).

## 3. Limiares e constantes: uma tabela com origem
Nova seção do relatório, **Pressupostos e limiares**, gerada da execução, e a mesma tabela no contrato (§3.6). Colunas:
valor · origem (convenção estatística / decisão desta ferramenta / derivado da amostra) · sustentação · sensibilidade publicada.
Itens: Spearman 0,95 · margem 0,03 · P 0,95 · nível 95 % · margem da utilidade 0,03 · cos 0,90 / 0,80 · R² 0,50 · tolerância 0,05
· B 2.000 · CV 5×50 · partição 70/30 · n mínimo 30 · fora da bolsa 20 · reamostras válidas 10 % de B (≥ 20) · aviso de faltantes 10 %.
Decisão pendente do Thalles, após leitura das fontes que eu trago: ancorar Spearman 0,95 na repetibilidade teste-reteste da BIA
(ICC de R/PhA) e a margem 0,03 no efeito pequeno de Cohen (f² 0,02), **ou** declarar os dois como convenção desta ferramenta.
Nenhum DOI entra sem resolver no Crossref.

A sensibilidade passa a cobrir também os cortes de geometria (cos 0,90/0,80 → grade 0,85/0,90/0,95 e 0,70/0,80/0,90), reportada.

## 4. Seção "Pressupostos" no relatório
Uma linha por procedimento, com o estado **nesta execução**: atendido por construção · verificado (com o número) · limitação
declarada. Lista: positividade dos logs; identidade Σ (exata para monômios; lacuna máxima para compostos); Spearman (postos);
ajuste log-linear (R² mínimo por estrato); partição de desenho (hash); ridge nos logs (escala); linhas trocáveis (id mapeado ou
não; pesos ignorados — amostra de conveniência, padrões no indivíduo); bootstrap (B válidas por estrato); regra do veredito
(k métodos, sem correção; sensibilidade); geometria (projeção); casos completos (diferenças padronizadas). Quatro línguas.

## 5. Rigor e testes
- A: intervalo bootstrap cobre a correlação verdadeira num caso sintético com Σ conhecida (cobertura ≈ 95 % em 200 repetições).
- B: caso construído com alvo = produto de potências × ruído lognormal — nos logs o ganho é maior e o veredito estável; a escala
  bruta aparece só na sensibilidade; determinismo byte a byte; `render` intacto.
- C: k métodos → nível 1 − 0,05/k na sensibilidade; com k = 1 idêntico ao padrão.
- D: dados com falta dependente do valor → aviso; falta ao acaso → sem aviso.
- Tabela de limiares: todo valor no relatório é o valor da configuração resolvida (teste com valores alterados no YAML).
- Seção Pressupostos: cada item presente nas 4 línguas; estados coerentes com as tabelas.
- Suíte completa; simulação de usuário; as três bases de 15/09 rodadas de novo, com comparação log vs bruta registrada.

## 6. Fora deste plano
Classificação (revisão própria: mínimo por classe, AUROC, margem 0,03, calibração); notebook Jupyter/Colab (próximo ciclo);
imputação (nunca); ajuste fino da penalidade do ridge (contrato: a auditoria mede informação, não capacidade de modelo).

## 7. Sequência (um passo por vez, com o "vai" do Thalles)
1. Correção deste plano. 2. Leitura das fontes para Spearman 0,95 e margem 0,03; decisão. 3. Código A–D + tabela + seção +
testes. 4. Suíte e simulação. 5. Rerodar NHANES 300, CrossFit, atletismo; comparar. 6. Commit seu (`1.1.0-rc1`).
