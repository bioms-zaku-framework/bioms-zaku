# Leituras das fontes primárias dos índices — BioMS Zaku

Uma entrada por artigo, na ordem em que foram lidos. Cada entrada registra o que o artigo
de fato diz (com página), o que isso implica para o catálogo e para o método, e as decisões
tomadas a partir dele.

Este é o registro que o contrato (`CONTRATOS.md` §2.1) exige de toda entrada marcada `curated`:
o campo `curation_record` de cada método do catálogo aponta para a seção correspondente aqui.
Os PDFs lidos **não são redistribuídos**, por direito autoral; cada entrada traz o DOI, e o
registro é verificável contra o artigo original por qualquer leitor que o obtenha.
Escrito em português, a língua em que a leitura foi feita — como todo registro datado deste projeto.

---

## 1. Hoffer EC, Meador CK, Simpson DC (1969). Correlation of whole-body impedance with total body water volume. J Appl Physiol 27(4):531-534. DOI 10.1152/jappl.1969.27.4.531

**Arquivo:** hoffer1969.pdf (4 p., digitalizado, texto OCR).

**O que o artigo faz.**
- Mede impedância de corpo inteiro |Z| a 100 kHz, 100 µA, tetrapolar mão direita–pé esquerdo, supino (p. 531-532). Não separa R e Xc: só o módulo Z = E/I.
- Deriva o índice pela física do condutor: Z = ρL/A → V = ρL²/Z (eq. 1-3, p. 531). Usa a altura T como L. É a origem teórica do expoente +2 na altura e −1 na impedância.
- Amostra: 20 estudantes de medicina homens, saudáveis (Tabela 1, dados individuais: peso, altura, TBW por diluição de trítio, Z), mais 34 pacientes com hidratação anormal (ICC, insuficiência renal, Cushing, obesidade; Tabela 2, dados individuais).
- Tabela 3 (p. 533), correlações com TBW nos 20 normais / 34 pacientes: peso 0,83 / 0,74; Z 0,70 / 0,86; T/Z 0,84 / 0,91; T²/Z 0,92 / 0,93; "massa iônica" vs T²/Z 0,92 / 0,93.
- Equação TBW = A·T²/Z + B ajustada nos 20 normais e aplicada aos 34 pacientes: r 0,92, desvio-padrão do erro 3,89 L (p. 534).
- Reconhece os antecedentes: Thomasset 1962-1965 (agulhas, 1 kHz) e Nyboer 1959.

**Como se enquadra no Zaku.**
- **Precedência.** O monômio H²/Z é de 1969. O catálogo hoje atribui H²/R a Lukaski 1985. Pela regra de precedência do framework, H²/Z (Hoffer 1969) é o antecessor; H²/R a 50 kHz (Lukaski 1985) é a versão em resistência. A 50 kHz, com ângulo de fase típico de 5-8°, Z = R/cos φ difere de R por 0,4-1 %; em log, ln Z = ln R − ln cos φ, quase identidade. Os dois índices são redundantes (ρ ≈ 1) e o framework, se tivesse os dois no catálogo, apontaria Lukaski 1985 como redundante com Hoffer 1969.
- **Vetor teórico vs vetor ajustado.** A física dá o vetor (H: +2, Z: −1). A etapa de desenho do Zaku ajusta expoentes aos dados. Comparar o vetor ajustado no NHANES com o vetor físico (2, −1) é um teste de sanidade do desenho que o artigo de 1969 fornece de graça.
- **Tabela 3 é uma triagem de expoentes feita à mão.** Hoffer compara T⁰/Z, T¹/Z, T²/Z: variou o expoente da altura e escolheu o de maior correlação. É exatamente a operação que o vetor de expoentes formaliza. Não há controle negativo, e "melhora sobre o peso" (0,83 → 0,92) é a versão de 1969 do "valor acrescentado sobre covariáveis".
- **Transferência entre populações.** Ajuste em 20 normais, aplicação em 34 pacientes com hidratação anormal. É o primeiro teste de transferência da literatura BIA; o Zaku o formaliza com Σ por estrato e a tabela de transferência.
- **Frequência.** 100 kHz, não 50 kHz. Qualquer entrada de catálogo para Hoffer precisa registrar `frequency_khz: 100` e variável Z, não R.
- **Dados individuais publicados.** As Tabelas 1 e 2 trazem 54 indivíduos com peso, altura, TBW e Z. Servem como `check_example` numérico do catálogo e como uma lição de cálculo à mão (Σ dos 20 normais em log).

