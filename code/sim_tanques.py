import pandas as pd
import math
from collections import defaultdict

class Tanques:
    def __init__(self, df_materiales, capacidad_tanques, dimensiones_tanques,
                 tonelaje, densidad_pulpa, ge, intervalo, tiempo_total):
        self.df_materiales = df_materiales
        self.capacidad_tanques = capacidad_tanques
        self.dimensiones_tanques = dimensiones_tanques
        self.tonelaje = tonelaje
        self.densidad_pulpa = densidad_pulpa
        self.ge = ge
        self.intervalo = intervalo
        self.tiempo_total = tiempo_total

    def simular_tanques(self):
        num_pasos = (24*60*self.tiempo_total) // self.intervalo
        num_tanques = len(self.capacidad_tanques)
        historial_tanques = defaultdict(list)

        # 🔹 Cálculo del volumen y tiempos de transferencia
        porc_solidos = ((self.densidad_pulpa - 1000) / (((self.ge - 1) / self.ge) * self.densidad_pulpa)) * 100
        vol_liquido = (self.tonelaje * (100 - porc_solidos)) / porc_solidos
        vol_mineral = self.tonelaje / self.ge

        T_transferencia = {
            t: round((math.pi * 0.25 * 24 * 60 * 0.85 * 0.02831 * 
                      (self.dimensiones_tanques[t][0] ** 2) * 
                      self.dimensiones_tanques[t][1] / (vol_liquido + vol_mineral)))
            for t in self.capacidad_tanques
        }

        # 🔹 Inicializar tanques y tiempos
        contenido = {t: {} for t in self.capacidad_tanques}
        tiempo_acumulado = {t: 0 for t in self.capacidad_tanques}

        df_materiales = self.df_materiales.copy()
        df_materiales["time"] = df_materiales["hora_salida_molino"]

        # 🔹 Simulación
        for paso in range(num_pasos):
            if paso >= len(df_materiales):
                break  # Evitar errores si se supera el tamaño del DataFrame

            tiempo_actual = df_materiales.iloc[paso]["time"]

            # 🔹 Entrada de material en el Tanque 1
            material_entrada = df_materiales.iloc[paso]["id_blending"]
            cantidad_entrada = df_materiales.iloc[paso]["ton_5min"]
            if material_entrada in contenido[1]:
                contenido[1][material_entrada] += cantidad_entrada
            else:
                contenido[1][material_entrada] = cantidad_entrada

            # 🔹 Transferencia entre tanques
            for t in range(1, num_tanques):  # Desde el Tanque 1 hasta el penúltimo
                if contenido[t]:  # Si hay material en el tanque actual
                    tiempo_acumulado[t] += self.intervalo

                    if tiempo_acumulado[t] >= T_transferencia[t]:  # Si es momento de transferir
                        if contenido[t + 1]:
                            for material, cantidad in contenido[t].items():
                                contenido[t + 1][material] = contenido[t + 1].get(material, 0) + cantidad
                        else:
                            contenido[t + 1] = contenido[t].copy()

                        contenido[t] = {}  # Vaciar el tanque actual
                        tiempo_acumulado[t] = 0  # Reiniciar tiempo acumulado

            # 🔹 Guardar estado de los tanques en el historial
            for t in self.capacidad_tanques:
                historial_tanques[t].append({"time": tiempo_actual, **contenido[t]})

        # 🔹 Convertir historial en DataFrames
        df_resultados = {t: pd.DataFrame(historial) for t, historial in historial_tanques.items()}
        return tuple(df_resultados[t] for t in sorted(df_resultados.keys()))