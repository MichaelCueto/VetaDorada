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

class Reconciliacion:
    def __init__(self, df_cosechas, df_tanques):
        self.df_cosechas = df_cosechas
        self.df_tanques = df_tanques

    def aplicar_transferencia_cosechas(self):
        df_cosechas = self.df_cosechas
        df_tanques = self.df_tanques

        df_cosechas["fecha_cosecha"] = pd.to_datetime(df_cosechas["fecha_cosecha"], format="%m/%d/%y %H:%M")
        df_cosechas = df_cosechas.sort_values(by="fecha_cosecha").reset_index(drop=True)
        cosechas_por_tanque = {}

        # Llenar el diccionario con la lista de cosechas de cada tanque
        for index, row in df_cosechas.iterrows():
        tanque = row["tanque_cosechado"]
        if tanque not in cosechas_por_tanque:
            cosechas_por_tanque[tanque] = []
        cosechas_por_tanque[tanque].append(index)

        # **Aplicar transferencias**
        for index, row in df_cosechas.iterrows():
        tanque_cosechado = row["tanque_cosechado"]
        tanque_aportador = row["tanque_aportador"]

            # Si no hay tanque aportador, no hay transferencia
            if pd.isna(tanque_aportador):
                continue

            # Buscar la siguiente cosecha del tanque cosechado
            cosechas_tanque = cosechas_por_tanque.get(tanque_cosechado, [])
            siguiente_cosecha_idx = next((idx for idx in cosechas_tanque if idx > index), None)

            if siguiente_cosecha_idx is not None:
                # Obtener el DataFrame correspondiente al tanque aportador y cosechado
                df_aportador = df_tanques[int(tanque_aportador) - 1]
                df_cosechado = df_tanques[int(tanque_cosechado) - 1]

                # Obtener la fecha de la siguiente cosecha
                fecha_siguiente_cosecha = df_cosechas.loc[siguiente_cosecha_idx, "fecha_cosecha"]

                # Sumar los valores de los ID de Blendings del tanque aportador al tanque cosechado en la siguiente cosecha
                for col in df_aportador.columns:
                    if col != "time" and col in df_cosechado.columns:
                        df_cosechado.loc[df_cosechado["time"] == fecha_siguiente_cosecha, col] += df_aportador.loc[df_aportador["time"] == row["fecha_cosecha"], col].values[0]
                    elif col != "time":  # Si la columna no existe en el tanque cosechado, crearla
                        df_cosechado[col] = 0
                        df_cosechado.loc[df_cosechado["time"] == fecha_siguiente_cosecha, col] = df_aportador.loc[df_aportador["time"] == row["fecha_cosecha"], col].values[0]
        return df_tanques

#df_tanques_actualizado = aplicar_transferencias_cosechas(df_cosechas, df_tanques)
    
    def ajustar_oro_general(self):
        df_tanques = self.aplicar_transferencias_cosechas()
        n_tanques = len(df_tanques)
        df_resultados = []
        betas = [0.35, 0.85, 0.50, 0.75, 0.75, 0.45, 0.45, 0.45, 0.40, 0.10, 0.15]
        for i in range(n_tanques):
            dfn = df_tanques[i]
            id_mineral_sets = [set(df_tanques[j]["id_mineral"]) for j in range(i)]  # Conjuntos de id_mineral previos
            dfn["cm_au"] = dfn["tonelaje"] * dfn["ley_au"] * dfn["rec_au"]
            ajuste = np.prod([(1 - betas[j]) for j in range(i)]) if i > 0 else 1
            # Aplicar reglas de ajuste de cm_au
            dfn["cm_au"] = dfn.apply(
                lambda row: row["cm_au"] * ajuste * betas[i] if any(row["id_mineral"] in id_set for id_set in id_mineral_sets)
                else row["cm_au"] * betas[i],
                axis=1
            )
            df_resultados.append(dfn)

        return df_resultados



fecha_cosecha_anterior = "2025-01-05 10:00:00"
fecha_cosecha_actual = "2025-01-10 10:00:00"
num_tanque = 1
cm_au_real = 636.09
    def resultados(self):
        df_cosecha_tanques = [
            Cosecha(df_tanques_actualizado[i], fecha_cosecha_anterior, fecha_cosecha_actual).resumen_blending()
            for i in range(len(df_tanques))
        ]
        df_carbon_tanques = [
            Trazabilidad(df_info_blendings, df_cosecha_tanques[i], alfa=0.10).participacion()
            for i in range(len(df_tanques))
        ]
        df_au_carbon_tanques = ajustar_oro_generalizado(df_carbon_tanques, betas)
        df_au_carbon_tanques = df_au_carbon_tanques[num_tanque-1]


df_participacion = df_au_carbon_tanques.copy()
df_participacion["%participacion"] = (df_participacion["cm_au"]/(df_participacion["cm_au"].sum(skipna=True)))*100
df_participacion = df_participacion.groupby("nombre_del_minero")["%participacion"].sum().reset_index()
df_participacion = df_participacion[["nombre_del_minero","%participacion"]].sort_values(by=["%participacion"], ascending=False)

df_trazabilidad = df_au_carbon_tanques.copy()
df_trazabilidad = df_trazabilidad[["id_blending","id_mineral","cm_au"]]
#df_trazabilidad["cm_au"] = df_trazabilidad["cm_au"]*(cm_au_real/df_trazabilidad["cm_au"].sum())
df_trazabilidad = df_trazabilidad.sort_values(by=['id_blending', 'cm_au'], ascending=[True, False])

output_path = f"trazabilidad_tanque{num_tanque}.xlsx"
with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
    df_participacion.to_excel(writer, sheet_name="participacion", index=False)
    df_trazabilidad.to_excel(writer, sheet_name="trazabilidad", index=False)

print(df_trazabilidad["cm_au"].sum())