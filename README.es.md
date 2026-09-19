<p align="center"><img src="docs/assets/logo.svg" alt="BioMS Zaku" width="360"></p>

# BioMS Zaku

[English](README.md) · **Español** · [Português](README.pt.md) · [Italiano](README.it.md)

Descomposición algebraica y auditoría fuera de muestra de índices y ecuaciones predictivas. Demostrado en bioimpedancia.

*zaku* es un verbo de la lengua juruna (yudjá), familia tupí, Xingu, Mato Grosso, Brasil: "ver / cuidar / esperar"
(Lima, S. *A estrutura argumental dos verbos na língua Juruna (Yudjá)*, tesis de maestría, USP, 2008, ítem 290).
El método mira un índice antes de aceptarlo, cuida su validez y espera el resultado fuera de muestra.

## ¿Qué es esto?

Usted tiene una hoja de cálculo: una fila por persona, con resistencia y reactancia de un equipo de bioimpedancia,
estatura, masa corporal y una medida de referencia como DXA. BioMS Zaku mira los índices que usted está evaluando y responde
tres preguntas sobre cada uno. *¿Es nuevo*, o ya existe con otro nombre? *¿Mide lo que dice medir*, o está siguiendo el
tamaño corporal, como casi todo lo sigue? *¿Agrega algo* sobre la estatura y la masa corporal solas?

La segunda pregunta es la que importa. "Mi índice correlaciona con la masa magra" prueba poco: los individuos de mayor porte
tienen más de todos los tejidos. Por eso, antes de ver cualquier resultado, usted declara un objetivo y un **control
negativo**, y la herramienta prueba si el índice predice el objetivo *más allá* de lo que el control ya predice.
Cuando no lo hace, lo dice con claridad.

No necesita saber programar. En un terminal, `bioms-zaku start datos.csv` le hace las preguntas y registra sus respuestas;
en un notebook, usted lo abre y ejecuta todas las celdas, con los datos de ejemplo ya dentro. La salida es un solo archivo,
`report.html`: cada número, cada figura y, al lado de cada uno, cómo se calculó y cómo leerlo.

Estado: candidato a publicación (1.0.0rc1) · Licencia: MIT · Cita: `CITATION.cff` · **Lo que la herramienta garantiza, y bajo qué supuestos:** [`CONTRACTS.md`](CONTRACTS.md)

## Qué hace

1. **Descomposición.** Todo índice o ecuación se escribe como producto de potencias de las variables medidas y se
   representa por su **vector de exponentes**. La matriz de covarianza Σ de las variables en logaritmo, en una
   población, predice la correlación de Pearson de los logs entre dos índices cualesquiera *antes de calcular ninguno
   de los dos*: aᵀΣb / √(aᵀΣa · bᵀΣb), una identidad válida para cualquier distribución. La redundancia observada se
   mide con la correlación de rangos de Spearman (umbral 0,95) y la publicación más antigua conserva la precedencia.
   Los índices que no son productos exactos reciben un vector ajustado con el R² del ajuste.
2. **Control negativo condicional.** El investigador declara un objetivo y un control negativo. Sobre remuestras
   fuera de bolsa idénticas, el framework ajusta el control como predictor del objetivo con y sin el índice (ganancia
   S1) y el objetivo como predictor del control con y sin el índice (ganancia S2). Veredictos: *específico* (S1
   presente, S2 ausente), *sigue al control* (lo inverso), *mide ambos*, *sin señal*; una ganancia está presente cuando
   su media supera 0,03, su intervalo del 95 % excluye el 0 y P(d > 0) ≥ 0,95. Más el **valor agregado** sobre
   covariables básicas.
3. **Transferencia de Σ.** El Σ de un estrato aplicado a otro, reportado como error propio contra error transferido,
   exceso par a par con bootstrap de personas y la fracción de pares dentro de una tolerancia fija (nada de eso
   depende de n).
