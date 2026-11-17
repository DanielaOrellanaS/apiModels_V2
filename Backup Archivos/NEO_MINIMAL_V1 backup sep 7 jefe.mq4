//+------------------------------------------------------------------+
//| NEO_MINIMAL_V1.mq4                                               |
//| EA minimo: consulta la API nueva (ApiModels_v2) y opera SOLO con |
//| lo que ella responde. No usa Neo_OSC, no usa AUTOLOT por defecto,|
//| no llama a ninguna otra API. Una sola orden por vela, con el     |
//| TP/SL real que la API calculo (multiplo de ATR del momento).     |
//|                                                                    |
//| VERSION 1.1 -- correcciones previas:                              |
//|   1) Lote ajustado a LOTSTEP / MINLOT / MAXLOT (error 131).       |
//|   2) Validacion de margen libre antes del OrderSend (error 134).  |
//|   3) TP/SL normalizados a MODE_DIGITS y respetando STOPLEVEL.     |
//|   4) La vela ya no se "quema" si la API falla.                    |
//|                                                                    |
//| VERSION 1.2 -- correcciones de esta revision:                     |
//|   A) WebRequest ahora valida el CODIGO HTTP, no solo res==-1.     |
//|      Antes, un 500 del servidor marcaba el cierre como reportado  |
//|      y ese trade se perdia PARA SIEMPRE del winrate, en silencio. |
//|   B) El profit reportado ahora es NETO: profit + swap + comision. |
//|      Antes se mandaba el bruto y el winrate no era el real.       |
//|   C) La 'fecha' enviada a /predict es la de la vela M5 cerrada    |
//|      (barra 1), no TimeCurrent(). Antes el timestamp no           |
//|      correspondia a la foto de indicadores que lo acompanaba.     |
//|   D) Sizing opcional por riesgo: el SL viene de la API en precio  |
//|      y varia con ATR, asi que con lote fijo el riesgo en USD es   |
//|      distinto en cada trade. Ver ModoLote mas abajo.              |
//|      POR DEFECTO SIGUE EN LOTE FIJO: nada cambia si no lo tocas.  |
//|   E) ExtraerCampoJSON recorta espacios; " 0.0015" ya no rompe.    |
//|   F) ReportarCierresNuevos: busqueda binaria + una sola escritura |
//|      de archivo por vela, en vez de O(n*m) y un FileOpen por      |
//|      ticket.                                                      |
//+------------------------------------------------------------------+
#property copyright "Copyright (c) 2026"
#property version   "1.2"
#property strict

//===================================================================
// INPUTS -- todo lo que se puede tocar sin recompilar esta aca
//===================================================================
enum ENUM_MODO_LOTE
  {
   LOTE_FIJO    = 0,  // Siempre LoteFijo (riesgo en USD variable)
   LOTE_RIESGO  = 1,  // Calculado desde el SL para arriesgar RiesgoPorcentaje
  };

input string API_URL_BASE   = "http://127.0.0.1/";  // base de la API (sin /predict al final)

input ENUM_MODO_LOTE ModoLote = LOTE_FIJO;           // ver nota de sizing abajo
input double LoteFijo         = 0.01;                // usado si ModoLote = LOTE_FIJO
input double RiesgoPorcentaje = 0.5;                 // % del equity a arriesgar si LOTE_RIESGO
input double LoteMaximo       = 0.0;                 // tope duro al lote calculado (0 = sin tope)

input int    MagicNumber    = 20260805;              // identifica las ordenes de ESTE EA
input int    Slippage       = 5;                     // en puntos, para el OrderSend
input int    Timeout        = 5000;                  // timeout del WebRequest, ms
input bool   PermitirBUY    = true;
input bool   PermitirSELL   = true;

// OJO: este umbral esta en UNIDADES DE PRECIO, no en pips ni en puntos.
// Un valor que filtra bien en EURUSD (ej 0.0010) no significa nada en
// BTCUSD. Si operas varios simbolos, o lo dejas en 0 o pones un valor
// distinto por grafico.
input double UmbralMinimoTP = 0.0;   // ignorar senal si tp < este valor (0 = sin filtro)

