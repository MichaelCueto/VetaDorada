import pandas as pd
import numpy as np

class Cosecha:
    def __init__(self, df, fecha_cosecha_anterior, fecha_cosecha_actual):
        self.fecha_cosecha_anterior = pd.to_datetime(fecha_cosecha_anterior)
        self.fecha_cosecha_actual = pd.to_datetime(fecha_cosecha_actual)
        self.df = df
    
    def extraccion(self):
        mask_interval = (self.df["time"] >= self.fecha_cosecha_anterior) & (self.df["time"] <= self.fecha_cosecha_actual)
        df_interval = self.df.loc[mask_interval].copy()
        df_sin_time = df_interval.drop(columns=["time"])
        filas_vacias = df_sin_time.isna().all(axis=1)
        indices_vacios = filas_vacias[filas_vacias].index.tolist()  # Convertir a lista de índices
        indices_validos = [idx - 1 for idx in indices_vacios if idx - 1 in self.df.index]
        
        if indices_validos:  # Si hay índices válidos
            filas_anteriores = self.df.loc[indices_validos]
            filas_anteriores = filas_anteriores[filas_anteriores["time"] < self.fecha_cosecha_actual]
        else:
            filas_anteriores = pd.DataFrame()

        fecha_especifica = self.fecha_cosecha_actual
        fecha_menor = self.df[self.df["time"] <= fecha_especifica].iloc[-1] if not self.df[self.df["time"] <= fecha_especifica].empty else None
        fecha_mayor = self.df[self.df["time"] > fecha_especifica].iloc[0] if not self.df[self.df["time"] > fecha_especifica].empty else None
        
        if fecha_menor is not None and fecha_mayor is not None:
            distancia_menor = abs(fecha_menor["time"] - fecha_especifica)
            distancia_mayor = abs(fecha_mayor["time"] - fecha_especifica)
            
            if fecha_menor.drop("time").isna().all():
                fila_cercana = fecha_mayor.to_frame().T  # Si la fecha menor es NaN, tomar la mayor
            elif distancia_menor < distancia_mayor:
                fila_cercana = fecha_menor.to_frame().T
            elif distancia_mayor < distancia_menor:
                fila_cercana = fecha_mayor.to_frame().T
            else:
                fila_cercana = fecha_menor.to_frame().T  # Si están a la misma distancia, tomar la menor
        elif fecha_menor is not None:
            fila_cercana = fecha_menor.to_frame().T
        elif fecha_mayor is not None:
            fila_cercana = fecha_mayor.to_frame().T
        else:
            fila_cercana = pd.DataFrame()  # Si no hay fechas disponible
        df_resultado = pd.concat([filas_anteriores, fila_cercana])
        return df_resultado
    
    def resumen_blending(self):
        df_resultado = self.extraccion().sort_values(by="time", ascending=True).reset_index(drop=True)
        df_resultado = df_resultado.drop(columns=["time"])
        df_transpuesto = df_resultado.T
        df_transpuesto = df_transpuesto.dropna(how='all')
        df_transpuesto["tonelaje"] = df_transpuesto.sum(axis=1)
        df_transpuesto = df_transpuesto.reset_index().rename(columns={"index": "id_blending"})
        df_transpuesto = df_transpuesto[["id_blending","tonelaje"]]
        return df_transpuesto
