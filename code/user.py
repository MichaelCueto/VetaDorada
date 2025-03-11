from parametros import *
from data import integracion_data
from sim_tanques import Tanques
from cosecha_tanques import Cosecha 
from trazabilidad import Trazabilidad
from scipy.optimize import minimize_scalar
import pandas as pd
import numpy as np
from itertools import combinations
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# **Carga de Datos**
df_materiales = integracion_data(root_mineral, root_blending, root_recuperacion, root_fecha, minutos).mill_to_lix(deltatime=45)
df_info_blendings = integracion_data(root_mineral, root_blending, root_recuperacion, root_fecha, minutos).info_blending(rec_estandar=0.90)
# **Simulación de los Tanques**
df_tanques = Tanques(df_materiales, capacidad_tanques, dimensiones_tanques, tonelaje, densidad_pulpa, ge, intervalo, tiempo_total).simular_tanques()
df_cosechas = pd.read_excel(root_cosecha)
betas = [0.35, 0.55, 0.50, 0.75, 0.75, 0.45, 0.45, 0.45, 0.40, 0.10, 0.15]
df_cosechas["fecha_cosecha"] = pd.to_datetime(df_cosechas["fecha_cosecha"], format="%d/%m/%y %H:%M")
ultima_fecha_general = df_cosechas["fecha_cosecha"].min()
ultima_fecha_cosecha = {}
fecha_cosecha_anterior = []
for _, row in df_cosechas.iterrows():
    tanque = row["tanque_cosechado"]
    if tanque in ultima_fecha_cosecha:
        fecha_cosecha_anterior.append(ultima_fecha_cosecha[tanque])
    else:
        fecha_cosecha_anterior.append(ultima_fecha_general)  # Si es la primera, se usa la fecha mínima general
    ultima_fecha_cosecha[tanque] = row["fecha_cosecha"]
df_parametros = df_cosechas.copy()
df_parametros["fecha_cosecha_anterior"] = fecha_cosecha_anterior
df_parametros = df_parametros[["id_campaña", "fecha_cosecha_anterior", "fecha_cosecha", "tanque_cosechado", "cm_au_real"]]
df_parametros.rename(columns={"fecha_cosecha": "fecha_cosecha_actual"}, inplace=True)

class SimulacionTrazabilidad:
    def __init__(self, df_cosechas, df_tanques, df_info_blendings, betas):
        self.df_cosechas = df_cosechas
        self.df_tanques = df_tanques
        self.df_info_blendings = df_info_blendings
        self.betas = betas
    
    def ajustar_oro_generalizado(self, df_tanques, betas):
        n_tanques = len(df_tanques)
        df_resultados = []

        for i in range(n_tanques):
            dfn = df_tanques[i].copy()
            id_mineral_sets = [set(df_tanques[j]["id_mineral"]) for j in range(i)]
            dfn["cm_au"] = dfn["tonelaje"] * dfn["ley_au"] * dfn["rec_au"]
            ajuste = np.prod([(1 - betas[j]) for j in range(i)]) if i > 0 else 1
            dfn["cm_au"] = dfn.apply(
                lambda row: row["cm_au"] * ajuste * betas[i] if any(row["id_mineral"] in id_set for id_set in id_mineral_sets)
                else row["cm_au"] * betas[i],
                axis=1
            )
            df_resultados.append(dfn)

        return df_resultados

    def ejecutar_simulacion(self, df_parametros=None, output_path="trazabilidad_resultados.xlsx", all=True,
                            id_campana=None, fecha_cosecha_anterior=None, fecha_cosecha_actual=None, 
                            tanque_cosechado=None, cm_au_real=None):
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            if all:
                data_iterable = df_parametros.iterrows()
            else:
                data_iterable = [(None, {"id_campaña": id_campana.replace("*", "_"),
                                         "fecha_cosecha_anterior": fecha_cosecha_anterior,
                                         "fecha_cosecha_actual": fecha_cosecha_actual,
                                         "tanque_cosechado": tanque_cosechado,
                                         "cm_au_real": cm_au_real})]

            for _, row in data_iterable:
                id_campana = row["id_campaña"].replace("*", "_")
                fecha_cosecha_anterior = row["fecha_cosecha_anterior"]
                fecha_cosecha_actual = row["fecha_cosecha_actual"]
                num_tanque = row["tanque_cosechado"]
                cm_au_real = row["cm_au_real"]

                df_cosecha_tanques = [
                    Cosecha(self.df_tanques[i], fecha_cosecha_anterior, fecha_cosecha_actual).resumen_blending()
                    for i in range(len(self.df_tanques))
                ]

                df_carbon_tanques = [
                    Trazabilidad(self.df_info_blendings, df_cosecha_tanques[i], alfa=0.10).participacion()
                    for i in range(len(self.df_tanques))
                ]

                df_au_carbon_tanques = self.ajustar_oro_generalizado(df_carbon_tanques, self.betas)
                df_au_carbon_tanques = df_au_carbon_tanques[num_tanque-1]

                df_participacion = df_au_carbon_tanques.copy()
                df_participacion["%participacion"] = (df_participacion["cm_au"] / (df_participacion["cm_au"].sum(skipna=True))) * 100
                df_participacion = df_participacion.groupby("nombre_del_minero")["%participacion"].sum().reset_index()
                df_participacion = df_participacion[["nombre_del_minero", "%participacion"]].sort_values(by=["%participacion"], ascending=False)

                df_trazabilidad = df_au_carbon_tanques.copy()
                df_trazabilidad = df_trazabilidad[["id_blending", "id_mineral", "cm_au"]]
                df_trazabilidad["cm_au"] = df_trazabilidad["cm_au"] * (cm_au_real / df_trazabilidad["cm_au"].sum())
                df_trazabilidad = df_trazabilidad.sort_values(by=['id_blending', 'cm_au'], ascending=[True, False])

                df_participacion.to_excel(writer, sheet_name=f"{id_campana}_participacion", index=False)
                df_trazabilidad.to_excel(writer, sheet_name=f"{id_campana}_trazabilidad", index=False)

        print(f"Archivo generado: {output_path}")

SimulacionTrazabilidad(df_cosechas=df_cosechas, df_tanques=df_tanques,
                         df_info_blendings=df_info_blendings, betas=betas).ejecutar_simulacion(df_parametros=df_parametros, 
                         output_path="trazabilidad_resultados.xlsx",all=True,id_campana=None, fecha_cosecha_anterior=None,
                         fecha_cosecha_actual=None, tanque_cosechado=None, cm_au_real=None)