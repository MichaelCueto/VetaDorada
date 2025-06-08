import time
import random
import re
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright

PALABRAS_MINERIA = ["mineral", "minería", "extracción", "comercialización de minerales"]

def actividad_es_mineria(actividad: str) -> bool:
    return any(p in actividad.lower() for p in PALABRAS_MINERIA)

def consultar_ruc_sunat(ruc: str, reintentos=3) -> dict:
    ruc = str(int(float(ruc)))  # asegurar formato limpio

    for intento in range(1, reintentos + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, slow_mo=150)
                context = browser.new_context()
                page = context.new_page()

                print(f"🌐 Intento {intento}: Navegando a SUNAT para RUC {ruc}")
                page.goto("https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp", timeout=20000)

                # Usamos el frame por si aún existe, pero validamos también si está directamente en la página
                frame = page.frame(name="main") or page.main_frame

                # Esperar el input y botón
                frame.wait_for_selector("#txtRuc", timeout=10000)
                frame.fill("#txtRuc", ruc)
                time.sleep(random.uniform(1, 2))
                frame.click("#btnAceptar")

                # Esperar carga de resultado
                page.wait_for_url("**/jcrS00Alias", timeout=15000)
                page.wait_for_selector(".panel.panel-primary", timeout=10000)

                # Extraer HTML y parsear
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                actividades = [
                    td.text.strip()
                    for td in soup.select("td")
                    if re.search(r'(Principal|Secundaria)\s*-\s*\d{4}', td.text)
                ]
                actividad_str = "; ".join(actividades)
                alerta = "Normal" if actividad_es_mineria(actividad_str) else "⚠️ Actividad no minera"

                print(f"✅ Actividad económica detectada: {actividad_str[:60]}...")

                return {
                    "ruc": ruc,
                    "actividad_economica": actividad_str or "No encontrado",
                    "alerta": alerta
                }

        except Exception as e:
            print(f"❌ Error en intento {intento} para RUC {ruc}: {e}")
            time.sleep(random.uniform(5, 10))  # evitar bloqueo

    return {
        "ruc": ruc,
        "actividad_economica": "Error",
        "alerta": f"❌ No se pudo consultar tras {reintentos} intentos"
    }
def procesar_df_rucs(df: pd.DataFrame, columna_ruc="ruc") -> pd.DataFrame:
    resultados = []
    for ruc in df[columna_ruc].dropna().astype(str).unique():
        resultado = consultar_ruc_sunat(ruc)
        resultados.append(resultado)
        time.sleep(random.uniform(1, 3))
    
    df_resultados = pd.DataFrame(resultados)
    df = df.copy()
    df[columna_ruc] = df[columna_ruc].astype(str)
    df_resultados["ruc"] = df_resultados["ruc"].astype(str)
    return df