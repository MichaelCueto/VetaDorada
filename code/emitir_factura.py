# Requisitos:
# pip install lxml cryptography signxml zeep pandas requests

import os
import base64
import pandas as pd
from lxml import etree
from datetime import datetime

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from signxml import XMLSigner, methods

from requests import Session
from requests.auth import HTTPBasicAuth

from zeep import Client, Transport
from zeep.wsse.username import UsernameToken

# ---------------------- CONFIGURACIÓN ----------------------
RUC_EMISOR       = "20123456789"
RAZON_SOCIAL_EMISOR = "MI EMPRESA SAC"
PFX_PATH         = "certificado_prueba.pfx"
PFX_PASSWORD     = "123456"           # La que usaste en OpenSSL
USUARIO_SOL      = "TUUSUARIO"        # Sin RUC
CLAVE_SOL        = "TUCLAVE"
WSDL_SUNAT = "file:///Users/michaelcueto/Documents/proyectos/trazavilidad-VetaDorada/code/billService.wsdl"
VALOR_MINERAL    = 1500.00            # Valor por tonelada de mineral

# ---------------------- UTIL: Verificar carga del .pfx ----------------------
def verificar_certificado(pfx_path, pfx_password):
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()
    try:
        pkcs12.load_key_and_certificates(
            pfx_data,
            pfx_password.encode(),
            backend=default_backend()
        )
        print("✅ El certificado .pfx se cargó correctamente.")
    except Exception as e:
        raise RuntimeError(f"❌ Error cargando el .pfx: {e}")

# ---------------------- PASO 1: Generar XML ----------------------
def generar_xml_factura(factura: dict, output_path: str) -> str:
    root = etree.Element("Invoice")

    # Mapeo explícito tag → clave en el dict
    etree.SubElement(root, "FechaEmision").text           = factura["fecha_emision"]
    etree.SubElement(root, "RUCEmisor").text             = factura["ruc_emisor"]
    etree.SubElement(root, "RazonSocialEmisor").text     = factura["razon_social_emisor"]
    etree.SubElement(root, "RUCReceptor").text           = factura["ruc_receptor"]
    etree.SubElement(root, "NombreReceptor").text        = factura["nombre_receptor"]
    etree.SubElement(root, "Moneda").text                = factura["moneda"]
    etree.SubElement(root, "MetodoPago").text            = factura["metodo_pago"]

    items = etree.SubElement(root, "Items")
    for item in factura["items"]:
        item_element = etree.SubElement(items, "Item")
        for key, value in item.items():
            etree.SubElement(item_element, key).text = str(value)

    tree = etree.ElementTree(root)
    tree.write(output_path, pretty_print=True, xml_declaration=True, encoding="utf-8")
    return output_path

# ---------------------- PASO 2: Firmar XML ----------------------
def firmar_xml(xml_path: str, pfx_path: str, pfx_password: str) -> str:
    verificar_certificado(pfx_path, pfx_password)
    xml = etree.parse(xml_path)
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data, pfx_password.encode(), backend=default_backend()
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem  = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256"
    )
    signed = signer.sign(xml, key=key_pem, cert=cert_pem)
    out = xml_path.replace(".xml", "_firmado.xml")
    with open(out, "wb") as f:
        f.write(etree.tostring(
            signed, pretty_print=True, 
            xml_declaration=True, encoding="utf-8"
        ))
    return out

# ---------------------- PASO 3: Enviar a SUNAT ----------------------
def enviar_sunat(xml_firmado_path: str, ruc: str, usuario: str, clave: str) -> str:
    # … tu código de lectura y base64 …

    # Construye la URL con credenciales en línea
    wsdl_url = (
        f"https://{ruc}{usuario}:{clave}"
        "@e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl"
    )

    session = Session()
    # Ya no es estrictamente necesario session.auth, pero no hace daño
    session.auth = HTTPBasicAuth(f"{ruc}{usuario}", clave)
    transport = Transport(session=session)

    client = Client(
        wsdl=wsdl_url,           # URL con user:pass@
        transport=transport,
        wsse=UsernameToken(f"{ruc}{usuario}", clave)
    )

    response = client.service.sendBill(archivo_zip, zip_b64)
    # … resto igual …
    cdr = base64.b64decode(resp.applicationResponse)
    cdr_path = xml_firmado_path.replace("_firmado.xml", "_CDR.xml")
    with open(cdr_path, "wb") as f:
        f.write(cdr)
    return cdr_path

# ---------------------- PASO 4: Leer Excel y emitir facturas ----------------------
def generar_facturas_desde_excel(excel_path: str):
    df = pd.read_excel(excel_path).head()
    df = df[df['ruc'].notna()].copy()
    df['ruc'] = df['ruc'].astype(int).astype(str)

    facturas = []
    for idx, row in df.iterrows():
        fact = {
            "fecha_emision": datetime.now().strftime("%Y-%m-%d"),
            "ruc_emisor": RUC_EMISOR,
            "razon_social_emisor": RAZON_SOCIAL_EMISOR,
            "ruc_receptor": row['ruc'],
            "nombre_receptor": row['nombre_del_minero'],
            "moneda": "PEN",
            "metodo_pago": "Contado",
            "items": [{
                "descripcion":   "Compra de mineral",
                "unidad_medida": "TM",
                "cantidad":      round(row['tonelaje'], 2),
                "valor_unitario": VALOR_MINERAL,
                "precio_unitario": round(VALOR_MINERAL * 1.18, 2),
                "subtotal":       round(row['tonelaje'] * VALOR_MINERAL, 2),
                "igv":            round(row['tonelaje'] * VALOR_MINERAL * 0.18, 2),
                "total":          round(row['tonelaje'] * VALOR_MINERAL * 1.18, 2)
            }]
        }
        facturas.append((idx, fact))
    return facturas

# ---------------------- EJECUCIÓN ----------------------
if __name__ == "__main__":
    excel_path = "../database/mineral_test.xlsx"
    facturas = generar_facturas_desde_excel(excel_path)
    print(f"✅ Se generaron {len(facturas)} facturas a partir del archivo Excel.")

    for idx, factura in facturas:
        xml_name    = f"factura_{idx+1}.xml"
        xml_path    = generar_xml_factura(factura, xml_name)
        xml_signed  = firmar_xml(xml_path, PFX_PATH, PFX_PASSWORD)
        cdr_path    = enviar_sunat(xml_signed, RUC_EMISOR, USUARIO_SOL, CLAVE_SOL)
        print(f"✅ Factura {idx+1} enviada. CDR en: {cdr_path}")