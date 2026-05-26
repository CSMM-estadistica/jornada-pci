import pandas as pd
import os

def procesar_informacion_his():
    # El archivo plano pesado que se descargará del HISMINSA
    ruta_origen = 'data/his_raw.csv'
    # El archivo limpio final procesado que consumirá el HTML
    ruta_destino = 'data/data_jornada.csv'
    
    if not os.path.exists(ruta_origen):
        print("Aviso: No se detectó un archivo nuevo en 'data/his_raw.csv'. Manteniendo la base de datos estática actual.")
        return

    print("Iniciando el procesamiento analítico del archivo plano HISMINSA...")
    
    # 1. Carga inteligente de la trama (MINSA suele exportar separado por comas o punto y coma)
    try:
        df = pd.read_csv(ruta_origen, sep=';', dtype={'Codigo_Item': str, 'Valor_Lab': str})
    except Exception:
        df = pd.read_csv(ruta_origen, sep=',', dtype={'Codigo_Item': str, 'Valor_Lab': str})
    
    # 2. Limpieza de espacios en los nombres de las columnas
    df.columns = [col.strip() for col in df.columns]
    
    # 3. Filtrado estricto por valores de control sanitario (Plan Inicio: 1, Plan Término: TA)
    df = df[df['Valor_Lab'].str.strip().isin(['1', 'TA'])]
    
    # 4. Asegurar que las columnas etarias sean tratadas como enteros numéricos
    grupos_etarios = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    for grupo in grupos_etarios:
        if grupo in df.columns:
            df[grupo] = pd.to_numeric(df[grupo], errors='coerce').fillna(0).astype(int)
        else:
            df[grupo] = 0
            
    # 5. Agrupación y compactación masiva por fecha y tipo de plan
    df_agrupado = df.groupby(['Fecha_Atencion', 'Valor_Lab'])[grupos_etarios].sum().reset_index()
    
    # 6. Sobrescribir la base de datos estática
    df_agrupado.to_csv(ruta_destino, index=False)
    print(f"Procesamiento exitoso. Se generaron {len(df_agrupado)} registros consolidados para producción.")

if __name__ == "__main__":
    procesar_informacion_his()
