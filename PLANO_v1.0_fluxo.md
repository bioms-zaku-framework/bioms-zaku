# PLANO v1.0 — um fio condutor: padrão, expert, índice próprio

Data: 15/09/2026. Estado: PROPOSTA, aguardando correções do Thalles antes de qualquer código.
Princípio: a pessoa tem dados e roda uma vez. Se quiser mais, o próprio Zaku sugere, ela aceita ou ajusta, e a validação sai pronta.
Nada do que já existe muda de cálculo. Muda o caminho que a pessoa percorre.

## 1. Os três usos, do ponto de vista de quem usa

| uso | o que a pessoa faz | o que recebe |
|---|---|---|
| **padrão** | dados → responde às perguntas → roda | como os índices publicados se comportam nos dados dela (relatório) |
| **expert** | o mesmo, e no fim responde "quero sugestões" | o Zaku desenha índices para o alvo dela, mostra cada um em linguagem simples, ela aceita/ajusta, e o relatório final traz publicados + aceitos, validados em linhas que o desenho nunca viu |
| **índice próprio** | cola a fórmula | o índice entra na mesma validação dos publicados (◇) |

Os três podem ser combinados na mesma sessão, mas cada um funciona sozinho.

## 2. Um comando que conduz: `bioms-zaku start dados.csv`

`init`, `check`, `run`, `propose` e `render` continuam existindo, iguais, para quem já sabe. `start` só encadeia, uma tela por vez,
e **escreve o YAML** a cada etapa: qualquer sessão guiada pode ser repetida sem perguntas com `bioms-zaku run analise.yaml` e dá
as mesmas tabelas byte a byte (teste de reprodução).

### Navegação, válida em toda pergunta
- **`<` volta à pergunta anterior.** A resposta que já tinha sido dada aparece como sugestão entre colchetes; Enter a mantém.
  Pode voltar quantas vezes quiser, até a primeira pergunta. Voltar nunca apaga o que veio depois: as respostas seguintes
  reaparecem como sugestão quando a pessoa avança de novo (só o que ela mudar é substituído).
- **`?` repete a ajuda** da pergunta atual. **Enter** aceita a sugestão. **`none`** recusa uma sugestão de coluna.
- **No fim de cada tela, o resumo do que foi respondido**, numerado, e a pergunta "corrigir alguma linha? (número, ou Enter
  para seguir)". Só depois disso a tela é gravada no YAML.
- Regra de rigor: o YAML guarda só as respostas finais; a sessão inteira (idas e voltas) não é registrada, porque não muda o
  cálculo. Teste: qualquer sequência de idas e voltas que termine nas mesmas respostas escreve o mesmo YAML byte a byte.

### Tela 1 — quem e o quê
idioma · nome dos dados · pesquisador. (Já existe.)

### Tela 2 — as colunas
R, Xc, H, W, alvo, controle, covariáveis, estrato e rótulos, id, sexo/idade/perímetros, declaração de independência. (Já existe;
sugestão entre colchetes, Enter aceita, erro repete a pergunta.) **Sai daqui a pergunta `design`.**

### Tela 3 — rodada padrão (diagnóstico)
`check` automático; se OK, roda. Barra de progresso. No fim: caminho do relatório e o comando para abrir. **Uso padrão termina aqui.**

### Tela 4 — "quer sugestões de índices para o seu alvo?" (expert)
Só se a pessoa disser sim. O Zaku então:
1. separa 70 % das linhas por estrato (partição fixa por semente, hash no manifesto) e ajusta um índice para o alvo e um para o
   controle, por estrato — o desenho simples, que é o índice "limpo" no sentido do controle condicional (teorema §2.7 dos contratos);
2. **imprime cada sugestão** assim, em linguagem simples:
   ```
   sugestão 1 · alvo massa_magra_dxa_kg · mulheres (n=105 no desenho)
     fórmula   R^-0.49 · Xc^+0.11 · H^+1.27 · W^+0.42      R² no desenho 0.94
     leitura   H^1.3·W^0.4/R^0.5: o índice de impedância de Lukaski (H²/R) com R atenuado e um pouco de massa corporal
     vizinho   Lukaski1985_II (ρ 0.90 no desenho) — não repete nenhum publicado
     nome sugerido: Zaku_LM_F
   aceitar? (yes = aceita · edit = mudar nome/arredondar expoentes · no = descartar) [yes]:
   ```
