//+------------------------------------------------------------------+
//|                                                      ProjectName |
//|                                      Copyright 2018, CompanyName |
//|                                       http://www.companyname.net |
//+------------------------------------------------------------------+
#property copyright "Copyright © 2023, NEO Trading IA";
#property version "10.0";
#property strict
#property description "Internal Use Only";

//+------------------------INCLUDE-----------------------------------+
#include <stdlib.mqh>
#include <stderror.mqh>
#define CPBuy     0
#define CPSell    1

#define  OP_NA    -1

enum ENUM_TYPE_ORDER
  {
   BUY=OP_BUY,
   SELL=OP_SELL,
   AMBAS=6,
  };

extern double StartingLots       = 1;  //parametro
extern double MinLots            = 0.1;  //parametro
extern int    Max_vagones        = 1   ;
extern double Propocion_Lote     = 5 ; // parametro para AUTOLOT
extern double Proporcion_Balance = 50000 ;//  // parametro para AUTOLOT
extern double factor             = 1.2;;  //parametro
extern double gap                = 100;  //parametro
extern double gap_ult_fractal    = 150;  //parametro
extern double gap_max_fractal    = 1000;  //parametro
extern int    quiebre_fractal    = 2; // es el numero de fractales para cambio de tenedntencia
extern int    quiebres_seguidos  = 1; // es el numero de fractales para cambio de tenedntencia
extern double gap_max_dia        = 1000;  //parametro

extern bool   flag_BUY = true;
extern bool   flag_SELL = true;

extern double TakeProfit     = 40;  ;  //parametro
extern double StopLoss       = 0;  ;  //parametro // parametro
extern bool   flag_score_modelo = false;
extern bool   flag_riesgo_externo = false;
extern double porcentaje_bonus   = 0;

extern double   lim_rsi_inferior  = 30;
extern double   lim_rsi_superior  = 70;
extern double   lim_indicador_inferior  = 20;
extern double   lim_indicador_superior  = 80;
extern double   lim_rsi_inferior_minimo  = 36;
extern double   lim_rsi_superior_minimo  = 56;
extern string   modeloTP = "Largo";
extern double   saltogap = 0.5;
extern double   max_atr = 0.0001;
extern double   min_atr = 0.0005;
extern double   factor_atr_tpsl = 1;
extern string   tipo_generacion_tpsl  = "atr";
extern string   tipo_generacion_lotes = "proyeccion";



extern int      timeframeIndicador = 15;
extern double   factor_lote_indicador = 1;
extern double   factor_lote_indicador_duro = 1;
extern int      MagicNumber = 22;;  //parametro

extern bool     Flag_Autolot = true;
extern string   EAName = "Trail ";  //parametro
extern int      modelo = 1; //parametro  2 = Pholosofical    1= TRAIL

extern string   txt_score = "";

extern bool     flag_recover_close = false;
extern double   lote_recover = 0;
extern int      timeout = 120000;

extern double   max_perdida_cuenta =   0.09;  // perdida máxima
extern double   apetito_risk = 0.5;
extern double   pips_max_riesgo = 80;
extern bool     flag_alerta_evento = false;
extern int hora_open = 7;
extern int hora_close= 20;
double PointVal = _Point ;

extern int tipo_transformer = 1; // 0 version anterior, 1 nueva version con dif
int flag_trace = 0;   // 0 sin trace   1   Buy    -1 SELL
bool trace_url = true;

int time_no_proceso =  10;  // tiempo en minutos
datetime fecha_cronos = 0;
long     timebar;


int    flag_alerta= 0;
int    horario_especial = 0;
int    time_antes_evento = 60; // tiempo de consulta antes del evento.
int    time_despues_del_evento = 2*60;  // espacio de tiempos de laa consulta

// Generico

datetime fecha_datos_limites = 0;
datetime fecha_banda_anterior = 0;
datetime fecha_datos_alertas = 0;

datetime fecha_risk = 0;
double   risky = 0;

double  limite_compra_out = 0;
double  limite_venta_out = 0;
double  score_glob = 0;
int     tipo_zona = 0;
int     tipo_zona_anterior = 0;
int     tipo_accion_buy = 0;
int     tipo_accion_sell = 0;
double   informacionmarket;
datetime fecha_hora_monitoreo = 0;
double   sumatoria_lotes_inversa = 0;

double   Id_00050 = 5000; //Es unsado para sumar al precio y calcular el TP  ;  //parametro
double   Id_00058 = 100; // usado para stop loss  ;  //parametro
double   Id_00060 = 100; // usado para stop loss;  //parametro
bool     Ib_00080 = false;;  //parametro
double   Id_00088 = 30; // sleeppage para la crwacion de una orde,;  //parametro
int      max_cola = 99999;;  //parametro
int      Digitos = 2; // digitos para normalizar;  //parametro
string   Is_00098 = "AutoLot";;  //parametro
double   Id_000A8 = 0.02;  // para dividi con 10000;  //parametro
double   Id_000B0 = 10000; // para sacar la precion de 02/10000;  //parametro
double   Id_000C0 = 20;     // Si el valor absoluto del profit es mayor que el 20% del equity;  //parametro
double   Id_000D0 = 48;  // parece ser usado de un tiempo en hpras, no en esta version //parametro
double   limite_venta= 0;
double   limite_compra= 0;
//+--------------------VARIABLES EXTERNAS----------------------------+
//+------------------------------------------------------------------+
bool               PopupAlert      = false;       //Mensaje alerta
bool               PushAlert       = false;       //Mensaje al móvil
//+--------------------VARIABLES GLOBALES----------------------------+
//+------------------------------------------------------------------+
string btClose;
string btClosesymbol;
string gsLog;
double Ind_000;
double Id_00120;
int    returned_i;
int    Gi_00000;
double Gd_00001;
int Gi_00002;
int Gi_00003;
int Gi_00004;
int Gi_00005;
int Gi_00006;
double Gd_00007;
int Gi_00008;
int Gi_00009;
int Gi_0000A;
double Gd_0000B;
int Gi_0000C;
int Gi_0000D;
int Gi_0000E;
double Gd_0000F;
int Gi_00010;
int Gi_00011;
int Gi_00012;
double Gd_00013;
int Gi_00014;
int Gi_00015;
int Gi_00016;
double Gd_00017;
int Gi_00018;
int Gi_00019;
int Gi_0001A;
double Gd_0001B;
int Gi_0001C;
int Gi_0001D;
int Gi_0001E;
double Gd_0001F;
int Gi_00020;
int Gi_00021;
int Gi_00022;
double Gd_00023;
int Gi_00024;
int Gi_00025;
int Gi_00026;
int Gi_00027;
int Gi_00028;
string Is_00000;
long returned_l;
int Ii_00070;
double Ind_002;
double Gd_00029;
double Id_000F8;
int Gi_00029;
long Gl_00029;
long Gl_0002A;
int Ii_00130;
int Gi_0002A;
double Gd_0002B;
double Gd_0002C;
int Gi_0002D;
double Gd_0002E;
double Gd_0002F;
int Gi_00030;
long Gl_00031;
int Ii_0012C;
long Gl_00030;
int Gi_00031;
int Ii_00140;
bool Gb_00032;
double Gd_00032;
double Gd_00033;
int Gi_00034;
double Id_00160;
bool Gb_00034;
double Id_00168;
double Gd_00035;
double Gd_00036;
int Gi_00037;
double Gd_00038;
double Gd_00039;
int Gi_0003A;

bool flag_actualiza_tp= false;
int  cola= 0;
bool actualiza_tp_tren = false;


bool   Ib_00151 = false;
bool   Ib_00152= false;
double Id_00110;
double Id_00118;
double Gd_0003A;
bool   Gb_0003A;
bool   tren= false;

int    Ii_00134;
double Ind_004;
double Id_00138;
int    Ii_00154;
int    Ticket_inversa;

double Id_00100;
double Id_00108;
long Gl_0003A;

double Gd_0003B;
int Gi_0003B;
double Id_000D8;
double TP_inversa;
double SL_inversa;

//double Id_000E8;
//double Id_00148;
//double Id_000F0;
int    Gi_0003C;
string Is_00010;
string Is_00020;
string Is_00030;
string Is_00040;

double Gd_00000;
double Gd_00003;
double Gd_00004;
double Gd_00006;
double Gd_00009;
double Gd_0000A;
int    Gi_0000B;
double Gd_0000C;
double Gd_0000D;
double Gd_00010;
double Gd_00012;
double Gd_00015;
double Gd_00016;
int    Gi_00017;
double Gd_00018;
double Gd_00019;
double Gd_0001C;
double Gd_0001E;
double Gd_00021;
double Gd_00022;
int Gi_00023;
long Gl_00035;
int Gi_00036;
bool returned_b;
bool Gb_00038;
int Gi_00038;
long Gl_00039;
bool Gb_0003C;
double Gd_00037;
int Gi_0002B;
bool Gb_0002C;
int Gi_0002C;
long Gl_0002D;
int Gi_0002E;
int Gi_0002F;
bool Gb_00030;
int Gi_00032;
int Gi_00033;
long Gl_00025;
bool Gb_00028;
double Gd_00027;
bool Gb_00000;
int Gi_00001;
bool Gb_00001;
double returned_double;
bool order_check;
bool order_check2;

double ultimo_lote_buy = 0;
double ultimo_lote_sell = 0;

bool nueva_cola_sell = false;
bool nueva_cola_buy =  false;
bool fin_max_vagones = false;
bool respbum = false;
int boom = 0;
double tmp_lotes = 0;

//************************************
extern int    hora_ini          = 3;         // hora Bloher
extern int    hora_fin          = 23;        // hora Broker
extern int    hora_open_market  = 9 ;        // hora NY
extern int    tiempo_no_market  = 1;         // cuanti tienpo sin operar
string pairs[] =       {"AUDCAD", "AUDUSD",        "EURUSD",    "GBPAUD", "GBPUSD",      "NZDUSD",    "USDCAD",      "USDJPY",   "BTCUSD","ETHUSD"};
string dependencia[] = {"1,3,6", "0,3,2,4,5,6,7", "1,4,5,6,7", "0,1,4",  "3,1,2,5,6,7", "1,2,4,6,7", "0,1,2,4,6,7", "1,2,4,6,7","9",     "8"};
string   descrip_no_proceso = "";
int cur_colas [10] ;
datetime hora_sigp_eventos = 0;
// buffers globales
int      aid [];
string   ahora [];
datetime afecha [];
string   acurrency  [];
string   aname  [];
string   afult [];
string   asource  [];
string   aimportance  [];
datetime fechaproceso_eventos = 0;
int correccion = 0;
//************************************
int herror = 0;
int conteollamadas = 0;
double lim_transformer_buy = 0.0005;
double lim_transformer_sell = -0.0005;

//***************************
// Sync
bool flag_sync = false;
datetime fecha_hora_sync = 0;
int ticksync [];
int cuenta_sync = 2000;
int cuentas_sync[] = {2000,3000,4000, 6000};
double factor_sinc = 1;
string modelo_SL = "mult";
double factor_tpsl = 0.7;//1.51;

//***********************************

  int flag_fprecios      = 0;
  int flag_ffmaxp        = 0;
  int flag_ffmaxbum      = 0;
  int flag_ffatr         = 0;
  int flag_ffhorario     = 0;
  int flag_ffsoportes    = 0; //1;
  int flag_ffresistencias= 0; //1;
  int flag_ffmax_fractal = 0; //1;
  int flag_ffresbal      = 0;
  int flag_ff8           = 0;
  int flag_ff9           = 0;
  
  int resp_fprecio        = 0;
  int resp_fmaxp          = 0;
  int resp_fmaxbum        = 0;
  int resp_fatr           = 0;
  int resp_fhorario       = 0;
  int resp_fsoportes      = 0;
  int resp_fresistencias  = 0;
  int resp_fmax_fractal   = 0;
  int resp_fresbal             = 0;
  int resp_f8             = 0;
  int resp_f9             = 0;


   double SCORE0 = 0;
   double SCORE1 = 0;
   double SCORE2 = 0;
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
int init()
  {

   Id_000D8 = 0;
   //Id_000E8 = 0;
 //  Id_000F0 = 0;
   Id_000F8 = 0;
   Id_00100 = 0;
   Id_00108 = 0;
   Id_00110 = 0;
   Id_00118 = 0;
   Id_00120 = 0;
   Ii_0012C = 0;
   Ii_00130 = 0;
   Ii_00134 = 0;
   Id_00138 = 0;
   Ii_00140 = 0;
//   Id_00148 = 0;
   Ii_00154 = 0;

   Id_00160 = 0;
   Id_00168 = 0;



   btClose           = (string)MagicNumber+"CLOSE";
   btClosesymbol     = (string)MagicNumber+"CLOSESYMBOL";
   btClose();
   fecha_banda_anterior = TimeCurrent()- 3600;

   if(Symbol() == "GBPAUD")
     {
      TakeProfit  = 100;
      gap         = 150;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 80;
      lim_indicador_inferior  = 20;
      gap_ult_fractal   = 350;
      gap_max_fractal   = 500;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 0.0010;
      min_atr = 0.0002;
      factor_lote_indicador = 0.5;
      max_perdida_cuenta =   0.03;  // perdida máxima
      correccion = 1;
      if(Period()==5)
        {
         flag_BUY  = true;
         flag_SELL = true;
        }
      if(Period()==15)
        {
         flag_BUY  = true;
         flag_SELL = true;
        }
      hora_open = 7;
      hora_close= 23;
      lim_transformer_buy =  0.0002 ;// 0.000070;//0.000032;//0.00002;
      lim_transformer_sell = -0.0002;//  -0.0003 ; //-0.00033;
     }
   if(Symbol() == "EURUSD")
     {
      TakeProfit  = 60;
      gap         = 100;
      Max_vagones = 1;
      lim_rsi_superior  = 80;
      lim_rsi_inferior  = 20 ;
      lim_indicador_superior  = 80;
      lim_indicador_inferior  = 20;
      gap_ult_fractal   = 200;
      gap_max_fractal   = 350;
      factor_lote_indicador = 0.7;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 0.0010;
      min_atr = 0.0001;
      max_perdida_cuenta =   0.03;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 7;
      hora_close= 23;
      correccion = 1;
      lim_transformer_buy =   0.0002;  //0.000096;
      lim_transformer_sell = -0.00007;  //-0.000089;

     }

   if(Symbol() == "GBPUSD")
     {
      TakeProfit  = 60;
      gap         = 100;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 80;
      lim_indicador_inferior  = 20;
      gap_ult_fractal = 300;
      gap_max_fractal = 400;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 0.0010;
      min_atr = 0.0002;
      factor_lote_indicador = 0.6;
      max_perdida_cuenta =   0.03;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 7;
      hora_close= 23;
      lim_transformer_buy =   0.000120;
      lim_transformer_sell = -0.000170;
      correccion = 1;

     }
   if(Symbol() == "AUDUSD")
     {
      TakeProfit = 50;
      gap        = 100;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 80;
      lim_indicador_inferior  = 20;
      gap_ult_fractal = 200;
      gap_max_fractal = 350;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 0.0010;
      min_atr = 0.0002;
      factor_lote_indicador = 0.4;
      max_perdida_cuenta =   0.03;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 7;
      hora_close= 23;
      lim_transformer_buy =  0.00008;//0.000170; //0.00025;
      lim_transformer_sell = -0.00008 ; //0.000021;
      correccion = 1;
     }
     
   if(Symbol() == "BTCUSD")     
          {
      TakeProfit = 8000;
      gap        = 20000;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 70;
      lim_indicador_inferior  = 30;
      gap_ult_fractal = 10000;
      gap_max_fractal = 50000;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 100;
      min_atr = 500;
      factor_lote_indicador = 0.6;
      max_perdida_cuenta =   0.02;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 1;
      hora_close= 23;
      lim_transformer_buy = 150 ; //65;
      lim_transformer_sell = 2;   //11;
      correccion = 1;

     }
   if(Symbol() == "EURCHF")
     {
      TakeProfit  = 50;
      gap         = 100;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 80;
      lim_indicador_inferior  = 20;
      gap_ult_fractal = 160;
      gap_max_fractal = 200;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 0.0010;
      min_atr = 0.0002;
      factor_lote_indicador = 0.6;
      max_perdida_cuenta =   0.03;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 7;
      hora_close= 23;
      lim_transformer_buy =   0.000100;
      lim_transformer_sell = -0.000070;
      correccion = 1;
     }
   if(Symbol() == "US30")
     {
      TakeProfit = 300;
      gap        = 600;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 70;
      lim_indicador_inferior  = 30;
      gap_ult_fractal = 400;
      gap_max_fractal = 600;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 100;
      min_atr = 500;
      factor_lote_indicador = 5;
      max_perdida_cuenta =   0.05;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 1;
      hora_close= 23;
      lim_transformer_buy  = 20; //130000;
      lim_transformer_sell = 1;// 90000;
      PointVal = 0.1 ;
      correccion = 1;


     }


   if(Symbol() == "GER40")
     {
      TakeProfit = 600;
      StopLoss = 350;
      
      gap        = 600;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 70;
      lim_indicador_inferior  = 30;
      gap_ult_fractal = 400;
      gap_max_fractal = 600;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 100;
      min_atr = 500;
      factor_lote_indicador = 5;
      max_perdida_cuenta =   0.10;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 1;
      hora_close= 23;
      lim_transformer_buy =   2;
      lim_transformer_sell = -2;
      PointVal = 0.1 ;
      correccion = 1;

     }


   if(Symbol() == "NAS100")
     {
      TakeProfit = 1600;
      StopLoss = 200;
      gap        = 800;
      Max_vagones = 1;
      lim_rsi_superior  = 70;
      lim_rsi_inferior  = 30;
      lim_indicador_superior  = 70;
      lim_indicador_inferior  = 30;
      gap_ult_fractal = 600;
      gap_max_fractal = 1000;
      modeloTP = "Largo";
      saltogap = 1.5;
      max_atr = 100;
      min_atr = 500;
      factor_lote_indicador = 5;
      max_perdida_cuenta =   0.10;  // perdida máxima
      flag_BUY  = true;
      flag_SELL = true;
      hora_open = 1;
      hora_close= 23;
      lim_transformer_buy =  18;
      lim_transformer_sell = 0;
      PointVal = 0.1 ;
      correccion = 1;

     }
fecha_hora_sync = TimeCurrent();
fecha_hora_monitoreo = TimeCurrent();

//1            ,1          ,1            ,0         ,1             ,1              ,1                  ,1                 ,0       ,0       ,0);
//flag_fprecios,flag_ffmaxp,flag_ffmaxbum,flag_ffatr,flag_ffhorario,flag_ffsoportes,flag_ffresistencias,flag_ffmax_fractal,flag_ffresbal,flag_ff8,flag_ff9


if (  (Symbol()== "NAS100") ||   (Symbol()== "US30") ||  (Symbol()== "GER40"))
{ 
      flag_fprecios      = 0;
      flag_ffmaxp        = 0;
      flag_ffmaxbum      = 0;
      flag_ffatr         = 0;
      flag_ffhorario     = 0;
      flag_ffsoportes    = 0;
      flag_ffresistencias= 0;
      flag_ffmax_fractal = 0;
      flag_ffresbal      = 0;
      flag_ff8           = 0;
      flag_ff9           = 0;
}
else
{
      flag_fprecios      = 0;
      flag_ffmaxp        = 0;
      flag_ffmaxbum      = 0;
      flag_ffatr         = 0;
      flag_ffhorario     = 0;
      flag_ffsoportes    = 0;
      flag_ffresistencias= 0;
      flag_ffmax_fractal = 0;
      flag_ffresbal      = 1;
      flag_ff8           = 0;
      flag_ff9           = 0;

}



   

   return (INIT_SUCCEEDED);
  }
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
//*******************************************************************************************************************************************************************************
int deinit()
  {
   objectsDelete();

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
int start()
  {
   color c = Black;
   int zona=-1;
   string tmp_str;
   int Li_FFFFC;
   string Ls_FFFF0;
   long Ll_FFFE8;

   double Ld_FFFD8;
   double Ld_FFFD0;
   double Ld_FFFC8;
   double Ld_FFFC0;
   double Ld_FFFB8;

   Li_FFFFC = 0;
   Ll_FFFE8 = 0;

   Ld_FFFD8 = 0;
   Ld_FFFD0 = 0;
   Ld_FFFC8 = 0;
   Ld_FFFC0 = 0;
   Ld_FFFB8 = 0;
   Gi_00000 = 0;
   Gd_00001 = 0;
   Gi_00002 = 0;
   Gi_00003 = 0;
   Gi_00004 = 0;
   Gi_00005 = 0;
   Gi_00006 = 0;
   Gd_00007 = 0;
   Gi_00008 = 0;
   Gi_00009 = 0;
   Gi_0000A = 0;
   Gd_0000B = 0;
   Gi_0000C = 0;
   Gi_0000D = 0;
   Gi_0000E = 0;
   Gd_0000F = 0;
   Gi_00010 = 0;
   Gi_00011 = 0;
   Gi_00012 = 0;
   Gd_00013 = 0;
   Gi_00014 = 0;
   Gi_00015 = 0;
   Gi_00016 = 0;
   Gd_00017 = 0;
   Gi_00018 = 0;
   Gi_00019 = 0;
   Gi_0001A = 0;
   Gd_0001B = 0;
   Gi_0001C = 0;
   Gi_0001D = 0;
   Gi_0001E = 0;
   Gd_0001F = 0;
   Gi_00020 = 0;
   Gi_00021 = 0;
   Gi_00022 = 0;
   Gd_00023 = 0;
   Gi_00024 = 0;
   Gi_00025 = 0;
   Gi_00026 = 0;
   Gi_00027 = 0;
   Gi_00028 = 0;

   Ls_FFFF0 = Is_00000;
   Ll_FFFE8 = StringToTime(Ls_FFFF0);

   ultimo_lote_buy = 0;
   ultimo_lote_sell = 0;
   tipo_accion_buy = 0;
   tipo_accion_sell = 0;

   nueva_cola_sell = false;
   nueva_cola_buy = false;
   tren = false;
   fin_max_vagones = false;
   bool retorno = false;
   tmp_lotes = 0;


//*********************************************** Validaciones previas
//*********************************************** Validaciones previas
   Ld_FFFD8 = (Id_000A8 / Id_000B0);
   Ld_FFFD0 = 0;
   Ld_FFFC8 = 0;



//*********************************************************************
// 1
// Validaciones de horario
//*********************************************************************



//********************************
   double nuevo_dif_fractal = 0;
   if(New_bar(timebar))
   {
         
         SCORE0 = 0;
         SCORE1 = SCORE0;
         SCORE2 = SCORE1;

         
         
         bool resp_new = false;
         resp_new = Max_Bumm(Symbol(),Period(),OP_BUY,gap_ult_fractal,nuevo_dif_fractal);
         if(resp_new)
         {
               boom = 1 ;
               respbum = true;
         }
         else
         {
               resp_new = Max_Bumm(Symbol(),Period(),OP_SELL,gap_ult_fractal,nuevo_dif_fractal);
               if(resp_new)
               {
                  boom = -1 ;
                  respbum = true;
               }
               else
               {
                  boom = 0 ;
                  respbum = false;
               }
         }
         if( flag_sync)
         {
               Sync_oper ();
               //printf("sincronizando...");
         }
     }
     else
     {
         Sleep(60000);
         return 0;
     }



   if(Cambio_de_hora("hh",2,fecha_hora_monitoreo))
   {
         printf("Aqui reportando TRANSF"+" "  + Symbol()+" Timeframe:"+ IntegerToString(Period()));
   }

//*********************************************************************
// 1
// Validaciones de horario
//*********************************************************************
   if(horario())
     {
      Sleep(60000);
      retorno = true;
     }
//*********************************************************************
   if(Flag_Autolot == true)
     {
      Calculo_Lotes();
     }
//*********************************************************************
// 2
// Validaciones de profit
//*********************************************************************
   if(validacion_max_perdida())
     {

      retorno = true;
     }


//********************************* TERMINA LAS VALIDACIONES PREVIAS
   Print_trail(respbum,nuevo_dif_fractal);


//********************************* TERMINA LAS VALIDACIONES PREVIAS
   if(flag_alerta_evento)
     {
      eval_risk_dia(TimeCurrent(), fecha_risk, risky, flag_alerta);
      if(flag_alerta == 1)
        {
         ObjectDelete("Alerta");
         DrawLabel("Alerta","Alert EVENTOS risky = "+ DoubleToStr(risky,3), 10,  65, clrRed, CORNER_RIGHT_UPPER,8, "Arial");
         //sleep (60000)
         retorno = true;
        }
      else
        {
         ObjectDelete("Alerta");
         DrawLabel("Alerta","No Alert, risky = "+ DoubleToStr(risky,3), 10,  65, clrBlue, CORNER_RIGHT_UPPER,8, "Arial");
         //sleep (60000)
        }

     }
//***************************************??????????????
// 1 de   14
// VALIDACIONES PREVIAS

   if(retorno)
     {
      //bool retorno = false;
       Sleep(60000);
      return 0;
     }

//***************************************??????????????
// 0 de   14
// VALIDACIONES PREVIAS

   Gl_00031 = Ii_0012C;
   if(Gl_00031 == Time[0])
     {
      Li_FFFFC = 0;
      return 0;
     }
   Ii_0012C = (int)Time[0];

//****************************************************************************************************************************************************??????????????????????????????
// 1 DE  14
//********************************************** se calcula el profit flotante
   Gd_00001 = 0;
   Ii_00140 = OrdersTotal() - 1;
   if(Ii_00140 >= 0)
     {
      do
        {
         order_check = OrderSelect(Ii_00140, 0, 0);
         if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber)
           {
            if(OrderType() == OP_BUY || OrderType() == OP_SELL)
              {
               Gd_00001 = (Gd_00001 + OrderProfit());
              }
           }
         Ii_00140 = Ii_00140 - 1;
        }
      while(Ii_00140 >= 0);
     }
// en Gd esta el profit total

//****************************************************************************************************************************************************??????????????????????????????
// 2 de 14
// ********************************* Se calcula el numero de operaciones pendientes
// Ib_000B8 esta como false y profit negativo
// Esto nunca se jecuta

   Ld_FFFC0 = Gd_00001; // Gd_00001 viene el flotante

//****************************************************************************************************************************************************??????????????????????????????
//   3 de 14
// Se cuentasn el numero de operaciones
// Solo calcula este numero

   sumatoria_lotes_inversa = 0;

   Gi_00005 = 0;
   Gi_0003A = OrdersTotal() - 1;
   Gi_00006 = Gi_0003A;
   if(Gi_0003A >= 0)
     {
      do
        {
         order_check = OrderSelect(Gi_00006, 0, 0);
         if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber)
           {
            if(OrderType() == OP_SELL || OrderType() == OP_BUY)
              {

               Gi_00005 = Gi_00005 + 1;
               sumatoria_lotes_inversa = sumatoria_lotes_inversa + OrderLots();
              }
           }
         Gi_00006 = Gi_00006 - 1;
        }
      while(Gi_00006 >= 0);
     }
//****************************************************************************************************************************************************??????????????????????????????
//   4 de 14
//   Calcula el numero y pone actualiza_tp_tren en falso si no hay operaciones abiertas
//   bool actualiza_tp_tren;
//   actualiza_tp_tren = false;
//   int cola;
//   cola = 0;

//Gi_00005 tiene el numero de operaciones
   cola = Gi_00005;
   if(Gi_00005 == 0)
     {
      actualiza_tp_tren = false;
     }

//****************************************************************************************************************************************************??????????????????????????????
//   5 de    14
// se validan si existen transacciones para Buy o para sell pendientes

   if(Gd_00001 < 0)   //si el profit es negativo // AÑADIDO
     {
      Ii_00140 = OrdersTotal() - 1;
      if(Ii_00140 >= 0)
        {
         do
           {
            order_check = OrderSelect(Ii_00140, 0, 0);
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber)
              {
               if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_BUY)
                 {
                  Ib_00151 = true; // si hay cola Buy
                  Ib_00152 = false;
                  break;
                 }
               if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_SELL)
                 {
                  Ib_00151 = false;
                  Ib_00152 = true; // si hay cola sell
                  break;
                 }
              }
            Ii_00140 = Ii_00140 - 1;
           }
         while(Ii_00140 >= 0);
        }
     }
//****************************************************************************************************************************************************??????????????????????????????
//   6 de  14
// se saca el ultimo registro del tren para buy o para sell
// cola viene el numero de operaciones pendientes
// si es mayor que 0 las operaciones pendientes y < 99999



//******************************************************************************************************************************
//******************************************************************************************************************************

   if(cola >= Max_vagones)  // se cierra cuando se llega a 10 vagones
   {
      fin_max_vagones = true;
   }
//*****************************************************************************************************************************
//*******************************************************************************************************************************
// Si hay cola Buy o sell se valida so se tiene el GAP
// se saca el maximo registro para buy y sell (repetido que el anterior pero hay un
// Se saca el maximo Buy o Sell
// se prende el flag para buy o SELL

   if(cola > 0)
   {
      RefreshRates();
      Gd_00007 = 0;
      Gi_00008 = 0;
      Gi_00009 = 0;


      // Se saca el maximo Buy
      Gi_0003A = OrdersTotal() - 1;
      Gi_0000A = Gi_0003A;
      if(Gi_0003A >= 0)
        {
         do
           {
            order_check = OrderSelect(Gi_0000A, 0, 0);
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_BUY)
              {
               Gi_00008 = OrderTicket();
               if(Gi_00008 > Gi_00009)
                 {
                  Gd_00007 = OrderOpenPrice();
                  Gi_00009 = Gi_00008;
                  ultimo_lote_buy = OrderLots();
                  //ultimo_lote_Sell = 0;
                 }
              }
            Gi_0000A = Gi_0000A - 1;
           }
         while(Gi_0000A >= 0);
        }
      Id_00110 = Gd_00007; // aqui queda el mayor Openprice BUY
      Gd_0000B = 0;
      Gi_0000C = 0;
      Gi_0000D = 0;

      // Se saca el maximo SELL
      Gi_0003A = OrdersTotal() - 1;
      Gi_0000E = Gi_0003A;
      if(Gi_0003A >= 0)
        {
         do
           {
            order_check = OrderSelect(Gi_0000E, 0, 0);
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_SELL)
              {
               Gi_0000C = OrderTicket();
               if(Gi_0000C > Gi_0000D)
                 {
                  Gd_0000B = OrderOpenPrice();
                  Gi_0000D = Gi_0000C;
                  ultimo_lote_sell = OrderLots();
                 }
              }
            Gi_0000E = Gi_0000E - 1;
           }
         while(Gi_0000E >= 0);
        }
      Id_00118 = Gd_0000B;   //Aqui queda el menor openproce de sell

      // S hay cola buy se prende flag  flag para un nuevo vagon

      if(Ib_00151)  // si hay cola buy
        {

         Gd_0003A = (Id_00110 - Ask);// Id_00110 = al mayor precio buy
         double newgap = Calculo_gap(cola,modeloTP, saltogap);
         if((Gd_0003A >= (newgap * PointVal)))
           {

            double tmp_score = 0;
            if(Calculo_score_accion(2, OP_BUY, tipo_accion_buy, tipo_accion_sell,tmp_score))
              {
               if(tipo_accion_buy == -1)
                 {

                  closeOrderssymbol(OP_BUY);
                  Ib_00151 = false;
                 }
               if(tipo_accion_sell > 0)
                 {
                  nueva_cola_sell  = true;
                 }
               tren = true;
              }
           }
        }
      // S hay cola buy se prende flag para primer vagon  nuevo vagon

      if(Ib_00152)   // si hay cola sell
        {
         Gd_0003A = (Bid - Id_00118); // Id_00118 el menor precio sell
         double newgap = Calculo_gap(cola,modeloTP, saltogap);
         if((Gd_0003A >= (newgap * PointVal)))
           {

            double tmp_score = 0;
            if(Calculo_score_accion(2, OP_SELL, tipo_accion_buy, tipo_accion_sell,tmp_score))
              {
               if(tipo_accion_sell == -1)
                 {
                  closeOrderssymbol(OP_SELL);
                  Ib_00152 = false;
                 }
               if(tipo_accion_buy > 0)
                 {
                  nueva_cola_buy  = true;
                 }
               tren = true;
              }
           }
         // VALIDAR SCORE
        }
     } // termina    if (cola > 0 && cola <= max_cola)

//****************************************************************************************************************************************************??????????????????????????????
//   7 de  14
// Si no hay cola solo se prende para el primer vagon

   if(cola < 1)  // Si no hay COla
     {
      Ib_00152 = false;   // reinicia el flag de que si hay cola sell
      Ib_00151 = false;   // reinicia el flag de que si hay cola buy
      tren = true;    // arme tren
     }

