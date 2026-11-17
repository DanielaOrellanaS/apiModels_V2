from registry import Registry

reg = Registry()
for s in ["NAS100", "GER40", "US30", "BTCUSD"]:
    a = reg.activo(s)
    print(s, "->", a["lados_aprobados"] if a else "sin activar")
