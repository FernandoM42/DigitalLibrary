# migrate_editorials.py
import pandas as pd
import mysql.connector
import json
import os
from config import Config # Para usar la misma configuración de DB

# --- Configuración de la Base de Datos (usando la misma de Flask) ---
DB_CONFIG = {
    'host': Config.MYSQL_HOST,
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'database': Config.MYSQL_DB,
    'port': Config.MYSQL_PORT
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar con la base de datos: {err}")
        return None

def migrate_editorial_data():
    conn = get_db_connection()
    if conn is None:
        print("No se pudo establecer conexión con la base de datos. Saliendo de la migración.")
        return

    cursor = conn.cursor()
    
    try:
        print("--- Iniciando migración de datos de Editoriales ---")

        # Paso 1: Obtener todos los nombres de editoriales distintos de la tabla 'obras'
        # Usamos TRIM() en SQL y luego .strip() en Python para doble seguridad.
        print("1. Extrayendo nombres de editoriales distintos de la tabla 'obras'...")
        # Modificación: Asegurarse de que el SQL también trimee los resultados
        cursor.execute("SELECT DISTINCT TRIM(editorial) FROM obras WHERE editorial IS NOT NULL AND TRIM(editorial) != '';")
        # Modificación: Aplicar .strip() directamente en el Python si 'row[0]' es una cadena
        distinct_editorials = [row[0].strip() for row in cursor.fetchall() if row[0] is not None]
        print(f"   Encontradas {len(distinct_editorials)} editoriales distintas.")

        # Paso 2: Insertar estos nombres distintos en la nueva tabla 'editoriales'
        print("2. Insertando editoriales en la tabla 'editoriales'...")
        for editorial_name in distinct_editorials:
            if editorial_name: # Asegurarse de que el nombre no esté vacío después del .strip()
                insert_editorial_query = "INSERT IGNORE INTO editoriales (nombre_editorial) VALUES (%s);"
                cursor.execute(insert_editorial_query, (editorial_name,))
        conn.commit()
        print("   Editoriales únicas pobladas en la tabla 'editoriales'.")

        # Paso 3: Obtener el mapeo de nombre_editorial a id_editorial
        print("3. Obteniendo el mapeo de nombres de editorial a IDs...")
        cursor.execute("SELECT id_editorial, nombre_editorial FROM editoriales;")
        editorial_map = {row[1]: row[0] for row in cursor.fetchall()}
        print(f"   Mapeo de {len(editorial_map)} editoriales cargado.")

        # Opcional: Asegurarse de tener un ID para 'Desconocido' o nombres vacíos
        if 'Desconocido' not in editorial_map:
            cursor.execute("INSERT IGNORE INTO editoriales (nombre_editorial) VALUES ('Desconocido');")
            conn.commit()
            cursor.execute("SELECT id_editorial FROM editoriales WHERE nombre_editorial = 'Desconocido';")
            editorial_map['Desconocido'] = cursor.fetchone()[0]
            print("   ID para 'Desconocido' asegurado.")

        # Paso 4: Actualizar la columna 'id_editorial' en la tabla 'obras'
        print("4. Actualizando la columna 'id_editorial' en la tabla 'obras'...")
        cursor.execute("SELECT id_obra, editorial FROM obras;")
        all_books_old_editorials = cursor.fetchall()
        
        updated_count = 0
        for book_id, old_editorial_name in all_books_old_editorials:
            # Modificación: Usar .strip() y manejar None directamente
            cleaned_editorial_name = old_editorial_name.strip() if old_editorial_name is not None else ''
            
            # Obtener el id_editorial del mapeo, si no se encuentra, usar el ID de 'Desconocido'
            id_editorial_to_assign = editorial_map.get(cleaned_editorial_name)
            if id_editorial_to_assign is None:
                id_editorial_to_assign = editorial_map.get('Desconocido') # Fallback para editoriales no encontradas/nulas
                if id_editorial_to_assign is None: # Si 'Desconocido' no existe por alguna razón
                    print(f"   Advertencia: No se encontró ID para '{cleaned_editorial_name}' y 'Desconocido' no existe. Saltando obra {book_id}.")
                    continue 

            update_obra_query = "UPDATE obras SET id_editorial = %s WHERE id_obra = %s;"
            cursor.execute(update_obra_query, (id_editorial_to_assign, book_id))
            updated_count += 1
        
        conn.commit()
        print(f"   {updated_count} obras actualizadas con sus nuevos IDs de editorial.")

        print("--- Migración de datos de Editoriales completada exitosamente ---")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error de base de datos durante la migración: {err}")
    except Exception as e:
        conn.rollback()
        print(f"Error inesperado durante la migración: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    migrate_editorial_data()

# La función auxiliar TRIM(s) ya no es necesaria y puede ser eliminada.