//****************************************************************************************************************************************************??????????????????????????????
//   8 de  14
//   PRIMER VAGON
//   O NUEVO VAGON

   if(nueva_cola_sell)   // Si no hay COla
      Ib_00152 = true;   // reinicia el flag de que si hay cola sell
   if(nueva_cola_buy)   // Si no hay COla
      Ib_00151 = true;   // reinicia el flag de que si hay cola buy
   if(tren)  // se debe crear una operacion si hay cola Buy y sell con >48 puntos, o cola < 1
      // armar un tren
     {

      // Se busca el maximo ticket y su precio BUY
      Gd_0000F = 0;
      Gi_00010 = 0;
      Gi_00011 = 0;
      Gi_0003A = OrdersTotal() - 1;
      Gi_00012 = Gi_0003A;
      if(Gi_0003A >= 0)
        {
         do
           {
            order_check = OrderSelect(Gi_00012, 0, 0);
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_BUY)
              {
               Gi_00010 = OrderTicket();
               if(Gi_00010 > Gi_00011)
                 {
                  Gd_0000F = OrderOpenPrice();
                  Gi_00011 = Gi_00010;
                 }
              }


            Gi_00012 = Gi_00012 - 1;
           }
         while(Gi_00012 >= 0);
        }
      Id_00110 = Gd_0000F; // la mayor ticket buy
      Gd_00013 = 0;
      Gi_00014 = 0;

      // Se busca el maximo ticket y su precio BUY
      Gi_00015 = 0;
      Gi_0003A = OrdersTotal() - 1;
      Gi_00016 = Gi_0003A;
      if(Gi_0003A >= 0)
        {
         do
           {
            order_check = OrderSelect(Gi_00016, 0, 0);
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_SELL)
              {
               Gi_00014 = OrderTicket();
               if(Gi_00014 > Gi_00015)
                 {
                  Gd_00013 = OrderOpenPrice();
                  Gi_00015 = Gi_00014;      // la mayor ticket Sell
                 }
              }
            Gi_00016 = Gi_00016 - 1;
           }
         while(Gi_00016 >= 0);
        }


      // Has aqui se tienen los maximos registros

      //***********************************************************************
      // se crea la operacion para SELL
      // Lotaje
      Id_00118 = Gd_00013;

      // se crea la operacion para SELL
      if(Ib_00152)     // si hay cola sell
      {

         if(!flag_SELL)
         {
            printf("NO FLAG SELL");
            return 0;
         }

         Id_00138 = NormalizeDouble((StartingLots * (MathPow(factor, cola))), Digitos);

         //         Id_00138 = StartingLots + ultimo_lote_sell * factor;
         //           Id_00138 =  NormalizeDouble(   (StartingLots *   MathPow(factor, cola)) , Digitos );
         if(Id_00138 > 99)
            Id_00138 = 99;

         RefreshRates();
         tmp_str = "T21 " ;



         Ii_00154 = OpenPendingOrder(OP_SELL,           Id_00138*factor_lote_indicador,       Bid, (int)Id_00088, Ask, 0, 0, tmp_str, MagicNumber, 0, 11823615);
         if(Ii_00154 < 0)
           {
            Print("Error: ", GetLastError(), " Lotes ", DoubleToStr(factor_lote_indicador * Id_00138)," factor ",DoubleToStr(factor_lote_indicador));
            return 0;
           }

         Gd_00017 = 0;
         Gi_00018 = 0;
         Gi_00019 = 0;
         //          Se calcula nuevamente el mayor ticket SELL y Open price

         Gi_0003A = OrdersTotal() - 1;
         Gi_0001A = Gi_0003A;
         if(Gi_0003A >= 0)
           {
            do
              {
               order_check = OrderSelect(Gi_0001A, 0, 0);
               if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_SELL)
                 {
                  Gi_00018 = OrderTicket();
                  if(Gi_00018 > Gi_00019)
                    {
                     Gd_00017 = OrderOpenPrice();
                     Gi_00019 = Gi_00018;
                    }
                 }
               Gi_0001A = Gi_0001A - 1;
              }
            while(Gi_0001A >= 0);
           }

         Id_00118 = Gd_00017;   // el PRECIO DEL TICKET MAS ALTO sell
         tren = false;
         flag_actualiza_tp = true;


        }  // end de sell

      // se crea la operacion para buy
      else
        {
         //***********************************************************************
         // se crea la operacion para SELL
         if(Ib_00151)  // si hay cola BUY
           {
            // Lotaje
            // se crea la operacion para Buy
            Ii_00134 = cola;

            //         Se abre la operacion
            Id_00138 = NormalizeDouble((StartingLots * (MathPow(factor, cola))), Digitos);

            //          Id_00138 = StartingLots+ ultimo_lote_buy * factor;
            //           Id_00138 =  NormalizeDouble(   (StartingLots *   MathPow(factor, cola)) , Digitos );
            if(Id_00138 > 99)
               Id_00138 = 99;

            tmp_str = "T21 ";

            if(!flag_BUY)
              {
               printf("NO FLAG BUY");
               return 0;
              }


            Ii_00154 = OpenPendingOrder(OP_BUY, Id_00138*factor_lote_indicador, Ask, (int)Id_00088, Bid, 0, 0, tmp_str, MagicNumber, 0, 65280);
            if(Ii_00154 < 0)
              {
               Print("Error: ", GetLastError(), " Lotes ", DoubleToStr(Id_00138)," factor ",DoubleToStr(factor_lote_indicador * Id_00138));


               return 0;
              }
            // se crea la operacion Calcula nuevamente el máximo ticket y precio BUYl
            Gd_0001B = 0;
            Gi_0001C = 0;
            Gi_0001D = 0;
            Gi_0003A = OrdersTotal() - 1;
            Gi_0001E = Gi_0003A;
            if(Gi_0003A >= 0)
              {
               do
                 {
                  order_check = OrderSelect(Gi_0001E, 0, 0);
                  if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_BUY)
                    {
                     Gi_0001C = OrderTicket();
                     if(Gi_0001C > Gi_0001D)
                       {
                        Gd_0001B = OrderOpenPrice();
                        Gi_0001D = Gi_0001C;
                       }
                    }
                  Gi_0001E = Gi_0001E - 1;
                 }
               while(Gi_0001E >= 0);
              }

            Id_00110 = Gd_0001B;  // el PRECIO DEL TICKET MAS ALTO buy
            tren = false;
            flag_actualiza_tp = true;


           } // de Buy


        } // DE ELSE

     }  // DEL IF TREN Crear Vagon
//****************************************************************************************************************************************************??????????????????????????????
//   9 de 14
// se crea la operacion para Buy PRIMERA OPERACION

   if(tren && cola < 1)
   {
      // Primer registro
      if(Ib_00152 == false && Ib_00151 == false)  // SI no hay cola buy y cola sell // PRIMER VAGON
      {
         Ii_00134 = cola;
         returned_double = MathPow(factor, cola);
         Id_00138 = NormalizeDouble((StartingLots * MathPow(factor, cola)), Digits);

         int negocio = negociar(modelo, cola);
         if(negocio == -1)
         {
            return 0;
         }
        }
    } // end del if tre y cola

//****************************************************************************************************************************************************??????????????????????????????
// 10 de 14
// RECALCULA COLA BUY O SELL

   Gi_00027 = 0;
   Gi_0003B = OrdersTotal() - 1;
   Gi_00028 = Gi_0003B;
   if(Gi_0003B >= 0)
   {
      do
      {
         order_check = OrderSelect(Gi_00028, 0, 0);
         if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber)
         {
            if(OrderType() == OP_SELL || OrderType() == OP_BUY)
            {
               Gi_00027 = Gi_00027 + 1;
            }
         }
         Gi_00028 = Gi_00028 - 1;
        }
      while(Gi_00028 >= 0);
     }

     cola = Gi_00027; // se recalcula la cola, seguramente hay un nuevo registro

//****************************************************************************************************************************************************??????????????????????????????
//   11 de 14
// se saca el flotante acumulado, precioopen * lots y a parte el total de lotes

   Id_000F8 = 0;
   Ld_FFFB8 = 0;

   Ii_00140 = OrdersTotal() - 1;
   if(Ii_00140 >= 0)
     {
      do
        {
         order_check = OrderSelect(Ii_00140, 0, 0);
         if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber)
           {
            if(OrderType() == OP_BUY || OrderType() == OP_SELL)
              {
               Gd_0003B = OrderOpenPrice();
               Id_000F8 = ((Gd_0003B * OrderLots()) + Id_000F8);   // sumatoria lotes * precio
               Ld_FFFB8 = (Ld_FFFB8 + OrderLots());       // sumatoria Lotes totales
              }
           }
         Ii_00140 = Ii_00140 - 1;
        }
      while(Ii_00140 >= 0);
     }
//****************************************************************************************************************************************************??????????????????????????????
//   12 de 14
//  SI HAY COLA, se calcula nuevamente el nuevo TP

   if(cola > 0)
   {
      Id_000F8 = NormalizeDouble((Id_000F8 / Ld_FFFB8), _Digits);    //Id_000F8  sumatoria lotes * precio / sumatoria de lotes
   }
//****************************************************************************************************************************************************??????????????????????????????
//Se SE ACTUALIZA TP

   int vtipo = -1;
   if(flag_actualiza_tp)  // Si se creo un nuevo VAGON se CALCULA EL TP
   {


      Ii_00140 = OrdersTotal() - 1;
      if(Ii_00140 >= 0)
        {
         do
           {
            order_check = OrderSelect(Ii_00140, 0, 0);
            if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber)
              {
                  if(OrderType() == OP_BUY)
                  {
                        Id_000D8 = ((TakeProfit * PointVal) + Id_000F8); //Id_000F8 sumatoria de profit (puede ser la perdida / lote
                        tmp_lotes = tmp_lotes + OrderLots();
                        //Id_000E8 = ((TakeProfit * PointVal) + Id_000F8);
//                      Gd_0003B = (Id_00050 * PointVal); // 5000  esto da 0,5 puntos
//                      Id_00148 = (Id_000F8 - Gd_0003B);//-  Id_000F8 es la perdida x lote , Gd_0003B=  0.5
                        vtipo = OP_BUY;
                        actualiza_tp_tren = true;
                  }
                  if(OrderType() == OP_SELL)
                  {
                        //Gd_0003B = (TakeProfit * PointVal);
                        Id_000D8 = (Id_000F8 - (TakeProfit * PointVal));
                        tmp_lotes = tmp_lotes + OrderLots();
//                      Id_000F0 = (Id_000F8 - (TakeProfit * PointVal));
//                      Id_00148 = ((Id_00050 * PointVal) + Id_000F8);
                        vtipo = OP_SELL;
                        actualiza_tp_tren = true;
                  }
              }
            Ii_00140 = Ii_00140 - 1;
           }
         while(Ii_00140 >= 0);
        }
     } // en del si actualiza TP


//****************************************************************************************************************************************************??????????????????????????????
// 13 de 14


   if(flag_actualiza_tp == false)
      return 0;

   string tmp_modelo_SL = "";
   if (cola>1)
   {
         tmp_modelo_SL = "zero";
   }
   else
   {
          tmp_modelo_SL = modelo_SL;
   }

   double tpatr = GET_TP_ATR();
   double SLN = 0;
   double TEMP_SLN = 0;
   double TPN = 0;
   double precioSL = 0;
   
   if (StopLoss == 0)
   {
      TEMP_SLN =  calcula_SL (vtipo,tmp_modelo_SL,StopLoss*4,precioSL,tmp_lotes);
   
      
      if (vtipo == OP_BUY)
      {
             TPN = Ask + (TakeProfit * PointVal );
             SLN = Ask - TEMP_SLN;
      }
      if (vtipo == OP_SELL)
      {
             TPN = Bid - (TakeProfit * PointVal  );
             SLN = Bid + TEMP_SLN;
      }
   }
   else
   {
     if (vtipo == OP_BUY)
      {
             TPN = Ask + (TakeProfit * PointVal );
             SLN = Ask - (StopLoss * PointVal );;
      }
      if (vtipo == OP_SELL)
      {
             TPN = Bid - (TakeProfit * PointVal);
             SLN = Bid + (StopLoss * PointVal );
      }
   
    }
   
   
   
   
   
   bool r = ActualizaTP(TPN, SLN);
   //order_check = OrderModify(OrderTicket(), Id_000F8, OrderStopLoss(), Id_000D8, 0, 65535);
   flag_actualiza_tp = false;
   

   return 0;
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



//+------------------------------------------------------------------+
//| Calculo_accion                    |
//calculo de la accion pero con limites calculados
//+------------------------------------------------------------------+
void  Calculo_accion_v2(int tipo_validacion, string simboloin, double scorein,int tipoin,int & tipo_accion_buyin, int & tipo_accion_sellin)
  {
   tipo_accion_buyin = 0;
   tipo_accion_sellin = 0;

// Limite red venta, limite gree compra
   limites_score(limite_compra, limite_venta, 15,fecha_datos_limites);
//write_logTransaccional(TimeCurrent(),Symbol(),Period(),timeframeIndicador,scorein,limite_compra, limite_venta );


//rango_indice_online (limite_compra, limite_venta, Period());

   if(tipo_validacion == 1)  //primer vagon;
     {
      if(tipoin == OP_BUY)
        {
         if(scorein > limite_compra)
           {

            tipo_accion_buyin = 1;
            if(fin_max_vagones)
              {

               tipo_accion_buyin = 0;
              }
            return;
           }
         if(scorein < limite_venta)
           {
            //                  tipo_accion_buyin = -1;
            //                  tipo_accion_sellin = 1;


            if(fin_max_vagones)
              {
               //                           tipo_accion_buyin = -1;
               //                           tipo_accion_sellin = 1;
               //                           tipo_accion_buyin = 0;

              }
            return;
           }
        }

      if(tipoin == OP_SELL)
        {
         if(scorein <  limite_venta)
           {
            //                  if (!fin_max_vagones)
            tipo_accion_sellin = 1;

            if(fin_max_vagones)
              {
               tipo_accion_sellin = 0;

              }
            return;
           }
         if(scorein > limite_compra)
           {
            //                 tipo_accion_buyin =  1;
            //                 tipo_accion_sellin = -1;

            if(fin_max_vagones)
              {
               //                           tipo_accion_sellin = -1;
               //                           tipo_accion_buyin =  1;

               //                           tipo_accion_sellin = 0;

              }
            return;
           }

        }

     }


   if(tipo_validacion == 2)  // vagon;
     {
      if(tipoin == OP_BUY)
        {
         tipo_accion_buyin = 1;
         if(fin_max_vagones)
           {
            tipo_accion_buyin = 0;
           }
         return;
         if(scorein < limite_venta)
           {
            //                        tipo_accion_buyin = -1;
            //                      tipo_accion_sellin = 1;

           }
        }

      if(tipoin == OP_SELL)
        {

         tipo_accion_sellin = 1;
         if(fin_max_vagones)
           {
            tipo_accion_sellin = 0;
           }
         return;
         if(scorein > limite_compra)
           {
            //                      tipo_accion_sellin = -1;


           }

        }

     }
   return ;

  }
//+------------------------------------------------------------------+
//| Calculo_accion                    |
//+------------------------------------------------------------------+
void  Calculo_accion(int modeloin, string simboloin, double scorein,int tipoin,int & tipo_accion_buyin, int & tipo_accion_sellin)
  {
   tipo_accion_buyin = 0;
   tipo_accion_sellin = 0;

   if(simboloin == "GBPAUD")
     {
      limite_compra = 30;
      limite_venta =  -50;
     }
   if(simboloin == "GBPUSD")
     {
      limite_compra = 30;
      limite_venta =  -50;
     }
   if(simboloin == "AUDUSD")
     {
      limite_compra = 25;
      limite_venta =  -50;
     }
   if(simboloin == "USDJPY")
     {
      limite_compra = 30;
      limite_venta =  -60;
     }
   if(simboloin == "AUDCAD")
     {
      limite_compra = 25;
      limite_venta =  -60;
     }
   if(simboloin == "EURUSD")
     {
      limite_compra = 25;
      limite_venta =  -50;
     }
   if(simboloin == "NZDUSD")
     {
      limite_compra = 25;
      limite_venta =  -50;
     }
// Limite red venta, limite gree compra
   if(tipoin == OP_BUY)
     {
      if(scorein > limite_compra)
        {
         tipo_accion_buyin = 3;
         return;
        }

      if((scorein > limite_venta) && (scorein <= limite_compra))
        {
         //                tipo_accion_buyin = 2;
         return;
        }
      if(scorein < limite_venta)
        {
         tipo_accion_buyin = -1;
         tipo_accion_sellin = 1;
         return;
        }
     }

   if(tipoin == OP_SELL)
     {
      if(scorein <  limite_venta)
        {
         tipo_accion_sellin = 3;
         return;
        }
      if((scorein > limite_venta) && (scorein <= limite_compra))
        {
         //                  tipo_accion_buyin =  1;
         //                  tipo_accion_sellin = -1;
         return;
        }
      if(scorein > limite_compra)
        {
         tipo_accion_buyin =  1;
         tipo_accion_sellin = -1;
         return;
        }
     }
   return ;
  }
//+------------------------------------------------------------------+
//|                     |
//+------------------------------------------------------------------+
bool Crear_Tren(int modeloin,int tipoin,int & tipo_acc_buy, int & tipo_acc_sell, double & factor_lote_ind, double & scorein)
  {
   bool respuesta = false;
 
   if(modeloin == 1)
      respuesta = Crear_Tren_trail(modeloin,tipoin,tipo_acc_buy, tipo_acc_sell, factor_lote_ind, scorein);

   return (respuesta);
  }

//+------------------------------------------------------------------+
//|                     |
//+------------------------------------------------------------------+
bool Crear_Tren_trail(int modeloin, int tipoin, int & tipo_acc_buy, int & tipo_acc_sell, double & factor_lote_ind, double & tmp_score)
  {
   bool respuesta = False;
   tmp_score = 0;
   tipo_acc_buy =    0;
   tipo_acc_sell =   0;
//factor_lote_ind = 0;

   double precio_menos_2 = 0;
   double precio_menos_1 = 0;

   precio_menos_2 = iClose(_Symbol, 0, 2); // Precio de cierre del Timeframe , 0 Current, periodos atras
   precio_menos_1 = iClose(_Symbol, 0, 1); // Precio de cierre del Timeframe , 0 Current, 1 peíodo atras



//******************* trace
   if(flag_trace == 1)
     {

            tipo_acc_buy = 1;
            tipo_acc_sell = 0;
            return true;
     }
   if(flag_trace == -1)
     {

            tipo_acc_buy = 0;
            tipo_acc_sell = 1;      
            return true;
     }
//******************* trace

   string  uno = "";
   string  dos = "";
   string  tres = "";
   

   if(tipoin == OP_SELL)
   {


  
      if(Calculo_score_accion(1, OP_SELL, tipo_acc_buy, tipo_acc_sell,tmp_score))
        {
            printf ("Trentrail.......SELL...............");
            uno= "SI pasa Score SELL = "+ DoubleToStr(tmp_score);
            /*
            if((precio_menos_2 > precio_menos_1))   // Precio de cierre -2   mayor que precio de cierre -1  (esta bajando la curva)
            {

               //if ((iRSI(NULL, 15, 5, 0, 1) >l im_rsi_superior)   &&   Calculo_score_accion(1, OP_SELL, tipo_acc_buy, tipo_acc_sell))

               if(iRSI(NULL, 15, 5, 0, 1) >lim_rsi_superior)
               {
                     dos=",  pasa rsi SELL";   //factor_lote_ind = 1;
                     respuesta = true;
               }
               else
               {
                     tres= ",  NO pasa rsi SELL" ;
               }


               dos= "SI pasa PRECIO BAJA SELL";
               respuesta = true; // ojo ojo  ojo

           }
           else
           {
               dos= "NO pasa PRECIO BAJA SELL";
               DrawEvent("DURO");
           }*/

            //  uno= "NO pasa Score SELL";
            respuesta = true;
        }
     } // de si e precio esta bajando

   if(tipoin == OP_BUY)
     {


      if(Calculo_score_accion(1, OP_BUY, tipo_accion_buy, tipo_accion_sell, tmp_score))
      {
         uno = "SI pasa Score BUY "+ DoubleToStr(tmp_score);
         printf ("Trentrail.......BUY...............");
         /*
         //factor_lote_ind = 1;

         if((precio_menos_2 <= precio_menos_1))   // Precio de cierre -2   mayor que precio de cierre -1  (esta bajando la curva)
           {
            // se crea la orden para BUY


            /*
            if (iRSI(NULL, 15, 5, 0, 1) < lim_rsi_inferior)
            {

               dos = "pasa rsi BUY";
               respuesta = true;
            } // del else
            else
            {
              tres = "NO pasa rsi BUY";
            }

            dos= "SI pasa PRECIO SUBE BUY";
            respuesta = true; // ojo ojo ojo

           }
         else
           {
            dos= "NO pasa PRECIO SUBE BUY";
            DrawEvent("DURO");

           } //decreciendo
           */
           respuesta = true;

        }

     }

   if(uno!= "")
      printf(uno+","+dos+","+tres+","+TimeToStr(TimeCurrent()));
   return (respuesta);
  }
//+------------------------------------------------------------------+
//|                                        |
//+------------------------------------------------------------------+
// retorna falso si no se puede hacer la operacion.
// verdad si de debe crear un registro
bool  Calculo_score_Nbot(int & tipooperacion,double & scorein,double & limite_compra_in,double & limite_venta_in, int & bonus)
  {
// tipo accion 1 ejecutar transaccion preguntada
   scorein = 0;
   bonus = 0;
   bool respuesta = false;
   tipooperacion = -1;
   limite_compra_in = 0;
   limite_venta_in = 0;



   if(flag_score_modelo)
     {
      indicador_online(scorein);
      limites_score(limite_compra_in, limite_venta_in, 15,fecha_datos_limites);
     }
   else
     {
      limite_compra_in = 50;
      limite_venta_in = -50;

      double tmp_tx =   iCustom(NULL,Period(),"Neo_OSC",lim_indicador_superior,lim_indicador_inferior,timeframeIndicador,1,1);
      if(tmp_tx == 1)
         scorein = 90;

      if(tmp_tx == -1)
         scorein = -90;
      if(tmp_tx == 0)
         scorein = 0;

     }






   double precio_menos_2 = 0;
   double precio_menos_1 = 0;
   precio_menos_2 = iClose(_Symbol, 0, 2); // Precio de cierre del Timeframe , 0 Current, periodos atras
   precio_menos_1 = iClose(_Symbol, 0, 1); // Precio de cierre del Timeframe , 0 Current, 1 peíodo atras
   double rsi5 = 0;
   double rsi15 = 0;

   rsi15 = iRSI(NULL, 5, 5, 0, 1);
   rsi15 = iRSI(NULL, 15, 5, 0, 1);


   if(scorein >= limite_compra_in)
     {
      if((precio_menos_2 <= precio_menos_1))   // Precio de cierre -2   mayor que precio de cierre -1  (esta bajando la curva)
        {
         // se crea la orden para BUY
         //printf("ordeb buy solo cambio precio BUY");
         return true;
         if(rsi15 < lim_rsi_inferior)
           {
            tipooperacion = OP_BUY;
            if(rsi5 < lim_rsi_inferior)
              {

               bonus = 1;
              }
            return true;
           }
        }
     }
   if(scorein <= limite_venta_in)
     {
      if((precio_menos_2 > precio_menos_1))   // Precio de cierre -2   mayor que precio de cierre -1  (esta bajando la curva)
        {
         //printf("orden Sell solo cambio precio RELL");
         return true;

         if(rsi15 >lim_rsi_superior)
           {
            tipooperacion = OP_SELL;
            if(rsi15 >lim_rsi_superior)
              {

               bonus = 1;
              }

            return true;
           }
        } // de si e precio esta bajando
     }
   return (false);
  }

//**********************************************************************************
//NEGPCIAR
//**********************************************************************************
int negociar(int modeloin, int colain)
  {
//Modelo 1 = Trail               2: Cesar
   if(modeloin == 1)  // TRAIL MIKE
     {
      Id_00100 = 0;
      Id_00108 = 0;
      string tmp_str = "TRANSF";
      double limite_buy_in = 0;
      double limite_sell_in = 0;



      bool nuevo_reg = false;

      bool eliminar_buy = false;
      bool eliminar_sell= false;
      bool crear_buy    = false;
      bool crear_sell   = false;
      double scorein = 0;

 
      /*
      nuevo_reg=  Crear_Tren(modelo,OP_SELL, tipo_accion_buy, tipo_accion_sell, factor_lote_indicador,scorein);
      if(nuevo_reg)
      {
         printf("negociar....SELL...........................");
         if(tipo_accion_buy == -1)
            eliminar_buy = true;
         if(tipo_accion_sell == -1)
            eliminar_sell= true;
         if(tipo_accion_buy >0)
            crear_buy    = true;
         if(tipo_accion_sell >0)
            crear_sell   = true;
      }
      else
      {
         nuevo_reg=  Crear_Tren(modelo,OP_BUY, tipo_accion_buy, tipo_accion_sell, factor_lote_indicador,scorein);
         if(nuevo_reg)
         {
            printf("negociar....BUY...........................");
            if(tipo_accion_buy == -1)
               eliminar_buy = true;
            if(tipo_accion_sell == -1)
               eliminar_sell= true;
            if(tipo_accion_buy >0)
               crear_buy    = true;
            if(tipo_accion_sell >0)
               crear_sell   = true;
         }
         else
         {
            return -1;
         }

      }

      if(eliminar_buy)
         closeOrderssymbol(OP_BUY);
      if(eliminar_sell)
         closeOrderssymbol(OP_SELL);

      bool risk_externo = analisis_risk_externo();
      if(flag_riesgo_externo &&  risk_externo)
      {
         printf ("Riesgo Externo");
         return -1;
      }
      */
      
      double dif = 0;
      double dif1 = 0;
      double dif2 = 0; 
      string txtr = "";
      string txtr1 = "";
      string txtr2 = "";   
      double tmp_resp0= consulta_score_transformer_v3(1, txtr,dif); 
      double tmp_resp1= consulta_score_transformer_v3(2, txtr1,dif1); 
      double tmp_resp2= consulta_score_transformer_v3(3, txtr2,dif2); 
      
         SCORE0 = tmp_resp0;
         SCORE1 = tmp_resp1;
         SCORE2 = tmp_resp2;
      
       
      if (  tmp_resp0 != 0 ||  tmp_resp1 != 0 || tmp_resp2 != 0  ) 
      {
         printf ("tres periodos s0,s1,s2=  %.1f   %.1f   %.1f  ; SCORE1= %.1f   SCORE2= %1.f",tmp_resp0,tmp_resp1,tmp_resp2,SCORE0,SCORE1 ); 
      }
/*
      if (( SCORE0 ==0) && (SCORE1 ==1.0))
      {
               printf ("BUY............CHANGE");
               crear_buy = true;
      }
      if (( SCORE0 ==0)  && (SCORE1 ==-1.0))
      {
               printf ("SELL............CHANGE");
               crear_sell = true;

      } 
*/
      if (( SCORE0 == 1 * correccion ))  //&& (SCORE1 ==1* correccion))
      {
               
               printf ("BUY...............CONTRA");
               crear_buy = true;

               

      } 
            if (( SCORE0 ==-1* correccion)) // && (SCORE1 ==-1* correccion))
      {
               printf ("SELL.............CONTRA");
               crear_sell = true;


      }        
       
      if(crear_sell)
      {

         printf ("Crear Sell......");
         bool validacion_pre = false;
         validacion_pre= validacion_pre_operacion(tmp_str, scorein, limite_buy_in, limite_sell_in,
                            OP_SELL, flag_fprecios,flag_ffmaxp,flag_ffmaxbum,flag_ffatr,flag_ffhorario,flag_ffsoportes,flag_ffresistencias,flag_ffmax_fractal,flag_ffresbal,flag_ff8,flag_ff9);
  


         if(! validacion_pre)
         {
            return 0;
         }

         if(!flag_SELL)
         {
            printf("NO FLAG SELL");
            return 0;
         }

         double vl = NormalizeDouble((factor_lote_indicador*Id_00138),2);
         double vlotes = AjustarVolumenAlPaso(vl);
         Ii_00154 = OpenPendingOrder(OP_SELL,vlotes, Id_00100, (int)Id_00088, Id_00100, 0, 0, tmp_str, MagicNumber, 0, 11823615);
         if(Ii_00154 < 0)
           {
            Print("NewT Error: ", GetLastError(), " Lotes antes ajustar ",DoubleToStr(vl) ," Lotes ", DoubleToStr( vl)," factor ",DoubleToStr(factor_lote_indicador), "sl ",IntegerToString(0) ," tp ",IntegerToString(0) );
            return -1;
           }
         //se saca el mayor registro de buy
         Gd_0001F = 0;
         Gi_00020 = 0;
         Gi_00021 = 0;
         Gi_0003A = OrdersTotal() - 1;
         Gi_00022 = Gi_0003A;
         if(Gi_0003A >= 0)
           {
            do
              {
               order_check = OrderSelect(Gi_00022, 0, 0);
               if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_BUY)
                 {
                  Gi_00020 = OrderTicket();
                  if(Gi_00020 > Gi_00021)
                    {
                     Gd_0001F = OrderOpenPrice();
                     Gi_00021 = Gi_00020;
                    }
                 }
               Gi_00022 = Gi_00022 - 1;
              }
            while(Gi_00022 >= 0);
           }
         Id_00110 = Gd_0001F; // PRECIO DEL MAYOR TICKET BUY
         flag_actualiza_tp = true;
        } // SELL

      if(crear_buy)
      {
         
         printf ("Crear Buy...........");
         bool validacion_pre = false;

         validacion_pre= validacion_pre_operacion(tmp_str, scorein, limite_buy_in, limite_sell_in,
                                             OP_BUY,flag_fprecios,flag_ffmaxp,flag_ffmaxbum,flag_ffatr,flag_ffhorario,flag_ffsoportes,flag_ffresistencias,flag_ffmax_fractal,flag_ffresbal,flag_ff8,flag_ff9);

         if(! validacion_pre)
         {
            printf ("No pasa validaciones");
            return 0;
         }         
         if(!flag_BUY)
         {
            printf("NO FLAG BUY");
            return 0;
         }

         double vl = NormalizeDouble(factor_lote_indicador * Id_00138,2);
         double vlotes = AjustarVolumenAlPaso(vl);
         Ii_00154 = OpenPendingOrder(OP_BUY,vlotes, Id_00108, (int)Id_00088, Id_00108, 0, 0, tmp_str, MagicNumber, 0, 65280);
         if(Ii_00154 < 0)
           {
            Print("NewT Error: ", GetLastError(),  " Lotes antes ajustar ",DoubleToStr(vl)," Lotes ", DoubleToStr( tmp_lotes)," factor ",DoubleToStr(factor_lote_indicador), "sl ",IntegerToString(0) ," tp ",IntegerToString(0) );
            return -1;
           }
         Gd_00023 = 0;
         Gi_00024 = 0;
         Gi_00025 = 0;
         Gi_0003A = OrdersTotal() - 1;


         // se saca el maximo recurso para sell
         Gi_00026 = Gi_0003A;
         if(Gi_0003A >= 0)
           {
            do
              {
               order_check = OrderSelect(Gi_00026, 0, 0);
               if(OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderSymbol() == _Symbol && OrderMagicNumber() == MagicNumber && OrderType() == OP_SELL)
                 {
                  Gi_00024 = OrderTicket();
                  if(Gi_00024 > Gi_00025)
                    {
                     Gd_00023 = OrderOpenPrice();
                     Gi_00025 = Gi_00024;
                    }
                 }

               // se saca el maximo recurso para sell
               Gi_00026 = Gi_00026 - 1;
              }
            while(Gi_00026 >= 0);
           }
         Id_00118 = Gd_00023;// PRECIO DEL MAYOR PRECIO SELL
         flag_actualiza_tp = true;
        } // buy
      if(Ii_00154 > 0)   // si se tiene abierto el ticket
        {
         Gl_0003A = TimeCurrent();
         Gd_0003B = ((Id_000D0 * 60) * 60); // Id_000D0 = 48
         Ii_00130 = (int)(Gl_0003A + Gd_0003B); // fecha actual mas 48 * 60 * 60   (asumo que son 48 Horas
        }
      tren = false;

     }// // end del modelo 1
     
 
   return 1;
  }

//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//*******************************************************************************
//********************************************************************************
int  OpenPendingOrder(int tipoin,double lotesin, double p1, int sleepagein,      double p2,     int slint,int tpint, string descrip, int magicin, int expirin, int colorin)
{
    double tpdouble = 0;
    double sldouble = 0;
    int checkin = 0;
    int ticket = 0;

   if(tipoin == OP_BUY)
   {
         RefreshRates();
         if(tpint == 0)
         {
            tpdouble = 0;
         }
         else
         {
            tpdouble = ((tpint * PointVal) + Ask);
         }


         if(slint == 0)
         {
            sldouble = 0;
         }
         else
         {
            sldouble = (Bid -(slint * PointVal));
         }
         //131 Invalid lotes
         // 130 invalid SL o TP
         ticket =  OrderSend(_Symbol, 0, lotesin, Ask, sleepagein, sldouble, tpdouble, descrip, magicin, expirin, colorin);
         int err = GetLastError();
         if(ticket > 0)
            return ticket;
         else
         {
            Print ("Error Open BUY; ",IntegerToString(err)," lotes ",DoubleToStr(lotesin), " SL ",DoubleToStr(sldouble)   ," TP ", DoubleToStr(tpdouble),"  ",TimeToStr(TimeCurrent()));
            return -1;
         }
     }


   if(tipoin == OP_SELL)
   {

         if(tpint == 0)
         {
            tpdouble = 0;
         }
         else
         {
            tpdouble = (Bid - (tpint * PointVal));
         }


         if(slint == 0)
         {
            sldouble = 0;
         }
         else
         {
            sldouble = ((slint * PointVal) + Ask);
         }
         
         ticket = OrderSend(_Symbol, 1, lotesin, Bid, sleepagein, sldouble, tpdouble, descrip, magicin, expirin, colorin);
         int err = GetLastError();

         if(ticket > 0)
            return ticket;
         else
         {
            Print ("Error Open SELL ; ",IntegerToString(err)," lotes ",DoubleToStr(lotesin), " SL ",DoubleToStr(sldouble)   ," TP ", DoubleToStr(tpdouble),"  ",TimeToStr(TimeCurrent()));
            return -1;
         };

}
     

   return -1;
  }
