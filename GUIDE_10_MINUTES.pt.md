# BioMS Zaku em dez minutos

[English](GUIDE_10_MINUTES.md) · [Español](GUIDE_10_MINUTES.es.md) · **Português** · [Italiano](GUIDE_10_MINUTES.it.md)

Você tem uma planilha com bioimpedância (R e Xc a 50 kHz), estatura, massa corporal e uma medida de referência, como massa magra
ou massa gorda por DXA. Quer saber como os índices publicados se comportam nos seus dados, e talvez criar os seus. Tudo é feito
no terminal, com um comando que conduz por perguntas. Nada é decidido em silêncio: cada resposta fica gravada num arquivo YAML,
e a mesma análise pode ser repetida sem perguntas.

## 1. Instalar (uma vez)

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang pt
```

A segunda linha mostra o letreiro e os três comandos. Se apareceu, está instalado.

## 2. Preparar a planilha

Um arquivo `.csv` com uma linha por pessoa e colunas numéricas para R, Xc, estatura, massa corporal e a referência. Separador
e decimal são detectados. Nomes de coluna livres; o Zaku sugere o mapeamento e você confirma.

## 3. Rodar

```
bioms-zaku --lang pt start dados.csv
```

Em qualquer pergunta: **Enter** aceita a sugestão entre [colchetes], **`<`** volta à pergunta anterior, **`?`** repete a
ajuda, **`none`** recusa uma coluna sugerida. No fim de cada tela aparece um resumo numerado e "corrigir alguma linha?".

O que ele pergunta, na ordem:

1. **idioma, nome dos dados, pesquisador** — vão para o cabeçalho do relatório e para o registro da execução;
2. **as colunas** — R, Xc, H, W e suas unidades; o **alvo** (o que os índices deveriam prever, medido por método independente);
   o **controle negativo** (o que eles NÃO deveriam prever, por exemplo massa gorda quando o alvo é massa magra); covariáveis
   (massa e estatura, sugeridas); estrato (sexo) e rótulos (`0=F,1=M`); identificador; colunas opcionais de sexo, idade e
   perímetros para os métodos que as usam; e a declaração de que alvo e controle **não foram calculados** a partir de R, Xc, H, W;
3. **rodada padrão** — o `check` confere tudo e o Zaku roda. A última linha diz onde está o relatório e como abrir.

Quem quer só isso, parou aqui. É o **uso padrão**.

4. **"quer sugestões de índices desenhados?"** — se disser `yes`, o Zaku ajusta um índice para o alvo e um para o controle, por
   estrato, usando 70 % das linhas, e mostra cada um: fórmula, R² nessas linhas, o índice publicado mais parecido, um nome
   sugerido. Você responde `yes`, `edit` (mudar o nome, arredondar expoentes) ou `no`. Nenhum veredito aparece antes de você
   decidir, de propósito. Expoente mexido à mão vira índice **proposto** (◇), não desenhado (△).
5. **"tem um índice seu para testar?"** — cole a fórmula em R, Xc, H, W (`H_m` estatura em metros, `PhA` ângulo de fase em
   graus, `mean(PhA)` média amostral). Ela é conferida na hora nos seus dados: quantos valores finitos e positivos, mínimo,
   mediana, máximo; se for constante, sem valor auditável ou igual a um método publicado, você fica sabendo antes de aceitar.
6. **rodada final** — só se algo foi aceito ou proposto: publicados + aceitos + seus, validados nos 30 % de linhas que o desenho
   nunca viu.

## 4. Ler o relatório

Abra o `report.html` no navegador (o comando está na última linha do terminal). Ordem de leitura:

- **Números-chave**: pessoas auditadas, métodos, vereditos como selos coloridos, quantos acrescentam valor, se alvo e controle
  estão acoplados nos seus dados.
- **Ficha de vereditos** (uma por estrato): cada método em três colunas — original ou repete um método anterior; específico,
  acompanha o controle, mede os dois ou sem sinal; acrescenta valor além de massa e estatura ou não. ◇ = seu; △ = desenhado.
- **Pressupostos e limiares**: cada procedimento com o pressuposto que carrega e o estado nesta execução; cada limiar com valor,
  origem e sustentação. É onde um revisor confere que nada foi improvisado.
- **Referências**: as fontes dos métodos avaliados e dos métodos estatísticos, com DOI.

Regras de leitura que valem sempre: cada número descreve **esta** amostra; um índice "repete" outro só nesta amostra e para este
alvo; "útil" quer dizer que passou de massa e estatura sozinhas.

## 5. Repetir, trocar idioma, outra base

```
bioms-zaku run dados.zaku.yaml              # a mesma análise, sem perguntas, tabelas byte a byte iguais
bioms-zaku --lang en render zaku_out/dados  # o mesmo relatório em outro idioma, sem recalcular
bioms-zaku propose outra.zaku.yaml          # digitar um índice (por exemplo, um vetor desenhado aqui) para validar em outra base
```

Para validar um índice desenhado em outra base, copie o vetor que aparece no resumo (por exemplo `R −0.49, Xc +0.11, H +1.27,
W +0.42`) e digite-o no `propose` como `R**(-0.49) * Xc**(0.11) * H**(1.27) * W**(0.42)`.

## 6. Quando algo dá errado

- **"não está no arquivo"**: nome de coluna com erro de digitação; a pergunta se repete com a lista.
- **"o controle é o próprio alvo"**: controle e alvo têm de ser medidas diferentes.
- **"deixaria ≈ N linhas para auditar, abaixo de data.min_n"**: poucas pessoas por estrato para desenhar índices; use mais
  linhas ou rode sem estrato. A rodada padrão não é afetada.
- **"faltam as entradas [...]"**: um método do catálogo precisa de uma coluna que você não tem (por exemplo |Z| a 100 kHz);
  ele é pulado e o relatório diz.
- **Ctrl+C** encerra sem escrever mais nada.

## 7. Três casos reais, e o que cada um ensinou (15/09/2026)

- **Amostra NHANES, 300 pessoas, alvo massa magra por DXA.** Lukaski e R/H específicos nos dois sexos; Rsp e Xcsp acompanham o
  controle (são de gordura, e o relatório diz). Lição: para **desenhar** índices por sexo é preciso uns 185 pessoas por estrato;
  com menos, o `start` bloqueia as sugestões antes de mostrá-las, porque a auditoria não teria bootstrap válido.
- **CrossFit, 107 homens, alvo gordura por dobras, controle perímetro do braço corrigido.** Rsp foi o único específico para gordura,
  exatamente o que seus autores desenharam. Os índices desenhados no NHANES para gordura viraram "mede os dois" em atletas: onde a
  massa extra é músculo, um índice quase igual a W²/H² lê músculo. Lição: transferência entre populações se lê pela geometria
  (cosseno com o controle) antes de qualquer veredito.
- **Atletismo, 61 atletas, alvo altura do salto, controle tempo de sprint.** Tudo "sem sinal", e o motivo apareceu num número: o
  cosseno entre alvo e controle foi −0,98. Salto e sprint são a mesma direção no espaço da BIA. Lição: o controle negativo precisa
  ser um construto **diferente** do alvo; outra medida de desempenho não serve. O ângulo de fase foi o que mais acrescentou sobre
  massa e estatura (+0,38), com intervalo largo.

## Dados de exemplo e resultados que nunca se sobrescrevem

O Zaku traz **uma** base de exemplo, sintética, que serve para tudo:

```bash
bioms-zaku examples --copy     # copia para ./zaku_exemplos (se já existir: zaku_exemplos_2, …)
cd zaku_exemplos
```

`zaku_exemplo.csv`: 400 pessoas (200 por sexo), sorteadas a partir das médias e covariâncias do NHANES estimadas separadamente
para cada combinação de sexo e diabetes; nenhuma pessoa real. O que dá para testar com ela:

| teste | alvo | controle | resposta esperada |
|---|---|---|---|
| regressão | `LMI_DXA` | `FMI_DXA` | índices de massa magra carregam o alvo |
| classificação com gabarito | `label_synthetic` | `FMI_DXA` | **nenhum** índice específico: o rótulo depende só de FMI e idade |
| diabetes | `diabetes` | `FMI_DXA` ou `LMI_DXA` | pergunta aberta, como num estudo real |

Use `-o` para dar nome a cada teste (`bioms-zaku start zaku_exemplo.csv -o regressao.yaml`). As massas em kg (`lean_kg`,
`fat_kg`) são calculadas a partir da altura: não as use como alvo com a altura mapeada. Arquivos técnicos (exemplo antigo de
8000 linhas, formato planilha, amostra real do NHANES): `bioms-zaku examples --all`.

Cada execução grava em `zaku_out/<nome>`; se a pasta já tem uma execução concluída, a nova vai para `<nome>_2`, `<nome>_3`, …
No `start`, a rodada padrão e a rodada final (com os índices aceitos) ficam em pastas separadas. Nada é sobrescrito.

## Quantas pessoas eu preciso?

O Zaku descreve a sua amostra e avisa quando a régua fica curta; não estima população. Os mínimos são operacionais, e o relatório
diz, em cada caso, o que foi possível calcular.

| o que você quer | mínimo | por quê |
|---|---|---|
| rodada padrão, alvo contínuo (ex.: massa magra do DXA) | 30 pessoas por estrato | um ridge com um preditor e reamostras com ≥ 20 pessoas fora da bolsa |
| classificação (ex.: diabetes sim/não) | 20 pessoas na classe menor, por estrato | abaixo disso o bootstrap não tem reamostra válida; entre 20 e ~32 o relatório marca *eventos por variável < 10* e o veredito é exploratório |
| sugestões de índices (desenho) | ≈ 185 pessoas por estrato | 70 % vão para o desenho; os 30 % restantes precisam manter ≥ 20 fora da bolsa |
| estratos (ex.: por sexo) | cada estrato cumpre os mínimos acima | senão o Zaku audita sem estrato ou avisa |
| medidas repetidas da mesma pessoa (pré/pós) | **uma linha por pessoa** | agregue antes (média, ou uma visita); o Zaku recusa `id` repetido nesta versão |

Com poucos dados, prefira: sem estrato, sem sugestões, alvo contínuo. Os vereditos saem com intervalos largos, e o relatório
diz isso; é informação, não defeito.

## Classificação com poucos casos e um segundo classificador

O estimador principal da classificação é a regressão logística com penalidade L2: é o mais estável quando há poucos eventos.
O relatório calcula, para cada modelo, os **eventos por variável** de uma reamostra de treino (`epv_train`) e marca abaixo
de 10 (Peduzzi 1996): leia esses vereditos como exploratórios. O mínimo por classe continua 20; o Zaku descreve a sua amostra
e avisa quando a régua fica curta, em vez de recusar.

Se quiser ver se o veredito resiste a um classificador de máquina (boosting), declare-o como **sensibilidade**: roda nas mesmas
reamostras, sai ao lado do principal e nunca é escolhido pelo resultado:

```yaml
audit:
  sensitivity: {estimator: hgb, params: {max_depth: 3, learning_rate: 0.05, max_iter: 300}}
```

`xgboost` também é aceito se estiver instalado. Boosting precisa de mais dados que a logística, não de menos: com poucas
dezenas de eventos, espere ganhos instáveis, e é exatamente isso que a comparação lado a lado mostra.
