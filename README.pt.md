<p align="center"><img src="docs/assets/logo.svg" alt="BioMS Zaku" width="360"></p>

# BioMS Zaku

[English](README.md) · [Español](README.es.md) · **Português** · [Italiano](README.it.md)

Decomposição algébrica e auditoria preditiva de índices e equações preditivas. Demonstrado em bioimpedância.

*zaku* é um verbo da língua juruna (yudjá), família tupi, Xingu, Mato Grosso, Brasil: "ver / cuidar / esperar"
(Lima, S. *A estrutura argumental dos verbos na língua Juruna (Yudjá)*, dissertação de mestrado, USP, 2008, item 290).
O método olha um índice antes de aceitá-lo, cuida da sua validade e espera o resultado fora da amostra.

## O que é isto?

Você tem uma planilha: uma linha por pessoa, com resistência e reatância de um aparelho de bioimpedância,
estatura, massa corporal e uma medida de referência como o DXA. O BioMS Zaku olha os índices que interessam a você e
responde três perguntas sobre cada um. *Ele é novo*, ou já existe com outro nome? *Ele mede o que diz medir*, ou está
seguindo o tamanho corporal — que quase tudo segue? *Ele acrescenta algo* sobre a estatura e a massa corporal sozinhas?

A segunda pergunta é a que importa. "Meu índice correlaciona com massa magra" prova pouco: pessoas maiores têm mais de
tudo. Por isso, antes de ver qualquer resultado, você declara um alvo e um **controle negativo**, e a ferramenta testa
se o índice prediz o alvo *além* do que o controle já prediz. Quando não prediz, ela diz isso com clareza.

Você não precisa saber programar. No terminal, `bioms-zaku start dados.csv` faz as perguntas e anota as suas respostas;
no notebook, você abre e clica em rodar, com os dados de exemplo já dentro. Sai um arquivo único, `report.html`: cada
número, cada figura e, ao lado de cada um, como foi calculado e como ler.

Estado: candidato a lançamento (1.0.0rc1) · Licença: MIT · Citação: `CITATION.cff` · **O que a ferramenta garante, e sob quais pressupostos:** [`CONTRATOS.md`](CONTRATOS.md)

## O que ela faz

1. **Decomposição.** Todo índice ou equação é escrito como produto de potências das variáveis medidas e representado
   pelo seu **vetor de expoentes**. A matriz de covariância Σ das variáveis em logaritmo, numa população, prevê a
   correlação de Pearson dos logs entre dois índices quaisquer *antes de qualquer um deles ser calculado*:
   aᵀΣb / √(aᵀΣa · bᵀΣb), uma identidade válida para qualquer distribuição. A redundância observada é medida pela
   correlação de postos de Spearman (limiar 0,95) e a publicação mais antiga mantém a precedência. Índices que não são
   produtos exatos recebem um vetor ajustado com o R² do ajuste.
2. **Controle negativo condicional.** O pesquisador declara um alvo e um controle negativo. Sobre reamostras
   fora-da-bolsa idênticas, o framework ajusta o controle como preditor do alvo com e sem o índice (ganho S1) e o alvo
   como preditor do controle com e sem o índice (ganho S2). Vereditos: *específico* (S1 presente, S2 ausente), *mede o
   controle* (o inverso), *mede os dois*, *sem sinal*; um ganho está presente quando a média passa de 0,03, o intervalo
   de 95 % exclui 0 e P(d > 0) ≥ 0,95. Mais o **valor acrescentado** sobre covariáveis básicas.
3. **Transferência de Σ.** O Σ de um estrato aplicado a outro, reportado como erro próprio contra erro transferido,
   excesso par a par com bootstrap de pessoas e a fração de pares dentro de uma tolerância fixa (nada disso depende de n).
4. **Desenho (experimental).** Um índice novo é ajustado numa partição de desenho e auditado numa partição disjunta;
   exige a declaração de que o alvo não é calculado a partir das variáveis mapeadas.

As saídas são tabelas agregadas (precisão completa), um manifesto (hashes, versões, sementes), um resumo, quatro figuras
(`lineage` árvore genealógica, `target_control` barras pareadas, `exponents` + Σ, `scorecard`) e um `report.html` de
arquivo único. Dados por linha nunca saem da execução. As figuras aceitam
`figures: {title, subtitle, language: en|es|pt|it, palette, captions}`. Como ler cada figura: `docs/index.html`, seção 3.