**Decisões pendentes (Thalles).**
1. Criar a entrada `Hoffer1969_H2Z` no catálogo (variável Z a 100 kHz, vetor H +2, Z −1, confiança high, fonte primária conferida) e marcar `Lukaski1985_II` como versão em R do mesmo monômio, ou manter Hoffer só como nota de precedência no rótulo de Lukaski. Observação técnica: Z não é variável mapeada no Zaku; se o usuário só tem R e Xc, Z = √(R² + Xc²) entra como forma composta com R² de ajuste, não como monômio exato.
2. Usar as Tabelas 1-2 como exemplo numérico de verificação da entrada.

**Executado (11/09/2026):** entrada `Hoffer1969_H2Z` criada no catálogo 1.1.0 (Z100 a 100 kHz, vetor H +2 / Z100 −1,
confiança high, exemplo numérico da Tabela 1: 181,6 cm e 427 Ω → 77,233 cm²/Ω). Antes disso foram corrigidas três
fragilidades do esquema: regra de exatidão do vetor (PhA e Z nunca em `vector`; PhA e LMI passam a `composite` com
vetor ajustado e R²), fixture congelada da migração (o catálogo pode evoluir) e variável `Z100` nas convenções.

---

## 2. Lukaski HC, Johnson PE, Bolonchuk WW, Lykken GI (1985). Assessment of fat-free mass using bioelectrical impedance measurements of the human body. Am J Clin Nutr 41(4):810-817. DOI 10.1093/ajcn/41.4.810

**Arquivo:** lukaski1985.pdf (8 p.).

**O que o artigo faz.**
- Amostra: 37 homens aparentemente saudáveis, 19-42 anos, altura 163,1-194,8 cm, massa 51,8-135,4 kg, gordura 7,8-43,0 % (Tabela 1, p. 812). Referências: FFM por hidrodensitometria (Brozek), TBW por diluição de D₂O, TBK por contagem de ⁴⁰K.
- Medida: pletismógrafo de quatro terminais RJL, 800 µA a 50 kHz, tetrapolar mão-pé, supino, ~2 h após refeição; R e Xc medidos separadamente (nota 5, p. 813); Z = √(R² + Xc²) (nota 3, p. 811). Usa o menor R entre quatro configurações de eletrodos (p. 813), lado direito na maioria (dominante).
- Derivação (p. 811): parte de V = ρL²/Z (Nyboer) e assume Xc pequena em relação a R → V = ρL²/R (eq. 4). Justifica empiricamente: r(R, Z) = 0,99 contra r(Xc, Z) = 0,70 (p. 813). É aqui que |Z| de Hoffer vira R.
- Confiabilidade: CV de R em 5 dias 0,9-3,4 % (média 2 %); teste-reteste 0,99; diferença máxima entre colocações de eletrodos 1,5 % (Tabelas 2-3).
- Tabela 4 (p. 814, n = 37), correlações: Ht²/R com FFM 0,98, TBW 0,95, TBK 0,96, massa 0,86, FM 0,49, % gordura −0,22 (n.s.), M/Ht² 0,73. R sozinho: FFM −0,86. Xc: FFM −0,54. M/Ht² (IMC): FFM 0,79, FM 0,89, % gordura 0,65.
- Equações de regressão (Fig. 2, p. 815, x em cm²/Ω): FFM = 3,04 + 0,85·Ht²/R (SEE 2,61 kg, r 0,98); TBW = 2,03 + 0,63·Ht²/R (SEE 2,09 L); TBK = −23,09 + 2,56·Ht²/R (SEE 10,70 g).
- Cita Hoffer 1969 (ref. 13) e Nyboer 1943/1972 como antecedentes; a contribuição declarada é a validação contra três referências, a confiabilidade da medida e o uso de R a 50 kHz.

