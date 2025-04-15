import pandas as pd
import numpy as np
from parametros import *
from sim_tanques import Tanques
from cosecha_tanques import Cosecha 
from trazabilidad import Trazabilidad
from datetime import datetime
from data import cargar_data_mysql, integracion_data  # agrega cargar_data_mysql
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class TrazabilidadSimulador:
    def __init__(self, paths=None, db_uri=None, densidad=None, ge=None, tonelaje=None, a=0.20, betas=None,
                 df_materiales=None, df_info_blendings=None, df_tanques=None, df_cosechas=None, df_parametros=None):

        self.paths = paths
        self.db_uri = db_uri
        self.densidad = densidad or densidad_pulpa
        self.ge = ge or ge_default
        self.tonelaje = tonelaje or tonelaje_default
        self.a = a
        self.betas = betas or [0.35, 0.55, 0.50, 0.75, 0.75, 0.45, 0.45, 0.45, 0.40, 0.10, 0.15]

        self.df_materiales = df_materiales
        self.df_info_blendings = df_info_blendings
        self.df_tanques = df_tanques
        self.df_cosechas = df_cosechas
        self.df_parametros = df_parametros

        if self.df_materiales is None or self.df_info_blendings is None or self.df_tanques is None or self.df_cosechas is None:
            self._preparar_datos()
        if self.df_parametros is None:
            self.df_parametros = self._calcular_parametros(self.df_cosechas)

    def _preparar_datos(self):
        if self.paths:
            print("📂 Cargando datos desde archivos...")
            # código actual con integracion_data desde paths
            self.df_materiales = integracion_data(
                self.paths["minerales"], 
                self.paths["blending"],
                self.paths["recuperacion"],
                root_fecha,
                minutos
            ).mill_to_lix(deltatime=45)

            self.df_tanques = Tanques(
                self.df_materiales,
                capacidad_tanques,
                dimensiones_tanques,
                self.tonelaje,
                self.densidad,
                self.ge,
                intervalo,
                tiempo_total
            ).simular_tanques()

            self.df_info_blendings = integracion_data(
                self.paths["minerales"], 
                self.paths["blending"],
                self.paths["recuperacion"],
                root_fecha,
                minutos
            ).info_blending(rec_estandar=0.90)

            self.df_cosechas = pd.read_excel(self.paths["cosechas"])
            self.df_cosechas["fecha_cosecha"] = pd.to_datetime(self.df_cosechas["fecha_cosecha"], format="%d/%m/%y %H:%M")

        elif self.db_uri:
            print("🔌 Cargando datos desde MySQL...")
            df_mineral, df_blending, df_recuperacion, df_fecha_blending, df_cosechas = cargar_data_mysql(self.db_uri)
            
            self.df_materiales = integracion_data(
                df_mineral,
                df_blending,
                df_recuperacion,
                df_fecha_blending,
                minutos
            ).mill_to_lix(deltatime=45)
            print(self.df_materiales, "df_materiales")

            self.df_tanques = Tanques(
                self.df_materiales,
                capacidad_tanques,
                dimensiones_tanques,
                self.tonelaje,
                self.densidad,
                self.ge,
                intervalo,
                tiempo_total
            ).simular_tanques()

            self.df_info_blendings = integracion_data(
                df_mineral,
                df_blending,
                df_recuperacion,
                root_fecha,
                minutos
            ).info_blending(rec_estandar=0.90)
            
            df_cosechas["fecha_cosecha"] = pd.to_datetime(df_cosechas["fecha_cosecha"])
            self.df_cosechas = df_cosechas
        
        else:
            raise ValueError("⚠️ No se proporcionaron ni paths ni conexión a base de datos.")

        self.df_parametros = self._calcular_parametros(self.df_cosechas)

    def _calcular_parametros(self, df_cosechas):
        ultima_fecha_general = df_cosechas["fecha_cosecha"].min()
        ultima_fecha_cosecha = {}
        fecha_cosecha_anterior = []

        for _, row in df_cosechas.iterrows():
            tanque = row["tanque_cosechado"]
            if tanque in ultima_fecha_cosecha:
                fecha_cosecha_anterior.append(ultima_fecha_cosecha[tanque])
            else:
                fecha_cosecha_anterior.append(ultima_fecha_general)
            ultima_fecha_cosecha[tanque] = row["fecha_cosecha"]

        df_param = df_cosechas.copy()
        df_param["fecha_cosecha_anterior"] = fecha_cosecha_anterior
        df_param = df_param[["id_campania", "fecha_cosecha_anterior", "fecha_cosecha", "tanque_cosechado", "cm_au_real"]]
        df_param.rename(columns={"fecha_cosecha": "fecha_cosecha_actual"}, inplace=True)
        return df_param

    def ajustar_oro_generalizado(self, df_tanques, betas):
        n_tanques = len(df_tanques)
        df_resultados = []
        #print(df_tanques, "calculando el contenido de los tanques")
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
        #print(df_resultados)

        return df_resultados

    def ejecutar(self, all=True, fila=None, output_path="trazabilidad_resultados.xlsx"):
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            if all:
                iter_data = self.df_parametros.iterrows()
            else:
                iter_data = [(None, fila)]

            df_au_carbon_tanques_anterior = None

            for _, row in iter_data:
                id_campana = row["id_campania"].replace("*", "_")
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
                df_au_carbon_tanques = df_au_carbon_tanques[int(num_tanque)-1]

                if "recuperado" in id_campana.lower() and df_au_carbon_tanques_anterior is not None:
                    df_au_carbon_tanques = df_au_carbon_tanques_anterior.copy(deep=True)
                    df_au_carbon_tanques["cm_au"] *= self.a

                df_participacion = df_au_carbon_tanques.copy()
                df_participacion["%participacion"] = (df_participacion["cm_au"] / df_participacion["cm_au"].sum()) * 100
                df_participacion = df_participacion.groupby("nombre_del_minero")["%participacion"].sum().reset_index()
                df_participacion = df_participacion.sort_values(by="%participacion", ascending=False)

                df_trazabilidad = df_au_carbon_tanques.copy()
                cm_au_total = df_trazabilidad["cm_au"].sum()
                if cm_au_total > 0:
                    df_trazabilidad["cm_au"] *= (cm_au_real / cm_au_total)
                else:
                    df_trazabilidad["cm_au"] = 0 
                df_trazabilidad = df_trazabilidad[["id_blending", "id_mineral", "cm_au"]].sort_values(by=['id_blending', 'cm_au'], ascending=[True, False])

                df_participacion.to_excel(writer, sheet_name=f"{id_campana}_participacion", index=False)
                df_trazabilidad.to_excel(writer, sheet_name=f"{id_campana}_trazabilidad", index=False)

                df_au_carbon_tanques_anterior = df_au_carbon_tanques.copy(deep=True)
                
        print(f"✅ Archivo generado: {output_path}")