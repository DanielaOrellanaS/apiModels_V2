//+------------------------------------------------------------------+
//|                                              NEO_Bajar_VAGON     |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "NERO"
#property version   "2.00"
#property description "EXPORTAR_INDICADORES - reemplaza a NEO_WRFILE_TRANSFORMER"
#property description "Corrige 5 errores del original. Ver comentarios CORRECCION 1..5."
#property strict
//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+


int archivo = 0;
extern datetime fechadesde = D'2024-01-01 00:00:00';  // desde que fecha exportar
//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{

       int flag_alerta = 0;



      if(MessageBox("¿DUMP RSI???","ADVERTENCIA",1)==1)
      {
 //              notificacion("DOWNLOWING ...................");
   
      }
      else
      {
               return;
      }

 /*     
         string strl=     StringConcatenate("transformer_","1",".CSV");  // the FileOpen has the FILE_COMMON flag meaning it is saved to the Commong/Files folder.
         archivo = FileOpen (strl,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ );      
         string linea = "simbolo;timeframe;fecha; precioopen5;precioclose5;preciohigh5;preciolow5;volume5;precioopen15;precioclose15;preciohigh15;preciolow15;volume15;rsi5;rsi15;iStochaMain5;iStochaSign5;iStochaMain15;iStochaSign15;iBBs5;iBBi5;iBBs15;iBBi15;fill"; 
         FileWrite ( archivo, linea);
*/
      string ff = FormatDateTimeToCustomFormat2(TimeCurrent());  
   
      // string pairs[] = { "BTCUSD" ,"GER40" ,"NAS100","US30",/*"EURCHF", "USDCAD", "USDJPY","ETHUSD","DOGEUSD","SOLUSD","NAS100","US30","GER40","USDX"*/ };
      string pairs[] = {"BTCUSD","EURUSD", "GBPAUD","AUDCAD","GBPUSD", "AUDUSD",  "EURCHF", "USDCAD", "USDJPY","ETHUSD","DOGEUSD","SOLUSD","NAS100","US30","GER40","USDX" };
      for (int j = 0; j < ArraySize(pairs); j++)
      {
     
         string strl=     StringConcatenate("indicadores_",pairs[j],"_",ff,".CSV");  // the FileOpen has the FILE_COMMON flag meaning it is saved to the Commong/Files folder.
         archivo = FileOpen (strl,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ );      
         string linea = "simbolo;timeframe;fecha; precioopen5;precioclose5;preciohigh5;preciolow5;volume5;precioopen15;precioclose15;preciohigh15;preciolow15;volume15;rsi5;rsi15;iStochaMain5;iStochaSign5;iStochaMain15;iStochaSign15;iBBs5;iBBi5;iBBs15;iBBi15;";
                linea = linea +        "ema550;ema5200;ema50_prev;ema5200_prev;macdLine5;signalLine5;macdLine_prev5;signalLine_prev5;adx5;diPlus5;diMinus5;ema5015;ema20015;ema50_prev15;ema200_prev15;macdLine15;signalLine15;macdLine_prev15;signalLine_prev15;adx15;diPlus15;diMinus15;";
                linea = linea +         "atr5;atr15"; 
         FileWrite ( archivo, linea);
     
         consulta_tx(pairs[j]);

         FileClose(archivo);

         printf("OK "+ pairs[j]);

      }