**Como se enquadra no Zaku.**
- **Precedência confirmada na fonte.** O próprio artigo atribui a relação Z-TBW a Hoffer. O catálogo passa a registrar Lukaski 1985 como versão em R (50 kHz) do monômio de Hoffer (|Z|, 100 kHz).
- **A Tabela 4 é um controle negativo em correlação.** Ht²/R: 0,98 com FFM e 0,49 com FM (−0,22 com % gordura). M/Ht² (IMC): 0,79 com FFM e 0,89 com FM. Em 1985 os dados já mostravam que Ht²/R é específico para massa livre de gordura e que o IMC acompanha a gordura. O Zaku transforma essa leitura de tabela num veredito preditivo, fora da amostra, com intervalo.
- **Vetor exato.** Ht²/R é monômio exato (H +2, R −1); a decisão de trocar Z por R é explicitamente uma aproximação (Xc << R), e o framework agora trata Z como não-monômio, coerente com o que o artigo assume.
- **Correlações de Σ publicadas.** r(R, Z) = 0,99, r(Xc, Z) = 0,70, r(R, Xc) = 0,71, r(altura, massa) = 0,63: fragmentos de uma matriz de covariância dos logs para homens saudáveis, úteis como comparação externa da Σ do NHANES masculino.
- **Limites de validade.** Só homens, 19-42 anos, saudáveis. O próprio artigo pede validação em composições anormais (renais, oncológicos) e em treinamento físico. Aplicar a mulheres ou a 8-18 anos é fora da validade declarada (flag †).
- **Sem exemplo numérico individual.** Não há tabela de indivíduos. Média de altura (180,7 cm) e de menor R (443,0 Ω) dão 73,70 cm²/Ω, dentro da faixa da Fig. 2 (≈55-110), registrado como `consistency_note`, não como `check_example`.

**Executado (11/09/2026):** `Lukaski1985_II` reverificado na fonte primária: procedência pdf_text/high (o asterisco sai do scorecard), validade (homens, 19-42), aparelho, métodos de referência, n = 37, antecedentes; catálogo 1.1.1.

**Pendente (decisão do Thalles).** As três equações da Fig. 2 são equações preditivas (kind `equation`) e ficam para a etapa das equações.

---

**Correção de esquema (11/09/2026, decisão do Thalles).** O catálogo passa a separar `derivation_sample` (quem foi usado
para ajustar; descritivo, nunca gera flag) de `validity` (aplicabilidade afirmada ou testada pelo autor; fora dela o
framework marca † e nunca bloqueia). Hoffer 1969: derivação em 20 homens saudáveis de 21-38 anos, mas testado e proposto
para pacientes de ambos os sexos, 18-77 anos, com hidratação anormal → validade corrigida para ambos os sexos, 18-77.
Lukaski 1985: derivação e validade coincidem (homens saudáveis 19-42; os autores dizem que a validade em mulheres e em
composições anormais não está estabelecida). Catálogo 1.2.0. Daqui em diante cada leitura registra as duas informações.

---

## 3. Baumgartner RN, Chumlea WC, Roche AF (1988). Bioelectric impedance phase angle and body composition. Am J Clin Nutr 48(1):16-23. DOI 10.1093/ajcn/48.1.16

**Arquivo:** baumgartner1988.pdf (8 p.).

**O que o artigo faz.**
- Amostra de derivação: 53 homens (9-62 anos) e 69 mulheres (9-58 anos), brancos, Ohio, não selecionados por composição corporal; 48 menores de 18 anos; gordura de < 5 % a > 50 % (Tabela 1, p. 18). Referência: hidrodensitometria (Siri, com correções de densidade da massa livre de gordura para < 25 anos) e dobras cutâneas.
- Medida: RJL BIA 101, 800 µA a 50 kHz, lado direito, jejum de 12 h, supino; corpo inteiro **e** segmentos (braço, perna, tronco), com posições de eletrodo descritas (p. 17).
- Definição (eq. 3, p. 18): φ = atan(Xc/R) em radianos, × 57,297 para graus. Também calcula S²/R como índice de FFM, W/S² como índice de adiposidade total e a média dos logs de três dobras (MSK).
- Resultados (Tabela 7, p. 20, correlações ajustadas por idade, corpo inteiro): φ com % gordura −0,34 nos homens e −0,46 nas mulheres; com FFM +0,50 nos homens e não significativa nas mulheres; com S²/R +0,52 nos homens. S²/R com FFM 0,89-0,91; W/S² com % gordura 0,42 (H) e 0,67 (M).
- Regressão de % gordura (Tabela 8): idade + dobras + W/S² + **φ do tronco**; o ângulo de fase do tronco acrescenta R² 0,10 (H) e 0,15 (M). Sexo + idade + φ do tronco explicam 55,8 % da variância; com φ de corpo inteiro só 31,5 %. Ângulos de fase não acrescentam nada à predição de FFM depois de idade e S²/R (p. 20).
- Tabela 5: r(R, Xc) de corpo inteiro varia por grupo: meninos 0,76, meninas 0,56, homens 0,38, mulheres 0,71.
- Fig. 3: gráfico Xc × R do tronco com retas por grupo de gordura, precursor gráfico da BIVA.
- Antecedentes citados: Brazier 1935 e Barnett 1936-1937 (ângulo de impedância para função tireoidiana), Hoffer 1970, Lukaski 1985.