//*******************************************************************************
//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//*******************************************************************************
//********************************************************************************
//*******************************************************************************
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
void ini_array(int reg)
  {
   ArrayResize(aid,reg) ;
   ArrayResize(ahora,reg) ;
   ArrayResize(afecha,reg) ;
   ArrayResize(acurrency,reg) ;
   ArrayResize(aname,reg) ;
   ArrayResize(afult,reg) ;
   ArrayResize(asource,reg) ;
   ArrayResize(aimportance,reg) ;
   return ;
  }
//+------------------------------------------------------------------+
//|                                               |
//+------------------------------------------------------------------+
int DIferencia_hora(int tipoi, string par)
  {
   if(tipoi== 1)  // de Broker a pais
     {
      if(par == "USD")
         return           -7  ;
      if(par == "GBP")
         return           -3  ;
      if(par == "AUD")
         return           +8  ;
      if(par == "NZD")
         return           +10 ;
      if(par == "JPY")
         return           +6  ;
      if(par == "CAD")
         return           -7  ;
      if(par == "EUR")
         return           -3  ;
      return -7;
     }
   if(tipoi== 2) //  tipo 2 de pais a broker
     {
      if(par == "USD")
         return           +7  ;
      if(par == "GBP")
         return           +3  ;
      if(par == "AUD")
         return           -8  ;
      if(par == "NZD")
         return           -10 ;
      if(par == "JPY")
         return           -6  ;
      if(par == "CAD")
         return           +7  ;
      if(par == "EUR")
         return           +3  ;
      return +7;
     }
   datetime a = TimeLocal();   // Hora de la maquina terminal
   datetime b = TimeCurrent(); // Hora del server del Broker
// Broker  GMT+3                    Ppper_PAIS     Pais a PPER

// USD NY  (GMT-4)     +3    -4   =   -7           +7
// GBP     (GMT)       +3     0   =   -3           +3
// AUD     (GMT+11)    +3    +11  =   +8           -8
// NZD     (GMT+13)    +3    +13  =   +10          -10
// JPY     (GMT+9)     +3    +9   =   +6           -6
// CAD     (GMT-4)     +3    -4   =   -7           +7
// EUR     (GMT)       +3    0    =   -3           +3
   return 0;
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool control_hora(string &detallein)
  {
   bool respuesta = false;
   int hora_cierre = 0;
   int hora_pais = 0;
   int hora = TimeHour(TimeCurrent());
   int min  = TimeMinute(TimeCurrent());
   if((hora < hora_ini) || (hora > hora_fin))
     {
      detallein = "Fuera de Horario Broker entre "+IntegerToString(hora_ini)+"y las "+IntegerToString(hora_fin);
      Sleep(60000);
      return true;
     }
// desde las 9 hasta las 10 de de ny)  / en esta temporada es una hora menos en ecuador, osea las 8 hasta noviembre
   int diferencia = DIferencia_hora(1,"USD");
   hora_pais =  hora + diferencia ;
   if(hora_open_market == hora_pais)
     {
      detallein = "Bloqueo Apertura market 1 hora desde "+IntegerToString(hora_open_market);
      Sleep(60000);
      return true;
     }
   return respuesta;
  }
//+------------------------------------------------------------------+
//|                   |
//+------------------------------------------------------------------+
bool Maxgap(int tipo, double open, int spreadin)
  {

   double precio_tope = 0;

   if(tipo == OP_BUY)
     {
      precio_tope= open-(spreadin *  PointVal);
      if(Ask < precio_tope)
        {
         return true;
        }
     }
   else
      if(tipo == OP_SELL)
        {
         precio_tope= open+ (spreadin *  PointVal);
         if(Bid > precio_tope)
           {
            return true;
           }
        }

//printf ("MaxGap llego tipotx %d, precioopen %f, spreadmaximo %d",tipo, open,spreadin);

// borrar return false;

   return true; // se deshabilito este control
  }
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool valida_operacion_tiempo(string simbolo, datetime fechai, datetime fechaf, int tipo, int & count, double & profit)
  {
   count = 0;
   profit = 0;

   int total = OrdersHistoryTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, SELECT_BY_POS, MODE_HISTORY);
      int ticket = OrderTicket();
      string simb = OrderSymbol();
      datetime f = OrderOpenTime();
      int o = OrderType();
      if((OrderSymbol()==Symbol())   && (OrderType()== tipo) && (OrderOpenTime()>= fechai)   && (OrderOpenTime()<= fechaf)     && OrderMagicNumber() == MagicNumber)
        {
         count= count +1;
         profit= profit+ OrderProfit();
        }
     }
   if(count>0)
      return(true);
   else
      return false;
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool count_operprofit(int & numbuy, double & profitbuy, double & lotesbuyin,int & numsell, double & profitsell, double & lotessellin, double & SLin)
  {
   numbuy= 0;
   profitbuy = 0;
   lotesbuyin = 0;
   profitsell = 0;
   numsell = 0;
   lotessellin = 0;
   int total = OrdersTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, 0, 0);
      if((OrderSymbol()==Symbol())   && (OrderType()== OP_BUY)    && (OrderMagicNumber() == MagicNumber))
        {
         numbuy= numbuy +1;
         profitbuy = profitbuy+ OrderProfit();
         lotesbuyin = lotesbuyin + OrderLots();
         SLin = OrderStopLoss();
        }
      else
         if((OrderSymbol()==Symbol())   && (OrderType()== OP_SELL) && (OrderMagicNumber() == MagicNumber))
           {
            numsell= numsell +1;
            profitsell = profitsell+ OrderProfit();
            lotessellin = lotessellin + OrderLots();
            SLin = OrderStopLoss();
           }
     }
   return(true);
  }



