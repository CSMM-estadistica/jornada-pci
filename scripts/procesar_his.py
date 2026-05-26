import pandas as pd
import os

def procesar_informacion_his():
    ruta_origen = 'data/his_raw.csv'
    ruta_destino = 'data/data_jornada.csv'
    
    if not os.path.exists(ruta_origen):
        print("Aviso: No se detectó un archivo nuevo en 'data/his_raw.csv'.")
        return

    print("Iniciando consolidación adaptativa de etapas de vida...")
    
    # 1. Leer el CSV detectando el separador automáticamente (soportando UTF-8 y Latin-1)
    try:
        df = pd.read_csv(ruta_origen, sep=';', encoding='utf-8')
    except Exception:
        try:
            df = pd.read_csv(ruta_origen, sep=',', encoding='utf-8')
        except Exception:
            df = pd.read_csv(ruta_origen, sep=None, engine='python', encoding='latin-1')
    
    # Limpiar espacios rebeldes en las cabeceras y pasarlo a mayúsculas string limpias
    df.columns = [str(col).strip().upper() for col in df.columns]
    
    # 2. Identificación dinámica de columnas para evitar fallos por tildes, eñes o espacios
    col_fecha = None
    col_lab = None
    col_niño = None
    col_adolescente = None
    col_joven = None
    col_adulto = None
    col_mayor = None

    for col in df.columns:
        if 'FECHA' in col: col_fecha = col
        elif 'LAB' in col: col_lab = col
        elif 'NIÑ' in col: col_niño = col
        elif 'ADOLE' in col: col_adolescente = col
        elif 'JOV' in col: col_joven = col
        elif 'MAYOR' in col: col_mayor = col
        elif 'ADULT' in col and 'MAYOR' not in col: col_adulto = col

    # Validar que al menos las columnas de control existan
    if not col_fecha or not col_lab:
        print(f"Error Crítico: No se encontraron las columnas de Fecha o Valor_Lab. Cabeceras reales: {list(df.columns)}")
        return

    # 3. Forzar el renombrado estandarizado para que el HTML reciba exactamente lo que espera
    mapeo = {col_fecha: 'Fecha_Atencion', col_lab: 'Valor_Lab'}
    if col_niño: mapeo[col_niño] = 'NIÑO'
    if col_adolescente: mapeo[col_adolescente] = 'ADOLESCENTE'
    if col_joven: mapeo[col_joven] = 'JOVEN'
    if col_adulto: mapeo[col_adulto] = 'ADULTO'
    if col_mayor: mapeo[col_mayor] = 'ADULTO MAYOR'
    
    df.rename(columns=mapeo, inplace=True)

    # 4. Limpieza y filtrado estricto por valores permitidos ('1' o 'TA')
    df['Valor_Lab'] = df['Valor_Lab'].astype(str).str.strip()
    df = df[df['Valor_Lab'].isin(['1', 'TA'])]

    if df.empty:
        print("Aviso: No se encontraron registros con Valor_Lab = '1' o 'TA'. El archivo quedará intacto.")
        return

    # 5. Asegurar y forzar que los grupos etarios sean números enteros perfectos
    grupos_finales = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    for g in grupos_finales:
        if g in df.columns:
            df[g] = pd.to_numeric(df[g], errors='coerce').fillna(0).astype(int)
        else:
            df[g] = 0
            
    # Limpiar la fecha de atención retirando horas (se queda en YYYY-MM-DD)
    df['Fecha_Atencion'] = df['Fecha_Atencion'].astype(str).str.split(' ').str[0]
    
    # 6. Agrupación final masiva para consolidar las filas del personal
    df_consolidado = df.groupby(['Fecha_Atencion', 'Valor_Lab'])[grupos_finales].sum().reset_index()
    
    # 7. Sobrescribir el archivo de producción forzando el formato estándar de comas
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Éxito Absoluto! Se reescribió data_jornada.csv con {len(df_consolidado)} filas consolidadas.")

if __name__ == "__main__":
    procesar_informacion_his()
