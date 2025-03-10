
densidad_pulpa = 1290

ge = 2.7

tonelaje = 550

dimensiones_tanques = {
    1: (24, 24), 2: (24, 24), 3: (24, 24), 4: (24, 24), 5: (28, 28),
    6: (28, 28), 7: (28, 28), 8: (28, 28), 9: (28, 28), 10: (24, 24), 11: (24, 24)
}  # (Diámetro, Altura) de cada tanque

capacidad = 100 # no importa mucho la verdad
capacidad_tanques = {i: capacidad for i in range(1, 12)}


minutos = 5
intervalo = 5
tiempo_total = 9999
root_mineral = 'version1.0/database/mineral.xlsx'
root_blending = 'version1.0/database/blendings.xlsx'
root_recuperacion = 'version1.0/database/recuperacion.xlsx'
root_fecha = 'version1.0/database/fecha_blending.xlsx'
root_cosecha = 'version1.0/database/cosechas.xlsx'