//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool validacion_gap(int tipooperacion)
  {
   bool respuesta = false;
   double precio_menos_2 = 0;
   double precio_menos_1 = 0;
   precio_menos_2 = iClose(_Symbol, 0, 2); // Precio de cierre del Timeframe , 0 Current, periodos atras
   precio_menos_1 = iClose(_Symbol, 0, 1); // Precio de cierre del Timeframe , 0 Current, 1 peíodo atras
   double rsi5 = 0;
   double rsi15 = 0;
   rsi15 = iRSI(NULL, 5, 5, 0, 1);
   rsi15 = iRSI(NULL, 15, 5, 0, 1);

   if(tipooperacion == OP_BUY)
     {
      if((precio_menos_2 < precio_menos_1))   // Precio de cierre -2   mayor que precio de cierre -1  (esta bajando la curva)
        {
         respuesta = true;
        }
     }
   if(tipooperacion == OP_SELL)
     {
      if((precio_menos_2 > precio_menos_1))   // Precio de cierre -2   mayor que precio de cierre -1  (esta bajando la curva)
        {
         respuesta = true;
         respuesta = true;
        }
     } // de si e precio esta bajando
   return respuesta;

  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void get_estatus_operacion_b(int bonus_score)
  {
   int num_perdidas = 0;
   int totaloperaciones = 0;
   int max_tren_perdidas = 0;
   int num_vagones_maximo = 0;

   datetime dia = TimeCurrent();


//string pairs[] = {"AUDCAD", "AUDUSD", "EURUSD", "GBPAUD", "GBPUSD", "NZDUSD", "USDCAD", "USDJPY","BTCUSD","ETHUSD"};
   int colas [10] ;
   ArrayInitialize(colas,0);
   int total = OrdersTotal();
   for(int j=0; j<= total -1; j++)
     {
      bool check = OrderSelect(j, 0, 0);
      for(int k = 0; k < ArraySize(pairs); k++)
        {
         if((OrderSymbol()==pairs[j])    && (OrderMagicNumber()==MagicNumber))
           {
            colas[j]++;
           }
        }
     }

   return ;
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void get_estatus_operacion()
  {

   int total = OrdersTotal();
   for(int j=0; j<= total -1; j++)
     {
      bool check = OrderSelect(j, 0, 0);
      int m = OrderMagicNumber();
      string sim = OrderSymbol();
      for(int k = 0; k < ArraySize(pairs); k++)
        {

         if((OrderSymbol()==pairs[k])    && (OrderMagicNumber()==MagicNumber))
           {
            cur_colas[k]++;
           }
        }
     }

   return ;
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string get_num_dependencias(string simbolo)
  {
   string num_dependencias = "";
   int indice = 0;



   for(int j = 0; j < ArraySize(pairs); j++)
     {
      if(simbolo==pairs[j])
        {
         indice = j;
        }
     }

   return dependencia[indice] ;

  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool existe_dependencia(string simbolo, int tamano_cola)
  {
   bool existe = false;
   ArrayInitialize(cur_colas,0);
   get_estatus_operacion();

   string dep = get_num_dependencias(simbolo);
   string valuesArray[];
   int count = StringSplit(dep, ',', valuesArray);

   for(int j = 0; j < count; j++)
     {
      int indice = (int)StringToInteger(valuesArray[j]);
      int cola_simbolo = cur_colas[indice];
      if(cola_simbolo >= tamano_cola)
        {
         existe = true;
         break;
        }
     }

   return existe ;

  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void write_log(string operacion,string evento,double SL,double TP,string tipo_precio,double precio,int ticket,double SL_ant,double TP_ant,double profit,double Eq,double price_open,string adicionales)
  {
   int account = AccountNumber();
   string linea2 = "cuenta"+ ";" +
                   "fecha"+ ";" +
                   "par" + ";" +
                   "operacion" + ";" +
                   "ticket" + ";" +
                   "price_open" + ";" +
                   "evento" + ";" +
                   "SL" + ";" +
                   "TP" + ";" +
                   "profit" + ";" +
                   "open -SL" + ";" +
                   "open -TP" + ";" +
                   "SL_ant"  + ";"+
                   "TP_ant"  + ";" +
                   "tipo_precio" + ";" +
                   "precio" + ";" +
                   "Ask" + ";" +
                   "Bid" + ";" +
                   "precio-SL" + ";" +
                   "precio-TP" + ";" +
                   "TP-SL" + ";" +
                   "pips TP-SL" + ";" +
                   " % (precio-TP)/ (precio-SL)" + ";" +
                   "SL_ant- SL"  + ";"+
                   "pips(SL_ant- SL)"  + ";"+
                   "TP_ant- TP"  + ";" +
                   "pips(TP_ant- TP)"  + ";" +
                   "Eq" + ";" +
                   "StartingLots" + ";" +
                   "factor_lote_indicador" + ";" +
                   "adicionales"   ;

   string linea =

      IntegerToString(account)+ ";" +
      TimeToStr(TimeCurrent())+ ";" +
      Symbol() + ";" +
      operacion + ";" +
      IntegerToString(ticket) + ";" +
      DoubleToStr(price_open) + ";" +
      evento + ";" +
      DoubleToStr(SL) + ";" +
      DoubleToStr(TP) + ";" +
      DoubleToStr(profit) + ";" +

      DoubleToStr(MathAbs(price_open - SL)) + ";" +
      DoubleToStr(MathAbs(price_open - TP)) + ";" +

      DoubleToStr(SL_ant)  + ";"+
      DoubleToStr(TP_ant)  + ";" +


      tipo_precio + ";" +
      DoubleToStr(precio) + ";" +
      DoubleToStr(Ask) + ";" +
      DoubleToStr(Bid) + ";" +

      DoubleToStr(MathAbs(precio-SL)) + ";" +
      DoubleToStr(MathAbs(precio-TP)) + ";" +

      DoubleToStr(MathAbs(TP-SL)) + ";" +
      DoubleToStr(MathAbs(TP-SL) / PointVal) + ";" +


      DoubleToStr(MathAbs((precio-TP)/ (precio-SL)*100)) + ";" +

      DoubleToStr(MathAbs(SL_ant- SL))  + ";"+
      DoubleToStr(MathAbs(SL_ant- SL)   / PointVal)  + ";"+

      DoubleToStr(MathAbs(TP_ant- TP))  + ";" +
      DoubleToStr(MathAbs(TP_ant- TP)  / PointVal)  + ";" +

      DoubleToStr(Eq) + ";" +
      DoubleToStr(StartingLots) + ";" +
      DoubleToStr(factor_lote_indicador) + ";" +
      adicionales   ;
   int archivo = 0;
   string strIndicador = "log_oper_"+ TimeToStr(TimeCurrent(),TIME_DATE)+".csv";
   bool imprimir_cab = false;


   if(!FileIsExist(strIndicador))
     {
      imprimir_cab = true;
     }

   archivo = FileOpen(strIndicador,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ);
   if(imprimir_cab)
     {
      FileWrite(archivo,linea2);
     }

   while(!FileIsEnding(archivo))
      FileReadString(archivo) ; //ir hasta el final del archivo

   FileWrite(archivo,linea);
//send_wlog( linea);
   FileClose(archivo);

   return;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
datetime Add_Fecha(datetime dateTime,int num, string periodo)
  {
   datetime new_date = 0;
   int year =   TimeYear(dateTime);
   int month =  TimeMonth(dateTime);
   int day =    TimeDay(dateTime);
   int hour =   TimeHour(dateTime);
   int minute = TimeMinute(dateTime);
   int second = TimeSeconds(dateTime);

//  return StringFormat("%04d-%02d-%02d %02d:%02d:%02d", year, month, day, hour, minute, second);
//datetime new_date = StringToTime(StringFormat("%04d-%02d-%02d 00:00:00", year, month, day));
   if(periodo == "dd")  // cambio de día
     {
      new_date =   dateTime + num * 24*60*60;
      int h =      TimeHour(new_date) * 60 * 60;
      int m =      TimeMinute(new_date)* 60;

      new_date =   new_date - h - m;

     }
   if(periodo == "hh")
     {
      new_date =   dateTime + (num * 60 * 60);
     }
   if(periodo == "mm")
     {
      new_date =   dateTime + (num  * 60);

     }
   return new_date;
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool  ActualizaTP(/*int tipoin,*/double TP1, double SL1)
  {
   int i;
   bool respuesta = false;
   int order_check1;
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   double SL2 =  NormalizeDouble(SL1,digits);
   double TP2 =  NormalizeDouble(TP1,digits);

   i = OrdersTotal() - 1;
   if(i < 0)
      return false;
   do
     {
      order_check1 = OrderSelect(i, 0, 0);
      printf("ActualizaTP ; OrderTicket() %d OrderOpenPrice() %f SL2 %f TP2 %f ",OrderTicket(),OrderOpenPrice(), SL2, TP2);
      if((OrderSymbol() == _Symbol) && (OrderMagicNumber() == MagicNumber) /*&& (OrderType() == tipoin)*/)
        {
            bool order_checkn = OrderModify(OrderTicket(), OrderOpenPrice(), SL2, TP2, 0, 65535);
            if(!order_checkn)
            {   
               int err = GetLastError();
               printf("Error ActualizaTP:  + ErrorDescription(error)   Ticket  %d"+" "+TimeToStr(TimeCurrent()),OrderTicket());
            }       
        }
      i = i - 1;
     }
   while(i >= 0);


   return (true);
  }


//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
double profit()
  {
   double ldProfit = 0;
   for(int i=OrdersTotal(); i>=1; i--)
     {
      if(OrderSelect(i-1,SELECT_BY_POS,MODE_TRADES)!=true)
         continue;
      ldProfit+=OrderProfit()+OrderCommission()+OrderSwap();
     }
   return(NormalizeDouble(ldProfit,2));
  }
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
string limpiar_string(string strin)
  {
   string textolimpio = strin;
   while(StringFind(textolimpio, "\"") >= 0)
     {
      StringReplace(textolimpio, "\"","");
     }
   return textolimpio;
  }
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
string limpiar_fecha(string strin)
  {

   string textolimpio = strin;
   while(StringFind(textolimpio, "-") >= 0)
     {
      StringReplace(textolimpio, "-",".");
     }

   return textolimpio;
  }
//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
bool   proceso_cronos(datetime & fechain)
  {
   if(fechain == 0)
      return true;
   if(TimeCurrent() > fechain)
     {
      fechain = 0;
      descrip_no_proceso=  "";
      return true;
     }
   else
     {
      return false;
     }
  }


//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void closeOrdersAll()
  {
   for(int i=1; i<=OrdersTotal(); i++)
     {
      if(OrderSelect(i,0,0))
         if(OrderSymbol()==Symbol())
           {
            if(orderClose())
              {
               printf("Se ha cerrado EA la orden con ticket %d"+" "+TimeToStr(TimeCurrent()),OrderTicket());
               //return(true);
              }
           }
      Sleep(1000);
     }
//return(false);
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
int orderOpen()
  {
   for(int i=1; i<=OrdersTotal(); i++)
     {
      if(OrderSelect(i-1,SELECT_BY_POS)!=true)
         continue;
      if(OrderMagicNumber()!=MagicNumber)
         continue;
      if(OrderType()!=OP_BUY && OrderType()!=OP_SELL)
         continue;
      return(OrderType());
     }
   return(OP_NA);
  }
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
string getPeriod(int piPeriod)
  {
   switch(piPeriod)
     {
      case 1:
         return("M1");
         break;
      case 5:
         return("M5");
         break;
      case 15:
         return("M15");
         break;
      case 30:
         return("M30");
         break;
      case 60:
         return("H1");
         break;
      case 240:
         return("H4");
         break;
      case 1440:
         return("D1");
         break;
      case 10080:
         return("W1");
         break;
      case 43200:
         return("MN1");
         break;
      case PERIOD_CURRENT:
         return(getPeriod(Period()));
         break;
      default:
         return("");
         break;
     }
  }
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool orderClose(int piPorc=100)
  {
   double ldPrecio = 0;
   for(int i=0; i<=10; i++)
     {
      //1.- En el momento de lanzar la orden no este la meta ocupada por como EA
      //2.- Que el contexto de negociación no esté ocupado.
      while(IsTradeContextBusy() || !IsTradeAllowed())
         Sleep(30);

      RefreshRates();

      double ldLots = NormalizeDouble(OrderLots()/100*piPorc,2);
      if(OrderClose(OrderTicket(),ldLots,OrderClosePrice(),0,clrBlack))
        {
         return(true);
        }
      Sleep(200);
     }

   int error=GetLastError();
   printf("Error al cerrar la orden. Error:  + ErrorDescription(error)   Ticket  %d"+" "+TimeToStr(TimeCurrent()),OrderTicket());
   return(false);
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void btClose()
  {
   if(ObjectFind(0,btClose) >= 0)
      ObjectDelete(btClose);
   ButtonCreate(0,btClose,      0,120,15,110,25,CORNER_RIGHT_UPPER,"Close orders symbol","Arial",8,clrWhite,clrRed,clrWhite,false,false,false,true,0);
//   ButtonCreate(0,btClosesymbol,0,60,60,110,25,CORNER_RIGHT_UPPER,"Close orders Symbol","Arial",8,clrWhite,clrRed,clrWhite,false,false,false,true,0);

  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
bool New_bar(long & time_in)
  {
   if(time_in == Time[0])
     {
      return false;
     }
   time_in = Time[0];

   return true;
  }


//+------------------------------------------------------------------+
//| Create the button                                                |
//+------------------------------------------------------------------+
bool ButtonCreate(const long              chart_ID=0,               // chart's ID
                  const  string            name="Button",            // button name
                  const int               sub_window=0,             // subwindow index
                  const int               x=0,                      // X coordinate
                  const int               y=0,                      // Y coordinate
                  const int               width=50,                 // button width
                  const int               height=18,                // button height
                  const ENUM_BASE_CORNER  corner=CORNER_LEFT_UPPER, // chart corner for anchoring
                  const string            text="Button",            // text
                  const string            font="Arial",             // font
                  const int               font_size=10,             // font size
                  const color             clr=clrBlack,             // text color
                  const color             back_clr=C'236,233,216',  // background color
                  const color             border_clr=clrNONE,       // border color
                  const bool              state=false,              // pressed/released
                  const bool              back=false,               // in the background
                  const bool              selection=false,          // highlight to move
                  const bool              hidden=true,              // hidden in the object list
                  const long              z_order=0)                // priority for mouse click
  {
//--- reset the error value
   ResetLastError();
//--- create the button

   ObjectDelete(chart_ID,name);

   if(!ObjectCreate(chart_ID,name,OBJ_BUTTON,sub_window,0,0))
     {
      notificacion(__FUNCTION__+
                   ": failed to create the button! Error code = "+(string)GetLastError());
      return(false);
     }
//--- set button coordinates
   ObjectSetInteger(chart_ID,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(chart_ID,name,OBJPROP_YDISTANCE,y);


//--- set button size
   ObjectSetInteger(chart_ID,name,OBJPROP_XSIZE,width);
   ObjectSetInteger(chart_ID,name,OBJPROP_YSIZE,height);
//--- set the chart's corner, relative to which point coordinates are defined
   ObjectSetInteger(chart_ID,name,OBJPROP_CORNER,corner);
//--- set the text
   ObjectSetString(chart_ID,name,OBJPROP_TEXT,text);
//--- set text font
   ObjectSetString(chart_ID,name,OBJPROP_FONT,font);
//--- set font size
   ObjectSetInteger(chart_ID,name,OBJPROP_FONTSIZE,font_size);
//--- set text color
   ObjectSetInteger(chart_ID,name,OBJPROP_COLOR,clr);
//--- set background color
   ObjectSetInteger(chart_ID,name,OBJPROP_BGCOLOR,back_clr);
//--- set border color
   ObjectSetInteger(chart_ID,name,OBJPROP_BORDER_COLOR,border_clr);
//--- display in the foreground (false) or background (true)
   ObjectSetInteger(chart_ID,name,OBJPROP_BACK,back);
//--- set button state
   ObjectSetInteger(chart_ID,name,OBJPROP_STATE,state);
//--- enable (true) or disable (false) the mode of moving the button by mouse
   ObjectSetInteger(chart_ID,name,OBJPROP_SELECTABLE,selection);
   ObjectSetInteger(chart_ID,name,OBJPROP_SELECTED,selection);
//--- hide (true) or display (false) graphical object name in the object list
   ObjectSetInteger(chart_ID,name,OBJPROP_HIDDEN,hidden);
//--- set the priority for receiving the event of a mouse click in the chart
   ObjectSetInteger(chart_ID,name,OBJPROP_ZORDER,z_order);
//--- successful execution
   return(true);
  }


//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void notificacion(string psMensaje)
  {
   gsLog = psMensaje;
   string lsMensaje = Symbol() +"(" +getPeriod(Period()) +")" +": " +psMensaje;
   if(PopupAlert)
      Alert(lsMensaje);
   else
      Print(psMensaje);
   if(PushAlert)
      SendNotification(lsMensaje);
//  if (EmailAlert) SendMail(lsMensaje, psMensaje);
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void objectsDelete()
  {
   for(int i=ObjectsTotal(); i>=0; i--)
     {
      if(StringFind(ObjectName(i),(string)MagicNumber,0)>=0)
        {
         ObjectDelete(0,ObjectName(i));
        }
     }
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void DrawLabel(string name,string txt,int x, int y, color col, int LabelCorner, int size, string font)
  {
   if(ObjectFind(0, name) == -1)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_CORNER, LabelCorner);
      if(LabelCorner == CORNER_LEFT_LOWER || LabelCorner == CORNER_LEFT_UPPER)
         ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
      if(LabelCorner == CORNER_RIGHT_LOWER || LabelCorner == CORNER_RIGHT_UPPER)
         ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_RIGHT);


      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
      if(col != clrNONE)
         ObjectSetInteger(0, name, OBJPROP_COLOR, col);
      ObjectSetString(0, name, OBJPROP_FONT, font);
      ObjectSetString(0, name, OBJPROP_TEXT, txt);
      ObjectSetInteger(0, name, OBJPROP_CORNER, LabelCorner);

     }
   if(ObjectGetInteger(0, name, OBJPROP_XDISTANCE) != x)
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   if(ObjectGetInteger(0, name, OBJPROP_YDISTANCE) != y)
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   if(ObjectGetInteger(0, name, OBJPROP_COLOR) != col)
      ObjectSetInteger(0, name, OBJPROP_COLOR, col);
  }



//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long& lparam, const double& dparam, const string& sparam)
  {
   if(id==CHARTEVENT_OBJECT_CLICK)
     {
      if(sparam==btClose)
        {
         if(orderOpen()!=OP_NA)
           {
            if(MessageBox("¿Estás seguro de cerrar todo?","ADVERTENCIA",1)==1)
              {
               notificacion("Se cierran todas las órdenes abiertas en este momento.");
               closeOrders();
              }
           }
         else
           {

            if(sparam==btClosesymbol)
              {

               if(orderOpen()!=OP_NA)
                 {
                  if(MessageBox("¿Estás seguro de cerrar todas operacionde de esta moneda?","ADVERTENCIA",1)==1)
                    {
                     notificacion("Se cierran todas las órdenes abiertas de esta moneda en este momento.");
                     closeOrderssymbol();
                    }

                 }
               else
                 {
                  Alert("No hay operaciones abiertas.");

                 }
              }


            Sleep(100);
            btDelete(ChartID(),btClose);
            btClose();
           }

        }
     }

  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void closeOrders(int piType=-1)
  {
   while(orderOpen()!=OP_NA)
     {
      for(int i=OrdersTotal(); i>0; i--)
        {
         if(OrderSelect(i-1,SELECT_BY_POS)!=true)
            continue;
         if(OrderMagicNumber() != MagicNumber)
            continue;
         if(OrderType()!=OP_BUY && OrderType()!=OP_SELL)
            continue;

         if(piType!=-1)
           {
            if(piType!=OrderType())
               continue;
           }
         if(orderClose())
           {
            notificacion("Se ha cerrado la orden con ticket " +IntegerToString(OrderTicket()) +" con un profit de " +print(OrderProfit(),2) +".");
            //return(true);
           }
        }
      Sleep(1000);
     }
//return(false);
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void closeOrderssymbol(int piType=-1)
  {

   for(int i=OrdersTotal(); i>0; i--)
     {
      if(OrderSelect(i-1,SELECT_BY_POS)!=true)
         continue;
      if(OrderMagicNumber() != MagicNumber)
         continue;
      if(OrderType()!=OP_BUY && OrderType()!=OP_SELL)
         continue;
      if(OrderSymbol()!=Symbol())
         continue;


      if(piType!=-1)
        {
         if(piType!=OrderType())
            continue;
        }

      if(orderClose())
        {
         notificacion("Se ha cerrado la orden con ticket " +IntegerToString(OrderTicket()) +" con un profit de " +print(OrderProfit(),2) +".");
         //return(true);
        }

     }

//return(false);
  }


//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
string print(double pdValor, int piDecimales)
  {
   return(DoubleToStr(NormalizeDouble(pdValor,piDecimales),piDecimales));
  }


//+------------------------------------------------------------------+
//| Delete the button                                                |
//+------------------------------------------------------------------+
bool btDelete(const long   chart_ID=0,    // chart's ID
              const string name="Button") // button name
  {
   if(ObjectFind(ChartID(),name)<0)
      return(false);
//--- reset the error value
   ResetLastError();
//--- delete the button
   if(!ObjectDelete(chart_ID,name))
     {
      Print(__FUNCTION__,
            ": failed to delete the button! Error code = ",GetLastError());
      return(false);
     }
//--- successful execution
   return(true);
  }




//+------------------------------------------------------------------+
//|                                                 |
//+------------------------------------------------------------------+
bool Calculo_Lotes()
  {
//extern double Propocion_Lote = 0.6 ; // parametro para AUTOLOT
//extern double Proporcion_Balance = 50000 ;//  // parametro para AUTOLOT
// Por cada 50.000 de Balance el lote es 0.2
   double balance_calculo = AccountEquity(); // Balance
   StartingLots = (balance_calculo / Proporcion_Balance) * Propocion_Lote      ;
   if(StartingLots < MinLots)
      StartingLots =MinLots;
   return true;
  }

//**********************************************************************************
//**********************************************************************************
bool indicador_online(double & indice)
  {
   string headers = "Content-Type: application/json";
   char result[];
   bool respuesta = false ;
   string symbol = Symbol();

   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];

   string api_url = "https://tradinapi.azurewebsites.net/neobot/";

   string post = "{"+ "\"par\":\"" + Symbol()  + "\","+ "\"time_frame\":\""+IntegerToString(timeframeIndicador)+"\""                                    + "}";

   char postArray[];
   int length = StringToCharArray(post, postArray);

   int res = WebRequest("GET", api_url, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      Print("Error in WebRequest indicador online. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' in the list of allowed URLs on tab 'Expert Advisors'", "Error", MB_ICONINFORMATION);
      return(false);
     }
   resultado= CharArrayToString(result);
   int numero = StringSplit(resultado, ':',par_respuesta);

   numero = StringSplit(par_respuesta[1], '}',indice_respuesta);
   indice = StringToDouble(indice_respuesta[0]);
   return(true);
  }

//+------------------------------------------------------------------+
//| Score_online                                       |
//+------------------------------------------------------------------+
double  Score_online(string simboloin, int tipo_in)
  {
   bool resp = false;
   double score_out = 0;
   if(indicador_online(score_out))
     {
      if(score_out == 0)
         printf("Score Calculado: %f"+" "+TimeToStr(TimeCurrent()), score_out);
      return score_out;
     }
   else
     {
      printf("Error en score %f"+" "+TimeToStr(TimeCurrent()), score_out);
     }
   return (false);
  }


//+------------------------------------------------------------------+
//| Cambio de dia                    |
//+------------------------------------------------------------------+
bool Cambio_de_dia(datetime fecha_base)
  {
   int hoy=     TimeDayOfYear(TimeCurrent());
   int tdate =  TimeDayOfYear(fecha_base) ;

   if(hoy > tdate)
      return true;
   else
      return false;
  }
//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
void Carga_eventos(datetime fechain, datetime & fecha_analisis, int & reg)
  {
   if(Cambio_de_dia(fecha_analisis))
     {
      fecha_analisis = TimeCurrent();
      bool rr =  qry_events_onlines(fecha_analisis, reg);
      // Carga de la base online los eventos de la fecja mencionada
     }
   return ;
  }
//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
// retorn true si hay alertas y no se debe procesar.
bool Alertas(int tipo_control_evento_in, int & flag_alerta_in, datetime & fecha_risk_in, double & risky_in, datetime & ult_fecha_eventosin, int regs)
  {
   int num_events = 0;
   int eventos_dia[];
   int nivel_riesgo_in = 1;   // para consultar los evetos con esa mportance 1 H 2 MH  3 LMH
//int time_antes_evento = 5; // tiempo de consulta antes del evento.
//int time_despues_del_evento = 55;  // espacio de tiempos de laa consulta

// Si la hora del siguiente proceso aún no llega

   datetime tempdate = TimeLocal()+(TimeCurrent() - TimeLocal());  // convertir hora metatrader
   datetime finicial = 0;
   datetime ffinal   = 0;

//if(flag_alerta_in && (hora_sigp_eventos < tempdate))

   if((0 < hora_sigp_eventos) && (hora_sigp_eventos > tempdate))
      return true;
// si la hora de eventos ya pasó.

// En el arreglo de mwmoria se buscan todos los ventos que cumplan con los filtros y los saca en un arreglo donde estan los punteros de los eventos.
// Busca en el archivo, los eventos    desde tiemecurrent - tiempo antes hasta timecurrent + tiempo después.

   string parbuscado = "";// puede enviarse GBPUSD   USD  o "" donde busca todos
   parbuscado = Symbol();

//   Filtrar_eventos (string simbolo ,int &eventosin[] ,int time_antes_in,int time_despues_in     ,int regs, int & encontrados,int nivel_riesgo_in)
// si el control es por día.
   if(tipo_control_evento_in == 1) // Todo el día
     {
      //Si es cambio de día quita el riesgo y actualuza la fecha
      /*      eval_risk_dia(TimeCurrent(), fecha_risk_in, risky_in, flag_alerta_in);

            if(flag_alerta_in == 1)
              {
               ObjectDelete("Alerta");
               DrawLabel("Alerta","Alert EVENTOS risky = "+ DoubleToStr(risky_in,3), 10,  60, clrRed, CORNER_RIGHT_UPPER,8, "Arial");
               return true;
              }
            else
              {
               ObjectDelete("Alerta");
               DrawLabel("Alerta","No Alert, risky = "+ DoubleToStr(risky_in,3), 10,  60, clrBlue, CORNER_RIGHT_UPPER,8, "Arial");
               return false;
              }

       ojo ojo ojo este es el cambio para validacion del día completo   */

      datetime hoy = TimeCurrent();
      datetime iniciodia = FormatDateZero(TimeCurrent());
      finicial = iniciodia;
      ffinal   = iniciodia + 22*60*60;
      //time_antes_evento =        FormatDateZero(TimeCurrent())-TimeCurrent())  ;
      //time_despues_del_evento =  (int)MathAbs(FormatDateZero(TimeCurrent())-TimeCurrent()+(22*60*60)) ;
     }
//**********************************************************
   if(tipo_control_evento_in == 2)  // por el tiempo del evento
     {
      /*ojo ojo ojo igual que el anterior para controlar todo dia*/

      finicial = TimeCurrent()-time_antes_evento*60;
      ffinal   =TimeCurrent() + time_despues_del_evento*60;

     }
   if(Filtrar_eventos(parbuscado,eventos_dia,     finicial,ffinal,regs, num_events,      nivel_riesgo_in))          //con comillas busca todos los pares
     {
      flag_alerta_in = true;

      int ult_evento = 0;
      string descrip = "";
      string curren = "";
      datetime ult_hora_evento = max_hora_evento(eventos_dia, num_events,ult_evento,descrip,curren);

      //hora_sigp_eventos = ult_hora_evento + (time_despues_del_evento*60) ;
      hora_sigp_eventos = ffinal ;


      // borrar Send_Message ("EVENT IMPORT "+curren, descrip, "");
      return true;
     }
   else
     {
      // si no encontro eventos, se retorna y se actualiza la fecha del siguiente proceso.
      flag_alerta_in = false;
      hora_sigp_eventos = TimeCurrent()+(time_despues_del_evento * 60);
      return false;
     }

   /*     }   igual eventod todo el día */
   return false;
  }
//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
bool Filtrar_eventos(string simbolo,int &eventosin[],datetime fechaini,datetime fechafin,int regs,int & encontrados,int nivel_riesgo_in)
  {

//Si no entra el simbolo
   bool respuesta = false;
   encontrados = 0;
//datetime fechaini = TimeCurrent()- (time_antes_in * 60);
//datetime fechafin = TimeCurrent()+ (time_despues_in*60);
//datetime fechaini = tmpdatel+ ( tmpdatec - tmpdatel)- (time_antes_in * 60);  // hora metatrader
//datetime fechafin = tmpdatel+ ( tmpdatec - tmpdatel) +(time_despues_in*60);  // hora metatrader
   string simbolo_origen = "";
   string simbolo_base =   "";

//  Primero los cuenta

   for(int i = 0; i< regs; i++)
     {


      if(StringLen(simbolo) == 6)
        {
         simbolo_origen = StringSubstr(simbolo,0,3);
         simbolo_base =   StringSubstr(simbolo,0,3);

         if((afecha[i]>fechaini)   && (afecha[i]<= fechafin)     && ((acurrency[i]== simbolo_origen)  || (acurrency[i]== simbolo_base)))
           {
            if((nivel_riesgo_in==1) && (aimportance[i] == "High"))
               encontrados ++;

            if((nivel_riesgo_in==2) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")))
               encontrados ++;

            if((nivel_riesgo_in==3) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")  || (aimportance[i] == "Low")))
               encontrados ++;
           }
        }
      else
         if(StringLen(simbolo) == 3)
           {
            if((afecha[i]>fechaini)   && (afecha[i]<= fechafin)   && (acurrency[i]== simbolo))
              {
               if((nivel_riesgo_in==1) && (aimportance[i] == "High"))
                  encontrados ++;

               if((nivel_riesgo_in==2) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")))
                  encontrados ++;

               if((nivel_riesgo_in==3) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")  || (aimportance[i] == "Low")))
                  encontrados ++;
              }
           }
         else
           {
            if((afecha[i]>fechaini)   && (afecha[i]<= fechafin))
              {
                 {
                  if((nivel_riesgo_in==1) && (aimportance[i] == "High"))
                     encontrados ++;

                  if((nivel_riesgo_in==2) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")))
                     encontrados ++;

                  if((nivel_riesgo_in==3) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")  || (aimportance[i] == "Low")))
                     encontrados ++;
                 }
              }
           }
     }
// Si no encuentra sale
   if(encontrados == 0)
      return false;

   ArrayFree(eventosin);
   ArrayResize(eventosin,encontrados+1);
   int j= 0;

   for(int i = 0; i< regs; i++)
     {


      if(StringLen(simbolo) == 6)
        {
         simbolo_origen = StringSubstr(simbolo,0,3);
         simbolo_base =   StringSubstr(simbolo,0,3);

         if((afecha[i]>fechaini)   && (afecha[i]<= fechafin)     && ((acurrency[i]== simbolo_origen)  || (acurrency[i]== simbolo_base)))
           {
            if((nivel_riesgo_in==1) && (aimportance[i] == "High"))
              {
               eventosin[j]= i;
               j ++;
              }

            if((nivel_riesgo_in==2) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")))
              {
               eventosin[j]= i;
               j ++;
              }

            if((nivel_riesgo_in==3) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")  || (aimportance[i] == "Low")))
              {
               eventosin[j]= i;
               j ++;
              }
           }
        }
      else
         if(StringLen(simbolo) == 3)
           {
            if((afecha[i]>fechaini)   && (afecha[i]<= fechafin)   && (acurrency[i]== simbolo))
              {
               if((nivel_riesgo_in==1) && (aimportance[i] == "High"))
                 {
                  eventosin[j]= i;
                  j ++;
                 }

               if((nivel_riesgo_in==2) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")))
                 {
                  eventosin[j]= i;
                  j ++;
                 }

               if((nivel_riesgo_in==3) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")  || (aimportance[i] == "Low")))
                 {
                  eventosin[j]= i;
                  j ++;
                 }
              }
           }
         else
           {
            if((afecha[i]>fechaini)   && (afecha[i]<= fechafin))
              {
                 {
                  if((nivel_riesgo_in==1) && (aimportance[i] == "High"))
                    {
                     eventosin[j]= i;
                     j ++;
                    }

                  if((nivel_riesgo_in==2) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")))
                    {
                     eventosin[j]= i;
                     j ++;
                    }

                  if((nivel_riesgo_in==3) && ((aimportance[i] == "High")    || (aimportance[i] == "Medium")  || (aimportance[i] == "Low")))
                    {
                     eventosin[j]= i;
                     j ++;
                    }
                 }

              }
           }

     } //del for
   return true;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
bool qry_events_onlines(datetime fechai,int & reg)
  {
   string headers = "Content-Type: application/json";
   char result[];
   bool respuesta = false ;
   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   char postArray[];
   string api_url = "https://tradinapi.azurewebsites.net/eventos/";

   datetime  ffecha = 0 ;
   datetime  fult  = 0 ;
   datetime  fhora = 0 ;
   int uid = 0 ;

   string scab ;
   string sid ;
   string scurrency;
   string sname;
   string sfecha;
   string sfult;
   string ssource;
   string simportance;

   int k=0;
   int hh= 0;
   int mm = 0;
   int ss = 0;



   string formattedDateini = FormatDateTimeToCustomFormat2(fechai);

   string url_with_params = api_url  + "?fecha=" + formattedDateini ;
   int length  = StringToCharArray(api_url, postArray);
   ResetLastError();
   int res = WebRequest("GET", url_with_params, cookie, NULL, timeout, postArray, length, result, headers);

   if(res == -1)
     {
      Print("Error in WebRequest qry_events_onlines. Error code =", GetLastError());
      return(false);
     }

   resultado= CharArrayToString(result);

   int numero = StringSplit(resultado, ',',par_respuesta);
   if(MathMod(numero-3,13)!= 0)
      return false;
   string campo = "";

   int     num  = StringSplit(par_respuesta[0], ':',indice_respuesta);
   reg  = (int) StringToInteger(indice_respuesta [1]);
   num  = StringSplit(par_respuesta[1], ':',indice_respuesta);
   num  = StringSplit(par_respuesta[2], ':',indice_respuesta);

   ini_array(reg);

   for(int i= 3 ; i< numero; i++)
     {

      int numero2 = StringSplit(par_respuesta[i], ':',indice_respuesta);


      if((MathMod(i,13)== 6) || (MathMod(i,13)== 7) || (MathMod(i,13)== 0) || (MathMod(i,13)== 1) || (MathMod(i,13)== 2))
        {
         scab = indice_respuesta [1]; // fill
        }
      if(MathMod(i,13) == 3)
        {
         sid =     indice_respuesta [numero2-1];                          // id
         uid = (int)  StringToInteger(sid);
        }
      if(MathMod(i,13) == 4)
        {
         string field = indice_respuesta [0];
         hh = StrToInteger(StringSubstr(indice_respuesta [1],1,2));
         mm = StrToInteger(indice_respuesta [2]);
         ss = StrToInteger(StringSubstr(indice_respuesta [3],0,2));


        }
      if(MathMod(i,13) == 5)
        {
         sfecha=     indice_respuesta [1];                    // fecha
         ffecha = 0 ;
        }
      if(MathMod(i,13) == 8)
        {
         scurrency =   indice_respuesta [1];                           // currency
        }
      if(MathMod(i,13) == 9)
        {
         sname =     indice_respuesta [1];                        // id name
        }
      if(MathMod(i,13) == 10)
        {
         sfult=    indice_respuesta [1];                   // ult
        }
      if(MathMod(i,13) == 11)
        {
         ssource =  indice_respuesta [1];
        }
      if(MathMod(i,13) == 12)
        {
         simportance = indice_respuesta [1];
        }
      if(MathMod(i,13)== 2)
        {
         aid [k]=   uid;
         //                 ahora [k]= shora;
         acurrency  [k]= limpiar_string(scurrency);
         aname  [k]= limpiar_string(sname);
         afult [k] =  limpiar_string(sfult);
         asource  [k]= limpiar_string(ssource);
         aimportance  [k] = limpiar_string(simportance);

         string str_temp = limpiar_fecha(StringSubstr(sfecha,1,10));
         sfecha =str_temp+ StringFormat(" %02d:%02d:%02d",hh, mm, ss);

         datetime fech_temp =  StrToTime(sfecha)+ (TimeCurrent() - TimeLocal());
         afecha [k]= fech_temp; // hora metatrader
         ahora[k] = StringFormat("%02d:%02d:%02d", TimeHour(afecha[k]),TimeMinute(afecha[k]), TimeSeconds(afecha[k]));  // hora metatrader
         k++;
        }
     }
   return true;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
bool alert_event(datetime fechai, datetime fechaf,
                 string symbol,
                 string & pcurrency,
                 string & pname,
                 datetime & pfecha,
                 double & ppips_ant,
                 double  & pcount_events,
                 double & pmax_pips,
                 double  & pprom_pips,
                 datetime  &pult_event
                )
  {
   string sproceso;
   string sid ;
   string spar;
   string scurrency;
   string sname;
   string sfecha;
   string spips_ant;
   string scount_events;
   string smax_pips;
   string sprom_pips;
   string sult_event;

   int    uid = 0 ;
   string upar = "";
   string ucurrency = "";
   string uname = "";
   datetime ufecha = 0;
   double upips_ant = 0;
   double ucount_events = 0;
   double umax_pips = 0;
   double uprom_pips = 0;
   datetime uult_event = 0;

   string headers = "Content-Type: application/json";
   char result[];
   bool respuesta = false ;
   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   char postArray[];
   string api_url = "https://tradinapi.azurewebsites.net/alertaeventos/";

   string formattedDateini = FormatDateTimeToCustomFormat2(fechai);
   string formattedDatefin = FormatDateTimeToCustomFormat2(fechaf);

   string post = "{";
   post += "\"par\": \"" + symbol + "\",";
   post += "\"fecha_inicio\": \"" + formattedDateini + "\",";
   post += "\"fecha_fin\": \""    + formattedDatefin + "\"";
   post += "}";


   string url_with_params = api_url + "?par=" + symbol + "&fecha_inicio=" + formattedDateini + "&fecha_fin=" + formattedDatefin;
   int length = StringToCharArray(post, postArray);
   int res = WebRequest("GET", url_with_params, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      Print("Error in WebRequest alert event. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' o revise dado que no está respondiendo a tiempo el servicio", "Error", MB_ICONINFORMATION);
      return(false);
     }
   resultado= CharArrayToString(result);
   /*
   {"alerts":[{"id":29,
              "par":4,
              "currency":"",
              "name":"Retail Sales m/m",
              "fecha":"2024-01-30",
               "pips_ant":-80.7000000000002,
               "count_events":13,
               "max_pips":264.600000000002,
               "prom_pips":72.4538461538463,
               "ult_event":"2024-01-09"}
               ]}
    */
   pcurrency = "";
   pname = "";
   pfecha = 0;
   ppips_ant = 0;
   pcount_events = 0;
   pmax_pips = 0;
   pprom_pips = 0;
   pult_event = 0;

   int numero = StringSplit(resultado, ',',par_respuesta);
   if(MathMod(numero,11)!= 0)
      return false;
   int i = 0;
   for(i= 0 ; i< numero; i++)
     {
      int numero2 = StringSplit(par_respuesta[i], ':',indice_respuesta);


      if(MathMod(i,11)== 0)
        {

        }
      if(MathMod(i,11)== 1)
        {
         sid = indice_respuesta [1];
        }
      if(MathMod(i,11)== 2)
        {
         spar = indice_respuesta [1];
        }
      if(MathMod(i,11)== 3)
        {
         scurrency = indice_respuesta [1];
        }
      if(MathMod(i,11)== 4)
        {
         sname = indice_respuesta [1];
        }
      if(MathMod(i,11)== 5)
        {
         sfecha = StringSubstr(indice_respuesta [1],1,10);
         ufecha = StringToTime(sfecha);
        }
      if(MathMod(i,11)== 6)
        {
         spips_ant = indice_respuesta [1];
         upips_ant = StringToDouble(spips_ant);
        }
      if(MathMod(i,11)== 7)
        {
         scount_events = indice_respuesta [1];
         ucount_events = ucount_events  + StringToDouble(scount_events);

        }
      if(MathMod(i,11)== 8)
        {
         smax_pips = indice_respuesta [1];
         umax_pips  = StringToDouble(smax_pips);
        }
      if(MathMod(i,11)== 9)
        {
         sprom_pips = indice_respuesta [1];
         uprom_pips = StringToDouble(sprom_pips);
        }
      if(MathMod(i,11)== 10)
        {
         sult_event = StringSubstr(indice_respuesta [1],1,10);
         uult_event = StringToTime(sult_event);
        }

      if(MathMod(i,11)== 0)
        {

         if(MathAbs(upips_ant)  > MathAbs(ppips_ant))
           {
            ppips_ant = upips_ant;
            pult_event = uult_event;
            pfecha = ufecha;
            pname = sname;
            pcount_events = ucount_events;
           }
         if(MathAbs(umax_pips)  > MathAbs(pmax_pips))
            pmax_pips = umax_pips;

         if(MathAbs(uprom_pips)  > MathAbs(pprom_pips))
            pprom_pips = uprom_pips;
        }


      pcurrency = scurrency ;
      pname = sname ;
     }

   return true;
  }
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
double risk_eval(
   datetime pfechai, datetime pfechaf,
   string psimbolo,
   string & pcurrency,
   string & pname,
   datetime & pfecha,
   double & ppips_ant,
   double  & pcount_events,
   double & pmax_pips,
   double  & pprom_pips,
   datetime  &pult_event
)
  {
   double risk = 0;
   int calificacion = 0;

   alert_event(pfechai,pfechaf,psimbolo, pcurrency,pname, pfecha,ppips_ant,pcount_events,pmax_pips,pprom_pips,pult_event);
   printf(TimeToStr(pfechai)+TimeToStr(pfechaf)+psimbolo+ pcurrency +pname+ TimeToStr(pfecha) + DoubleToStr(ppips_ant) + DoubleToStr(pcount_events) + DoubleToStr(pmax_pips) + DoubleToStr(pprom_pips)+ TimeToStr(pult_event));


   if(MathAbs(ppips_ant) >   pips_max_riesgo)
      calificacion = calificacion +2;

   if(MathAbs(pmax_pips) >   pips_max_riesgo)
      calificacion = calificacion +1;

   if(MathAbs(pprom_pips) >   pips_max_riesgo)
      calificacion = calificacion +1;

   risk = (calificacion / 4.0);
   return risk;
  }
//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
datetime max_hora_evento(int &eventosin[], int  encontrados, int & cont, string & descrip, string & currency)
  {
   datetime resp = 0;
   for(int i = 0; i < encontrados; i++)
     {
      if(StringToTime(ahora[ eventosin[i]]) > resp)
        {
         resp = StringToTime(ahora[ eventosin[i]]);
         descrip =           aname[ eventosin[i]];
         currency =    acurrency  [ eventosin[i]];
         cont = i;
        }
     }
   return resp;
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

//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
void eval_risk_dia(datetime fechain, datetime & fecha_risk_in, double & riesgo, int &flag_alerta_in)
  {

   string currency ;
   string name  ;
   datetime  fecha ;
   double  pips_ant ;
   double   count_events ;
   double  max_pips ;
   double   prom_pips ;
   datetime  ult_event ;

   datetime fechaini;
   datetime fechafin;

   if(Cambio_de_dia(fecha_risk_in))
     {
      fecha_risk_in = TimeCurrent();
      fechaini = fechain;
      fechafin = fechain;
      riesgo=   risk_eval(fechaini,fechafin,Symbol(), currency,name, fecha,pips_ant,count_events,max_pips,prom_pips,ult_event);
      //                printf (fechaini+fechafin+Symbol()+ currency +name+ TimeToStr (fecha) + DoubleToStr(pips_ant) + DoubleToStr(count_events) + DoubleToStr(max_pips) + DoubleToStr(prom_pips)+ TimeToStr (ult_event));
      if(riesgo > apetito_risk)
         flag_alerta_in = 1;
      else
         flag_alerta_in = 0;
     }
   return ;
  }


//+------------------------------------------------------------------+
//| Print Line                 |
//+------------------------------------------------------------------+
void Print_LINE2(string Name,   color c, datetime fecha1,datetime fecha2)
  {
   const color           clr=c;        // rectangle color
   const ENUM_LINE_STYLE style=STYLE_SOLID; // style of rectangle lines
   const int             width=1;           // width of rectangle lines
   const bool            fill=true;        // filling rectangle with color
   const bool            back=false;        // in the background
   const bool            selection=true;    // highlight to move
   const bool            hidden=false;       // hidden in the object list
   const long            z_order=0;



   string simbolo = Symbol();
   string ObjectLine = Name+TimeToStr(TimeCurrent());
   string Objectsquare = Name+"SQR"+TimeToStr(TimeCurrent())+TimeToStr(fecha1)+TimeToStr(fecha2);

   ObjectDelete(ObjectLine); // line open

   /*   if(!ObjectCreate(ChartID(), ObjectLine,OBJ_VLINE,0,fecha,0,fecha,100))  //Creamos la linea
        {
         Print("Error: can't create Linea! code #"+ObjectLine ,GetLastError());
         return;
        }
      ObjectSetInteger(ChartID(),ObjectLine,OBJPROP_COLOR,c); // Ponemos el color de la línea

      ObjectSetInteger(ChartID(),ObjectLine,OBJPROP_WIDTH,4);
   //--- display in the foreground (false) or background (true) */


   if(!ObjectCreate(ChartID(), Objectsquare,OBJ_RECTANGLE,0,fecha1,0,fecha2,100))  //Creamos la linea
     {
      Print("Error: can't create Square! code # " + IntegerToString(GetLastError()));
      return;
     }
//--- set rectangle color
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_COLOR,c);
//--- set the style of rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_STYLE,style);
//--- set width of the rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_WIDTH,width);
//--- enable (true) or disable (false) the mode of filling the rectangle
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_FILL,fill);
//--- display in the foreground (false) or background (true)
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_BACK,back);
//--- enable (true) or disable (false) the mode of highlighting the rectangle for moving
//--- when creating a graphical object using ObjectCreate function, the object cannot be
//--- highlighted and moved by default. Inside this method, selection parameter
//--- is true by default making it possible to highlight and move the object
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTABLE,selection);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTED,selection);
//--- hide (true) or display (false) graphical object name in the object list
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_HIDDEN,hidden);
//--- set the priority for receiving the event of a mouse click in the chart
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_ZORDER,z_order); //--- set rectangle color
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_COLOR,c);
//--- set the style of rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_STYLE,style);
//--- set width of the rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_WIDTH,width);
//--- enable (true) or disable (false) the mode of filling the rectangle
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_FILL,fill);
//--- display in the foreground (false) or background (true)
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_BACK,back);
//--- enable (true) or disable (false) the mode of highlighting the rectangle for moving
//--- when creating a graphical object using ObjectCreate function, the object cannot be
//--- highlighted and moved by default. Inside this method, selection parameter
//--- is true by default making it possible to highlight and move the object
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTABLE,selection);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTED,selection);
//--- hide (true) or display (false) graphical object name in the object list
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_HIDDEN,hidden);
//--- set the priority for receiving the event of a mouse click in the chart
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_ZORDER,z_order);

   return;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void write_logTransaccional(datetime date,string simb,int periodo,int periodo2,string versionin,double scorein,double limite_comprain,double limite_ventain, string scoreinmodelo, double dif)
  {

   string linea2 =
      "cuenta"+ ";" +
      "date"+ ";" +
      "simb"+ ";" +
      "version"+ ";" +
      "periodo"+ ";" +
      "periodo_indica"+ ";" +
      "score"+ ";" +
      "score_modelo"+ ";" +
      "dif_modelo"+ ";" +
      "limite_buye"+ ";" +
      "limite_sell";

   string linea =
      IntegerToString(AccountNumber())+ ";" +
      TimeToStr(date)+ ";" +
      simb+ ";" +
      versionin+ ";" +

      IntegerToString(periodo)+ ";" +
      IntegerToString(periodo2)+ ";" +
      DoubleToStr(scorein)+ ";" +
      scoreinmodelo+ ";" +
      DoubleToStr(dif)+ ";" +
      DoubleToStr(limite_comprain)+ ";" +
      DoubleToStr(limite_ventain);




   int archivolog = 0;
   string strIndicador = "log_"+simb+"_" +TimeToStr(TimeCurrent(),TIME_DATE)+".csv";
   bool imprimir_cab = false;


   if(!FileIsExist(strIndicador))
     {
      imprimir_cab = true;
     }

   archivolog = FileOpen(strIndicador,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ);
   if(imprimir_cab)
     {
      FileWrite(archivolog,linea2);
     }

   while(!FileIsEnding(archivolog))
      FileReadString(archivolog) ; //ir hasta el final del archivo

   FileWrite(archivolog,linea);
   FileClose(archivolog);

   return;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void write_log_validacion_pre(string algor, int tipo_in,string simb,int periodo,int periodo2,double scorein,double limite_comprain,double limite_ventain,
                              int resp_fprecio1,int resp_fmaxp1,int resp_fmaxbum1,int resp_fatr1, int resp_fhorario1,int resp_fsoportes1,int resp_fresistencias1,
                              int resp_fmax_fractal1, int resp_f71,    int resp_f81,   int resp_f91)
  {
//    write_log_validacion_pre(algor,tipo,Symbol()Period(),0,scorein,limite_buy_in,limite_sell_in,resp_fmaxp ,resp_fmaxbum,resp_fatr,resp_fhorario ,resp_fsoportes ,resp_fresistencias ,
//                             resp_max_fractal ,resp_f7, resp_f8 ,resp_f9     )

   string tipostr = "";
   if(tipo_in == OP_BUY)
      tipostr =   "BUY";
   if(tipo_in == OP_SELL)
      tipostr = "SELL";


   string linea2 =
      "algoritmo"+ ";" +
      "date"+ ";" +
      "simb"+ ";" +
      "tipo"+ ";" +
      "periodo"+ ";" +
      "periodo_indica"+ ";" +
      "score"+ ";" +
      "limite_buye"+ ";" +
      "limite_sell"+ ";" +
      "fprecios"+ ";" +
      "fmaxp"+ ";" +
      "fmaxbum"+ ";" +
      "fatr"+ ";" +
      "fhorario"+ ";" +
      "fsoportes"+ ";" +
      "fresistencias"+ ";" +
      "fmax_fractal"+ ";" +
      "f7"+ ";" +
      "f8"+ ";" +
      "f9"
      ;

   string linea =
      algor+ ";" +
      TimeToStr(TimeCurrent())+ ";" +
      simb+ ";" +
      tipostr+ ";" +
      IntegerToString(periodo)+ ";" +
      IntegerToString(periodo2)+ ";" +
      DoubleToStr(scorein)+ ";" +
      DoubleToStr(limite_comprain)+ ";" +
      DoubleToStr(limite_ventain)+ ";" +
      IntegerToString(resp_fprecio1)+ ";" +
      IntegerToString(resp_fmaxp1)+ ";" +
      IntegerToString(resp_fmaxbum1)+ ";" +
      IntegerToString(resp_fatr1)+ ";" +
      IntegerToString(resp_fhorario1)+ ";" +
      IntegerToString(resp_fsoportes1)+ ";" +
      IntegerToString(resp_fresistencias1)+ ";" +
      IntegerToString(resp_fmax_fractal1)+ ";" +
      IntegerToString(resp_f71)+ ";" +
      IntegerToString(resp_f81)+ ";" +
      IntegerToString(resp_f91)
      ;



   int archivolog = 0;
   // Para imprimir el log semanalmente
   datetime now = TimeCurrent();
   int dow = TimeDayOfWeek(now);
   int days_to_subtract = 0;
   // retroceder hasta el lunes
   if(dow == 0) // si hoy es domingo
      days_to_subtract = 6;
   else
      days_to_subtract = dow - 1;

   datetime monday = now - days_to_subtract * 86400;
   string monday_str = TimeToStr(monday, TIME_DATE);
   
   //string strIndicador = "log_score_"+simb+"_" +TimeToStr(TimeCurrent(),TIME_DATE)+".csv";
   string strIndicador = "log_score_" + Symbol() + "_" + monday_str + ".csv";
   
   bool imprimir_cab = false;
   if(!FileIsExist(strIndicador))
   {
      imprimir_cab = true;
   }

   archivolog = FileOpen(strIndicador,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ);
   if(imprimir_cab)
   {
      FileWrite(archivolog,linea2);
   }

   while(!FileIsEnding(archivolog))
      FileReadString(archivolog) ; //ir hasta el final del archivo

   FileWrite(archivolog,linea);
   FileClose(archivolog);

   return;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void write_log_url(string ver,string tipostr,string post, string respuesta, string dif, string strerr)
  {
   datetime fecha = TimeCurrent();
   string simb = Symbol();
   string linea2 =

      "date"+ ";" +
      "version"+ ";" +
      "simb"+ ";" +
      "timeframe"+ ";" +
      "post"+ ";" +
      "respuesta"+ ";" +
      "diferencia"+ ";" +
      "limbuy"+ ";" +
      "limsell"+ ";" +
      "error"+ ";" +
      "tipo"+ ";" +
      //"periodo"+ ";" +
      //"periodo_indica"+ ";" +
      //"score"+ ";" +
      //"limite_buye"+ ";" +
      //"limite_sell"+ ";" +
      "fprecios"+ ";" +
      "fmaxp"+ ";" +
      "fmaxbum"+ ";" +
      "fatr"+ ";" +
      "fhorario"+ ";" +
      "fsoportes"+ ";" +
      "fresistencias"+ ";" +
      "fmax_fractal"+ ";" +
      "f7"+ ";" +
      "f8"+ ";" +
      "f9"
      ;      

   string linea =

      TimeToStr(fecha)+ ";" +
      ver+ ";" +
      simb+ ";" +
      IntegerToString(Period())+ ";" +
      post+ ";" +
      respuesta+ ";" +
      dif+ ";" +
      DoubleToStr(lim_transformer_buy) + ";" +
      DoubleToStr(lim_transformer_sell) + ";" +
      strerr+ ";" +
      tipostr+ ";" +
      //IntegerToString(periodo)+ ";" +
      //IntegerToString(periodo2)+ ";" +
      //DoubleToStr(scorein)+ ";" +
      //DoubleToStr(limite_comprain)+ ";" +
      //DoubleToStr(limite_ventain)+ ";" +
      IntegerToString(resp_fprecio)+ ";" +
      IntegerToString(resp_fmaxp)+ ";" +
      IntegerToString(resp_fmaxbum)+ ";" +
      IntegerToString(resp_fatr)+ ";" +
      IntegerToString(resp_fhorario)+ ";" +
      IntegerToString(resp_fsoportes)+ ";" +
      IntegerToString(resp_fresistencias)+ ";" +
      IntegerToString(resp_fmax_fractal)+ ";" +
      IntegerToString(resp_fresbal)+ ";" +
      IntegerToString(resp_f8)+ ";" +
      IntegerToString(resp_f9)
      ;

   int archivolog = 0;
   string strIndicador = "log_url_"+simb+"_" +TimeToStr(TimeCurrent(),TIME_DATE)+".csv";
   bool imprimir_cab = false;


   if(!FileIsExist(strIndicador))
     {
      imprimir_cab = true;
     }

   archivolog = FileOpen(strIndicador,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ);
   if(imprimir_cab)
     {
      FileWrite(archivolog,linea2);
     }

   while(!FileIsEnding(archivolog))
      FileReadString(archivolog) ; //ir hasta el final del archivo

   FileWrite(archivolog,linea);
   FileClose(archivolog);

   return;
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void write_logtp(datetime date,string simb,int periodo,int periodo2,int ticket,int tipo,double tpant,double tpnuevo)
  {
   string tipostr = "";
   double tpin = MathAbs(tpnuevo - tpant);

   if(tipo== OP_BUY)
      tipostr  = "BUY";
   if(tipo== OP_SELL)
      tipostr = "SELL";
   string linea2 =
      "date"+ ";" +
      "simb"+ ";" +
      "periodo"+ ";" +
      "periodo_indica"+ ";" +
      "ticket"+ ";" +
      "tipo"+ ";" +
      "tpant"+ ";" +
      "tpdif"+ ";" +
      "tpnuevo";




   string linea =

      TimeToStr(date)+ ";" +
      simb+ ";" +
      IntegerToString(periodo)+ ";" +
      IntegerToString(periodo2)+ ";" +
      IntegerToString(ticket)+ ";" +
      tipostr + ";" +
      DoubleToStr(tpant)+ ";" +
      DoubleToStr(tpin)+ ";" +
      DoubleToStr(tpnuevo);




   int archivolog = 0;
   string strIndicador = "log_tp"+ TimeToStr(TimeCurrent(),TIME_DATE)+".csv";
   bool imprimir_cab = false;


   if(!FileIsExist(strIndicador))
     {
      imprimir_cab = true;
     }

   archivolog = FileOpen(strIndicador,FILE_WRITE  | FILE_SHARE_WRITE | FILE_READ);
   if(imprimir_cab)
     {
      FileWrite(archivolog,linea2);
     }

   while(!FileIsEnding(archivolog))
      FileReadString(archivolog) ; //ir hasta el final del archivo

   FileWrite(archivolog,linea);
   FileClose(archivolog);

   return;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool validacion_max_perdida()
  {

   bool respuesta = false;


   int cola_buy = 0;
   int cola_sell = 0;
   double  profitbuy = 0;
   double  profitsell = 0;
   double lotes_sell = 0;
   double lotes_buy = 0;
   int cola_buy_limit = 0;
   int cola_sell_limit = 0;

   RefreshRates();

   double open_con_SL = 0;
   count_operprofit_fibo(cola_buy,  profitbuy, lotes_buy, cola_sell,  profitsell,  lotes_sell,cola_buy_limit,cola_sell_limit,open_con_SL);


   if((cola_buy > 0) && (profitbuy <0))
     {

      if((MathAbs(profitbuy) /   AccountEquity()) > max_perdida_cuenta)
        {
         printf("******************Perdida maxima close, Equity: %f  profit: %f  Porcentaje %f    max_perdida: %f   ", AccountEquity(),MathAbs(profitbuy),MathAbs(profitbuy)/AccountEquity(),max_perdida_cuenta) ;
         closeOrderssymbol(OP_BUY);
         respuesta = true ;
        }

     }

   if((cola_sell > 0) && (profitsell <0))
     {


      if((MathAbs(profitsell) /   AccountEquity()) > max_perdida_cuenta)
        {
         printf("******************Perdida maxima close, Equity: %f  profit: %f  Porcentaje %f    max_perdida: %f   ",  AccountEquity(),MathAbs(profitsell),MathAbs(profitsell)/AccountEquity(),max_perdida_cuenta) ;
         closeOrderssymbol(OP_SELL);
         respuesta = true ;
        }
     }

   return respuesta;
  }
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool count_operprofit_manuales(int & numbuy, double & profitbuy, double & lotesbuyin,int & numsell, double & profitsell, double & lotessellin, double & SLin)
  {
   numbuy= 0;
   profitbuy = 0;
   lotesbuyin = 0;

   profitsell = 0;
   numsell = 0;
   lotessellin = 0;

   int total = OrdersTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, 0, 0);
      if((OrderSymbol()==Symbol())   && (OrderType()== OP_BUY)    && (OrderMagicNumber() == 0))
        {
         numbuy= numbuy +1;
         profitbuy = profitbuy+ OrderProfit();
         lotesbuyin = lotesbuyin + OrderLots();
         SLin = OrderStopLoss();
        }
      else
         if((OrderSymbol()==Symbol())   && (OrderType()== OP_SELL) && (OrderMagicNumber() == 0))
           {
            numsell= numsell +1;
            profitsell = profitsell+ OrderProfit();
            lotessellin = lotessellin + OrderLots();
            SLin = OrderStopLoss();
           }

     }
   return(true);
  }
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool count_operprofit_fibo(int & numbuy, double & profitbuy, double & lotesbuyin,int & numsell, double & profitsell, double & lotessellin,int & num_buy_limit,int & num_sell_limit,double & SLin)
  {
   numbuy= 0;
   profitbuy = 0;
   lotesbuyin = 0;
   profitsell = 0;
   numsell = 0;
   lotessellin = 0;


   int total = OrdersTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, 0, 0);
      if((OrderSymbol()==Symbol())   && (OrderType()== OP_BUY)      && (OrderMagicNumber() == MagicNumber))
        {
         numbuy= numbuy +1;
         profitbuy = profitbuy+ OrderProfit();
         lotesbuyin = lotesbuyin + OrderLots();
         SLin = OrderStopLoss();

        }
      else
         if((OrderSymbol()==Symbol())   && (OrderType()== OP_SELL)     && (OrderMagicNumber() == MagicNumber))
           {

            numsell= numsell +1;
            profitsell = profitsell+ OrderProfit();
            lotessellin = lotessellin + OrderLots();
            SLin = OrderStopLoss();
           }
         else
            if((OrderSymbol()==Symbol())   && (OrderType()== OP_BUYLIMIT)    && (OrderMagicNumber() == MagicNumber))
              {
               num_buy_limit= num_buy_limit +1;
              }
            else
               if((OrderSymbol()==Symbol())   && (OrderType()== OP_SELLLIMIT)         && (OrderMagicNumber() == MagicNumber))
                 {
                  num_sell_limit= numsell +1;
                 }

     }
   return(true);
  }


//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool Validar_TX_NO_MAGIC(double maxper)
  {

   bool respuesta = false;
   RefreshRates();

   int total = OrdersTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, 0, 0);

      string tmpsymbol = OrderSymbol();
      int tmptype = OrderType();
      double tmpprofit = OrderProfit();
      double tmpticket = OrderTicket();

      if((OrderSymbol()==Symbol())   && ((OrderType()== OP_BUY)  || (OrderType()== OP_SELL))      && (OrderProfit()< 0))
        {


         if((MathAbs(OrderProfit()) /   AccountEquity()) > maxper)
           {
            if(OrderClose(OrderTicket(),OrderLots(),OrderClosePrice(),0,clrBlack))
              {
               printf("CLOSE, BUY SELL,  SL x SL, Ask = %f, desde %f, hasta %f"+" "+TimeToStr(TimeCurrent()),Ask,0, 0);
               respuesta = true;
              }
           }

        }
     }
   return respuesta;
  }
//+------------------------------------------------------------------+
//| Cambio de dia                    |
//+------------------------------------------------------------------+
bool Cambio_de_hora(string tiempoval,int num,datetime & fecha_base)
  {

      datetime tc = TimeCurrent();
      datetime gapf = 0;
      if (tiempoval == "hh")
      {
         gapf= (num * 3600);
      }
      if (tiempoval == "mm")
      {
         gapf = (num * 60);
      }
      if (fecha_base+ gapf < TimeCurrent())
      {
               fecha_base = TimeCurrent()+gapf;
               return true;
               
      }

    
   return false;    
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void Print_trail(bool resp_bummm,double nuevo_dif_fractal)
  {

   int  trendtipo= -1;
   string tendencia = "";


   int cola_buy = 0;
   int cola_sell = 0;
   double  profitbuy = 0;
   double  profitsell = 0;
   double lotes_sell = 0;
   double lotes_buy = 0;
   double open_con_SL = 0;
   int cola_buy_limit = 0;
   int cola_sell_limit = 0;
   color cin1 = clrBlack;



   informacionmarket = (MarketInfo(_Symbol, MODE_SPREAD) * PointVal);
   Comment("",
           "\n Copyright © NeoTrading EA ",
           "\n Profi/Balance     =  ",
           NormalizeDouble(profitsimbol()/AccountBalance()*100,4),
           " %\n Max Perdida     =  ",
           NormalizeDouble(max_perdida_cuenta,4)*100,
           " %\n Ult fractal =", nuevo_dif_fractal,
           " \n Max vagones =", Max_vagones
          );




   RefreshRates();

   count_operprofit_fibo(cola_buy,  profitbuy, lotes_buy, cola_sell,  profitsell,  lotes_sell,cola_buy_limit,cola_sell_limit,open_con_SL);
   int colain = cola_buy+ cola_sell;
   int colainlimit = cola_buy_limit + cola_sell_limit;

//********************************** dibuja los TOPES
   double tope_altoin = 0;
   double tope_bajoin = 0;
   double tope_inicial = 0;

   topes_dia(FormatDateZero(TimeCurrent()), TimeCurrent(),  tope_altoin,tope_bajoin,tope_inicial);
   Print_HLINE("topealto",     clrYellow, TimeCurrent(),tope_altoin, STYLE_SOLID,2);
   Print_HLINE("topinicial",   clrYellow, TimeCurrent(),tope_inicial, STYLE_SOLID,2);
   Print_HLINE("topebajo",     clrYellow, TimeCurrent(),tope_bajoin, STYLE_SOLID,2);
   Print_LINE(0,"iniciodia","",  clrYellow, FormatDateZero(TimeCurrent()), 4);

   double scorein = 0;
   int tipoin = -1;
   double limite_compra_in = 50;
   double limite_venta_in = -50;

   
 


//bool resp =  Calculo_score_Nbot  (tipoin,scorein, limite_compra_in, limite_venta_in,bonusscore );
   string txtr = "";
   double dif = 0;

   double tmp_resp1  =  0; //consulta_score_transformer(1,txtr);
   double tmp_resp2  =  0; //consulta_score_transformer(1,txtr);  
          tmp_resp2= consulta_score_transformer_v3(1, txtr,dif);
/*
   double tmp_resp8= consulta_score_transformer_v3(1, txtr,dif);
   double tmp_resp9= consulta_score_transformer_v3(1, txtr,dif);
   double tmp_resp10= consulta_score_transformer_v3(1, txtr,dif);

        
         if ( tmp_resp2 ==1)
         {

               printf ("2  %f,8 %f,9 %f,10 %f",tmp_resp2,tmp_resp8,tmp_resp9,tmp_resp10);
               printf ("printtrail tempresp...BUY........................");
         }
         if ( tmp_resp2 ==-1)
         {
                
               printf ("2  %f,8 %f,9 %f,10 %f",tmp_resp2,tmp_resp8,tmp_resp9,tmp_resp10);
               printf ("printtrail tempresp...SELL........................");
         }


    if ((Symbol() == "NAS100") || (Symbol() == "GER40")  ||  (Symbol() == "US30")  )
             tmp_resp2= consulta_score_transformer_v3(1, txtr,dif);
             else

         if ((Symbol() == "BTCUSD")   ) 
            //  tmp_resp2= consulta_score_transformer_v4(1, txtr,dif); // matematico
                tmp_resp2= consulta_score_transformer_v3(1, txtr,dif);
          else
                     tmp_resp2= consulta_score_transformer_v2(1, txtr,dif);

                         tmp_resp2= consulta_score_transformer_v3(1, txtr,dif);
          */  
   

   //write_logTransaccional(TimeCurrent(),Symbol(),Period(),timeframeIndicador,"v1",tmp_resp1,limite_compra_in, limite_venta_in,"",0);
   write_logTransaccional(TimeCurrent(),Symbol(),Period(),timeframeIndicador,"v2",tmp_resp2,0, 0,txtr,dif);

//double tmp_resp2  =  iCustom(NULL,Period(),"Neo_OSC",80,20,15,1,1);
//if ((tmp_resp1 == 1) ||   (tmp_resp2 == 1))
   
   if(tmp_resp1 == 1)
      scorein = 75;
   if(tmp_resp1 == -1)
      scorein = -75;

//*******************
   if(flag_trace ==1)
   {
      tipoin = OP_BUY;
      scorein = 75;
      limite_compra_in = 50;
   }
   if(flag_trace ==-1)
   {
      tipoin = OP_SELL;
      scorein = -75;
      limite_compra_in = -50;
   }
   //***********************
   if(scorein > limite_compra_in)
      trendtipo = OP_BUY;
   if(scorein < limite_venta_in)
      trendtipo = OP_SELL;
      
   if(trendtipo == OP_BUY)
   {tendencia = "BUY" ; cin1 = clrGreen;}
   else
      if(trendtipo == OP_SELL)
      {tendencia = "SELL" ; cin1 = clrRed;}
      else
         tendencia = "NoNe" ;


   if((trendtipo == OP_BUY) ||(trendtipo == OP_SELL))
   {
      //graph_indicador(1,trendtipo,timeframeIndicador,0);
   }
//****************************
   if((tmp_resp2!= 0))
   {
      if(tmp_resp2==1)
      {
         printf ("printtrail asignacion...BUY........................");
         trendtipo = OP_BUY;
      }
      if(tmp_resp2==-1)
      {
         trendtipo = OP_SELL;
         printf ("printtrail asignacion...SELL........................");

      }
      graph_indicador(2,trendtipo,timeframeIndicador,dif);
   }
//*****************************
   double precio_menos_2 = 0;
   double precio_menos_1 = 0;
   precio_menos_2 = iClose(_Symbol, 0, 2); // Precio de cierre del Timeframe , 0 Current, periodos atras
   precio_menos_1 = iClose(_Symbol, 0, 1); // Precio de cierre del Timeframe , 0 Current, 1 peíodo atras
   double rsi = iRSI(NULL, 15, 5, 0, 1);

   string tmp_str = "";
   if((resp_bummm) && (nuevo_dif_fractal> 0))
   {
      tmp_str = "BOOM = "+StringFormat("%.2f",nuevo_dif_fractal,2);
      DrawLabel("BOOM", tmp_str,120, 20, clrRed, CORNER_RIGHT_UPPER,8, "Arial");

   }
   else
   {
      if(ObjectFind(0, "BOOM") >= 0)
      {
         ObjectDelete(0, "BOOM") ;

      }
      //tmp_str = "BOOM = "+StringFormat("%.2f",nuevo_dif_fractal,2);
      //DrawLabel("BOOM", tmp_str, 120,  20, clrWhite, CORNER_RIGHT_UPPER,8, "Arial");
     }
   string precios = "";
   if((precio_menos_2 - precio_menos_1) > 0)
   {
      precios = "PR UP ";
   }
   else
   {
      precios = "PR DW ";
   }

//string strrci = "RSI = "+ DoubleToStr(rsi)+",SI<36=BUY, SI> 56=SELL";




// Imprime derecha
   ObjectDelete("Mach");
   string linea1 = "TRANF, " +  "scor = "+    StringFormat("%.2f",scorein,2)+" ,limBUY = " +StringFormat("%.2f",limite_compra_in,2)+ " ,limSELL = " +StringFormat("%.2f",limite_venta_in,2) ;
   string linea2 = "SCORETX = "+ txtr +", "  +precios;   //  ," +",strrci+ "    ;

   DrawLabel("Mach", linea1, 15,  45, cin1, CORNER_RIGHT_UPPER,8, "Arial");
   DrawLabel("Mach2",linea2, 15,  55, cin1, CORNER_RIGHT_UPPER,8, "Arial");

   if(colain >0)
     {


      int  ulttipotx = -1;
      double  ultlotes = 0;
      double  ultsumalotes = 0;
      double  ultopenprice = 0;
      int     ultticket= 0;
      double  ultsl = 0;
      double  ulttp = 0;

      if(cola_buy >0)
         ulttipotx = OP_BUY;
      if(cola_sell >0)
         ulttipotx = OP_SELL;

      ultticket = buscar_ultima_tx(ulttipotx,ultlotes, ultsumalotes,ultopenprice,ultsl, ulttp);

     } // cola in
   return;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void graph_indicador(int tipo_grafico,int tipo, int minutes, double dif)
  {
   color d = clrBlack;
   string fl = "";
   
   if (Symbol() == "BTCUSD")
      dif = dif / 10;
   if(tipo_grafico == 1)
     {
      if(tipo  == OP_BUY)
         d = clrPowderBlue;
      if(tipo  == OP_SELL)
         d = clrMistyRose;
      Print_SQUARE("scorevisual",   d, TimeCurrent(),TimeCurrent()+ Period()*60);
     }
   if(tipo_grafico == 2)
     {
      if(tipo  == OP_BUY)
        {
         d = clrOrange;
         fl = "up";
        }
      if(tipo  == OP_SELL)
        {
         d = clrMagenta;
         fl = "dw";
        }
      Print_ARROW(tipo,"scorevisual"+fl,  d, TimeCurrent(),TimeCurrent()+ Period()*60,  dif);
     }


   return;
  }
//+------------------------------------------------------------------+
//| Print Line                 |
//+------------------------------------------------------------------+
void Print_SQUARE(string Name,   color c, datetime fecha1,datetime fecha2)
  {
   const color           clr=c;        // rectangle color
   const ENUM_LINE_STYLE style=STYLE_SOLID; // style of rectangle lines
   const int             width=1;           // width of rectangle lines
   const bool            fill=true;        // filling rectangle with color
   const bool            back=false;        // in the background
   const bool            selection=true;    // highlight to move
   const bool            hidden=false;       // hidden in the object list
   const long            z_order=0;



   string simbolo = Symbol();
   string Objectsquare = Name+"SQR"+TimeToStr(fecha1)+TimeToStr(fecha2);

//printf("SQUARE "+Symbol()+" "+ TimeToStr(TimeCurrent())+" "+Objectsquare);
   ObjectDelete(Objectsquare); // line open

   int objeto_indice = ObjectFind(0, Objectsquare);

   if(objeto_indice == 0)
      return;


   double minPrice= Bid/2;
   double maxPrice= Ask*2;
//minPrice= ChartGetDouble(ChartID(), CHART_PRICE_MIN, 0);
//maxPrice= ChartGetDouble(ChartID(), CHART_PRICE_MAX, 0);

   if(!ObjectCreate(ChartID(), Objectsquare, OBJ_RECTANGLE, 0, fecha1, minPrice, fecha2,maxPrice))
     {
      Print("Error: No Square code # " + IntegerToString(GetLastError()));
      return;
     }


//--- set rectangle color
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_COLOR,c);
//--- set the style of rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_STYLE,style);
//--- set width of the rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_WIDTH,width);
//--- enable (true) or disable (false) the mode of filling the rectangle
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_FILL,fill);
//--- display in the foreground (false) or background (true)
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_BACK,back);
//--- enable (true) or disable (false) the mode of highlighting the rectangle for moving
//--- when creating a graphical object using ObjectCreate function, the object cannot be
//--- highlighted and moved by default. Inside this method, selection parameter
//--- is true by default making it possible to highlight and move the object
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTABLE,selection);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTED,selection);
//--- hide (true) or display (false) graphical object name in the object list
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_HIDDEN,hidden);
//--- set the priority for receiving the event of a mouse click in the chart
//--- set the style of rectangle lines
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_ZORDER,z_order);

   return;
  }
//+------------------------------------------------------------------+
//|                  |
//+------------------------------------------------------------------+
void Print_ARROW(int tipo,string Name,   color c, datetime fecha1, datetime fecha2, double dif)
  {
   const color           clr=c;        // rectangle color
   const ENUM_LINE_STYLE style=STYLE_SOLID; // style of rectangle lines
   const int             width=1;           // width of rectangle lines
   const bool            fill=true;        // filling rectangle with color
   const bool            back=false;        // in the background
   const bool            selection=true;    // highlight to move
   const bool            hidden=false;       // hidden in the object list
   const long            z_order=0;
   int arrowCode = 0;
   string simbolo = Symbol();
   string Objectsquare = Name+"ARR"+TimeToStr(fecha1)+TimeToStr(fecha2);

   ObjectDelete(Objectsquare); // line open

   int objeto_indice = ObjectFind(0, Objectsquare);
   if(objeto_indice == 0)
      return;

   double pclose  = Close[iBarShift(NULL, 0, fecha1, false)];
   if(tipo == OP_BUY)
     {
      arrowCode = 233;     // Símbolo de flecha hacia arriba
      //pclose = pclose + dif;
      pclose = pclose + TakeProfit* PointVal;;
     }
   if(tipo == OP_SELL)
     {
      arrowCode = 234;     // Símbolo de flecha hacia arriba
      //pclose = pclose + dif;
      pclose = pclose - TakeProfit * PointVal;

     }
   if(!ObjectCreate(ChartID(), Objectsquare, OBJ_ARROW, 0, fecha1, pclose))
     {
      Print("Error: No Square code # " + IntegerToString(GetLastError()));
      return;
     }
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_ARROWCODE, arrowCode);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_COLOR,c);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_STYLE,style);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_WIDTH,width);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_FILL,fill);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_BACK,back);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTABLE,selection);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_SELECTED,selection);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_HIDDEN,hidden);
   ObjectSetInteger(ChartID(),Objectsquare,OBJPROP_ZORDER,z_order);

   return;
  }



