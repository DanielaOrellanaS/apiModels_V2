//+------------------------------------------------------------------+
//|                                                      ProjectName |
//|                                      Copyright 2018, CompanyName |
//|                                       http://www.companyname.net |
//+------------------------------------------------------------------+


#property copyright "Copyright © 2023, NEO Trading IA";
#property version "21.0";
#property description "EXPORTAR_MOVIMIENTOS - reemplaza a NEO_WRFILE_TRANSF_FRACTALES";
#property description "El original fechaba cada fila al INICIO del movimiento pero";
#property description "guardaba el precio del FINAL: era informacion del futuro.";
#property strict
#property description "Internal Use Only";

//+------------------------INCLUDE-----------------------------------+
#include <stdlib.mqh>
#include <stderror.mqh>
#define  OP_NA    -1

int MagicNumber = 404040;
extern double gap_ult_fractal = 150;  //parametro
extern double gap_max_fractal = 1000;  //parametro
extern int    quiebre_fractal = 2; // es el numero de fractales para cambio de tenedntencia

int archivo = 0;
extern datetime fecha_inicio = D'2024-01-01';
extern int timeframe = 5;

// ENTRENAMIENTO
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
int init()
{

   return (INIT_SUCCEEDED);
  }
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
int deinit()
  {
   return (INIT_SUCCEEDED);
  }
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
      string simbolo = "";
      double minimo = 0;
      int flag_alerta = 0;

      if(MessageBox("¿DUMP TX FRACTALES???","ADVERTENCIA",1)==1)
      {
 //              notificacion("DOWNLOWING ...................");
   
      }
      else
      {
               return;
      }


//      string pairs[] =         {"NAS100","US30",  "GER40" };
//      double pairsmin[] =      { 1000,    1000,     1000 };
//      double pipsconvert[] =   { 0.1 ,     0.1  ,   0.1 };
   
 /*
      string pairs[] =         { "BTCUSD",   "US30",  "GER40", "NAS100"};
      double pairsmin[] =      {    60000,      400,      600,   600 };
      double pipsconvert[] =   {    0.01 ,     0.1 ,      0.1,     0.1 };

*/
  
      string pairs[] =         {"BTCUSD","EURUSD", "AUDUSD", "GBPAUD", "GBPUSD","EURCHF", "USDCAD","USDJPY","ETHUSD","DOGEUSD","SOLUSD","NAS100","US30",  "GER40", "USDX", "AUDCAD" };
      double pairsmin[] =      { 60000,    50,       50,      50,       50,      50,      50,      5000,     1500,    1500   ,   1500,     1500,      1500,     1500,       1500,       50 };
      double pipsconvert[] =   { 0.01 ,  0.00001,   0.00001,0.00001 , 0.00001  ,0.00001     ,0.00001   , 0.1   ,  0.01    ,0.01   ,0.001   ,0.01  , 0.01   ,0.01  , 0.01 ,  0.00001};

      //string pairstotal[] =       {"GBPAUD", "GBPUSD", "EURUSD", "AUDUSD", "AUDCAD", "USDCAD", "NZDUSD", "USDJPY", "XAUUSD", "BTCUSD", "ETHUSD",  "NAS100", "US500", "GER40", "USDX"  };
      //double pipsconvert[] =        {0.00001 , 0.00001 , 0.00001 , 0.00001 , 0.00001 , 0.00001 , 0.00001 , 0.001   , 0.01    , 0.01    , 0.01    ,  0.1     , 0.1    , 0.1    , 0.001   };

/*
         string strl=     StringConcatenate("TX_","1",".CSV");  // the FileOpen has the FILE_COMMON flag meaning it is saved to the Commong/Files folder.
         archivo = FileOpen (strl,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ );      
         string linea = "simbolo;timeframe;fecha_confirmacion;fecha_inicio;fecha_fin;precio_inicio;precio_fin;movimiento;velas;direccion;minimo";
         FileWrite ( archivo, linea);
*/
      string ff = FormatDateTimeToCustomFormat2(TimeCurrent()); 
      
      for (int j = 0; j < ArraySize(pairs); j++)
      {
      
         simbolo = pairs[j];
         minimo =  pairsmin[j]*pipsconvert[j];

         string strl=     StringConcatenate("movimientos_",pairs[j],"_",ff,".CSV");  // the FileOpen has the FILE_COMMON flag meaning it is saved to the Commong/Files folder.
         archivo = FileOpen (strl,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ );      
         string linea = "simbolo;timeframe;fecha_confirmacion;fecha_inicio;fecha_fin;precio_inicio;precio_fin;movimiento;velas;direccion;minimo";
         FileWrite ( archivo, linea);
      
         bool b= print_fractales( simbolo,5,minimo,fecha_inicio );
         

         FileClose(archivo);

         printf("OK "+ pairs[j]);

      }
      FileClose(archivo);
      printf("OK");
      return;
}


