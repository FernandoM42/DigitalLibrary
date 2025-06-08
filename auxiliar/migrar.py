import pandas as pd
import mysql.connector
from mysql.connector import Error
import json
import re # Para expresiones regulares para parsear el título

# --- 1. Configuración de la Base de Datos ---
# ¡¡¡IMPORTANTE!!! Por favor, ajusta estos valores con los de tu base de datos
DB_CONFIG = {
    'host': '127.0.0.1',
    'database': 'sk_libros', # Ya me confirmaste que es 'sk_libros'
    'user': 'root',
    'password': '12admin34' # ¡¡¡CAMBIA ESTO CON TU CONTRASEÑA REAL!!!
}

# --- 2. Ruta del Archivo Excel y Nombres de las Hojas ---
# Asegúrate de que este archivo esté en el mismo directorio que tu script,
# o proporciona la ruta completa a él.
EXCEL_FILE = "Stephen King - Lista de Obras.xlsx"
SHEET_NAMES = ["Novelas", "Colecciones de relatos"] # Nombres exactos de tus hojas

# --- 3. Funciones de Ayuda para la Transformación de Datos ---

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print(f"Conexión exitosa a la base de datos: {DB_CONFIG['database']}")
        return conn
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

def get_editorial_id(cursor, editorial_name="Debolsillo"):
    """
    Busca el ID de una editorial por su nombre.
    Si no existe, la inserta y devuelve el nuevo ID.
    """
    try:
        select_query = "SELECT id_editorial FROM editoriales WHERE nombre_editorial = %s"
        cursor.execute(select_query, (editorial_name,))
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            print(f"Editorial '{editorial_name}' no encontrada. Insertándola...")
            insert_query = "INSERT INTO editoriales (nombre_editorial) VALUES (%s)"
            cursor.execute(insert_query, (editorial_name,))
            cursor.connection.commit() # Commit para asegurar la inserción de la editorial

            cursor.execute("SELECT LAST_INSERT_ID()")
            new_id = cursor.fetchone()[0]
            print(f"Editorial '{editorial_name}' insertada con ID: {new_id}")
            return new_id
    except Error as e:
        print(f"Error al gestionar la editorial '{editorial_name}': {e}")
        raise

def parse_title(full_title):
    """
    Extrae el título en español y el título original de una cadena como
    'Título en Español (Título Original)'.
    """
    if pd.isna(full_title) or not isinstance(full_title, str):
        return "", ""

    # Expresión regular para capturar "Texto antes del paréntesis (Texto dentro del paréntesis)"
    match = re.search(r'^(.*?)\s*\((.*?)\)$', full_title.strip())
    if match:
        titulo_espanol = match.group(1).strip()
        titulo_original = match.group(2).strip()
        return titulo_espanol, titulo_original
    else:
        # Si no coincide el patrón, asumimos que todo es el título en español
        # y el original es el mismo.
        return full_title.strip(), full_title.strip()

def map_adquirido_status(status_value):
    """
    Mapea el valor de 'STATUS' del CSV a 0 o 1 para p_adquirido_estado.
    0 o 1 del Excel -> 1 (Adquirido)
    Cualquier otro valor (incluido vacío/NaN) -> 0 (No adquirido)
    """
    # Convertir a cadena y limpiar espacios para comparación
    status_str = str(status_value).strip()
    if status_str in ['0', '1']: # Asumiendo que '0' y '1' son las cadenas literales en la celda
        return 1 # Adquirido
    else:
        return 0 # No adquirido