4. **Diseño (experimental).** Un índice nuevo se ajusta en una partición de diseño y se audita en una partición
   disjunta; exige la declaración de que el objetivo no se calcula a partir de las variables mapeadas.

Las salidas son tablas agregadas (precisión completa), un manifiesto (hashes, versiones, semillas), un resumen, cuatro
figuras (`lineage` árbol genealógico, `target_control` barras emparejadas, `exponents` + Σ, `scorecard`) y un
`report.html` de archivo único. Los datos por fila nunca salen de la ejecución. Las figuras aceptan
`figures: {title, subtitle, language: en|es|pt|it, palette, captions}`. Cómo leer cada figura: `docs/index.html`,
sección 3.

## Empiece aquí

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang es start datos.csv        # un camino guiado: columnas → ejecución estándar → sugerencias (aceptar/editar/no) → su propio índice → informe
```
`<` vuelve atrás, `?` repite la ayuda, Enter acepta la sugerencia. Todo lo que usted responde se escribe en
`datos.zaku.yaml`, así que `bioms-zaku run datos.zaku.yaml` repite el análisis sin preguntas. Guía de diez minutos:
[`GUIDE_10_MINUTES.es.md`](GUIDE_10_MINUTES.es.md).

**En un notebook (Colab o Jupyter)** no hay nada que descargar: `pip install bioms-zaku` trae los datos de ejemplo
dentro del paquete. `examples/zaku_exemplo.ipynb` instala, los carga y recorre los tres usos en cerca de un minuto — la
redundancia predicha por Σ antes de calcular ningún índice, la auditoría contra un control negativo y el informe.
`bioms-zaku examples --copy` copia el notebook junto con los datos.

## Instalar

```bash
pip install bioms-zaku            # después de la primera publicación; hasta entonces:
pip install -e ".[plots,dev]"     # desde un clon de este repositorio
```

Python ≥ 3.10. Dependencias: numpy, pandas, scipy, scikit-learn, pyyaml (+ matplotlib para las figuras).

## Datos de ejemplo

**Los datos de ejemplo** (nada se descarga; viajan con el paquete): UNA base sintética, `zaku_exemplo.csv`, 400 filas
(200 por sexo), extraídas de una log-normal cuyas medias y covarianzas se estimaron en NHANES 1999–2004 por separado
para cada celda sexo × diabetes diagnosticada por un médico — de modo que la asociación de la diabetes con cada
variable se conserva. Sirve para todos los usos: regresión (`LMI_DXA`, `FMI_DXA`, `ALMI_DXA`), clasificación con
respuesta conocida (`label_synthetic` depende solo de FMI y edad: con `FMI_DXA` como control, ningún índice debería
agregar) y `diabetes` (70 por sexo, enriquecido en casos a propósito). Parámetros y generador:
`examples/zaku_exemplo_params.json`, `tools/make_zaku_example.py` (reproduce el CSV byte a byte).

```bash
bioms-zaku examples --copy             # ./zaku_exemplos (una carpeta existente nunca se toca: _2, _3 …)
cd zaku_exemplos && bioms-zaku start zaku_exemplo.csv -o regresion.yaml
bioms-zaku examples --all              # también los archivos técnicos (ejemplo sintético antiguo de 8000 filas, formato de hoja de cálculo, una muestra real de NHANES)
```

```python
from bioms_zaku.api import load_example
df = load_example("zaku_exemplo")
```

`examples/example_data.csv` — 8 000 filas **sintéticas** (4 000 por sexo). Son extracciones de una log-normal multivariada
cuyo vector de medias y covarianza Σ de los logs se estimaron, por sexo, en una **muestra de conveniencia** de NHANES
1999–2004 (adultos de 18 a 49 años, DXA medido, BIA a 50 kHz; n = 2 792 mujeres, 3 036 hombres). Ninguna fila real se
reproduce; solo μ y Σ salieron de la fuente, y están publicados en `examples/example_data_params.json` (con la
asimetría y la curtosis de los logs de la fuente, para que la aproximación log-normal pueda juzgarse), junto con el
generador `tools/make_example_data.py` y su semilla. El archivo lleva R, Xc, estatura, masa corporal, edad, tres
perímetros, los índices de masa magra/apendicular/grasa por DXA y una etiqueta binaria sintética declarada. Úselo para
aprender el método, probar la herramienta y descomponer Σ a mano.

```bash
bioms-zaku run examples/example_quick.yaml      # 7 índices curados, preset quick, ~20 s
bioms-zaku run examples/example_full.yaml       # los mismos datos, preset full (CV 5×50, B = 2000), para reportar
bioms-zaku                                      # bienvenida: los tres comandos, en su idioma (--lang es)
bioms-zaku propose analisis.yaml                # agrega sus propios índices, una pregunta por vez (fórmula verificada en sus datos)
bioms-zaku run examples/minimal.yaml            # 150 filas, la ejecución más pequeña posible
ls zaku_out/example_quick                       # algebra sigma pairs redundancy sigma_transfer audit utility combinations screening sensitivity threshold_sensitivity (.csv) manifest.json summary.md report.html figures/
```

`examples/nhanes_diabetes_400.csv` — 400 filas **reales** de los archivos de uso público de NHANES 1999–2004 (CDC,
dominio público): adultos de 18 a 49 años con DXA medido y BIA a 50 kHz, casos completos, con la respuesta del
cuestionario de diabetes (`diabetes_1Y_0N` = diagnosticada por un médico). Es una **muestra de conveniencia enriquecida
en casos** — cada diabético diagnosticado con dato completo (139: 79 mujeres, 60 hombres) más un muestreo aleatorio con semilla de
no diabéticos — por lo tanto NO es representativa de la prevalencia; existe para demostrar la auditoría de
clasificación (≥ 20 por clase por sexo) y, con sus masas por DXA, la auditoría de regresión en datos reales.
Procedencia, exclusiones, semilla y SHA-256: `examples/nhanes_diabetes_400_provenance.json`; generador:
`tools/make_nhanes_example.py`. Los nombres de las columnas son los que el flujo guiado reconoce
(`bioms-zaku start examples/nhanes_diabetes_400.csv`). Este es el único ejemplo con filas reales; los otros son
sintéticos.

Las masas en kg se derivan de los índices y la estatura: no las use como objetivo mientras la estatura esté mapeada
(circularidad).

**Los resultados nunca se sobrescriben.** Una ejecución cuya carpeta ya contiene una ejecución terminada va a
`nombre_2`, `nombre_3`, …; la ejecución estándar y la final del flujo guiado caen, por lo tanto, en dos carpetas.
`output.overwrite: true` reemplaza en su lugar, y lo dice.

**¿Cuántas personas necesito?** 30 por estrato para un objetivo continuo; 20 en la clase menor para clasificación
(entre 20 y ~32 el informe señala *eventos por variable < 10* y el veredicto es exploratorio); cerca de 185 por estrato
para pedir índices diseñados; una fila por persona (agregue antes las medidas repetidas — los ids repetidos se rechazan
en esta versión).

El archivo también lleva `lean_kg`, `alm_kg`, `fat_kg` (índice × estatura², derivados, sin nueva extracción) para que las
masas absolutas puedan usarse como objetivo: `bioms-zaku run examples/example_kg.yaml`. Vea *Geometría* más abajo antes
de elegir.

Idioma: `bioms-zaku --lang es init …` (o `language: es` en el YAML; el `init` lo pregunta primero). en, es, pt, it.
Las preguntas, los mensajes de `check`/`run`, el `summary.md`, los títulos del informe y las figuras siguen el idioma;
los nombres de columna de los CSV y las claves del YAML permanecen en inglés.

Sus propios datos — tres comandos:

```bash
bioms-zaku init mis_datos.csv          # pregunta qué columna es R, Xc, H, W, objetivo, control y, opcionalmente, sexo, edad, perímetros de brazo/cintura/pantorrilla (sugiere, nunca adivina) → mis_datos.zaku.yaml
bioms-zaku check mis_datos.zaku.yaml   # valida datos + configuración SIN ejecutar: filas, clases, métodos, bootstrap, circularidad
bioms-zaku run   mis_datos.zaku.yaml   # el análisis
```

`init` no interactivo: `bioms-zaku init mis_datos.csv --map R=resistencia Xc=reactancia H=estatura W=masa_corporal target=lmi control=fmi independent=yes`,
agregando opcionalmente `strata=sexo id=sujeto age=edad arm=brazo waist=cintura calf=pantorrilla` para que las
ecuaciones del catálogo que necesitan sexo, edad o perímetros puedan evaluarse; el `check` lista cada método que no
puede evaluar y qué columna necesita. El YAML mapea columnas a papeles (ver `CONTRATOS.md` §1): `variables`
(R, Xc, H, W en la frecuencia declarada), `units`, `targets`, `controls`, y opcionalmente `covariates`, `strata`,
`groups`, `id` y `declarations.targets_independent_of_variables` (verdadero solo si ningún objetivo/control se calcula a
partir de las variables mapeadas — la regla de la circularidad).

```yaml
run_name: mi_estudio
data:
  path: mis_datos.csv
  columns:
    variables: {R: resistencia_ohm, Xc: reactancia_ohm, H: estatura_cm, W: masa_kg}
    units: {H: cm, W: kg}
    targets:  {LMI: indice_masa_magra}
    controls: {FMI: indice_masa_grasa}
    covariates: [masa_kg, estatura_cm]