**Como se enquadra no Zaku.**
- **O índice do artigo é o ângulo de fase do tronco, não o de corpo inteiro.** O catálogo avalia o de corpo inteiro (medida segmentar está fora do escopo do framework). O rótulo passa a "PhA whole body (Baumgartner 1988)" e a nota registra que os autores reportam o de corpo inteiro como preditor mais fraco. Um revisor da área cobraria exatamente isso.
- **Não é monômio.** atan não é produto de potências; a decisão de hoje (vetor ajustado com R²) é coerente com a definição publicada. A equivalência de posto com Xc/R é anotada.
- **Leitura de controle negativo já presente.** S²/R: forte com FFM, fraco ou nulo com % gordura. φ de corpo inteiro: fraco com os dois nos homens, só com gordura nas mulheres. É o mesmo padrão que o NHANES mostrou no Zaku (PhA específico mas com pouco valor acrescentado).
- **Σ condicional ao estrato, com números de 1988.** r(R, Xc) vai de 0,38 (homens) a 0,76 (meninos). Explica por que o framework exige Σ por estrato e por que a transferência entre sexos falhou no NHANES.
- **Precedência.** O ângulo de fase como medida fisiológica é dos anos 1930; Baumgartner 1988 é o primeiro uso para composição corporal. A regra de precedência do catálogo é relativa ao catálogo, e a nota registra os antecedentes.
- **Validade declarada:** ambos os sexos, 9-62 anos, brancos, toda a faixa de adiposidade. Derivação e validade coincidem.
- **Sem exemplo numérico individual;** só médias de φ por grupo (Tabela 2). Registrado como `consistency_note`.

**Executado (11/09/2026):** `Baumgartner1988_PhA` reverificado: rótulo, procedência pdf_text/high, amostra de derivação, validade, aparelho, referência, precedência e a ressalva do tronco; catálogo 1.2.1.

**Pendente (decisão do Thalles).** A equação de % gordura da Tabela 8 usa o ângulo de fase do tronco (segmentar) e não entra no escopo atual.

**Decisão do Thalles (11/09/2026) sobre Lukaski 1985 e Baumgartner 1988:** os cinco e os seis pontos propostos foram aprovados; as edições já feitas no catálogo ficam como estão (1.2.0 e 1.2.1).

---

## 4. Piccoli A, Rossi B, Pillon L, Bucciante G (1994). A new method for monitoring body fluid variation by bioimpedance analysis: the RXc graph. Kidney Int 46(2):534-539. DOI 10.1038/ki.1994.305

**Arquivo:** piccoli1994.pdf (6 p., nota técnica).

