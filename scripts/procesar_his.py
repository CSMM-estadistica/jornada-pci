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

    # Forzar la lectura con separador por coma basado en lo visto en el log
    df = None
    try:
        df = pd.read_csv(ruta_origen, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
    except Exception:
        try:
            df = pd.read_csv(ruta_origen, sep=',', encoding='latin-1', on_bad_lines='skip')
        except Exception as e:
            print(f"Error crítico al leer el archivo: {e}")
            return

    if df is None or df.empty:
        print("Error: No se pudo procesar la estructura del CSV.")
        return

    # Normalización radical de cabeceras
    df.columns = [str(col).encode('utf-8', 'ignore').decode('utf-8-sig').strip().upper() for col in df.columns]
    
    # Mapeo por palabras clave basándonos en la lista real del sistema
    col_item = 'CODIGO_ITEM' if 'CODIGO_ITEM' in df.columns else None
    col_corr = 'ID_CORRELATIVO_LAB' if 'ID_CORRELATIVO_LAB' in df.columns else None
    col_fecha = 'FECHA_ATENCION' if 'FECHA_ATENCION' in df.columns else None
    col_vlab = 'VALOR_LAB' if 'VALOR_LAB' in df.columns else None
    col_edad = 'ANIO_ACTUAL_PACIENTE' if 'ANIO_ACTUAL_PACIENTE' in df.columns else None

    # Fallbacks si por estructura compacta fallan las cadenas exactas
    if not col_item: col_item = next((c for c in df.columns if 'ITEM' in c or 'COD' in c), df.columns[22] if len(df.columns) > 22 else df.columns[0])
    if not col_corr: col_corr = next((c for c in df.columns if 'LAB' in c and 'CORR' in c), df.columns[26] if len(df.columns) > 26 else df.columns[0])
    if not col_fecha: col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c), df.columns[4] if len(df.columns) > 4 else df.columns[0])
    if not col_vlab: col_vlab = next((c for c in df.columns if 'VALOR' in c or 'LAB' in c), df.columns[24] if len(df.columns) > 24 else df.columns[0])
    if not col_edad: col_edad = next((c for c in df.columns if 'ANIO_ACTUAL' in c or 'EDAD' in c), df.columns[18] if len(df.columns) > 18 else df.columns[0])

    print(f"Mapeo indexado -> Item: {col_item} | Fecha: {col_fecha} | Valor Lab: {col_vlab} | Edad: {col_edad}")

    # Convertir a string y limpiar espacios
    df[col_item] = df[col_item].astype(str).str.strip()

    # Filtro de búsqueda parcial (Captura el código limpio)
    df_filtrado = df[df[col_item].str.contains('99801', na=False)].copy()
    print(f"Filas encontradas que contienen '99801': {len(df_filtrado)}")

    if df_filtrado.empty:
        print("AVISO: Ninguna fila coincide con el código '99801'. Generando archivo de contingencia.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    # Limpieza de tipos de datos sobre el DataFrame filtrado (CORRECCIÓN .str.upper())
    df_filtrado[col_edad] = pd.to_numeric(df_filtrado[col_edad], errors='coerce').fillna(-1).astype(int)
    df_filtrado[col_fecha] = df_filtrado[col_fecha].astype(str).str.strip().str.split(' ').str[0]
    df_filtrado[col_vlab] = df_filtrado[col_vlab].astype(str).str.strip().str.upper()

    # Banderas vectoriales de etapas de vida
    df_filtrado['NIÑO']         = df_filtrado[col_edad].between(0, 11).astype(int)
    df_filtrado['ADOLESCENTE']  = df_filtrado[col_edad].between(12, 17).astype(int)
    df_filtrado['JOVEN']        = df_filtrado[col_edad].between(18, 29).astype(int)
    df_filtrado['ADULTO']       = df_filtrado[col_edad].between(30, 59).astype(int)
    df_filtrado['ADULTO MAYOR'] = (df_filtrado[col_edad] > 59).astype(int)

    # Agrupación y suma plana de contadores
    df_consolidado = df_filtrado.groupby([col_fecha, col_vlab])[
        ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    ].sum().reset_index()

    # Renombrar para persistencia en el index.html
    df_consolidado.rename(columns={col_fecha: 'Fecha_Atencion', col_vlab: 'Valor_Lab'}, inplace=True)
    df_consolidado.sort_values('Fecha_Atencion', ascending=True, inplace=True)

    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento exitoso! {len(df_consolidado)} filas consolidadas guardadas en '{ruta_destino}'.")

if __name__ == "__main__":
    procesar_informacion_his()
