import requests
import pandas as pd
import numpy as np
from tabula.io import read_pdf

# URL donde se publica periódicamente el PDF
PDF_URL = "https://intranet2.minem.gob.pe/ProyectoDGE/Mineria/registro%20especial%20de%20comercializadores%20y%20procesadores%20de%20oro.pdf"
LOCAL_PDF_PATH = "recpo.pdf"

def descargar_pdf(url: str, destino: str) -> None:
    """
    Descarga el PDF desde 'url' y lo guarda en 'destino'.
    """
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(destino, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"✅ PDF descargado correctamente en '{destino}'.")

def correccion_pdf(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Aplica las dos condiciones de limpieza a cada DataFrame extraído del PDF,
    concatena todos, descarta filas sin 'ruc' y salva el resultado final en 'recpo.xlsx'.
    """
    dfs_corregidos: list[pd.DataFrame] = []

    for i, df in enumerate(dfs):
        df_copy = df.copy()

        # Condición 1: si en la columna 2 las filas 2 a 5 (índices 2:6) están todas NaN, eliminar esa columna
        if df_copy.shape[1] > 2 and df_copy.shape[0] > 5:
            col_vals = df_copy.iloc[2:6, 2]  # filas con índice 2,3,4,5 y columna índice 2
            print(f"Verificando DataFrame {i+1}, columna 2, filas 2 a 5: {col_vals.tolist()}")
            if col_vals.isna().all():
                df_copy = df_copy.drop(df_copy.columns[2], axis=1)
                print(f"Condición 1 aplicada a DataFrame {i+1}: columna 2 eliminada.")

            print(f"DataFrame {i+1} después de Condición 1: {df_copy.shape}")
            if df_copy.shape[1] == 12:
                # Si quedaron 12 columnas, eliminar también la columna en índice 9 (la décima original)
                df_copy = df_copy.drop(df_copy.columns[9], axis=1)
                print(f"Condición 1 adicional a DataFrame {i+1}: columna 10 eliminada.")

        # Renombrar columnas (ya quedan 11 columnas en cada tabla corregida)
        df_copy.columns = [
            "Item", "Declarante", "N° Registro", "N° Recurso", "Fecha Recurso",
            "Tipo Persona", "ruc", "dni", "email", "Condicion", "situacion"
        ]

        # Condición 2: si no es el primer DataFrame (i > 0), eliminar la primera fila
        if i > 0:
            df_copy = df_copy.iloc[1:].reset_index(drop=True)

        dfs_corregidos.append(df_copy)

    # Concatenar todos los DataFrames corregidos y limpiar filas sin 'ruc'
    df_completo = pd.concat(dfs_corregidos, ignore_index=True)
    df_completo = df_completo.dropna(subset=["ruc"])
    # Eliminar la primera fila agregada por el encabezado de la primera tabla
    df_completo = df_completo.iloc[1:].reset_index(drop=True)

    # Guardar a Excel
    df_completo.to_excel("recpo.xlsx", index=False)
    print("✅ Resultado final guardado en 'recpo.xlsx'.")
    return df_completo

if __name__ == "__main__":
    try:
        # 1) Descargar la última versión del PDF
        descargar_pdf(PDF_URL, LOCAL_PDF_PATH)

        # 2) Leer todas las tablas del PDF recién descargado
        dfs = read_pdf(
            LOCAL_PDF_PATH,
            pages="all",
            multiple_tables=True,
            force_subprocess=True
        )

        # 3) Aplicar la función de corrección y generar el Excel
        correccion_pdf(dfs)

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")