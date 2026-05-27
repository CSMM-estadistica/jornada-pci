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

    # Intentar leer con diferentes separadores eliminando el BOM si existiera
    df = None
    for separador in [';', ',']:
        try:
            df = pd.read_csv(ruta_origen, sep=separador, encoding='utf-8-sig')
            if df is not None and len(df.columns) > 1:
                print(f"-> Éxito al leer con separador '{separador}' en UTF-8.")
                break
        except Exception:
            try:
                df = pd.read_csv(ruta_origen, sep=separador, encoding='latin-1')
                if df is not None and len(df.columns) > 1:
                    print(f"-> Éxito al leer con separador '{separador}' en Latin-1.")
                    break
            except Exception:
                continue

    if df is None or df.empty:
        print("Error: No se pudo procesar la estructura del CSV.")
        return

    # ── NORMALIZACIÓN RADICAL DE CABECERAS ───────────────────────────────────
    df.columns = [
        str(col).encode('utf-8', 'ignore').decode('utf-8-sig').strip().upper() 
        for col in df.columns
    ]
    print("Columnas normalizadas detectadas en el archivo:", list(df.columns))

    # Diccionario de búsqueda flexible por palabras clave para evitar KeyErrors
    mapeo_columnas = {
        'ITEM': ['CODIGO_ITEM', 'COD_ITEM', 'ITEM', 'CODIGO'],
        'CORRELATIVO': ['ID_CORRELATIVO_LAB', 'ID_CORRELATIVO', 'CORRELATIVO', 'NUM_LAB', 'NRO_LAB'],
        'FECHA': ['FECHA_ATENCION', 'FECHA', 'FEC_ATENC', 'ATENCION'],
        'VALOR': ['VALOR_LAB', 'VALOR', 'LAB', 'RESULTADO'],
        'EDAD': ['ANIO_ACTUAL_PACIENTE', 'ANIO_ACTUAL', 'EDAD', 'EDAD_PACIENTE', 'AÑO', 'ANIO'],
        'CITA': ['ID_CITA', 'CITA', 'ID', 'IDENTIFICADOR']
    }

    columnas_identificadas = {}
    for clave, alternativas in mapeo_columnas.items():
        coincidencia = next((c for c in df.columns if any(alt in c for alt in alternativas)), None)
        if coincidencia:
            columnas_identificadas[clave] = coincidencia
        else:
            # Si no se encuentra, se asigna la primera columna que contenga parte del nombre o el primer campo por defecto
            columnas_identificadas[clave] = df.columns[0]

    col_item = columnas_identificadas['ITEM']
    col_corr = columnas_identificadas['CORRELATIVO']
    col_fecha = columnas_identificadas['FECHA']
    col_vlab = columnas_identificadas['VALOR']
    col_edad = columnas_identificadas['EDAD']
    col_cita = columnas_identificadas['CITA']

    print(f"Mapeo final aplicado -> Ítem: {col_item} | Correlativo: {col_corr} | Fecha: {col_fecha} | Edad: {col_edad}")

    # ── FILTROS DE CONTINGENCIA (WHERE Codigo_Item = '99801' AND Id_Correlativo_Lab = 1) ──
    # Limpieza de cadenas para evitar problemas si el código viene con decimales (.0)
    serie_item = df[col_item].astype(str).str.strip().str.split('.').str[0]
    serie_corr = pd.to_numeric(df[col_corr], errors='coerce').fillna(0).astype(int)

    df_filtrado = df[(serie_item == '99801') & (serie_corr == 1)].copy()
    print(f"Filas encontradas con filtro estricto (Correlativo = 1): {len(df_filtrado)}")

    if df_filtrado.empty:
        print("Aviso: Cero filas con Correlativo=1. Aplicando rescate flexible basado solo en código 99801...")
        df_filtrado = df[serie_item == '99801'].copy()
        print(f"Filas rescatadas: {len(df_filtrado)}")

    if df_filtrado.empty:
        print("AVISO: Ninguna fila coincide con el código '99801'. Generando archivo de contingencia vacío.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    # Limpieza de tipos de datos sobre el DataFrame filtrado
    df_filtrado[col_edad] = pd.to_numeric(df_filtrado[col_edad], errors='coerce').fillna(-1).astype(int)
    df_filtrado[col_fecha] = df_filtrado[col_fecha].astype(str).str.strip().str.split(' ').str[0]
    df_filtrado[col_vlab] = df_filtrado[col_vlab].astype(str).str.strip().upper()

    # ── CONSOLIDACIÓN VECTORIAL SEGURA ───────────────────────────────────────
    # Evaluamos los rangos asignando banderas numéricas directamente
    df_filtrado['NIÑO']         = df_filtrado[col_edad].between(0, 11).astype(int)
    df_filtrado['ADOLESCENTE']  = df_filtrado[col_edad].between(12, 17).astype(int)
    df_filtrado['JOVEN']        = df_filtrado[col_edad].between(18, 29).astype(int)
    df_filtrado['ADULTO']       = df_filtrado[col_edad].between(30, 59).astype(int)
    df_filtrado['ADULTO MAYOR'] = (df_filtrado[col_edad] > 59).astype(int)

    # Agrupación por campos estructurados
    df_consolidado = df_filtrado.groupby([col_fecha, col_vlab])[
        ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
    ].sum().reset_index()

    # Forzar nombres estándar de salida requeridos por el entorno web
    df_consolidado.rename(columns={
        col_fecha: 'Fecha_Atencion',
        col_vlab: 'Valor_Lab'
    }, inplace=True)

    # Ordenar cronológicamente
    df_consolidado.sort_values('Fecha_Atencion', ascending=True, inplace=True)

    # Guardar matriz procesada
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento exitoso! {len(df_consolidado)} filas consolidadas guardadas en '{ruta_destino}'.")

if __name__ == "__main__":
    procesar_informacion_his()