// Vela en la que ya se reportaron los cierres al servidor.
datetime g_vela_reportada  = 0;
// Vela en la que ya se consulto la senal CON EXITO. Si la API falla no se
// marca, para poder reintentar en el proximo tick de la misma vela.
datetime g_vela_consultada = 0;

string   g_archivo_reportados;
int      g_reportados[];   // tickets ya avisados al servidor, ORDENADO ASC

//+------------------------------------------------------------------+
int OnInit()
  {
   g_archivo_reportados = "reportados_" + Symbol() + "_" + IntegerToString(MagicNumber) + ".txt";
   CargarReportados();

   Print("NEO_MINIMAL_V1 v1.2 inicializado. API=", API_URL_BASE,
         "  Simbolo=", Symbol(), "  Magic=", MagicNumber,
         "  (", ArraySize(g_reportados), " cierres ya reportados antes)");

   double minlot  = MarketInfo(Symbol(), MODE_MINLOT);
   double maxlot  = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotstep = MarketInfo(Symbol(), MODE_LOTSTEP);

   Print("Broker ", Symbol(),
         ": MINLOT=",    DoubleToStr(minlot, 4),
         " MAXLOT=",     DoubleToStr(maxlot, 2),
         " LOTSTEP=",    DoubleToStr(lotstep, 4),
         " STOPLEVEL=",  DoubleToStr(MarketInfo(Symbol(), MODE_STOPLEVEL), 0),
         " TICKVALUE=",  DoubleToStr(MarketInfo(Symbol(), MODE_TICKVALUE), 5),
         " TICKSIZE=",   DoubleToStr(MarketInfo(Symbol(), MODE_TICKSIZE), 8),
         " DIGITS=",     DoubleToStr(MarketInfo(Symbol(), MODE_DIGITS), 0));

   if(ModoLote == LOTE_FIJO)
     {
      double lote_real = AjustarVolumen(LoteFijo);
      Print("Sizing: LOTE FIJO = ", DoubleToStr(LoteFijo, 4),
            ". El riesgo en USD por operacion VARIA con el SL que devuelva la API.");
      if(MathAbs(lote_real - LoteFijo) > 0.0000001)
         Print("ATENCION: LoteFijo=", DoubleToStr(LoteFijo, 4),
               " no es valido en este broker. Se operara con ",
               DoubleToStr(lote_real, 4),
               " lotes. Revisa que la exposicion sea la que esperas.");
     }
   else
     {
      if(RiesgoPorcentaje <= 0)
        {
         Print("ERROR: ModoLote=LOTE_RIESGO pero RiesgoPorcentaje=", RiesgoPorcentaje,
               ". Corrige el parametro; el EA no abriria nada.");
         return(INIT_PARAMETERS_INCORRECT);
        }
      if(MarketInfo(Symbol(), MODE_TICKVALUE) <= 0 || MarketInfo(Symbol(), MODE_TICKSIZE) <= 0)
        {
         Print("ERROR: el broker reporta TICKVALUE/TICKSIZE invalidos para ", Symbol(),
               ". No se puede calcular lote por riesgo.");
         return(INIT_FAILED);
        }
      Print("Sizing: POR RIESGO = ", DoubleToStr(RiesgoPorcentaje, 2),
            "% del equity por operacion, calculado sobre el SL de la API.");
     }

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime vela_actual = iTime(Symbol(), PERIOD_M5, 0);

   // ---- Reporte de cierres: una vez por vela, pase lo que pase ----
   if(vela_actual != g_vela_reportada)
     {
      g_vela_reportada = vela_actual;
      ReportarCierresNuevos();
     }

   // ---- Consulta de senal: una vez por vela, pero solo se marca la vela
   //      cuando la API respondio de verdad.
   if(vela_actual == g_vela_consultada)
      return;

   if(HayOrdenAbiertaDeEsteEA())
      return;

   if(!IsTradeAllowed())
     {
      static datetime ultimo_aviso = 0;
      if(ultimo_aviso != vela_actual)
        {
         ultimo_aviso = vela_actual;
         Print("AutoTrading no permitido -- no se puede operar.");
        }
      return;
     }

   double valor_profit, tp, sl;
   string resultado;
   if(!ConsultarAPI(valor_profit, resultado, tp, sl))
      return;  // no se marca la vela: se reintenta en el proximo tick

   g_vela_consultada = vela_actual;

   if(resultado == "NADA")
      return;

   if(UmbralMinimoTP > 0 && tp < UmbralMinimoTP)
     {
      Print("Senal ", resultado, " con tp=", tp, " por debajo del umbral minimo ",
            UmbralMinimoTP, " -- se ignora.");
      return;
     }

   if(resultado == "BUY" && PermitirBUY)
      AbrirOrden(OP_BUY, tp, sl, valor_profit);
   else if(resultado == "SELL" && PermitirSELL)
      AbrirOrden(OP_SELL, tp, sl, valor_profit);
  }

