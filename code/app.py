from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from user import TrazabilidadSimulador
import tempfile
import pymysql
import os

app = Flask(__name__, template_folder='../templates', static_folder='../frontend/static')
app.secret_key = "super-secret-key"
CORS(app)

# Config por defecto (puede ser reemplazada por /api/configurar_conexion)
default_config = {
    "usuario": "root",
    "password": "michael1800%",
    "host": "localhost",
    "base": "trazabilidad"
}

# Variable para almacenar la configuración activa
conexion_actual = default_config.copy()

# Función para construir la URI de SQLAlchemy desde la config
def construir_uri_mysql(config):
    return f"mysql+pymysql://{config['usuario']}:{config['password']}@{config['host']}/{config['base']}"

# Cargar la conexión inicial
app.config['SQLALCHEMY_DATABASE_URI'] = construir_uri_mysql(conexion_actual)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 📦 Modelos
class Mineral(db.Model):
    __tablename__ = 'mineral'
    id_mineral = db.Column(db.String(50), primary_key=True)
    fecha_ingreso = db.Column(db.DateTime)
    fecha_proceso = db.Column(db.DateTime)
    nombre_del_minero = db.Column(db.String(100))
    zona = db.Column(db.String(100))
    tonelaje = db.Column(db.Float)
    ley_au = db.Column(db.Float)
    ley_ag = db.Column(db.Float)

class Recuperacion(db.Model):
    __tablename__ = 'recuperacion'
    id = db.Column(db.Integer, primary_key=True)
    id_mineral = db.Column(db.String(50), db.ForeignKey('mineral.id_mineral'))
    rec_au = db.Column(db.Float)
    rec_ag = db.Column(db.Float)

class Blending(db.Model):
    __tablename__ = 'blending'
    id_blending = db.Column(db.String(50), primary_key=True)
    id_mineral = db.Column(db.String(50), db.ForeignKey('mineral.id_mineral'))
    fecha = db.Column(db.DateTime)

class FechaBlending(db.Model):
    __tablename__ = 'fecha_blending'
    id = db.Column(db.Integer, primary_key=True)
    id_blending = db.Column(db.String(50), db.ForeignKey('blending.id_blending'))
    fecha_ingreso_planta = db.Column(db.DateTime)
    tonelaje = db.Column(db.Float)

class Cosecha(db.Model):
    __tablename__ = 'cosechas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_campania = db.Column(db.String(50), nullable=False)
    tanque_cosechado = db.Column(db.Integer, nullable=False)
    fecha_cosecha = db.Column(db.DateTime, nullable=False)
    tanque_aportador = db.Column(db.Integer, nullable=True)  # puede estar vacío
    cm_au_real = db.Column(db.Float, nullable=False)

# 🚀 Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# 🧪 Endpoint para crear las tablas
@app.route('/api/connect_db', methods=['GET'])
def connect_db():
    try:
        db.create_all()
        return jsonify({"message": "Conexión exitosa. Tablas creadas."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔧 Endpoint para configurar conexión
@app.route('/api/configurar_conexion', methods=['POST'])
def configurar_conexion():
    global conexion_actual, db

    data = request.get_json()
    conexion_actual = {
        "usuario": data.get("usuario"),
        "password": data.get("password"),
        "host": data.get("host", "localhost"),
        "base": data.get("base")
    }

    try:
        # Probar conexión manualmente con pymysql
        conn = pymysql.connect(
            host=conexion_actual["host"],
            user=conexion_actual["usuario"],
            password=conexion_actual["password"],
            database=conexion_actual["base"]
        )
        conn.close()

        # Actualizar URI para SQLAlchemy
        app.config['SQLALCHEMY_DATABASE_URI'] = construir_uri_mysql(conexion_actual)
        db.engine.dispose()

        return jsonify({"message": "✅ Conexión establecida con éxito."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📊 Calcular trazabilidad desde archivos Excel
@app.route("/trazabilidad", methods=["POST"])
def calcular_trazabilidad():
    try:
        minerales = request.files['minerales']
        recuperacion = request.files['recuperacion']
        blending = request.files['blending']
        fecha_blending = request.files['fecha_blending']
        cosechas = request.files.get('cosechas')

        temp_dir = tempfile.mkdtemp()
        paths = {
            "minerales": os.path.join(temp_dir, "mineral.xlsx"),
            "recuperacion": os.path.join(temp_dir, "recuperacion.xlsx"),
            "blending": os.path.join(temp_dir, "blending.xlsx"),
            "fecha_blending": os.path.join(temp_dir, "fecha_blending.xlsx"),
            "cosechas": os.path.join(temp_dir, "cosechas.xlsx") if cosechas else None,
        }

        minerales.save(paths["minerales"])
        recuperacion.save(paths["recuperacion"])
        blending.save(paths["blending"])
        fecha_blending.save(paths["fecha_blending"])
        if cosechas:
            cosechas.save(paths["cosechas"])

        densidad = float(request.form.get("densidad_pulpa"))
        ge = float(request.form.get("ge"))
        tonelaje = float(request.form.get("tonelaje"))

        simulador = TrazabilidadSimulador(
            paths=paths,
            densidad=densidad,
            ge=ge,
            tonelaje=tonelaje
        )
        simulador.ejecutar(all=True,  output_path=output_path)

        return jsonify({"mensaje": "Trazabilidad generada con éxito."})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

from flask import send_file
import tempfile

@app.route("/trazabilidad_desde_mysql", methods=["POST"])
def calcular_trazabilidad_mysql():
    try:
        data = request.json
        densidad = float(data["densidad_pulpa"])
        ge = float(data["ge"])
        tonelaje = float(data["tonelaje"])

        # Archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        output_path = temp_file.name

        sim = TrazabilidadSimulador(
            db_uri=app.config["SQLALCHEMY_DATABASE_URI"],
            densidad=densidad,
            ge=ge,
            tonelaje=tonelaje
        )
        sim.ejecutar(all=True, output_path=output_path)

        return send_file(
            output_path,
            as_attachment=True,
            download_name="trazabilidad_resultados.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print("❌ Error al generar trazabilidad desde MySQL:")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True, port=7000)