## Comece aqui

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang pt start dados.csv        # um caminho guiado: colunas → execução padrão → sugestões (aceitar/editar/não) → o seu índice → relatório
```
`<` volta, `?` repete a ajuda, Enter aceita a sugestão. Tudo o que você responde é gravado em `dados.zaku.yaml`, então
`bioms-zaku run dados.zaku.yaml` repete a análise sem perguntas. Guia de dez minutos: `GUIA_10_MINUTOS.md`.

**No notebook (Colab ou Jupyter)** não há nada a baixar: `pip install bioms-zaku` traz os dados de exemplo dentro do
pacote. `examples/zaku_exemplo.ipynb` instala, carrega os dados e percorre os três usos em cerca de um minuto — a
redundância prevista por Σ antes de qualquer índice ser calculado, a auditoria contra um controle negativo e o
relatório. `bioms-zaku examples --copy` entrega o notebook junto dos dados.

## Instalar

```bash
pip install bioms-zaku            # depois do primeiro lançamento; até lá:
pip install -e ".[plots,dev]"     # a partir de um clone deste repositório
```

Python ≥ 3.10. Dependências: numpy, pandas, scipy, scikit-learn, pyyaml (+ matplotlib para as figuras).

## Dados de exemplo

**Os dados de exemplo** (nada é baixado; viajam com o pacote): UMA base sintética, `zaku_exemplo.csv`, 400 linhas
(200 por sexo), sorteadas de uma log-normal cujas médias e covariâncias foram estimadas no NHANES 1999–2004
separadamente para cada célula sexo × diabetes diagnosticada por médico — de modo que a associação do diabetes com
cada variável é preservada. Ela serve a todos os usos: regressão (`LMI_DXA`, `FMI_DXA`, `ALMI_DXA`), classificação com
resposta conhecida (`label_synthetic` depende só de FMI e idade: com `FMI_DXA` como controle, nenhum índice deveria
acrescentar) e `diabetes` (70 por sexo, enriquecido em casos de propósito). Parâmetros e gerador:
`examples/zaku_exemplo_params.json`, `tools/make_zaku_example.py` (reproduz o CSV byte a byte).

```bash
bioms-zaku examples --copy             # ./zaku_exemplos (uma pasta existente nunca é tocada: _2, _3 …)
cd zaku_exemplos && bioms-zaku start zaku_exemplo.csv -o regressao.yaml
bioms-zaku examples --all              # também os arquivos técnicos (exemplo sintético antigo de 8000 linhas, formato de planilha, uma amostra real do NHANES)
```

```python
from bioms_zaku.api import load_example
df = load_example("zaku_exemplo")
```

`examples/example_data.csv` — 8 000 linhas **sintéticas** (4 000 por sexo). São sorteios de uma log-normal
multivariada cujo vetor de médias e covariância Σ dos logs foram estimados, por sexo, numa **amostra de conveniência**
do NHANES 1999–2004 (adultos de 18 a 49 anos, DXA medido, BIA a 50 kHz; n = 2 792 mulheres, 3 036 homens). Nenhuma
linha real é reproduzida; só μ e Σ saíram da fonte, e estão publicados em `examples/example_data_params.json` (com a
assimetria e a curtose dos logs da fonte, para que a aproximação log-normal possa ser julgada), junto do gerador
`tools/make_example_data.py` e da sua semente. O arquivo traz R, Xc, estatura, massa corporal, idade, três perímetros,
os índices de massa magra/apendicular/gorda por DXA e um rótulo binário sintético declarado. Use-o para aprender o
método, testar a ferramenta e decompor Σ à mão.

```bash
bioms-zaku run examples/example_quick.yaml      # 7 índices curados, preset quick, ~20 s
bioms-zaku run examples/example_full.yaml       # os mesmos dados, preset full (CV 5×50, B = 2000), para reportar
bioms-zaku                                      # boas-vindas: os três comandos, na sua língua (--lang pt)
bioms-zaku propose analise.yaml                 # acrescenta os seus índices, uma pergunta por vez (fórmula conferida nos seus dados)
bioms-zaku run examples/minimal.yaml            # 150 linhas, a menor execução possível
ls zaku_out/example_quick                       # algebra sigma pairs redundancy sigma_transfer audit utility combinations screening sensitivity threshold_sensitivity (.csv) manifest.json summary.md report.html figures/
```

`examples/nhanes_diabetes_400.csv` — 400 linhas **reais** dos arquivos de uso público do NHANES 1999–2004 (CDC,
domínio público): adultos de 18 a 49 anos com DXA medido e BIA a 50 kHz, casos completos, com a resposta do
questionário de diabetes (`diabetes_1Y_0N` = diagnosticada por médico). É uma **amostra de conveniência enriquecida em
casos** — todo diabético diagnosticado com dado completo (139: 79 mulheres, 60 homens) mais um sorteio com semente de
não diabéticos — portanto NÃO é representativa da prevalência; existe para demonstrar a auditoria de classificação
(≥ 20 por classe por sexo) e, com as massas por DXA, a auditoria de regressão em dado real. Procedência, exclusões,
semente e SHA-256: `examples/nhanes_diabetes_400_provenance.json`; gerador: `tools/make_nhanes_example.py`. Os nomes das
colunas são os que o fluxo guiado reconhece (`bioms-zaku start examples/nhanes_diabetes_400.csv`). Este é o único
exemplo com linhas reais; os outros são sintéticos.

As massas em kg são derivadas dos índices e da estatura: não as use como alvo enquanto a estatura estiver mapeada
(circularidade).

**Resultados nunca são sobrescritos.** Uma execução cuja pasta já contém uma execução terminada vai para `nome_2`,
`nome_3`, …; a execução padrão e a final do fluxo guiado caem, portanto, em duas pastas. `output.overwrite: true`
substitui em vez disso, e avisa.

**De quantas pessoas eu preciso?** 30 por estrato para um alvo contínuo; 20 na classe menor para classificação (entre 20
e ~32 o relatório sinaliza *eventos por variável < 10* e o veredito é exploratório); cerca de 185 por estrato para pedir
índices desenhados; uma linha por pessoa (agregue medidas repetidas antes — ids repetidos são recusados nesta versão).

O arquivo também traz `lean_kg`, `alm_kg`, `fat_kg` (índice × estatura², derivados, sem novo sorteio) para que massas
absolutas possam ser usadas como alvo: `bioms-zaku run examples/example_kg.yaml`. Veja *Geometria* abaixo antes de
escolher.

Idioma: `bioms-zaku --lang pt init …` (ou `language: pt` no YAML; o `init` pergunta isso primeiro). en, es, pt, it.
As perguntas, as mensagens de `check`/`run`, o `summary.md`, os títulos do relatório e as figuras seguem o idioma;
nomes de coluna dos CSV e chaves do YAML permanecem em inglês.

Os seus próprios dados — três comandos:

```bash
bioms-zaku init meus_dados.csv          # pergunta qual coluna é R, Xc, H, W, alvo, controle e, opcionalmente, sexo, idade, perímetros de braço/cintura/panturrilha (sugere, nunca adivinha) → meus_dados.zaku.yaml
bioms-zaku check meus_dados.zaku.yaml   # valida dados + configuração SEM rodar: linhas, classes, métodos, bootstrap, circularidade
bioms-zaku run   meus_dados.zaku.yaml   # a análise
```

`init` não interativo: `bioms-zaku init meus_dados.csv --map R=resistencia Xc=reatancia H=estatura W=massa_corporal target=lmi control=fmi independent=yes`,
acrescentando opcionalmente `strata=sexo id=sujeito age=idade arm=braco waist=cintura calf=panturrilha` para que as
equações do catálogo que precisam de sexo, idade ou perímetros possam ser avaliadas; o `check` lista cada método que não
consegue avaliar e de qual coluna precisa. O YAML mapeia colunas para papéis (ver `CONTRATOS.md` §1): `variables`
(R, Xc, H, W na frequência declarada), `units`, `targets`, `controls`, e opcionalmente `covariates`, `strata`, `groups`,
`id` e `declarations.targets_independent_of_variables` (verdadeiro só se nenhum alvo/controle é calculado a partir das
variáveis mapeadas — a regra da circularidade).

```yaml
run_name: meu_estudo
data:
  path: meus_dados.csv
  columns:
    variables: {R: resistencia_ohm, Xc: reatancia_ohm, H: estatura_cm, W: massa_kg}
    units: {H: cm, W: kg}
    targets:  {LMI: indice_massa_magra}
    controls: {FMI: indice_massa_gorda}
    covariates: [massa_kg, estatura_cm]