//+------------------------------------------------------------------+
//| FIX A: un WebRequest que devuelve 500 NO es exito. Antes solo se  |
//| miraba res==-1 (error de transporte) y cualquier respuesta HTTP,  |
//| incluida una pagina de error, se trataba como valida.             |
//+------------------------------------------------------------------+
bool RespuestaHttpOK(int res)
  {
   return (res >= 200 && res < 300);
  }

//+------------------------------------------------------------------+
//| Formato de fecha comun para /predict y /registrar_cierre.         |
//+------------------------------------------------------------------+
string FormatearFechaISO(datetime t)
  {
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
                        TimeYear(t), TimeMonth(t), TimeDay(t),
                        TimeHour(t), TimeMinute(t), TimeSeconds(t));
  }

//+------------------------------------------------------------------+
//| Recorre el historial de ESTE simbolo+magic y avisa al servidor    |
//| (GET /registrar_cierre) cualquier operacion cerrada que todavia   |
//| no se haya reportado.                                             |
//|                                                                    |
//| FIX B: el profit enviado es NETO (profit + swap + comision).       |
//| FIX F: se acumulan los tickets nuevos y se escribe el archivo una  |
//| sola vez al final, en vez de un FileOpen por cada ticket.          |
//+------------------------------------------------------------------+
void ReportarCierresNuevos()
  {
   int nuevos[];
   ArrayResize(nuevos, 0);

   int total = OrdersHistoryTotal();
   for(int i = 0; i < total; i++)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != Symbol())
         continue;
      if(OrderType() != OP_BUY && OrderType() != OP_SELL)
         continue;
      if(OrderCloseTime() == 0)     // todavia abierta: no es un cierre
         continue;

      int ticket = OrderTicket();
      if(YaReportado(ticket))
         continue;

      // FIX B: resultado real de la operacion, no solo el movimiento de precio.
      double profit_bruto = OrderProfit();
      double swap         = OrderSwap();
      double comision     = OrderCommission();
      double profit_neto  = profit_bruto + swap + comision;

      string tipo = (OrderType() == OP_BUY) ? "BUY" : "SELL";
      string url = API_URL_BASE + "registrar_cierre?"
                   + "ticket=" + IntegerToString(ticket)
                   + "&symbol=" + Symbol()
                   + "&tipo=" + tipo
                   + "&fecha_apertura=" + FormatearFechaISO(OrderOpenTime())
                   + "&precio_apertura=" + DoubleToStr(OrderOpenPrice(), _Digits)
                   + "&fecha_cierre=" + FormatearFechaISO(OrderCloseTime())
                   + "&precio_cierre=" + DoubleToStr(OrderClosePrice(), _Digits)
                   + "&sl=" + DoubleToStr(OrderStopLoss(), _Digits)
                   + "&tp=" + DoubleToStr(OrderTakeProfit(), _Digits)
                   + "&profit=" + DoubleToStr(profit_neto, 2)
                   // Extras informativos. Si tu API valida parametros de forma
                   // estricta y los rechaza, borra estas tres lineas.
                   + "&profit_bruto=" + DoubleToStr(profit_bruto, 2)
                   + "&swap=" + DoubleToStr(swap, 2)
                   + "&comision=" + DoubleToStr(comision, 2);

      char data[], result[];
      string headers = "Content-Type: application/json";

      ResetLastError();
      int res = WebRequest("GET", url, NULL, NULL, Timeout, data, 0, result, headers);

      if(res == -1)
        {
         Print("FAIL reportar cierre ticket=", ticket, " error MT4=", GetLastError(),
               " -- se reintenta la proxima vela");
         continue;
        }

      // FIX A: sin esto, un 500 marcaba el ticket como reportado y el
      // cierre desaparecia del winrate sin dejar rastro.
      if(!RespuestaHttpOK(res))
        {
         Print("FAIL reportar cierre ticket=", ticket, " HTTP=", res,
               " body=", CharArrayToString(result),
               " -- NO se marca como reportado, se reintenta la proxima vela");
         continue;
        }

      int n = ArraySize(nuevos);
      ArrayResize(nuevos, n + 1);
      nuevos[n] = ticket;
      InsertarReportadoEnMemoria(ticket);

      Print("OK cierre reportado: ticket=", ticket, " ", tipo,
            " profit_neto=", DoubleToStr(profit_neto, 2),
            " (bruto=", DoubleToStr(profit_bruto, 2),
            " swap=", DoubleToStr(swap, 2),
            " com=", DoubleToStr(comision, 2), ")");
     }

   if(ArraySize(nuevos) > 0)
      PersistirReportados(nuevos);
  }

