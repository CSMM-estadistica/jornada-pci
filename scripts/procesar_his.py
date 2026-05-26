import pandas as pd
import os

def procesar_informacion_his():
    # Ruta del archivo que exportas con tu consulta SQL y subes a GitHub
    ruta_origen = 'data/his_raw.csv'
    # El archivo limpio final comprimido que lee tu HTML
    ruta_destino = 'data/data_jornada.csv'
    
    if not os.path.exists(ruta_origen):
        print("Aviso: No se detectó un archivo nuevo en 'data/his_raw.csv'. Se mantiene la data actual.")
        return

    print("Iniciando consolidación de datos exportados por el Script SQL...")
    
    # 1. Carga del CSV controlando codificación y separadores comunes en exportaciones de BD
    try:
        df = pd.read_csv(ruta_origen, sep=';', encoding='utf-8')
    except Exception:
        df = pd.read_csv(ruta_origen, sep=',', encoding='utf-8')
    
    # Limpiar espacios en blanco invisibles en los nombres de las cabeceras
    df.columns = [col.strip() for col in df.columns]
    
    # 2. Normalizar nombres de columnas críticas por si tu SQL exportó en mayúsculas/minúsculas
    # Buscamos correspondencias sin importar cómo lo haya estructurado el gestor de BD
    mapeo_columnas = {
        'anio': 'Anio', 'MES': 'Mes', 'FECHA_ATENCION': 'Fecha_Atencion', 
        'UPSS': 'UPSS', 'codigo_item': 'Codigo_Item', 'valor_lab': 'Valor_Lab'
    }
    df.rename(columns=mapeo_columnas, inplace=True)
    
    # 3. Filtrado de seguridad (por si acaso el filtro del SQL trajo otros datos o nulos)
    if 'Valor_Lab' in df.columns:
        df['Valor_Lab'] = df['Valor_Lab'].astype(str).str.strip()
        df = df[df['Valor_Lab'].isin(['1', 'TA'])]
    else:
        print("Error: No se encontró la columna 'valor_lab' en el archivo exportado.")
        return

    if df.empty:
        print("Aviso: El archivo no contiene registros válidos para '1' o 'TA'.")
        return

    # 4. Asegurar que las columnas de grupos etarios existan y sean numéricas (enteros)
    grupos_etarios = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    for grupo in grupos_etarios:
        if grupo in df.columns:
            df[grupo] = pd.to_numeric(df[grupo], errors='coerce').fillna(0).astype(int)
        else:
            # Si por alguna razón la BD no botó registros para una etapa, la inicializamos en 0
            df[grupo] = 0
            
    # 5. Normalizar el formato de la fecha de atención (eliminar horas si tu BD exportó tipo Timestamp)
    df['Fecha_Atencion'] = df['Fecha_Atencion'].astype(str).str.split(' ').str[0]
    
    # 6. Agrupación final masiva (Suma todos los conteos de los profesionales por día y plan)
    df_final = df.groupby(['Fecha_Atencion', 'Valor_Lab'])[grupos_etarios].sum().reset_index()
    
    # 7. Guardar la base de datos estática para producción
    df_final.to_csv(ruta_destino, index=False)
    print(f"Sincronización exitosa. Se consolidaron {len(df_final)} fechas de atención para el C.S. Medalla Milagrosa.")

if __name__ == "__main__":
    procesar_informacion_his()