//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool topes_dia(datetime fini, datetime ffin, double & tope_altoin,double & tope_bajoin, double & inicial)
  {


   int barini = iBarShift(Symbol(), 0, fini);
   int barfin = iBarShift(Symbol(), 0, ffin);
   int barras = barini  - barfin ;
   inicial = iClose(Symbol(), 0, barini);

   double max = iClose(Symbol(), 0, 1);
   double min = iClose(Symbol(), 0, 1);

   for(int i = 0; i< barras; i++)
     {
      double close = iClose(Symbol(), 0, barini-i);

      if(close > max)
         max = close;

      if(close < min)
         min = close;
     }

   if((max >0)  && (max >0))
     {
      tope_altoin  = max;
      tope_bajoin = min;
      return true;

     }


   return false;

  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int buscar_ultima_tx(int tipoi, double & ultimolotei, double & lotesi, double & openpricei, double & slin, double & tpin)
  {

   ultimolotei = 0;
   lotesi = 0;
   openpricei = 0;


   int count = 0;
   int tipo = -1;
   int ticket = 0;

   int i = 0;
   i = OrdersTotal() ;

   int order_checki = 0;

   if(i >= 0)
     {
      do
        {
         int check = OrderSelect(i-1, 0, 0);

         if(OrderSymbol() == _Symbol  && OrderMagicNumber() == MagicNumber &&    OrderType() == tipoi)
           {
            if(ticket <  OrderTicket())
              {
               ticket = OrderTicket();
               openpricei = OrderOpenPrice();
               ultimolotei = OrderLots();
               lotesi = lotesi + OrderLots();
               slin = OrderStopLoss();
               tpin = OrderTakeProfit();
              }
           }
         i = i - 1;
        }
      while(i >= 0);
     }
   return (ticket);
  }



//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
datetime FormatDateZero(datetime dateTime)
  {
   int year = TimeYear(dateTime);
   int month = TimeMonth(dateTime);
   int day = TimeDay(dateTime);
   int hour = TimeHour(dateTime);
   int minute = TimeMinute(dateTime);
   int second = TimeSeconds(dateTime);

//  return StringFormat("%04d-%02d-%02d %02d:%02d:%02d", year, month, day, hour, minute, second);
//datetime new_date = StringToTime(StringFormat("%04d-%02d-%02d 00:00:00", year, month, day));
   string str_new_date = StringFormat("%04d.%02d.%02d 00:00:00", year, month, day);
   datetime new_date = StringToTime(str_new_date);
   return new_date;

  }

//+------------------------------------------------------------------+
//| Print Line                 |
//+------------------------------------------------------------------+
void Print_HLINE(string Name,   color c, datetime fecha, double price, int estilo,int width)
  {
   string simbolo = Symbol();

   string ObjectLine = Name;

   ObjectDelete(ObjectLine); // line open
   if(width >0)
     {
      if(!ObjectCreate(ChartID(), ObjectLine,OBJ_HLINE,0,fecha,price))  //Creamos la linea
        {
         Print("Error: can't create Linea! code #"+ObjectLine,GetLastError());
         return;
        }
      ObjectSetInteger(ChartID(),ObjectLine,OBJPROP_COLOR,c); // Ponemos el color de la línea
      ObjectSetInteger(ChartID(),ObjectLine,OBJPROP_STYLE,estilo); // Ponemos el color de la línea
      ObjectSetInteger(ChartID(),ObjectLine,OBJPROP_WIDTH,width);
     }


   return;
  }

//+------------------------------------------------------------------+
//| Print Line                 |
//+------------------------------------------------------------------+
bool horario()
  {

   bool respuesta = false;

   if(horario_especial == 1)
     {
      // horario 1 es USA, opera desde 9:30 a 16. en horario del broker de 13:30 a 20:00
      int hora = TimeHour(TimeCurrent());
      int min  = TimeMinute(TimeCurrent());
      if((hora < 14) && (hora > 0))
        {

         respuesta =  true;
        }
     }
   else
      if(horario_especial == 2)
        {
         // horario 1 es Alemania, opera desde 9:00 a 17:00. en horario del broker de 13:30 a 20:00
         int hora = TimeHour(TimeCurrent());
         int min  = TimeMinute(TimeCurrent());
         if((hora < 2) && (hora > 10))
           {
            respuesta =  true;
           }
        }
      else
         if(horario_especial == 0)
           {
            // horario 1 es Alemania, opera desde 9:00 a 17:00. en horario del broker de 13:30 a 20:00
            int hora = TimeHour(TimeCurrent());
            int min  = TimeMinute(TimeCurrent());
            if((hora > 23) && (hora < 2))
              {
               respuesta =  true;
              }
           }


   return respuesta;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool analisis_risk_externo()
  {

   string pairsin[] = {"AUDCAD", "AUDUSD", "EURUSD", "GBPAUD", "GBPUSD", "NZDUSD", "USDCAD", "USDJPY","BTCUSD","ETHUSD"};
   int    risk [] = {0,        0,         1,        1,       1,         0,        1,        0,       0,       0      };
   int colas [10] ;

   ArrayInitialize(colas,0);
   bool respuesta = false;



   int count = 0;
   int tipo = -1;
   int ticket = 0;


   for(int j = 0; j < ArraySize(pairsin); j++)
     {

      int i = 0;
      int cont = 0;
      i = OrdersTotal() ;



      if(i >= 0)
        {
         do
           {
            int check = OrderSelect(i-1, 0, 0);
            if(OrderMagicNumber() == MagicNumber &&  OrderProfit()<0)
              {
               if(OrderSymbol() == pairsin[j])
                 {
                  cont = cont+1;
                 }
              }
            i = i - 1;
           }
         while(i >= 0);
        }
      colas [j]= cont;
     }
   for(int j = 0; j < ArraySize(pairsin); j++)
     {
      //printf (pairsin[j]+" = "+IntegerToString(colas[j]));
      if((colas[j]>= Max_vagones) && (risk [j]>=1))
        {
         respuesta = true;
        }
     }

   return respuesta;
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double Calculo_gap(int colain, string modeloTPin, double factorin)
  {
   double gapin = 0;

   if(modeloTPin == "Normal")
     {
      gapin = gap;
     }
   if(modeloTPin == "Corto")
     {
      gapin = (1- (factorin * colain))*gap;
     }
   if(modeloTPin == "Largo")
     {
      gapin = (1+ (factorin * colain))*gap;
     }
   return gapin;
  }


//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
void SET_No_proceso_cronos(datetime & fechain, int minutos)
  {
   datetime dd=  TimeCurrent();
   if(minutos > 0)
      fechain = TimeCurrent()+ (minutos*60);
   else
      fechain = FormatDateZero(TimeCurrent()) + (24*60*60);  // 1 día
   return;
  }



//+------------------------------------------------------------------+
//| Calculo_alerta                    |
//+------------------------------------------------------------------+
bool Calculo_No_proceso_cronos(datetime & fechain, int minutos)
  {
   if(fechain > TimeCurrent())
     {
      fechain = 0;
      return true;
     }
   else
      return false;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double get_bonus_castigo(int bonus_score)
  {

   double bonus_castigo = 1;
   int totaloperaciones = 0;
   int num_perdidas = 0;
   int num_vagones_maximo = 0;
   int max_tren_perdidas = 0;
   resumen_hoy(totaloperaciones, num_perdidas, num_vagones_maximo, max_tren_perdidas);


   if(max_tren_perdidas == Max_vagones)
     {
      bonus_castigo = 0;
     }
   else
     {
      if(num_vagones_maximo ==  Max_vagones)
        {
         bonus_castigo = bonus_castigo -  porcentaje_bonus;
        }
      else
        {
         if((totaloperaciones > 2)  && (num_perdidas == 0))
           {
            bonus_castigo = bonus_castigo +  porcentaje_bonus;
           }
        }
     }

   return bonus_castigo;

  }

//+------------------------------------------------------------------+
//| https://www.x-trader.net/mql4-para-novatos-iv/
//+------------------------------------------------------------------+
datetime FormatDate(datetime dateTime)
  {
   int year = TimeYear(dateTime);
   int month = TimeMonth(dateTime);
   int day = TimeDay(dateTime);
   int hour = TimeHour(dateTime);
   int minute = TimeMinute(dateTime);
   int second = TimeSeconds(dateTime);

//  return StringFormat("%04d-%02d-%02d %02d:%02d:%02d", year, month, day, hour, minute, second);
//datetime new_date = StringToTime(StringFormat("%04d-%02d-%02d 00:00:00", year, month, day));
   string str_new_date = StringFormat("%04d.%02d.%02d", year, month, day);
   datetime new_date = StringToTime(str_new_date);
   return new_date;
  }
//------------------------------------------------------------------------------
string FormatDateHour(datetime dateTime)
  {
   int year = TimeYear(dateTime);
   int month = TimeMonth(dateTime);
   int day = TimeDay(dateTime);
   int hour = TimeHour(dateTime);
   int minute = TimeMinute(dateTime);
   int second = TimeSeconds(dateTime);

   return StringFormat("%02d:%02d",  hour, minute);
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void resumen_hoy(int & totaloperaciones, int & num_perdidas, int & num_vagones_maximo, int &  max_tren_perdidas)
  {

   num_perdidas = 0;
   totaloperaciones = 0;
   max_tren_perdidas = 0;
   num_vagones_maximo = 0;

   datetime dia = TimeCurrent();

   int total = OrdersHistoryTotal();
   if(total > 100)
      total = 100;


   for(int j=0; j<= total -1; j++)
     {
      int operacionesvagon = 0;
      int operacionesvagon_perdidas = 0;
      bool check = OrderSelect(j, SELECT_BY_POS, MODE_HISTORY);

      if((OrderSymbol()==Symbol())     && (OrderMagicNumber()==MagicNumber)
         && (FormatDate(dia)  ==  FormatDate(OrderCloseTime())))
        {
         totaloperaciones ++;
         if(OrderProfit()< 0)
           {
            num_perdidas ++;
           }

         string fclosestr = FormatDateHour(OrderCloseTime());

         for(int z=0; z<= total -1; z++)
           {
            bool check2 = OrderSelect(z, SELECT_BY_POS, MODE_HISTORY);

            if((OrderSymbol()==Symbol())    && (OrderMagicNumber()==MagicNumber) &&
               (FormatDate(dia)  ==  FormatDate(OrderCloseTime())) && (fclosestr  ==  FormatDateHour(OrderCloseTime())))
              {
               operacionesvagon++;
               if(OrderProfit()<0)
                 {
                  operacionesvagon_perdidas++;
                 }
              }
           }
        }
      if(operacionesvagon > num_vagones_maximo)
        {
         num_vagones_maximo  =  operacionesvagon ;
        }
      if(operacionesvagon_perdidas >  max_tren_perdidas)
        {
         max_tren_perdidas = operacionesvagon_perdidas;
        }
     }
   return ;
  }


//*************************************************
//
//*************************************************
void primer_fractal_sentido(string simbolo, int periodoin, double & pr2, int & bar2, string & sentido, int barra_base)
  {
   bool stop = false;
   bool respuesta = false;
   int max = 1000;
   int i = barra_base;
   do
     {
      double tmp_fractalup =       iFractals(simbolo,periodoin,MODE_UPPER,i);
      double tmp_fractaldown =     iFractals(simbolo,periodoin,MODE_LOWER,i);

      if((tmp_fractalup != 0)   && ((sentido=="")  || (sentido=="up")))
        {
         pr2 = tmp_fractalup;
         bar2 = i;
         sentido = "up";
         respuesta = true;
         break;
        }
      if((tmp_fractaldown!=0) && ((sentido=="")   || (sentido=="down")))
        {
         stop = true;
         pr2 = tmp_fractaldown;
         bar2 = i;
         sentido = "down";
         break;
        }
      i++;
     }
   while((!stop) && (i< max));
//***************
   return;
  }
//*************************************************
//
//*************************************************
void reverse_fractal_2(string simbolo, int periodoin,string sentido,int max_breaks,int max_breaks_seguidos,double & pr1, int & bar1, double pr2,int bar2)
  {
   int max = 10000000;
   double pr1_down =  0;
   double pr1_up  =   0;
   int    bar1_up = 0;
   int    bar1_down = 0;
   int   total_breaks = 0;
   int   total_breaks_seguidos = 0;

   if(sentido=="up")  // se usan los lower de creciendo
     {
      pr1_down     =   pr2;
      bar1_down    =   bar2;
      // Busca siguiente punto down
      int i = bar2;
      i++;
      do
        {
         double pr1_tmp  =   iFractals(simbolo,periodoin,MODE_LOWER,i);
         if(pr1_tmp != 0)
           {
            if(pr1_tmp <= pr1_down)
              {
               pr1_down = pr1_tmp;
               bar1_down = i;
               total_breaks_seguidos = 0;
              }
            else
              {
               total_breaks_seguidos ++;
               if(total_breaks_seguidos >max_breaks_seguidos)  // Cuando ya no hay Down sale
                  total_breaks ++;
               if(total_breaks >max_breaks)  // Cuando ya no hay Down sale
                  break;
              }
           }
         i++;
        }
      while(i< max);
      //***************
      pr1  = pr1_down;
      bar1 = bar1_down;
      return;
     }
   if(sentido=="down")
     {
      pr1_up = pr2;
      bar1_up = bar2;
      // Busva un siguiente punto up
      int i = bar2;
      i++;
      do
        {
         double pr1_tmp  =   iFractals(simbolo,periodoin,MODE_UPPER,i);
         if(pr1_tmp != 0)
           {
            if(pr1_tmp >= pr1_up)
              {
               pr1_up = pr1_tmp;
               bar1_up = i;
               total_breaks_seguidos=0;
              }
            else
              {
               total_breaks_seguidos ++;
               if(total_breaks_seguidos >max_breaks_seguidos)  // Cuando ya no hay Down sale
                  total_breaks ++;
               if(total_breaks >max_breaks)  // Cuando ya no hay Down sale
                  break;
              }
           }
         i++;
        }
      while(i< max);
      pr1  = pr1_up;
      bar1 = bar1_up;
      return;
     }
   return ;
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
double profit_hoy()
  {
   double ldProfit = 0;
   int total = OrdersHistoryTotal();
   if(total == 0)
      return 0;
   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, SELECT_BY_POS, MODE_HISTORY);
      if((OrderSymbol()==Symbol())    && (OrderMagicNumber()==MagicNumber))
        {
         if(FormatDate(TimeCurrent())==FormatDate(OrderCloseTime()))
            ldProfit = ldProfit+ OrderProfit();
        }
     }
   return(ldProfit);
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double convert_pips(string simboloin, double valor)
  {
   double respuesta = -1;
   string pairstotal[] =       {"GBPAUD", "GBPUSD", "EURUSD", "AUDUSD", "AUDCAD", "USDCAD", "NZDUSD", "USDJPY", "XAUUSD", "BTCUSD", "ETHUSD",  "NAS100", "US30", "GER40", "USDX"  };
   double pipsconvert[] =        {0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001, 0.001, 0.01, 0.01, 0.01,  0.1, 0.1, 0.1, 0.001   };

   for(int j = 0; j < ArraySize(pairstotal); j++)
     {
      if(simboloin ==   pairstotal[j])
         respuesta = valor/pipsconvert[j];
     }
   return respuesta;
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void Print_LINE(long current_chart_id,string Name,string sTicket,  color c, datetime fecha, int width)
  {
   string simbolo = Symbol();
   string ObjectLine = Name;
   ObjectDelete(ObjectLine); // line open
   if(!ObjectCreate(current_chart_id, ObjectLine,OBJ_VLINE,0,fecha,0,fecha,100))  //Creamos la linea
     {
      //Print("Error: can't create Linea! code #"+ObjectLine ,GetLastError());
      return;
     }
   ObjectSetInteger(current_chart_id,ObjectLine,OBJPROP_COLOR,c); // Ponemos el color de la línea
   ObjectSetInteger(current_chart_id,ObjectLine,OBJPROP_WIDTH,width);
   return;
  }
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
string FormatDateHourMM(datetime dateTime)
  {
   int year = TimeYear(dateTime);
   int month = TimeMonth(dateTime);
   int day = TimeDay(dateTime);
   int hour = TimeHour(dateTime);
   int minute = TimeMinute(dateTime);
   int second = TimeSeconds(dateTime);

   string str_new_date = StringFormat("%04d.%02d.%02d %02d:%02d", year, month, day, hour,minute);
   return str_new_date;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool Max_Bumm(string simbolo, int perido,int tipo_tx,double gapanalisis, double & gapbumm)
  {

   bool respuesta = false;
   int bardesde = 1;
   double pr1 = 0;
   double pr2 = 0;
   double dif = 0;
   datetime d1 = 0;
   datetime d2 = 0;

   respuesta = Validacion_Bumm(tipo_tx,simbolo,perido,pr1, pr2,dif,gapanalisis,gapbumm,d1, d2,bardesde);
//(-1 ambas,

   return respuesta;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
bool Validacion_Bumm(int & tipotx, string simbolo, int periodoin, double & pr1, double & pr2,double & dif, double maxgapfractal,double  & gap_calculado,datetime & d1, datetime & d2, int k)
//  tipo_tx -1 busca en ambos lados
  {
   bool respuesta = false;
   pr1 = 0;
   pr2 = 0;
   d1= 0;
   d2 = 0;
   dif = 0;
   double pr1_tmp_buy = 0;
   double pr2_tmp_buy= 0;;
   double pr1_tmp_sell = 0;
   double pr2_tmp_sell= 0;
   double dif_precio= 0;

   int bar1_buy= 0;
   int bar2_buy= 0;
   int bar1_sell= 0;
   int bar2_sell= 0;
   int bar1= 0;
   int bar2= 0;

   double gap_calculado_buy = 0;
   double gap_calculado_sell = 0;
   string sentido = "";
   RefreshRates();
   color c1 = clrBlack;
   color c2 = clrBlack;

   if((tipotx == OP_BUY)  || (tipotx== -1))
     {
      sentido = "up";
      primer_fractal_sentido(simbolo, periodoin, pr2_tmp_buy,bar2_buy,sentido,k);    //trae el promer up
      reverse_fractal_2(simbolo, periodoin,sentido, quiebre_fractal, quiebres_seguidos,pr1_tmp_buy, bar1_buy,  pr2_tmp_buy, bar2_buy);
      gap_calculado_buy = MathAbs((pr1_tmp_buy - pr2_tmp_buy)/PointVal); // trae el menor de los LOWER
     }
   if((tipotx == OP_SELL)  || ((tipotx == -1)))
     {
      sentido = "down";
      primer_fractal_sentido(simbolo, periodoin, pr2_tmp_sell,bar2_sell,sentido,k);    // trae el primer down
      reverse_fractal_2(simbolo, periodoin,sentido, quiebre_fractal,quiebres_seguidos, pr1_tmp_sell, bar1_sell,  pr2_tmp_sell, bar2_sell);
      gap_calculado_sell = MathAbs((pr1_tmp_sell - pr2_tmp_sell)/PointVal); // trae el mas grade de los UPPER
     }
   if(gap_calculado_buy > gap_calculado_sell)
     {
      pr1 = pr1_tmp_buy;
      pr2 = pr2_tmp_buy;
      bar1 = bar1_buy;
      bar2 = bar2_buy;
      c1 = clrMagenta;
      c2 = clrMagenta;
      tipotx = OP_BUY;
      dif_precio = Ask - pr2_tmp_buy;

     }
   if(gap_calculado_buy < gap_calculado_sell)
     {

      pr1 = pr1_tmp_sell;
      pr2 = pr2_tmp_sell;
      bar1 = bar1_sell;
      bar2 = bar2_sell;

      c1 = clrGold;
      c2 = clrGold;
      tipotx = OP_SELL;
      dif_precio = pr2_tmp_sell - Bid;

     }
   dif = MathAbs(pr2-pr1);
   dif = convert_pips(simbolo,dif);


   if(dif >   maxgapfractal)
     {
      d2 = iTime(Symbol(), Period(),bar2);
      d1 = iTime(Symbol(), Period(),bar1);
      gap_calculado =dif;
      Print_LINE(0, "Maxd2"+ FormatDateHourMM(d2),"0", c1, d2,1);
      Print_LINE(0, "Maxd1"+ FormatDateHourMM(d1),"0", c2, d1+Period()*60,2);
      respuesta = true;
     }
   return respuesta;
  }    //de la funcion


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
bool Validacion_maxfractal(int & tipotx, string simbolo, int periodoin, double & pr1, double & pr2,double & dif, double maxgapfractal,double  & gap_calculado,datetime & d1, datetime & d2, int k)
//  tipo_tx -1 busca en ambos lados
  {
   bool respuesta = false;
   pr1 = 0;
   pr2 = 0;
   d1= 0;
   d2 = 0;
   dif = 0;
   double pr1_tmp_buy = 0;
   double pr2_tmp_buy= 0;;
   double pr1_tmp_sell = 0;
   double pr2_tmp_sell= 0;
   double dif_precio= 0;

   int bar1_buy= 0;
   int bar2_buy= 0;
   int bar1_sell= 0;
   int bar2_sell= 0;
   int bar1= 0;
   int bar2= 0;

   double gap_calculado_buy = 0;
   double gap_calculado_sell = 0;
   string sentido = "";
   RefreshRates();
   color c1 = clrBlack;
   color c2 = clrBlack;

   if((tipotx == OP_BUY)  || (tipotx== -1))
     {
      sentido = "up";
      primer_fractal_sentido(simbolo, periodoin, pr2_tmp_buy,bar2_buy,sentido,k);    //trae el promer up
      reverse_fractal_2(simbolo, periodoin,sentido, quiebre_fractal, quiebres_seguidos,pr1_tmp_buy, bar1_buy,  pr2_tmp_buy, bar2_buy);
      gap_calculado_buy = MathAbs((pr1_tmp_buy - pr2_tmp_buy)/PointVal); // trae el menor de los LOWER
     }
   if((tipotx == OP_SELL)  || ((tipotx == -1)))
     {
      sentido = "down";
      primer_fractal_sentido(simbolo, periodoin, pr2_tmp_sell,bar2_sell,sentido,k);    // trae el primer down
      reverse_fractal_2(simbolo, periodoin,sentido, quiebre_fractal,quiebres_seguidos, pr1_tmp_sell, bar1_sell,  pr2_tmp_sell, bar2_sell);
      gap_calculado_sell = MathAbs((pr1_tmp_sell - pr2_tmp_sell)/PointVal); // trae el mas grade de los UPPER
     }
   if(gap_calculado_buy > gap_calculado_sell)
     {
      pr1 = pr1_tmp_buy;
      pr2 = pr2_tmp_buy;
      bar1 = bar1_buy;
      bar2 = bar2_buy;
      c1 = clrMagenta;
      c2 = clrMagenta;
      tipotx = OP_BUY;
      dif_precio = Ask - pr2_tmp_buy;

     }
   if(gap_calculado_buy < gap_calculado_sell)
     {

      pr1 = pr1_tmp_sell;
      pr2 = pr2_tmp_sell;
      bar1 = bar1_sell;
      bar2 = bar2_sell;

      c1 = clrGold;
      c2 = clrGold;
      tipotx = OP_SELL;
      dif_precio = pr2_tmp_sell - Bid;

     }
   dif = MathAbs(pr2-pr1);
   dif = convert_pips(simbolo,dif);


   if(dif >   maxgapfractal)
     {
      d2 = iTime(Symbol(), Period(),bar2);
      d1 = iTime(Symbol(), Period(),bar1);
      gap_calculado =dif;
      Print_LINE(0, "Maxd2"+ FormatDateHourMM(d2),"0", c1, d2,1);
      Print_LINE(0, "Maxd1"+ FormatDateHourMM(d1),"0", c2, d1+Period()*60,2);
      respuesta = true;
     }
   return respuesta;
  }    //de la funcion



//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool Conteo_Bumm(string simbolo, int perido,int tipo_tx,double gapanalisis, double & gapbumm)
  {

   bool respuesta = false;
   int bardesde = 1;
   double pr1 = 0;
   double pr2 = 0;
   double dif = 0;
   datetime d1 = 0;
   datetime d2 = 0;

   respuesta = Conteo_Validacion_Bumm(tipo_tx,simbolo,perido,pr1, pr2,dif,gapanalisis,gapbumm,d1, d2,bardesde);
//(-1 ambas,

   return respuesta;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
bool Conteo_Validacion_Bumm(int & tipotx, string simbolo, int periodoin, double & pr1, double & pr2,double & dif, double maxgapfractal,double  & gap_calculado,datetime & d1, datetime & d2, int k)
//  tipo_tx -1 busca en ambos lados
  {
   bool respuesta = false;
   pr1 = 0;
   pr2 = 0;
   d1= 0;
   d2 = 0;
   dif = 0;
   double pr1_tmp_buy = 0;
   double pr2_tmp_buy= 0;;
   double pr1_tmp_sell = 0;
   double pr2_tmp_sell= 0;;
   int bar1_buy= 0;
   int bar2_buy= 0;
   int bar1_sell= 0;
   int bar2_sell= 0;
   int bar1= 0;
   int bar2= 0;

   double gap_calculado_buy = 0;
   double gap_calculado_sell = 0;
   string sentido = "";
   RefreshRates();
   color c = clrBlack;
   if((tipotx == OP_BUY)  || (tipotx== -1))
     {
      sentido = "up";
      primer_fractal_sentido(simbolo, periodoin, pr2_tmp_buy,bar2_buy,sentido,k);    //trae el promer up
      reverse_fractal_2(simbolo, periodoin,sentido, quiebre_fractal, quiebres_seguidos,pr1_tmp_buy, bar1_buy,  pr2_tmp_buy, bar2_buy);
      gap_calculado_buy = MathAbs((pr1_tmp_buy - pr2_tmp_buy)/PointVal); // trae el menor de los LOWER
     }
   if((tipotx == OP_SELL)  || ((tipotx == -1)))
     {
      sentido = "down";
      primer_fractal_sentido(simbolo, periodoin, pr2_tmp_sell,bar2_sell,sentido,k);    // trae el primer down
      reverse_fractal_2(simbolo, periodoin,sentido, quiebre_fractal,quiebres_seguidos, pr1_tmp_sell, bar1_sell,  pr2_tmp_sell, bar2_sell);
      gap_calculado_sell = MathAbs((pr1_tmp_sell - pr2_tmp_sell)/PointVal); // trae el mas grade de los UPPER
     }
   if(gap_calculado_buy > gap_calculado_sell)
     {
      pr1 = pr1_tmp_buy;
      pr2 = pr2_tmp_buy;
      bar1 = bar1_buy;
      bar2 = bar2_buy;
      c = clrMagenta;

     }
   else
     {
      pr1 = pr1_tmp_sell;
      pr2 = pr2_tmp_sell;
      bar1 = bar1_sell;
      bar2 = bar2_sell;

      c = clrGold;
     }
   dif = MathAbs(pr2-pr1);
   dif = convert_pips(simbolo,dif);
   if(dif >   maxgapfractal)
     {
      d2 = iTime(Symbol(), Period(),bar2);
      d1 = iTime(Symbol(), Period(),bar1);
      gap_calculado =dif;
      //Print_LINE( 0,"Maxd2"+ FormatDateHourMM(d2),"0", c, d2);
      //Print_LINE(0, "Maxd1"+ FormatDateHourMM(d1),"0", c, d1);
      respuesta = true;
     }
   return respuesta;
  }




//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
double profitsimbol()
  {

   double profit = 0;
   int total = OrdersTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, 0, 0);
      if((OrderSymbol()==Symbol())   && (OrderMagicNumber() == MagicNumber))
        {
         profit = profit + OrderProfit();
        }
     }
   return profit;
  }
//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool profitsimbol_close(double perdida_maxima_experada,datetime fechai, double & profit)
  {
   profit = 0;
   int total = OrdersHistoryTotal();
   if(total == 0)
      return false;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, SELECT_BY_POS, MODE_HISTORY);
      //if((OrderSymbol()==Symbol())   && (FormatDate(OrderCloseTime())== FormatDate(fechai))    && (OrderMagicNumber() == MagicNumber))
      if((OrderSymbol()==Symbol())   && (FormatDate(OrderCloseTime())== FormatDate(fechai))    && (OrderMagicNumber() == MagicNumber))
        {
         profit= profit+ OrderProfit();
        }
     }
   double bal = AccountBalance();
   if((profit < 0) && ((profit/bal)< (-1*perdida_maxima_experada)))
      return true;
   else
      return false;
  }
//**************************************
//**************************************
//************************************************************************************************
//************************************************************************************************
void dif_sopres(string tipo_sopres,int dias,double & dif1, double & dif2, int & regs)
  {
   double precio1 = 0;
   double precio2 = 0;
   int totalregs = 0;
   double tmpprecio = 0;

   if(tipo_sopres == "Soportes")
      tmpprecio = Bid;
   if(tipo_sopres == "Resistencias")
      tmpprecio = Ask;

   Sig_sopres(tipo_sopres,dias,tmpprecio,precio1, precio2,totalregs);
   regs = totalregs;
   dif1 = MathAbs(tmpprecio-precio1);
   dif2 = MathAbs(precio2-precio1);
   return;
  }
//************************************************************************************************
//************************************************************************************************

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void Sig_sopres(string tipostr,int dias,double precio, double & SopRes1, double & SopRes2, int & totalregs)
  {
   double tmp_SopRes1 =  0;

   double tmp_SopRes[100];
   ArrayInitialize(tmp_SopRes, 0);
   int count = 0;
   int tiposr = -1;

   int diaActual = TimeDayOfWeek(TimeCurrent());
   int diasTotal= 0;
   int contadorDiasHabiles = 0;


   while(contadorDiasHabiles < dias)
     {
      diaActual--;
      diasTotal++;
      if(diaActual < 0)
         diaActual = 6; // Restablecer a domingo
      if(diaActual != 0 && diaActual != 6)
         contadorDiasHabiles++;
     }

   if(tipostr=="Soportes")
     {
      tiposr = 1;
      int i = 0;
      count = 0;
      do
        {
         tmp_SopRes1 =  iCustom(NULL,Period(),"Neo_Soportes",diasTotal,15,tiposr,i);
         if(tmp_SopRes1 == EMPTY_VALUE)
           {
            break;
           }
         if(tmp_SopRes1 < precio)
           {
            tmp_SopRes[count] = tmp_SopRes1;
            count++;
           }
         i++;
        }
      while(i<100);
      BubbleSortDouble(tmp_SopRes, "DESC");


     }
   if(tipostr=="Resistencias")
     {
      tiposr = 0;
      int i = 0;
      count = 0;
      do
        {
         tmp_SopRes1 =  iCustom(NULL,Period(),"Neo_Soportes",diasTotal,15,tiposr,i);
         if(tmp_SopRes1 == EMPTY_VALUE)
           {
            break;
           }
         if(tmp_SopRes1 > precio)
           {
            tmp_SopRes[count] = tmp_SopRes1;
            count++;
           }
         i++;
        }
      while(i<100);
      BubbleSortDouble(tmp_SopRes, "ASC");

     }

   SopRes1 = tmp_SopRes[0];
   SopRes2 = tmp_SopRes[1];
   totalregs = count;
   return ;
  }

//+------------------------------------------------------------------+
//| Algoritmo de ordenación por burbuja (Bubble Sort)               |
//+------------------------------------------------------------------+
void BubbleSortDouble(double & levels[], string mode)
  {
   int n = ArraySize(levels);
   for(int i = 0; i < n - 1; i++)
     {
      for(int j = 0; j < n - i - 1; j++)
        {
         if((levels[j] > levels[j + 1])  && (mode == "ASC") && (levels[j+1] >0))
           {
            // Intercambiar los niveles
            double temp = levels[j];
            levels[j] = levels[j + 1];
            levels[j + 1] = temp;
           }
         if((levels[j] < levels[j + 1])  && (mode == "DESC") && (levels[j+1] >0))
           {
            // Intercambiar los niveles
            double temp = levels[j];
            levels[j] = levels[j + 1];
            levels[j + 1] = temp;
           }
        }
     }
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool qry_atr(int pers, double &  atrout,double &  atrout2)
  {
   /*
   double atrout1 = 0;
   double atrout2 = 0;

   bool resp_atr = qry_atr(14, atrout1,atrout2);
   if ((resp_atr ) && (fatr == 1))
   {
                                      printf ("NO OPEN "+oper+"ATR  ATR1%f  ATR2%f "+TimeToStr(TimeCurrent()),atrout1, atrout2);
                                      return false ;
   }
   */
   atrout = iATR(Symbol(), Period(), pers,1);
   atrout2 = iATR(Symbol(), Period(), 4,1);

   if(((atrout < min_atr)  && (atrout2 < min_atr))  || ((atrout > max_atr)&& (atrout > max_atr)))
      return true;
   return false;
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool NO_OPEN_HORARIO(int colain)
  {
//extern int hora_open = 7;
//extern int hora_close= 23;

//int colain = 0;
//bool resp_NO_OPEN = NO_OPEN_HORARIO(colain);
//if (resp_NO_OPEN )
//{
//           printf ("NO OPEN BUY : Fuera Horario   "+ TimeToStr (TimeCurrent()));
//           return 0 ;
//}
   int hora = TimeHour(TimeCurrent());
   if((colain == 0)   && ((hora>hora_close)||(hora<hora_open)))
      return true;
//   if((DayOfWeek()==5) && ((hora>hora_close)||(hora<19)))
//      return true;
   return false;
  }


//+------------------------------------------------------------------+
//| Calculo_accion                    |
//calculo de la accion pero con limites calculados
//+------------------------------------------------------------------+
void  Calculo_accion_m3(int tipo_validacion, string simboloin, double & scorein,int tipoin,int & tipo_accion_buyin, int & tipo_accion_sellin)
  {
   tipo_accion_buyin = 0;
   tipo_accion_sellin = 0;
// Limite red venta, limite gree compra
   limite_compra = 50;
   limite_venta = -50;
   double tmp_tx =   iCustom(NULL,Period(),"Neo_OSC",80,20,15,1,1);
   if(tmp_tx == 1)
     {
      scorein = 90;
      printf("compra");
     }
   if(tmp_tx == -1)
     {
      scorein = -90;
      printf("venta");
     }
   if(tmp_tx == 0)
     {
      scorein = 0;
     }
//write_logTransaccional(TimeCurrent(),Symbol(),Period(),timeframeIndicador,scorein,limite_compra, limite_venta );
//rango_indice_online (limite_compra, limite_venta, Period());
   if(tipo_validacion == 1)  //primer vagon;
     {
      if(tipoin == OP_BUY)
        {
         if(scorein > limite_compra)
           {
            tipo_accion_buyin = 1;
            if(fin_max_vagones)
              {
               tipo_accion_buyin = 0;
              }
            return;
           }
         if(scorein < limite_venta)
           {
            //                  tipo_accion_buyin = -1;
            //                  tipo_accion_sellin = 1;
            if(fin_max_vagones)
              {
               //                           tipo_accion_buyin = -1;
               //                           tipo_accion_sellin = 1;
               //                           tipo_accion_buyin = 0;
              }
            return;
           }
        }
      if(tipoin == OP_SELL)
        {
         if(scorein <  limite_venta)
           {
            //                  if (!fin_max_vagones)
            tipo_accion_sellin = 1;
            if(fin_max_vagones)
              {
               tipo_accion_sellin = 0;
              }
            return;
           }
         if(scorein > limite_compra)
           {
            //                 tipo_accion_buyin =  1;
            //                 tipo_accion_sellin = -1;
            if(fin_max_vagones)
              {
               //                           tipo_accion_sellin = -1;
               //                           tipo_accion_buyin =  1;
               //                           tipo_accion_sellin = 0;
              }
            return;
           }
        }
     }
   if(tipo_validacion == 2)  // vagon;
     {
      if(tipoin == OP_BUY)
        {
         tipo_accion_buyin = 1;
         if(fin_max_vagones)
           {
            tipo_accion_buyin = 0;
           }
         return;
         if(scorein < limite_venta)
           {
            //                        tipo_accion_buyin = -1;
            //                      tipo_accion_sellin = 1;
           }
        }

      if(tipoin == OP_SELL)
        {
         tipo_accion_sellin = 1;
         if(fin_max_vagones)
           {
            tipo_accion_sellin = 0;
           }
         return;
         if(scorein > limite_compra)
           {
            //                      tipo_accion_sellin = -1;
           }
        }
     }
   return ;
  }

//************************************************************************************************
//************************************************************************************************
//************************************************************************************************
//************************************************************************************************
double GET_TP_ATR()
  {
   double respuesta = 0;
   double atrout = 0;
   atrout = iATR(Symbol(), Period(), 14,1);
   respuesta = (atrout* factor_atr_tpsl)/ PointVal;
   //printf("Calculo TP atr: %f  *   factor Tpsl    %f   =   TP %f ",atrout,factor_atr_tpsl,respuesta);
   return respuesta;
  }
//************************************************************************************************
//************************************************************************************************
double CalculateLots(double riskPercentage, double priceDifference, string symbol, int gradas)
  {
//double lotes = CalculateLots(0.01, 0.001, "GBPAUD",3);
//double profitGBPAUD = CalculateProfitLoss("GBPAUD", 1,     0.0018,  3, 1.2, 1.68);
//double profitGBPUSD = CalculateProfitLoss("GBPUSD", 1*0.7, 0.001,   3, 1.2, 1.68);
//double profitEURUSD = CalculateProfitLoss("EURUSD", 1*2, 0.001,   2, 1.2, 1.68);

   double balance = AccountBalance();
   double targetProfit = balance * riskPercentage;
   double tickValue  = MarketInfo(symbol, MODE_TICKVALUE);
   double pointValue = MarketInfo(symbol, MODE_POINT);
   double pipDifference = priceDifference / pointValue;
   int segmentos = SumSegments(gradas);
// Calcular los lotes necesarios
   double lots = targetProfit / (pipDifference * tickValue);
// Ajustar los lotes al tamaño mínimo permitido
   double lotStep = MarketInfo(symbol, MODE_LOTSTEP);
   double minLot  = MarketInfo(symbol, MODE_MINLOT);
   double maxLot  = MarketInfo(symbol, MODE_MAXLOT);
// Ajustar los lotes al paso permitido por el bróker
   lots = NormalizeDouble(lots / lotStep, 0) * lotStep;
// Asegurar que esté dentro del rango permitido
   if(lots < minLot)
      lots = minLot;
   if(lots > maxLot)
      lots = maxLot;

   return lots;
  }
//************************************************************************************************
//************************************************************************************************
int SumSegments(int segments)
  {
   int sum = 0;
   for(int i = segments; i > 0; i--)
     {
      sum += i;
     }
   return sum;
  }
//************************************************************************************************
//************************************************************************************************
double CalculateProfitLoss(string symbol, double initialLots, double gapin, int numOperations, double lotGrowthFactor, double gapGrowthFactor)
  {
   double totalProfitLoss = 0;
   double currentLots = initialLots;
   double currentGap = gapin;
// Declarar arrays dinámicos
   double entryPrices[];
   double lots[];
   ArrayResize(entryPrices, numOperations);
   ArrayResize(lots, numOperations);
// Calcular los precios de entrada y los lotajes de cada operación
   entryPrices[0] = 0; // La primera operación se abre en 0 como referencia
   lots[0] = initialLots;

   for(int i = 1; i < numOperations; i++)
     {
      entryPrices[i] = entryPrices[i - 1] + currentGap;
      lots[i] = lots[i - 1] * lotGrowthFactor;
      currentGap *= gapGrowthFactor;
      int k=0;
     }

// Calcular el precio de cierre basado en el último gap aplicado
   double closingPrice = entryPrices[numOperations - 1] + currentGap;

// Calcular la ganancia o pérdida total
   double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
   double pointValue = MarketInfo(symbol, MODE_POINT);

   for(int i = 0; i < numOperations; i++)
     {
      double profitLoss = (closingPrice - entryPrices[i]) / pointValue * tickValue * lots[i];
      totalProfitLoss += profitLoss;
     }
   return totalProfitLoss;
  }

//+------------------------------------------------------------------+
//|                                                 |
//+------------------------------------------------------------------+
bool Calculo_Lotes_v2()
  {
//extern double Propocion_Lote = 0.6 ; // parametro para AUTOLOT
//extern double Proporcion_Balance = 50000 ;//  // parametro para AUTOLOT
// Por cada 50.000 de Balance el lote es 0.2
   double balance_calculo = AccountEquity(); // Balance
   if(tipo_generacion_lotes == "proyeccion")
     {
      StartingLots = (balance_calculo / Proporcion_Balance) * Propocion_Lote      ;
     }
   else
     {
      StartingLots = (balance_calculo / Proporcion_Balance) * Propocion_Lote      ;
     }

   if(StartingLots < MinLots)
      StartingLots =MinLots;
   return true;
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double consulta_score_transformer(int start, string & resscore)
  {
   // es el v1
   string simbolo  =  Symbol();


   datetime fecha = TimeCurrent();
   string linea = "";
   int max_barra5  = iBarShift(simbolo, 5,fecha, false);
   int max_barra15 = iBarShift(simbolo, 15,fecha, false);

   int total = 10;
   int barra  = 0;
   int barra15 = 0;
   double indice = 0;



   barra = start;
   datetime tmp_fecha = iTime(simbolo,5,barra);
   barra15 = iBarShift(simbolo,15,tmp_fecha,false);

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


   double precioopen5   =  iOpen(simbolo,5,barra);
   double precioclose5  =  iClose(simbolo,5,barra);
   double preciohigh5   =  iOpen(simbolo,5,barra);
   double preciolow5    =  iClose(simbolo,5,barra);
   double vol5          = (double)iVolume(simbolo,5,barra);

   double precioopen15  =  iOpen(simbolo,15,barra15);
   double precioclose15 =  iClose(simbolo,15,barra15);
   double preciohigh15  =  iOpen(simbolo,15,barra15);
   double preciolow15   =  iClose(simbolo,15,barra15);
   double vol15         = (double)iVolume(simbolo,15,barra15);

   string headers = "Content-Type: application/json";
   char result[];
   bool respuesta = false ;
   string symbol = Symbol();

   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];


//https://apipth.onrender.com/predict?
      string api_url2 = "http://172.16.0.4:80/";
   //string api_url = "https://apipth.onrender.com/";

//string post = "{"+ "\"par\":\"" + Symbol()  + "\","+ "\"time_frame\":\""+IntegerToString(timeframeIndicador)+"\""                                    + "}";



   string post = "";
   post= post+              "predict?symbol=" +Symbol()  +"&";
   post= post+              "o5="  +DoubleToStr(precioopen5)   +"&";
   post= post+              "c5=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "h5="  +DoubleToStr(preciohigh5)   +"&";
   post= post+              "l5="   +DoubleToStr(preciolow5)    +"&";
   post= post+              "v5="      +DoubleToStr(vol5)          +"&";
   post= post+              "o15=" +DoubleToStr(precioopen15)  +"&";
   post= post+              "c15="+DoubleToStr(precioclose15) +"&";
   post= post+              "h15=" +DoubleToStr(preciohigh15)  +"&";
   post= post+              "l15="  +DoubleToStr(preciolow15)   +"&";
   post= post+              "v15="     +DoubleToStr(vol15)         +"&";
   post= post+              "r5="         +DoubleToStr(rsi5)          +"&";
   post= post+              "r15="        +DoubleToStr(rsi15)         +"&";
   post= post+              "m5=" +DoubleToStr(stchMain5)     +"&";
   post= post+              "s5=" +DoubleToStr(stchSig5)      +"&";
   post= post+              "m15="+DoubleToStr(stchMain15)    +"&";
   post= post+              "s15="+DoubleToStr(stchSig15) ;


   // string api_url2 = "http://172.16.0.4:80/"+post;
        api_url2 = "http://172.16.0.4:80/"+post;
      //string api_url2 = "https://apipth.onrender.com/"+post;


   char postArray[];
   int length = StringToCharArray(post, postArray);
   int res = WebRequest("GET", api_url2, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      int err = GetLastError();
      printf("error v1 web request %d", res);
      write_log_url("v1","",api_url2,"FAIL Request","0",IntegerToString(err));
      return 0;

     }
   resultado= CharArrayToString(result);
   int numero = StringSplit(resultado, '"',par_respuesta);
   if(numero <= 1)
     {
      write_log_url("v1","",api_url2,"FAIL","0",resultado);
      printf("FAIL 2 Web request error v1 %d", res);
      return 0;
     }
   numero = StringSplit(par_respuesta[7], '}',indice_respuesta);
   string resultado_final ="";

   resultado_final = indice_respuesta[0];
   int len = StringLen(resultado_final);
   if((resultado_final != "NADA") && (resultado_final != "") && (len <6))
   {
      //printf ("SCORE v1  simbolo="+Symbol() + ",resultado =" + resultado_final  + "longitud ="+IntegerToString(len) );
   }


   if(resultado_final == "BUY")
   {

       resscore = resultado_final;
       if(trace_url)
       {
         bool validacion_pre = false;
         string tmp_str = "T2";
         double scorein = StrToDouble(resscore);
         double limite_buy_in=0;
         double limite_sell_in=0;

         validacion_pre= validacion_pre_operacion(tmp_str, scorein, limite_buy_in, limite_sell_in,
                            OP_BUY, flag_fprecios,flag_ffmaxp,flag_ffmaxbum,flag_ffatr,flag_ffhorario,flag_ffsoportes,flag_ffresistencias,flag_ffmax_fractal,flag_ffresbal,flag_ff8,flag_ff9);

         write_log_url("v1","",api_url2,resultado_final,"0","");
      }     

      return 1;
   }
   else
   if(resultado_final == "SELL")
   {
       resscore = resultado_final;
       if(trace_url)
       {
         bool validacion_pre = false;
         string tmp_str = "T2";
         double scorein = StrToDouble(resscore);
         double limite_buy_in=0;
         double limite_sell_in=0;
         validacion_pre= validacion_pre_operacion(tmp_str, scorein, limite_buy_in, limite_sell_in,
                            OP_SELL, flag_fprecios,flag_ffmaxp,flag_ffmaxbum,flag_ffatr,flag_ffhorario,flag_ffsoportes,flag_ffresistencias,flag_ffmax_fractal,flag_ffresbal,flag_ff8,flag_ff9);

         write_log_url("v1","",api_url2,resultado_final,"0","");
       }     


         return -1;
   }
   else
         if(resultado_final == "NADA")
           {
            resscore = resultado_final;
           }
         else
            resscore = "NA";


   return 0;

  }




//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double consulta_score_transformer_v2(int start, string & resscore, double & dif)
  {
   // v2 para Indicadores
   
   string simbolo  =  Symbol();
   double respuesta = 0;

   datetime fecha = TimeCurrent();
   string linea = "";
   int max_barra5  = iBarShift(simbolo, 5,fecha, false);
   int max_barra15 = iBarShift(simbolo, 15,fecha, false);

   int total = 10;
   int barra  = 0;
   int barra15 = 0;
   double indice = 0;
   string  resultado_final ="";
   int numero = 0;
   string stipo = "";
   string sdif = "";



   barra = start;
   datetime tmp_fecha = iTime(simbolo,5,barra);
   barra15 = iBarShift(simbolo,15,tmp_fecha,false);

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


   double precioopen5   =  iOpen(simbolo,5,barra);
   double precioclose5  =  iClose(simbolo,5,barra);
   double preciohigh5   =  iOpen(simbolo,5,barra);
   double preciolow5    =  iClose(simbolo,5,barra);
   double vol5          = (double)iVolume(simbolo,5,barra);

   double precioopen15  =  iOpen(simbolo,15,barra15);
   double precioclose15 =  iClose(simbolo,15,barra15);
   double preciohigh15  =  iOpen(simbolo,15,barra15);
   double preciolow15   =  iClose(simbolo,15,barra15);
   double vol15         = (double)iVolume(simbolo,15,barra15);

   //********************************************************
                     
                  double ema550 =          iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema5200 =         iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema50_prev =      iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double ema5200_prev =    iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double macdLine5 =       iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
                  double signalLine5 =     iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
                  double macdLine_prev5 =  iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1);
                  double signalLine_prev5 =iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
                  double adx5 =            iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MAIN, 0);
                  double diPlus5 =         iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
                  double diMinus5 =        iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MINUSDI, 0);

                  double ema5015 =          iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema20015 =         iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema50_prev15 =     iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double ema200_prev15 =    iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double macdLine15 =       iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
                  double signalLine15 =     iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
                  double macdLine_prev15 =  iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1);
                  double signalLine_prev15 =iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
                  double adx15 =            iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MAIN, 0);
                  double diPlus15 =         iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
                  double diMinus15 =        iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MINUSDI, 0);  
   
   //*********************************************************



   string headers = "Content-Type: application/json";
   char result[];

   string symbol = Symbol();

   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   string indice_respuesta2[];
   string fechas = StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",TimeYear(TimeCurrent()),TimeMonth(TimeCurrent()), TimeDay(TimeCurrent()),TimeHour(TimeCurrent()),TimeMinute(TimeCurrent()), TimeSeconds(TimeCurrent()));    //2025-05-12T00:40:00
   string post = "";
   post= post+              "predict?" ;
   //post= post+              "predict?"  +"&";
   post= post+              "symbol=" +Symbol() +"&";
   post= post+             "fecha=" +fechas  +"&";
   post= post+              "o5="  +DoubleToStr(precioopen5)   +"&";
   post= post+              "c5=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "c5d=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "h5="  +DoubleToStr(preciohigh5)   +"&";
   post= post+              "l5="   +DoubleToStr(preciolow5)    +"&";
   post= post+              "v5="      +DoubleToStr(vol5)          +"&";
   post= post+              "o15=" +DoubleToStr(precioopen15)  +"&";
   post= post+              "c15="+DoubleToStr(precioclose15) +"&";
   post= post+              "h15=" +DoubleToStr(preciohigh15)  +"&";
   post= post+              "l15="  +DoubleToStr(preciolow15)   +"&";
   post= post+              "v15="     +DoubleToStr(vol15)         +"&";
   post= post+              "r5="         +DoubleToStr(rsi5)          +"&";
   post= post+              "r15="        +DoubleToStr(rsi15)         +"&";
   post= post+              "m5=" +DoubleToStr(stchMain5)     +"&";
   post= post+              "s5=" +DoubleToStr(stchSig5)      +"&";
   post= post+              "m15="+DoubleToStr(stchMain15)    +"&";
   post= post+              "s15="+DoubleToStr(stchSig15) ;



   //string api_url2 = "https://apiprpth.onrender.com/"+post;
     string api_url2 = "http://172.16.0.4:80/"+post;
   
   char postArray[];
   int length = StringToCharArray(post, postArray);
   int res = WebRequest("GET", api_url2, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      int err = GetLastError();
      //Print("Error in WebRequest. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' in the list of allowed URLs on tab 'Expert Advisors'", "Error", MB_ICONINFORMATION);
      write_log_url("v2","",api_url2,"FAIL","0",IntegerToString(err));
      //write_log_url("v1","",api_url2,"FAIL Request","0",IntegerToString(err));
      printf("FAIL 1 error v2 %d webrequest", err);
      return(0);
     }
   resultado= CharArrayToString(result);
   numero = StringSplit(resultado, ',',par_respuesta);
   if(numero < 2)
     {
      write_log_url("v2","",api_url2,"FAIL","0",resultado);
      printf("FAIL 2 Web request error v2 %d", res);
      return 0;
     }
//*********************************************************
   /*
   resultado_final ="";
   numero = StringSplit (par_respuesta[3], '}',indice_respuesta);
   if (numero < 2)
   {
      printf ("error %d", res);return 0;
   }
   */
   numero = StringSplit(par_respuesta[0], ':',indice_respuesta2);
   if(numero < 2)
     {
      write_log_url("v2","",api_url2,"FAIL","0",par_respuesta[0]);
      printf("FAIL 3 (dif) error v2 %d", res);
      return 0;
     }
   resultado_final = indice_respuesta2[1];
   sdif = resultado_final;
   dif = StrToDouble(sdif);

//*********************************************************
   resultado_final ="";
   numero = StringSplit(par_respuesta[1], '"',indice_respuesta);
//"prediction":"SELL"
   if(numero < 4)
     {
      write_log_url("v2","",api_url2,"FAIL","0",par_respuesta[1]);
      printf("FAIL 4 (Tx) error v2 %d", res);
      return 0;
     }

   resultado_final =indice_respuesta[3];
   stipo = resultado_final;

   int len = StringLen(stipo);
   if((stipo != "NADA") && (stipo != "") && (len <6))
   {
      //printf ("SCORE V2  simbolo="+Symbol() + ",resultado =" + resultado_final  + "longitud ="+IntegerToString(len) );
   }
   resscore = stipo;
   stipo = "NADA";
//********************************************************
/*
   if(resscore== "BUY")
      respuesta = 1;
   if(resscore== "SELL")
      respuesta = -1;
*/
//********************************************************
      if (dif >= lim_transformer_buy )
      {
            respuesta = 1;
            resscore = "BUY";
            stipo = "BUY";
      }
      if (dif <= lim_transformer_sell )
      {
            respuesta = -1;
            resscore = "SELL";
            stipo = "SELL";
      }
      if(trace_url)
      {
     
            write_log_url("v2","",api_url2,stipo,sdif,"");
      }




      
//*********************************************************      

   return respuesta;

  }




//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double consulta_score_transformer_v5(int start, string & resscore, double & dif)
  {
   // Solo indicadores
   string simbolo  =  Symbol();
   double respuesta = 0;

   datetime fecha = TimeCurrent();
   string linea = "";
   int max_barra5  = iBarShift(simbolo, 5,fecha, false);
   int max_barra15 = iBarShift(simbolo, 15,fecha, false);

   int total = 10;
   int barra  = 0;
   int barra15 = 0;
   double indice = 0;
   string  resultado_final ="";
   int numero = 0;
   string stipo = "";
   string sdif = "";



   barra = start;
   datetime tmp_fecha = iTime(simbolo,5,barra);
   barra15 = iBarShift(simbolo,15,tmp_fecha,false);

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


   double precioopen5   =  iOpen(simbolo,5,barra);
   double precioclose5  =  iClose(simbolo,5,barra);
   double preciohigh5   =  iOpen(simbolo,5,barra);
   double preciolow5    =  iClose(simbolo,5,barra);
   double vol5          = (double)iVolume(simbolo,5,barra);

   double precioopen15  =  iOpen(simbolo,15,barra15);
   double precioclose15 =  iClose(simbolo,15,barra15);
   double preciohigh15  =  iOpen(simbolo,15,barra15);
   double preciolow15   =  iClose(simbolo,15,barra15);
   double vol15         = (double)iVolume(simbolo,15,barra15);

   //********************************************************
                     
                  double ema550 =          iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema5200 =         iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema50_prev =      iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double ema5200_prev =    iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double macdLine5 =       iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
                  double signalLine5 =     iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
                  double macdLine_prev5 =  iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1);
                  double signalLine_prev5 =iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
                  double adx5 =            iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MAIN, 0);
                  double diPlus5 =         iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
                  double diMinus5 =        iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MINUSDI, 0);

                  double ema5015 =          iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema20015 =         iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema50_prev15 =     iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double ema200_prev15 =    iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double macdLine15 =       iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
                  double signalLine15 =     iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
                  double macdLine_prev15 =  iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1);
                  double signalLine_prev15 =iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
                  double adx15 =            iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MAIN, 0);
                  double diPlus15 =         iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
                  double diMinus15 =        iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MINUSDI, 0);  
   
   //*********************************************************



   string headers = "Content-Type: application/json";
   char result[];

   string symbol = Symbol();

   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   string indice_respuesta2[];
   string fechas = StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",TimeYear(TimeCurrent()),TimeMonth(TimeCurrent()), TimeDay(TimeCurrent()),TimeHour(TimeCurrent()),TimeMinute(TimeCurrent()), TimeSeconds(TimeCurrent()));    //2025-05-12T00:40:00
   string post = "";
   post= post+              "predict?"+"&";
   post= post+              "symbol=" +Symbol()  +"v4&";
   post= post+             "fecha=" +fechas  +"&";
   post= post+              "o5="  +DoubleToStr(precioopen5)   +"&";
   post= post+              "c5=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "c5d=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "h5="  +DoubleToStr(preciohigh5)   +"&";
   post= post+              "l5="   +DoubleToStr(preciolow5)    +"&";
   post= post+              "v5="      +DoubleToStr(vol5)          +"&";
   post= post+              "o15=" +DoubleToStr(precioopen15)  +"&";
   post= post+              "c15="+DoubleToStr(precioclose15) +"&";
   post= post+              "h15=" +DoubleToStr(preciohigh15)  +"&";
   post= post+              "l15="  +DoubleToStr(preciolow15)   +"&";
   post= post+              "v15="     +DoubleToStr(vol15)         +"&";
   post= post+              "r5="         +DoubleToStr(rsi5)          +"&";
   post= post+              "r15="        +DoubleToStr(rsi15)         +"&";
   post= post+              "m5=" +DoubleToStr(stchMain5)     +"&";
   post= post+              "s5=" +DoubleToStr(stchSig5)      +"&";
   post= post+              "m15="+DoubleToStr(stchMain15)    +"&";
   post= post+              "s15="+DoubleToStr(stchSig15) +"&";

   //****************************
   post= post+"ema550="+DoubleToStr(ema550) +"&";
   post= post+"ema5200="+DoubleToStr(ema5200) +"&";
   post= post+"ema50_prev="+DoubleToStr(ema50_prev) +"&";
   post= post+"ema5200_prev="+DoubleToStr(ema5200_prev) +"&";
   post= post+"macdLine5="+DoubleToStr(macdLine5) +"&";
   post= post+"signalLine5="+DoubleToStr(signalLine5) +"&";
   post= post+"macdLine_prev5="+DoubleToStr(macdLine_prev5) +"&";
   post= post+"signalLine_prev5="+DoubleToStr(signalLine_prev5) +"&";
   post= post+"adx5="+DoubleToStr(adx5) +"&";
   post= post+"diPlus5="+DoubleToStr(diPlus5) +"&";
   post= post+"diMinus5="+DoubleToStr(diMinus5) +"&";

   post= post+"ema5015="+DoubleToStr(ema5015) +"&";
   post= post+"ema20015="+DoubleToStr(ema20015) +"&";
   post= post+"ema50_prev15="+DoubleToStr(ema50_prev15) +"&";
   post= post+"ema200_prev15="+DoubleToStr(ema200_prev15) +"&";
   post= post+"macdLine15="+DoubleToStr(macdLine15) +"&";
   post= post+"signalLine15="+DoubleToStr(signalLine15) +"&";
   post= post+"macdLine_prev15="+DoubleToStr(macdLine_prev15) +"&";
   post= post+"signalLine_prev15="+DoubleToStr(signalLine_prev15) +"&";
   post= post+"adx15="+DoubleToStr(adx15) +"&";
   post= post+"diPlus15="+DoubleToStr(diPlus15) +"&";
   post= post+"diMinus15="+DoubleToStr(diMinus15) ;
   //******************************


        string api_url2 = "http://172.16.0.4:80/"+post;
   // string api_url2 = "https://apiprpth.onrender.com/"+post;


   char postArray[];
   int length = StringToCharArray(post, postArray);


   int res = WebRequest("GET", api_url2, cookie, NULL, timeout, postArray, length, result, headers);

   if(res == -1)
     {
      int err = GetLastError();
      //Print("Error in WebRequest. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' in the list of allowed URLs on tab 'Expert Advisors'", "Error", MB_ICONINFORMATION);
      write_log_url("v2","",api_url2,"FAIL","0",IntegerToString(err));
      printf("FAIL 1 error v5 %d Webrequest", err);
      return(0);
     }

   resultado= CharArrayToString(result);
   numero = StringSplit(resultado, ',',par_respuesta);
 
   if(numero < 2)
     {
      write_log_url("v2","",api_url2,"FAIL","0",resultado);
      printf("FAIL 2 Web request error v2 %d", res);
      return 0;
     }