**O que o artigo faz.**
- Objetivo: monitorar variação de fluidos no paciente individual sem suposições sobre composição corporal e sem estimar volumes em litros. Método de hidratação, não índice de composição corporal.
- Amostra: 217 adultos caucasianos (Pádua): 86 controles saudáveis (38 H, 48 M, 16-66 anos), 55 com insuficiência renal crônica, 36 com síndrome nefrótica, 40 obesos (IMC > 31); 16-75 anos.
- Medida: RJL/Akern BIA-109, 800 µA a 50 kHz, tetrapolar mão-pé direitos; CV 1 % no dia, 3 % semanal, 2 % entre operadores.
- Definição: R/H e Xc/H em Ω/m (altura em metros). Tratamento bivariado: elipses de confiança 95 % (médias de grupos) e de tolerância 75 %/95 % (indivíduos), sob normalidade bivariada. Direção = ângulo de fase; comprimento = hidratação.
- Sem método de referência de composição corporal; validação clínica (edema, grupo). Polo inferior da elipse de 75 % identifica 28/29 renais com edema.
- Tabela 1: saudáveis, homens R/H 292,6 e Xc/H 30,2 Ω/m; mulheres 374,3 e 36,6. Tabela 2: r(R/H, Xc/H) saudáveis 0,48 (H 0,32, M 0,33), renais 0,56, nefróticos 0,67, obesos 0,71. Sem correlação com idade nos saudáveis.
- Advertência explícita (p. 537): pela correlação mútua entre R e Xc, os autores são cautelosos em aceitar que componentes isolados reflitam compartimentos específicos; etnias diferentes podem ter elipses diferentes.

**Como se enquadra no Zaku.**
- R/H e Xc/H não foram propostos como índices isolados; o catálogo os avalia como monômios exatos (R +1, H −1) e (Xc +1, H −1). O rótulo e a nota registram isso. No NHANES, R/H saiu redundante com H²/R (ρ 0,96), coerente com a advertência de Piccoli.
- Σ condicional ao estado clínico, não só ao sexo (0,32 a 0,71). "Estrato" pode ser condição clínica.
- Sem referência de composição: auditar R/H contra massa magra está fora do que o artigo propôs; a nota avisa.
- Unidade Ω/m: a expressão do catálogo passa a usar H_m.
- Sem exemplo numérico individual; médias da Tabela 1 como nota de consistência.

**Decisão do Thalles (11/09/2026):** manter R/H e Xc/H no catálogo como componentes auditados individualmente, com a ressalva explícita. Seis pontos aplicados; catálogo 1.2.2.

---

## 5. Levi Micheli M, Cannataro R, Gulisano M, Mascherini G (2022). Proposal of a new parameter for evaluating muscle mass in footballers through bioimpedance analysis. Biology 11(8):1182. DOI 10.3390/biology11081182

**Arquivo:** levimicheli2022.pdf (7 p., acesso aberto).

**O que o artigo faz.**
- Amostra: 664 futebolistas homens italianos, caucasianos, 18-35 anos (24,5 ± 5,8), séries A-D, em temporada, mesmo operador. Elite 241, alto 223, médio 200.
- Medida: Akern BIA-101, 800 µA a 50 kHz, lado direito, supino, calibração diária (380 Ω / 47 Ω).
- Definição (p. 3): LMI = (PA × H)/R, PA em graus, H em cm; °·cm·Ω⁻¹. Médias (Tabela 2): elite 3,08, alto 2,87, médio 2,71; discrimina níveis com tamanho de efeito até 1,04.
- Validação (Tabela 3): r 0,908 com BCM, 0,925 com BCMI, 0,704 com PA, 0,035 com massa gorda. BCM e massa gorda vêm da equação de Kotler 1996, derivada da BIA; não há método de referência independente, e os autores admitem (p. 5-6).
- Limites declarados: só mão-pé a 50 kHz; um país; usos em crianças, desnutridos e idosos são direções futuras.
- Dados sob pedido ao autor correspondente (Mascherini, Florença).

**Como se enquadra no Zaku.**
- Caso exemplar da tese do framework: a correlação LMI-BCM é em grande parte algébrica (mesmas R, Xc, H), previsível por Σ. O "controle" (massa gorda) também é derivado da BIA: a declaração de independência alvo-variáveis seria falsa.
- Forma aproximada Xc·H/R² = (Xc/H)/(R/H)², monômio nos componentes de Piccoli; não exato pelo arctan → `composite` com vetor ajustado e R² (decisão de 11/09).
- Sem antecessor no catálogo; no NHANES (critério DXA) foi original (ρ máx 0,86) e o mais específico dos cinco: índice bom com validação circular na origem; a validação independente é o que a demonstração oferece.
- Validade: homens caucasianos futebolistas 18-35, mão-pé 50 kHz.
- Exemplo numérico: médias de grupo dão 3,06 vs 3,08 e 2,67 vs 2,71; nota de consistência, não `check_example` (média de razões ≠ razão de médias).