//      FileClose(archivo);
      printf("OK");
      return;
}


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool consulta_tx(string simbolo)
  {


   
   string linea = "";
   int max_barra5  = iBarShift(simbolo, 5,fechadesde , false);
   int max_barra15 = iBarShift(simbolo, 15,fechadesde, false);
   
   int total = max_barra5;
   int barra  = 0; 
   int barra15 = 0; 
         

   
   // CORRECCION 1: se empieza en la vela 1. La vela 0 todavia esta en
   // formacion cuando se exporta, asi que sus indicadores estan a medio hacer.
   for(int j=1; j<= total -1; j++)
   {
                  barra = j;
                  datetime tmp_fecha = iTime(simbolo,5,barra);
                  // CORRECCION 2: FUGA DE FUTURO en todas las columnas de 15 min.
                  // Antes: iBarShift(simbolo,15,tmp_fecha) devolvia la vela de 15
                  // que CONTIENE a la de 5. En el historico esa vela ya esta
                  // cerrada, asi que para la vela de las 10:05 se guardaba el
                  // indicador de la vela 10:00-10:15, que incluye el precio hasta
                  // las 10:15. Diez minutos de futuro en cada fila.
                  // Ahora: la ultima vela de 15 ya cerrada al momento en que se
                  // consultaria en vivo, que es tmp_fecha + 5 minutos.
                  barra15 = iBarShift(simbolo,15,tmp_fecha + 300,false) + 1;
                  if(barra15 >= iBars(simbolo,15)) barra15 = iBars(simbolo,15) - 1;
                  if(barra15 < 0) continue;
                   
                  double rsi5= iRSI(simbolo,  5,  5, 0, barra) ; 
                  double rsi15= iRSI(simbolo, 15, 5, 0, barra15) ; 

                  double stchMain5 =     iStochastic(simbolo,5,13,3, 3, MODE_SMA,STO_LOWHIGH,MODE_MAIN,barra);          
                  double stchSig5 =      iStochastic(simbolo,5, 3,3, 3, MODE_SMA,STO_LOWHIGH,MODE_SIGNAL,barra);          
                           
                  double stchMain15 =    iStochastic(simbolo,15,13,3, 3, MODE_SMA,STO_LOWHIGH,MODE_MAIN,barra15);          
                  double stchSig15 =     iStochastic(simbolo,15, 3,3, 3, MODE_SMA,STO_LOWHIGH,MODE_SIGNAL,barra15);  
                  
                  double sBBs5  = iBands(simbolo,5, 20,1.4,0,PRICE_CLOSE,MODE_UPPER,barra);
                  double sBBi5  = iBands(simbolo,5, 20,1.4,0,PRICE_CLOSE,MODE_LOWER,barra);  
                  
                  double sBBs15 = iBands(simbolo,15,20,1.4,0,PRICE_CLOSE,MODE_UPPER,barra15);
                  double sBBi15 = iBands(simbolo,15,20,1.4,0,PRICE_CLOSE,MODE_LOWER,barra15);   
                     

                  double precioopen5   =  iOpen  (simbolo,5,barra); 
                  double precioclose5  =  iClose (simbolo,5,barra); 
                  double preciohigh5   =  iHigh  (simbolo,5,barra);   // CORRECCION 3: era iOpen
                  double preciolow5    =  iLow   (simbolo,5,barra);   // CORRECCION 3: era iClose
                  double vol5          =  (double)iVolume(simbolo,5,barra); 

                  double precioopen15  =  iOpen  (simbolo,15,barra15); 
                  double precioclose15 =  iClose (simbolo,15,barra15); 
                  double preciohigh15  =  iHigh  (simbolo,15,barra15);  // CORRECCION 3: era iOpen
                  double preciolow15   =  iLow   (simbolo,15,barra15);  // CORRECCION 3: era iClose
                  double vol15         =  (double)iVolume(simbolo,15,barra15);     
                  
                  //*******************************

                  
                  double ema550 =          iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, barra);
                  double ema5200 =         iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, barra);
                  double ema50_prev =      iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, barra+1);   // CORRECCION 4: era barra
                  double ema5200_prev =    iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, barra+1);  // CORRECCION 4
                  double macdLine5 =       iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra);
                  double signalLine5 =     iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra);
                  double macdLine_prev5 =  iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra+1);   // CORRECCION 4
                  double signalLine_prev5 =iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra+1); // CORRECCION 4
                  double adx5 =            iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MAIN, barra);
                  double diPlus5 =         iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_PLUSDI, barra);
                  double diMinus5 =        iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MINUSDI, barra);

                  double ema5015 =          iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, barra15);
                  double ema20015 =         iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, barra15);
                  double ema50_prev15 =     iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, barra15+1);  // CORRECCION 4
                  double ema200_prev15 =    iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, barra15+1); // CORRECCION 4
                  double macdLine15 =       iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra15);
                  double signalLine15 =     iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra15);
                  double macdLine_prev15 =  iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, barra15+1);   // CORRECCION 4
                  double signalLine_prev15 =iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, barra15+1); // CORRECCION 4
                  double adx15 =            iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MAIN, barra15);
                  double diPlus15 =         iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_PLUSDI, barra15);
                  double diMinus15 =        iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MINUSDI, barra15);

                  // CORRECCION 5: faltaba el ATR. Es con lo que se calculan el
                  // objetivo y el stop de cada operacion; sin el, el archivo no
                  // sirve para entrenar.
                  double atr5  = iATR(simbolo, 5, 14, barra);
                  double atr15 = iATR(simbolo, 15, 14, barra15);
                  
                  //*******************************              


            linea = 
                   simbolo                   +";"+
                   IntegerToString(5)      +";"+
                   TimeToStr( tmp_fecha)     +";"+

                   DoubleToStr(precioopen5)  +";"+
                   DoubleToStr(precioclose5) +";"+
                   DoubleToStr(preciohigh5)   +";"+
                   DoubleToStr(preciolow5)   +";"+
                   DoubleToStr(vol5)         +";"+

                   DoubleToStr(precioopen15)  +";"+
                   DoubleToStr(precioclose15) +";"+
                   DoubleToStr(preciohigh15)   +";"+
                   DoubleToStr(preciolow15)   +";"+
                   DoubleToStr(vol15)         +";"+

                   DoubleToStr(rsi5)            +";"+
                   DoubleToStr(rsi15)           +";"+

                   DoubleToStr(stchMain5)       +";"+
                   DoubleToStr(stchSig5)        +";"+
                   DoubleToStr(stchMain15)      +";"+
                   DoubleToStr(stchSig15)       +";"+                   

                   DoubleToStr(sBBs5)      +";"+
                   DoubleToStr(sBBi5)       +";"+    
                   DoubleToStr(sBBs15)      +";"+
                   DoubleToStr(sBBi15)       +";"+    
                   
                   //************************************

                    DoubleToStr( ema550)       +";"+ 
                    DoubleToStr( ema5200)       +";"+ 
                    DoubleToStr( ema50_prev)       +";"+  
                    DoubleToStr( ema5200_prev)       +";"+ 
                     DoubleToStr(macdLine5 )       +";"+ 
                    DoubleToStr( signalLine5)       +";"+ 
                    DoubleToStr( macdLine_prev5)       +";"+ 
                    DoubleToStr( signalLine_prev5)       +";"+  
                    DoubleToStr( adx5)       +";"+ 
                    DoubleToStr( diPlus5)       +";"+ 
                     DoubleToStr(diMinus5)       +";"+ 
                    DoubleToStr( ema5015)       +";"+ 
                    DoubleToStr( ema20015)       +";"+ 
                    DoubleToStr( ema50_prev15)       +";"+ 
                    DoubleToStr( ema200_prev15)       +";"+  
                    DoubleToStr( macdLine15)       +";"+ 
                    DoubleToStr( signalLine15)       +";"+  
                    DoubleToStr( macdLine_prev15)       +";"+  
                    DoubleToStr( signalLine_prev15)       +";"+  
                     DoubleToStr(adx15 )       +";"+ 
                     DoubleToStr(diPlus15)       +";"+ 
                    DoubleToStr( diMinus15)       +";"+   

//*****************                   
                   
                 
                   
                   
                   DoubleToStr(atr5)       +";"+
                   DoubleToStr(atr15)      ;
                   FileWrite ( archivo, linea);
            
         }
  return true;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
string FormatDateTimeToCustomFormat2(datetime dateTime)
{
    int year = TimeYear(dateTime);
    int month = TimeMonth(dateTime);
    int day = TimeDay(dateTime);
    int hour = TimeHour(dateTime);
    int minute = TimeMinute(dateTime);
    int second = TimeSeconds(dateTime);
    return StringFormat("%04d-%02d-%02d", year, month, day, hour, minute, second);
}
 		