strata: sexo
preset: full             # CV 5×50, B = 2000 (quick = 5×5, B = 200, só para demonstração)
```

## Regras que o código impõe

- tudo fora da amostra; todo contraste pareado sobre reamostras idênticas; a reamostragem é função determinística de
  (linhas, semente, B, min_oob) — `n_jobs` nunca muda um número;
- sem imputação por padrão (caso completo por método; caso completo na união para contrastes pareados);
- estimador declarado antes dos dados (Ridge / logística para índices isolados; boosting para combinações); nenhuma
  seleção por resultado;
- expressões do catálogo interpretadas por AST com lista branca (sem `eval`); vetores do catálogo validados
  numericamente; exemplos numéricos publicados conferidos no carregamento; métodos com transcrição inválida carregam
  `status: excluded` e nunca são avaliados;
- vereditos são descritivos (o P do bootstrap não é um valor-p); limiares fixados nos contratos;
- as saídas nunca contêm dados por linha (seguro rodar dentro do ambiente de um parceiro).

## Catálogo

Oito índices públicos de bioimpedância, cada um reconferido na sua fonte primária
(`catalogo/fontes_primarias_indices/LEITURAS.md`): H²/|Z| a 100 kHz (Hoffer 1969), índice de impedância H²/R
(Lukaski 1985), ângulo de fase de corpo inteiro (Baumgartner 1988), os componentes da BIVA R/H e Xc/H (Piccoli 1994),
resistividade e reatividade específicas Rsp/Xcsp (Marini 2013; validados no NHANES por Buffa 2013) e o LMI
(Levi Micheli 2022); a razão de impedância Z200/Z5 está listada com confiança baixa (origem comercial, sem artigo de
derivação). Cada entrada registra a amostra de derivação separadamente da validade afirmada pelos autores (fora dela o
framework sinaliza †, nunca bloqueia), o tipo declarado de alvo (`target_kind`: um índice de massa gorda auditado
contra um alvo de massa magra recebe um aviso de orientação) e todo evento de curadoria no `history` do catálogo. O
ângulo de fase e o LMI contêm atan e são portanto `composite`: o vetor de expoentes é ajustado por estrato e o R² do
ajuste é reportado (regra de exatidão, `CONTRATOS.md` §2.3). **Só entradas curadas são auditadas por padrão**
(`catalog.include: curated`, o valor que o `init` grava): as oito cuja fonte primária foi lida criticamente
(`curated: true`, com `curation_record`). As equações preditivas ficam no catálogo sem curadoria e são auditadas apenas
com `catalog.include: all`, marcadas com * em toda saída.

## Testar o seu próprio índice

Uma fórmula sua entra na auditoria ao lado dos métodos publicados como entrada **proposta**: sem DOI, nunca curada,
nunca com precedência sobre um método publicado, marcada ◇ em toda tabela e figura. Qualquer expressão em R, Xc, H, W é
aceita (`+ - * / **`, `log`, `exp`, `sqrt`, `atan`, `max`, as constantes `pi` e `e`, e as estatísticas de amostra
`mean`, `median`, `sd`, cujos valores são registrados por estrato e sinalizados); um produto puro recebe vetor exato,
qualquer outra coisa recebe vetor ajustado com o seu R². Os oito índices BioMS do próprio autor são entregues assim em
`examples/bioms_mota_proposed.yaml`. Ela só é auditada quando listada em `catalog.include`:

```yaml
catalog:
  include: [curated, meu_indice]        # os métodos curados mais o seu; o padrão (curated) nunca audita uma proposta
  user_entries:
    - id: meu_indice
      label: "H²·Xc/R (Mota, proposta 2026)"
      authors: Mota
      target: lean_mass                  # o que ele pretende medir
      expr: "H**2 * Xc / R"
      provenance: {formula_source: proposed, note: "hipótese: a reatância pondera a água intracelular"}