**Decisão do Thalles (11/09/2026):** aprovado com máximo rigor; seis pontos aplicados; catálogo 1.2.3. Registro à parte: contato com Mascherini pode ser enquadrado como auditoria independente do LMI com DXA.

---

## 6. Buffa R, Saragat B, Cabras S, Rinaldi AC, Marini E (2013). Accuracy of specific BIVA for the assessment of body composition in the United States population. PLoS ONE 8(3):e58533. DOI 10.1371/journal.pone.0058533

**Arquivo:** buffa2013.pdf (10 p., acesso aberto).

**O que o artigo faz.**
- Amostra: NHANES 2003-2004, 1.590 adultos (836 H, 754 M), 21-49 anos, etnias agrupadas, só ajuste perfeito ao modelo de Cole (BIDFIT = 0). HYDRA 4200; DXA Hologic QDR-4500A. Mesma fonte de dados da demonstração do Zaku; base depositada em veprints.unica.it/809.
- Definição (p. 3-4): Rsp = R·A/L, Xcsp = Xc·A/L; A = 0,45·área braço + 0,10·área cintura + 0,45·área panturrilha (C²/4π, m²); L = 1,1·H; ×100 → Ω·cm. Médias: homens Rsp 402,4, Xcsp 52,5; mulheres 492,0, 55,4.
- Referência independente: DXA (% gordura) e BIS (ECW/ICW).
- Tabela 2: Rsp com % gordura 0,85 (H) e 0,87 (M); Xcsp 0,68 e 0,77; R/H e Xc/H clássicos −0,16 a −0,35; PhA −0,94/−0,92 com ECW/ICW. ROC para gordura: específica 0,84-0,92, clássica 0,49-0,61 (p = 0,002).
- Tabela 1: r(R/H, Xc/H) 0,74 nos dois sexos; r(Rsp, Xcsp) 0,84/0,88.
- Precedência: proposta em Marini 2012 (idosos italianos); resistividade específica em Chumlea, Baumgartner e Roche 1988.

**Como se enquadra no Zaku.**
- Rsp/Xcsp medem gordura por desenho → contra alvo de massa magra "acompanham o controle"; a auditoria correta troca alvo e controle. Motivou o campo `target_kind` e o aviso de orientação.
- Confirmação externa da advertência de Piccoli: R/H e Xc/H isolados ≈ acaso para gordura.
- Não monômio (soma ponderada de quadrados) → `composite`, R² reportado.
- Σ específica de população: r(R/H, Xc/H) 0,74 (NHANES) vs 0,32 (saudáveis de Pádua).
- Escala: expressão corrigida para A/(1,1·H)·100; consistência 404,2 vs 402,4 (H) e 52,5 vs 52,5.

**Decisão do Thalles (11/09/2026):** aprovados os seis pontos e o `target_kind`. Aplicado: catálogo 1.3.0; contrato v0.4.6 (`target_kind`, `declarations.target_kinds`, aviso de orientação, nunca bloqueio); `target_kind` atribuído aos sete índices curados.

**A buscar (fundamentais):** Marini et al. 2012, J Nutr Health Aging (proposta original da BIVA específica); Chumlea, Baumgartner & Roche 1988, Am J Clin Nutr 48:7-15 (resistividade específica).

---

## 7. Lukaski HC, Kyle UG, Kondrup J (2017). Assessment of adult malnutrition and prognosis with bioelectrical impedance analysis: phase angle and impedance ratio. Curr Opin Clin Nutr Metab Care 20(5):330-339. DOI 10.1097/MCO.0000000000000387

**Arquivo:** lukaski2017.pdf (10 p.). Revisão narrativa; não é fonte primária.

**O que o artigo faz.** Revisa o ângulo de fase (50 kHz) e a razão de impedância Z200/Z5 como marcadores de prognóstico. Define a razão no texto (p. 2), atribuída a Mulasi 2015; antecedente Jenin 1975 (Z5/Z100). Tabela 1: 30 estudos observacionais desde 2012 com ângulo baixo predizendo desnutrição, complicações e mortalidade (cortes 4,4°-5,9°); ângulo de fase padronizado (escore z por sexo, idade, IMC). Pontos-chave: "não é diagnóstico"; hidratação e inflamação confundem; só aparelhos sensíveis à fase; aparelhos (Genton 2017) e eletrodos (Nescolarde 2016) deslocam os valores.

