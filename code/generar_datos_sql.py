from app import app, db, Mineral, Recuperacion, Blending, FechaBlending, Cosecha
from datetime import datetime, timedelta
from random import randint, uniform, choice
from calendar import monthrange

print("🔄 Cargando datos realistas para 6 meses...")

with app.app_context():
    db.drop_all()
    db.create_all()

    # Nuevos productores y zonas ampliados
    nombres_minero = [
        "Juan Pérez", "María Quispe", "Luis Gutiérrez", "Rosa Mamani", "Carlos Huamán",
        "Ana Rojas", "Pedro Salazar", "Lucía Vargas", "Miguel Choque", "Carmen Ccopa",
        "Jorge Ñahui", "Yolanda Lazo", "Óscar Ccallo", "Teresa Apaza", "Eduardo Cusihuamán",
        "Sandra Cutipa", "Diego Asto", "Elena Huanca", "Alberto Churata", "Viviana Puma",
        "Raúl Taco", "Fátima Ccama", "Andrés Huarcaya", "Yesenia Flores", "Julio Ccari",
        "Gloria Choquehuanca", "Felipe Loayza", "Vanessa Ríos", "Ricardo Camargo", "Karla Vilca"
    ]

    zonas = [
        "Cajamarca", "Arequipa", "Ayacucho", "Puno", "La Libertad",
        "Ancash", "Junín", "Pasco", "Cusco", "Apurímac",
        "Huancavelica", "Tacna", "Moquegua", "Piura", "Huánuco"
    ]

    base_date = datetime.now() - timedelta(days=180)  # 6 meses
    id_mineral_counter = 1
    id_blending_counter = 1

    for dia in range(180):
        fecha_dia = base_date + timedelta(days=dia)
        num_lotes = randint(10, 15)
        tonelaje_total = round(uniform(480, 520), 2)
        tonelaje_por_lote = tonelaje_total / num_lotes
        lotes_dia = []

        for _ in range(num_lotes):
            id_mineral = f"M{id_mineral_counter:05d}"
            lotes_dia.append(id_mineral)

            mineral = Mineral(
                id_mineral=id_mineral,
                fecha_ingreso=fecha_dia,
                fecha_proceso=fecha_dia + timedelta(days=1),
                nombre_del_minero=choice(nombres_minero),
                zona=choice(zonas),
                tonelaje=round(uniform(tonelaje_por_lote - 2, tonelaje_por_lote + 2), 2),
                ley_au=round(uniform(1.0, 3.5), 2),
                ley_ag=round(uniform(2.0, 7.0), 2)
            )

            recuperacion = Recuperacion(
                id_mineral=id_mineral,
                rec_au=round(uniform(75, 90), 2),
                rec_ag=round(uniform(65, 85), 2)
            )

            db.session.add(mineral)
            db.session.add(recuperacion)
            id_mineral_counter += 1

        db.session.flush()

        id_blending = f"B{id_blending_counter:05d}"
        id_mineral_blending = choice(lotes_dia)

        blending = Blending(
            id_blending=id_blending,
            id_mineral=id_mineral_blending,
            fecha=fecha_dia + timedelta(days=2)
        )

        db.session.add(blending)

        # 📈 FechaBlending: 24h continuas cada 5 minutos
        start_time = fecha_dia + timedelta(days=3)
        num_intervals = 288  # 24h * 60 / 5
        tonelaje_promedio = tonelaje_total / num_intervals

        for m in range(0, 1440, 5):  # Cada 5 minutos
            fecha_minuto = start_time + timedelta(minutes=m)
            tonelaje_5min = round(uniform(tonelaje_promedio - 0.5, tonelaje_promedio + 0.5), 2)
            registro = FechaBlending(
                id_blending=id_blending,
                fecha_ingreso_planta=fecha_minuto,
                tonelaje=tonelaje_5min
            )
            db.session.add(registro)

        id_blending_counter += 1

    # ➕ Cosechas simuladas
    print("📊 Agregando cosechas simuladas...")

    cosecha_fecha = base_date + timedelta(days=1)
    cosecha_count = {}

    for _ in range(90):
        mes = cosecha_fecha.month
        mes_str = f"{mes:02d}"
        cosecha_count[mes] = cosecha_count.get(mes, 0) + 1
        dia = cosecha_count[mes]
        dia_str = f"{dia:02d}"

        id_campania = f"C*{mes_str}-{dia_str}"

        hora = choice([2, 4, 5, 9, 10, 11])
        minuto = choice([0, 30])
        fecha_completa = datetime(
            year=cosecha_fecha.year,
            month=cosecha_fecha.month,
            day=cosecha_fecha.day,
            hour=hora,
            minute=minuto
        )

        cosecha = Cosecha(
            id_campania=id_campania,
            tanque_cosechado=randint(1, 5),
            fecha_cosecha=fecha_completa,
            tanque_aportador=choice([None, randint(7, 11)]),
            cm_au_real=round(uniform(420, 1100), 2)
        )
        db.session.add(cosecha)
        cosecha_fecha += timedelta(days=2)

    db.session.commit()
    print("✅ Datos cargados con éxito para 6 meses.")