//+------------------------------------------------------------------+
void CargarReportados()
  {
   ArrayResize(g_reportados, 0);
   int fh = FileOpen(g_archivo_reportados, FILE_READ | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
      return;  // todavia no existe -- esta bien, es la primera vez
   while(!FileIsEnding(fh))
     {
      string linea = FileReadString(fh);
      if(StringLen(linea) == 0)
         continue;
      int n = ArraySize(g_reportados);
      ArrayResize(g_reportados, n + 1);
      g_reportados[n] = (int)StringToInteger(linea);
     }
   FileClose(fh);

   // FIX F: se ordena una vez al cargar para poder usar busqueda binaria.
   if(ArraySize(g_reportados) > 1)
      ArraySort(g_reportados);
  }

//+------------------------------------------------------------------+
//| FIX F: busqueda binaria en vez de recorrido lineal por cada ticket|
//+------------------------------------------------------------------+
bool YaReportado(int ticket)
  {
   int lo = 0;
   int hi = ArraySize(g_reportados) - 1;
   while(lo <= hi)
     {
      int mid = (lo + hi) / 2;
      if(g_reportados[mid] == ticket) return true;
      if(g_reportados[mid] <  ticket) lo = mid + 1;
      else                            hi = mid - 1;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Insercion manteniendo el array ordenado ascendente.               |
//+------------------------------------------------------------------+
void InsertarReportadoEnMemoria(int ticket)
  {
   int n = ArraySize(g_reportados);
   ArrayResize(g_reportados, n + 1);

   int i = n - 1;
   while(i >= 0 && g_reportados[i] > ticket)
     {
      g_reportados[i + 1] = g_reportados[i];
      i--;
     }
   g_reportados[i + 1] = ticket;
  }

//+------------------------------------------------------------------+
//| Un solo FileOpen por vela, no uno por ticket.                     |
//+------------------------------------------------------------------+
void PersistirReportados(int &tickets[])
  {
   int fh = FileOpen(g_archivo_reportados, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
     {
      Print("ATENCION: no se pudo abrir ", g_archivo_reportados,
            " (error ", GetLastError(), "). Estos cierres se volveran a reportar ",
            "tras reiniciar el EA: puede haber duplicados en el servidor.");
      return;
     }
   FileSeek(fh, 0, SEEK_END);
   for(int i = 0; i < ArraySize(tickets); i++)
      FileWrite(fh, tickets[i]);
   FileClose(fh);
  }

//+------------------------------------------------------------------+
//| Llama a /predict con la foto de indicadores de la vela M5 cerrada.|
//|                                                                    |
//| FIX C: 'fecha' ahora es el open time de la barra 1, la misma vela  |
//| de la que salen todos los indicadores. Antes iba TimeCurrent() y   |
//| el timestamp no correspondia a los datos que lo acompanaban.       |
//+------------------------------------------------------------------+
bool ConsultarAPI(double & valor_profit, string & resultado, double & tp, double & sl)
  {
   valor_profit = 0; resultado = "NADA"; tp = 0; sl = 0;

   string simbolo = Symbol();

   int barra = 1;  // vela M5 YA CERRADA -- es la que vio el modelo al entrenar

   double rsi5  = iRSI(simbolo, 5, 5, 0, barra);
   double rsi15 = iRSI(simbolo, 15, 5, 0, barra);
   double stchMain5  = iStochastic(simbolo, 5, 13, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_MAIN, barra);
   double stchSig5   = iStochastic(simbolo, 5, 3, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_SIGNAL, barra);
   double stchMain15 = iStochastic(simbolo, 15, 13, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_MAIN, barra);
   double stchSig15  = iStochastic(simbolo, 15, 3, 3, 3, MODE_SMA, STO_LOWHIGH, MODE_SIGNAL, barra);
   double precioclose5 = iClose(simbolo, 5, barra);
   double ema550  = iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, barra);
   double ema5200 = iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, barra);
   double macdLine5   = iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra);
   double signalLine5 = iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra);
   double adx5      = iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MAIN, barra);
   double diPlus5   = iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_PLUSDI, barra);
   double diMinus5  = iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MINUSDI, barra);
   double atr5      = iATR(simbolo, 5, 14, barra);

   // FIX C: misma vela que los indicadores.
   datetime fecha = iTime(simbolo, PERIOD_M5, barra);
   if(fecha == 0)
     {
      Print("FAIL: iTime devolvio 0 (historial M5 incompleto). No se consulta la API.");
      return false;
     }
   string fechas = FormatearFechaISO(fecha);

   string post = "predict?";
   post = post + "symbol=" + simbolo + "&";
   post = post + "fecha=" + fechas + "&";
   post = post + "c5=" + DoubleToStr(precioclose5) + "&";
   post = post + "ema550=" + DoubleToStr(ema550) + "&";
   post = post + "ema5200=" + DoubleToStr(ema5200) + "&";
   post = post + "macdLine5=" + DoubleToStr(macdLine5) + "&";
   post = post + "signalLine5=" + DoubleToStr(signalLine5) + "&";
   post = post + "adx5=" + DoubleToStr(adx5) + "&";
   post = post + "diPlus5=" + DoubleToStr(diPlus5) + "&";
   post = post + "diMinus5=" + DoubleToStr(diMinus5) + "&";
   post = post + "r5=" + DoubleToStr(rsi5) + "&";
   post = post + "r15=" + DoubleToStr(rsi15) + "&";
   post = post + "m5=" + DoubleToStr(stchMain5) + "&";
   post = post + "s5=" + DoubleToStr(stchSig5) + "&";
   post = post + "m15=" + DoubleToStr(stchMain15) + "&";
   post = post + "s15=" + DoubleToStr(stchSig15) + "&";
   post = post + "atr5=" + DoubleToStr(atr5);

   string url = API_URL_BASE + post;
   string headers = "Content-Type: application/json";
   char   result[];
   char   data[];              // GET: sin cuerpo
   string cookie = NULL;

   ResetLastError();
   int res = WebRequest("GET", url, cookie, NULL, Timeout, data, 0, result, headers);

   if(res == -1)
     {
      Print("FAIL WebRequest NEO_MINIMAL error MT4=", GetLastError(), "  url=", url);
      return false;
     }

   // FIX A
   if(!RespuestaHttpOK(res))
     {
      Print("FAIL /predict HTTP=", res, "  body=", CharArrayToString(result));
      return false;
     }

   string resultado_json = CharArrayToString(result);
   string vp  = ExtraerCampoJSON(resultado_json, "valor_profit");
   string rs  = ExtraerCampoJSON(resultado_json, "RESULTADO");
   string tpS = ExtraerCampoJSON(resultado_json, "tp");
   string slS = ExtraerCampoJSON(resultado_json, "sl");

   if(vp == "" || rs == "")
     {
      Print("FAIL parseo de respuesta: ", resultado_json);
      return false;
     }

   valor_profit = StrToDouble(vp);
   resultado = rs;
   tp = StrToDouble(tpS);
   sl = StrToDouble(slS);
   return true;
  }