```

Você não precisa editar o YAML à mão: `bioms-zaku propose analise.yaml` pergunta o id, o nome, o que ele mede e a
fórmula, um por vez; cada fórmula é conferida na hora contra a gramática e avaliada nos seus dados (finita, positiva,
mínimo/mediana/máximo, estatísticas de amostra usadas), e depois gravada no YAML e incluída na auditoria.

O relatório então diz se ele repete um índice publicado (redundância), se é específico para o alvo contra o controle,
se acrescenta valor sobre as covariáveis e se está paralelo ao controle. O `bioms-zaku check` avisa quando uma proposta
é declarada mas não incluída.

## Desenhar o seu próprio índice a partir dos dados

O `init` pergunta `design: none | target | control | both`. Para cada um, os expoentes de R, Xc, H, W são ajustados a
ln(alvo) por mínimos quadrados em 70 % das linhas (por estrato) e o índice é auditado nos outros 30 %, nunca vistos,
como qualquer método publicado (marcado △). Uma propriedade registrada e testada faz deste o jeito certo de "limpar o
sinal": o melhor preditor do alvo é, por construção, condicionalmente não informativo sobre a projeção do controle —
então o desenho simples é o índice específico no sentido do controle negativo condicional, e a auditoria verifica se
isso sobreviveu fora da amostra. No YAML, `design:` é uma lista; `orthogonal_to: <coluna>` acrescenta
Σ-ortogonalidade marginal a uma coluna incômoda (tamanho corporal), o que é um objetivo diferente e em geral reprova
no controle condicional (o relatório diz isso).

## Geometria de alvo e controle

Alvo e controle muitas vezes vêm da mesma medida de referência e da mesma normalização (magra/H² e gorda/H² de um
mesmo exame de DXA; magra + gorda + osso = massa corporal, com H e W entre as variáveis mapeadas). No espaço das
variáveis mapeadas eles podem apontar quase na mesma direção, e então um índice próximo dessa direção (do tipo W/H²)
prediz os dois por aritmética. O framework mede isso com a álgebra que já usa: o *vetor implícito* de cada alvo e
controle (OLS dos logs), os cossenos em Σ índice–alvo, índice–controle e alvo–controle, e a identidade exata
r_log = cos_Σ·√R² para índices monomiais. Duas bandeiras com limiares declarados anotam os vereditos e nunca os mudam:
PARALLEL_TO_CONTROL (‡ ao lado do índice) e COUPLED_TARGET_CONTROL (‡ no título do painel). Tabelas
`implicit_vectors.csv` e `geometry.csv`; bloco no `summary.md`. No exemplo entregue, o cosseno alvo–controle é 0,90
(mulheres) e 0,86 (homens) para LMI contra FMI. Usar massas absolutas (kg) remove a estatura dos dois lados e baixa o
acoplamento, mas não remove o acoplamento via massa corporal, e torna o alvo mais "tamanho", o que favorece índices de
volume (H²/R): uma escolha declarada, não uma correção. A lição 12 do caderno faz a coisa inteira à mão com quatro
pessoas.

## O relatório

`report.html` é a saída principal: um arquivo único e autocontido (figuras e tabelas embutidas) que abre do disco. Num
notebook, `run()` mostra o relatório inline. Cada bloco de resultado traz três parágrafos fixos — *como foi calculado ·
como ler · rigor aplicado* — cujos números (folds, repetições, B, margens, limiares, sementes, estimador) vêm da
configuração resolvida, nunca de texto fixo. Toda tabela tem um botão de download em **CSV** (embutido, funciona
offline); `pip install bioms-zaku[excel]` acrescenta `tables.xlsx` (uma aba por tabela) ao lado do relatório. Uma seção
*Rigor desta execução* lista preset, sementes, versões, hash da entrada, o SHA-256 de cada tabela de saída, tempo de
relógio e avisos. O relatório não recalcula nada — e é por isso que
`bioms-zaku --lang en render zaku_out/minha_execucao` regrava resumo, figuras e relatório de uma execução terminada em
outra língua em segundos, deixando tabelas e manifesto intactos.

O relatório abre com um sumário fixo e o **diagrama do método Zaku** (também salvo como `figures/zaku_method.svg`),
mostra números-chave lidos das tabelas, agrupa figuras por família e os blocos de resultado em acordeão (um aberto por
vez), e termina com uma seção de **Referências**: as fontes de bioimpedância dos métodos avaliados na execução, os
antecedentes estatísticos e algébricos (índices de razão, escalonamento alométrico, controles negativos, ridge,
validação cruzada, bootstrap, combinações) etiquetados por bloco de resultado, e o software executado. Todo registro
vem de metadados do Crossref verificados em 15/09/2026 (`references.py`); nada é carregado da rede quando o relatório é
aberto.

## Reprodutibilidade

O `manifest.json` registra a configuração resolvida, as sementes, as versões do pacote e das bibliotecas, o hash da
entrada e o SHA-256 de cada saída. Duas execuções idênticas dão hashes idênticos (conferido por
`python tools/gate.py`, que roda os passos que o fluxo de CI rodava: build, instalação limpa do wheel, a suíte, uma
execução de exemplo repetida e um usuário externo). Toda verificação de qualidade roda a partir do repositório sozinho:
lições calculadas à mão, identidades algébricas exatas, casos sintéticos com resposta construída e o exemplo entregue,
que é reproduzível byte a byte a partir dos seus parâmetros publicados
(`tools/make_example_data.py --from-params`). Nenhum teste depende de dado fora do repositório.

O contrato [`CONTRATOS.md`](CONTRATOS.md) é o documento normativo por trás de tudo isso: o que a ferramenta promete
para entrada, catálogo, configuração, saídas e reprodutibilidade — cinco contratos, cada um fechando com a sua
justificativa. Leia-o para saber o que um número desta ferramenta afirma e o que não afirma.

## Desenvolvimento

```bash
pytest -q                   # suíte inteira, ~2 min, autocontida
python -m build && twine check dist/*
```

Um gancho de pre-commit recusa commits quando a suíte rápida falha.
