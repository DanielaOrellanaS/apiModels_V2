//+------------------------------------------------------------------+
//| NEO_MINIMAL_V1.mq4                                               |
//| EA minimo: consulta la API nueva (ApiModels_v2) y opera SOLO con |
//| lo que ella responde. No usa Neo_OSC, no usa AUTOLOT, no llama a |
//| ninguna otra API. Una sola orden por vela, con el TP/SL real que |
//| la API calculo (multiplo de ATR del momento).                    |
//|                                                                    |
//| Por que existe: NEO_TRANSFORMER / NEO_TRANSFORMER_V2 tienen 9000+|
//| lineas con 3 sistemas de señales distintos conviviendo (Neo_OSC, |
//| una API en la nube ajena, y esta). Ninguno de los que abren      |
//| ordenes usa el modelo nuevo -- confirmado leyendo el codigo linea|
//| por linea. En vez de desenredar eso, este EA es la alternativa   |
//| limpia: se puede auditar entero en una sola lectura.             |
//+------------------------------------------------------------------+
#property copyright "Copyright (c) 2026"
#property version   "1.0"
#property strict

//===================================================================
// INPUTS -- todo lo que se puede tocar sin recompilar esta aca
//===================================================================
input string API_URL_BASE   = "http://127.0.0.1/";  // base de la API (sin /predict al final)
input double LoteFijo       = 0.01;                  // lote fijo, NO autolot
input int    MagicNumber    = 20260805;              // identifica las ordenes de ESTE EA
input int    Slippage       = 5;                     // en puntos, para el OrderSend
input int    Timeout        = 5000;                  // timeout del WebRequest, ms
input bool   PermitirBUY    = true;
input bool   PermitirSELL   = true;
input double UmbralMinimoTP = 0.0;   // filtro extra opcional: ignorar si tp<este valor (0 = sin filtro)

datetime g_ultima_vela_procesada = 0;
string   g_archivo_reportados;
int      g_reportados[];   // tickets ya avisados al servidor -- persistido en archivo

//+------------------------------------------------------------------+
int OnInit()
  {
   g_archivo_reportados = "reportados_" + Symbol() + "_" + IntegerToString(MagicNumber) + ".txt";
   CargarReportados();
   Print("NEO_MINIMAL_V1 inicializado. API=", API_URL_BASE,
         "  Simbolo=", Symbol(), "  Magic=", MagicNumber,
         "  (", ArraySize(g_reportados), " cierres ya reportados antes)");
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // Procesar UNA sola vez por vela nueva -- evita el bug del EA viejo
   // de pedir la misma vela 3-4 veces seguidas.
   datetime vela_actual = iTime(Symbol(), PERIOD_M5, 0);
   if(vela_actual == g_ultima_vela_procesada)
      return;
   g_ultima_vela_procesada = vela_actual;

   // Avisar al servidor de cualquier cierre nuevo -- corre siempre, haya o
   // no señal nueva esta vela. Es lo que alimenta /reporte_winrate.html.
   ReportarCierresNuevos();

   // No abrir una orden nueva si ya hay una de este EA abierta en este
   // simbolo -- una operacion por vez, sin apilar.
   if(HayOrdenAbiertaDeEsteEA())
      return;

   if(!IsTradeAllowed())
     {
      Print("AutoTrading no permitido -- no se puede operar.");
      return;
     }

   double valor_profit, tp, sl;
   string resultado;
   if(!ConsultarAPI(valor_profit, resultado, tp, sl))
      return;  // ConsultarAPI ya loguea el motivo del fallo

   if(resultado == "NADA")
      return;

   if(UmbralMinimoTP > 0 && tp < UmbralMinimoTP)
     {
      Print("Señal ", resultado, " con tp=", tp, " por debajo del umbral minimo ",
            UmbralMinimoTP, " -- se ignora.");
      return;
     }

   if(resultado == "BUY" && PermitirBUY)
      AbrirOrden(OP_BUY, tp, sl, valor_profit);
   else if(resultado == "SELL" && PermitirSELL)
      AbrirOrden(OP_SELL, tp, sl, valor_profit);
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
//| Recorre el historial de ESTE simbolo+magic, y avisa al servidor   |
//| (GET /registrar_cierre) cualquier operacion cerrada que todavia no|
//| se haya reportado. Asi el reporte de winrate es en vivo, sin      |
//| exportar nada a mano.                                             |
//+------------------------------------------------------------------+
void ReportarCierresNuevos()
  {
   int total = OrdersHistoryTotal();
   for(int i = 0; i < total; i++)
     {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != Symbol())
         continue;
      if(OrderType() != OP_BUY && OrderType() != OP_SELL)
         continue;

      int ticket = OrderTicket();
      if(YaReportado(ticket))
         continue;

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
                   + "&profit=" + DoubleToStr(OrderProfit(), 2);

      char data[], result[];
      string headers = "Content-Type: application/json";

      ResetLastError();
      int res = WebRequest("GET", url, NULL, NULL, Timeout, data, 0, result, headers);
      if(res == -1)
        {
         Print("FAIL reportar cierre ticket=", ticket, " error=", GetLastError(),
               " -- se reintenta la proxima vela");
         continue;
        }

      MarcarReportado(ticket);
      Print("OK cierre reportado: ticket=", ticket, " ", tipo, " profit=", OrderProfit());
     }
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
  }