//+------------------------------------------------------------------+
//| FIX E: se saltan espacios tras los dos puntos y se recorta el      |
//| final. Antes, {"tp": 0.0015} devolvia " 0.0015" con el espacio.    |
//+------------------------------------------------------------------+
string ExtraerCampoJSON(string json, string campo)
  {
   string buscar = "\"" + campo + "\":";
   int pos = StringFind(json, buscar);
   if(pos < 0) return "";

   int inicio = pos + StringLen(buscar);
   int len = StringLen(json);

   // saltar espacios / tabs entre ':' y el valor
   while(inicio < len)
     {
      int c = StringGetCharacter(json, inicio);
      if(c == ' ' || c == '\t' || c == '\n' || c == '\r') inicio++;
      else break;
     }
   if(inicio >= len) return "";

   bool esString = (StringGetCharacter(json, inicio) == '"');
   if(esString) inicio++;

   int fin = inicio;
   while(fin < len)
     {
      int ch = StringGetCharacter(json, fin);
      if(esString && ch == '"') break;
      if(!esString && (ch == ',' || ch == '}')) break;
      fin++;
     }

   string valor = StringSubstr(json, inicio, fin - inicio);
   valor = StringTrimLeft(valor);
   valor = StringTrimRight(valor);
   return valor;
  }

