
import pandas as pd
import numpy as np

class integracion_data:
    def __init__(self, root_mineral, root_blending, root_recuperacion, root_fecha, minutos):
        self.root_mineral = root_mineral
        self.root_blending = root_blending
        self.root_recuperacion = root_recuperacion
        self.root_fecha = root_fecha
        self.minutos = minutos #usamos minutos = 5
    
    def mineral(self):
        df_mineral = pd.read_excel(self.root_mineral)
        df_mineral["id_mineral"] = df_mineral["id_mineral"].astype(str)
        return df_mineral

    def blending(self):
        df_blending = pd.read_excel(self.root_blending)
        df_blending["id_blending"] = df_blending["id_blending"].astype(str)
        df_blending["id_mineral"] = df_blending["id_mineral"].astype(str)
        return df_blending

    def recuperacion(self):
        df_recuperacion = pd.read_excel(self.root_recuperacion)
        df_recuperacion["id_mineral"] = df_recuperacion["id_mineral"].astype(str).str.zfill(4)
        df_recuperacion["rec_au"] = df_recuperacion["rec_au"].replace("#DIV/0!", 0.90).astype(float)
        df_recuperacion["rec_ag"] = df_recuperacion["rec_ag"].replace("#DIV/0!", 0.90).astype(float)
        df_recuperacion["rec_ag"] = df_recuperacion["rec_ag"].fillna(0.90).astype(float)
        df_recuperacion["rec_au"] = df_recuperacion["rec_au"].fillna(0.90).astype(float)
        return df_recuperacion
    
    def fecha(self):
        df_fecha = pd.read_excel(self.root_fecha)
        df_fecha["fecha_ingreso_planta"] = pd.to_datetime(df_fecha["fecha_ingreso_planta"], format="%d-%m-%Y %H:%M:%S")
        df_fecha["id_blending"] = df_fecha["id_blending"].astype(str)
        return df_fecha

    def info_blending(self,rec_estandar):
        db1 = pd.merge(self.mineral(),self.blending(),left_on="id_mineral",right_on="id_mineral",how="left")
        db2 = pd.merge(db1,self.recuperacion(),left_on="id_mineral",right_on="id_mineral",how="left")
        db2["rec_au"] = db2["rec_au"].fillna(rec_estandar)
        db2["rec_ag"] = db2["rec_ag"].fillna(rec_estandar)
        return db2

    def integracion(self):
        db3 = self.info_blending(rec_estandar=0.90).groupby("id_blending")["tonelaje"].sum().reset_index()
        df_fecha = self.fecha().sort_values(by="fecha_ingreso_planta").reset_index(drop=True)
        df_fecha_2 = df_fecha.groupby("id_blending").agg(
            hora_inicio=("fecha_ingreso_planta", "first"),  # Primer registro de cada blending
            tonelaje_total=("tonelaje", "sum")              # Sumar tonelaje de cada blending
            ).reset_index()
        db4 = pd.merge(df_fecha_2,db3,left_on="id_blending",right_on="id_blending",how="left")
        db4 = db4.sort_values(by="hora_inicio").reset_index(drop=True)
        db4["hora_final"] = db4["hora_inicio"].shift(-1)
        db4.loc[db4.index[-1], "hora_final"] = df_fecha["fecha_ingreso_planta"].max()
        db5 = db4.copy()
        delta_t = (db5["hora_final"] - db5["hora_inicio"]).dt.total_seconds()
        db5["ton_5min"] = np.where(delta_t == 0, None, db5["tonelaje"] / (delta_t / (60*self.minutos)))
        return db5
    
    def mill_to_lix(self,deltatime):
        db6 = []
        for _, row in self.integracion().iterrows():
            hora_actual = row["hora_inicio"]
            while hora_actual < row["hora_final"]:
                hora_siguiente = hora_actual + pd.Timedelta(minutes=self.minutos)

                if hora_siguiente > row["hora_final"]:
                    break
                
                db6.append({
                    "id_blending": row["id_blending"],
                    "hora_inicio": hora_actual,
                    "hora_final": hora_siguiente,
                    "ton_5min": row["ton_5min"] 
                })
                hora_actual = hora_siguiente
        db6 = pd.DataFrame(db6)
        db7 = db6.copy()
        db7["hora_salida_molino"] = db7["hora_final"] + pd.Timedelta(minutes=deltatime)
        db7 = db7.drop(columns=["hora_final","hora_inicio"])
        return db7