//*********************************************************

   /*
   resultado_final ="";
   numero = StringSplit (par_respuesta[3], '}',indice_respuesta);
   if (numero < 2)
   {
      printf ("error %d", res);return 0;
   }
   */
    
   numero = StringSplit(par_respuesta[0], ':',indice_respuesta2);


   if(numero < 2)
     {
      write_log_url("v2","",api_url2,"FAIL","0",par_respuesta[0]);
      printf("FAIL 3 (dif) error v2 %d", res);
      return 0;
     }

   resultado_final = indice_respuesta2[1];

   sdif = resultado_final;
 
   dif = StrToDouble(sdif);

//*********************************************************
   resultado_final ="";
   numero = StringSplit(par_respuesta[1], '"',indice_respuesta);
//"prediction":"SELL"
   if(numero < 4)
     {
      write_log_url("v2","",api_url2,"FAIL","0",par_respuesta[1]);
      printf("FAIL 4 (Tx) error v2 %d", res);
      return 0;
     }

   resultado_final =indice_respuesta[3];
   stipo = resultado_final;

   int len = StringLen(stipo);
   if((stipo != "NADA") && (stipo != "") && (len <6))
   {
      //printf ("SCORE V2  simbolo="+Symbol() + ",resultado =" + resultado_final  + "longitud ="+IntegerToString(len) );
   }
   resscore = stipo;
   stipo = "NADA";

