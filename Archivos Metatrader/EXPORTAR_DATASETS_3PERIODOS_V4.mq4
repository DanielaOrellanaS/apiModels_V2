//+------------------------------------------------------------------+
//| EXPORTAR_DATASETS_3PERIODOS.mq4                                  |
//| Genera EN UNA SOLA PASADA los 3 datasets (train / holdout A /    |
//| holdout B) para el simbolo del grafico actual.                   |
//| No llama a la API: solo arma la URL exacta por barra M5.         |
//+------------------------------------------------------------------+
#property copyright "Copyright © 2026"
#property version   "4.0"
#property strict
#property show_inputs

//===================================================================
// INPUTS
//===================================================================
// V2 (05-ago-2026): en vez de fechas fijas, se reparte TODO el historial
// disponible por PORCENTAJE. Asi, cada vez que se corre el script usa lo
// ultimo que haya (HOLDOUT_B siempre llega hasta "hoy"), sin tener que
// tocar fechas a mano cada vez -- que era por lo que el log de agosto
// quedaba sin cobertura de precio con la version de fechas fijas.
input string   InpEtiq1     = "TRAIN";
input string   InpEtiq2     = "HOLDOUT_A_TPSL";
input string   InpEtiq3     = "HOLDOUT_B_CONFIRM";

input double   InpPctTrain  = 70.0;   // % del historial total (mas viejo)
input double   InpPctA      = 15.0;   // % siguiente (para elegir TP/SL)
// El resto (100 - PctTrain - PctA) es HOLDOUT_B_CONFIRM, y siempre llega
// hasta la barra mas reciente cargada -- ahi es donde entra el log real.

input string   InpBaseURL = "http://172.16.0.4:80/";

//===================================================================
#define NPER 3

string   g_etiq[NPER];
datetime g_ini[NPER];
datetime g_fin[NPER];
int      g_handle[NPER];
int      g_filas[NPER];
string   g_file[NPER];

//===================================================================
string FechaCorta(datetime t)   // "2025-01-01"
{
   return StringFormat("%04d-%02d-%02d", TimeYear(t), TimeMonth(t), TimeDay(t));
}

// El fin es exclusivo: para el nombre mostramos el ultimo dia incluido.
string FechaFinNombre(datetime t)
{
   return FechaCorta(t - 86400);
}

