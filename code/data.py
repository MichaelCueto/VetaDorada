import pandas as pd
import numpy as np
from sqlalchemy import create_engine

class integracion_data:
    def __init__(self, mineral, blendings, recuperaciones, fechas_blending, minutos):
        self.root_mineral = mineral
        self.root_blending = blendings
        self.root_recuperacion = recuperaciones
        self.root_fecha = fechas_blending
        self.minutos = minutos

    def _leer(self, source, parse_date_cols=None):
        if isinstance(source, pd.DataFrame):
            df = source.copy()
        else:
            df = pd.read_excel(source)

        if parse_date_cols:
            for col in parse_date_cols:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def mineral(self):
        df = self._leer(self.root_mineral)
        df["id_mineral"] = df["id_mineral"].astype(str)
        return df

    def blending(self):
        df = self._leer(self.root_blending)
        df["id_blending"] = df["id_blending"].astype(str)
        df["id_mineral"] = df["id_mineral"].astype(str)
        return df

    def recuperacion(self):
        df = self._leer(self.root_recuperacion)
        df["id_mineral"] = df["id_mineral"].astype(str).str.zfill(4)
        df["rec_au"] = df["rec_au"].replace("#DIV/0!", 0.90).astype(float).fillna(0.90)
        df["rec_ag"] = df["rec_ag"].replace("#DIV/0!", 0.90).astype(float).fillna(0.90)
        return df

    def fecha(self):
        df = self._leer(self.root_fecha, parse_date_cols=["fecha_ingreso_planta"])
        df["id_blending"] = df["id_blending"].astype(str)
        return df

    def info_blending(self, rec_estandar=0.90):
        db1 = pd.merge(self.mineral(), self.blending(), on="id_mineral", how="left")
        db2 = pd.merge(db1, self.recuperacion(), on="id_mineral", how="left")
        db2["rec_au"] = db2["rec_au"].fillna(rec_estandar)
        db2["rec_ag"] = db2["rec_ag"].fillna(rec_estandar)
        return db2

    def integracion(self):
        db3 = self.info_blending().groupby("id_blending")["tonelaje"].sum().reset_index()
        df_fecha = self.fecha().sort_values(by="fecha_ingreso_planta").reset_index(drop=True)

        df_fecha_2 = df_fecha.groupby("id_blending").agg(
            hora_inicio=("fecha_ingreso_planta", "first"),
            tonelaje_total=("tonelaje", "sum")
        ).reset_index()

        db4 = pd.merge(df_fecha_2, db3, on="id_blending", how="left").sort_values(by="hora_inicio").reset_index(drop=True)
        db4["hora_final"] = db4["hora_inicio"].shift(-1)
        db4.loc[db4.index[-1], "hora_final"] = df_fecha["fecha_ingreso_planta"].max()

        delta_t = (db4["hora_final"] - db4["hora_inicio"]).dt.total_seconds()
        db4["ton_5min"] = np.where(delta_t == 0, None, db4["tonelaje"] / (delta_t / (60 * self.minutos)))
        return db4

    def mill_to_lix(self, deltatime):
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
        db6["hora_salida_molino"] = db6["hora_final"] + pd.Timedelta(minutes=deltatime)
        return db6.drop(columns=["hora_final", "hora_inicio"])
    
def cargar_data_mysql(uri):
    engine = create_engine(uri)

    df_mineral = pd.read_sql("SELECT * FROM mineral", engine)
    df_blending = pd.read_sql("SELECT * FROM blending", engine)
    df_recuperacion = pd.read_sql("SELECT * FROM recuperacion", engine)
    df_fecha_blending = pd.read_sql("SELECT * FROM fecha_blending", engine)
    df_cosechas = pd.read_sql("SELECT * FROM cosechas", engine)

    return df_mineral, df_blending, df_recuperacion, df_fecha_blending, df_cosechas