//********************************************************
/*
   if(resscore== "BUY")
      respuesta = 1;
   if(resscore== "SELL")
      respuesta = -1;
*/
//********************************************************
      if (dif >= lim_transformer_buy )
      {
            respuesta = 1;
            resscore = "BUY";
            stipo = "BUY";
      }
      if (dif <= lim_transformer_sell )
      {
            respuesta = -1;
            resscore = "SELL";
            stipo = "SELL";
      }
      
//*********************************************************      
   if(trace_url)
      write_log_url("v2","",api_url2,stipo,sdif,"");

   return respuesta;

  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double consulta_score_transformer_v3(int start, string & resscore, double & dif)
  {
   //===================================================================
   // V2 (05-ago-2026): contrato de API reducido. Se sacaron del request
   // los campos que nunca se usaron o estaban mal calculados (bloque M15
   // ema/macd/adx via 'barra' en vez de 'barra15', y los _prev de M5 que
   // son duplicados de ema550/ema5200). Se agrega atr5. La respuesta ahora
   // trae tp/sl -- el EA ya NO hardcodea TakeProfit/StopLoss por simbolo,
   // los toma de la API para que nunca queden desincronizados del modelo.
   // Ver ApiModels_v2/README.md para el detalle de cada bug encontrado.
   //===================================================================
   string simbolo  =  Symbol();
   double respuesta = 0;
   resscore = "";
   dif = 0;
   datetime fecha = TimeCurrent();

   int barra = start;

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

   string fechas = StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
                                 TimeYear(fecha), TimeMonth(fecha), TimeDay(fecha),
                                 TimeHour(fecha), TimeMinute(fecha), TimeSeconds(fecha));

   string post = "";
   post = post + "predict?";
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

   string headers = "Content-Type: application/json";
   char result[];
   string cookie = NULL;
   char postArray[];
   int length = StringToCharArray(post, postArray);

   string api_url2 = "http://172.16.0.4:80/" + post;
   int res = WebRequest("GET", api_url2, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      int err = GetLastError();
      write_log_url("v2b", "", api_url2, "FAIL", "0", IntegerToString(err));
      printf("FAIL WebRequest v2b error %d", err);
      return(0);
     }

   string resultado = CharArrayToString(result);
   // Respuesta esperada: {"valor_profit":X,"RESULTADO":"BUY|SELL|NADA","tp":Y,"sl":Z}
   double valor_profit = 0;
   string resultado_txt = "NADA";
   double tp_api = 0;
   double sl_api = 0;

   if(!ParsearRespuestaJSON(resultado, valor_profit, resultado_txt, tp_api, sl_api))
     {
      write_log_url("v2b", "", api_url2, "FAIL_PARSE", "0", resultado);
      printf("FAIL parseo de respuesta v2b: %s", resultado);
      return(0);
     }

   dif = valor_profit;
   resscore = resultado_txt;

   if(resultado_txt == "BUY")
      respuesta = 1;
   else if(resultado_txt == "SELL")
      respuesta = -1;
   else
      respuesta = 0;

   // El EA ya NO usa TakeProfit/StopLoss hardcodeados por simbolo: los toma
   // de la API en cada prediccion, para que nunca queden desincronizados
   // del TP/SL con el que se entreno y valido el modelo.
   if(tp_api > 0 && sl_api > 0)
     {
      TakeProfit = tp_api;
      StopLoss   = sl_api;
     }
   else
     {
      printf("AVISO %s: API no devolvio tp/sl valido (tp=%f sl=%f). Se mantiene TakeProfit/StopLoss anterior.",
             simbolo, tp_api, sl_api);
     }

   if(trace_url)
      write_log_url("v2b", "", api_url2, resultado_txt,
                     DoubleToStr(valor_profit),
                     "tp=" + DoubleToStr(tp_api) + ";sl=" + DoubleToStr(sl_api));

   return respuesta;
  }

//+------------------------------------------------------------------+
//| Parseo de la respuesta JSON de /predict por nombre de campo, no  |
//| por posicion. Formato fijo y simple (4 campos, sin anidar) para  |
//| no necesitar una libreria JSON completa en MQL4.                 |
//+------------------------------------------------------------------+
bool ParsearRespuestaJSON(string json, double & valor_profit, string & resultado, double & tp, double & sl)
  {
   valor_profit = 0;
   resultado = "NADA";
   tp = 0;
   sl = 0;

   string vp = ExtraerCampoJSON(json, "valor_profit");
   string rs = ExtraerCampoJSON(json, "RESULTADO");
   string tpS = ExtraerCampoJSON(json, "tp");
   string slS = ExtraerCampoJSON(json, "sl");

   if(vp == "" || rs == "")
      return false;

   valor_profit = StrToDouble(vp);
   resultado = rs;
   tp = StrToDouble(tpS);
   sl = StrToDouble(slS);
   return true;
  }

//+------------------------------------------------------------------+
//| Busca "campo":valor o "campo":"valor" dentro de un JSON plano (sin|
//| objetos anidados). Devuelve "" si no lo encuentra.                |
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
   string valor = StringSubstr(json, inicio, fin - inicio);
   return valor;
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+

double consulta_score_transformer_v4(int start, string & resscore, double & dif)
  {

   string simbolo  =  Symbol();
   double respuesta = 0;

   datetime fecha = TimeCurrent();
   string linea = "";
   int max_barra5  = iBarShift(simbolo, 5,fecha, false);
   int max_barra15 = iBarShift(simbolo, 15,fecha, false);

   int total = 10;
   int barra  = 0;
   int barra15 = 0;
   double indice = 0;
   string  resultado_final ="";
   int numero = 0;
   string stipo = "";
   string sdif = "";



   barra = start;
   datetime tmp_fecha = iTime(simbolo,5,barra);
   barra15 = iBarShift(simbolo,15,tmp_fecha,false);

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


   double precioopen5   =  iOpen(simbolo,5,barra);
   double precioclose5  =  iClose(simbolo,5,barra);
   double preciohigh5   =  iOpen(simbolo,5,barra);
   double preciolow5    =  iClose(simbolo,5,barra);
   double vol5          = (double)iVolume(simbolo,5,barra);

   double precioopen15  =  iOpen(simbolo,15,barra15);
   double precioclose15 =  iClose(simbolo,15,barra15);
   double preciohigh15  =  iOpen(simbolo,15,barra15);
   double preciolow15   =  iClose(simbolo,15,barra15);
   double vol15         = (double)iVolume(simbolo,15,barra15);

   //********************************************************
                     
                  double ema550 =          iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema5200 =         iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema50_prev =      iMA(simbolo, 5, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double ema5200_prev =    iMA(simbolo, 5, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double macdLine5 =       iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
                  double signalLine5 =     iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
                  double macdLine_prev5 =  iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1);
                  double signalLine_prev5 =iMACD(simbolo, 5, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
                  double adx5 =            iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MAIN, 0);
                  double diPlus5 =         iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
                  double diMinus5 =        iADX(simbolo, 5, 14, PRICE_CLOSE, MODE_MINUSDI, 0);

                  double ema5015 =          iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema20015 =         iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, 0);
                  double ema50_prev15 =     iMA(simbolo, 15, 50, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double ema200_prev15 =    iMA(simbolo, 15, 200, 0, MODE_EMA, PRICE_CLOSE, 1);
                  double macdLine15 =       iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 0);
                  double signalLine15 =     iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 0);
                  double macdLine_prev15 =  iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1);
                  double signalLine_prev15 =iMACD(simbolo, 15, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
                  double adx15 =            iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MAIN, 0);
                  double diPlus15 =         iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_PLUSDI, 0);
                  double diMinus15 =        iADX(simbolo, 15, 14, PRICE_CLOSE, MODE_MINUSDI, 0);  
   
   //*********************************************************



   string headers = "Content-Type: application/json";
   char result[];

   string symbol = Symbol();

   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   string indice_respuesta2[];
   string fechas = StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",TimeYear(TimeCurrent()),TimeMonth(TimeCurrent()), TimeDay(TimeCurrent()),TimeHour(TimeCurrent()),TimeMinute(TimeCurrent()), TimeSeconds(TimeCurrent()));    //2025-05-12T00:40:00
   string post = "";
   post= post+              "predict?"+"&";
   post= post+              "symbol=" +Symbol()  +"v3&";
   post= post+             "fecha=" +fechas  +"&";
   post= post+              "o5="  +DoubleToStr(precioopen5)   +"&";
   post= post+              "c5=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "c5d=" +DoubleToStr(precioclose5)  +"&";
   post= post+              "h5="  +DoubleToStr(preciohigh5)   +"&";
   post= post+              "l5="   +DoubleToStr(preciolow5)    +"&";
   post= post+              "v5="      +DoubleToStr(vol5)          +"&";
   post= post+              "o15=" +DoubleToStr(precioopen15)  +"&";
   post= post+              "c15="+DoubleToStr(precioclose15) +"&";
   post= post+              "h15=" +DoubleToStr(preciohigh15)  +"&";
   post= post+              "l15="  +DoubleToStr(preciolow15)   +"&";
   post= post+              "v15="     +DoubleToStr(vol15)         +"&";
   post= post+              "r5="         +DoubleToStr(rsi5)          +"&";
   post= post+              "r15="        +DoubleToStr(rsi15)         +"&";
   post= post+              "m5=" +DoubleToStr(stchMain5)     +"&";
   post= post+              "s5=" +DoubleToStr(stchSig5)      +"&";
   post= post+              "m15="+DoubleToStr(stchMain15)    +"&";
   post= post+              "s15="+DoubleToStr(stchSig15) ;



   //  string api_url2 = "https://apiprpth.onrender.com/"+post;
   //  string api_url2 = "https://apiprpth.onrender.com/"+post;
   string api_url2 = "http://172.16.0.4:80/"+post;
   char postArray[];
   int length = StringToCharArray(post, postArray);
   int res = WebRequest("GET", api_url2, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      int err = GetLastError();
      //Print("Error in WebRequest. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' in the list of allowed URLs on tab 'Expert Advisors'", "Error", MB_ICONINFORMATION);
      write_log_url("v2","",api_url2,"FAIL","0",IntegerToString(err));
      //write_log_url("v1","",api_url2,"FAIL Request","0",IntegerToString(err));
      printf("FAIL 1 error v4 %d Webrequest", err);
      return(0);
     }
   resultado= CharArrayToString(result);
   numero = StringSplit(resultado, ',',par_respuesta);
   if(numero < 2)
     {
      write_log_url("v2","",api_url2,"FAIL","0",resultado);
      printf("FAIL 2 Web request error v2 %d", res);
      return 0;
     }
//*********************************************************
   /*
   resultado_final ="";
   numero = StringSplit (par_respuesta[3], '}',indice_respuesta);
   if (numero < 2)
   {
      printf ("error %d", res);return 0;
   }
   */
   numero = StringSplit(par_respuesta[0], ':',indice_respuesta2);
   if(numero < 2)
     {
      write_log_url("v2","",api_url2,"FAIL","0",par_respuesta[0]);
      printf("FAIL 3 (dif) error v2 %d", res);
      return 0;
     }
   resultado_final = indice_respuesta2[1];
   sdif = resultado_final;
   dif = StrToDouble(sdif);

//*********************************************************
   resultado_final ="";
   numero = StringSplit(par_respuesta[1], '"',indice_respuesta);
//"prediction":"SELL"
   if(numero < 4)
     {
      write_log_url("v2","",api_url2,"FAIL","0",par_respuesta[1]);
      printf("FAIL 4 (Tx) error v2 %d", res);
      return 0;
     }

   resultado_final =indice_respuesta[3];
   stipo = resultado_final;

   int len = StringLen(stipo);
   if((stipo != "NADA") && (stipo != "") && (len <6))
   {
      //printf ("SCORE V2  simbolo="+Symbol() + ",resultado =" + resultado_final  + "longitud ="+IntegerToString(len) );
   }
   resscore = stipo;
   stipo = "NADA";
//********************************************************
/*
   if(resscore== "BUY")
      respuesta = 1;
   if(resscore== "SELL")
      respuesta = -1;
*/
//********************************************************
      if (dif >= lim_transformer_buy )
      {
            respuesta = 1;
            resscore = "BUY";
            stipo = "BUY";
      }
      if (dif <= lim_transformer_sell )
      {
            respuesta = -1;
            resscore = "SELL";
            stipo = "SELL";
      }
      if(trace_url)
      {
     
            write_log_url("v2","",api_url2,stipo,sdif,"");
      }




      
//*********************************************************      

   return respuesta;

  }




//+------------------------------------------------------------------+
//|                                        |
//+------------------------------------------------------------------+
// retorna falso si no se puede hacer la operacion.
// verdad si de debe crear un registro
bool  Calculo_score_accion(int modeloin, int tipoin, int & tipo_accion_buyin,int & tipo_accion_sellin, double & score)
  {
// tipo accion 1 ejecutar transaccion preguntada
   score = 0;
   bool respuesta = false;
   tipo_accion_sellin = 0;
   tipo_accion_buyin  = 0;
   double dif = 0;

// Primero validacion dura
   if((tipoin == OP_BUY)&&(!flag_BUY))
   {
      printf ("Calculo_score_accion  mal flag_BUY..............");
      return false;
   }
   if((tipoin == OP_SELL)&&(!flag_SELL))
   {
      printf ("Calculo_score_accion  mal flag_BUY..............");
      return false;
   }
   if(fin_max_vagones)
   {
      printf ("Calculo_score_accion  mal fin_max_vagones..............");
      return false;
   }
   if(flag_score_modelo)
   {
      score = Score_online(Symbol(), tipoin);
      Calculo_accion_v2(modeloin, Symbol(), score, tipoin,tipo_accion_buyin,tipo_accion_sellin);
      txt_score = DoubleToStr(score);
      printf ("calculo_score_accion flag_modelo_score tempresp...MAL........................");
   }
   else
   {
      double tmp_resp = 0;
      double tmp_resp2 = 0;
      // Si es trace
      // *******************
      if(flag_trace != 0)    // Si esta en modo trace
      {
         score = 99;
         tipoin = OP_BUY;
         tipo_accion_buyin = 1;
         tipo_accion_sellin = 0;
         return true;
      }
      //tmp_resp =  iCustom(NULL,Period(),"Neo_OSC",80,20,15,1,1);
      // *******************
      string txtr = "";

      if(tipo_transformer == 0)
      {
                 
                tmp_resp= consulta_score_transformer(1, txtr);
                printf ("calculo_score_accion v0 MAL tempresp...BUY........................");               
      }
      else
      {
         /*
                     
         if ((Symbol() == "NAS100") || (Symbol() == "GER40")  ||  (Symbol() == "US30")  )
 
                     tmp_resp= consulta_score_transformer_v3(1, txtr,dif);

         else
                     if ((Symbol() == "BTCUSD")   )
                              //tmp_resp= consulta_score_transformer_v4(1, txtr,dif);
                              tmp_resp= consulta_score_transformer_v3(1, txtr,dif);

                     else
          
                              tmp_resp= consulta_score_transformer_v2(1, txtr,dif);
         */
         
         tmp_resp= consulta_score_transformer_v3(1, txtr,dif);
         if ( tmp_resp ==1.0)
         {
               printf ("calculo_score_accion v3 tempresp...BUY........................");
         }
         if ( tmp_resp ==-1.0)
         {
               printf ("calculo_score_accion v3 tempresp...SELL........................");
         }

      }

      if((tmp_resp== 1) && (tipoin == OP_BUY))
      
        {
         /*
         score = 99;
         //tipoin = OP_BUY;
         tipo_accion_buyin = 1;
         tipo_accion_sellin = 0;
         txt_score = DoubleToStr(score);
         return true;
         */
         score = -99;
         //tipoin = OP_SELL;
         tipo_accion_sellin = 1;
         tipo_accion_buyin  = 0;
         txt_score = DoubleToStr(score);
         return true;
         
        }

      
      if((tmp_resp== -1) && (tipoin == OP_SELL))
        {
         
         /*
         score = -99;
         //tipoin = OP_SELL;
         tipo_accion_sellin = 1;
         tipo_accion_buyin  = 0;
         txt_score = DoubleToStr(score);
         return true;

         */
 
          score = 99;
         //tipoin = OP_BUY;
         tipo_accion_buyin = 1;
         tipo_accion_sellin = 0;
         txt_score = DoubleToStr(score);
         return true;
         
         


        }
      else
        {
         score = 0;
         txt_score = DoubleToStr(score);
        }

     }


   return (respuesta);
  }


//+------------------------------------------------------------------+
//| Calculo_accion                    |
//+------------------------------------------------------------------+
bool limites_score(double & limite_compra_in, double & limite_venta_in, int timeframe_in, datetime & fecha_limites)
  {
   string simboloin = Symbol();
   if((limite_compra_in == 0) || (limite_venta_in ==0))
     {
      if(rango_indice_online(limite_compra_in, limite_venta_in, timeframe_in))
        {
         fecha_limites = TimeCurrent();
         return true;
        }
      else
        {
         if(simboloin == "GBPAUD")
           {
            limite_compra_in = 30;
            limite_venta_in =  -50;
           }
         if(simboloin == "GBPUSD")
           {
            limite_compra_in = 30;
            limite_venta_in =  -50;
           }
         if(simboloin == "AUDUSD")
           {
            limite_compra_in = 25;
            limite_venta_in =  -50;
           }
         if(simboloin == "USDJPY")
           {
            limite_compra_in = 30;
            limite_venta_in =  -60;
           }
         if(simboloin == "AUDCAD")
           {
            limite_compra_in = 25;
            limite_venta_in =  -60;
           }

         if(simboloin == "EURUSD")
           {
            limite_compra_in = 25;
            limite_venta_in =  -50;
           }
         if(simboloin == "NZDUSD")
           {
            limite_compra_in = 25;
            limite_venta_in =  -50;
           }

        }
     }
   else
      if(Cambio_de_dia(fecha_limites))
         if(rango_indice_online(limite_compra_in, limite_venta_in, timeframe_in))
           {
            fecha_limites = TimeCurrent();
            return true;
           }
   return true;
  }

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
bool rango_indice_online(double & indice_buy, double & indice_sell, int timeframe)
  {
   string headers = "Content-Type: application/json";
   char result[];
   bool respuesta = false ;
   string symbol = Symbol();
   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   char postArray[];
//************************************
   indice_buy = 50;
   indice_sell = -50;
   return true;
//************************************


   string api_url = "https://tradinapi.azurewebsites.net/rangos_indicador/";

   string post = "{"+ "\"par\":\"" + Symbol()  + "\","+ "\"time_frame\":\""+IntegerToString(timeframe)+"\""                                    + "}";
   int length = StringToCharArray(post, postArray);

   int res = WebRequest("GET", api_url, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      Print("Error in WebRequest indice online. Error code =", GetLastError());
      //         MessageBox("Add the address '"+api_url+"' o revise dado que no está respondiendo a tiempo el servicio", "Error", MB_ICONINFORMATION);
      return(false);
     }

   resultado= CharArrayToString(result);
   int numero = StringSplit(resultado, ':',par_respuesta);

   numero = StringSplit(par_respuesta[1], '}',indice_respuesta);
   indice_buy = StringToDouble(indice_respuesta[0]);

   numero = StringSplit(par_respuesta[2], ':',indice_respuesta);
   indice_sell = StringToDouble(indice_respuesta[0]);

   if((indice_sell!= 0)||(indice_buy!=0))
      return(true);
   else
      return false;
  }

//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
void profitsimbol_close_presupuesto(datetime fechai, double & profit,int & transaccpos, int & transaccneg)
  {
   /*
      profitsimbol_close_presupuesto(TimeCurrent(), profit_cerrado, tx_cerradas_pos, tx_cerradas_neg);
      if (  (profit_cerrado > 0 )     &&  (tx_cerradas_pos >= max_tx_pos) )
      {
                          printf ("NO OPEN VALIDACION PRESUPUESTO profit POSITIVO %f   tx %d",profit_cerrado,tx_cerradas_pos );
                          return  false;
      }
      if (  (profit_cerrado < 0 )     &&  (tx_cerradas_neg >= max_tx_pos) )
      {
                          printf ("NO OPEN VALIDACION PRESUPUESTO profit NEGATIVO %f   tx %d",profit_cerrado,tx_cerradas_pos );
                          return  false;
      }
   */
   profit = 0;
   int total = OrdersHistoryTotal();
   if(total == 0)
      return ;

   for(int i=0; i<= total -1; i++)
     {
      bool check = OrderSelect(i, SELECT_BY_POS, MODE_HISTORY);
      if((OrderSymbol()==Symbol())   && (FormatDate(OrderCloseTime())== FormatDate(fechai))    && (OrderMagicNumber() == MagicNumber))
         //if(                                 (FormatDate(OrderCloseTime())== FormatDate(fechai))    && (OrderMagicNumber() == MagicNumber))
        {
         profit= profit+ OrderProfit();
         if(OrderProfit() >0)
            transaccpos ++;
         if(OrderProfit() <0)
            transaccneg ++;

        }
     }

   return ;
  }
