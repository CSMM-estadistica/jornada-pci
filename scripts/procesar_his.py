import pandas as pd
import os

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    os.makedirs('data', exist_ok=True)
    
    # 1. Ubicar archivo de origen
    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv']
    ruta_origen = None
    for r in posibles_rutas:
        if os.path.exists(r):
            ruta_origen = r
            break
            
    if not ruta_origen:
        print("AVISO: No se encontró 'his_raw.csv'. Generando base vacía.")
        pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']).to_csv(ruta_destino, index=False)
        return

    print(f"Leyendo archivo desde: {ruta_origen}")
    
    # 2. Leer con separadores comunes (Tolerancia total)
    df = None
    for encoding_v in ['latin-1', 'utf-8', 'utf-8-sig', 'cp1252']:
        for separador in [';', ',']:
            try:
                df = pd.read_csv(ruta_origen, sep=separador, encoding=encoding_v, low_memory=False)
                if len(df.columns) > 3:
                    print(f"Éxito leyendo con separador '{separador}' y encoding '{encoding_v}'")
                    break
            except Exception:
                continue
        if df is not None and len(df.columns) > 3:
            break

    if df is None or df.empty:
        print("Error Crítico: No se pudo estructurar el CSV.")
        return

    # Limpiar y estandarizar nombres de columnas a Mayúsculas sin espacios
    df.columns = [str(col).strip().upper() for col in df.columns]
    print(f"Columnas encontradas en tu CSV: {list(df.columns)}")

    # 3. Búsqueda Ultra-Flexible de Columnas por palabras clave (Keywords)
    col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c or 'FEC_AT' in c), None)
    col_vlab = next((c for c in df.columns if 'VALOR_LAB' in c or 'VALOR' in c or 'V_LAB' in c), None)
    col_item = next((c for c in df.columns if 'ITEM' in c or 'COD_IT' in c or 'PRESTACION' in c), None)
    col_corr = next((c for c in df.columns if 'CORRELATIVO' in c or 'NUM_LAB' in c or 'ID_CORREL' in c), None)
    col_edad = next((c for c in df.columns if 'ANIO_ACTUAL' in c or 'EDAD' in c or 'ANIO_PAC' in c or 'AÑO' in c), None)
    col_cita = next((c for c in df.columns if 'CITA' in c or 'ID_CITA' in c), None)

    # Fallbacks posicionales extremos en caso de que los nombres difieran completamente
    if not col_fecha: col_fecha = df.columns[0]
    if not col_item: col_item = next((c for c in df.columns if 'COD' in c), df.columns[1])
    if not col_vlab: col_vlab = next((c for c in df.columns if 'LAB' in c and 'CORR' not in c), df.columns[2])
    if not col_corr: col_corr = next((c for c in df.columns if 'CORR' in c or 'NUM' in c), df.columns[3])
    if not col_edad: col_edad = next((c for c in df.columns if 'EDAD' in c or 'ANIO' in c or 'AÑO' in c), df.columns[4])

    print(f"Mapeo adoptado -> Fecha: {col_fecha}, Item: {col_item}, Valor_Lab: {col_vlab}, Correlativo: {col_corr}, Edad: {col_edad}")

    # 4. Homologación forzada de tipos de datos (Evita colapsos de Pandas)
    df['FECHA_LIMPIA'] = df[col_fecha].astype(str).str.strip().str.split(' ').str[0]
    df['ITEM_LIMPIO'] = df[col_item].astype(str).str.strip()
    df['VLAB_LIMPIO'] = df[col_vlab].astype(str).str.strip().upper()
    
    # Conversión numérica ultra-segura a prueba de errores
    df['CORR_LIMPIO'] = pd.to_numeric(df[col_corr], errors='coerce').fillna(0).astype(int)
    df['EDAD_LIMPIA'] = pd.to_numeric(df[col_edad], errors='coerce').fillna(-1).astype(int)

    # Verificar si el ID_CITA es nulo o vacío (Cláusula COUNT de tu SQL)
    if col_cita:
        df['CITA_VALIDA'] = df[col_cita].notna() & (df[col_cita].astype(str).str.strip() != '')
    else:
        df['CITA_VALIDA'] = True

    # 5. Aplicar Filtro WHERE equivalente: codigo_item = '99801' AND Id_Correlativo_Lab = 1
    df_filtrado = df[(df['ITEM_LIMPIO'] == '99801') & (df['CORR_LIMPIO'] == 1)].copy()
    print(f"Registros que pasaron el filtro WHERE (99801 + Correlativo 1): {len(df_filtrado)}")

    if df_filtrado.empty:
        print("Aviso: Ningún registro coincide con los filtros. Generando reporte vacío compatible.")
        pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']).to_csv(ruta_destino, index=False)
        return

    # 6. Replicar la matriz condicional de los COUNT(CASE WHEN...) usando vectores numéricos estables
    edad = df_filtrado['EDAD_LIMPIA']
    valido = df_filtrado['CITA_VALIDA']

    df_filtrado['NIÑO'] = ((edad >= 0) & (edad <= 11) & valido).astype(int)
    df_filtrado['ADOLESCENTE'] = ((edad >= 12) & (edad <= 17) & valido).astype(int)
    df_filtrado['JOVEN'] = ((edad >= 18) & (edad <= 29) & valido).astype(int)
    df_filtrado['ADULTO'] = ((edad >= 30) & (edad <= 59) & valido).astype(int)
    df_filtrado['ADULTO MAYOR'] = ((edad > 59) & valido).astype(int)

    # 7. GROUP BY FECHA_ATENCION, VALOR_LAB y ORDER BY FECHA_ATENCION ASC
    grupos_etarios = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    df_consolidado = df_filtrado.groupby(['FECHA_LIMPIA', 'VLAB_LIMPIO'])[grupos_etarios].sum().reset_index()
    
    # Ordenar cronológicamente de forma ascendente
    df_consolidado = df_consolidado.sort_values(by='FECHA_LIMPIA', ascending=True)

    # 8. Renombrar campos finales para alimentar correctamente tu index.html
    df_consolidado = df_consolidado.rename(columns={
        'FECHA_LIMPIA': 'Fecha_Atencion',
        'VLAB_LIMPIO': 'Valor_Lab'
    })

    # Guardar reporte unificado
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento Completado con Éxito! {len(df_consolidado)} filas consolidadas.")

if __name__ == "__main__":
    procesar_informacion_his()
