<p align="center"><img src="docs/assets/logo.svg" alt="BioMS Zaku" width="360"></p>

# BioMS Zaku

[English](README.md) · [Español](README.es.md) · [Português](README.pt.md) · **Italiano**

Decomposizione algebrica e audit predittivo di indici ed equazioni predittive. Dimostrato sulla bioimpedenza.

*zaku* è un verbo della lingua juruna (yudjá), famiglia tupi, Xingu, Mato Grosso, Brasile: "vedere / prendersi cura /
attendere" (Lima, S. *A estrutura argumental dos verbos na língua Juruna (Yudjá)*, tesi di laurea magistrale, USP,
2008, voce 290). Il metodo guarda un indice prima di accettarlo, si prende cura della sua validità e attende il
risultato fuori campione.

## Che cos'è?

Hai un foglio di calcolo: una riga per persona, con resistenza e reattanza da un apparecchio di bioimpedenza,
statura, massa corporea e una misura di riferimento come la DXA. BioMS Zaku guarda gli indici che ti interessano e
risponde a tre domande su ciascuno. *È nuovo*, o esiste già con un altro nome? *Misura ciò che dichiara*, o sta
seguendo la taglia corporea — che quasi tutto segue? *Aggiunge qualcosa* rispetto a statura e massa corporea da sole?

La seconda domanda è quella che conta. "Il mio indice correla con la massa magra" prova poco: le persone più grandi
hanno più di tutto. Perciò, prima di vedere qualsiasi risultato, dichiari un target e un **controllo negativo**, e lo
strumento verifica se l'indice predice il target *oltre* ciò che il controllo già predice. Quando non lo fa, lo dice
chiaramente.

Non devi saper programmare. In un terminale, `bioms-zaku start dati.csv` ti fa le domande e annota le tue risposte; in
un notebook, lo apri e premi esegui, con i dati di esempio già dentro. Ne esce un unico file, `report.html`: ogni
numero, ogni figura e, accanto a ciascuno, come è stato calcolato e come leggerlo.

Stato: release candidate (1.0.0rc1) · Licenza: MIT · Citazione: `CITATION.cff` · **Ciò che lo strumento garantisce, e sotto quali ipotesi:** [`CONTRATOS.md`](CONTRATOS.md)

## Che cosa fa

1. **Decomposizione.** Ogni indice o equazione è scritto come prodotto di potenze delle variabili misurate e
   rappresentato dal suo **vettore di esponenti**. La matrice di covarianza Σ delle variabili in logaritmo, in una
   popolazione, prevede la correlazione di Pearson dei logaritmi fra due indici qualsiasi *prima che uno dei due sia
   calcolato*: aᵀΣb / √(aᵀΣa · bᵀΣb), un'identità valida per qualsiasi distribuzione. La ridondanza osservata è
   misurata con la correlazione per ranghi di Spearman (soglia 0,95) e la pubblicazione più antica mantiene la
   precedenza. Gli indici che non sono prodotti esatti ricevono un vettore stimato con l'R² della stima.