//+------------------------------------------------------------------+
//| Ajusta el volumen a lo que el broker acepta.                      |
//| Se usa MathRound, NO MathCeil: redondear siempre hacia arriba      |
//| infla el riesgo de forma silenciosa.                              |
//+------------------------------------------------------------------+
double AjustarVolumen(double volumen)
  {
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
   double minLot  = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot  = MarketInfo(Symbol(), MODE_MAXLOT);

   if(lotStep <= 0) lotStep = 0.01;
   if(minLot  <= 0) minLot  = lotStep;
   if(maxLot  <= 0) maxLot  = 100.0;

   double ajustado = MathRound(volumen / lotStep) * lotStep;

   if(ajustado < minLot) ajustado = minLot;
   if(ajustado > maxLot) ajustado = maxLot;

   // Decimales derivados del propio LOTSTEP, no hardcodeados.
   int dec = 0;
   double s = lotStep;
   while(s < 1.0 && dec < 8) { s *= 10.0; dec++; }

   return NormalizeDouble(ajustado, dec);
  }

//+------------------------------------------------------------------+
//| FIX D: lote derivado del SL real de la operacion.                 |
//|                                                                    |
//| perdida_por_lote = (distancia_SL_en_precio / TICKSIZE) * TICKVALUE |
//| lote             = (equity * riesgo%) / perdida_por_lote           |
//|                                                                    |
//| Devuelve -1 si el broker no da datos utiles; el llamador decide.   |
//+------------------------------------------------------------------+
double LotePorRiesgo(double distancia_sl_precio)
  {
   if(distancia_sl_precio <= 0) return -1;

   double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize  = MarketInfo(Symbol(), MODE_TICKSIZE);
   if(tickValue <= 0 || tickSize <= 0) return -1;

   double perdida_por_lote = (distancia_sl_precio / tickSize) * tickValue;
   if(perdida_por_lote <= 0) return -1;

   double riesgo_usd = AccountEquity() * (RiesgoPorcentaje / 100.0);
   if(riesgo_usd <= 0) return -1;

   return riesgo_usd / perdida_por_lote;
  }

