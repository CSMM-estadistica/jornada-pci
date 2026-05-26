import pandas as pd
import os

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    os.makedirs('data', exist_ok=True)
    
    # Listar los archivos para el log de GitHub Actions
    print("Archivos presentes en la raíz del repositorio:", os.listdir('.'))
    if os.path.exists('data'):
        print("Archivos presentes en la carpeta 'data/':", os.listdir('data'))

    # Buscar el archivo en cualquier ubicación o variante de nombre
    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv', 'his_raw.csv.csv']
    ruta_origen = None
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break
            
    if not ruta_origen:
        print("AVISO: No se encontró el archivo 'his_raw.csv'. Generando estructura base vacía de contingencia.")
        # Generamos un archivo base para que el HTML no se rompa mientras subes el archivo correcto
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    print(f"Procesando archivo detectado desde: {ruta_origen}")
    
    # Intentar leer con codificaciones estándar
    try:
        df = pd.read_csv(ruta_origen, sep=';', encoding='latin-1')
    except Exception:
        try:
            df = pd.read_csv(ruta_origen, sep=',', encoding='latin-1')
        except Exception:
            print("Error: No se pudo procesar la estructura del CSV.")
            return

    # Limpieza absoluta de cabeceras
    df.columns = [str(col).strip().upper() for col in df.columns]

    # Mapeo por palabras clave
    col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c), df.columns[0])
    col_lab = next((c for c in df.columns if 'LAB' in c or 'VALOR' in c), None)
    
    col_niño = next((c for c in df.columns if 'NIÑ' in c or 'NIN' in c), None)
    col_ado = next((c for c in df.columns if 'ADOLE' in c or 'ADOL' in c), None)
    col_jov = next((c for c in df.columns if 'JOV' in c), None)
    col_adu = next((c for c in df.columns if 'ADULT' in c and 'MAYOR' not in c), None)
    col_may = next((c for c in df.columns if 'MAYOR' in c or '60' in c), None)

    # Renombrar al estándar del HTML
    mapeo = {col_fecha: 'Fecha_Atencion'}
    if col_lab: mapeo[col_lab] = 'Valor_Lab'
    if col_niño: mapeo[col_niño] = 'NIÑO'
    if col_ado: mapeo[col_ado] = 'ADOLESCENTE'
    if col_jov: mapeo[col_jov] = 'JOVEN'
    if col_adu: mapeo[col_adu] = 'ADULTO'
    if col_may: mapeo[col_may] = 'ADULTO MAYOR'
    
    df.rename(columns=mapeo, inplace=True)

    if 'Valor_Lab' not in df.columns:
        df['Valor_Lab'] = '1'

    grupos_finales = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    for g in grupos_finales:
        if g in df.columns:
            df[g] = pd.to_numeric(df[g], errors='coerce').fillna(0).astype(int)
        else:
            df[g] = 0

    df['Fecha_Atencion'] = df['Fecha_Atencion'].astype(str).str.split(' ').str[0]
    df_consolidado = df.groupby(['Fecha_Atencion', 'Valor_Lab'])[grupos_finales].sum().reset_index()

    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento exitoso! {len(df_consolidado)} filas consolidadas.")

if __name__ == "__main__":
    procesar_informacion_his()