//*******************************************************************************
//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//*******************************************************************************
//********************************************************************************

//*************************************************
//
//*************************************************
bool print_fractales( string simbolo, int periodoin,double minimo ,datetime fecha )
{
      int max  = 1000;
      bool respuesta = true;
      double pr1 = 0;
      double pr2 = 0;
      int bar1 = 0;
      int bar2 = 0;
      string sentido = ""; 
      double tope_altoin = 0;
      double tope_bajoin = 0;

      bar2= 1;
      int barfinal = iBarShift(simbolo, periodoin, fecha, false);                  

       primer_fractal ( simbolo, periodoin, pr2,bar2,sentido );


      int t= 0;

      int i = bar2;
      string linea3 = "";
      datetime fechahora_anterior = 0;
      do
      {
               bool resp = reverse_fractal (simbolo,periodoin,sentido,pr1,bar1,pr2,bar2  );
               if (!resp)
               {
                     return false;
               }
               int k = 0;
               datetime fechahora =  iTime(simbolo, periodoin,bar1);  
               datetime fechahorat = iTime(simbolo, periodoin,bar2); 
               double temp_pr1 = iClose(simbolo, periodoin,bar1);
               double temp_pr2 = iClose(simbolo, periodoin,bar2);
               

               string TX = "";
         
               if (sentido == "up") TX = "BUY";
               else  TX = "SELL";


               string linea = "";

               //--------------------------------------------------------------
               // CORRECCION PRINCIPAL: el original fechaba la fila en `fechahora`
               // (el INICIO del movimiento, bar1) pero guardaba temp_pr2, que es
               // el precio del FINAL (bar2, mas adelante en el tiempo).
               //
               // Comprobado sobre TX_GER40_2026-09-23.CSV: la columna `tipo`
               // coincidia con el signo del movimiento futuro en el 99.3% de las
               // 3652 filas. No era una señal: era la respuesta.
               //
               // Ademas iFractals solo confirma un fractal 2 velas DESPUES, asi
               // que ni siquiera bar2 se conoce en bar2.
               //
               // Ahora cada fila se fecha en el momento en que el movimiento
               // termino de confirmarse (2 velas despues de bar2). Ahi la fila
               // dice "acaba de completarse un movimiento de X puntos en Y
               // velas", que es un dato del PASADO y se puede usar sin trampa.
               // Se conservan tambien las fechas de inicio y fin, para poder
               // auditar.
               //--------------------------------------------------------------
               int bar_confirma = bar2 - 2;          // iFractals confirma 2 velas despues
               if(bar_confirma < 0)                  // todavia no confirmado: no se escribe
                 {
                  if (sentido == "up") sentido = "down"; else sentido = "up";
                  bar2 = bar1; pr2 = pr1; i = bar2; continue;
                 }
               datetime fecha_confirma = iTime(simbolo, periodoin, bar_confirma);

                   linea = 
                           simbolo+";"+
                           IntegerToString(periodoin)+";"+
                           FormatDateTimeMM(fecha_confirma)+";"+
                           FormatDateTimeMM(fechahora)+";"+
                           FormatDateTimeMM(fechahorat)+";"+
                           DoubleToStr(temp_pr1)+";"+
                           DoubleToStr(temp_pr2)+";"+
                           DoubleToStr(temp_pr2-temp_pr1)+";"+
                           IntegerToString(bar1-bar2)+";"+
                           TX+";"+
                           DoubleToStr(minimo)
 
                           ;
              
               if (MathAbs(temp_pr2-temp_pr1)> minimo )
               //***********************
               FileWrite(archivo,linea);
               //***********************               

               if (sentido == "up") sentido = "down";
               else  sentido = "up";
               bar2 = bar1  ;
               pr2 = pr1 ;
               
               i= bar2;
               linea3= linea;
         }  while(i<= barfinal);

return respuesta;
}


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
string FormatDateTimeMM(datetime dateTime)
  {
   int year = TimeYear(dateTime);
   int month = TimeMonth(dateTime);
   int day = TimeDay(dateTime);
   int hour = TimeHour(dateTime);
   int minute = TimeMinute(dateTime);
   int second = TimeSeconds(dateTime);

   return StringFormat("%04d.%02d.%02d %02d:%02d", year, month, day, hour, minute);
  }