2. **Controllo negativo condizionale.** Il ricercatore dichiara un target e un controllo negativo. Su ricampionamenti
   out-of-bag identici, il framework stima il controllo come predittore del target con e senza l'indice (guadagno S1) e
   il target come predittore del controllo con e senza l'indice (guadagno S2). Verdetti: *specifico* (S1 presente, S2
   assente), *segue il controllo* (l'inverso), *misura entrambi*, *nessun segnale*; un guadagno è presente quando la
   sua media supera 0,03, il suo intervallo al 95 % esclude lo 0 e P(d > 0) ≥ 0,95. Più il **valore aggiunto** rispetto
   alle covariate di base.
3. **Trasferimento di Σ.** La Σ di uno strato applicata a un altro, riportata come errore proprio contro errore
   trasferito, eccesso a coppie con bootstrap di persone e la frazione di coppie entro una tolleranza fissa (nulla di
   ciò dipende da n).
4. **Progettazione (sperimentale).** Un indice nuovo è stimato su una partizione di progettazione e sottoposto ad audit
   su una partizione disgiunta; richiede la dichiarazione che il target non sia calcolato dalle variabili mappate.

Gli output sono tabelle aggregate (precisione completa), un manifest (hash, versioni, semi), un riassunto, quattro
figure (`lineage` albero genealogico, `target_control` barre appaiate, `exponents` + Σ, `scorecard`) e un `report.html`
in un unico file. I dati per riga non lasciano mai l'esecuzione. Le figure accettano
`figures: {title, subtitle, language: en|es|pt|it, palette, captions}`. Come leggere ogni figura: `docs/index.html`,
sezione 3.

## Inizia qui

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang it start dati.csv        # un percorso guidato: colonne → esecuzione standard → suggerimenti (accetta/modifica/no) → il tuo indice → rapporto
```
`<` torna indietro, `?` ripete l'aiuto, Invio accetta il suggerimento. Tutto ciò che rispondi è scritto in
`dati.zaku.yaml`, così `bioms-zaku run dati.zaku.yaml` ripete l'analisi senza domande. Guida di dieci minuti:
`GUIA_10_MINUTOS.md`.

**In un notebook (Colab o Jupyter)** non c'è nulla da scaricare: `pip install bioms-zaku` porta i dati di esempio
dentro il pacchetto. `examples/zaku_exemplo.ipynb` installa, li carica e percorre i tre usi in circa un minuto — la
ridondanza prevista da Σ prima che qualsiasi indice sia calcolato, l'audit contro un controllo negativo e il rapporto.
`bioms-zaku examples --copy` consegna il notebook insieme ai dati.

## Installare

```bash
pip install bioms-zaku            # dopo la prima pubblicazione; fino ad allora:
pip install -e ".[plots,dev]"     # da un clone di questo repository
```

Python ≥ 3.10. Dipendenze: numpy, pandas, scipy, scikit-learn, pyyaml (+ matplotlib per le figure).

## Dati di esempio

**I dati di esempio** (nulla è scaricato; viaggiano col pacchetto): UNA base sintetica, `zaku_exemplo.csv`, 400 righe
(200 per sesso), estratte da una log-normale le cui medie e covarianze sono state stimate in NHANES 1999–2004
separatamente per ogni cella sesso × diabete diagnosticato dal medico — così che l'associazione del diabete con ogni
variabile è conservata. Serve a tutti gli usi: regressione (`LMI_DXA`, `FMI_DXA`, `ALMI_DXA`), classificazione con
risposta nota (`label_synthetic` dipende solo da FMI ed età: con `FMI_DXA` come controllo nessun indice dovrebbe
aggiungere) e `diabetes` (70 per sesso, arricchito in casi di proposito). Parametri e generatore:
`examples/zaku_exemplo_params.json`, `tools/make_zaku_example.py` (riproduce il CSV byte per byte).

```bash
bioms-zaku examples --copy             # ./zaku_exemplos (una cartella esistente non è mai toccata: _2, _3 …)
cd zaku_exemplos && bioms-zaku start zaku_exemplo.csv -o regressione.yaml
bioms-zaku examples --all              # anche i file tecnici (vecchio esempio sintetico da 8000 righe, formato foglio di calcolo, un campione reale NHANES)
```

```python
from bioms_zaku.api import load_example
df = load_example("zaku_exemplo")
```

`examples/example_data.csv` — 8 000 righe **sintetiche** (4 000 per sesso). Sono estrazioni da una log-normale
multivariata il cui vettore di medie e la covarianza Σ dei logaritmi sono stati stimati, per sesso, su un **campione di
convenienza** di NHANES 1999–2004 (adulti da 18 a 49 anni, DXA misurata, BIA a 50 kHz; n = 2 792 donne, 3 036 uomini).
Nessuna riga reale è riprodotta; solo μ e Σ hanno lasciato la fonte, e sono pubblicati in
`examples/example_data_params.json` (con l'asimmetria e la curtosi dei logaritmi della fonte, perché
l'approssimazione log-normale possa essere giudicata), insieme al generatore `tools/make_example_data.py` e al suo
seme. Il file porta R, Xc, statura, massa corporea, età, tre circonferenze, gli indici di massa magra/appendicolare/
grassa da DXA e un'etichetta binaria sintetica dichiarata. Usalo per imparare il metodo, provare lo strumento e
decomporre Σ a mano.

```bash
bioms-zaku run examples/example_quick.yaml      # 7 indici curati, preset quick, ~20 s
bioms-zaku run examples/example_full.yaml       # gli stessi dati, preset full (CV 5×50, B = 2000), per riportare
bioms-zaku                                      # benvenuto: i tre comandi, nella tua lingua (--lang it)
bioms-zaku propose analisi.yaml                 # aggiunge i tuoi indici, una domanda per volta (formula verificata sui tuoi dati)
bioms-zaku run examples/minimal.yaml            # 150 righe, l'esecuzione più piccola possibile
ls zaku_out/example_quick                       # algebra sigma pairs redundancy sigma_transfer audit utility combinations screening sensitivity threshold_sensitivity (.csv) manifest.json summary.md report.html figures/
```

`examples/nhanes_diabetes_400.csv` — 400 righe **reali** dai file di uso pubblico di NHANES 1999–2004 (CDC, dominio
pubblico): adulti da 18 a 49 anni con DXA misurata e BIA a 50 kHz, casi completi, con la risposta del questionario sul
diabete (`diabetes_1Y_0N` = diagnosticato dal medico). È un **campione di convenienza arricchito in casi** — ogni
diabetico diagnosticato con dato completo (139: 79 donne, 60 uomini) più un'estrazione con seme di non diabetici —
quindi NON è rappresentativo della prevalenza; esiste per dimostrare l'audit di classificazione (≥ 20 per classe per
sesso) e, con le sue masse da DXA, l'audit di regressione su dati reali. Provenienza, esclusioni, seme e SHA-256:
`examples/nhanes_diabetes_400_provenance.json`; generatore: `tools/make_nhanes_example.py`. I nomi delle colonne sono
quelli che il flusso guidato riconosce (`bioms-zaku start examples/nhanes_diabetes_400.csv`). Questo è l'unico esempio
con righe reali; gli altri sono sintetici.

Le masse in kg sono derivate dagli indici e dalla statura: non usarle come target mentre la statura è mappata
(circolarità).

**I risultati non sono mai sovrascritti.** Un'esecuzione la cui cartella contiene già un'esecuzione terminata va in
`nome_2`, `nome_3`, …; l'esecuzione standard e quella finale del flusso guidato finiscono quindi in due cartelle.
`output.overwrite: true` sostituisce invece, e lo dichiara.

**Di quante persone ho bisogno?** 30 per strato per un target continuo; 20 nella classe minore per la classificazione
(fra 20 e ~32 il rapporto segnala *eventi per variabile < 10* e il verdetto è esplorativo); circa 185 per strato per
chiedere indici progettati; una riga per persona (aggrega prima le misure ripetute — gli id ripetuti sono rifiutati in
questa versione).

Il file porta anche `lean_kg`, `alm_kg`, `fat_kg` (indice × statura², derivati, senza nuova estrazione) perché le masse
assolute possano essere usate come target: `bioms-zaku run examples/example_kg.yaml`. Vedi *Geometria* più sotto prima
di scegliere.

Lingua: `bioms-zaku --lang it init …` (oppure `language: it` nel YAML; `init` lo chiede per primo). en, es, pt, it.
Le domande, i messaggi di `check`/`run`, il `summary.md`, i titoli del rapporto e le figure seguono la lingua; i nomi
di colonna dei CSV e le chiavi del YAML restano in inglese.

I tuoi dati — tre comandi:

```bash
bioms-zaku init miei_dati.csv          # chiede quale colonna è R, Xc, H, W, target, controllo e, opzionalmente, sesso, età, circonferenze di braccio/vita/polpaccio (suggerisce, non indovina mai) → miei_dati.zaku.yaml
bioms-zaku check miei_dati.zaku.yaml   # valida dati + configurazione SENZA eseguire: righe, classi, metodi, bootstrap, circolarità
bioms-zaku run   miei_dati.zaku.yaml   # l'analisi
```

`init` non interattivo: `bioms-zaku init miei_dati.csv --map R=resistenza Xc=reattanza H=statura W=massa_corporea target=lmi control=fmi independent=yes`,
aggiungendo opzionalmente `strata=sesso id=soggetto age=eta arm=braccio waist=vita calf=polpaccio` perché le equazioni
del catalogo che richiedono sesso, età o circonferenze possano essere valutate; `check` elenca ogni metodo che non
riesce a valutare e di quale colonna ha bisogno. Il YAML mappa le colonne ai ruoli (vedi `CONTRATOS.md` §1):
`variables` (R, Xc, H, W alla frequenza dichiarata), `units`, `targets`, `controls`, e opzionalmente `covariates`,
`strata`, `groups`, `id` e `declarations.targets_independent_of_variables` (vero solo se nessun target/controllo è
calcolato dalle variabili mappate — la regola della circolarità).

```yaml
run_name: mio_studio
data:
  path: miei_dati.csv
  columns:
    variables: {R: resistenza_ohm, Xc: reattanza_ohm, H: statura_cm, W: massa_kg}
    units: {H: cm, W: kg}
    targets:  {LMI: indice_massa_magra}
    controls: {FMI: indice_massa_grassa}
    covariates: [massa_kg, statura_cm]
strata: sesso
preset: full             # CV 5×50, B = 2000 (quick = 5×5, B = 200, solo per dimostrazione)
```

## Regole che il codice impone

- tutto fuori campione; ogni contrasto appaiato sugli stessi ricampionamenti; il ricampionamento è funzione
  deterministica di (righe, seme, B, min_oob) — `n_jobs` non cambia mai un numero;
- nessuna imputazione per impostazione predefinita (caso completo per metodo; caso completo dell'unione per i
  contrasti appaiati);
- stimatore dichiarato prima dei dati (Ridge / logistica per gli indici singoli; boosting per le combinazioni); nessuna
  selezione in base al risultato;
- espressioni del catalogo interpretate da un AST con lista bianca (senza `eval`); vettori del catalogo validati
  numericamente; esempi numerici pubblicati verificati al caricamento; i metodi con trascrizione non valida portano
  `status: excluded` e non sono mai valutati;
- i verdetti sono descrittivi (la P del bootstrap non è un valore p); soglie fissate nei contratti;
- gli output non contengono mai dati per riga (sicuro da eseguire dentro l'ambiente di un partner).

## Catalogo

Otto indici pubblici di bioimpedenza, ciascuno riverificato sulla sua fonte primaria
(`catalogo/fontes_primarias_indices/LEITURAS.md`): H²/|Z| a 100 kHz (Hoffer 1969), indice di impedenza H²/R
(Lukaski 1985), angolo di fase di tutto il corpo (Baumgartner 1988), le componenti della BIVA R/H e Xc/H
(Piccoli 1994), resistività e reattività specifiche Rsp/Xcsp (Marini 2013; validate su NHANES da Buffa 2013) e l'LMI
(Levi Micheli 2022); il rapporto di impedenza Z200/Z5 è elencato con bassa confidenza (origine commerciale, nessun
articolo di derivazione). Ogni voce registra il campione di derivazione separatamente dalla validità dichiarata dagli
autori (fuori da essa il framework segnala †, non blocca mai), il tipo dichiarato di target (`target_kind`: un indice
di massa grassa sottoposto ad audit contro un target di massa magra riceve un avviso di orientamento) e ogni evento di
curatela nella `history` del catalogo. L'angolo di fase e l'LMI contengono atan e sono quindi `composite`: il loro
vettore di esponenti è stimato per strato e l'R² della stima è riportato (regola di esattezza, `CONTRATOS.md` §2.3).
**Solo le voci curate sono sottoposte ad audit per impostazione predefinita** (`catalog.include: curated`, il valore
che `init` scrive): le otto la cui fonte primaria è stata letta criticamente (`curated: true`, con
`curation_record`). Le equazioni predittive restano nel catalogo senza curatela e sono sottoposte ad audit solo con
`catalog.include: all`, contrassegnate con * in ogni output.

## Provare il tuo indice

Una tua formula entra nell'audit accanto ai metodi pubblicati come voce **proposta**: senza DOI, mai curata, mai con
precedenza su un metodo pubblicato, contrassegnata ◇ in ogni tabella e figura. È accettata qualsiasi espressione in
R, Xc, H, W (`+ - * / **`, `log`, `exp`, `sqrt`, `atan`, `max`, le costanti `pi` ed `e`, e le statistiche di campione
`mean`, `median`, `sd`, i cui valori sono registrati per strato e segnalati); un prodotto puro riceve un vettore
esatto, qualsiasi altra cosa un vettore stimato con il suo R². Gli otto indici BioMS dell'autore sono consegnati così
in `examples/bioms_mota_proposed.yaml`. È sottoposta ad audit solo quando elencata in `catalog.include`:

```yaml
catalog:
  include: [curated, mio_indice]        # i metodi curati più il tuo; il valore predefinito (curated) non sottopone mai ad audit una proposta
  user_entries:
    - id: mio_indice
      label: "H²·Xc/R (Mota, proposta 2026)"
      authors: Mota
      target: lean_mass                  # che cosa intende misurare
      expr: "H**2 * Xc / R"
      provenance: {formula_source: proposed, note: "ipotesi: la reattanza pesa l'acqua intracellulare"}
```

Non devi modificare il YAML a mano: `bioms-zaku propose analisi.yaml` chiede l'id, il nome, che cosa misura e la
formula, una per volta; ogni formula è verificata subito contro la grammatica e valutata sui tuoi dati (finita,
positiva, minimo/mediana/massimo, statistiche di campione usate), poi scritta nel YAML e inclusa nell'audit.

Il rapporto dice allora se ripete un indice pubblicato (ridondanza), se è specifico per il target contro il controllo,
se aggiunge valore rispetto alle covariate e se è parallelo al controllo. `bioms-zaku check` avvisa quando una proposta
è dichiarata ma non inclusa.

## Progettare il tuo indice dai dati

`init` chiede `design: none | target | control | both`. Per ciascuno, gli esponenti di R, Xc, H, W sono stimati su
ln(target) ai minimi quadrati sul 70 % delle righe (per strato) e l'indice è sottoposto ad audit sull'altro 30 %, mai
visto, come qualsiasi metodo pubblicato (contrassegnato △). Una proprietà registrata e testata rende questo il modo
giusto di "pulire il segnale": il miglior predittore del target è, per costruzione, condizionalmente non informativo
sulla proiezione del controllo — quindi la progettazione semplice è l'indice specifico nel senso del controllo
negativo condizionale, e l'audit verifica se ciò è sopravvissuto fuori campione. Nel YAML, `design:` è una lista;
`orthogonal_to: <colonna>` aggiunge la Σ-ortogonalità marginale a una colonna di disturbo (la taglia corporea), che è
un obiettivo diverso e in generale non supera il controllo condizionale (il rapporto lo dice).

## Geometria di target e controllo

Target e controllo vengono spesso dalla stessa misura di riferimento e dalla stessa normalizzazione (magra/H² e
grassa/H² dallo stesso esame DXA; magra + grassa + osso = massa corporea, con H e W fra le variabili mappate). Nello
spazio delle variabili mappate possono puntare quasi nella stessa direzione, e allora un indice vicino a quella
direzione (del tipo W/H²) predice entrambi per aritmetica. Il framework misura questo con l'algebra che già usa: il
*vettore implicito* di ogni target e controllo (OLS dei logaritmi), i coseni in Σ indice–target, indice–controllo e
target–controllo, e l'identità esatta r_log = cos_Σ·√R² per gli indici monomiali. Due bandiere con soglie dichiarate
annotano i verdetti e non li cambiano mai: PARALLEL_TO_CONTROL (‡ accanto all'indice) e COUPLED_TARGET_CONTROL (‡ nel
titolo del pannello). Tabelle `implicit_vectors.csv` e `geometry.csv`; blocco nel `summary.md`. Nell'esempio
consegnato il coseno target–controllo è 0,90 (donne) e 0,86 (uomini) per LMI contro FMI. Usare masse assolute (kg)
toglie la statura da entrambi i lati e abbassa l'accoppiamento, ma non toglie l'accoppiamento attraverso la massa
corporea, e rende il target più "taglia", il che favorisce gli indici di volume (H²/R): una scelta dichiarata, non una
correzione. La lezione 12 del quaderno svolge tutta la cosa a mano con quattro persone.

## Il rapporto

`report.html` è l'output principale: un unico file autocontenuto (figure e tabelle incorporate) che si apre dal disco.
In un notebook, `run()` lo mostra inline. Ogni blocco di risultato porta tre paragrafi fissi — *come è stato calcolato ·
come leggerlo · rigore applicato* — i cui numeri (fold, ripetizioni, B, margini, soglie, semi, stimatore) vengono
dalla configurazione risolta, mai da testo fisso. Ogni tabella ha un pulsante di download in **CSV** (incorporato,
funziona offline); `pip install bioms-zaku[excel]` aggiunge `tables.xlsx` (un foglio per tabella) accanto al rapporto.
Una sezione *Rigore di questa esecuzione* elenca preset, semi, versioni, hash dell'input, lo SHA-256 di ogni tabella di
output, il tempo di orologio e gli avvisi. Il rapporto non ricalcola nulla — ed è per questo che
`bioms-zaku --lang en render zaku_out/mia_esecuzione` riscrive riassunto, figure e rapporto di un'esecuzione terminata
in un'altra lingua in pochi secondi, lasciando tabelle e manifest intatti.

Il rapporto apre con un indice fisso e il **diagramma del metodo Zaku** (salvato anche come
`figures/zaku_method.svg`), mostra i numeri chiave letti dalle tabelle, raggruppa le figure per famiglia e i blocchi di
risultato a fisarmonica (uno aperto per volta), e termina con una sezione **Riferimenti**: le fonti di bioimpedenza dei
metodi valutati nell'esecuzione, gli antecedenti statistici e algebrici (indici di rapporto, scalatura allometrica,
controlli negativi, ridge, validazione incrociata, bootstrap, combinazioni) etichettati per blocco di risultato, e il
software eseguito. Ogni record viene dai metadati Crossref verificati il 15/09/2026 (`references.py`); nulla è caricato
dalla rete quando il rapporto è aperto.

## Riproducibilità

Il `manifest.json` registra la configurazione risolta, i semi, le versioni del pacchetto e delle librerie, l'hash
dell'input e lo SHA-256 di ogni output. Due esecuzioni identiche danno hash identici (verificato da
`python tools/gate.py`, che esegue i passi che il flusso di CI eseguiva: build, installazione pulita del wheel, la
suite, un'esecuzione di esempio ripetuta e un utente esterno). Ogni verifica di qualità parte dal solo repository:
lezioni calcolate a mano, identità algebriche esatte, casi sintetici con risposta costruita e l'esempio consegnato, che
è riproducibile byte per byte dai suoi parametri pubblicati (`tools/make_example_data.py --from-params`). Nessun test
dipende da dati fuori dal repository.

Il contratto [`CONTRATOS.md`](CONTRATOS.md) è il documento normativo dietro tutto questo: ciò che lo strumento promette
per input, catalogo, configurazione, output e riproducibilità — cinque contratti, ciascuno che chiude con la sua
giustificazione. Leggilo per sapere che cosa un numero di questo strumento afferma e che cosa non afferma.

## Sviluppo

```bash
pytest -q                   # suite intera, ~2 min, autocontenuta
python -m build && twine check dist/*
```

Un hook di pre-commit rifiuta i commit quando la suite rapida fallisce.