bool YaReportado(int ticket)
  {
   for(int i = 0; i < ArraySize(g_reportados); i++)
      if(g_reportados[i] == ticket)
         return true;
   return false;
  }

void MarcarReportado(int ticket)
  {
   int n = ArraySize(g_reportados);
   ArrayResize(g_reportados, n + 1);
   g_reportados[n] = ticket;

   int fh = FileOpen(g_archivo_reportados, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
      return;
   FileSeek(fh, 0, SEEK_END);
   FileWrite(fh, ticket);
   FileClose(fh);
  }

//+------------------------------------------------------------------+
//| Llama a /predict con los mismos campos que ya se validaron en    |
//| NEO_TRANSFORMER_V2 -- misma foto de indicadores, un solo lugar.   |
//+------------------------------------------------------------------+
bool ConsultarAPI(double & valor_profit, string & resultado, double & tp, double & sl)
  {
   valor_profit = 0; resultado = "NADA"; tp = 0; sl = 0;

   string simbolo = Symbol();
   int barra = 0;  // vela actual recien cerrada/en formacion, igual que V2

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

   datetime fecha = TimeCurrent();
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
   char result[];
   string cookie = NULL;
   char postArray[];
   int length = StringToCharArray(post, postArray);

   ResetLastError();
   int res = WebRequest("GET", url, cookie, NULL, Timeout, postArray, length, result, headers);
   if(res == -1)
     {
      Print("FAIL WebRequest NEO_MINIMAL error ", GetLastError(), "  url=", url);
      return false;
     }

   string resultado_json = CharArrayToString(result);
   string vp = ExtraerCampoJSON(resultado_json, "valor_profit");
   string rs = ExtraerCampoJSON(resultado_json, "RESULTADO");
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
string ExtraerCampoJSON(string json, string campo)
  {
   string buscar = "\"" + campo + "\":";
   int pos = StringFind(json, buscar);
   if(pos < 0) return "";
   int inicio = pos + StringLen(buscar);
   int len = StringLen(json);
   bool esString = (inicio < len && StringGetCharacter(json, inicio) == '"');
   if(esString) inicio++;
   int fin = inicio;
   while(fin < len)
     {
      int ch = StringGetCharacter(json, fin);
      if(esString && ch == '"') break;
      if(!esString && (ch == ',' || ch == '}')) break;
      fin++;
     }
   return StringSubstr(json, inicio, fin - inicio);
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
   double precio_entrada, precio_tp, precio_sl;
   color flecha;
   string tipo_txt;

   if(tipo == OP_BUY)
     {
      precio_entrada = Ask;
      precio_tp = Ask + tp;
      precio_sl = Bid - sl;
      flecha = clrLime;
      tipo_txt = "BUY";
     }
   else
     {
      precio_entrada = Bid;
      precio_tp = Bid - tp;
      precio_sl = Ask + sl;
      flecha = clrRed;
      tipo_txt = "SELL";
     }

   string comentario = "NEO_MINIMAL prob=" + DoubleToStr(valor_profit, 4);
   int ticket = OrderSend(Symbol(), tipo, LoteFijo, precio_entrada, Slippage,
                          precio_sl, precio_tp, comentario, MagicNumber, 0, flecha);

   if(ticket < 0)
      Print("FAIL OrderSend ", tipo_txt, " error=", GetLastError(),
            "  precio=", precio_entrada, " tp=", precio_tp, " sl=", precio_sl);
   else
      Print("OK ", tipo_txt, " ticket=", ticket, "  precio=", precio_entrada,
            "  TP=", precio_tp, " (+", tp, ")  SL=", precio_sl, " (-", sl, ")",
            "  prob=", valor_profit);
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
