# import pandas as pd
# from itertools import combinations

# class Trazabilidad:
#     def __init__(self,df_info,df_cosecha,alfa,beta):
#         self.df_info = df_info[df_info["id_blending"].isin(df_cosecha["id_blending"])]
#         self.df_cosecha = df_cosecha
#         self.alfa = alfa #umbral de deficit de material en busqueda de id_mineral
#         self.beta = beta #constante de retención de tanque
    
#     def deficit(self):
#         df_info_agrupado = self.df_info.groupby("id_blending")["tonelaje"].sum().reset_index()
#         df_comparacion = self.df_cosecha.merge(df_info_agrupado, on="id_blending", suffixes=("_cosecha", "_info"))
#         deficit_ids = df_comparacion[df_comparacion["tonelaje_cosecha"] < (1 - self.alfa) * df_comparacion["tonelaje_info"]]["id_blending"].tolist()
#         df_deficit = df_comparacion[df_comparacion["tonelaje_cosecha"] < (1 - self.alfa) * df_comparacion["tonelaje_info"]]
#         return deficit_ids, df_deficit

#     def participacion(self):
#         def encontrar_mejor_combinacion(df_blendings, id_blending, tonelaje_objetivo):
#             minerales = df_blendings[df_blendings['id_blending'] == id_blending]
#             mejores_minerales = None
#             mejor_diferencia = float('inf')

#             for i in range(1, len(minerales) + 1):
#                 for combo in combinations(minerales.itertuples(index=False), i):
#                     suma_tonelaje = sum(mineral.tonelaje for mineral in combo)
#                     diferencia = abs(tonelaje_objetivo - suma_tonelaje)

#                     if diferencia < mejor_diferencia:
#                         mejor_diferencia = diferencia
#                         mejores_minerales = combo

#                     if diferencia == 0:
#                         return combo
#             return mejores_minerales

#         selecciones = []
#         for id_blending in self.deficit()[0]:
#             tonelaje_cosecha = self.df_cosecha[self.df_cosecha["id_blending"] == id_blending]["tonelaje"].values[0]
#             mejores_minerales = encontrar_mejor_combinacion(self.df_info, id_blending, tonelaje_cosecha)
            
#             if mejores_minerales:
#                 for mineral in mejores_minerales:
#                     selecciones.append(self.df_info[(self.df_info['id_blending'] == id_blending) & 
#                                                         (self.df_info['id_mineral'] == mineral.id_mineral)])
#         df_minerales_corregidos = pd.concat(selecciones, ignore_index=True) if selecciones else pd.DataFrame()
#         df_sin_deficit = self.df_info[~self.df_info['id_blending'].isin(self.deficit()[1]["id_blending"])]
#         df_resultado = pd.concat([df_minerales_corregidos, df_sin_deficit], ignore_index=True)
#         df_transferencia = df_resultado.copy()
#         df_resultado["cm_au"] = df_resultado["tonelaje"]*df_resultado["ley_au"]*df_resultado["rec_au"]*self.beta
#         df_transferencia["cm_au"] = df_transferencia["tonelaje"]*df_transferencia["ley_au"]*df_transferencia["rec_au"]*(1-self.beta)
#         return df_resultado, df_transferencia

import pandas as pd
from itertools import combinations

class Trazabilidad:
    def __init__(self, df_info, df_cosecha, alfa):
        self.df_info = df_info[df_info["id_blending"].isin(df_cosecha["id_blending"])]
        self.df_cosecha = df_cosecha
        self.alfa = alfa  # Umbral de déficit de material en búsqueda de id_mineral

    def deficit(self):
        df_info_agrupado = self.df_info.groupby("id_blending")["tonelaje"].sum().reset_index()
        df_comparacion = self.df_cosecha.merge(df_info_agrupado, on="id_blending", suffixes=("_cosecha", "_info"))
        df_comparacion["deficit"] = df_comparacion["tonelaje_cosecha"] < (1 - self.alfa) * df_comparacion["tonelaje_info"]
        df_deficit = df_comparacion[df_comparacion["deficit"]]
        return df_deficit["id_blending"].tolist(), df_deficit

    def encontrar_mejor_aproximacion(self, df_blendings, id_blending, tonelaje_objetivo):
        minerales = df_blendings[df_blendings['id_blending'] == id_blending].copy()
        minerales = minerales.sort_values(by="tonelaje", ascending=False)  # Ordenar por tonelaje
        seleccion = []
        tonelaje_acumulado = 0

        for _, mineral in minerales.iterrows():
            if tonelaje_acumulado + mineral["tonelaje"] <= tonelaje_objetivo:
                seleccion.append(mineral)
                tonelaje_acumulado += mineral["tonelaje"]
                
            if tonelaje_acumulado >= tonelaje_objetivo:
                break
        
        return seleccion

    def participacion(self):
        selecciones = []
        for id_blending in self.deficit()[0]:
            tonelaje_cosecha = self.df_cosecha.query("id_blending == @id_blending")["tonelaje"].values[0]
            mejores_minerales = self.encontrar_mejor_aproximacion(self.df_info, id_blending, tonelaje_cosecha)
            
            if mejores_minerales:
                selecciones.append(pd.DataFrame(mejores_minerales))
        
        df_minerales_corregidos = pd.concat(selecciones, ignore_index=True) if selecciones else pd.DataFrame()
        df_sin_deficit = self.df_info[~self.df_info['id_blending'].isin(self.deficit()[1]["id_blending"])]
        df_resultado = pd.concat([df_minerales_corregidos, df_sin_deficit], ignore_index=True)
        
        return df_resultado