//*************************************************
//
//*************************************************     

void primer_fractal (string simbolo, int periodoin,double & pr2, int & bar2, string & sentido )
{


sentido = "";
bool stop = false;
bool respuesta = false;
int max = 1000;
      
               int i = bar2;
               do{
                        double tmp_fractalup =       iFractals (simbolo,periodoin,MODE_UPPER,i );
                        double tmp_fractaldown =     iFractals (simbolo,periodoin,MODE_LOWER,i );
                        
                        if (tmp_fractalup != 0)
                        {
                            pr2 = tmp_fractalup;
                            bar2 = i;
                            sentido = "up";
                            respuesta = true;
                            break;
                        }
                        
                        if (tmp_fractaldown != 0)
                        {
                            stop = true; 
                            pr2 = tmp_fractaldown;
                            bar2 = i;
                            sentido = "down";
                            break;
                        }
           
                        i++;     
                  }while ((!stop) &&  (i< max));
 
//***************


return;
}

 


//*************************************************
//
//*************************************************     

bool reverse_fractal (string simbolo, int periodoin,string sentido,double & pr1, int & bar1, double pr2 ,int bar2  )
{
      int max = 10000000;

      double pr1_down =  0;
      double pr1_up  =   0;
      int    bar1_up = 0;
      int    bar1_down = 0;
      int i = bar2;      

      if (sentido=="up") // se usan los lower de creciendo
      {
               pr1_down     =   pr2;
               bar1_down    =   bar2;
               // Busca siguiente punto down

               i++;
               do{
                        double pr1_tmp  =   iFractals (simbolo,periodoin,MODE_LOWER,i );
                        if ( pr1_tmp != 0)
                        {
                              if (pr1_tmp <= pr1_down )  
                              {
                                 pr1_down = pr1_tmp;
                                 bar1_down = i;
                              }   
                              else
                                 break;  
                        }
                        i++;     
                  }while  (i< max);
      
                  if (bar1_down != bar2)
                  {
                           pr1  = pr1_down;
                           bar1 = bar1_down;
                  }
                  else
                  {
                           i++;
                           do{
                                    double pr1_tmp  =   iFractals (simbolo,periodoin,MODE_LOWER,i );
                                    if ( pr1_tmp != 0)
                                    {
                                          if (pr1_tmp <= pr1_down )  
                                          {
                                                   pr1_down = pr1_tmp;
                                                   bar1_down = i;
                                          }   
                                          else
                                          break;  
                                    }
                                    i++;     
                            }while  (i< max);
                            if (bar1_down != bar2)
                           {
                                    pr1  = pr1_down;
                                    bar1 = bar1_down;
                            }
                  
                  }
                  return true;
         }


     if (sentido=="down")
      {

               pr1_up = pr2;
               bar1_up = bar2;



               i++;
               do{
                        double pr1_tmp  =   iFractals (simbolo,periodoin,MODE_UPPER,i );
                        if (pr1_tmp != 0)   
                        {
                              if (pr1_tmp >= pr1_up )  
                              {
                                    pr1_up = pr1_tmp;
                                    bar1_up = i;
                              }
                              else
                                    break;
                        }
                        i++;     
                  }while  (i< max);
               //******************************* 
                  if(bar1_up != bar2)
                  {
                           pr1  = pr1_up;
                           bar1 = bar1_up;
                  }
                  else
                  {
                           // avanza un lowr mas
                           i++;
                           do{
                                    double pr1_tmp  =   iFractals (simbolo,periodoin,MODE_UPPER,i );
                                    if (pr1_tmp != 0)   
                                    {
                                             if (pr1_tmp >= pr1_up )  
                                             {
                                                   pr1_up = pr1_tmp;
                                                   bar1_up = i;
                                             }
                                             else
                                             break;
                                     }
                              i++;
                              }while  (i< max);
                              if(bar1_up != bar2)
                              {
                                    pr1  = pr1_up;
                                    bar1 = bar1_up;
                              }
                                    
                     

                    }

      }

     if (i>=max) 
     { 
            return false;
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
 		