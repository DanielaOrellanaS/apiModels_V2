# ApiModels_v2

Reconstrucción completa del pipeline de modelos de trading, partiendo de cero.
No confundir con `F:\ApiModels\` (proyecto anterior) — esta carpeta es
independiente. `F:\ApiModels\` sigue sirviendo en producción (GER40 en demo)
hasta que un modelo de acá pase `validar.py` y se lo active a propósito en
`registry.json`.

## Estructura

```
ApiModels_v2/
├── core.py          # features + etiquetado TP/SL — única fuente de verdad
├── entrenar.py       # (pendiente) datos -> modelo -> modelos/
├── validar.py         # (pendiente) LA comprobación única: holdout + baseline
│                       #   direccional + null por bloques + saturación +
│                       #   contraste contra logs reales
├── api.py             # (pendiente) servidor que responde a MetaTrader
├── registry.py        # gestor de registry.json — nunca elegir modelo por mtime
├── registry.json       # única fuente de verdad de qué versión corre
├── datos/
│   ├── crudos/         # CSV tal como salen de EXPORTAR_DATASETS_3PERIODOS.mq4
│   └── procesados/     # (si hace falta cachear features ya calculadas)
├── modelos/             # un .pt/.pkl + su scaler por version_id, nunca sueltos
└── reportes/            # salida de validar.py, un archivo por corrida
```

## Decisiones tomadas (05-ago-2026)

1. **Se descartó el bloque de 11 indicadores M15** que venían en el `url` de
   los CSV (`ema5015` ... `diMinus15`). Bug confirmado: usan el índice de
   vela M5 (`barra`) para pedir una vela de la serie M15, en vez de `barra15`.
   En el histórico da 0.0 en 99-100% de TRAIN. Contexto M15 ahora se
   recalcula en `core.py` por resample M5->M15 (evita el bug del todo, no
   depende de que se corrija el EA).
2. **Se descartaron `ema50_prev`/`ema5200_prev`** (M5): duplicados de
   `ema550`/`ema5200`, correlación ~0.99999.
3. **`ema550`/`ema5200` pasan a distancia relativa** (`close/ema - 1`) en vez
   de nivel absoluto — resuelve la saturación del normalizador cuando el
   precio sale del rango de entrenamiento.
4. **`macdLine5`/`signalLine5` pasan a relativos** (`/close`) por el mismo
   motivo — son diferencias de EMAs, están en unidades de precio.
5. **Se sacan `percentil_inf`/`percentil_sup`** del contrato de la API:
   siempre vienen `null` en producción, confirmado en el log real del
   4-ago-2026. No tenían uso.
6. **Target nuevo:** no es dirección a N velas fijas. Es "¿toca TP antes que
   SL?", simulado sobre high/low reales, BUY y SELL evaluados por separado.

## Pendiente de confirmar con el usuario

- **TP/SL/costo por símbolo.** Se usó 200/30/costo=3 para el test preliminar
  de NAS100 (mismo que GER40 documentado). Sin confirmar para NAS100 y US30.
- **Horizonte de resolución** (hoy 288 velas M5 = 1 día). Ajustable.
- **Criterio de fracaso en vivo**, a fijar ANTES de ver resultados (pendiente
  del resumen del 03-ago, sección 10.5).

## Resultado preliminar (NO es validación final)

Con las features nuevas + target TP/SL, NAS100 muestra AUC 0.58-0.64 (LogReg)
contra ruido ~0.50, consistente en HOLDOUT_A y HOLDOUT_B, BUY y SELL. Mejora
real sobre el ~0.52 que daban las features viejas. Falta: null corregido por
agrupamiento, baseline de dirección fija, backtest de PF con costo real —
eso es lo que hace `validar.py`, todavía no escrito.

## Actualización 05-ago-2026 (segunda parte)

- **Corrección importante:** las features de `core.py` se rediseñaron para
  salir de una sola foto de indicadores (los mismos campos que manda el EA
  por request), no de ventanas móviles sobre historial completo. La versión
  anterior de `core.py` calculaba features en entrenamiento que la API en
  producción no puede reproducir (no hay historial del lado del servidor).
  Se verificó que el AUC no cambia al corregir esto (0.583/0.639 antes y
  después en NAS100 BUY).
- **`api.py` escrito.** Contrato de respuesta: `valor_profit`, `RESULTADO`,
  `tp`, `sl` — 4 campos, nada más. `tp`/`sl` se sacan de la versión activa
  en `registry.json`, así el EA nunca hardcodea TakeProfit/StopLoss.
- **`NEO_TRANSFORMER_V2.mq4` creado** (copia de `NEO_TRANSFORMER.mq4`, el
  original queda intacto como fallback). Se tocó SOLO la función
  `consulta_score_transformer_v3`: request más chico (se sacaron los campos
  que no se usan), se agregó `atr5`, y ahora `TakeProfit`/`StopLoss` los
  fija la respuesta de la API en vez de estar hardcodeados por símbolo.
  Se verificó byte a byte que el resto del archivo (8.900 líneas) es
  idéntico al original.
- **Pendiente:** `entrenar.py` — hace el barrido de TP/SL como múltiplos de
  ATR (no puntos fijos), entrena, y registra el candidato.
