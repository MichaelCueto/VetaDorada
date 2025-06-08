# Usa una imagen oficial de Python como base
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos necesarios
COPY . /app

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto en el que Flask se ejecutará
EXPOSE 5001

# Comando por defecto para ejecutar la aplicación
CMD ["python", "code/app.py"]