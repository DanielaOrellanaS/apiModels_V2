//+------------------------------------------------------------------+
//| LEER_BALANCE_Y_LOTE.mq4                                           |
//| Lee el balance real de la cuenta y el valor real de un punto por  |
//| lote para cada simbolo -- para calcular el lote correcto segun    |
//| cuanto % de la cuenta se quiere arriesgar por operacion. No abre  |
//| nada, no modifica nada, solo lee e imprime.                       |
//+------------------------------------------------------------------+
#property copyright "Copyright (c) 2026"
#property version   "1.0"
#property strict
#property show_inputs

input string InpSimbolos = "NAS100,GER40,US30,BTCUSD";
input double InpRiesgoPct = 0.5;  // % de la cuenta a arriesgar por operacion (0.5 = medio por ciento)

void OnStart()
{
   double balance = AccountBalance();
   double equity  = AccountEquity();

   Print("==================================================================");
   Print("BALANCE Y LOTE SUGERIDO — ", TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES));
   Print("Balance: ", DoubleToStr(balance, 2), "   Equity: ", DoubleToStr(equity, 2));
   Print("Riesgo por operacion: ", InpRiesgoPct, "%  =  ", DoubleToStr(balance * InpRiesgoPct / 100.0, 2));
   Print("==================================================================");

   string simbolos[];
   int n = StringSplit(InpSimbolos, ',', simbolos);

   string archivo = "balance_lote_" + TimeToString(TimeCurrent(), TIME_DATE) + ".csv";
   StringReplace(archivo, ".", "-");
   int fh = FileOpen(archivo, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   bool puedeEscribir = (fh != INVALID_HANDLE);
   if(puedeEscribir)
      FileWrite(fh, "simbolo", "balance", "tick_value", "tick_size", "point",
                "valor_por_punto_por_lote", "lot_step", "min_lot");

   for(int i = 0; i < n; i++)
   {
      string sim = simbolos[i];
      StringTrimLeft(sim);
      StringTrimRight(sim);
      if(sim == "") continue;

      if(!SymbolSelect(sim, true))
      {
         Print(sim, ": ERROR — no se pudo seleccionar.");
         continue;
      }

      double tickValue = MarketInfo(sim, MODE_TICKVALUE);
      double tickSize  = MarketInfo(sim, MODE_TICKSIZE);
      double lotStep   = MarketInfo(sim, MODE_LOTSTEP);
      double minLot    = MarketInfo(sim, MODE_MINLOT);
      double point     = MarketInfo(sim, MODE_POINT);

      if(tickValue == 0 || tickSize == 0)
      {
         Print(sim, ": ERROR — tick_value/tick_size en 0, revisar el simbolo.");
         continue;
      }

      // valor de 1 PUNTO de precio, por 1 lote (no por 1 tick -- point puede ser
      // mas chico que tick_size en algunos brokers)
      double valorPorPuntoPorLote = (tickValue / tickSize) * point;

      double riesgoDinero = balance * InpRiesgoPct / 100.0;

      // ejemplo con un SL generico de 20 puntos, solo para mostrar la cuenta en
      // el log -- el CSV guarda los datos crudos, el lote real se calcula en Python
      double slEjemplo = 20.0;
      double loteEjemplo = riesgoDinero / (slEjemplo * valorPorPuntoPorLote);
      loteEjemplo = MathFloor(loteEjemplo / lotStep) * lotStep;
      if(loteEjemplo < minLot) loteEjemplo = minLot;

      Print(sim, "  tick_value=", DoubleToStr(tickValue, 4),
            "  tick_size=", DoubleToStr(tickSize, 5),
            "  valor_por_punto_por_lote=", DoubleToStr(valorPorPuntoPorLote, 4),
            "  |  con SL de ", slEjemplo, " puntos -> lote sugerido = ", DoubleToStr(loteEjemplo, 2));

      if(puedeEscribir)
         FileWrite(fh, sim, DoubleToStr(balance, 2), DoubleToStr(tickValue, 4), DoubleToStr(tickSize, 5),
                   DoubleToStr(point, 8), DoubleToStr(valorPorPuntoPorLote, 4),
                   DoubleToStr(lotStep, 2), DoubleToStr(minLot, 2));
   }

   if(puedeEscribir)
   {
      FileClose(fh);
      Print("\nGuardado tambien en MQL4/Files/", archivo);
   }
   Print("\nNOTA: el 'lote sugerido' de arriba es un EJEMPLO con SL=20 puntos, solo para");
   Print("ver el valor_por_punto_por_lote de cada simbolo. El lote real de cada señal hay");
   Print("que calcularlo con el SL de ESA señal en particular (varia por simbolo y lado --");
   Print("ver registry.json). El script de Python calcular_lote.py hace esa cuenta bien,");
   Print("usando estos valores.");
   Print("==================================================================");
}
