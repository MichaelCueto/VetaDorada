# download_sunat_wsdl.py
import requests
from base64 import b64encode

# ——— CONFIGURACIÓN ———
RUC_EMISOR  = "20123456789"
USUARIO_SOL = "TUUSUARIO"    # sin RUC
CLAVE_SOL   = "TUCLAVE"
BASE_URL    = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"

# Map de suffix → fichero local
endpoints = {
    "?wsdl":      "billService.wsdl",
    "?ns1.wsdl":  "billService_ns1.wsdl",
    "?ns2.xsd":   "billService_ns2.xsd",
    "?ns3.xsd":   "billService_ns3.xsd",
}

# Prepara el header Authorization
userpass = f"{RUC_EMISOR}{USUARIO_SOL}:{CLAVE_SOL}"
auth_header = "Basic " + b64encode(userpass.encode()).decode()

# Sesión sin tomar de entorno, con header fijo
session = requests.Session()
session.trust_env = False
session.headers.update({
    "Authorization": auth_header
})

for suffix, filename in endpoints.items():
    url = BASE_URL + suffix
    print(f"Descargando {url} → {filename}")
    resp = session.get(url, allow_redirects=True)
    if resp.status_code != 200:
        print(f" ❌ {resp.status_code} al descargar {suffix}")
        continue
    with open(filename, "wb") as f:
        f.write(resp.content)

print("✅ Descarga local completada.")