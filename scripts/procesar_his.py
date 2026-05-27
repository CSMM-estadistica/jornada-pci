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
            if df is not None and len(df.columns) > 2:
                print(f"-> Éxito al leer con separador '{separador}' en UTF-8.")
                break
        except Exception:
            try:
                df = pd.read_csv(ruta_origen, sep=separador, encoding='latin-1')
                if df is not None and len(df.columns) > 2:
                    print(f"-> Éxito al leer con separador '{separador}' en Latin-1.")
                    break
            except Exception:
                continue

    if df is None or df.empty:
        print("Error: No se pudo procesar la estructura del CSV.")
        return

    # ── NORMALIZACIÓN RADICAL DE CABECERAS ───────────────────────────────────
    # Elimina caracteres invisibles de control, espacios y estandariza a MAYÚSCULAS
    df.columns = [
        str(col).encode('utf-8', 'ignore').decode('utf-8-sig').strip().upper() 
        for col in df.columns
    ]
    print("Columnas normalizadas en memoria:", list(df.columns))

    # Mapeo flexible de nombres de columnas (Inmune a tildes o guiones bajos)
    col_item  = next((c for c in df.columns if 'ITEM' in c or 'COD' in c), None)
    col_corr  = next((c for c in df.columns if 'CORREL' in c or 'NUM_LAB' in c or 'ID_CORR' in c), None)
    col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c or 'FEC' in c), None)
    col_vlab  = next((c for c in df.columns if 'VALOR_LAB' in c or 'VALOR' in c or 'LAB' in c), None)
    col_edad  = next((c for c in df.columns if 'EDAD' in c or 'ANIO' in c or 'AÑO' in c or 'PACIENTE' in c), None)
    col_cita  = next((c for c in df.columns if 'CITA' in c or 'ID' in c), None)

    # Fallbacks si las búsquedas por texto parcial fallan por completo
    if not col_item: col_item = 'CODIGO_ITEM' if 'CODIGO_ITEM' in df.columns else df.columns[0]
    if not col_corr: col_corr = 'ID_CORRELATIVO_LAB' if 'ID_CORRELATIVO_LAB' in df.columns else df.columns[1]
    if not col_fecha: col_fecha = 'FECHA_ATENCION' if 'FECHA_ATENCION' in df.columns else df.columns[2]
    if not col_vlab: col_vlab = 'VALOR_LAB' if 'VALOR_LAB' in df.columns else df.columns[3]
    if not col_edad: col_edad = 'ANIO_ACTUAL_PACIENTE' if 'ANIO_ACTUAL_PACIENTE' in df.columns else df.columns[4]
    if not col_cita: col_cita = 'ID_CITA' if 'ID_CITA' in df.columns else df.columns[5]

    print(f"Campos asignados -> Ítem: {col_item} | Correlativo: {col_corr} | Cita: {col_cita}")

    # ── FILTROS ULTRA-PERMISIVOS (WHERE Codigo_Item = '99801' AND Id_Correlativo_Lab = 1) ──
    # Limpiamos decimales flotantes invisibles que deja Excel (ej: 99801.0 -> 99801)
    serie_item = df[col_item].astype(str).str.strip().str.split('.').str[0]
    serie_corr = pd.to_numeric(df[col_corr], errors='coerce').fillna(0).astype(int)

    df_filtrado = df[(serie_item == '99801') & (serie_corr == 1)].copy()
    print(f"Filas que pasaron el filtro estricto (Correlativo = 1): {len(df_filtrado)}")

    # Fallback si el correlativo viene vacío o mapeado de otra forma
    if df_filtrado.empty:
        print("Aviso: Cero filas encontradas con Correlativo=1. Intentando rescate basado solo en el código 99801...")
        df_filtrado = df[serie_item == '99801'].copy()
        print(f"Filas rescatadas con filtro flexible: {len(df_filtrado)}")

    if df_filtrado.empty:
        print("AVISO: Ninguna fila cumple los filtros del código '99801'. Generando archivo de contingencia.")
        df_vacio = pd.DataFrame(columns=['Fecha_Atencion', 'Valor_Lab', 'NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR'])
        df_vacio.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        return

    # Asegurar tipos y limpiezas en el set filtrado
    df_filtrado[col_edad] = pd.to_numeric(df_filtrado[col_edad], errors='coerce').fillna(-1)
    df_filtrado[col_fecha] = df_filtrado[col_fecha].astype(str).str.strip().str.split(' ').str[0]
    df_filtrado[col_vlab] = df_filtrado[col_vlab].astype(str).str.strip().upper()

    # ── CONSOLIDACIÓN DE ETAPAS DE VIDA (GROUP BY & COUNT) ───────────────────
    grupos = [col_fecha, col_vlab]

    df_consolidado = df_filtrado.groupby(grupos).apply(
        lambda g: pd.Series({
            'NIÑO':         g.loc[g[col_edad].between(0, 11),  col_cita].count(),
            'ADOLESCENTE':  g.loc[g[col_edad].between(12, 17), col_cita].count(),
            'JOVEN':        g.loc[g[col_edad].between(18, 29), col_cita].count(),
            'ADULTO':       g.loc[g[col_edad].between(30, 59), col_cita].count(),
            'ADULTO MAYOR': g.loc[g[col_edad] > 59,            col_cita].count(),
        })
    ).reset_index()

    # Asegurar formato entero para los conteos
    for col in ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']:
        df_consolidado[col] = df_consolidado[col].astype(int)

    # Renombrar columnas finales para que coincidan con la estructura que consume el index.html
    df_consolidado.rename(columns={
        col_fecha: 'Fecha_Atencion',
        col_vlab: 'Valor_Lab'
    }, inplace=True)

    # ORDER BY Fecha_Atencion ASC
    df_consolidado.sort_values('Fecha_Atencion', ascending=True, inplace=True)

    # Guardar a producción
    df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
    print(f"¡Procesamiento exitoso! {len(df_consolidado)} filas consolidadas de la jornada guardadas en '{ruta_destino}'.")

if __name__ == "__main__":
    procesar_informacion_his()
