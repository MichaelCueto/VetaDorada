function importarExcel() {
  alert("Función de importación aún en desarrollo.");
}

function cambiarFuente() {
  const fuente = document.getElementById("fuente").value;
  const excelInputs = document.getElementById("inputs-excel");
  const dbConnection = document.getElementById("db-connection");

  if (fuente === "excel") {
    excelInputs.style.display = "block";
    dbConnection.style.display = "none";
  } else {
    excelInputs.style.display = "none";
    dbConnection.style.display = "block";
  }
}

function conectarBD() {
  document.getElementById("modal-conexion").style.display = "flex";
}

function cerrarModalConexion() {
  document.getElementById("modal-conexion").style.display = "none";
}

function confirmarConexion() {
  const usuario = document.getElementById("db-user").value;
  const password = document.getElementById("db-pass").value;
  const host = document.getElementById("db-host").value;
  const base = document.getElementById("db-name").value;

  fetch("/api/configurar_conexion", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ usuario, password, host, base })
  })
    .then(res => res.json())
    .then(data => {
      if (data.message) {
        alert(data.message);
        cerrarModalConexion();
      } else {
        alert("Error al conectar: " + data.error);
      }
    })
    .catch(err => {
      alert("Error de red al intentar conectar a la base de datos.");
      console.error(err);
    });
}

function toggleParametros() {
  const all = document.getElementById("all").value;
  const parametros = document.getElementById("parametros");
  const btnCalc = document.getElementById("btn-calcular");
  const btnRastreo = document.getElementById("btn-rastrear");

  if (all === "false") {
    parametros.style.display = "block";
    btnCalc.style.display = "none";
    btnRastreo.style.display = "inline-block";
  } else {
    parametros.style.display = "none";
    btnCalc.style.display = "inline-block";
    btnRastreo.style.display = "none";
  }
}

function obtenerTrazabilidad() {
  const fuente = document.getElementById("fuente").value;
  const ejecutarTodos = document.getElementById("all").value;

  if (fuente === "excel" && ejecutarTodos === "true") {
    const formData = new FormData();
    formData.append("mineral", document.getElementById("import-mineral").files[0]);
    formData.append("recuperacion", document.getElementById("import-recuperacion").files[0]);
    formData.append("blendings", document.getElementById("import-blendings").files[0]);
    formData.append("fecha_blending", document.getElementById("import-fecha_blending").files[0]);
    formData.append("cosechas", document.getElementById("import-cosechas").files[0]);
    formData.append("densidad_pulpa", document.getElementById("densidad_pulpa").value);
    formData.append("ge", document.getElementById("ge").value);
    formData.append("tonelaje", document.getElementById("tonelaje").value);

    fetch("/trazabilidad", {
      method: "POST",
      body: formData
    })
      .then(response => {
        if (!response.ok) throw new Error("Error al generar trazabilidad.");
        return response.blob();
      })
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "trazabilidad_resultados.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch(err => {
        alert("❌ Error al calcular trazabilidad desde archivo");
        console.error(err);
      });

  } else if (fuente === "db" && ejecutarTodos === "true") {
    const body = {
      densidad_pulpa: document.getElementById("densidad_pulpa").value,
      ge: document.getElementById("ge").value,
      tonelaje: document.getElementById("tonelaje").value
    };

    fetch("/trazabilidad_desde_mysql", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    })
      .then(response => {
        if (!response.ok) throw new Error("Error al generar trazabilidad desde base de datos.");
        return response.blob();
      })
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "trazabilidad_resultados.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch(err => {
        alert(err.message);
        console.error(err);
      });

  } else {
    alert("Selecciona una fuente y asegúrate que 'Ejecutar para todos' esté en Sí.");
  }
}

function calcularRastreo() {
  alert("Función de rastreo en desarrollo...");
}

function cerrarModal() {
  document.getElementById("modal-trazabilidad").style.display = "none";
}

function habilitarParametros() {
  ["densidad_pulpa", "ge", "tonelaje"].forEach(id => {
    const input = document.getElementById(id);
    input.disabled = !input.disabled;
  });
}