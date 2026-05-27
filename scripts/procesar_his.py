import pandas as pd
import os

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    os.makedirs('data', exist_ok=True)

    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv', 'his_raw.csv.csv']
    ruta_origen = None

    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break

    if not ruta_origen:
        print("AVISO: No se encontró el archivo 'his_raw.csv'.")
        return

    print(f"Procesando archivo detectado desde: {ruta_origen}")

    # Intentar leer con diferentes separadores
    df = None
    for separador in [';', ',']:
        try:
            df = pd.read_csv(ruta_origen, sep=separador, encoding='utf-8-sig')
            if df is not None and len(df.columns) > 1:
                break
        except Exception:
            try:
                df = pd.read_csv(ruta_origen, sep=separador, encoding='latin-1')
                if df is not None and len(df.columns) > 1:
                    break
            except Exception:
                continue

    if df is None or df.empty:
        print("Error: No se pudo procesar la estructura del CSV.")
        return

    # Normalización radical de cabeceras
    df.columns = [str(col).encode('utf-8', 'ignore').decode('utf-8-sig').strip().upper() for col in df.columns]
    print("--- DETECCIÓN DE COLUMNAS DISPONIBLES ---")
    print(list(df.columns))

    # Mapeo por palabras clave
    mapeo_columnas = {
        'ITEM': ['CODIGO_ITEM', 'COD_ITEM', 'ITEM', 'CODIGO', 'PRESTACION'],
        'CORRELATIVO': ['ID_CORRELATIVO_LAB', 'ID_CORRELATIVO', 'CORRELATIVO', 'NUM_LAB', 'NRO_LAB', 'VALOR_LAB'],
        'FECHA': ['FECHA_ATENCION', 'FECHA', 'FEC_ATENC', 'ATENCION'],
        'VALOR': ['VALOR_LAB', 'VALOR', 'LAB', 'RESULTADO'],
        'EDAD': ['ANIO_ACTUAL_PACIENTE', 'ANIO_ACTUAL', 'EDAD', 'EDAD_PACIENTE', 'AÑO', 'ANIO'],
        'CITA': ['ID_CITA', 'CITA', 'ID', 'IDENTIFICADOR']
    }

    columnas_identificadas = {}
    for clave, alternativas in mapeo_columnas.items():
        coincidencia = next((c for c in df.columns if any(alt in c for alt in alternativas)), df.columns[0])
        columnas_identificadas[clave] = coincidencia

    col_item = columnas_identificadas['ITEM']
    col_corr = columnas_identificadas['CORRELATIVO']
    col_fecha = columnas_identificadas['FECHA']
    col_vlab = columnas_identificadas['VALOR']
    col_edad = columnas_identificadas['EDAD']

    # --- DIAGNÓSTICO EN CONSOLA ---
    print("\n--- VALORES DE MUESTRA EN LA COLUMNA DE ÍTEMS ---")
    print(df[col_item].dropna().astype(str).unique()[:10])

    # Convertir a string y limpiar espacios
    df[col_item] = df[col_item].astype(str).str.strip()

    # Filtro de búsqueda parcial (Captura '99801', '99801.0', o si viene con texto)
    df_filtrado = df[df[col_item].str.contains('99801', na=False)].copy()
    print(f"\nFilas encontradas que contienen '99801': {len(df_filtrado)}")

    if df_filtrado.empty:
        print("CRÍTICO: No se encontró el código 99801 bajo ninguna forma. Revisa la muestra de arriba.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    # Limpieza de tipos de datos
    df_filtrado[col_edad] = pd.to_numeric(df_filtrado[col_edad], errors='coerce').fillna(-1).astype(int)
    df_filtrado[col_fecha] = df_filtrado[col_fecha].astype(str).str.strip().str.split(' ').str[0]
    df_filtrado[col_vlab] = df_filtrado[col_vlab].astype(str).str.strip().upper()

    # Banderas de etapas de vida
    df_filtrado['NIÑO']         = df_filtrado[col_edad].between(0, 11).astype(int)
    df_filtrado['ADOLESCENTE']  = df_filtrado[col_edad].between(12, 17).astype(int)
    df_filtrado['JOVEN']        = df_filtrado[col_edad].between(18, 29).astype(int)
    df_filtrado['ADULTO']       = df_filtrado[col_edad].between(30, 59).astype(int)
    df_filtrado['ADULTO MAYOR'] = (df_filtrado[col_edad] > 59).astype(int)

    # Agrupación plana
    df_consolidado = df_filtrado.groupby([col_fecha, col_vlab])[
        ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    ].sum().reset_index()

    df_consolidado.rename(columns={col_fecha: 'Fecha_Atencion', col_vlab: 'Valor_Lab'}, inplace=True)
    df_consolidado.sort_values('Fecha_Atencion', ascending=True, inplace=True)

    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento exitoso! {len(df_consolidado)} filas consolidadas guardadas.")

if __name__ == "__main__":
    procesar_informacion_his()