**Como se enquadra no Zaku.** Sustenta "um aparelho por base"; o escore z por estrato é a versão clínica de Σ por estrato; hidratação como confundidor declarado = controle negativo natural para o ângulo de fase; a razão de impedância mantém confiança baixa (fonte secundária). NHANES BIX tem R e Xc a 5, 50 e 200 kHz → razão avaliável na demonstração ao acrescentar Z5 e Z200 ao CSV.

**Decisão do Thalles (11/09/2026):** aprovados os quatro pontos. Aplicado: entrada IR (rótulo, target_kind hidratação, nota de precedência, confiança baixa), nota no PhA, referências de aparelho/eletrodo na página; catálogo 1.3.1. Pendente: acrescentar Z5/Z200 ao CSV da demonstração.

---

## 8. Marini E, Sergi G, Succa V, Saragat B, Sarti S, Coin A, Manzato E, Buffa R (2013). Efficacy of specific bioelectrical impedance vector analysis (BIVA) for assessing body composition in the elderly. J Nutr Health Aging 17(6):515-521. DOI 10.1007/s12603-012-0411-7

**Arquivo:** marini2013.pdf (7 p.). Proposta original da BIVA específica (recebido em junho de 2012).

**O que o artigo faz.** Fórmula completa (p. 516): A = 0,45·braço + 0,10·cintura + 0,45·panturrilha (C²/4π), L = 1,1·H, ×100 → Ω·cm; pesos da partição da resistência (braços 45 %, pernas 45 %, tronco 10 %); 1,1 de antropometria sarda. Amostra: 207 idosos de Pádua (75 H, 132 M), 65-93 anos, saudáveis e ativos; 5 desidratados excluídos → 202. Akern BIA 101; DXA Hologic QDR 4500W. BIVA clássica distingue massa absoluta mas não % de gordura (R/H e Xc/H iguais entre quartis); valores específicos distinguem (Tabela 3). Fig. 3: Rsp 0,75/0,69 e Xcsp 0,53/0,48 com % gordura; R/H −0,13/−0,16 n.s. Antecedente declarado: Chumlea, Baumgartner e Roche 1988.

**Como se enquadra no Zaku.** Fixa fórmula e precedência na origem (2013); Buffa 2013 vira validação em NHANES. Dois pontos publicados para transferência de Σ (idosos italianos vs adultos americanos: mesmo sinal, magnitudes 0,75 vs 0,85). Terceira confirmação de que R/H isolado não mede gordura. Sem exemplo individual; médias da Tabela 1 dão 392,6 Ω·cm (entre os grupos de quartil 334,7 e 450,3).

**Decisão do Thalles (11/09/2026):** aprovado; cinco pontos aplicados; catálogo 1.3.2.

---

## 9. Mulasi U, Kuchnia AJ, Cole AJ, Earthman CP (2015). Bioimpedance at the bedside: current applications, limitations, and opportunities. Nutr Clin Pract 30(2):180-193. DOI 10.1177/0884533614568155

**Arquivo:** mulasi2015.pdf (14 p.). Revisão convidada; não é fonte primária.

**O que o artigo faz.** Define a razão de impedância (p. 8) como Z200/Z5, nome introduzido pela Bodystat (fabricante); cortes de referência ≤0,78 (H) e ≤0,82 (M) de um resumo (Plank 2013); aplicações em edema, insuficiência cardíaca, desnutrição, todas sem corte consensual. Tabela 1: aparelhos comerciais e frequências. P. 3: o modelo de condutor de volume assume cilindro único; BIA de frequência única não separa água intra/extracelular; aparelhos "caixa preta".

**Como se enquadra no Zaku.** Achado de curadoria: a razão 200/5 não tem artigo de derivação; cadeia fabricante → resumos → revisões. Antecedente científico Jenin 1975 (5/100 kHz), só resumo disponível. Confiança fica baixa por regra do contrato. Tabela 1 sustenta "um aparelho por base".

**Decisão do Thalles (11/09/2026):** ok; aplicado; catálogo 1.3.3.