strata: sexo
preset: full             # CV 5×50, B = 2000 (quick = 5×5, B = 200, solo para demostración)
```

## Reglas que el código impone

- todo fuera de muestra; todo contraste emparejado sobre remuestras idénticas; el remuestreo es función determinista de
  (filas, semilla, B, min_oob) — `n_jobs` nunca cambia un número;
- sin imputación por defecto (caso completo por método; caso completo de la unión para contrastes emparejados);
- estimador declarado antes de los datos (Ridge / logística para índices aislados; boosting para combinaciones);
  ninguna selección por resultado;
- expresiones del catálogo interpretadas por AST con lista blanca (sin `eval`); vectores del catálogo validados
  numéricamente; ejemplos numéricos publicados verificados al cargar; los métodos con transcripción inválida llevan
  `status: excluded` y nunca se evalúan;
- los veredictos son descriptivos (la P del bootstrap no es un valor p); umbrales fijados en los contratos;
- las salidas nunca contienen datos por fila (seguro de ejecutar dentro del entorno de un socio).

## Catálogo

Ocho índices públicos de bioimpedancia, cada uno reverificado en su fuente primaria
(`catalogo/fontes_primarias_indices/LEITURAS.md`): H²/|Z| a 100 kHz (Hoffer 1969), índice de impedancia H²/R
(Lukaski 1985), ángulo de fase de cuerpo entero (Baumgartner 1988), los componentes de la BIVA R/H y Xc/H
(Piccoli 1994), resistividad y reactividad específicas Rsp/Xcsp (Marini 2013; validados en NHANES por Buffa 2013) y el
LMI (Levi Micheli 2022); la razón de impedancia Z200/Z5 está listada con confianza baja (origen comercial, sin
artículo de derivación). Cada entrada registra la muestra de derivación por separado de la validez afirmada por los
autores (fuera de ella el framework señala †, nunca bloquea), el tipo declarado de objetivo (`target_kind`: un índice
de masa grasa auditado contra un objetivo de masa magra recibe un aviso de orientación) y cada evento de curaduría en
el `history` del catálogo. El ángulo de fase y el LMI contienen atan y son por lo tanto `composite`: su vector de
exponentes se ajusta por estrato y se reporta el R² del ajuste (regla de exactitud, `CONTRATOS.md` §2.3). **Solo las
entradas curadas se auditan por defecto** (`catalog.include: curated`, el valor que el `init` escribe): las ocho cuya
fuente primaria fue leída críticamente (`curated: true`, con `curation_record`). Las ecuaciones predictivas quedan en
el catálogo sin curaduría y se auditan solo con `catalog.include: all`, marcadas con * en toda salida.

## Probar su propio índice

Una fórmula suya entra en la auditoría al lado de los métodos publicados como entrada **propuesta**: sin DOI, nunca
curada, nunca con precedencia sobre un método publicado, marcada ◇ en toda tabla y figura. Se acepta cualquier
expresión en R, Xc, H, W (`+ - * / **`, `log`, `exp`, `sqrt`, `atan`, `max`, las constantes `pi` y `e`, y los
estadísticos de muestra `mean`, `median`, `sd`, cuyos valores se registran por estrato y se señalan); un producto puro
recibe un vector exacto, cualquier otra cosa un vector ajustado con su R². Los ocho índices BioMS del propio autor se
entregan así en `examples/bioms_mota_proposed.yaml`. Se audita solo cuando está listada en `catalog.include`:

```yaml
catalog:
  include: [curated, mi_indice]         # los métodos curados más el suyo; el valor por defecto (curated) nunca audita una propuesta
  user_entries:
    - id: mi_indice
      label: "H²·Xc/R (Mota, propuesta 2026)"
      authors: Mota
      target: lean_mass                  # lo que pretende medir
      expr: "H**2 * Xc / R"
      provenance: {formula_source: proposed, note: "hipótesis: la reactancia pondera el agua intracelular"}
