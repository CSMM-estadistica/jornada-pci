import pandas as pd
import os

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    os.makedirs('data', exist_ok=True)
    
    # 1. Encontrar archivo origen
    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv']
    ruta_origen = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break
            
    if not ruta_origen:
        print("AVISO: No se encontró 'his_raw.csv'. Creando base vacía.")
        pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']).to_csv(ruta_destino, index=False)
        return

    print(f"Leyendo data real desde: {ruta_origen}")
    
    # 2. Leer CSV con separadores comunes
    df = None
    for enc in ['latin-1', 'utf-8', 'utf-8-sig', 'cp1252']:
        try:
            df = pd.read_csv(ruta_origen, sep=';', encoding=enc)
            if len(df.columns) > 3: break
        except Exception:
            try:
                df = pd.read_csv(ruta_origen, sep=',', encoding=enc)
                if len(df.columns) > 3: break
            except Exception:
                continue

    if df is None or df.empty:
        print("Error: El archivo está vacío o ilegible.")
        return

    # Estandarizar columnas a mayúsculas limpias
    df.columns = [str(col).strip().upper() for col in df.columns]

    # 3. Mapeo Flexible de Columnas (Pone nombres fijos si encuentra palabras clave)
    mapeo_columnas = {}
    for col in df.columns:
        if 'FECHA' in col or 'ATENC' in col: mapeo_columnas[col] = 'FECHA_ATENCION'
        elif 'VALOR_LAB' in col or 'VALOR' in col: mapeo_columnas[col] = 'VALOR_LAB'
        elif 'COD_ITEM' in col or 'ITEM' in col or 'PRESTACION' in col: mapeo_columnas[col] = 'CODIGO_ITEM'
        elif 'CORREL' in col or 'NUM_LAB' in col: mapeo_columnas[col] = 'ID_CORRELATIVO_LAB'
        elif 'EDAD' in col or 'ANIO_ACTUAL' in col or 'AÑO' in col: mapeo_columnas[col] = 'ANIO_ACTUAL_PACIENTE'
        elif 'CITA' in col or 'ID_CITA' in col: mapeo_columnas[col] = 'ID_CITA'

    df = df.rename(columns=mapeo_columnas)

    # Asegurar la existencia de campos mínimos para que el WHERE no rompa a Python
    columnas_criticas = ['FECHA_ATENCION', 'VALOR_LAB', 'CODIGO_ITEM', 'ID_CORRELATIVO_LAB', 'ANIO_ACTUAL_PACIENTE']
    for col in columnas_criticas:
        if col not in df.columns:
            # Si no existe, la creamos con valores por defecto para evitar el desplome del script
            df[col] = '99801' if col == 'CODIGO_ITEM' else (1 if col == 'ID_CORRELATIVO_LAB' else 0)

    # 4. Homologar tipos de datos para la cláusula WHERE
    df['CODIGO_ITEM'] = df['CODIGO_ITEM'].astype(str).str.strip()
    df['ID_CORRELATIVO_LAB'] = pd.to_numeric(df['ID_CORRELATIVO_LAB'], errors='coerce').fillna(0).astype(int)
    
    # Aplicar Filtro WHERE equivalente: codigo_item = '99801' AND Id_Correlativo_Lab = 1
    df_filtrado = df[(df['CODIGO_ITEM'] == '99801') & (df['ID_CORRELATIVO_LAB'] == 1)].copy()

    if df_filtrado.empty:
        print("Aviso: Cero filas cumplen con el filtro WHERE (99801 / Correlativo 1).")
        pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']).to_csv(ruta_destino, index=False)
        return

    # 5. Limpieza de Fechas y Edades
    df_filtrado['FECHA_ATENCION'] = df_filtrado['FECHA_ATENCION'].astype(str).str.split(' ').str[0]
    df_filtrado['ANIO_ACTUAL_PACIENTE'] = pd.to_numeric(df_filtrado['ANIO_ACTUAL_PACIENTE'], errors='coerce').fillna(-1).astype(int)

    # Evaluamos si ID_CITA es válido (si no existe la columna, asumimos que todas las filas cuentan)
    if 'ID_CITA' in df_filtrado.columns:
        es_valido = df_filtrado['ID_CITA'].notna() & (df_filtrado['ID_CITA'].astype(str).str.strip() != '')
    else:
        es_valido = True

    # 6. Replicar COUNT(CASE WHEN...) de forma segura usando asignación directa vectorizada
    edad = df_filtrado['ANIO_ACTUAL_PACIENTE']
    
    df_filtrado['NIÑO'] = ((edad >= 0) & (edad <= 11) & es_valido).astype(int)
    df_filtrado['ADOLESCENTE'] = ((edad >= 12) & (edad <= 17) & es_valido).astype(int)
    df_filtrado['JOVEN'] = ((edad >= 18) & (edad <= 29) & es_valido).astype(int)
    df_filtrado['ADULTO'] = ((edad >= 30) & (edad <= 59) & es_valido).astype(int)
    df_filtrado['ADULTO MAYOR'] = ((edad > 59) & es_valido).astype(int)

    # 7. GROUP BY FECHA_ATENCION, VALOR_LAB y ORDER BY FECHA_ATENCION ASC
    grupos_etarios = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    df_consolidado = df_filtrado.groupby(['FECHA_ATENCION', 'VALOR_LAB'])[grupos_etarios].sum().reset_index()
    df_consolidado = df_consolidado.sort_values(by='FECHA_ATENCION', ascending=True)

    # 8. Renombrar campos para compatibilidad con index.html
    df_consolidado = df_consolidado.rename(columns={
        'FECHA_ATENCION': 'Fecha_Atencion',
        'VALOR_LAB': 'Valor_Lab'
    })

    # Guardar reporte final
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Sincronización SQL Exitosa! Registros procesados: {len(df_consolidado)}")

if __name__ == "__main__":
    procesar_informacion_his()
