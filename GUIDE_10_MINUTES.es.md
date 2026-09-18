# BioMS Zaku en diez minutos

[English](GUIDE_10_MINUTES.md) · **Español** · [Português](GUIDE_10_MINUTES.pt.md) · [Italiano](GUIDE_10_MINUTES.it.md)

Usted tiene una planilla con bioimpedancia (R y Xc a 50 kHz), estatura, masa corporal y una medida de referencia, como masa
magra o masa grasa por DXA. Quiere saber cómo se comportan los índices publicados en sus datos, y quizá crear los suyos. Todo se
hace en el terminal, con un comando que lo conduce por preguntas. Nada se decide en silencio: cada respuesta queda escrita en un
archivo YAML, y el mismo análisis puede repetirse sin preguntas.

## 1. Instalar (una vez)

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang es
```

La segunda línea muestra el cartel y los tres comandos. Si apareció, está instalado.

## 2. Preparar la planilla

Un archivo `.csv` con una fila por persona y columnas numéricas para R, Xc, estatura, masa corporal y la referencia. El
separador y el decimal se detectan. Los nombres de columna son libres; Zaku sugiere el mapeo y usted lo confirma.

## 3. Ejecutar

```
bioms-zaku --lang es start datos.csv
```

En cualquier pregunta: **Enter** acepta la sugerencia entre [corchetes], **`<`** vuelve a la pregunta anterior, **`?`** repite la
ayuda, **`none`** rechaza una columna sugerida. Al final de cada pantalla aparece un resumen numerado y "¿corregir alguna línea?".

Lo que pregunta, en orden:

1. **idioma, nombre de los datos, investigador** — van al encabezado del informe y al registro de la ejecución;
2. **las columnas** — R, Xc, H, W y sus unidades; el **objetivo** (lo que los índices deberían predecir, medido por un método
   independiente); el **control negativo** (lo que NO deberían predecir, por ejemplo masa grasa cuando el objetivo es masa
   magra); covariables (masa y estatura, sugeridas); estrato (sexo) y etiquetas (`0=F,1=M`); identificador; columnas opcionales
   de sexo, edad y perímetros para los métodos que las usan; y la declaración de que objetivo y control **no fueron calculados**
   a partir de R, Xc, H, W;
3. **ejecución estándar** — el `check` verifica todo y Zaku ejecuta. La última línea dice dónde está el informe y cómo abrirlo.

Quien quiere solo eso, terminó aquí. Es el **uso estándar**.

4. **"¿quiere sugerencias de índices diseñados?"** — si dice `yes`, Zaku ajusta un índice al objetivo y otro al control, por
   estrato, usando el 70 % de las filas, y muestra cada uno: fórmula, R² en esas filas, el índice publicado más parecido, un
   nombre sugerido. Usted responde `yes`, `edit` (cambiar el nombre, redondear exponentes) o `no`. Ningún veredicto aparece
   antes de que usted decida, a propósito. Un exponente cambiado a mano se vuelve un índice **propuesto** (◇), no diseñado (△).
5. **"¿tiene un índice propio para probar?"** — escriba la fórmula en R, Xc, H, W (`H_m` estatura en metros, `PhA` ángulo de
   fase en grados, `mean(PhA)` media de la muestra). Se verifica en el momento sobre sus datos: cuántos valores finitos y
   positivos, mínimo, mediana, máximo; si es constante, no tiene valor auditable o es igual a un método publicado, usted lo sabe
   antes de aceptarlo.
6. **ejecución final** — solo si algo fue aceptado o propuesto: publicados + aceptados + los suyos, validados en el 30 % de
   filas que el diseño nunca vio.

## 4. Leer el informe

Abra `report.html` en el navegador (el comando está en la última línea del terminal). Orden de lectura:

- **Números clave**: personas auditadas, métodos, veredictos como sellos de color, cuántos agregan valor, si objetivo y control
  están acoplados en sus datos.
- **Ficha de veredictos** (una por estrato): cada método en tres columnas — original o repite un método anterior; específico,
  sigue al control, mide ambos o sin señal; agrega valor más allá de masa y estatura o no. ◇ = suyo; △ = diseñado.
- **Supuestos y umbrales**: cada procedimiento con el supuesto que lleva y su estado en esta ejecución; cada umbral con su
  valor, origen y sustento. Es donde un revisor comprueba que nada se improvisó.
- **Referencias**: las fuentes de los métodos evaluados y de los métodos estadísticos, con DOI.

Reglas de lectura que valen siempre: cada número describe **esta** muestra; un índice "repite" a otro solo en esta muestra y
para este objetivo; "útil" quiere decir que superó a masa y estatura solas.

## 5. Repetir, cambiar de idioma, otra base

```
bioms-zaku run datos.zaku.yaml               # el mismo análisis, sin preguntas, tablas idénticas byte a byte
bioms-zaku --lang en render zaku_out/datos   # el mismo informe en otro idioma, sin recalcular
bioms-zaku propose otra.zaku.yaml            # escribir un índice (por ejemplo, un vector diseñado aquí) para validarlo en otra base
```

Para validar un índice diseñado en otra base, copie el vector que aparece en el resumen (por ejemplo `R −0.49, Xc +0.11,
H +1.27, W +0.42`) y escríbalo en `propose` como `R**(-0.49) * Xc**(0.11) * H**(1.27) * W**(0.42)`.

## 6. Cuando algo sale mal

- **"no está en el archivo"**: nombre de columna con error de tipeo; la pregunta se repite con la lista.
- **"el control es el objetivo mismo"**: control y objetivo tienen que ser medidas distintas.
- **"dejaría ≈ N filas para auditar, por debajo de data.min_n"**: pocas personas por estrato para diseñar índices; use más filas
  o ejecute sin estrato. La ejecución estándar no se ve afectada.
- **"faltan las entradas [...]"**: un método del catálogo necesita una columna que usted no tiene (por ejemplo |Z| a 100 kHz);
  se omite y el informe lo dice.
- **Ctrl+C** termina sin escribir nada más.

## 7. Tres casos reales, y lo que enseñó cada uno (15/09/2026)

- **Muestra NHANES, 300 personas, objetivo masa magra por DXA.** Lukaski y R/H específicos en ambos sexos; Rsp y Xcsp siguen al
  control (son de grasa, y el informe lo dice). Lección: para **diseñar** índices por sexo hacen falta unas 185 personas por
  estrato; con menos, `start` bloquea las sugerencias antes de mostrarlas, porque la auditoría no tendría un bootstrap válido.
- **CrossFit, 107 hombres, objetivo grasa por pliegues, control perímetro del brazo corregido.** Rsp fue el único específico
  para grasa, exactamente lo que sus autores diseñaron. Los índices diseñados en NHANES para grasa se volvieron "mide ambos" en
  atletas: donde la masa extra es músculo, un índice casi igual a W²/H² lee músculo. Lección: la transferencia entre poblaciones
  se lee por la geometría (el coseno con el control) antes de cualquier veredicto.
- **Atletismo, 61 atletas, objetivo altura del salto, control tiempo de sprint.** Todo "sin señal", y el motivo apareció en un
  número: el coseno entre objetivo y control fue −0,98. Salto y sprint son la misma dirección en el espacio de la BIA. Lección:
  el control negativo tiene que ser un constructo **distinto** del objetivo; otra medida de rendimiento no sirve. El ángulo de
  fase fue el que más agregó sobre masa y estatura (+0,38), con un intervalo amplio.

## Datos de ejemplo y resultados que nunca se sobrescriben

Zaku trae **una** base de ejemplo, sintética, que sirve para todo:

```bash
bioms-zaku examples --copy     # copia a ./zaku_exemplos (si ya existe: zaku_exemplos_2, …)
cd zaku_exemplos
```

`zaku_exemplo.csv`: 400 personas (200 por sexo), sorteadas a partir de las medias y covarianzas de NHANES estimadas por separado
para cada combinación de sexo y diabetes; ninguna persona real. Lo que se puede probar con ella:

| prueba | objetivo | control | respuesta esperada |
|---|---|---|---|
| regresión | `LMI_DXA` | `FMI_DXA` | los índices de masa magra llevan el objetivo |
| clasificación con respuesta conocida | `label_synthetic` | `FMI_DXA` | **ningún** índice específico: la etiqueta depende solo de FMI y edad |
| diabetes | `diabetes` | `FMI_DXA` o `LMI_DXA` | pregunta abierta, como en un estudio real |

Use `-o` para dar nombre a cada prueba (`bioms-zaku start zaku_exemplo.csv -o regresion.yaml`). Las masas en kg (`lean_kg`,
`fat_kg`) se calculan a partir de la estatura: no las use como objetivo con la estatura mapeada. Archivos técnicos (ejemplo
antiguo de 8000 filas, formato de planilla, muestra real de NHANES): `bioms-zaku examples --all`.

Cada ejecución escribe en `zaku_out/<nombre>`; si la carpeta ya tiene una ejecución concluida, la nueva va a `<nombre>_2`,
`<nombre>_3`, … En `start`, la ejecución estándar y la final (con los índices aceptados) quedan en carpetas separadas. Nada se
sobrescribe.

## ¿Cuántas personas necesito?

Zaku describe su muestra y avisa cuando la regla queda corta; no estima una población. Los mínimos son operativos, y el informe
dice, en cada caso, qué fue posible calcular.

| lo que usted quiere | mínimo | por qué |
|---|---|---|
| ejecución estándar, objetivo continuo (p. ej. masa magra del DXA) | 30 personas por estrato | un ridge con un predictor y remuestras con ≥ 20 personas fuera de la bolsa |
| clasificación (p. ej. diabetes sí/no) | 20 personas en la clase menor, por estrato | por debajo de eso el bootstrap no tiene remuestra válida; entre 20 y ~32 el informe marca *eventos por variable < 10* y el veredicto es exploratorio |
| sugerencias de índices (diseño) | ≈ 185 personas por estrato | el 70 % va al diseño; el 30 % restante debe mantener ≥ 20 fuera de la bolsa |
| estratos (p. ej. por sexo) | cada estrato cumple los mínimos de arriba | si no, Zaku audita sin estrato o avisa |
| medidas repetidas de la misma persona (pre/post) | **una fila por persona** | agregue antes (media, o una visita); Zaku rechaza un `id` repetido en esta versión |

Con pocos datos, prefiera: sin estrato, sin sugerencias, objetivo continuo. Los veredictos salen con intervalos amplios, y el
informe lo dice; es información, no defecto.

## Clasificación con pocos casos y un segundo clasificador

El estimador principal de la clasificación es la regresión logística con penalidad L2: es el más estable cuando hay pocos
eventos. El informe calcula, para cada modelo, los **eventos por variable** de una remuestra de entrenamiento (`epv_train`) y
los marca por debajo de 10 (Peduzzi 1996): lea esos veredictos como exploratorios. El mínimo por clase sigue siendo 20; Zaku
describe su muestra y avisa cuando la regla queda corta, en lugar de rechazar.

Si quiere ver si el veredicto resiste a un clasificador de máquina (boosting), declárelo como **sensibilidad**: corre en las
mismas remuestras, sale al lado del principal y nunca se elige por el resultado:

```yaml
audit:
  sensitivity: {estimator: hgb, params: {max_depth: 3, learning_rate: 0.05, max_iter: 300}}
```

`xgboost` también se acepta si está instalado. El boosting necesita más datos que la logística, no menos: con unas pocas decenas
de eventos, espere ganancias inestables, y es exactamente eso lo que muestra la comparación lado a lado.
