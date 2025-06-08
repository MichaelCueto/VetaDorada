from playwright.sync_api import sync_playwright
import pandas as pd
import io

def extraer_reinfo_por_ruc(ruc: str) -> pd.DataFrame:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        dfs = []

        try:
            # 1) Navegar y esperar a que cargue completamente
            page.goto("https://pad.minem.gob.pe/REINFO_WEB/Index.aspx", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)

            # 2) Rellenar el campo de RUC
            page.wait_for_selector("#txtruc", timeout=30000)
            page.fill("#txtruc", ruc)

            # 3) Hacer clic en "Buscar"
            page.click("#btnBuscar")

            # 4) Esperar a que aparezca la tabla por primera vez
            page.wait_for_selector("#stdregistro", timeout=30000)

            # 5) Recorrer páginas hasta que el botón "Siguiente" esté deshabilitado
            while True:
                # a) Extraer el HTML de la tabla actual
                html_tabla = page.evaluate("() => document.querySelector('#stdregistro').outerHTML")
                current_df = pd.read_html(io.StringIO(html_tabla), flavor="bs4")[0]
                dfs.append(current_df)

                # b) Verificar si el botón "Siguiente" está deshabilitado
                disabled = page.get_attribute("#ImgBtnSiguiente", "disabled")
                if disabled is not None:
                    break

                # c) Si no está deshabilitado, hacer clic en "Siguiente" y esperar la recarga
                page.click("#ImgBtnSiguiente")
                page.wait_for_selector("#stdregistro", timeout=30000)

            # 6) Concatenar todas las páginas y agregar columna de RUC
            df_total = pd.concat(dfs, ignore_index=True)
            df_total["RUC consultado"] = ruc
            print(f"✅ Se extrajeron {len(df_total)} filas en total para el RUC {ruc}.")

        except Exception as e:
            print(f"❌ Error al procesar RUC {ruc}: {e}")
            page.screenshot(path=f"error_{ruc}.png", full_page=True)
            df_total = pd.DataFrame()

        browser.close()
        return df_total

if __name__ == "__main__":
    ruc_prueba = "20100037689"
    resultado = extraer_reinfo_por_ruc(ruc_prueba)
    print(resultado.head())

    if not resultado.empty:
        # Aplanar columnas MultiIndex antes de exportar
        resultado.columns = [
            " ".join([str(x) for x in col if str(x) != ""])
            for col in resultado.columns
        ]
        resultado.to_excel("resultado_reinfo_completo.xlsx", index=False)
        print("Archivo resultado_reinfo_completo.xlsx creado con éxito.")
    else:
        print("No se recuperaron datos para ese RUC.")