```

No tiene que editar el YAML a mano: `bioms-zaku propose analisis.yaml` pregunta el id, el nombre, qué mide y la
fórmula, uno por vez; cada fórmula se verifica en el momento contra la gramática y se evalúa en sus datos (finita,
positiva, mínimo/mediana/máximo, estadísticos de muestra usados), y luego se escribe en el YAML y se incluye en la
auditoría.

El informe dice entonces si repite un índice publicado (redundancia), si es específico para el objetivo contra el
control, si agrega valor sobre las covariables y si está paralelo al control. `bioms-zaku check` avisa cuando una
propuesta se declara pero no se incluye.

## Diseñar su propio índice a partir de los datos

El `init` pregunta `design: none | target | control | both`. Para cada uno, los exponentes de R, Xc, H, W se ajustan a
ln(objetivo) por mínimos cuadrados en el 70 % de las filas (por estrato) y el índice se audita en el otro 30 %, nunca
visto, como cualquier método publicado (marcado △). Una propiedad registrada y probada hace de esta la forma correcta
de "limpiar la señal": el mejor predictor del objetivo es, por construcción, condicionalmente no informativo sobre la
proyección del control — así que el diseño simple es el índice específico en el sentido del control negativo
condicional, y la auditoría verifica si eso sobrevivió fuera de muestra. En el YAML, `design:` es una lista;
`orthogonal_to: <columna>` agrega Σ-ortogonalidad marginal a una columna molesta (tamaño corporal), lo cual es un
objetivo distinto y en general falla el control condicional (el informe lo dice).

## Geometría del objetivo y del control

Objetivo y control a menudo vienen de la misma medida de referencia y de la misma normalización (magra/H² y grasa/H²
de un mismo examen de DXA; magra + grasa + hueso = masa corporal, con H y W entre las variables mapeadas). En el
espacio de las variables mapeadas pueden apuntar casi en la misma dirección, y entonces un índice cercano a esa
dirección (del tipo W/H²) predice ambos por aritmética. El framework mide esto con el álgebra que ya usa: el *vector
implícito* de cada objetivo y control (MCO de los logs), los cosenos en Σ índice–objetivo, índice–control y
objetivo–control, y la identidad exacta r_log = cos_Σ·√R² para índices monomiales. Dos banderas con umbrales
declarados anotan los veredictos y nunca los cambian: PARALLEL_TO_CONTROL (‡ al lado del índice) y
COUPLED_TARGET_CONTROL (‡ en el título del panel). Tablas `implicit_vectors.csv` y `geometry.csv`; bloque en
`summary.md`. En el ejemplo entregado, el coseno objetivo–control es 0,90 (mujeres) y 0,86 (hombres) para LMI contra
FMI. Usar masas absolutas (kg) quita la estatura de ambos lados y baja el acoplamiento, pero no quita el acoplamiento
por la masa corporal, y hace el objetivo más "tamaño", lo que favorece los índices de volumen (H²/R): una elección
declarada, no una corrección. La lección 12 del cuaderno hace todo el asunto a mano con cuatro personas.

## El informe

`report.html` es la salida principal: un archivo único y autocontenido (figuras y tablas embebidas) que se abre desde
el disco. En un notebook, `run()` lo muestra inline. Cada bloque de resultado lleva tres párrafos fijos — *cómo se
calculó · cómo leerlo · rigor aplicado* — cuyos números (folds, repeticiones, B, márgenes, umbrales, semillas,
estimador) vienen de la configuración resuelta, nunca de texto fijo. Toda tabla tiene un botón de descarga en **CSV**
(embebido, funciona sin conexión); `pip install bioms-zaku[excel]` agrega `tables.xlsx` (una hoja por tabla) al lado
del informe. Una sección *Rigor de esta ejecución* lista preset, semillas, versiones, hash de la entrada, el SHA-256 de
cada tabla de salida, tiempo de reloj y avisos. El informe no recalcula nada — y por eso
`bioms-zaku --lang en render zaku_out/mi_ejecucion` reescribe resumen, figuras e informe de una ejecución terminada en
otro idioma en segundos, dejando tablas y manifiesto intactos.

El informe abre con un índice fijo y el **diagrama del método Zaku** (también guardado como
`figures/zaku_method.svg`), muestra números clave leídos de las tablas, agrupa figuras por familia y los bloques de
resultado en acordeón (uno abierto a la vez), y termina con una sección de **Referencias**: las fuentes de
bioimpedancia de los métodos evaluados en la ejecución, los antecedentes estadísticos y algebraicos (índices de razón,
escalamiento alométrico, controles negativos, ridge, validación cruzada, bootstrap, combinaciones) etiquetados por
bloque de resultado, y el software ejecutado. Todo registro viene de metadatos de Crossref verificados el 15/09/2026
(`references.py`); nada se carga de la red cuando el informe se abre.

## Reproducibilidad

El `manifest.json` registra la configuración resuelta, las semillas, las versiones del paquete y de las bibliotecas, el
hash de la entrada y el SHA-256 de cada salida. Dos ejecuciones idénticas dan hashes idénticos (verificado por
`python tools/gate.py`, que corre los pasos que el flujo de CI corría: build, instalación limpia del wheel, la suite,
una ejecución de ejemplo repetida y un usuario externo). Toda verificación de calidad corre desde el repositorio solo:
lecciones calculadas a mano, identidades algebraicas exactas, casos sintéticos con respuesta construida y el ejemplo
entregado, que es reproducible byte a byte desde sus parámetros publicados (`tools/make_example_data.py --from-params`).
Ninguna prueba depende de datos fuera del repositorio.

El contrato [`CONTRACTS.md`](CONTRACTS.md) es el documento normativo detrás de todo esto: lo que la herramienta promete
para entrada, catálogo, configuración, salidas y reproducibilidad — cinco contratos, cada uno cerrando con su
justificación. Léalo para saber qué afirma y qué no afirma un número de esta herramienta.

## Desarrollo

```bash
pytest -q                   # suite completa, ~2 min, autocontenida
python -m build && twine check dist/*
```

Un hook de pre-commit rechaza los commits cuando la suite rápida falla.
