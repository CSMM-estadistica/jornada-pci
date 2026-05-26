import pandas as pd
import os
import sys

def procesar_informacion_his():
    ruta_destino = 'data/data_jornada.csv'
    
    try:
        print("=== PASO 1: Creando carpetas de salida ===")
        os.makedirs('data', exist_ok=True)
        
        print("=== PASO 2: Localizando archivo de origen ===")
        posibles_rutas = ['his_raw.csv', 'data/his_raw.csv', 'HIS_RAW.csv', 'his_raw.CSV']
        ruta_origen = None
        for r in posibles_rutas:
            if os.path.exists(r):
                ruta_origen = r
                break
        
        if not ruta_origen:
            print("AVISO: No se encontró un archivo físico compatible. Ejecutando contingencia.")
            generar_data_contingencia(ruta_destino)
            return

        print(f"Archivo real encontrado en: '{ruta_origen}' ({os.path.getsize(ruta_origen)} bytes)")
        
        print("=== PASO 3: Lectura Avanzada del Dataset ===")
        df = None
        # Probamos diferentes configuraciones de lectura para romper bloqueos de formato
        for sep_v in [';', ',', '\t']:
            for enc in ['latin-1', 'utf-8', 'utf-8-sig', 'cp1252']:
                try:
                    df = pd.read_csv(ruta_origen, sep=sep_v, encoding=enc, engine='python', on_bad_lines='skip')
                    if df is not None and len(df.columns) > 3:
                        print(f"-> Éxito: Separador '{sep_v}' | Codificación '{enc}'. Filas leídas: {len(df)}")
                        break
                except Exception:
                    continue
            if df is not None and len(df.columns) > 3:
                break

        if df is None or df.empty:
            print("Error: No se pudo extraer la matriz del CSV.")
            generar_data_contingencia(ruta_destino)
            return

        print("=== PASO 4: Mapeo y Normalización de Cabeceras ===")
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        # Identificación flexible de columnas clave (Inmune a variaciones de exportación)
        col_fecha = next((c for c in df.columns if 'FECHA' in c or 'ATENC' in c or 'FEC' in c), df.columns[0])
        col_vlab = next((c for c in df.columns if 'VALOR_LAB' in c or 'VALOR' in c or 'V_LAB' in c or 'LAB' in c), None)
        col_item = next((c for c in df.columns if 'ITEM' in c or 'COD' in c or 'PREST' in c), None)
        col_corr = next((c for c in df.columns if 'CORREL' in c or 'NUM_LAB' in c or 'ID_CORR' in c), None)
        col_edad = next((c for c in df.columns if 'EDAD' in c or 'ANIO' in c or 'AÑO' in c or 'PACIENTE' in c), None)

        # Asignaciones forzadas por posición si fallan las búsquedas textuales
        if not col_item: col_item = df.columns[1]
        if not col_vlab: col_vlab = df.columns[2]
        if not col_corr: col_corr = df.columns[3] if len(df.columns) > 3 else df.columns[0]
        if not col_edad: col_edad = df.columns[4] if len(df.columns) > 4 else df.columns[0]

        print(f"Mapeo de Campos -> Fecha: {col_fecha} | Item: {col_item} | Valor_Lab: {col_vlab} | Correlativo: {col_corr} | Edad: {col_edad}")

        # Crear series de datos ultra limpias sin alterar el df original
        fecha_serie = df[col_fecha].astype(str).str.strip().str.split(' ').str[0]
        
        # Normalizar Ítem (Eliminar punto decimal flotante si Excel lo guardó como número, ej: 99801.0 -> 99801)
        item_serie = df[col_item].astype(str).str.strip().str.split('.').str[0]
        
        vlab_serie = df[col_vlab].astype(str).str.strip().upper() if col_vlab else '1'
        corr_serie = pd.to_numeric(df[col_corr], errors='coerce').fillna(1).astype(int)
        edad_serie = pd.to_numeric(df[col_edad], errors='coerce').fillna(-1).astype(int)

        # Construir un dataframe intermedio limpio para ejecutar la lógica de tu SQL
        df_limpio = pd.DataFrame({
            'FECHA': fecha_serie,
            'ITEM': item_serie,
            'VALOR_LAB': vlab_serie,
            'CORRELATIVO': corr_serie,
            'EDAD': edad_serie
        })

        print("=== PASO 5: Ejecutando el filtro WHERE de Inmunizaciones ===")
        # Filtramos buscando la cadena pura '99801' y asegurando correlativo igual a 1
        df_filtrado = df_limpio[(df_limpio['ITEM'] == '99801') & (df_limpio['CORRELATIVO'] == 1)].copy()
        print(f"Filas reales que pasaron el filtro WHERE: {len(df_filtrado)}")

        # Si el filtro es demasiado estricto y da 0, intentamos un fallback abriendo el filtro del correlativo
        if df_filtrado.empty:
            print("Aviso: Cero filas con Correlativo=1. Intentando rescatar registros basándonos solo en el código 99801...")
            df_filtrado = df_limpio[df_limpio['ITEM'] == '99801'].copy()
            print(f"Filas rescatadas con filtro flexible de Inmunización: {len(df_filtrado)}")

        if df_filtrado.empty:
            print("Alerta: No se encontraron códigos '99801' en el archivo. Desplegando contingencia estructural.")
            generar_data_contingencia(ruta_destino)
            return

        print("=== PASO 6: Clasificación por Etapas de Vida ===")
        edad = df_filtrado['EDAD']
        df_filtrado['NIÑO'] = ((edad >= 0) & (edad <= 11)).astype(int)
        df_filtrado['ADOLESCENTE'] = ((edad >= 12) & (edad <= 17)).astype(int)
        df_filtrado['JOVEN'] = ((edad >= 18) & (edad <= 29)).astype(int)
        df_filtrado['ADULTO'] = ((edad >= 30) & (edad <= 59)).astype(int)
        df_filtrado['ADULTO MAYOR'] = ((edad > 59)).astype(int)

        print("=== PASO 7: Consolidación Final (GROUP BY & ORDER BY) ===")
        grupos = ['NIÑO', 'ADOLESCENTE', 'JOVEN', 'ADULTO', 'ADULTO MAYOR']
        df_consolidado = df_filtrado.groupby(['FECHA', 'VALOR_LAB'])[grupos].sum().reset_index()
        
        # Ordenar de forma cronológica ascendente
        df_consolidado = df_consolidado.sort_values(by='FECHA', ascending=True)

        # Adecuar nombres exactos de columnas para la interfaz web (index.html)
        df_consolidado = df_consolidado.rename(columns={
            'FECHA': 'Fecha_Atencion',
            'VALOR_LAB': 'Valor_Lab'
        })

        print("=== PASO 8: Escribiendo Dataset de Producción ===")
        df_consolidado.to_csv(ruta_destino, sep=',', index=False, encoding='utf-8')
        print(f"¡Sincronización Exitosa! {len(df_consolidado)} filas consolidadas escritas en la data de la jornada.")

    except Exception as e:
        print(f"ERROR CRÍTICO EN PROCESAMIENTO: {str(e)}")
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
    print("Estructura base de contingencia guardada de manera segura.")

if __name__ == "__main__":
    procesar_informacion_his()
