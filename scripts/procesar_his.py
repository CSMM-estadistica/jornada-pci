import pandas as pd
import os

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    os.makedirs('data', exist_ok=True)
    
    # 1. Localizar el archivo de origen
    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv']
    ruta_origen = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break
            
    if not ruta_origen:
        print("AVISO: No se encontró 'his_raw.csv'. Generando estructura base vacía.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    print(f"Leyendo data real desde: {ruta_origen}")
    
    # 2. Leer el CSV con tolerancia a codificaciones de sistemas de salud
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
        print("Error: No se pudo leer o estructurar el CSV.")
        return

    # 3. Estandarizar cabeceras a mayúsculas para evitar fallos de tipeo
    df.columns = [str(col).strip().upper() for col in df.columns]

    # 4. Mapeo inteligente de las columnas necesarias para tu consulta SQL
    col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c), None)
    col_vlab = next((c for c in df.columns if 'VALOR_LAB' in c or 'VALOR' in c), None)
    col_item = next((c for c in df.columns if 'CODIGO_ITEM' in c or 'ITEM' in c or 'COD_ITEM' in c), None)
    col_corr = next((c for c in df.columns if 'ID_CORRELATIVO_LAB' in c or 'CORRELATIVO' in c or 'ID_CORREL' in c), None)
    col_edad = next((c for c in df.columns if 'ANIO_ACTUAL_PACIENTE' in c or 'EDAD' in c or 'ANIO_ACTUAL' in c), None)
    col_cita = next((c for c in df.columns if 'ID_CITA' in c or 'CITA' in c), None)

    # Validar que existan los campos mínimos para operar el WHERE y el SELECT
    if not all([col_fecha, col_vlab, col_item, col_corr, col_edad]):
        print(f"Error: Faltan columnas críticas en el CSV. Detectadas: {list(df.columns)}")
        return

    # Renombrar temporalmente para trabajar con nombres limpios idénticos a tu SQL
    df = df.rename(columns={
        col_fecha: 'FECHA_ATENCION',
        col_vlab: 'VALOR_LAB',
        col_item: 'CODIGO_ITEM',
        col_corr: 'ID_CORRELATIVO_LAB',
        col_edad: 'ANIO_ACTUAL_PACIENTE',
        col_cita: 'ID_CITA' if col_cita else 'FECHA_ATENCION' # Si no hay ID_CITA, usamos la fecha como fallback para contar
    })

    # 5. Aplicar la cláusula WHERE: codigo_item = '99801' AND Id_Correlativo_Lab = 1
    df['CODIGO_ITEM'] = df['CODIGO_ITEM'].astype(str).str.strip()
    df['ID_CORRELATIVO_LAB'] = pd.to_numeric(df['ID_CORRELATIVO_LAB'], errors='coerce').fillna(0).astype(int)
    
    df_filtrado = df[(df['CODIGO_ITEM'] == '99801') & (df['ID_CORRELATIVO_LAB'] == 1)].copy()

    print(f"Filas que cumplen el WHERE (99801 y Correlativo=1): {len(df_filtrado)}")

    if df_filtrado.empty:
        print("Aviso: Ningún registro cumple con los filtros WHERE del SQL. Archivo de salida quedará vacío.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    # Limpiar formato de la Fecha_Atencion (eliminar horas si las hay: YYYY-MM-DD)
    df_filtrado['FECHA_ATENCION'] = df_filtrado['FECHA_ATENCION'].astype(str).str.split(' ').str[0]
    
    # Estandarizar la columna de edad a números enteros
    df_filtrado['ANIO_ACTUAL_PACIENTE'] = pd.to_numeric(df_filtrado['ANIO_ACTUAL_PACIENTE'], errors='coerce').fillna(-1).astype(int)

    # 6. Replicar los COUNT(CASE WHEN...) evaluando las edades condicionalmente
    # Si id_cita es nulo en esa fila, el CASE WHEN de SQL no lo contaría, replicamos esa lógica con .notna()
    valido = df_filtrado['ID_CITA'].notna()

    df_filtrado['NIÑO'] = ((df_filtrado['ANIO_ACTUAL_PACIENTE'] >= 0) & (df_filtrado['ANIO_ACTUAL_PACIENTE'] <= 11) & valido).astype(int)
    df_filtrado['ADOLESCENTE'] = ((df_filtrado['ANIO_ACTUAL_PACIENTE'] >= 12) & (df_filtrado['ANIO_ACTUAL_PACIENTE'] <= 17) & valido).astype(int)
    df_filtrado['JOVEN'] = ((df_filtrado['ANIO_ACTUAL_PACIENTE'] >= 18) & (df_filtrado['ANIO_ACTUAL_PACIENTE'] <= 29) & valido).astype(int)
    df_filtrado['ADULTO'] = ((df_filtrado['ANIO_ACTUAL_PACIENTE'] >= 30) & (df_filtrado['ANIO_ACTUAL_PACIENTE'] <= 59) & valido).astype(int)
    df_filtrado['ADULTO MAYOR'] = ((df_filtrado['ANIO_ACTUAL_PACIENTE'] > 59) & valido).astype(int)

    # 7. Aplicar el GROUP BY FECHA_ATENCION, VALOR_LAB sumando los contadores calculados
    grupos_etarios = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    df_consolidado = df_filtrado.groupby(['FECHA_ATENCION', 'VALOR_LAB'])[grupos_etarios].sum().reset_index()

    # 8. Replicar el ORDER BY FECHA_ATENCION ASC
    df_consolidado = df_consolidado.sort_values(by='FECHA_ATENCION', ascending=True)

    # 9. Renombrar las columnas finales para mantener compatibilidad estricta con tu Front-End (HTML/JS)
    df_consolidado = df_consolidado.rename(columns={
        'FECHA_ATENCION': 'Fecha_Atencion',
        'VALOR_LAB': 'Valor_Lab'
    })

    # Guardar el CSV final para producción
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento SQL-Equivalente Exitoso! Generadas {len(df_consolidado)} filas agrupadas.")

if __name__ == "__main__":
    procesar_informacion_his()