//***************************************
//***************************************
void DrawEvent(string evento)
  {

   string evento_txt = "";
   double precio = High[1]+(MarketInfo(Symbol(), MODE_POINT) * 20);
   color c = clrOrange;
   int style = STYLE_SOLID;
   int width = 1;
   int tipo = -1;
   int fsize = 8;
   string name = evento+TimeToStr(TimeCurrent());

   if(tipo == OP_BUY)  {; }
   if(tipo == OP_SELL) {;  }

   if(evento == "PRECIO")
     {
      evento_txt = "PR";
     }
   if(evento == "DURO")
     {
      evento_txt =  "X";
     }
   if(evento == "MAXPERDIDA")
     {
      evento_txt = "$";
     }
   if(evento == "MAXFRACTAL")
     {
      evento_txt = "M$";
     }
   if(evento == "RESBAL")
     {
      evento_txt = "REB";
     }
   if(evento == "BUMCONTRARIO")
     {
      evento_txt = "BU";
     }
   if(evento == "ATR")
     {
      evento_txt = "AT";
     }
   if(evento == "FUERAHORARIO")
     {
      evento_txt = "HH";
     }
   if(evento == "NORESIST")
     {
      evento_txt = "NR";
     }
   if(evento == "NOSOP")
     {
      evento_txt = "NS";
      precio = Low[1];
     }
   if(evento == "TOPESUP")
     {
      evento_txt = "TS";
     }
   if(evento == "TOPEINF")
     {
      evento_txt = "TI";
      precio = Low[1] ;
     }



   DrawCustomObject(name, evento_txt, TimeCurrent(), precio, c,style,width,fsize) ;

   return;
  }
//*******************
//********************
void DrawCustomObject(string name, string evento_txt, datetime time, double price, color c, int style, int width, int fsize)
  {
   ResetLastError();
   // Crear el objeto
   if(ObjectFind(0, name) == -1)  // -1 significa que no existe
   {
      if(!ObjectCreate(0, name, OBJ_TEXT, 0, time, price))
      {
         int err = GetLastError();
         PrintFormat("Error al crear el objeto '%s': %d", name, err);
         return;
      }
   }
// Configurar propiedades
   ObjectSetString(0,name,OBJPROP_TEXT,evento_txt);
   ObjectSetInteger(0,name,OBJPROP_COLOR, c);
//ObjectSetInteger(0,name,OBJPROP_STYLE, style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH, width);   // Ancho opcional
   ObjectSetString(0,name,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,fsize);
   ObjectSetDouble(0,name,OBJPROP_ANGLE,0);
//ObjectSetInteger(0,name,OBJPROP_ANCHOR,ANCHOR_UPPER);
   return;
  }
//******************************************
//******************************************
//************************************************************************************************
//************************************************************************************************
//************************************************************************************************
//************************************************************************************************
//************************************************************************************************
//************************************************************************************************
bool validacion_pre_operacion(string algor,double scorein, double limite_buy_in, double limite_sell_in,int tipo, int fprecio,int fmaxp,int fmaxbum,int fatr,int fhorario, int fsoportes, int fresistencias, int fmaxfrac, int f7, int f8, int f9)
  {

   resp_fprecio = 0;
   resp_fmaxp = 0;
   resp_fmaxbum = 0;
   resp_fatr = 0;
   resp_fhorario = 0;
   resp_fsoportes = 0;
   resp_fresistencias = 0;
   //resp_fmaxfrac = 0;
   resp_fmax_fractal = 0;
   resp_fresbal = 0;
   resp_f8 = 0;
   resp_f9 = 0;
   int num_validaciones = 0;

   bool respuesta = true;
   string  oper = "";
   int contra_oper = -1;
   if(tipo == OP_BUY)
   {
      oper = " BUY " ;
      contra_oper = OP_SELL ;
   }
   if(tipo == OP_SELL)
   {
      oper = " SELL ";
      contra_oper = OP_BUY;
   }
   double preciom2 = 0;
   double preciom1 = 0;

   bool bool_val_precio = validacion_precios(tipo,Symbol(),Period(),preciom2,preciom1);
   if((bool_val_precio) && (fprecio == 1))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("PRECIO");
      resp_fprecio = 1;
      printf("NO OPEN "+oper+"PRECIO: pmenos2 %f   pmenos1 %f"+" "+TimeToStr(TimeCurrent()),preciom2,preciom1);
      //return  false;
   }

   double nuevo_dif_fractal = 0;
   double profit_perdida = 0;
   bool bool_max_perdida = profitsimbol_close(max_perdida_cuenta,TimeCurrent(), profit_perdida);
   if((bool_max_perdida) && (fmaxp == 1))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("MAXPERDIDA");
      resp_fmaxp = 1;
      printf("NO OPEN "+oper+"MAX PERDIDA:  %f"+" "+TimeToStr(TimeCurrent()),profit_perdida);
      //return  false;
   }
   
   int tipo_tx_tmp = -1;
   bool resp_new = Max_Bumm(Symbol(),Period(),tipo_tx_tmp,gap_ult_fractal,nuevo_dif_fractal);
   if((resp_new) && (fmaxbum == 1) && (tipo_tx_tmp !=tipo))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("BUMCONTRARIO");
      resp_fmaxbum = 1;
      printf("NO OPEN "+oper+"BUM CONTRARIO %f "+" "+TimeToStr(TimeCurrent())+TimeToStr(TimeCurrent()),nuevo_dif_fractal);
      //return false ;
   }
   double atrout1 = 0;
   double atrout2 = 0;
   bool resp_atr = qry_atr(14, atrout1,atrout2);
   if((resp_atr) && (fatr == 1))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("ATR");
      resp_fatr =1;
      printf("NO OPEN "+oper+"ATR  ATR1%f  ATR2%f "+TimeToStr(TimeCurrent()),atrout1, atrout2);
      //return false ;
   }
   int colain = cola;
   bool resp_NO_OPEN = NO_OPEN_HORARIO(colain);
   if((resp_NO_OPEN) && (fhorario == 1))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("FUERAHORARIO");
      resp_fhorario = 1;
      printf("NO OPEN "+oper+"Fuera Horario   "+ TimeToStr(TimeCurrent()));
      //return false ;
   }
   double dif1 = 0;
   double dif2 = 0;
   int totalregs = 0;
   int dias = 2;
//dif_sopres("Soportes",dias,dif1, dif2,totalregs);
   /*
   dif_sopres("Resistencias",dias ,dif1, dif2,totalregs);
   if ((totalregs < 2 ) && (fsoportes == 1))
   {
                                      DrawEvent("NORESIST");
                                      printf ("NO OPEN "+oper+"No Resistencias  %d"+" "+TimeToStr(TimeCurrent()),totalregs);
                                      return false ;
   }

   dif_sopres("Soportes",dias ,dif1, dif2,totalregs);
   if ((totalregs < 2 ) && (fresistencias == 1))
   {
                                      DrawEvent("NOSOP");
                                      printf ("NO OPEN "+oper+"No Soportes  %d"+" "+TimeToStr(TimeCurrent()),totalregs);
                                      return false ;
   }
   */
   double tope_altoin = 0;
   double tope_bajoin = 0;
   double inicial = 0;
   topes_dia(FormatDateZero(TimeCurrent()), TimeCurrent(),  tope_altoin,tope_bajoin, inicial);
   if((tipo == OP_BUY)&&(fresistencias == 1)&& (Ask+(3*TakeProfit*PointVal) > tope_altoin))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("TOPESUP");
      resp_fresistencias = 1;
      printf("NO OPEN "+oper+"CERCA TOPE SUP  Ask %f,tope_altoin %f  "+" "+TimeToStr(TimeCurrent()),totalregs,tope_altoin);
      //return false ;
   }
   if((tipo == OP_SELL)&&(fresistencias == 1) && (Bid-(3*TakeProfit*PointVal) < tope_bajoin))
   {
      if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
         DrawEvent("TOPEINF");
      resp_fresistencias = 1;
      printf("NO OPEN "+oper+"CERCA TOPE INF  Bid %f,tope_bajoin %f "+" "+TimeToStr(TimeCurrent()),totalregs,tope_bajoin);
      //return false ;
   }
   if(fmaxfrac)
   {
      double max_buy = 0;
      double max_sell = 0;

      bool maxfrac = validacion_max_fractal(Symbol(),Period(),gap_ult_fractal,quiebre_fractal,quiebres_seguidos,gap_max_fractal,FormatDateZero(TimeCurrent()), max_buy, max_sell);

      if(maxfrac)
      {
         if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
            DrawEvent("MAXFRACTAL");
         resp_fmax_fractal = 1;
         printf("NO OPEN "+oper+" MAX FRACTAL DIA   "+ TimeToStr(TimeCurrent()));
         //return false ;
      }
      //*****************
      double pr1 = 0;
      double pr2 = 0;
      
      bool resbal= validacion_resbaladera(tipo,Symbol(),Period(),gap_ult_fractal,quiebre_fractal,quiebres_seguidos,gap_max_fractal,pr1,pr2);
      if(resbal)
      {
         if(!validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
            DrawEvent("RESBAL");
         resp_fresbal = 1;
         printf("NO OPEN "+oper+" RESBAL   "+ TimeToStr(TimeCurrent()));
         //return false ;
      }      
      
      //*****************


     }
   if(validacion_unos(resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias, resp_fmax_fractal, resp_fresbal,resp_f8,resp_f9,num_validaciones))
     {
      respuesta = false;
     }

   write_log_validacion_pre(algor,tipo,Symbol(),Period(),timeframeIndicador,scorein,limite_buy_in,limite_sell_in,resp_fprecio,resp_fmaxp,resp_fmaxbum,resp_fatr,resp_fhorario,resp_fsoportes,resp_fresistencias,
                            resp_fmax_fractal,resp_fresbal, resp_f8,resp_f9);

   return respuesta;
  }
//************************************
//************************************

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool validacion_unos(int resp_fprecio1,int resp_fmaxp1,int resp_fmaxbum1,int resp_fatr1, int resp_fhorario1,int resp_fsoportes1,int resp_fresistencias1,
                     int resp_fmax_fractal1, int resp_fresbal1,    int resp_f81,   int resp_f91, int & num_unos)
  {



   bool  respuesta = false;
   if(
      (resp_fprecio1 ==1) ||
      (resp_fmaxp1 == 1) ||
      (resp_fmaxbum1 == 1) ||
      (resp_fatr1 == 1) ||
      (resp_fhorario1 == 1) ||
      (resp_fsoportes1 == 1) ||
      (resp_fresistencias1 == 1) ||
      (resp_fmax_fractal1 == 1) ||
      (resp_fresbal1 == 1) ||
      (resp_f81 == 1) ||
      (resp_f91 == 1)
   )
     {
      respuesta = true;
     }
   num_unos= resp_fprecio1 +resp_fmaxp1 + resp_fmaxbum1 + resp_fatr1 + resp_fhorario1 + resp_fsoportes1 +resp_fresistencias1 + resp_fmax_fractal1 +resp_fresbal1 +resp_f81 +resp_f91;
   return respuesta;
  }



//***************************************
//***************************************
void max_segmentos(string simbolo,int timeframe_indicador,double gap_ult_fractal_in,int quiebre_fractal_in,int quiebres_seguidos_in,datetime fechadesde, double & max_buy, double & max_sell)
  {

   max_buy = 0;
   max_sell = 0;
   int barrafinal = iBarShift(Symbol(), 0, fechadesde, false);
   double dif = 0;
   bool primero = true;
   for(int i = 1; i<barrafinal; i++)
     {
      dif = 0;
      double tmp_down =    iCustom(simbolo,timeframe_indicador,"Neo_MMF",timeframe_indicador,gap_ult_fractal,quiebre_fractal,quiebres_seguidos,0,0,i);
      double tmp_up =      iCustom(simbolo,timeframe_indicador,"Neo_MMF",timeframe_indicador,gap_ult_fractal,quiebre_fractal,quiebres_seguidos,0,1,i);
      int j = 0;
      if(tmp_down != 0)
        {
         if(primero)
           {
            max_buy = MathAbs(Ask- tmp_down);
            primero = false;
            i --;
            continue;

           }


         for(j = i; j < barrafinal; j++)
           {
            dif = 0;
            double tmp_up2 =      iCustom(simbolo,timeframe_indicador,"Neo_MMF",timeframe_indicador,gap_ult_fractal,quiebre_fractal,quiebres_seguidos,0,1,j);
            if(tmp_up2!=0)
              {
               dif = MathAbs(tmp_down-tmp_up2);
               break;
              }
           }
         i=j-1;
         if(dif > max_sell)
            max_sell = dif;

        }
      if(tmp_up != 0)
        {

         if(primero)
           {
            max_sell = MathAbs(Bid- tmp_up);
            primero = false;
            i --;
            continue;

           }

         for(j = i; j < barrafinal; j++)
           {
            dif = 0;
            double tmp_down2 =      iCustom(simbolo,timeframe_indicador,"Neo_MMF",timeframe_indicador,gap_ult_fractal,quiebre_fractal,quiebres_seguidos,0,0,j);
            if(tmp_down2!=0)
              {
               dif = MathAbs(tmp_up-tmp_down2);
               break;
              }
           }
         i=j-1;
         if(dif > max_buy)
            max_buy = dif;

        }


     }


   return;
  }
//***************************************
//***************************************
bool validacion_max_fractal(string simbolo,int timeframe_indicador,double gap_ult_fractal_in,int quiebre_fractal_in,int quiebres_seguidos_in,double gap_max_fractal_in,datetime fechadesde, double & max_buy, double & max_sell)
  {

   bool respuesta = false;


   double max_buy_in = 0;
   double max_sell_in = 0;
   max_segmentos(simbolo,timeframe_indicador,gap_ult_fractal_in,quiebre_fractal_in,quiebres_seguidos_in,fechadesde, max_buy_in, max_sell_in);
   double max_dif = gap_max_fractal_in * PointVal;

   if(max_dif <= max_buy_in)
     {
      max_buy = max_buy_in;
      respuesta = true;
     }
   if(max_dif <= max_sell_in)
     {
      max_sell = max_sell_in;
      respuesta = true;
     }



   return respuesta;
  }

//***************************************
//***************************************
bool validacion_precios(int tipoin,string simbolo,int periodoin,double & prm2,double & prm1)
  {

   bool respuesta = false;
   prm2 = 0;
   prm1 = 0;

   prm2 = iClose(simbolo, periodoin, 2); // Precio de cierre del Timeframe , 0 Current, periodos atras
   prm1 = iClose(simbolo, periodoin, 1); // Precio de cierre del Timeframe , 0 Current, 1 peíodo atras

   if((tipoin == OP_BUY) && (prm2 <  prm1))
      respuesta = true;
      
   if((tipoin == OP_SELL) && (prm2 >  prm1))
      respuesta = true;

      return respuesta;
     }



//***************************************
//***************************************
void Sync_oper()
{


   int cuenta_to_sync = 0;
   int num_cuentas_to_sync = ArraySize(cuentas_sync);
   int ticket = 0;
   int index = -1;
   
   int j = OrdersTotal() - 1;
   if(j >= 0)
   {
      do
        {
         int order_checkin = OrderSelect(j, 0, 0);
         if(  OrderSymbol() == _Symbol && OrderMagicNumber() &&   OrderProfit()>0 )
         {
            if(OrderType() == OP_BUY || OrderType() == OP_SELL)
            {
                  ticket = OrderTicket();
                  for (int x = 0; x < ArraySize(ticksync); x++)
                  {
                           if (ticksync[x] == ticket)
                           {
                                 index = x;
                                 break;
                           }
                  }
                     
                  if (index == -1)
                  {
                           int   newsize =  ArraySize(ticksync) + 1;
                           ArrayResize(ticksync, newsize);
                           ticksync[newsize - 1] = ticket;
                           
                           //Sincronizar
                           int ticketin = OrderTicket();
                           double lotesin = OrderLots();
                           
                           string tipoin = "";
                           if (OrderType() == OP_BUY)  tipoin = "BUY";
                           if (OrderType() == OP_SELL)  tipoin = "SELL";
                           
                           datetime opentimein = OrderOpenTime();
                           double pricein = OrderOpenPrice();
                           int magicin = OrderMagicNumber();
                           double vsl = OrderStopLoss();
                           double vtp = OrderTakeProfit();
                           double profitin = OrderProfit();
                           double slin = 0 ;
                           double tpin = 0 ;
                           if (OrderStopLoss() !=0)
                              slin = MathAbs(pricein - OrderStopLoss()) ;

                           if (OrderTakeProfit() !=0)
                              tpin = MathAbs(pricein - OrderTakeProfit()) ;
                           

                           string resp = "";
                           
                           for (int y = 0;y< num_cuentas_to_sync; y++)
                           {
                                 bool f = dispatchsend(cuentas_sync[y],ticketin,Symbol(),lotesin,tipoin,opentimein,pricein,magicin,slin,tpin,profitin,resp);
                                 if (!f)
                                 {
                           
                                       printf("Error Sync origen %d ,cuenta %d",ticketin,cuentas_sync[y]);
                                       return ;
                                 }
                           }
                           printf("Dispatch ticket %d a token",ticketin,cuenta_sync );
                           //bool r = dispatchreceive("BTCUSD",TimeCurrent());
                           //string resp1 = "";
                           //bool f1 = dispatchsend(9999,"BTCUSD",1.19,"BUY",TimeCurrent(),Ask,MagicNumber,3000,4000,1200,resp1);
                           
                  }
            }
           }
         j = j - 1;
        }
      while(j >= 0);
     }
     else
     {
                            ArrayResize(ticksync, 0);
     }




return;
}
//**************************************************************************
//*************************************************************************

bool dispatchsend(int cuenta_sync_in ,int ticket,string simbolo,double lotes,string tipotx,datetime fechai, double precio,int magic,double sl, double tp,double profit, string & retorno)
  {

   string headers = "Content-Type: application/json";
   char result[];

   bool respuesta = false ;
   string msgsend = "";


   string cookie = NULL;
   string resultado = "";
   string par_respuesta[]  ;
   string indice_respuesta[];
   char postArray[];
   string api_url = "https://tradinapi.azurewebsites.net/dispatcher/";


   int numero = 0;
   string formattedDateini = FormatDateTimeToCustomFormat2(fechai);


  //select dispatcher('syncsend,   EURUSD,20040,20050,12345,EURUSD,0.69,BUY,2025-07-04 17:59:56,1.39001, 777777,0.00005,0.000005,2.25');
  //select dispatcher('syncreceive,EURUSD,20050, 2025-07-04 20:59:56');


   string tx = "syncsend"+","+
               simbolo+","+
               IntegerToString(AccountNumber())+","+
               IntegerToString(cuenta_sync_in)+","+
               IntegerToString(ticket)+","+
               simbolo+","+
               DoubleToString (lotes)+","+
               tipotx+","+
               TimeToString (fechai)+","+
               DoubleToString(precio)+","+
               IntegerToString(magic)+","+
               DoubleToString(sl)+","+
               DoubleToString(tp)+","+
               DoubleToString(profit);
               

   //msgsend = tx+","+simbolo;
   string url_with_params = api_url  + "?entrada=" + tx ;
   
   //url_with_params="https://tradinapi.azurewebsites.net/dispatcher/?entrada=tendencia,EURUSD";
   int length  = StringToCharArray(url_with_params, postArray);

   ResetLastError();
   printf("Trama: "+url_with_params);
   printf("SL: %f  TP: %f ",sl,tp);
   int res = WebRequest("GET", url_with_params, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      Print("Error in WebRequest dispatch. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' in the list of allowed URLs on tab 'Expert Advisors'", "Error", MB_ICONINFORMATION);
      retorno = "Error Rquest";
      return(false);
     }

   resultado= CharArrayToString(result);


   numero = StringSplit(resultado, ',',par_respuesta);

// primer parametro
   string resp = par_respuesta[0];


   resp = limpiar_string_char(resp,"{");
   resp = limpiar_string_char(resp,"\"");
   resp = limpiar_string_char(resp,"resultado:");
   resp = limpiar_string_char(resp," ");

   retorno = resp;
   if( (resp != "Duplicate") && (resp != "Exito"))
   {

      return false;
   }
   printf ("Sync ok, %d",ticket);
   return true;
  }

//**************************************************
//**************************************************
bool dispatchreceive(string simbolo,datetime fechain)
  {

   string headers = "Content-Type: application/json";
   char result[];

   bool respuesta = false ;
   string msgsend = "";


   string cookie = NULL;
   string resultado = "";
   string par_respuesta[20]  ;
   string indice_respuesta[];
   char postArray[];
   string api_url = "https://tradinapi.azurewebsites.net/dispatcher/";


   int numero = 0;
   string formattedDateini = FormatDateTimeToCustomFormat2(fechain);


  //select dispatcher('syncsend,   EURUSD,20040,20050,12345,EURUSD,0.69,BUY,2025-07-04 17:59:56,1.39001, 777777,0.00005,0.000005,2.25');
  //select dispatcher('syncreceive,EURUSD,20050, 2025-07-04 20:59:56');


   string tx = "syncreceive"+","+
               simbolo+","+
               IntegerToString(cuenta_sync)+","+
               TimeToString (fechain);


   //msgsend = tx+","+simbolo;
   string url_with_params = api_url  + "?entrada=" + tx ;
   
   //url_with_params="https://tradinapi.azurewebsites.net/dispatcher/?entrada=tendencia,EURUSD";
   int length  = StringToCharArray(url_with_params, postArray);

   ResetLastError();
   int res = WebRequest("GET", url_with_params, cookie, NULL, timeout, postArray, length, result, headers);
   if(res == -1)
     {
      Print("Error in WebRequest dispatch. Error code =", GetLastError());
      //        MessageBox("Add the address '"+api_url+"' in the list of allowed URLs on tab 'Expert Advisors'", "Error", MB_ICONINFORMATION);
      return(false);
     }

   resultado= CharArrayToString(result);


   numero = StringSplit(resultado, ',',par_respuesta);

// primer parametro
   string resp = par_respuesta[0];
   resp = limpiar_string_char(resp,"{");
   resp = limpiar_string_char(resp,"\"");
   resp = limpiar_string_char(resp,"resultado:");
   resp = limpiar_string_char(resp," ");

   if (resp != "Exito") 
      return false;


        string ssimbolo = par_respuesta[1];
        string sid = par_respuesta[2];
        string scuenta_origen = par_respuesta[3];
        string sticket = par_respuesta[4];
        string slotes = par_respuesta[5];
        string stipo = par_respuesta[6];
        string sfecha_receive = par_respuesta[7];
        string sprecio = par_respuesta[8];
        string smagic = par_respuesta[9];
        string ssl = par_respuesta[10];
        string stp = par_respuesta[11];
        string sprofit = par_respuesta[12];

        sprofit= limpiar_string_char(sprofit,"}");

        int vtipo = -1;
        double vlotes = StrToDouble(slotes)* factor_sinc;
        int slsl = 0;
        int tptp = 0;
        double precioin = 0;
        int vmagic = StrToInteger(smagic);
        printf("Sinc oper"+", "+ssimbolo+", "+sid+", "+scuenta_origen+", "+sticket+", "+slotes+", "+stipo+", "+sfecha_receive+", "+sprecio+", "+smagic+", "+ssl+", "+stp+", "+sprofit);
        string tmp_str = "SINC";
        if (stipo == "BUY")
        {
            vtipo = OP_BUY;
            precioin = Ask;
            slsl =   (int)(StrToDouble(ssl) / PointVal) ;
            tptp =   (int)(StrToDouble(stp) / PointVal);
        
        }
        if (stipo == "SELL")
        {
        
            vtipo = OP_SELL;
            precioin = Bid;
            slsl =   (int)(StrToDouble(ssl)/ PointVal);
            tptp =   (int)(StrToDouble(stp)/ PointVal);
        }
        vlotes = NormalizeDouble(vlotes,2);
        vlotes = AjustarVolumenAlPaso(vlotes);
        int new_ticket = OpenPendingOrder(vtipo, vlotes, Ask, 30, Ask, slsl, tptp, tmp_str, vmagic, 0, 11823615);
         if(new_ticket < 0)
         {
            Print("NewT Error: ", GetLastError(), " Lotes ", DoubleToStr(vlotes)," factor ",DoubleToStr(factor_lote_indicador), "sl ",IntegerToString(slsl) ," tp ",IntegerToString(tptp) );
            return false;
         }

        
        return true;
  }

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
string limpiar_string_char(string strin, string caracter)
  {

   string textolimpio = strin;

   while(StringFind(textolimpio, "\n") >= 0)
     {
      StringReplace(textolimpio, "\n","");
     }

   while(StringFind(textolimpio, caracter) >= 0)
     {
      StringReplace(textolimpio, caracter,"");
     }


   return textolimpio;
  }
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------


//+------------------------------------------------------------------+
//|
//+------------------------------------------------------------------+
bool tendenciaonline(int & intipo,string insimbol,datetime & infecha,datetime & infechai,datetime & infechaf,double & insl, double & intp,double & inbase)
  {


   string p1,p2,p3,p4,p5,p6,p7;

  //select dispatcher('syncsend,   EURUSD,20040,20050,12345,EURUSD,0.69,BUY,2025-07-04 17:59:56,1.39001, 777777,0.00005,0.000005,2.25');
  //select dispatcher('syncreceive,EURUSD,20050, 2025-07-04 20:59:56');



  bool disp = 1;//dispatch("tendencia",insimbol,p1,p2,p3,p4,p5,p6,p7);
//Exito,GBPAUD,sell,1.89365,1.89,2024-05-09 00:00:00,2024-05-10 23:59:59
   if(!disp)
      return false;



   if(p2 == "buy")
      intipo = OP_BUY;
   if(p2 == "sell")
      intipo = OP_SELL;

   if((intipo != OP_BUY) && (intipo != OP_SELL))
      return false;

   insl = StringToDouble(p3);
   intp = StringToDouble(p4);
   inbase = StringToDouble(p5);

   p6= limpiar_fecha(p6);
   p7= limpiar_fecha(p7);

   infechai = StrToTime(p6);
   infechaf = StrToTime(p7);


   return true;
  }
//------------------------------------------------------------------------------
//------------------------------------------------------------------------------

double calcula_SL (int tipoopin,string modelo_SL_in, double SLin, double precioSL, double tem_lotes_in)
{
      //zero, prop, eq, mult,prom
      double respuesta = 0;
      if (modelo_SL_in == "zero")
      {
            double temp_dif = VariacionPrecioNecesaria(Symbol(), AccountEquity(), max_perdida_cuenta, tem_lotes_in);
            respuesta = temp_dif;
            return respuesta;
      }
      if (modelo_SL_in == "prop")
      {
         return SLin;
      }
      if (modelo_SL_in == "mult")
      {
         return (factor_tpsl*TakeProfit*PointVal);
      }
      if (modelo_SL_in == "prom")
      {
          respuesta =  (int)GET_TP_ATR();
          return respuesta;
      }
      if (modelo_SL_in == "eq")
      {
         if (tipoopin == OP_BUY)
         {
            respuesta = MathAbs(( Ask - precioSL ));
         }
         if (tipoopin == OP_SELL)
         {
            respuesta = MathAbs((  Bid - precioSL ));
         }
      }
      return respuesta;
}
//****************************************************************************************
//****************************************************************************************
double VariacionPrecioNecesaria(string symbol, double balanceUSD, double percent, double lots)
{
   // Dinero que quiero ganar o perder
   double objetivoUSD = balanceUSD * percent ;

   // Valor de un tick en USD para el símbolo
   double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
   double tickSize  = MarketInfo(symbol, MODE_TICKSIZE);

   if(tickValue <= 0 || tickSize <= 0) return 0; // Evitar errores

   // Variación de precio necesaria
   double variacionPrecio = objetivoUSD / ( (tickValue / tickSize) * lots );

   return variacionPrecio;
}
//**************************
//**************************
double AjustarVolumenAlPaso(double volumen) 
{

  //vlotes = AjustarVolumenAlPaso(vlotes); 
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
   double minLot = MarketInfo(Symbol(), MODE_MINLOT);

   double ajustado = MathCeil(volumen / lotStep) * lotStep;
   if (ajustado < minLot) ajustado = minLot;

   int decimales = (lotStep == 0.1) ? 1 : (lotStep == 0.01) ? 2 : 3;
   return NormalizeDouble(ajustado, decimales);
}

//***************************************
//***************************************
bool validacion_estabilidad(int tipoin,double gap_ult_fractal_in,int quiebre_fractal_in,int quiebres_seguidos_in,datetime fechadesde, int num_puntos)
{

   bool respuesta = true;
   int barrafinal = iBarShift(Symbol(), 0, fechadesde, false);
   int tipo_tope = -1;
   
   if ( tipoin == OP_BUY)
   {
         tipo_tope = 1;  // 0 = UP   Se debe buscar al menos 2 puntos 
   }
   if ( tipoin == OP_SELL)
   {
          tipo_tope = 0;  // 1 = DOWN
   }


   double dif = 0;
   bool primero = true;
   int count = 0;
   for(int i = 1; i<barrafinal; i++)
   {
         double tmp_point =    iCustom(Symbol(),Period(),"Neo_MMF",Period(),gap_ult_fractal,quiebre_fractal,quiebres_seguidos,0,tipo_tope,i);
         

         
         int j = 0;
         if(tmp_point != 0)
         {
               count ++;
         }

   }
   
   if (count >= num_puntos)
   {
               respuesta = false;
   }
        
   return respuesta;
  }
  
  //***************************************
//***************************************
bool validacion_resbaladera(int tipoin, string simbolo,int periodoin,double gap_ult_fractal_in,int quiebre_fractal_in,int quiebres_seguidos_in,double gap_max_fractal_in, double & pr1, double & pr2)
  {

/*
   int tipoin; 
   string simbolo;
   int periodoin;
   double  gap_ult_fractal_in;
   int quiebre_fractal_in;
   int quiebres_seguidos_in;
   double gap_max_fractal_in; 
   double  pr1;
   double  pr2;
   bool validacion_resbaladera(tipoin,simbolo,periodoin,gap_ult_fractal_in,quiebre_fractal_in,quiebres_seguidos_in,gap_max_fractal_in,pr1,pr2);

*/


   bool respuesta = false;
   double precio_origen = 0;
   double precio_actual = 0;
   double dif = 0;
   int tipo_tope = -1;
   RefreshRates();
   datetime fecha_origen = 0;
   pr2 = 0;
   pr1 = 0;
   
   datetime fechadesde = FormatDateZero(TimeCurrent());
   int barrafinal = iBarShift(Symbol(), 0, fechadesde, false);
   if ( tipoin == OP_BUY)
   {
         tipo_tope = 1;  // 0 = UP   Se debe buscar al menos 2 puntos 
         precio_actual = Ask;
   }
   if ( tipoin == OP_SELL)
   {
          tipo_tope = 0;  // 1 = DOWN
          precio_actual = Bid;
   }

   bool find = false;
   //************************************
   double tmp_up = 0;
   int barra = 0;
   for(int i = 1; i<barrafinal; i++)
   {
         tmp_up =    iCustom(simbolo,periodoin,"Neo_MMF",periodoin,gap_ult_fractal_in,quiebre_fractal_in,quiebres_seguidos_in,0,tipo_tope,i);
         if (tmp_up > 0)
         {
               find = true;
               precio_origen =   iClose(simbolo, periodoin, i); // Precio de cierre del Timeframe , 0 Current, periodos atras
               break;
         }
   }
   if (!find)
      return respuesta; 

 
   
   dif = MathAbs(precio_origen-precio_actual);
   double max_dif = gap_max_fractal_in * PointVal;
   
   if ( ( tipoin == OP_BUY) &&  (Ask < precio_origen) && (max_dif <= dif)  )
   {
                  respuesta = true;
                  pr1 = precio_origen;
                  pr2 = precio_actual;
   }
   if ( ( tipoin == OP_SELL) &&  (Bid >precio_origen ) &&  (max_dif <= dif) )
   {
                  respuesta = true;
                  pr1 = precio_origen;
                  pr2 = precio_actual;
   }
  


   return respuesta;
}

//+------------------------------------------------------------------+
//| SafeStringSplit3: Divide hasta en 3 partes                       |
//| Retorna la cantidad de partes encontradas                        |
//+------------------------------------------------------------------+
int SafeStringSplit3(string inputin, string delimiter,
                     string &resp1,string &resp2 ,string &resp3, string &resp4)
  {
   resp1 = "";
   resp3 = "";
   resp2 = "";
   resp4 = "";
   
   int count = 0;
   int start = 0;
   int pos;

   // Primera búsqueda
   pos = StringFind(inputin, delimiter, start);
   if(pos == -1)
   {
      resp1 = inputin;
      return 1;
   }

   
   resp1 = StringSubstr(inputin, start, pos-start);
   count = 1;
   start = pos +1 ;

   // Segunda búsqueda
   pos = StringFind(inputin, delimiter, start);
   if(pos == -1)
   {
      resp1 = inputin;
      return 2;
   }
   resp2 = StringSubstr(inputin, start, pos-start);
   count = 2;
   start = pos + 1;
   // tercera
   
   pos = StringFind(inputin, delimiter, start);
   if(pos == -1)
   {
      resp1 = inputin;
      return 2;
   }   
   resp3 = StringSubstr(inputin, start, pos-start);
   count = 3;
   
   start = pos + 1;   // cuarta (resto de la cadena)
   pos = StringLen(inputin);
   
   resp4 = StringSubstr(inputin, start,pos-start);
   return 3;
  }