//===================================================================
void OnStart()
{
   string sim = Symbol();

   int totalBars = iBars(sim, PERIOD_M5);
   if(totalBars <= 0)
   {
      Print("ERROR: sin barras M5 para ", sim);
      return;
   }

   datetime primera = iTime(sim, PERIOD_M5, totalBars-1);
   datetime ultima  = iTime(sim, PERIOD_M5, 0);
   Print("Historial M5 disponible de ", sim, ": ",
         TimeToString(primera, TIME_DATE|TIME_MINUTES), "  ->  ",
         TimeToString(ultima,  TIME_DATE|TIME_MINUTES),
         "  (", totalBars, " barras)");

   if(InpPctTrain + InpPctA >= 100.0)
   {
      Print("ERROR: InpPctTrain + InpPctA tiene que ser menor a 100 (falta espacio para HOLDOUT_B).");
      return;
   }

   // Las barras estan indexadas de mas nueva (0) a mas vieja (totalBars-1).
   // Se cortan por indice de barra (no por dias de calendario) para
   // controlar el tamano real del dataset de train, sin que fines de
   // semana/feriados lo distorsionen.
   int n_train = (int)MathRound(totalBars * InpPctTrain / 100.0);
   int n_a     = (int)MathRound(totalBars * InpPctA     / 100.0);
   int n_b     = totalBars - n_train - n_a;   // el resto, absorbe el redondeo

   // Indices de barra (0=mas nueva) que delimitan cada tramo.
   int idxFinTrain = totalBars - n_train;         // primera barra que YA NO es train
   int idxFinA     = totalBars - n_train - n_a;   // primera barra que YA NO es A

   g_etiq[0] = InpEtiq1; g_ini[0] = primera;                             g_fin[0] = iTime(sim, PERIOD_M5, idxFinTrain);
   g_etiq[1] = InpEtiq2; g_ini[1] = iTime(sim, PERIOD_M5, idxFinTrain);  g_fin[1] = iTime(sim, PERIOD_M5, idxFinA);
   g_etiq[2] = InpEtiq3; g_ini[2] = iTime(sim, PERIOD_M5, idxFinA);      g_fin[2] = ultima + PeriodSeconds(PERIOD_M5);

   Print("Reparto: TRAIN ", n_train, " barras (", InpPctTrain, "%) | ",
         "HOLDOUT_A ", n_a, " barras (", InpPctA, "%) | ",
         "HOLDOUT_B ", n_b, " barras (", DoubleToStr(100.0 - InpPctTrain - InpPctA, 1), "%, llega hasta hoy)");

   // --- abrir los 3 archivos ---
   for(int p = 0; p < NPER; p++)
   {
      g_filas[p] = 0;

      if(g_ini[p] >= g_fin[p])
      {
         Print("AVISO: periodo ", g_etiq[p], " tiene rango invalido, se omite.");
         g_handle[p] = INVALID_HANDLE;
         continue;
      }

      g_file[p] = sim + "_" + g_etiq[p] + "_" +
                  FechaCorta(g_ini[p]) + "_al_" + FechaFinNombre(g_fin[p]) + "_M5.csv";

      g_handle[p] = FileOpen(g_file[p], FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
      if(g_handle[p] == INVALID_HANDLE)
      {
         Print("ERROR al crear ", g_file[p], " code=", GetLastError());
         continue;
      }
      FileWrite(g_handle[p], "fecha","periodo","symbol",
                "open","high","low","close","volumen","url");

      if(g_ini[p] < primera || g_fin[p] > ultima + PeriodSeconds(PERIOD_M5))
         Print("AVISO: el periodo ", g_etiq[p], " excede el historial cargado. ",
               "Subi 'Max bars in chart' y descarga M5+M15 antes de correr.");
   }

   // --- UNA SOLA pasada sobre las barras M5 ---
   for(int b = totalBars - 1; b >= 0; b--)
   {
      datetime t = iTime(sim, PERIOD_M5, b);

      int dest = -1;
      for(int p = 0; p < NPER; p++)
      {
         if(g_handle[p] == INVALID_HANDLE) continue;
         if(t >= g_ini[p] && t < g_fin[p]) { dest = p; break; }
      }
      if(dest < 0) continue;   // barra fuera de todos los periodos

      // Si los periodos se solapan (ej. holdout A y B comparten abril),
      // escribimos la barra en TODOS los que la contengan.
      for(int p2 = 0; p2 < NPER; p2++)
      {
         if(g_handle[p2] == INVALID_HANDLE) continue;
         if(!(t >= g_ini[p2] && t < g_fin[p2])) continue;

         string fecha = TimeToString(t, TIME_DATE|TIME_MINUTES);
         double o  = iOpen (sim, PERIOD_M5, b);
         double hh = iHigh (sim, PERIOD_M5, b);
         double ll = iLow  (sim, PERIOD_M5, b);
         double c  = iClose(sim, PERIOD_M5, b);
         long   v  = iVolume(sim, PERIOD_M5, b);

         FileWrite(g_handle[p2], fecha, g_etiq[p2], sim,
                   DoubleToStr(o,_Digits), DoubleToStr(hh,_Digits),
                   DoubleToStr(ll,_Digits), DoubleToStr(c,_Digits),
                   IntegerToString(v), ArmarURL(sim, b));
         g_filas[p2]++;
      }
   }

   // --- cerrar y reportar ---
   for(int p3 = 0; p3 < NPER; p3++)
   {
      if(g_handle[p3] == INVALID_HANDLE) continue;
      FileClose(g_handle[p3]);
      Print("OK ", g_file[p3], "  filas=", g_filas[p3]);
      if(g_filas[p3] == 0)
         Print("   >>> 0 filas: falta historial M5 en ese rango.");
   }
   Print("Listo. Archivos en MQL4/Files/");
}

//===================================================================
// ArmarURL: replica exacta del armado de consulta_score_transformer_v3
//===================================================================
string ArmarURL(string simbolo, int barra)
{
   datetime tmp_fecha = iTime(simbolo, PERIOD_M5, barra);

   //-----------------------------------------------------------------
   // V4 -- CORRECCION DE FUGA DE FUTURO EN LOS INDICADORES DE M15
   //
   // V3 hacia:  barra15 = iBarShift(simbolo, PERIOD_M15, tmp_fecha)
   // o sea la vela M15 que CONTIENE a la vela M5. Sobre historico esa
   // vela ya esta cerrada, asi que para la vela M5 de las 10:05 se
   // guardaba el indicador de la M15 de 10:00-10:15: incluia el precio
   // hasta las 10:15. Diez minutos de futuro metidos en la fila.
   //
   // El EA en vivo no puede hacer eso. Consulta al abrir la vela M5
   // siguiente (instante T), lee M5 con barra=1 (la vela [T-5,T) recien
   // cerrada) y M15 con barra=1 (la ULTIMA M15 completa antes de T).
   //
   //   vela M5 [10:00,10:05) -> consulta a las 10:05 -> M15 [09:45,10:00)
   //   vela M5 [10:10,10:15) -> consulta a las 10:15 -> M15 [10:00,10:15)
   //
   // Es decir: la ultima M15 cerrada al momento de la consulta, que es
   // tmp_fecha + 5 minutos. Se busca la M15 que contiene ese instante y
   // se retrocede una (en MT4 los indices mas altos son mas viejos).
   //
   // Comprobado con analisis\analizar.py --vivo: con V3, rsi15,
   // stoch_m15 y stoch_s15 eran las UNICAS 3 variables que no coincidian
   // con lo que recibe el EA; las 12 de M5 coincidian exacto.
   //-----------------------------------------------------------------
   int barra15 = iBarShift(simbolo, PERIOD_M15, tmp_fecha + 300, false) + 1;
   if(barra15 >= iBars(simbolo, PERIOD_M15))
      barra15 = iBars(simbolo, PERIOD_M15) - 1;

   double rsi5  = iRSI(simbolo, PERIOD_M5, 5, 0, barra);
   double rsi15 = iRSI(simbolo, PERIOD_M15, 5, 0, barra15);
   double atr5  = iATR(simbolo, PERIOD_M5, 14, barra);  // ATR REAL -- antes no se mandaba, core.py lo aproximaba

   double stchMain5  = iStochastic(simbolo, PERIOD_M5, 13, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_MAIN, barra);
   double stchSig5   = iStochastic(simbolo, PERIOD_M5, 3, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_SIGNAL, barra);
   double stchMain15 = iStochastic(simbolo, PERIOD_M15, 13, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_MAIN, barra15);
   double stchSig15  = iStochastic(simbolo, PERIOD_M15, 3, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_SIGNAL, barra15);

   double precioopen5  = iOpen(simbolo, PERIOD_M5, barra);
   double precioclose5 = iClose(simbolo, PERIOD_M5, barra);
   double preciohigh5  = iOpen(simbolo, PERIOD_M5, barra);
   double preciolow5   = iClose(simbolo, PERIOD_M5, barra);
   double vol5         = (double)iVolume(simbolo, PERIOD_M5, barra);

   double precioopen15  = iOpen(simbolo, PERIOD_M15, barra15);
   double precioclose15 = iClose(simbolo, PERIOD_M15, barra15);
   double preciohigh15  = iOpen(simbolo, PERIOD_M15, barra15);
   double preciolow15   = iClose(simbolo, PERIOD_M15, barra15);
   double vol15         = (double)iVolume(simbolo, PERIOD_M15, barra15);

   double ema550           = iMA(simbolo, PERIOD_M5, 50, 0, MODE_EMA, PRICE_CLOSE, barra);
   double ema5200          = iMA(simbolo, PERIOD_M5, 200, 0, MODE_EMA, PRICE_CLOSE, barra);
   double ema50_prev       = iMA(simbolo, PERIOD_M5, 50, 0, MODE_EMA, PRICE_CLOSE, barra + 1);
   double ema5200_prev     = iMA(simbolo, PERIOD_M5, 200, 0, MODE_EMA, PRICE_CLOSE, barra + 1);
   double macdLine5        = iMACD(simbolo, PERIOD_M5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra);
   double signalLine5      = iMACD(simbolo, PERIOD_M5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra);
   double macdLine_prev5   = iMACD(simbolo, PERIOD_M5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra + 1);
   double signalLine_prev5 = iMACD(simbolo, PERIOD_M5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra + 1);
   double adx5      = iADX(simbolo, PERIOD_M5, 14, PRICE_CLOSE, MODE_MAIN, barra);
   double diPlus5   = iADX(simbolo, PERIOD_M5, 14, PRICE_CLOSE, MODE_PLUSDI, barra);
   double diMinus5  = iADX(simbolo, PERIOD_M5, 14, PRICE_CLOSE, MODE_MINUSDI, barra);

   double ema5015           = iMA(simbolo, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE, barra);
   double ema20015          = iMA(simbolo, PERIOD_M15, 200, 0, MODE_EMA, PRICE_CLOSE, barra);
   double ema50_prev15      = iMA(simbolo, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE, barra + 1);
   double ema200_prev15     = iMA(simbolo, PERIOD_M15, 200, 0, MODE_EMA, PRICE_CLOSE, barra + 1);
   double macdLine15        = iMACD(simbolo, PERIOD_M15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra);
   double signalLine15      = iMACD(simbolo, PERIOD_M15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra);
   double macdLine_prev15   = iMACD(simbolo, PERIOD_M15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra + 1);
   double signalLine_prev15 = iMACD(simbolo, PERIOD_M15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra + 1);
   double adx15     = iADX(simbolo, PERIOD_M15, 14, PRICE_CLOSE, MODE_MAIN, barra);
   double diPlus15  = iADX(simbolo, PERIOD_M15, 14, PRICE_CLOSE, MODE_PLUSDI, barra);
   double diMinus15 = iADX(simbolo, PERIOD_M15, 14, PRICE_CLOSE, MODE_MINUSDI, barra);

   string fechas = StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
                                 TimeYear(tmp_fecha), TimeMonth(tmp_fecha), TimeDay(tmp_fecha),
                                 TimeHour(tmp_fecha), TimeMinute(tmp_fecha), TimeSeconds(tmp_fecha));

   string post = "";
   post = post + "predict?";
   post = post + "symbol=" + simbolo + "&";
   post = post + "fecha=" + fechas + "&";
   post = post + "o5="  + DoubleToStr(precioopen5)   + "&";
   post = post + "c5="  + DoubleToStr(precioclose5)  + "&";
   post = post + "c5d=" + DoubleToStr(precioclose5)  + "&";
   post = post + "h5="  + DoubleToStr(preciohigh5)   + "&";
   post = post + "l5="  + DoubleToStr(preciolow5)    + "&";
   post = post + "v5="  + DoubleToStr(vol5)          + "&";
   post = post + "o15=" + DoubleToStr(precioopen15)  + "&";
   post = post + "c15=" + DoubleToStr(precioclose15) + "&";
   post = post + "h15=" + DoubleToStr(preciohigh15)  + "&";
   post = post + "l15=" + DoubleToStr(preciolow15)   + "&";
   post = post + "v15=" + DoubleToStr(vol15)         + "&";
   post = post + "r5="  + DoubleToStr(rsi5)          + "&";
   post = post + "r15=" + DoubleToStr(rsi15)         + "&";
   post = post + "m5="  + DoubleToStr(stchMain5)     + "&";
   post = post + "s5="  + DoubleToStr(stchSig5)      + "&";
   post = post + "m15=" + DoubleToStr(stchMain15)    + "&";
   post = post + "s15=" + DoubleToStr(stchSig15)     + "&";
   post = post + "ema550=" + DoubleToStr(ema550) + "&";
   post = post + "ema5200=" + DoubleToStr(ema5200) + "&";
   post = post + "ema50_prev=" + DoubleToStr(ema50_prev) + "&";
   post = post + "ema5200_prev=" + DoubleToStr(ema5200_prev) + "&";
   post = post + "macdLine5=" + DoubleToStr(macdLine5) + "&";
   post = post + "signalLine5=" + DoubleToStr(signalLine5) + "&";
   post = post + "macdLine_prev5=" + DoubleToStr(macdLine_prev5) + "&";
   post = post + "signalLine_prev5=" + DoubleToStr(signalLine_prev5) + "&";
   post = post + "adx5=" + DoubleToStr(adx5) + "&";
   post = post + "diPlus5=" + DoubleToStr(diPlus5) + "&";
   post = post + "diMinus5=" + DoubleToStr(diMinus5) + "&";
   post = post + "atr5=" + DoubleToStr(atr5) + "&";
   post = post + "ema5015=" + DoubleToStr(ema5015) + "&";
   post = post + "ema20015=" + DoubleToStr(ema20015) + "&";
   post = post + "ema50_prev15=" + DoubleToStr(ema50_prev15) + "&";
   post = post + "ema200_prev15=" + DoubleToStr(ema200_prev15) + "&";
   post = post + "macdLine15=" + DoubleToStr(macdLine15) + "&";
   post = post + "signalLine15=" + DoubleToStr(signalLine15) + "&";
   post = post + "macdLine_prev15=" + DoubleToStr(macdLine_prev15) + "&";
   post = post + "signalLine_prev15=" + DoubleToStr(signalLine_prev15) + "&";
   post = post + "adx15=" + DoubleToStr(adx15) + "&";
   post = post + "diPlus15=" + DoubleToStr(diPlus15) + "&";
   post = post + "diMinus15=" + DoubleToStr(diMinus15);

   return InpBaseURL + post;
}
