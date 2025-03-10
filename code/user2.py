from parametros import densidad_pulpa, ge, tonelaje, dimensiones_tanques, capacidad_tanques
from data import integracion_data
from sim_tanques import Tanques
from cosecha_tanques import Cosecha 
from trazabilidad import Trazabilidad
import pandas as pd
from itertools import combinations
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

minutos = 5
intervalo = 5
tiempo_total = 24*60*25
root_mineral = 'version1.0/database/mineral.xlsx'
root_blending = 'version1.0/database/blendings.xlsx'
root_recuperacion = 'version1.0/database/recuperacion.xlsx'
root_fecha = 'version1.0/database/fecha_blending.xlsx'


fecha_cosecha_anterior = "2025-01-02 06:00:00"
fecha_cosecha_actual = "2025-01-05 10:00:00"
beta1 = 0.5

df_materiales = integracion_data(root_mineral, root_blending, root_recuperacion, root_fecha, minutos).mill_to_lix(deltatime=45)
df_info_blendings = integracion_data(root_mineral, root_blending, root_recuperacion, root_fecha, minutos).info_blending(rec_estandar=0.90)
df_tk1, df_tk2, df_tk3, df_tk4, df_tk5, df_tk6, df_tk7, df_tk8, df_tk9, df_tk10, df_tk11 = Tanques(df_materiales, capacidad_tanques, dimensiones_tanques, tonelaje, densidad_pulpa, ge, intervalo, tiempo_total).simular_tanques()

#Para el tanque 1
df_cosecha_tk1 = Cosecha(df_tk1, fecha_cosecha_anterior, fecha_cosecha_actual).resumen_blending()
df_carbon_tk1 = Trazabilidad(df_info_blendings,df_cosecha_tk1,alfa=0.10).participacion()
df_au_carbon_tk1 = df_carbon_tk1.copy()
df_au_carbon_tk1["cm_au"] = df_au_carbon_tk1["rec_au"]*df_au_carbon_tk1["ley_au"]*df_au_carbon_tk1["tonelaje"]*beta1

def ajustar_oro_tk2(db1, db2,beta1,beta2):
    id_mineral_comun = set(db1["id_mineral"]).intersection(set(db2["id_mineral"]))
    db2["cm_au"] = db2["tonelaje"]*db2["ley_au"]*db2["rec_au"]
    db2["cm_au"] = db2.apply(
        lambda row: row["cm_au"] * (1-beta1)*(beta2) if row["id_mineral"] in id_mineral_comun else row["tonelaje"] * (beta2), 
        axis=1)
    return db2

#Para el tanque 2
df_cosecha_tk2 = Cosecha(df_tk2, fecha_cosecha_anterior, fecha_cosecha_actual).resumen_blending()
df_carbon_tk2 = Trazabilidad(df_info_blendings,df_cosecha_tk2,alfa=0.10).participacion()
df_au_carbon_tk2 = ajustar_oro_tk2(df_carbon_tk1, df_carbon_tk2, beta1, beta2=0.4)

def ajustar_oro_tk3(db1, db2, db3, beta1, beta2, beta3):
    id_mineral_db1 = set(db1["id_mineral"])
    id_mineral_db2 = set(db2["id_mineral"])
    db3["cm_au"] = db3["tonelaje"]*db3["ley_au"]*db3["rec_au"]
    db3["cm_au"] = db3.apply(
        lambda row: row["cm_au"] * (1 - beta1) * (1 - beta2) * beta3 if row["id_mineral"] in id_mineral_db1
        else (row["cm_au"] * (1 - beta2) * beta3 if row["id_mineral"] in id_mineral_db2
        else row["cm_au"] * beta3),
        axis=1
    )
    return db3

#Para el tanque 3
df_cosecha_tk3 = Cosecha(df_tk3, fecha_cosecha_anterior, fecha_cosecha_actual).resumen_blending()
df_carbon_tk3 = Trazabilidad(df_info_blendings,df_cosecha_tk3,alfa=0.10).participacion()
df_au_carbon_tk3 = ajustar_oro_tk3(df_carbon_tk1, df_carbon_tk2, df_carbon_tk3, beta1, beta2=0.4, beta3=0.4)

def ajustar_oro_tk4(db1, db2, db3, db4, beta1, beta2, beta3, beta4):
    id_mineral_db1 = set(db1["id_mineral"])
    id_mineral_db2 = set(db2["id_mineral"])
    id_mineral_db3 = set(db3["id_mineral"])
    db4["cm_au"] = db4["tonelaje"]*db4["ley_au"]*db4["rec_au"]
    db4["cm_au"] = db4.apply(
        lambda row: row["cm_au"] * (1 - beta1) * (1 - beta2) * (1 - beta3) * beta4 if row["id_mineral"] in id_mineral_db1
        else (row["cm_au"] * (1 - beta2) * (1- beta3) * beta4 if row["id_mineral"] in id_mineral_db2
        else (row["cm_au"] * (1 - beta3) * beta4  if row["id_mineral"] in id_mineral_db3
        else row["cam_au"] * beta4)),
        axis=1
    )
    return db4

#Para el tanque 4
df_cosecha_tk4 = Cosecha(df_tk4, fecha_cosecha_anterior, fecha_cosecha_actual).resumen_blending()
df_carbon_tk4 = Trazabilidad(df_info_blendings,df_cosecha_tk4,alfa=0.10).participacion()
df_au_carbon_tk4 = ajustar_oro_tk4(df_carbon_tk1, df_carbon_tk2, df_carbon_tk3, df_carbon_tk4, beta1, beta2=0.4, beta3=0.4, beta4=0.3)
print(df_au_carbon_tk4["cm_au"].sum())
