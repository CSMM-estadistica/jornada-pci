import pandas as pd
import os

def procesar_informacion_his():
    # 1. Buscar el archivo donde sea que se haya subido (Raíz o carpeta data/)
    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv']
    ruta_origen = None
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break
            
    ruta_destino = 'data/data_jornada.csv'
    
    if not ruta_origen:
        print("Error: No se encontró el archivo 'his_raw.csv' ni en la raíz ni en 'data/'.")
        return

    print(f"Leyendo archivo detectado en: {ruta_origen}")
    
    # 2. Carga del archivo con codificación tolerante a la 'Ñ' de los sistemas de salud peruanos
    try:
        df = pd.read_csv(ruta_origen, sep=';', encoding='latin-1')
    except Exception:
        try:
            df = pd.read_csv(ruta_origen, sep=',', encoding='latin-1')
        except Exception:
            df = pd.read_csv(ruta_origen, sep=None, engine='python', encoding='utf-8-sig')

    # Limpiar espacios rebeldes en los nombres de las columnas y pasarlas a mayúsculas puras
    df.columns = [str(col).strip().upper() for col in df.columns]
    print(f"Columnas detectadas en tu Excel: {list(df.columns)}")

    # 3. Mapeo inteligente por aproximación de texto (así evitamos problemas de tildes o eñes)
    col_fecha = None
    col_lab = None
    col_niño = None
    col_adolescente = None
    col_joven = None
    col_adulto = None
    col_mayor = None

    for col in df.columns:
        if 'FECHA' in col or 'ATENCION' in col: col_fecha = col
        elif 'LAB' in col: col_lab = col
        elif 'NIÑ' in col: col_niño = col
        elif 'ADOLE' in col: col_adolescente = col
        elif 'JOV' in col: col_joven = col
        elif 'MAYOR' in col: col_mayor = col
        elif 'ADULT' in col and 'MAYOR' not in col: col_adulto = col

    # Validación crítica de control
    if not col_fecha or not col_lab:
        print("Error: Columnas de control 'Fecha_Atencion' o 'Valor_Lab' no identificadas.")
        return

    # Renombrar dinámicamente al formato estricto que requiere tu HTML
    mapeo = {col_fecha: 'Fecha_Atencion', col_lab: 'Valor_Lab'}
    if col_niño: mapeo[col_niño] = 'NIÑO'
    if col_adolescente: mapeo[col_adolescente] = 'ADOLESCENTE'
    if col_joven: mapeo[col_joven] = 'JOVEN'
    if col_adulto: mapeo[col_adulto] = 'ADULTO'
    if col_mayor: mapeo[col_mayor] = 'ADULTO MAYOR'
    
    df.rename(columns=mapeo, inplace=True)

    # 4. Filtrado estricto de atenciones (Plan Inicio = 1, Plan Término = TA)
    df['Valor_Lab'] = df['Valor_Lab'].astype(str).str.strip().upper()
    df = df[df['Valor_Lab'].isin(['1', 'TA'])]

    if df.empty:
        print("Aviso: No quedaron filas tras filtrar por Valor_Lab ('1' o 'TA'). Checkea los valores de tu Excel.")
        return

    # 5. Estandarizar valores numéricos de las etapas de vida
    grupos_finales = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    for g in grupos_finales:
        if g in df.columns:
            df[g] = pd.to_numeric(df[g], errors='coerce').fillna(0).astype(int)
        else:
            df[g] = 0

    # Extraer solo la fecha limpia YYYY-MM-DD (descartando la hora si existiera)
    df['Fecha_Atencion'] = df['Fecha_Atencion'].astype(str).str.split(' ').str[0]

    # 6. Agrupación masiva (Consolidación)
    df_consolidado = df.groupby(['Fecha_Atencion', 'Valor_Lab'])[grupos_finales].sum().reset_index()

    # 7. Guardado seguro en la carpeta de producción
    os.makedirs('data', exist_ok=True) # Asegura que la carpeta data exista
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Éxito Absoluto! data_jornada.csv actualizado con {len(df_consolidado)} registros consolidados.")

if __name__ == "__main__":
    procesar_informacion_his()