# --- 4. Lógica Principal de Migración ---
def migrate_data():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return

        cursor = conn.cursor()

        # Obtener el ID de la editorial por defecto ("Debolsillo") una sola vez
        try:
            default_editorial_id = get_editorial_id(cursor, "Debolsillo")
        except Exception as e:
            print(f"No se pudo inicializar la editorial por defecto. Abortando migración: {e}")
            return

        # Definir los valores JSON por defecto
        default_autores_json = json.dumps([{"nombre": "Stephen", "apellido": "King"}])
        default_generos_json = json.dumps(["Terror"])
        default_imagenes_json = json.dumps([])

        total_processed_rows = 0
        total_errors = 0

        for sheet_name in SHEET_NAMES:
            print(f"\n--- Procesando hoja: {sheet_name} del archivo {EXCEL_FILE} ---")
            try:
                # header=0 porque los encabezados están en la primera fila (índice 0)
                df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name, header=0)

                # Asegurarse de que las columnas esperadas existan (ahora en mayúsculas)
                required_cols = ['AÑO', 'TÍTULO DEL LIBRO', 'STATUS']
                if not all(col in df.columns for col in required_cols):
                    print(f"Error: La hoja '{sheet_name}' no contiene todas las columnas requeridas ({', '.join(required_cols)}). Columnas encontradas: {df.columns.tolist()}")
                    continue

            except FileNotFoundError:
                print(f"Error: El archivo Excel '{EXCEL_FILE}' no se encontró. Asegúrate de que está en la ruta correcta.")
                return
            except ValueError:
                print(f"Error: La hoja '{sheet_name}' no se encontró en el archivo '{EXCEL_FILE}'. Asegúrate de que el nombre de la hoja es correcto.")
                continue
            except Exception as e:
                print(f"Error al leer la hoja '{sheet_name}' del archivo Excel: {e}. Saltando.")
                continue

            # Determinar el tipo de obra basado en el nombre de la hoja
            if sheet_name == "Novelas":
                p_tipo_obra_nombre = "Novela"
            elif sheet_name == "Colecciones de relatos":
                p_tipo_obra_nombre = "Colección de relatos"
            else:
                print(f"Advertencia: Tipo de obra desconocido para la hoja '{sheet_name}'. Saltando esta hoja.")
                continue

            for index, row in df.iterrows():
                # El +2 es para el número de fila real en Excel (si los headers están en la fila 1, los datos empiezan en la fila 2)
                row_number_excel = index + 2
                print(f"  Procesando fila {row_number_excel} de la hoja '{sheet_name}'...")
                
                # Omitir filas donde 'AÑO' y 'TÍTULO DEL LIBRO' están completamente vacíos
                # Accediendo a las columnas con los nombres esperados en mayúsculas
                if pd.isna(row['AÑO']) and pd.isna(row['TÍTULO DEL LIBRO']):
                    print(f"    Saltando fila {row_number_excel}: AÑO y TÍTULO DEL LIBRO están vacíos (posible fila de resumen/vacía).")
                    continue

                try:
                    # 1. Extraer y parsear Título en Español y Original
                    # Accediendo a la columna con el nombre en mayúsculas
                    full_title = str(row['TÍTULO DEL LIBRO']).strip()
                    if not full_title: # Si el título está vacío, saltar esta fila
                        print(f"    Advertencia: TÍTULO DEL LIBRO vacío en fila {row_number_excel}. Saltando.")
                        total_errors += 1
                        continue

                    p_titulo_espanol, p_titulo_original = parse_title(full_title)

                    # 2. Extraer y convertir Año de Publicación
                    p_anio_publicacion = None
                    # Accediendo a la columna con el nombre en mayúsculas
                    anio_data = row['AÑO']
                    if pd.notna(anio_data): # Comprobar si no es NaN
                        try:
                            # A veces pandas lee años como flotantes (ej. 1980.0)
                            p_anio_publicacion = int(float(str(anio_data).strip()))
                        except ValueError:
                            print(f"    Advertencia: Año '{anio_data}' no válido en fila {row_number_excel}. Usando NULL.")
                    else:
                        print(f"    Advertencia: Año vacío en fila {row_number_excel}. Usando NULL.")

                    # 3. Mapear Status a p_adquirido_estado
                    # Accediendo a la columna con el nombre en mayúsculas
                    p_adquirido_estado = map_adquirido_status(row['STATUS'])

                    # 4. Valores por defecto según las pautas
                    p_sinopsis = ''
                    p_numero_paginas = 0 # Pauta: por defecto 0
                    p_isbn = '-'         # Pauta: por defecto "-"
                    p_nombre_encuadernacion = '' # No hay columna, se deja vacío. El SP lo gestionará.

                    # 5. Parámetros JSON por defecto
                    p_autores_json = default_autores_json
                    p_generos_json = default_generos_json
                    p_imagenes_json = default_imagenes_json

                    # 6. Preparar argumentos para el procedimiento almacenado
                    args = (
                        1,                     # ev (Registrar)
                        None,                  # p_id_obra (NULL para registrar)
                        p_titulo_original,
                        p_titulo_espanol,
                        p_anio_publicacion,
                        p_sinopsis,
                        p_tipo_obra_nombre,
                        p_numero_paginas,
                        p_isbn,
                        p_adquirido_estado,
                        p_autores_json,
                        p_generos_json,
                        p_imagenes_json,
                        p_nombre_encuadernacion,
                        default_editorial_id
                    )

                    # 7. Ejecutar el procedimiento almacenado
                    cursor.callproc('gestionar_obra', args)
                    conn.commit()
                    total_processed_rows += 1
                    print(f"    Fila {row_number_excel} (Obra '{p_titulo_espanol}') insertada con éxito.")

                except Error as e:
                    conn.rollback() # Hacer rollback en caso de error de DB
                    print(f"    Error de DB al procesar la fila {row_number_excel} (Obra: '{full_title}'): {e}")
                    total_errors += 1
                except Exception as e:
                    conn.rollback() # Hacer rollback por cualquier otra excepción
                    print(f"    Error inesperado al procesar la fila {row_number_excel} (Obra: '{full_title}'): {e}")
                    total_errors += 1

        print("\n--- Migración Finalizada ---")
        print(f"Total de filas procesadas con éxito: {total_processed_rows}")
        print(f"Total de errores encontrados: {total_errors}")

    except Error as e:
        print(f"Error general de base de datos durante la migración: {e}")
    except Exception as e:
        print(f"Error inesperado en la migración: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Conexión a la base de datos cerrada.")

# --- Ejecutar la migración ---
if __name__ == "__main__":
    migrate_data()