//+------------------------------------------------------------------+
//| Distancia minima que exige el broker, expresada en PRECIO.        |
//| Causa numero 1 del error 130 (invalid stops).                     |
//+------------------------------------------------------------------+
double DistanciaMinima()
  {
   double punto  = MarketInfo(Symbol(), MODE_POINT);
   double sl_lvl = MarketInfo(Symbol(), MODE_STOPLEVEL)   * punto;
   double fz_lvl = MarketInfo(Symbol(), MODE_FREEZELEVEL) * punto;
   double spread = (Ask - Bid);

   double d = MathMax(MathMax(sl_lvl, fz_lvl), spread);
   if(d <= 0)
      d = 10 * punto;   // el broker reporta 0: colchon minimo

   return d * 1.10;     // 10% extra de margen
  }

//+------------------------------------------------------------------+
//| tp/sl vienen en unidades de precio DIRECTAS (mismas unidades que  |
//| close, ema550, etc. -- no son "puntos" de broker, no se multiplica|
//| por Point). Asi es como se calcularon en Python de punta a punta. |
//+------------------------------------------------------------------+
void AbrirOrden(int tipo, double tp, double sl, double valor_profit)
  {
   if(tp <= 0 || sl <= 0)
     {
      Print("tp/sl invalidos de la API (tp=", tp, " sl=", sl, ") -- no se abre nada.");
      return;
     }

   RefreshRates();

   int    dig  = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double dmin = DistanciaMinima();

   double precio_entrada, precio_tp, precio_sl;
   color flecha;
   string tipo_txt;

   if(tipo == OP_BUY)
     {
      precio_entrada = Ask;
      precio_tp = Ask + tp;
      precio_sl = Bid - sl;

      // Empujar los niveles fuera de la zona prohibida por el broker.
      if(precio_tp < Bid + dmin) precio_tp = Bid + dmin;
      if(precio_sl > Bid - dmin) precio_sl = Bid - dmin;

      flecha = clrLime;
      tipo_txt = "BUY";
     }
   else
     {
      precio_entrada = Bid;
      precio_tp = Bid - tp;
      precio_sl = Ask + sl;

      if(precio_tp > Ask - dmin) precio_tp = Ask - dmin;
      if(precio_sl < Ask + dmin) precio_sl = Ask + dmin;

      flecha = clrRed;
      tipo_txt = "SELL";
     }

   precio_entrada = NormalizeDouble(precio_entrada, dig);
   precio_tp      = NormalizeDouble(precio_tp,      dig);
   precio_sl      = NormalizeDouble(precio_sl,      dig);

   // Distancia de SL REAL, ya recortada por STOPLEVEL. Es la que hay que
   // usar para el sizing: si el broker movio el SL, el riesgo cambio.
   double dist_sl_real = MathAbs(precio_entrada - precio_sl);

   // ---- Sizing ----
   double lote_pedido = 0;

   if(ModoLote == LOTE_FIJO)
     {
      lote_pedido = LoteFijo;
     }
   else
     {
      lote_pedido = LotePorRiesgo(dist_sl_real);
      if(lote_pedido <= 0)
        {
         Print("FAIL sizing por riesgo (dist_sl=", DoubleToStr(dist_sl_real, dig),
               " tickvalue=", DoubleToStr(MarketInfo(Symbol(), MODE_TICKVALUE), 5),
               " ticksize=", DoubleToStr(MarketInfo(Symbol(), MODE_TICKSIZE), 8),
               ") -- no se abre nada.");
         return;
        }
     }

   if(LoteMaximo > 0 && lote_pedido > LoteMaximo)
     {
      Print("Lote recortado por LoteMaximo: pedido=", DoubleToStr(lote_pedido, 4),
            " tope=", DoubleToStr(LoteMaximo, 4));
      lote_pedido = LoteMaximo;
     }

   double lote = AjustarVolumen(lote_pedido);

   if(MathAbs(lote - lote_pedido) > 0.0000001)
      Print("Lote ajustado: pedido=", DoubleToStr(lote_pedido, 4),
            " enviado=",  DoubleToStr(lote, 4),
            "  (minlot=", DoubleToStr(MarketInfo(Symbol(), MODE_MINLOT), 4),
            " step=",     DoubleToStr(MarketInfo(Symbol(), MODE_LOTSTEP), 4),
            " maxlot=",   DoubleToStr(MarketInfo(Symbol(), MODE_MAXLOT), 2), ")");

   // Riesgo efectivo del lote que REALMENTE se va a enviar. Si MINLOT te
   // obligo a subir, esto lo dice en numeros en vez de que lo descubras
   // en el estado de cuenta.
   double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize  = MarketInfo(Symbol(), MODE_TICKSIZE);
   double riesgo_usd_real = 0;
   if(tickValue > 0 && tickSize > 0)
      riesgo_usd_real = (dist_sl_real / tickSize) * tickValue * lote;

   if(ModoLote == LOTE_RIESGO && riesgo_usd_real > 0)
     {
      double objetivo = AccountEquity() * (RiesgoPorcentaje / 100.0);
      if(riesgo_usd_real > objetivo * 1.20)
         Print("ATENCION: el lote minimo del broker fuerza un riesgo de ",
               DoubleToStr(riesgo_usd_real, 2), " USD, por encima del objetivo de ",
               DoubleToStr(objetivo, 2), " USD (", DoubleToStr(RiesgoPorcentaje, 2), "%).");
     }

   ResetLastError();
   double margen_libre = AccountFreeMarginCheck(Symbol(), tipo, lote);
   if(margen_libre <= 0 || GetLastError() == 134)
     {
      Print("FAIL margen insuficiente para ", DoubleToStr(lote, 4),
            " lotes  (free margin=", DoubleToStr(AccountFreeMargin(), 2),
            ") -- no se abre nada.");
      return;
     }

   string comentario = "NEO_MINIMAL prob=" + DoubleToStr(valor_profit, 4);
   int ticket = OrderSend(Symbol(), tipo, lote, precio_entrada, Slippage,
                          precio_sl, precio_tp, comentario, MagicNumber, 0, flecha);

   if(ticket < 0)
      Print("FAIL OrderSend ", tipo_txt, " error=", GetLastError(),
            "  lote=",   DoubleToStr(lote, 4),
            "  precio=", DoubleToStr(precio_entrada, dig),
            " tp=",      DoubleToStr(precio_tp, dig),
            " sl=",      DoubleToStr(precio_sl, dig),
            "  Bid=",    DoubleToStr(Bid, dig),
            " Ask=",     DoubleToStr(Ask, dig),
            " stoplevel=", DoubleToStr(MarketInfo(Symbol(), MODE_STOPLEVEL), 0));
   else
      Print("OK ", tipo_txt, " ticket=", ticket,
            "  lote=",   DoubleToStr(lote, 4),
            "  precio=", DoubleToStr(precio_entrada, dig),
            "  TP=",     DoubleToStr(precio_tp, dig), " (+", tp, ")",
            "  SL=",     DoubleToStr(precio_sl, dig), " (-", sl, ")",
            "  riesgo=", DoubleToStr(riesgo_usd_real, 2), " USD",
            "  prob=",   valor_profit);
  }

//+------------------------------------------------------------------+
bool HayOrdenAbiertaDeEsteEA()
  {
   for(int i = 0; i < OrdersTotal(); i++)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(OrderSymbol() == Symbol() && OrderMagicNumber() == MagicNumber)
         return true;
     }
   return false;
  }
//+------------------------------------------------------------------+