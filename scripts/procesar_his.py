import pandas as pd
import os

def procesar_informacion_his():
    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv']
    ruta_origen = None
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break
            
    ruta_destino = 'data/data_jornada.csv'
    
    if not ruta_origen:
        print("Error: No se encontró 'his_raw.csv'.")
        return

    print(f"Procesando archivo desde: {ruta_origen}")
    
    encodings_to_try = ['latin-1', 'utf-8', 'utf-8-sig', 'cp1252']
    df = None
    
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(ruta_origen, sep=';', encoding=enc)
            if len(df.columns) > 2: break
        except Exception:
            try:
                df = pd.read_csv(ruta_origen, sep=',', encoding=enc)
                if len(df.columns) > 2: break
            except Exception:
                continue

    if df is None or df.empty:
        print("Error Crítico: No se pudo leer el archivo con ninguna configuración.")
        return

    # Limpieza absoluta de cabeceras
    df.columns = [str(col).strip().upper() for col in df.columns]
    print(f"Cabeceras procesadas en el pipeline: {list(df.columns)}")

    # Mapeo por palabras clave ultra-flexible (Sintaxis corregida aquí)
    col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c or 'FEC' in c), None)
    col_lab = next((c for c in df.columns if 'LAB' in c or 'CORREL' in c), None)
    
    col_niño = next((c for c in df.columns if 'NIÑ' in c or 'NIN' in c or 'HIJO' in c), None)
    col_ado = next((c for c in df.columns if 'ADOLE' in c or 'ADOL' in c), None)
    col_jov = next((c for c in df.columns if 'JOV' in c), None)
    col_adu = next((c for c in df.columns if 'ADULT' in c and 'MAYOR' not in c), None)
    col_may = next((c for c in df.columns if 'MAYOR' in c or '60' in c or 'ANCIAN' in c), None)

    if not col_fecha:
        col_fecha = df.columns[2] if len(df.columns) > 2 else df.columns[0]
    
    if not col_lab:
        col_lab = next((c for c in df.columns if 'VALOR' in c or 'ITEM' in c), df.columns[1])

    # Renombrar al estándar del HTML
    mapeo = {col_fecha: 'Fecha_Atencion'}
    if col_lab: mapeo[col_lab] = 'Valor_Lab'
    if col_niño: mapeo[col_niño] = 'NIÑO'
    if col_ado: mapeo[col_ado] = 'ADOLESCENTE'
    if col_jov: mapeo[col_jov] = 'JOVEN'
    if col_adu: mapeo[col_adu] = 'ADULTO'
    if col_may: mapeo[col_may] = 'ADULTO MAYOR'
    
    df.rename(columns=mapeo, inplace=True)

    # Inicializar o limpiar la columna de control
    if 'Valor_Lab' not in df.columns:
        df['Valor_Lab'] = '1'
    else:
        df['Valor_Lab'] = df['Valor_Lab'].astype(str).str.strip().upper()
        df_filtrado = df[df['Valor_Lab'].isin(['1', 'TA', '1.0'])]
        if not df_filtrado.empty:
            df = df_filtrado

    # Estandarizar valores numéricos a enteros
    grupos_finales = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    for g in grupos_finales:
        if g in df.columns:
            df[g] = pd.to_numeric(df[g], errors='coerce').fillna(0).astype(int)
        else:
            df[g] = 0

    # Limpiar formato de fecha
    df['Fecha_Atencion'] = df['Fecha_Atencion'].astype(str).str.split(' ').str[0]

    # Consolidar (Agrupar)
    df_consolidado = df.groupby(['Fecha_Atencion', 'Valor_Lab'])[grupos_finales].sum().reset_index()

    # Forzar la escritura
    os.makedirs('data', exist_ok=True)
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Sincronización Forzada Exitosa! {len(df_consolidado)} filas listas.")

if __name__ == "__main__":
    procesar_informacion_his()
