# BioMS Zaku in dieci minuti

[English](GUIDE_10_MINUTES.md) · [Español](GUIDE_10_MINUTES.es.md) · [Português](GUIDE_10_MINUTES.pt.md) · **Italiano**

Hai un foglio di calcolo con la bioimpedenza (R e Xc a 50 kHz), la statura, la massa corporea e una misura di riferimento, come
la massa magra o la massa grassa da DXA. Vuoi sapere come si comportano gli indici pubblicati sui tuoi dati, e forse creare i
tuoi. Tutto si fa in un terminale, con un comando che ti conduce per domande. Nulla è deciso in silenzio: ogni risposta è
scritta in un file YAML, e la stessa analisi può essere ripetuta senza domande.

## 1. Installare (una volta)

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang it
```

La seconda riga mostra l'insegna e i tre comandi. Se è apparsa, è installato.

## 2. Preparare il foglio di calcolo

Un file `.csv` con una riga per persona e colonne numeriche per R, Xc, statura, massa corporea e il riferimento. Il separatore e
il decimale sono rilevati. I nomi delle colonne sono liberi; Zaku suggerisce la mappatura e tu la confermi.

## 3. Eseguire

```
bioms-zaku --lang it start dati.csv
```

A qualsiasi domanda: **Invio** accetta il suggerimento fra [parentesi quadre], **`<`** torna alla domanda precedente, **`?`**
ripete l'aiuto, **`none`** rifiuta una colonna suggerita. Alla fine di ogni schermata appare un riassunto numerato e "correggere
qualche riga?".

Che cosa chiede, nell'ordine:

1. **lingua, nome dei dati, ricercatore** — vanno nell'intestazione del rapporto e nel registro dell'esecuzione;
2. **le colonne** — R, Xc, H, W e le loro unità; il **target** (ciò che gli indici dovrebbero predire, misurato con un metodo
   indipendente); il **controllo negativo** (ciò che NON dovrebbero predire, per esempio la massa grassa quando il target è la
   massa magra); le covariate (massa e statura, suggerite); lo strato (sesso) e le etichette (`0=F,1=M`); l'identificatore;
   colonne opzionali di sesso, età e circonferenze per i metodi che le usano; e la dichiarazione che target e controllo **non
   sono stati calcolati** da R, Xc, H, W;
3. **esecuzione standard** — `check` verifica tutto e Zaku esegue. L'ultima riga dice dove è il rapporto e come aprirlo.

Se è tutto ciò che ti serve, puoi fermarti qui. È l'**uso standard**.

4. **"vuoi suggerimenti di indici progettati?"** — se rispondi `yes`, Zaku stima un indice sul target e uno sul controllo, per
   strato, usando il 70 % delle righe, e mostra ciascuno: formula, R² su quelle righe, l'indice pubblicato più somigliante, un
   nome suggerito. Tu rispondi `yes`, `edit` (cambiare il nome, arrotondare gli esponenti) oppure `no`. Nessun verdetto appare
   prima che tu decida, di proposito. Un esponente modificato a mano diventa un indice **proposto** (◇), non progettato (△).
5. **"hai un indice tuo da provare?"** — scrivi la formula in R, Xc, H, W (`H_m` statura in metri, `PhA` angolo di fase in
   gradi, `mean(PhA)` media del campione). È verificata subito sui tuoi dati: quanti valori finiti e positivi, minimo, mediana,
   massimo; se è costante, non ha valore verificabile o è uguale a un metodo pubblicato, lo sai prima di accettarla.
6. **esecuzione finale** — solo se qualcosa è stato accettato o proposto: pubblicati + accettati + i tuoi, validati sul 30 % di
   righe che la progettazione non ha mai visto.

## 4. Leggere il rapporto

Apri `report.html` nel browser (il comando è sull'ultima riga del terminale). Ordine di lettura:

- **Numeri chiave**: persone sottoposte ad audit, metodi, verdetti come sigilli colorati, quanti aggiungono valore, se target e
  controllo sono accoppiati nei tuoi dati.
- **Scheda dei verdetti** (una per strato): ogni metodo in tre colonne — originale o ripete un metodo precedente; specifico,
  segue il controllo, misura entrambi o nessun segnale; aggiunge valore oltre massa e statura oppure no. ◇ = tuo;
  △ = progettato.
- **Ipotesi e soglie**: ogni procedura con l'ipotesi che porta e il suo stato in questa esecuzione; ogni soglia con il suo
  valore, l'origine e il sostegno. È dove un revisore controlla che nulla sia stato improvvisato.
- **Riferimenti**: le fonti dei metodi valutati e dei metodi statistici, con DOI.

Regole di lettura che valgono sempre: ogni numero descrive **questo** campione; un indice "ripete" un altro solo in questo
campione e per questo target; "utile" vuol dire che ha superato massa e statura da sole.

## 5. Ripetere, cambiare lingua, un'altra base

```
bioms-zaku run dati.zaku.yaml               # la stessa analisi, senza domande, tabelle identiche byte per byte
bioms-zaku --lang en render zaku_out/dati   # lo stesso rapporto in un'altra lingua, senza ricalcolare
bioms-zaku propose altra.zaku.yaml          # scrivere un indice (per esempio un vettore progettato qui) per validarlo su un'altra base
```

Per validare un indice progettato su un'altra base, copia il vettore che appare nel riassunto (per esempio `R −0.49, Xc +0.11,
H +1.27, W +0.42`) e scrivilo in `propose` come `R**(-0.49) * Xc**(0.11) * H**(1.27) * W**(0.42)`.

## 6. Quando qualcosa va storto

- **"non è nel file"**: nome di colonna con un errore di battitura; la domanda è ripetuta con l'elenco.
- **"il controllo è il target stesso"**: controllo e target devono essere misure diverse.
- **"lascerebbe ≈ N righe da sottoporre ad audit, sotto data.min_n"**: troppe poche persone per strato per progettare indici;
  usa più righe o esegui senza strato. L'esecuzione standard non è toccata.
- **"mancano gli input [...]"**: un metodo del catalogo ha bisogno di una colonna che non hai (per esempio |Z| a 100 kHz); è
  saltato e il rapporto lo dice.
- **Ctrl+C** termina senza scrivere altro.

## 7. Tre casi reali, e che cosa ha insegnato ciascuno (15/09/2026)

- **Campione NHANES, 300 persone, target massa magra da DXA.** Lukaski e R/H specifici in entrambi i sessi; Rsp e Xcsp seguono
  il controllo (sono indici di grasso, e il rapporto lo dice). Lezione: per **progettare** indici per sesso servono circa 185
  persone per strato; con meno, `start` blocca i suggerimenti prima di mostrarli, perché l'audit non avrebbe un bootstrap valido.
- **CrossFit, 107 uomini, target grasso da plicometria, controllo circonferenza del braccio corretta.** Rsp è stato il solo
  specifico per il grasso, esattamente ciò che i suoi autori hanno progettato. Gli indici progettati su NHANES per il grasso
  sono diventati "misura entrambi" negli atleti: dove la massa in più è muscolo, un indice quasi uguale a W²/H² legge muscolo.
  Lezione: il trasferimento fra popolazioni si legge dalla geometria (il coseno con il controllo) prima di qualsiasi verdetto.
- **Atletica, 61 atleti, target altezza del salto, controllo tempo dello sprint.** Tutto "nessun segnale", e il motivo è
  apparso in un numero: il coseno fra target e controllo è stato −0,98. Salto e sprint sono la stessa direzione nello spazio
  della BIA. Lezione: il controllo negativo deve essere un costrutto **diverso** dal target; un'altra misura di prestazione non
  serve. L'angolo di fase è stato quello che ha aggiunto di più su massa e statura (+0,38), con un intervallo ampio.

## Dati di esempio e risultati che non vengono mai sovrascritti

Zaku porta **una** base di esempio, sintetica, che serve a tutti gli usi:

```bash
bioms-zaku examples --copy     # copia in ./zaku_exemplos (se esiste già: zaku_exemplos_2, …)
cd zaku_exemplos
```

`zaku_exemplo.csv`: 400 persone (200 per sesso), estratte dalle medie e covarianze di NHANES stimate separatamente per ogni
combinazione di sesso e diabete; nessuna persona reale. Che cosa puoi provare con essa:

| prova | target | controllo | risposta attesa |
|---|---|---|---|
| regressione | `LMI_DXA` | `FMI_DXA` | gli indici di massa magra portano il target |
| classificazione con risposta nota | `label_synthetic` | `FMI_DXA` | **nessun** indice specifico: l'etichetta dipende solo da FMI ed età |
| diabete | `diabetes` | `FMI_DXA` o `LMI_DXA` | domanda aperta, come in uno studio reale |

Usa `-o` per dare un nome a ogni prova (`bioms-zaku start zaku_exemplo.csv -o regressione.yaml`). Le masse in kg (`lean_kg`,
`fat_kg`) sono calcolate dalla statura: non usarle come target con la statura mappata. File tecnici (vecchio esempio da 8000
righe, formato foglio di calcolo, campione reale NHANES): `bioms-zaku examples --all`.

Ogni esecuzione scrive in `zaku_out/<nome>`; se la cartella contiene già un'esecuzione conclusa, la nuova va in `<nome>_2`,
`<nome>_3`, … In `start`, l'esecuzione standard e quella finale (con gli indici accettati) restano in cartelle separate. Nulla
viene sovrascritto.

## Di quante persone ho bisogno?

Zaku descrive il tuo campione e avvisa quando è troppo piccolo per sostenere un verdetto; non stima una popolazione. I minimi sono operativi, e il
rapporto dice, in ogni caso, che cosa è stato possibile calcolare.

| che cosa vuoi | minimo | perché |
|---|---|---|
| esecuzione standard, target continuo (es. massa magra da DXA) | 30 persone per strato | un ridge con un predittore e ricampionamenti con ≥ 20 persone fuori dal sacco |
| classificazione (es. diabete sì/no) | 20 persone nella classe minore, per strato | sotto questo il bootstrap non ha un ricampionamento valido; fra 20 e ~32 il rapporto segna *eventi per variabile < 10* e il verdetto è esplorativo |
| suggerimenti di indici (progettazione) | ≈ 185 persone per strato | il 70 % va alla progettazione; il 30 % restante deve mantenere ≥ 20 fuori dal sacco |
| strati (es. per sesso) | ogni strato soddisfa i minimi sopra | altrimenti Zaku esegue l'audit senza strato, o avvisa |
| misure ripetute della stessa persona (pre/post) | **una riga per persona** | aggrega prima (una media, o una visita); Zaku rifiuta un `id` ripetuto in questa versione |

Con pochi dati, preferisci: senza strato, senza suggerimenti, target continuo. I verdetti escono con intervalli ampi, e il
rapporto lo dice; è informazione, non un difetto.

## Classificazione con pochi casi e un secondo classificatore

Lo stimatore principale della classificazione è la regressione logistica con penalità L2: è il più stabile quando gli eventi
sono pochi. Il rapporto calcola, per ogni modello, gli **eventi per variabile** di un ricampionamento di addestramento
(`epv_train`) e li segna sotto 10 (Peduzzi 1996): leggi quei verdetti come esplorativi. Il minimo per classe resta 20; Zaku
descrive il tuo campione e avvisa quando è troppo piccolo, invece di rifiutare.

Se vuoi vedere se il verdetto resiste a un classificatore di macchina (boosting), dichiaralo come **sensibilità**: gira sugli
stessi ricampionamenti, esce accanto al principale e non è mai scelto in base al risultato:

```yaml
audit:
  sensitivity: {estimator: hgb, params: {max_depth: 3, learning_rate: 0.05, max_iter: 300}}
```

`xgboost` è accettato anche, se installato. Il boosting ha bisogno di più dati della logistica, non di meno: con poche decine di
eventi, aspettati guadagni instabili, ed è esattamente ciò che mostra il confronto affiancato.
