import pandas as pd
import os
import sys

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    
    try:
        print("=== PASO 1: Creando directorios ===")
        os.makedirs('data', exist_ok=True)
        
        print("=== PASO 2: Buscando archivo origen ===")
        posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv']
        ruta_origen = None
        for r in posibles_rutas:
            if os.path.exists(r):
                ruta_origen = r
                break
        
        if not ruta_origen:
            print("AVISO: No se encontró 'his_raw.csv'. Generando base de contingencia")
            generar_data_contingencia(ruta_destino)
            return

        print(f"Archivo detectado en: {ruta_origen}. Tamaño: {os.path.getsize(ruta_origen)} bytes")
        
        print("=== PASO 3: Intentando leer CSV ===")
        df = None
        
        # Método mejorado de lectura
        for enc in ['latin-1', 'utf-8', 'cp1252', 'utf-8-sig']:
            for sep in [',', ';', '\t', '|']:
                try:
                    df = pd.read_csv(ruta_origen, sep=sep, encoding=enc, 
                                   on_bad_lines='skip', nrows=1000)  # Leer primeras 1000 filas
                    if df is not None and len(df.columns) > 2:
                        print(f"✓ Lectura exitosa: encoding={enc}, sep='{sep}', {len(df.columns)} columnas")
                        # Leer el archivo completo ahora
                        df = pd.read_csv(ruta_origen, sep=sep, encoding=enc, 
                                       on_bad_lines='skip')
                        break
                except Exception as e:
                    continue
            if df is not None and len(df.columns) > 2:
                break

        if df is None or df.empty:
            print("❌ No se pudo leer el archivo. Generando contingencia.")
            generar_data_contingencia(ruta_destino)
            return

        print(f"✓ Archivo leído: {len(df)} filas, {len(df.columns)} columnas")

        print("=== PASO 4: Limpiando columnas ===")
        df.columns = [str(col).strip().upper() for col in df.columns]
        print(f"Columnas: {list(df.columns[:5])}...")  # Mostrar solo primeras 5

        # Búsqueda más robusta de columnas
        col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENCION' in c), None)
        col_vlab = next((c for c in df.columns if 'VALOR' in c or 'LAB' in c), None)
        col_item = next((c for c in df.columns if 'ITEM' in c or 'CODIGO' in c or 'PRESTACION' in c), None)
        col_corr = next((c for c in df.columns if 'CORREL' in c or 'NUMERO' in c), None)
        col_edad = next((c for c in df.columns if 'EDAD' in c or 'AÑO' in c or 'ANIO' in c), None)

        # Fallback seguro
        if not col_fecha: 
            col_fecha = df.columns[0] if len(df.columns) > 0 else None
        if not col_item: 
            col_item = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        if not col_vlab: 
            col_vlab = df.columns[2] if len(df.columns) > 2 else df.columns[0]
        if not col_corr: 
            col_corr = df.columns[3] if len(df.columns) > 3 else df.columns[0]
        if not col_edad: 
            col_edad = df.columns[4] if len(df.columns) > 4 else df.columns[0]

        print(f"✓ Columnas asignadas: Fecha={col_fecha}, Item={col_item}, Valor={col_vlab}")

        print("=== PASO 5: Homologando tipos de datos ===")
        df['FECHA_LIMPIA'] = df[col_fecha].astype(str).str.strip().str.split(' ').str[0]
        df['ITEM_LIMPIO'] = df[col_item].astype(str).str.strip()
        df['VLAB_LIMPIO'] = df[col_vlab].astype(str).str.strip().upper()
        df['CORR_LIMPIO'] = pd.to_numeric(df[col_corr], errors='coerce').fillna(0).astype(int)
        df['EDAD_LIMPIA'] = pd.to_numeric(df[col_edad], errors='coerce').fillna(-1).astype(int)

        print("=== PASO 6: Aplicando Filtros ===")
        df_filtrado = df[(df['ITEM_LIMPIO'] == '99801') & (df['CORR_LIMPIO'] == 1)].copy()
        print(f"✓ Filas después del filtro: {len(df_filtrado)}")

        if df_filtrado.empty:
            print("⚠️ No hay datos con los filtros requeridos. Generando estructura base.")
            generar_data_contingencia(ruta_destino)
            return

        print("=== PASO 7: Calculando Etapas de Vida ===")
        edad = df_filtrado['EDAD_LIMPIA']
        df_filtrado['NIÑO'] = ((edad >= 0) & (edad <= 11)).astype(int)
        df_filtrado['ADOLESCENTE'] = ((edad >= 12) & (edad <= 17)).astype(int)
        df_filtrado['JOVEN'] = ((edad >= 18) & (edad <= 29)).astype(int)
        df_filtrado['ADULTO'] = ((edad >= 30) & (edad <= 59)).astype(int)
        df_filtrado['ADULTO MAYOR'] = ((edad > 59)).astype(int)

        print("=== PASO 8: Agrupando y Ordenando ===")
        grupos = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
        df_consolidado = df_filtrado.groupby(['FECHA_LIMPIA', 'VLAB_LIMPIO'])[grupos].sum().reset_index()
        df_consolidado = df_consolidado.sort_values(by='FECHA_LIMPIA', ascending=True)

        df_consolidado = df_consolidado.rename(columns={
            'FECHA_LIMPIA': 'Fecha_Atencion',
            'VLAB_LIMPIO': 'Valor_Lab'
        })

        print("=== PASO 9: Guardando archivo procesado ===")
        df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        print(f"✅ ¡Éxito! {len(df_consolidado)} filas guardadas en {ruta_destino}")

    except Exception as error_general:
        print(f"❌ ERROR CRÍTICO: {str(error_general)}")
        import traceback
        traceback.print_exc()
        print("Activando protocolo de emergencia...")
        generar_data_contingencia(ruta_destino)

def generar_data_contingencia(ruta):
    df_base = pd.DataFrame([{
        'Fecha_Atencion': '2026-05-26',
        'Valor_Lab': '1',
        'NIÑO': 0,
        'ADOLESCENTE': 0,
        'JOVEN': 0,
        'ADULTO': 0,
        'ADULTO MAYOR': 0
    }])
    df_base.to_csv(ruta, sep=',', index=False, encoding='utf-8')
    print(f"✅ Estructura de contingencia creada en {ruta}")

if __name__ == "__main__":
    procesar_informacion_his()