3. o que a pessoa pode ajustar: **nome** e **arredondamento dos expoentes** (ex.: −0,49 → −0,5). Nada mais. Expoente editado à mão
   vira índice **proposto** (◇), não desenhado (△), e é dito na hora;
4. com os aceitos, roda a validação **nas 30 % nunca vistas**: publicados + aceitos + próprios, tudo no mesmo relatório.
   O relatório diz, para cada aceito: específico ou não, útil ou não, repete ou não, e transfere ou não entre estratos.

### Tela 5 — "tem um índice seu para testar?" (índice próprio)
Cola a fórmula (é o `propose`, já existe, com a validação imediata nos dados). Entra na mesma rodada da tela 4, ou numa rodada
padrão se a pessoa não quis sugestões.

### O que sai do caminho principal
`design` como pergunta do `init` (fica só no YAML e no `start`); `orthogonal_to` (YAML, seção "avançado" da documentação, com o
aviso de que não é o caminho para passar no controle); qualquer marca ou termo que só faça sentido para quem leu os contratos.

## 3. Rigor (padrão industrial no que couber)

- **Nenhum número de validação vem de linha usada no desenho.** Teste: hash das tabelas de auditoria independe dos nomes
  aceitos e da ordem de aceitação; trocar `yes` por `no` numa sugestão não muda os números dos outros métodos.
- **Reprodutível sem perguntas.** O YAML escrito pelo `start` rodado com `run` reproduz as tabelas byte a byte (teste). As
  respostas ficam no YAML, o manifesto guarda a partição (hash), as sementes, as versões e o SHA-256 da entrada.
- **Aceitar não é escolher.** A pessoa não vê veredito antes de aceitar: vê fórmula, R² e vizinho, todos calculados só na partição
  de desenho. O veredito só existe depois, nas linhas nunca vistas. (Evita selecionar pelo resultado.)
- **Determinismo e ambiente.** Sementes fixas, threads limitados, `NO_COLOR`/`TERM=dumb` respeitados, saída sem cor fora do
  terminal, código de saída ≠ 0 em erro, mensagens com a ação a tomar, `--yes` para aceitar tudo em scripts/CI.
- **Versionamento.** Semântico. Este plano implementado = `1.0.0-rc1`; contratos v1.0; CHANGELOG; CI em 3.10–3.13 com passo de
  usuário externo (já existe) mais um passo com o `start` roteirizado.
- **Testes novos.** (a) fluxo completo roteirizado nos três usos; (b) reprodução não interativa; (c) independência da validação
  em relação à aceitação; (d) `no` em todas as sugestões = relatório igual ao da rodada padrão; (e) expoente editado vira ◇;
  (f) `--yes`; (g) sem vazamento de inglês nas 4 línguas nas telas novas; (h) navegação: `<` volta e mostra a resposta anterior
  como sugestão, `?` repete a ajuda, "corrigir alguma linha?" refaz só a linha escolhida, e idas e voltas com as mesmas respostas
  finais escrevem o mesmo YAML.

## 4. Documentação que acompanha
- `GUIA_10_MINUTOS.md` em português: a sessão inteira do `start`, copiar e colar, com o que olhar no relatório, para os três usos.
- README: seção "Start here" com o mesmo, em inglês; o resto do README vira "referência".
- Notebook tutorial (Jupyter/Colab) com o mesmo fluxo via API, depois.

## 5. Sequência de trabalho (um passo por vez, com o seu "vai" em cada um)
1. Você corrige este plano. 2. `start` + testes (a)–(g). 3. Guia de 10 minutos. 4. Você roda do zero, três usos. 5. Commit seu:
`1.0.0-rc1`. 6. CrossFit (outro alvo) como primeiro uso real fora do contexto DXA.
