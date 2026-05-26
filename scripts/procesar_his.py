import pandas as pd
import os

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    os.makedirs('data', exist_ok=True)

    print("Archivos presentes en la raíz del repositorio:", os.listdir('.'))
    if os.path.exists('data'):
        print("Archivos presentes en la carpeta 'data/':", os.listdir('data'))

    posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv', 'his_raw.csv.csv']
    ruta_origen = None

    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_origen = ruta
            break

    if not ruta_origen:
        print("AVISO: No se encontró el archivo 'his_raw.csv'. Generando estructura base vacía de contingencia.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    print(f"Procesando archivo detectado desde: {ruta_origen}")

    try:
        df = pd.read_csv(ruta_origen, sep=';', encoding='latin-1')
    except Exception:
        try:
            df = pd.read_csv(ruta_origen, sep=',', encoding='latin-1')
        except Exception:
            print("Error: No se pudo procesar la estructura del CSV.")
            return

    # Normalizar cabeceras
    df.columns = [str(col).strip() for col in df.columns]

    # ── Filtros equivalentes al WHERE de tu SQL ──────────────────────────────
    # WHERE Codigo_Item = '99801' AND Id_Correlativo_Lab = 1
    df = df[
        (df['Codigo_Item'].astype(str).str.strip() == '99801') &
        (pd.to_numeric(df['Id_Correlativo_Lab'], errors='coerce') == 1)
    ]

    if df.empty:
        print("AVISO: Ninguna fila cumple los filtros (Codigo_Item='99801' AND Id_Correlativo_Lab=1). Generando archivo vacío.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    # Asegurar tipos correctos
    df['Anio_Actual_Paciente'] = pd.to_numeric(df['Anio_Actual_Paciente'], errors='coerce')
    df['Fecha_Atencion'] = df['Fecha_Atencion'].astype(str).str.split(' ').str[0]
    df['Valor_Lab'] = df['Valor_Lab'].astype(str).str.strip()

    # ── COUNT(CASE WHEN ... THEN id_cita END) equivalente ────────────────────
    # pandas: para cada grupo contar Id_Cita solo donde se cumple el rango de edad
    def contar_rango(serie_edad, serie_id, edad_min, edad_max):
        mascara = serie_edad.between(edad_min, edad_max)
        return serie_id.where(mascara).notna().groupby(serie_edad.index).sum()

    grupos = ['Fecha_Atencion', 'Valor_Lab']

    df_consolidado = df.groupby(grupos).apply(
        lambda g: pd.Series({
            'NIÑO':         g.loc[g['Anio_Actual_Paciente'].between(0, 11),  'Id_Cita'].count(),
            'ADOLESCENTE':  g.loc[g['Anio_Actual_Paciente'].between(12, 17), 'Id_Cita'].count(),
            'JOVEN':        g.loc[g['Anio_Actual_Paciente'].between(18, 29), 'Id_Cita'].count(),
            'ADULTO':       g.loc[g['Anio_Actual_Paciente'].between(30, 59), 'Id_Cita'].count(),
            'ADULTO MAYOR': g.loc[g['Anio_Actual_Paciente'] > 59,            'Id_Cita'].count(),
        })
    ).reset_index()

    # Convertir conteos a entero
    for col in ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']:
        df_consolidado[col] = df_consolidado[col].astype(int)

    # ORDER BY Fecha_Atencion ASC
    df_consolidado.sort_values('Fecha_Atencion', ascending=True, inplace=True)

    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento exitoso! {len(df_consolidado)} filas consolidadas.")


if __name__ == "__main__":
    procesar_informacion_his()
