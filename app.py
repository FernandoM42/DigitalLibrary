# app.py
from asyncio.windows_events import NULL
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
import json
import os
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config["TEMPLATES_AUTO_RELOAD"] = (
    True  # Permite que los cambios en plantillas se recarguen automáticamente
)


if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=app.config["MYSQL_HOST"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
            database=app.config["MYSQL_DB"],
            port=app.config["MYSQL_PORT"],
        )
        return conn
    except mysql.connector.Error as err:
        flash(f"Error al conectar con la base de datos: {err}", "danger")
        return None


@app.route("/")
@app.route("/index")
def index():
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return render_template(
            "index.html",
            obras=[],
            search_query="",
            tipos_obra_list=[],
            tipos_encuadernacion_list=[],
        )

    cursor = conn.cursor(dictionary=True)
    try:
        # --- Obtener datos para los filtros dropdowns (sin cambios) ---
        cursor.execute("SELECT id_tipo_obra, tipo FROM tipos_obra ORDER BY tipo")
        tipos_obra_list = cursor.fetchall()

        cursor.execute(
            "SELECT id_tipo_encuadernacion, nombre_encuadernacion FROM tipos_encuadernacion ORDER BY nombre_encuadernacion"
        )
        tipos_encuadernacion_list = cursor.fetchall()
        # -----------------------------------------------

        # --- Obtener todos los parámetros de filtro de la URL ---
        main_search_query = request.args.get("q", "").strip()
        q_title = request.args.get("q_title", "").strip()
        q_editorial = request.args.get("id_editorial_filter", "").strip()
        id_tipo_obra_filter = request.args.get("id_tipo_obra_filter", "").strip()
        id_tipo_encuadernacion_filter = request.args.get(
            "id_tipo_encuadernacion_filter", ""
        ).strip()
        min_anio_publicacion = request.args.get("min_anio_publicacion", "").strip()
        max_anio_publicacion = request.args.get("max_anio_publicacion", "").strip()
        adquirido_filter = request.args.get("adquirido_filter", "").strip()
        min_ranking = request.args.get("min_ranking", "").strip()
        max_ranking = request.args.get("max_ranking", "").strip()
        author_ids_filter = request.args.get("author_ids_filter", "").strip()
        genre_ids_filter = request.args.get("genre_ids_filter", "").strip()
        # *** NUEVO: Obtener el parámetro de ordenación ***
        sort_by = request.args.get("sort_by", "").strip()
        # --------------------------------------------------------

        base_query = "SELECT * FROM vista_obras_detalles"
        where_clauses = []
        query_params = []

        # --- Aplicar la barra de búsqueda principal (q) ---
        if main_search_query:
            search_pattern = f"%{main_search_query}%"
            where_clauses.append(
                "(titulo_original LIKE %s OR titulo_espanol LIKE %s OR editorial_nombre LIKE %s OR generos LIKE %s OR autores LIKE %s)"
            )
            query_params.extend([search_pattern] * 5)

        # --- Aplicar Filtros Avanzados (combinados con AND) ---

        if q_title:
            where_clauses.append("(titulo_original LIKE %s OR titulo_espanol LIKE %s)")
            query_params.extend([f"%{q_title}%", f"%{q_title}%"])

        if q_editorial:
            where_clauses.append("id_editorial = %s")
            query_params.append(q_editorial)

        if id_tipo_obra_filter:
            where_clauses.append("id_tipo_obra = %s")
            query_params.append(id_tipo_obra_filter)

        if id_tipo_encuadernacion_filter:
            where_clauses.append("id_tipo_encuadernacion = %s")
            query_params.append(id_tipo_encuadernacion_filter)

        if min_anio_publicacion:
            where_clauses.append("anio_publicacion >= %s")
            query_params.append(min_anio_publicacion)

        if max_anio_publicacion:
            where_clauses.append("anio_publicacion <= %s")
            query_params.append(max_anio_publicacion)

        if adquirido_filter:
            where_clauses.append("estado_adquisicion = %s")
            query_params.append(adquirido_filter)

        if min_ranking:
            where_clauses.append("ranking_personal_puntuacion >= %s")
            query_params.append(min_ranking)

        if max_ranking:
            where_clauses.append("ranking_personal_puntuacion <= %s")
            query_params.append(max_ranking)

        # Filtrado por autores (por ID)
        if author_ids_filter:
            author_ids = [
                int(id_str.strip())
                for id_str in author_ids_filter.split(",")
                if id_str.strip().isdigit()
            ]
            if author_ids:
                author_names_query = "SELECT CONCAT(nombre_autor, ' ', apellido_autor) AS full_name FROM autores WHERE id_autor IN (%s)"
                placeholders = ", ".join(["%s"] * len(author_ids))
                cursor.execute(author_names_query % placeholders, tuple(author_ids))
                temp_author_names = [row["full_name"] for row in cursor.fetchall()]

                if temp_author_names:
                    author_or_clauses = []
                    for name in temp_author_names:
                        author_or_clauses.append("autores LIKE %s")
                        query_params.append(f"%{name}%")
                    if author_or_clauses:
                        where_clauses.append("(" + " OR ".join(author_or_clauses) + ")")

        # Filtrado por géneros (por ID)
        if genre_ids_filter:
            genre_ids = [
                int(id_str.strip())
                for id_str in genre_ids_filter.split(",")
                if id_str.strip().isdigit()
            ]
            if genre_ids:
                genre_names_query = "SELECT nombre_genero AS genre_name FROM generos WHERE id_genero IN (%s)"
                placeholders = ", ".join(["%s"] * len(genre_ids))
                cursor.execute(genre_names_query % placeholders, tuple(genre_ids))
                temp_genre_names = [row["genre_name"] for row in cursor.fetchall()]

                if temp_genre_names:
                    genre_or_clauses = []
                    for name in temp_genre_names:
                        genre_or_clauses.append("generos LIKE %s")
                        query_params.append(f"%{name}%")

                    if genre_or_clauses:
                        where_clauses.append("(" + " OR ".join(genre_or_clauses) + ")")

        # --- Construir la consulta final ---
        full_query = base_query
        if where_clauses:
            full_query += " WHERE " + " AND ".join(where_clauses)

        # *** MODIFICACIÓN: Aplicar ordenación dinámica ***
        order_by_clause = (
            " ORDER BY titulo_espanol ASC"  # Orden por defecto si no se especifica
        )

        if sort_by == "title_asc":
            order_by_clause = " ORDER BY titulo_espanol ASC"
        elif sort_by == "title_desc":
            order_by_clause = " ORDER BY titulo_espanol DESC"
        elif sort_by == "author_asc":
            order_by_clause = " ORDER BY autores ASC"
        elif sort_by == "author_desc":
            order_by_clause = " ORDER BY autores DESC"
        elif sort_by == "year_desc":
            order_by_clause = " ORDER BY anio_publicacion DESC"
        elif sort_by == "year_asc":
            order_by_clause = " ORDER BY anio_publicacion ASC"
        elif sort_by == "rating_desc":
            # Para MySQL, NULLs LAST es implícito para DESC. Los nulos van al final.
            order_by_clause = (
                " ORDER BY ranking_personal_puntuacion DESC, titulo_espanol ASC"
            )
        elif sort_by == "rating_asc":
            # Para MySQL, NULLs FIRST es implícito para ASC. Los nulos van al principio.
            order_by_clause = (
                " ORDER BY ranking_personal_puntuacion ASC, titulo_espanol ASC"
            )
        elif sort_by == "pages_asc":
            order_by_clause = " ORDER BY numero_paginas ASC"
        elif sort_by == "pages_desc":
            order_by_clause = " ORDER BY numero_paginas DESC"
        # Puedes añadir más opciones si las definiste en el select

        full_query += order_by_clause  # Añadir la cláusula de ordenación dinámica
        # *** FIN MODIFICACIÓN ***

        # print(f"DEBUG SQL: Full Query: {full_query}")
        # print(f"DEBUG SQL: Query Params: {query_params}")

        cursor.execute(full_query, query_params)

        obras = cursor.fetchall()
        # print(f"DEBUG FLASK INDEX: Obras fetched (raw): {obras}")

        processed_obras = []
        for obra_dict in obras:
            current_id_obra = None
            if (
                isinstance(obra_dict, dict)
                and "id_obra" in obra_dict
                and obra_dict["id_obra"] is not None
            ):
                try:
                    current_id_obra = int(obra_dict["id_obra"])
                except (ValueError, TypeError):
                    current_id_obra = None
            else:
                current_id_obra = None

            obra_dict["id_obra"] = current_id_obra

            if obra_dict["id_obra"] is not None:
                processed_obras.append(obra_dict)
            else:
                print(
                    f"DEBUG FLASK INDEX: Saltando obra con id_obra faltante/inválido: {obra_dict}"
                )

        # print(
        #     f"DEBUG FLASK INDEX: Obras fetched (processed for id_obra and filtered): {processed_obras}"
        # )

        return render_template(
            "index.html",
            obras=processed_obras,
            search_query=main_search_query,
            tipos_obra_list=tipos_obra_list,
            tipos_encuadernacion_list=tipos_encuadernacion_list,
            # Pasar los valores de los filtros actuales a la plantilla
            q_title=q_title,
            q_editorial=q_editorial,
            id_tipo_obra_filter=id_tipo_obra_filter,
            id_tipo_encuadernacion_filter=id_tipo_encuadernacion_filter,
            min_anio_publicacion=min_anio_publicacion,
            max_anio_publicacion=max_anio_publicacion,
            adquirido_filter=adquirido_filter,
            min_ranking=min_ranking,
            max_ranking=max_ranking,
            author_ids_filter=author_ids_filter,
            genre_ids_filter=genre_ids_filter,
            sort_by=sort_by,  # *** Pasar el valor de sort_by a la plantilla ***
        )
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/api/tipos_obra", methods=["GET"])
def get_tipos_obra():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_tipo_obra, tipo FROM tipos_obra ORDER BY tipo")
    tipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(tipos)


@app.route("/api/tipos_encuadernacion", methods=["GET"])
def get_tipos_encuadernacion():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_tipo_encuadernacion, nombre_encuadernacion FROM tipos_encuadernacion ORDER BY nombre_encuadernacion"
    )
    tipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(tipos)


@app.route("/api/editoriales", methods=["GET"])
def get_editoriales():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(
        dictionary=True
    )  # <<< MODIFICADO: Usar cursor de diccionario para acceder por nombre
    try:
        query = request.args.get("q", "").lower()
        # MODIFICACIÓN: Consultar la nueva tabla 'editoriales'
        cursor.execute(
            f"SELECT id_editorial, nombre_editorial FROM editoriales WHERE LOWER(nombre_editorial) LIKE %s ORDER BY nombre_editorial LIMIT 10",
            ("%" + query + "%",),
        )
        # MODIFICACIÓN: Devolver el diccionario completo (id_editorial, nombre_editorial)
        editoriales = cursor.fetchall()
        return jsonify(editoriales)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/api/autores", methods=["GET"])
def get_autores():
    query = request.args.get("q", "").lower()
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"SELECT id_autor, nombre_autor, apellido_autor FROM autores WHERE LOWER(nombre_autor) LIKE %s OR LOWER(apellido_autor) LIKE %s ORDER BY apellido_autor, nombre_autor LIMIT 10",
        (
            "%" + query + "%",
            "%" + query + "%",
        ),
    )
    autores = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(autores)


@app.route("/api/generos", methods=["GET"])
def get_generos():
    query = request.args.get("q", "").lower()
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"SELECT id_genero, nombre_genero FROM generos WHERE LOWER(nombre_genero) LIKE %s ORDER BY nombre_genero LIMIT 10",
        ("%" + query + "%",),
    )
    generos = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(generos)


# Endpoint API para series (autocompletado)
@app.route("/api/series", methods=["GET"])
def get_series():
    query = request.args.get("q", "").lower()
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"SELECT id_serie, nombre_serie, descripcion_serie FROM series WHERE LOWER(nombre_serie) LIKE %s ORDER BY nombre_serie LIMIT 10",
        ("%" + query + "%",),
    )
    series = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(series)


# *** NUEVO ENDPOINT API para obtener libros para la selección de series ***
@app.route("/api/books_for_series_selection", methods=["GET"])
def get_books_for_series_selection():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    search_query = request.args.get("q", "").strip()

    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT o.id_obra, o.titulo_espanol, o.titulo_original, o.anio_publicacion,
               GROUP_CONCAT(CONCAT(a.nombre_autor, ' ', a.apellido_autor) SEPARATOR ', ') AS autores
        FROM obras o
        LEFT JOIN obra_autor oa ON o.id_obra = oa.id_obra
        LEFT JOIN autores a ON oa.id_autor = a.id_autor
    """
    where_clauses = []
    query_params = []

    if search_query:
        search_pattern = f"%{search_query}%"
        where_clauses.append(
            "(LOWER(o.titulo_espanol) LIKE %s OR LOWER(o.titulo_original) LIKE %s OR LOWER(a.nombre_autor) LIKE %s OR LOWER(a.apellido_autor) LIKE %s)"
        )
        query_params.extend(
            [search_pattern, search_pattern, search_pattern, search_pattern]
        )

    full_query = base_query
    if where_clauses:
        full_query += " WHERE " + " AND ".join(where_clauses)

    full_query += " GROUP BY o.id_obra, o.titulo_espanol, o.titulo_original, o.anio_publicacion ORDER BY o.titulo_espanol"

    cursor.execute(full_query, query_params)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(books)


# --- RUTAS para la gestión dedicada de series ---


@app.route("/api/series/check_name", methods=["GET"])
def check_series_name_exists():
    name = request.args.get("name", "").strip()
    # NUEVO: Obtener el ID de la serie si se está editando
    exclude_id = request.args.get("exclude_id", type=int)

    if not name:
        return jsonify({"error": "El parámetro 'name' es obligatorio."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = (
            "SELECT COUNT(*) AS count FROM series WHERE LOWER(nombre_serie) = LOWER(%s)"
        )
        params = [name]

        # MODIFICACIÓN CLAVE (Problema 1): Excluir la serie actual por ID
        if exclude_id is not None:
            query += " AND id_serie != %s"
            params.append(exclude_id)

        cursor.execute(query, tuple(params))
        result = cursor.fetchone()

        print(
            f"DEBUG API CHECK NAME: Name='{name}', ExcludeID={exclude_id}, Query='{query}', Params={params}, Exists={result['count'] > 0}"
        )
        return jsonify({"exists": result["count"] > 0})
    except Exception as e:
        print(f"Error checking series name existence: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Modificación en la ruta POST de new_series para validar unicidad
@app.route("/series/new", methods=["GET", "POST"])
def new_series():
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {
                "message": "Error al conectar con la base de datos.",
                "category": "danger",
                "redirect": url_for("index"),
            }
        ), 500

    cursor = conn.cursor(dictionary=True)  # Cursor para la ruta new_series
    try:
        if request.method == "GET":
            return render_template(
                "series_form.html",
                series={},
                all_books=[],
                series_id=None,
                current_series_books={},
            )

        if request.method == "POST":
            print("DEBUG FLASK POST (new_series): Recibiendo POST request.")
            data = request.get_json(silent=True)
            print(
                f"DEBUG FLASK POST (new_series): JSON data recibido por request.get_json(): {data}"
            )

            series_data_from_payload = (
                data.get("series_to_add")[0]
                if data and data.get("series_to_add")
                else {}
            )

            nombre_serie = series_data_from_payload.get("nombre_serie")
            descripcion_serie = series_data_from_payload.get("descripcion_serie", None)
            selected_books_with_order = series_data_from_payload.get(
                "libros_a_asignar", []
            )

            print(
                f"DEBUG FLASK POST (new_series): Extrayendo nombre_serie: '{nombre_serie}'"
            )
            # ... (otros prints de depuración) ...

            if not nombre_serie:
                return jsonify(
                    {
                        "message": "El nombre de la serie es obligatorio.",
                        "category": "danger",
                    }
                ), 400

            # --- MODIFICACIÓN CLAVE (Problema 3): Validación de unicidad aquí en el backend ---
            cursor.execute(
                "SELECT id_serie FROM series WHERE LOWER(nombre_serie) = LOWER(%s)",
                (nombre_serie,),
            )
            existing_series = cursor.fetchone()
            if existing_series:
                return jsonify(
                    {
                        "message": f"Ya existe una serie con el nombre '{nombre_serie}'. Por favor, elige un nombre diferente o edita la serie existente.",
                        "category": "danger",
                    }
                ), 409  # 409 Conflict
            # --- FIN MODIFICACIÓN CLAVE ---

            # ... (resto de la lógica de llamada al SP manage_bulk_series_assignments sin cambios) ...
            cursor_sp = conn.cursor()  # Usa un nuevo cursor para callproc si el cursor anterior es dictionary=True
            try:
                cursor_sp.callproc(
                    "manage_bulk_series_assignments",
                    (
                        json.dumps([]),  # p_book_ids_json (vacío para nuevas series)
                        json.dumps(
                            [
                                {  # p_series_to_add_json (solo la nueva serie)
                                    "nombre_serie": nombre_serie,
                                    "descripcion_serie": descripcion_serie,
                                    "libros_a_asignar": selected_books_with_order,
                                }
                            ]
                        ),
                        json.dumps([]),  # p_series_to_remove_json (vacío)
                    ),
                )
                conn.commit()
                return jsonify(
                    {
                        "message": "Serie guardada exitosamente.",
                        "redirect": url_for("list_series"),
                        "category": "success",
                    }
                ), 200
            except mysql.connector.Error as err:
                conn.rollback()
                print(f"Error al guardar la serie (DB Error): {err}")
                return jsonify(
                    {
                        "message": f"Error al guardar la serie (DB): {str(err)}",
                        "category": "danger",
                    }
                ), 500
            except Exception as e:
                conn.rollback()
                print(f"Error inesperado al guardar la serie: {e}")
                return jsonify(
                    {
                        "message": f"Error inesperado al guardar la serie: {str(e)}",
                        "category": "danger",
                    }
                ), 500
            finally:
                if cursor_sp:
                    cursor_sp.close()  # Cierra el cursor del SP
    finally:  # Cierra la conexión al final de la función new_series
        if cursor:  # Cierra el cursor inicial si se usó
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Depuración para el Problema 2
@app.route("/series/<int:series_id>/edit", methods=["GET", "POST"])
def edit_series(series_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {
                "message": "Error al conectar con la base de datos.",
                "category": "danger",
                "redirect": url_for("index"),
            }
        ), 500

    # NUEVO PRINT DE DEPURACIÓN (Problema 2)
    print(
        f"DEBUG FLASK EDIT SERIES (ROUTE HIT): Request for series_id={series_id}, Method={request.method}"
    )

    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == "GET":
            # ... (Lógica GET sin cambios) ...
            cursor.execute(
                "SELECT id_serie, nombre_serie, descripcion_serie FROM series WHERE id_serie = %s",
                (series_id,),
            )
            series_data = cursor.fetchone()
            if not series_data:
                flash("Serie no encontrada.", "warning")
                return redirect(url_for("index"))

            cursor.execute(
                "SELECT id_obra, orden_en_serie FROM obra_serie WHERE id_serie = %s",
                (series_id,),
            )
            current_series_books = cursor.fetchall()

            series_books_map = {
                book["id_obra"]: book["orden_en_serie"] for book in current_series_books
            }

            return render_template(
                "series_form.html",
                series=series_data,
                all_books=[],
                series_id=series_id,
                current_series_books=series_books_map,
            )

        if request.method == "POST":
            print("DEBUG FLASK POST (edit_series): Recibiendo POST request.")
            data = request.get_json(silent=True)
            print(
                f"DEBUG FLASK POST (edit_series): JSON data recibido por request.get_json(): {data}"
            )

            series_data_from_payload = (
                data.get("series_to_add")[0]
                if data and data.get("series_to_add")
                else {}
            )

            nombre_serie = series_data_from_payload.get("nombre_serie")
            descripcion_serie = series_data_from_payload.get("descripcion_serie", None)
            selected_books_with_order = series_data_from_payload.get(
                "libros_a_asignar", []
            )

            print(
                f"DEBUG FLASK POST (edit_series): Extrayendo nombre_serie: '{nombre_serie}'"
            )
            print(
                f"DEBUG FLASK POST (edit_series): series_id de la URL: {series_id}"
            )  # NUEVO PRINT DE DEPURACIÓN (Problema 2)

            if not nombre_serie:
                return jsonify(
                    {
                        "message": "El nombre de la serie es obligatorio.",
                        "category": "danger",
                    }
                ), 400

            # --- LLAMADA AL NUEVO PROCEDIMIENTO ALMACENADO edit_series_and_books ---
            p_books_with_order_json_sp = json.dumps(selected_books_with_order)

            cursor_sp = (
                conn.cursor()
            )  # Asegurarse de tener un cursor aquí para la llamada al SP
            try:
                cursor_sp.callproc(
                    "edit_series_and_books",
                    (
                        series_id,  # p_series_id (viene de la URL)
                        nombre_serie,  # p_nombre_serie
                        descripcion_serie,  # p_descripcion_serie
                        p_books_with_order_json_sp,  # p_books_with_order_json
                    ),
                )
                conn.commit()
                return jsonify(
                    {
                        "message": "Serie actualizada exitosamente.",
                        "redirect": url_for("list_series"),
                        "category": "success",
                    }
                ), 200
            except mysql.connector.Error as err:
                conn.rollback()
                print(f"Error al actualizar la serie (DB Error): {err}")
                return jsonify(
                    {
                        "message": f"Error al actualizar la serie (DB): {str(err)}",
                        "category": "danger",
                    }
                ), 500
            except Exception as e:
                conn.rollback()
                print(f"Error inesperado al actualizar la serie: {e}")
                return jsonify(
                    {
                        "message": f"Error inesperado al actualizar la serie: {str(e)}",
                        "category": "danger",
                    }
                ), 500
            finally:
                if cursor_sp:
                    cursor_sp.close()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/libro/form", defaults={"id_obra": None}, methods=["GET", "POST"])
@app.route("/libro/form/<id_obra>", methods=["GET", "POST"])
def form_libro(id_obra):
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {
                "message": "Error al conectar con la base de datos.",
                "category": "danger",
                "redirect": url_for("index"),
            }
        ), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # --- Obtener listas para dropdowns (sin cambios) ---
        cursor.execute("SELECT id_tipo_obra, tipo FROM tipos_obra ORDER BY tipo")
        tipos_obra_list = cursor.fetchall()

        cursor.execute(
            "SELECT id_tipo_encuadernacion, nombre_encuadernacion FROM tipos_encuadernacion ORDER BY nombre_encuadernacion"
        )
        tipos_encuadernacion_list = cursor.fetchall()

        # `editoriales_list` ya no se usa para un dropdown en el form, pero se mantiene si se usa para otra cosa
        editoriales_list = []  # Se pasa vacío o se elimina si no se usa.

        obra = {}
        if request.method == "GET":
            if id_obra:  # Modo edición
                # Consulta principal para obtener la obra y datos unidos
                cursor.execute(
                    """
                    SELECT o.*, e.adquirido AS estado_adquisicion_value, ed.nombre_editorial
                    FROM obras o
                    JOIN estado e ON o.estado_idestado = e.idestado
                    LEFT JOIN editoriales ed ON o.id_editorial = ed.id_editorial
                    WHERE o.id_obra = %s
                """,
                    (id_obra,),
                )
                obra = cursor.fetchone()

                if not obra:
                    flash("Obra no encontrada.", "warning")
                    return redirect(url_for("index"))

                # --- NUEVA LÓGICA DE FALLBACK PARA nombre_editorial ---
                # Si nombre_editorial es None a pesar del JOIN y id_editorial está presente,
                # intentar obtenerlo con una consulta directa.
                if (
                    obra.get("nombre_editorial") is None
                    and obra.get("id_editorial") is not None
                ):
                    print(
                        f"DEBUG FLASK: nombre_editorial es None para id_editorial={obra['id_editorial']}. Intentando consulta directa."
                    )
                    temp_cursor = conn.cursor(
                        dictionary=True
                    )  # Usar un cursor temporal
                    try:
                        temp_cursor.execute(
                            "SELECT nombre_editorial FROM editoriales WHERE id_editorial = %s",
                            (obra["id_editorial"],),
                        )
                        direct_editorial = temp_cursor.fetchone()
                        if direct_editorial:
                            obra["nombre_editorial"] = direct_editorial[
                                "nombre_editorial"
                            ]
                            print(
                                f"DEBUG FLASK: nombre_editorial recuperado directamente: {obra['nombre_editorial']}"
                            )
                        else:
                            print(
                                f"DEBUG FLASK: Consulta directa para id_editorial={obra['id_editorial']} tampoco encontró el nombre. Datos inconsistentes."
                            )
                    except Exception as e:
                        print(
                            f"DEBUG FLASK: Error en consulta directa de editorial: {e}"
                        )
                    finally:
                        if temp_cursor:
                            temp_cursor.close()
                # --- FIN NUEVA LÓGICA DE FALLBACK ---

                # Consultas para obtener autores, géneros e imágenes (sin cambios)
                cursor.execute(
                    """
                    SELECT a.id_autor, a.nombre_autor, a.apellido_autor
                    FROM autores a JOIN obra_autor oa ON a.id_autor = oa.id_autor
                    WHERE oa.id_obra = %s
                """,
                    (id_obra,),
                )
                obra["autores_data"] = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT g.id_genero, g.nombre_genero
                    FROM generos g JOIN obra_genero og ON g.id_genero = og.id_genero
                    WHERE og.id_obra = %s
                """,
                    (id_obra,),
                )
                obra["generos_data"] = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT url_imagen, descripcion
                    FROM imagenes_obra
                    WHERE id_obra = %s
                """,
                    (id_obra,),
                )
                obra["imagenes_data"] = cursor.fetchall()

            # # --- DEPURACIÓN: Datos de obra antes de renderizar la plantilla ---
            # print("\n--- DEBUG FLASK (form_libro GET): Obra data sent to template ---")
            # print(f"Obra (full dict): {obra}")
            # print(f"Tipo autores_data: {type(obra.get('autores_data'))}, Valor: {obra.get('autores_data')}")
            # print(f"Tipo generos_data: {type(obra.get('generos_data'))}, Valor: {obra.get('generos_data')}")
            # print(f"Tipo imagenes_data: {type(obra.get('imagenes_data'))}, Valor: {obra.get('imagenes_data')}")
            # print(f"Tipo id_editorial: {type(obra.get('id_editorial'))}, Valor: {obra.get('id_editorial')}")
            # print(f"Tipo editorial_nombre: {type(obra.get('nombre_editorial'))}, Valor: {obra.get('nombre_editorial')}")
            # print("----------------------------------------------------------------\n")
            # # --- FIN DEPURACIÓN ---

            return render_template(
                "form_libro.html",
                obra=obra,
                id_obra=id_obra,
                tipos_obra_list=tipos_obra_list,
                tipos_encuadernacion_list=tipos_encuadernacion_list,
                editoriales_list=[],
            )  # Mantenemos vacío ya que no se usa como select

        elif request.method == "POST":
            # ... (el resto del código POST sin cambios, ya está en la última versión) ...
            titulo_original = request.form["titulo_original"]
            titulo_espanol = request.form["titulo_espanol"]
            anio_publicacion = request.form["anio_publicacion"]
            sinopsis = request.form["sinopsis"]

            id_tipo_obra = request.form.get("id_tipo_obra")
            if not id_tipo_obra:
                return jsonify(
                    {
                        "message": "Error: Selecciona un Tipo de Obra.",
                        "category": "danger",
                    }
                ), 400
            id_tipo_obra = int(id_tipo_obra)

            # --- Manejo de Editorial Dinámica (sin cambios) ---
            nombre_editorial_from_form = request.form.get("nombre_editorial_input")
            id_editorial_from_form = request.form.get("id_editorial_selected")

            final_id_editorial_for_sp = None

            if not nombre_editorial_from_form:
                return jsonify(
                    {
                        "message": "Error: El campo Editorial es obligatorio.",
                        "category": "danger",
                    }
                ), 400

            if id_editorial_from_form and id_editorial_from_form.isdigit():
                final_id_editorial_for_sp = int(id_editorial_from_form)

            if final_id_editorial_for_sp is None:
                cursor.execute(
                    "SELECT id_editorial FROM editoriales WHERE LOWER(nombre_editorial) = LOWER(%s)",
                    (nombre_editorial_from_form,),
                )
                existing_editorial = cursor.fetchone()

                if existing_editorial:
                    final_id_editorial_for_sp = existing_editorial["id_editorial"]
                else:
                    cursor.execute(
                        "INSERT INTO editoriales (nombre_editorial) VALUES (%s)",
                        (nombre_editorial_from_form,),
                    )
                    conn.commit()
                    final_id_editorial_for_sp = cursor.lastrowid
                    print(
                        f"DEBUG FLASK: Nueva editorial creada: {nombre_editorial_from_form} con ID: {final_id_editorial_for_sp}"
                    )

            if final_id_editorial_for_sp is None:
                return jsonify(
                    {
                        "message": "Error: No se pudo determinar la editorial final.",
                        "category": "danger",
                    }
                ), 500
            # --- FIN Manejo de Editorial Dinámica ---

            numero_paginas = request.form.get("numero_paginas")
            isbn = request.form["isbn"]
            adquirido = int(request.form["adquirido"])

            id_tipo_encuadernacion = request.form.get("id_tipo_encuadernacion")
            if not id_tipo_encuadernacion:
                return jsonify(
                    {
                        "message": "Error: Selecciona un Tipo de Encuadernación.",
                        "category": "danger",
                    }
                ), 400
            id_tipo_encuadernacion = int(id_tipo_encuadernacion)

            nombre_encuadernacion = None
            cursor.execute(
                "SELECT nombre_encuadernacion FROM tipos_encuadernacion WHERE id_tipo_encuadernacion = %s",
                (id_tipo_encuadernacion,),
            )
            encuadernacion_result = cursor.fetchone()
            if encuadernacion_result:
                nombre_encuadernacion = encuadernacion_result["nombre_encuadernacion"]
            else:
                return jsonify(
                    {
                        "message": "Tipo de encuadernación no válido seleccionado.",
                        "category": "danger",
                    }
                ), 400

            autores_json_str = request.form.get("autores_selected_json", "[]")
            generos_json_str = request.form.get("generos_selected_json", "[]")
            imagenes_externas_json_str = request.form.get(
                "imagenes_externas_json", "[]"
            )

            try:
                autores_list = (
                    json.loads(autores_json_str) if autores_json_str.strip() else []
                )
                generos_list = (
                    json.loads(generos_json_str) if generos_json_str.strip() else []
                )
                imagenes_list_from_form = (
                    json.loads(imagenes_externas_json_str)
                    if imagenes_externas_json_str.strip()
                    else []
                )
            except json.JSONDecodeError as e:
                return jsonify(
                    {
                        "message": f"Error en el formato JSON enviado (autores, géneros o imágenes externas): {e}",
                        "category": "danger",
                    }
                ), 400

            uploaded_image_urls = []
            all_images_for_sp = uploaded_image_urls + imagenes_list_from_form

            autores_json_for_sp = json.dumps(
                [
                    {
                        "nombre": autor["nombre_autor"],
                        "apellido": autor["apellido_autor"],
                    }
                    for autor in autores_list
                ]
            )

            generos_json_for_sp = json.dumps(
                [genero["nombre_genero"] for genero in generos_list]
            )

            imagenes_json_for_sp = json.dumps(all_images_for_sp)

            cursor.execute(
                "SELECT tipo FROM tipos_obra WHERE id_tipo_obra = %s", (id_tipo_obra,)
            )
            tipo_obra_result = cursor.fetchone()
            if tipo_obra_result:
                tipo_obra_nombre = tipo_obra_result["tipo"]
            else:
                return jsonify(
                    {"message": "Tipo de obra no válido.", "category": "danger"}
                ), 400

            adquirido_estado_valor = adquirido

            try:
                ev = 2 if id_obra else 1
                flash_msg = (
                    "Obra actualizada exitosamente."
                    if id_obra
                    else "Obra registrada exitosamente."
                )

                cursor.callproc(
                    "gestionar_obra",
                    (
                        ev,
                        id_obra,
                        titulo_original,
                        titulo_espanol,
                        anio_publicacion,
                        sinopsis,
                        tipo_obra_nombre,
                        numero_paginas,
                        isbn,
                        adquirido_estado_valor,
                        autores_json_for_sp,
                        generos_json_for_sp,
                        imagenes_json_for_sp,
                        nombre_encuadernacion,
                        final_id_editorial_for_sp,  # Pasa el ID final de la editorial (existente o recién creada)
                    ),
                )
                conn.commit()

                return jsonify(
                    {
                        "message": flash_msg,
                        "redirect": url_for("index"),
                        "category": "success",
                    }
                )

            except mysql.connector.Error as err:
                conn.rollback()
                print(f"Error al guardar la obra: {err}")
                return jsonify(
                    {
                        "message": f"Error al guardar la obra: {err}",
                        "category": "danger",
                    }
                ), 500
            except Exception as e:
                conn.rollback()
                print(f"Error inesperado al guardar la obra: {e}")
                return jsonify(
                    {
                        "message": f"Error inesperado al guardar la obra: {str(e)}",
                        "category": "danger",
                    }
                ), 500
            finally:
                # El cursor principal se cierra en el finally más externo
                pass
    finally:
        # Cierra el cursor y la conexión al final de la función form_libro
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/libro/eliminar/<int:id_obra>", methods=["GET", "POST"])
def eliminar_libro(id_obra):
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {
                "message": "Error de conexión a la base de datos.",
                "category": "danger",
                "redirect": url_for("index"),
            }
        ), 500

    if request.method == "POST":
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM ranking_personal WHERE id_obra = %s", (id_obra,)
            )

            # *** MODIFICACIÓN DE LA LLAMADA AL SP: Añadir None para p_id_editorial ***
            cursor.callproc(
                "gestionar_obra",
                (
                    3,  # ev = 3 (Eliminar)
                    id_obra,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                ),
            )
            # *** FIN MODIFICACIÓN ***
            conn.commit()
            return jsonify(
                {
                    "message": "Obra eliminada exitosamente.",
                    "redirect": url_for("index"),
                    "category": "success",
                }
            )
        except mysql.connector.Error as err:
            conn.rollback()
            return jsonify(
                {"message": f"Error al eliminar la obra: {err}", "category": "danger"}
            ), 500
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT titulo_espanol FROM obras WHERE id_obra = %s", (id_obra,))
    obra_a_eliminar = cursor.fetchone()
    cursor.close()
    conn.close()

    if obra_a_eliminar:
        return render_template(
            "confirm_delete.html", obra=obra_a_eliminar, id_obra=id_obra
        )
    else:
        flash("Obra no encontrada para eliminar.", "warning")
        return redirect(url_for("index"))


# --- NUEVA RUTA: Página de listado de series ---
@app.route("/series")
def list_series():
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return render_template("series_list.html", series_list=[], search_query="")

    search_query = request.args.get("q", "").strip()

    cursor = conn.cursor(dictionary=True)
    try:
        # Paso 1: Obtener los datos de las series (con búsqueda)
        base_series_query = (
            "SELECT id_serie, nombre_serie, descripcion_serie FROM series"
        )
        series_where_clauses = []
        series_query_params = []

        if search_query:
            search_pattern = f"%{search_query}%"
            series_where_clauses.append(
                "(LOWER(nombre_serie) LIKE %s OR LOWER(descripcion_serie) LIKE %s)"
            )
            series_query_params.extend([search_pattern, search_pattern])

        full_series_query = base_series_query
        if series_where_clauses:
            full_series_query += " WHERE " + " AND ".join(series_where_clauses)
        full_series_query += " ORDER BY nombre_serie"

        cursor.execute(full_series_query, series_query_params)
        series_list = cursor.fetchall()  # Esto es una lista de diccionarios de series

        # Paso 2: Para cada serie, obtener sus libros asociados
        for series_item in series_list:
            cursor.execute(
                """
                SELECT os.orden_en_serie, o.id_obra, o.titulo_espanol, o.titulo_original
                FROM obra_serie os
                JOIN obras o ON os.id_obra = o.id_obra
                WHERE os.id_serie = %s
                ORDER BY os.orden_en_serie, o.titulo_espanol -- Ordenar por orden y luego título
            """,
                (series_item["id_serie"],),
            )
            series_item["books"] = (
                cursor.fetchall()
            )  # Añadir una clave 'books' a cada diccionario de serie

        return render_template(
            "series_list.html", series_list=series_list, search_query=search_query
        )
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# --- NUEVA RUTA para eliminar series ---
@app.route("/series/delete/<int:series_id>", methods=["GET", "POST"])
def delete_series(series_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {
                "message": "Error al conectar con la base de datos.",
                "category": "danger",
                "redirect": url_for("list_series"),
            }
        ), 500

    cursor = conn.cursor()
    try:
        if request.method == "POST":
            # Paso 1: Eliminar todas las relaciones en obra_serie para esta serie
            cursor.execute("DELETE FROM obra_serie WHERE id_serie = %s", (series_id,))

            # Paso 2: Eliminar la serie de la tabla series
            cursor.execute("DELETE FROM series WHERE id_serie = %s", (series_id,))

            conn.commit()
            return jsonify(
                {
                    "message": "Serie eliminada exitosamente.",
                    "redirect": url_for("list_series"),
                    "category": "success",
                }
            ), 200

        # Si es GET, simplemente mostrar la página de confirmación
        cursor.execute(
            "SELECT nombre_serie FROM series WHERE id_serie = %s", (series_id,)
        )
        series_to_delete = (
            cursor.fetchone()
        )  # Fetchone para obtener el nombre de la serie

        if series_to_delete:
            series_name = series_to_delete[
                0
            ]  # Acceder por índice 0 si cursor no es diccionario
            return render_template(
                "confirm_delete_series.html",
                series_name=series_name,
                series_id=series_id,
            )
        else:
            flash("Serie no encontrada para eliminar.", "warning")
            return redirect(url_for("list_series"))

    except mysql.connector.Error as err:
        conn.rollback()
        # Puedes añadir más detalle al error si es por restricción (ej. si aún tiene libros)
        print(f"Error al eliminar la serie (DB Error): {err}")
        return jsonify(
            {
                "message": f"Error al eliminar la serie (DB): {str(err)}",
                "category": "danger",
            }
        ), 500
    except Exception as e:
        conn.rollback()
        print(f"Error inesperado al eliminar la serie: {e}")
        return jsonify(
            {
                "message": f"Error inesperado al eliminar la serie: {str(e)}",
                "category": "danger",
            }
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/admin")
def admin_dashboard():
    # No necesita datos específicos de DB para esta página inicial
    return render_template("admin_dashboard.html")


MASTER_DATA_CONFIG = {
    "autores": {
        "table": "autores",
        "id_col": "id_autor",
        "name_cols": [
            "nombre_autor",
            "apellido_autor",
        ],  # Columnas por las que se puede buscar por nombre
        "display_name_sql": "CONCAT(nombre_autor, ' ', apellido_autor)",  # Cómo se muestra el nombre en SQL
        "singular_name": "Autor",
        "plural_name": "Autores",
        "create_url_suffix": "/new",  # Sufijo para la URL de creación (ej. /admin/autores/new)
        "edit_url_suffix": "/edit",  # Sufijo para la URL de edición
        "delete_url_suffix": "/delete",  # Sufijo para la URL de eliminación
    },
    "generos": {
        "table": "generos",
        "id_col": "id_genero",
        "name_cols": ["nombre_genero"],
        "display_name_sql": "nombre_genero",
        "singular_name": "Género",
        "plural_name": "Géneros",
        "create_url_suffix": "/new",
        "edit_url_suffix": "/edit",
        "delete_url_suffix": "/delete",
    },
    "tipos_obra": {
        "table": "tipos_obra",
        "id_col": "id_tipo_obra",
        "name_cols": ["tipo"],
        "display_name_sql": "tipo",
        "singular_name": "Tipo de Obra",
        "plural_name": "Tipos de Obra",
        "create_url_suffix": "/new",
        "edit_url_suffix": "/edit",
        "delete_url_suffix": "/delete",
    },
    "tipos_encuadernacion": {
        "table": "tipos_encuadernacion",
        "id_col": "id_tipo_encuadernacion",
        "name_cols": ["nombre_encuadernacion"],
        "display_name_sql": "nombre_encuadernacion",
        "singular_name": "Tipo de Encuadernación",
        "plural_name": "Tipos de Encuadernación",
        "create_url_suffix": "/new",
        "edit_url_suffix": "/edit",
        "delete_url_suffix": "/delete",
    },
    "editoriales": {
        "table": "editoriales",
        "id_col": "id_editorial",
        "name_cols": ["nombre_editorial"],
        "display_name_sql": "nombre_editorial",
        "singular_name": "Editorial",
        "plural_name": "Editoriales",
        "create_url_suffix": "/new",  # Ahora sí se puede crear
        "edit_url_suffix": "/edit",  # Ahora sí se puede editar
        "delete_url_suffix": "/delete",  # Ahora sí se puede eliminar
    },
}


@app.route("/admin/<string:data_type>")
def list_master_data(data_type):
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return redirect(url_for("admin_dashboard"))

    # Verificar si el data_type es válido según nuestra configuración
    if data_type not in MASTER_DATA_CONFIG:
        flash("Tipo de dato maestro no válido.", "danger")
        return redirect(url_for("admin_dashboard"))

    config = MASTER_DATA_CONFIG[data_type]  # Obtener la configuración específica

    cursor = conn.cursor(
        dictionary=True
    )  # Usamos cursor de diccionario para fácil acceso por nombre
    try:
        search_query = request.args.get(
            "q", ""
        ).strip()  # Parámetro de búsqueda para la lista

        # Construir la consulta SQL dinámicamente
        base_query = f"SELECT {config['id_col']}, {config['display_name_sql']} AS display_name FROM {config['table']}"
        where_clauses = []
        query_params = []

        if search_query:
            search_pattern = f"%{search_query}%"
            # Buscar en todas las columnas de nombre configuradas para este tipo de dato
            name_search_clauses = []
            for col in config["name_cols"]:
                name_search_clauses.append(f"LOWER({col}) LIKE %s")
                query_params.append(search_pattern)
            if (
                name_search_clauses
            ):  # Solo añadir si hay cláusulas de búsqueda de nombre
                where_clauses.append("(" + " OR ".join(name_search_clauses) + ")")

        full_query = base_query
        if where_clauses:
            full_query += " WHERE " + " AND ".join(where_clauses)
        full_query += f" ORDER BY {config['id_col']}"  # Ordenar por el ID de la columna

        # Depuración
        print(f"DEBUG MASTER_DATA_LIST: Query: {full_query}")
        print(f"DEBUG MASTER_DATA_LIST: Params: {query_params}")

        cursor.execute(full_query, query_params)
        items_list = cursor.fetchall()  # Obtener todos los elementos maestros

        # Renderizar la plantilla genérica de listado de datos maestros
        return render_template(
            "master_list.html",
            data_type=data_type,  # Tipo de dato actual (ej. 'autores')
            items_list=items_list,  # La lista de elementos a mostrar
            search_query=search_query,  # La query de búsqueda actual
            config=config,
        )  # Pasar la configuración para usar en la plantilla
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


MASTER_DATA_FORM_FIELDS = {
    "autores": [
        {"name": "nombre_autor", "label": "Nombre", "type": "text", "required": True},
        {
            "name": "apellido_autor",
            "label": "Apellido",
            "type": "text",
            "required": True,
        },
    ],
    "generos": [
        {
            "name": "nombre_genero",
            "label": "Nombre del Género",
            "type": "text",
            "required": True,
        },
    ],
    "tipos_obra": [
        {"name": "tipo", "label": "Tipo de Obra", "type": "text", "required": True},
    ],
    "tipos_encuadernacion": [
        {
            "name": "nombre_encuadernacion",
            "label": "Nombre de Encuadernación",
            "type": "text",
            "required": True,
        },
    ],
    "editoriales": [  # Solo listado, pero si se habilitara edición, estos serían sus campos
        {
            "name": "nombre_editorial",
            "label": "Nombre de la Editorial",
            "type": "text",
            "required": True,
        },
    ],
}


@app.route("/admin/<string:data_type>/new", methods=["GET", "POST"])
def create_master_data(data_type):
    # Llama a la lógica principal de manage_master_data con item_id=None
    return manage_master_data_logic(data_type, item_id=None)


# Ruta para editar un elemento maestro existente (lleva item_id numérico en la URL)
@app.route("/admin/<string:data_type>/<int:item_id>/edit", methods=["GET", "POST"])
def edit_master_data(data_type, item_id):
    # Llama a la lógica principal de manage_master_data con el item_id
    return manage_master_data_logic(data_type, item_id=item_id)


# *** NUEVA FUNCIÓN: Lógica principal unificada para crear y editar ***
def manage_master_data_logic(
    data_type, item_id
):  # Ahora esta es la función que tiene el código
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return redirect(url_for("admin_dashboard"))

    # Validar data_type
    if data_type not in MASTER_DATA_CONFIG:
        flash("Tipo de dato maestro no válido.", "danger")
        return redirect(url_for("admin_dashboard"))

    config = MASTER_DATA_CONFIG[data_type]
    form_fields = MASTER_DATA_FORM_FIELDS[data_type]

    cursor = conn.cursor(dictionary=True)
    try:
        # --- Lógica para GET: Mostrar el formulario ---
        if request.method == "GET":
            item_data = {}  # Diccionario para pre-llenar el formulario en edición
            if item_id:  # Modo edición
                # Asegurarse de que el sufijo de edición esté definido para este tipo
                if not config.get("edit_url_suffix"):
                    flash(
                        f"Edición no permitida para {config['plural_name']}.", "warning"
                    )
                    return redirect(url_for("list_master_data", data_type=data_type))

                query = f"SELECT * FROM {config['table']} WHERE {config['id_col']} = %s"
                cursor.execute(query, (item_id,))
                item_data = cursor.fetchone()
                if not item_data:
                    flash(f"{config['singular_name']} no encontrado.", "warning")
                    return redirect(url_for("list_master_data", data_type=data_type))

            # Renderizar el formulario genérico
            return render_template(
                "master_form.html",
                data_type=data_type,
                item_id=item_id,  # item_id será None o el ID numérico
                item_data=item_data,
                config=config,
                form_fields=form_fields,
            )

        # --- Lógica para POST: Procesar el formulario ---
        if request.method == "POST":
            data = request.get_json(silent=True)
            if not data:
                return jsonify(
                    {
                        "message": "Datos no recibidos en formato JSON válido.",
                        "category": "danger",
                    }
                ), 400

            # Validar campos requeridos y recolectar valores
            values = {}
            for field in form_fields:
                value = data.get(field["name"])
                if field["required"] and (value is None or str(value).strip() == ""):
                    return jsonify(
                        {
                            "message": f"El campo '{field['label']}' es obligatorio.",
                            "category": "danger",
                        }
                    ), 400
                values[field["name"]] = (
                    str(value).strip() if value is not None else None
                )

            # Construir la consulta SQL (INSERT o UPDATE)
            if item_id:  # Modo edición (UPDATE)
                # Asegurarse de que la edición esté permitida
                if not config.get("edit_url_suffix"):
                    return jsonify(
                        {
                            "message": f"Edición no permitida para {config['plural_name']}.",
                            "category": "warning",
                        }
                    ), 403

                set_clauses = []
                update_params = []
                for field in form_fields:
                    set_clauses.append(f"{field['name']} = %s")
                    update_params.append(values[field["name"]])

                update_params.append(item_id)  # Último parámetro es el ID para WHERE
                query = f"UPDATE {config['table']} SET {', '.join(set_clauses)} WHERE {config['id_col']} = %s"

                flash_msg = f"{config['singular_name']} actualizado(a) exitosamente."

            else:  # Modo creación (INSERT)
                # Asegurarse de que la creación esté permitida
                if not config.get("create_url_suffix"):
                    return jsonify(
                        {
                            "message": f"Creación no permitida para {config['plural_name']}.",
                            "category": "warning",
                        }
                    ), 403

                cols = []
                insert_params = []
                for field in form_fields:
                    cols.append(field["name"])
                    insert_params.append(values[field["name"]])

                placeholders = ", ".join(["%s"] * len(cols))
                query = f"INSERT INTO {config['table']} ({', '.join(cols)}) VALUES ({placeholders})"

                flash_msg = f"{config['singular_name']} creado(a) exitosamente."

            # Ejecutar la consulta SQL
            print(f"DEBUG MASTER_DATA_CRUD: Query: {query}")
            print(
                f"DEBUG MASTER_DATA_CRUD: Params: {update_params if item_id else insert_params}"
            )

            cursor.execute(query, update_params if item_id else insert_params)
            conn.commit()

            return jsonify(
                {
                    "message": flash_msg,
                    "redirect": url_for("list_master_data", data_type=data_type),
                    "category": "success",
                }
            ), 200

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error DB al gestionar {data_type}: {err}")
        if err.errno == 1062:  # Duplicate entry for key (ej. nombre_genero UNIQUE)
            return jsonify(
                {
                    "message": f"Error: Ya existe un(a) {config['singular_name'].lower()} con este nombre.",
                    "category": "danger",
                }
            ), 400
        return jsonify(
            {
                "message": f"Error al guardar {config['singular_name'].lower()}: {str(err)}",
                "category": "danger",
            }
        ), 500
    except Exception as e:
        conn.rollback()
        print(f"Error inesperado al gestionar {data_type}: {e}")
        return jsonify(
            {
                "message": f"Error inesperado al guardar {config['singular_name'].lower()}: {str(e)}",
                "category": "danger",
            }
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/admin/<string:data_type>/<int:item_id>/delete", methods=["POST"])
def delete_master_data(data_type, item_id):
    conn = get_db_connection()
    if conn is None:
        # Si no hay conexión a DB, devolver JSON de error y redirección
        return jsonify(
            {
                "message": "Error al conectar con la base de datos.",
                "category": "danger",
                "redirect": url_for("admin_dashboard"),
            }
        ), 500

    # Validar data_type
    if data_type not in MASTER_DATA_CONFIG:
        flash("Tipo de dato maestro no válido.", "danger")
        # Devolver JSON de error, ya que esta ruta será llamada por AJAX
        return jsonify(
            {"message": "Tipo de dato maestro no válido.", "category": "danger"}
        ), 404  # 404 Not Found

    config = MASTER_DATA_CONFIG[data_type]  # Obtener la configuración específica

    # Verificar si la eliminación está permitida para este tipo (según config.delete_url_suffix)
    if not config.get("delete_url_suffix"):
        return jsonify(
            {
                "message": f"Eliminación no permitida para {config['plural_name']}.",
                "category": "warning",
            }
        ), 403  # 403 Forbidden

    cursor = conn.cursor()  # Crear cursor aquí
    try:
        flash_msg = ""  # Mensaje por defecto

        if data_type == "autores":
            # `autores` tiene ON DELETE CASCADE en `obra_autor`, así que la eliminación es directa
            query = f"DELETE FROM {config['table']} WHERE {config['id_col']} = %s"
            cursor.execute(query, (item_id,))
            flash_msg = f"{config['singular_name']} eliminado(a) exitosamente."
        elif data_type in ["generos", "tipos_obra", "tipos_encuadernacion"]:
            # Estas tablas tienen ON DELETE RESTRICT si están en uso por obras.
            # Primero verificar si el elemento está siendo utilizado.
            is_in_use = False
            if data_type == "generos":
                cursor.execute(
                    "SELECT 1 FROM obra_genero WHERE id_genero = %s LIMIT 1", (item_id,)
                )
                is_in_use = cursor.fetchone() is not None
            elif data_type == "tipos_obra":
                cursor.execute(
                    "SELECT 1 FROM obras WHERE id_tipo_obra = %s LIMIT 1", (item_id,)
                )
                is_in_use = cursor.fetchone() is not None
            elif data_type == "tipos_encuadernacion":
                cursor.execute(
                    "SELECT 1 FROM obras WHERE id_tipo_encuadernacion = %s LIMIT 1",
                    (item_id,),
                )
                is_in_use = cursor.fetchone() is not None

            if is_in_use:
                return jsonify(
                    {
                        "message": f"No se puede eliminar {config['singular_name'].lower()} porque está siendo utilizado(a) por una o más obras.",
                        "category": "danger",
                    }
                ), 409  # 409 Conflict

            # Si no está en uso, proceder con la eliminación
            query = f"DELETE FROM {config['table']} WHERE {config['id_col']} = %s"
            cursor.execute(query, (item_id,))
            flash_msg = f"{config['singular_name']} eliminado(a) exitosamente."

        elif data_type == "editoriales":
            # `editoriales` tiene ON DELETE RESTRICT en `obras`.
            # Verificar si está en uso por obras.
            cursor.execute(
                "SELECT 1 FROM obras WHERE id_editorial = %s LIMIT 1", (item_id,)
            )
            is_in_use = cursor.fetchone() is not None

            if is_in_use:
                return jsonify(
                    {
                        "message": f"No se puede eliminar la editorial porque está siendo utilizada por una o más obras. Normalice la tabla de obras primero.",
                        "category": "danger",
                    }
                ), 409  # 409 Conflict

            # Si no está en uso, proceder con la eliminación
            query = f"DELETE FROM {config['table']} WHERE {config['id_col']} = %s"
            cursor.execute(query, (item_id,))
            flash_msg = f"{config['singular_name']} eliminado(a) exitosamente."

        else:  # Si se llega aquí con un data_type no cubierto por la lógica específica
            flash_msg = "Operación de eliminación no definida para este tipo de dato."
            return jsonify({"message": flash_msg, "category": "danger"}), 400

        conn.commit()
        # Devolver JSON de éxito y redirección
        return jsonify(
            {
                "message": flash_msg,
                "redirect": url_for("list_master_data", data_type=data_type),
                "category": "success",
            }
        ), 200

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error DB al eliminar {data_type}: {err}")
        # Error específico de FK (ej. 1451) si ON DELETE RESTRICT no se manejó antes
        if (
            err.errno == 1451
        ):  # Cannot delete or update a parent row: a foreign key constraint fails
            return jsonify(
                {
                    "message": f"No se puede eliminar {config['singular_name'].lower()} porque tiene registros relacionados. Elimine primero los registros dependientes.",
                    "category": "danger",
                }
            ), 409
        return jsonify(
            {
                "message": f"Error al eliminar {config['singular_name'].lower()}: {str(err)}",
                "category": "danger",
            }
        ), 500
    except Exception as e:
        conn.rollback()
        print(f"Error inesperado al eliminar {data_type}: {e}")
        return jsonify(
            {
                "message": f"Error inesperado al eliminar {config['singular_name'].lower()}: {str(e)}",
                "category": "danger",
            }
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# --- MODIFICACIÓN: Endpoint API para Valorar un libro ---
@app.route("/api/rate_book", methods=["POST"])
def rate_book():
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {"message": "Error al conectar con la base de datos.", "category": "danger"}
        ), 500

    cursor = conn.cursor()
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify(
                {
                    "message": "Datos no recibidos en formato JSON válido.",
                    "category": "danger",
                }
            ), 400

        id_obra = data.get("id_obra")
        puntuacion = data.get("puntuacion")
        comentarios = data.get("comentarios", None)
        fecha_ranking = data.get("fecha_ranking", None)  # Formato esperado 'YYYY-MM-DD'

        if not id_obra:
            return jsonify(
                {
                    "message": "ID de obra es obligatorio para valorar.",
                    "category": "danger",
                }
            ), 400

        # --- VALIDACIÓN REFORZADA (Solo para valores que se van a GUARDAR) ---
        if puntuacion is None or comentarios is None or fecha_ranking is None:
            # Si al menos uno de los campos principales de valoración es None,
            # y no estamos en el endpoint de eliminación, y no hay otros datos,
            # podría ser una señal de que no se quiere guardar nada.
            # Sin embargo, la validación principal ya lo maneja.
            # Aquí, si puntuacion es None, pero se intenta guardar, el REPLACE INTO fallaría por NOT NULL.
            # Así que, si puntuacion es None, simplemente no intentamos el REPLACE INTO.
            if puntuacion is None:
                return jsonify(
                    {
                        "message": "La puntuación es obligatoria para guardar una valoración.",
                        "category": "danger",
                    }
                ), 400

        try:
            puntuacion = float(puntuacion)  # Usar float para permitir 0.5, etc.
            # Si en la BD es INT, esta conversión a float podría ser problema o truncar.
            # Si es INT en la BD, la validación 1-10 es crucial.
            if not (1 <= puntuacion <= 10):
                return jsonify(
                    {
                        "message": "La puntuación debe ser entre 1 y 10.",
                        "category": "danger",
                    }
                ), 400
        except (ValueError, TypeError):
            return jsonify(
                {
                    "message": "La puntuación debe ser un número válido.",
                    "category": "danger",
                }
            ), 400
        # --- FIN VALIDACIÓN REFORZADA ---

        # Lógica para insertar o actualizar ranking_personal
        # REPLACE INTO funciona porque id_obra es UNIQUE en ranking_personal.
        insert_update_query = """
        REPLACE INTO ranking_personal (id_obra, puntuacion, comentarios, fecha_ranking)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(
            insert_update_query, (id_obra, puntuacion, comentarios, fecha_ranking)
        )
        conn.commit()

        return jsonify(
            {"message": "Valoración guardada exitosamente.", "category": "success"}
        ), 200

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error al guardar valoración (DB Error): {err}")
        if err.errno == 1062:
            return jsonify(
                {
                    "message": "Ya existe una valoración para esta obra.",
                    "category": "danger",
                }
            ), 409
        return jsonify(
            {
                "message": f"Error al guardar valoración: {str(err)}",
                "category": "danger",
            }
        ), 500
    except Exception as e:
        conn.rollback()
        print(f"Error inesperado al guardar valoración: {e}")
        return jsonify(
            {
                "message": f"Error inesperado al guardar valoración: {str(e)}",
                "category": "danger",
            }
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# --- NUEVO ENDPOINT API: Eliminar valoración de un libro ---
@app.route("/api/delete_rating/<int:id_obra>", methods=["POST"])
def delete_rating(id_obra):
    conn = get_db_connection()
    if conn is None:
        return jsonify(
            {"message": "Error al conectar con la base de datos.", "category": "danger"}
        ), 500

    cursor = conn.cursor()
    try:
        if not id_obra:
            return jsonify(
                {
                    "message": "ID de obra es obligatorio para eliminar la valoración.",
                    "category": "danger",
                }
            ), 400

        cursor.execute("DELETE FROM ranking_personal WHERE id_obra = %s", (id_obra,))
        conn.commit()

        if cursor.rowcount > 0:  # rowcount > 0 si se eliminó alguna fila
            return jsonify(
                {"message": "Valoración eliminada exitosamente.", "category": "success"}
            ), 200
        else:
            return jsonify(
                {
                    "message": "No se encontró valoración para eliminar.",
                    "category": "warning",
                }
            ), 404

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Error al eliminar valoración (DB Error): {err}")
        return jsonify(
            {
                "message": f"Error al eliminar valoración: {str(err)}",
                "category": "danger",
            }
        ), 500
    except Exception as e:
        conn.rollback()
        print(f"Error inesperado al eliminar valoración: {e}")
        return jsonify(
            {
                "message": f"Error inesperado al eliminar valoración: {str(e)}",
                "category": "danger",
            }
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# --- NUEVA RUTA: Ver detalles de una serie y sus libros ---
@app.route("/series/<int:series_id>")
def view_series_detail(series_id):
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return redirect(
            url_for("list_series")
        )  # Redirigir a la lista de series si falla la conexión

    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Obtener los detalles de la serie
        cursor.execute(
            "SELECT id_serie, nombre_serie, descripcion_serie FROM series WHERE id_serie = %s",
            (series_id,),
        )
        series_data = cursor.fetchone()
        if not series_data:
            flash("Serie no encontrada.", "warning")
            return redirect(url_for("list_series"))

        # 2. Obtener todos los libros asociados a esta serie, con sus detalles y orden
        # Esta consulta es similar a vista_obras_detalles pero filtrada por id_serie
        books_in_series_query = """
            SELECT
                os.orden_en_serie,
                o.id_obra,
                o.titulo_original,
                o.titulo_espanol,
                o.anio_publicacion,
                o.sinopsis,
                tp.tipo AS tipo_obra,
                o.numero_paginas,
                o.isbn,
                e.adquirido AS estado_adquisicion,
                GROUP_CONCAT(DISTINCT CONCAT(a.nombre_autor, ' ', a.apellido_autor) SEPARATOR '; ') AS autores,
                GROUP_CONCAT(DISTINCT g.nombre_genero SEPARATOR '; ') AS generos,
                GROUP_CONCAT(DISTINCT CONCAT(io.url_imagen, ' [', io.descripcion, ']') SEPARATOR '; ') AS imagenes_con_descripcion,
                rp.puntuacion AS ranking_personal_puntuacion,
                rp.comentarios AS ranking_personal_comentarios,
                rp.fecha_ranking AS ranking_personal_fecha,
                te.nombre_encuadernacion,
                ed.nombre_editorial AS editorial_nombre
            FROM
                obra_serie os
            JOIN
                obras o ON os.id_obra = o.id_obra
            LEFT JOIN
                tipos_obra tp ON o.id_tipo_obra = tp.id_tipo_obra
            LEFT JOIN
                estado e ON o.estado_idestado = e.idestado
            LEFT JOIN
                obra_autor oa ON o.id_obra = oa.id_obra
            LEFT JOIN
                autores a ON oa.id_autor = a.id_autor
            LEFT JOIN
                obra_genero og ON o.id_obra = og.id_obra
            LEFT JOIN
                generos g ON og.id_genero = g.id_genero
            LEFT JOIN
                imagenes_obra io ON o.id_obra = io.id_obra
            LEFT JOIN
                ranking_personal rp ON o.id_obra = rp.id_obra
            LEFT JOIN
                tipos_encuadernacion te ON o.id_tipo_encuadernacion = te.id_tipo_encuadernacion
            LEFT JOIN
                editoriales ed ON o.id_editorial = ed.id_editorial
            WHERE
                os.id_serie = %s
            GROUP BY
                os.orden_en_serie, o.id_obra, o.titulo_original, o.titulo_espanol, o.anio_publicacion,
                o.sinopsis, tp.tipo, o.numero_paginas, o.isbn, e.adquirido,
                rp.puntuacion, rp.comentarios, rp.fecha_ranking,
                te.nombre_encuadernacion, ed.nombre_editorial
            ORDER BY
                os.orden_en_serie, o.titulo_espanol;
        """

        print(f"DEBUG SERIES DETAIL: Fetching books for series ID: {series_id}")
        cursor.execute(books_in_series_query, (series_id,))
        books_in_series = cursor.fetchall()

        # Asegurar que id_obra sea int y filtrar None (similar a la ruta index)
        processed_books_in_series = []
        for book_dict in books_in_series:
            current_id_obra = None
            if (
                isinstance(book_dict, dict)
                and "id_obra" in book_dict
                and book_dict["id_obra"] is not None
            ):
                try:
                    current_id_obra = int(book_dict["id_obra"])
                except (ValueError, TypeError):
                    current_id_obra = None
            else:
                current_id_obra = None

            book_dict["id_obra"] = current_id_obra

            if book_dict["id_obra"] is not None:
                processed_books_in_series.append(book_dict)
            else:
                print(
                    f"DEBUG FLASK SERIES DETAIL: Saltando libro con id_obra faltante/inválido en serie {series_id}: {book_dict}"
                )

        return render_template(
            "series_detail.html", series=series_data, books=processed_books_in_series
        )
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return render_template("dashboard.html", stats={})

    cursor = conn.cursor(dictionary=True)
    stats = {}  # Diccionario para almacenar todas las estadísticas
    try:
        # 1. Resumen General de la Colección
        cursor.execute("SELECT COUNT(*) AS total_libros FROM obras")
        stats["total_libros"] = cursor.fetchone()["total_libros"]

        cursor.execute("""
            SELECT 
                estado.adquirido, 
                COUNT(obras.id_obra) AS count 
            FROM obras 
            JOIN estado ON obras.estado_idestado = estado.idestado 
            GROUP BY estado.adquirido
        """)
        adquiridos_data = cursor.fetchall()
        stats["libros_adquiridos"] = next(
            (item["count"] for item in adquiridos_data if item["adquirido"] == 1), 0
        )
        stats["libros_no_adquiridos"] = next(
            (item["count"] for item in adquiridos_data if item["adquirido"] == 0), 0
        )

        cursor.execute("SELECT COUNT(DISTINCT id_autor) AS total_autores FROM autores")
        stats["total_autores"] = cursor.fetchone()["total_autores"]

        cursor.execute("SELECT COUNT(DISTINCT id_genero) AS total_generos FROM generos")
        stats["total_generos"] = cursor.fetchone()["total_generos"]

        cursor.execute(
            "SELECT COUNT(DISTINCT id_editorial) AS total_editoriales FROM editoriales"
        )
        stats["total_editoriales"] = cursor.fetchone()["total_editoriales"]

        cursor.execute("SELECT COUNT(DISTINCT id_serie) AS total_series FROM series")
        stats["total_series"] = cursor.fetchone()["total_series"]

        # *** NUEVO: Libros Leídos (basado en tener valoración) ***
        cursor.execute(
            "SELECT COUNT(*) AS libros_leidos FROM ranking_personal WHERE puntuacion IS NOT NULL"
        )
        stats["libros_leidos"] = cursor.fetchone()["libros_leidos"]
        stats["libros_no_leidos"] = (
            stats["total_libros"] - stats["libros_leidos"]
        )  # Derivado

        # 2. Estadísticas por Categoría (para gráficos de torta)
        cursor.execute("""
            SELECT g.nombre_genero, COUNT(og.id_obra) AS count 
            FROM generos g 
            JOIN obra_genero og ON g.id_genero = og.id_genero 
            GROUP BY g.nombre_genero 
            ORDER BY count DESC LIMIT 8
        """)
        stats["libros_por_genero"] = cursor.fetchall()

        cursor.execute("""
            SELECT CONCAT(a.nombre_autor, ' ', a.apellido_autor) AS author_name, COUNT(oa.id_obra) AS count 
            FROM autores a 
            JOIN obra_autor oa ON a.id_autor = oa.id_autor 
            GROUP BY author_name 
            ORDER BY count DESC
            LIMIT 5
        """)
        stats["top_5_autores"] = cursor.fetchall()

        cursor.execute("""
            SELECT ed.nombre_editorial, COUNT(o.id_obra) AS count 
            FROM editoriales ed 
            JOIN obras o ON ed.id_editorial = o.id_editorial 
            GROUP BY ed.nombre_editorial 
            ORDER BY count DESC
            LIMIT 5
        """)
        stats["top_5_editoriales"] = cursor.fetchall()

        cursor.execute("""
            SELECT tipo.tipo, COUNT(o.id_obra) AS count 
            FROM tipos_obra tipo 
            JOIN obras o ON tipo.id_tipo_obra = o.id_tipo_obra 
            GROUP BY tipo.tipo 
            ORDER BY count DESC
        """)
        stats["libros_por_tipo_obra"] = cursor.fetchall()

        cursor.execute("""
            SELECT te.nombre_encuadernacion, COUNT(o.id_obra) AS count 
            FROM tipos_encuadernacion te 
            JOIN obras o ON te.id_tipo_encuadernacion = o.id_tipo_encuadernacion 
            GROUP BY te.nombre_encuadernacion 
            ORDER BY count DESC
        """)
        stats["libros_por_encuadernacion"] = cursor.fetchall()

        # 3. Estadísticas de Valoración
        cursor.execute(
            "SELECT AVG(puntuacion) AS promedio_puntuacion FROM ranking_personal WHERE puntuacion IS NOT NULL"
        )
        promedio = cursor.fetchone()["promedio_puntuacion"]
        stats["promedio_puntuacion"] = round(float(promedio), 2) if promedio else 0.0

        # Top 3 libros mejor valorados
        cursor.execute("""
            SELECT o.titulo_espanol, rp.puntuacion 
            FROM obras o 
            JOIN ranking_personal rp ON o.id_obra = rp.id_obra 
            ORDER BY rp.puntuacion DESC 
            LIMIT 3
        """)
        stats["top_3_libros_valorados"] = cursor.fetchall()

        # print(f"DEBUG DASHBOARD: Estadísticas calculadas: {stats}") # Para depuración

        return render_template("dashboard.html", stats=stats)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# --- NUEVO ENDPOINT API: Obtener libros filtrados por criterio ---
@app.route("/api/books_by_filter", methods=["GET"])
def get_books_by_filter():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection error"}), 500

    filter_type = request.args.get("filter_type", "").strip()
    filter_value = request.args.get("filter_value", "").strip()

    if not filter_type or not filter_value:
        return jsonify(
            {
                "message": "filter_type y filter_value son obligatorios.",
                "category": "danger",
            }
        ), 400

    cursor = conn.cursor(dictionary=True)
    try:
        base_query = "SELECT * FROM vista_obras_detalles"
        where_clauses = []
        query_params = []

        # Lógica para construir la cláusula WHERE basada en filter_type
        if filter_type == "genre":
            # Busca por nombre de género. Asume que vista_obras_detalles.generos es un GROUP_CONCAT de nombres.
            where_clauses.append("generos LIKE %s")
            query_params.append(f"%{filter_value}%")
        elif filter_type == "editorial":
            # Busca por nombre de editorial. Asume vista_obras_detalles.editorial_nombre
            where_clauses.append("editorial_nombre LIKE %s")
            query_params.append(f"%{filter_value}%")
        elif filter_type == "work_type":
            # Busca por nombre de tipo de obra. Asume vista_obras_detalles.tipo_obra
            where_clauses.append("tipo_obra LIKE %s")
            query_params.append(f"%{filter_value}%")
        elif filter_type == "binding_type":
            # Busca por nombre de tipo de encuadernación. Asume vista_obras_detalles.nombre_encuadernacion
            where_clauses.append("nombre_encuadernacion LIKE %s")
            query_params.append(f"%{filter_value}%")
        elif filter_type == "acquired":
            # Busca por estado adquirido (0 o 1). Asume vista_obras_detalles.estado_adquisicion
            # Asegura que el valor sea '0' o '1'
            if filter_value in ["0", "1"]:
                where_clauses.append("estado_adquisicion = %s")
                query_params.append(filter_value)
            else:
                return jsonify(
                    {
                        "message": "Valor de filtro 'adquirido' no válido.",
                        "category": "danger",
                    }
                ), 400
        elif filter_type == "read_status":
            # Busca por estado de lectura (leído si tiene ranking, no leído si no)
            if filter_value == "leidos":
                where_clauses.append("ranking_personal_puntuacion IS NOT NULL")
            elif filter_value == "no_leidos":
                where_clauses.append("ranking_personal_puntuacion IS NULL")
            else:
                return jsonify(
                    {
                        "message": "Valor de filtro 'read_status' no válido.",
                        "category": "danger",
                    }
                ), 400
        elif (
            filter_type == "author"
        ):  # Aunque no hay gráfico para top autores, el filtro es útil
            where_clauses.append("autores LIKE %s")
            query_params.append(f"%{filter_value}%")
        elif (
            filter_type == "ranking"
        ):  # Aunque no hay gráfico para ranking, el filtro es útil
            # Aquí filter_value podría ser un rango o un valor específico si viene de un segmento de ranking
            # Para simplificar ahora, si se clica en un top ranking, se mostrará solo ese.
            # O se asume que este filtro no se activará desde el pie chart directamente.
            pass  # Por ahora, no lo vinculamos a un slice de pie chart.
        else:
            return jsonify(
                {"message": "Tipo de filtro no válido.", "category": "danger"}
            ), 400

        full_query = base_query
        if where_clauses:
            full_query += " WHERE " + " AND ".join(where_clauses)
        full_query += " ORDER BY titulo_espanol"

        # print(f"DEBUG API BOOKS_BY_FILTER: Query: {full_query}")
        # print(f"DEBUG API BOOKS_BY_FILTER: Params: {query_params}")

        cursor.execute(full_query, query_params)
        books = cursor.fetchall()

        # Asegurar que id_obra sea int y filtrar None (similar a la ruta index)
        processed_books = []
        for book_dict in books:
            current_id_obra = None
            if (
                isinstance(book_dict, dict)
                and "id_obra" in book_dict
                and book_dict["id_obra"] is not None
            ):
                try:
                    current_id_obra = int(book_dict["id_obra"])
                except (ValueError, TypeError):
                    current_id_obra = None
            else:
                current_id_obra = None

            book_dict["id_obra"] = current_id_obra

            if book_dict["id_obra"] is not None:
                processed_books.append(book_dict)
            else:
                print(
                    f"DEBUG API BOOKS_BY_FILTER: Saltando libro con id_obra faltante/inválido: {book_dict}"
                )

        return jsonify(processed_books)
    except Exception as e:
        print(f"Error en get_books_by_filter: {e}")
        return jsonify(
            {
                "message": f"Error interno del servidor al filtrar libros: {str(e)}",
                "category": "danger",
            }
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# --- NUEVA RUTA: Visualización del Ranking de Libros ---
@app.route("/ranking")
def ranking():
    conn = get_db_connection()
    if conn is None:
        flash("Error al conectar con la base de datos.", "danger")
        return render_template(
            "ranking.html",
            ranked_books=[],
            series_list=[],
            authors_list=[],
            current_series_id="",
            current_author_id="",
        )

    cursor = conn.cursor(dictionary=True)
    try:
        # Obtener parámetros de filtro de la URL
        filter_series_id = request.args.get("series_id", "").strip()
        filter_author_id = request.args.get("author_id", "").strip()

        # Consulta base para obtener libros valorados
        base_query = """
            SELECT
                o.id_obra,
                o.titulo_espanol,
                o.titulo_original,
                rp.puntuacion,
                rp.comentarios,
                rp.fecha_ranking,
                GROUP_CONCAT(DISTINCT CONCAT(a.nombre_autor, ' ', a.apellido_autor) SEPARATOR '; ') AS autores,
                GROUP_CONCAT(DISTINCT CONCAT(io.url_imagen, ' [', io.descripcion, ']') SEPARATOR '; ') AS imagenes_con_descripcion
            FROM
                obras o
            JOIN
                ranking_personal rp ON o.id_obra = rp.id_obra
            LEFT JOIN
                obra_autor oa ON o.id_obra = oa.id_obra
            LEFT JOIN
                autores a ON oa.id_autor = a.id_autor
            LEFT JOIN
                imagenes_obra io ON o.id_obra = io.id_obra
        """
        where_clauses = [
            "rp.puntuacion IS NOT NULL"
        ]  # Solo libros que tienen puntuación
        query_params = []

        # Añadir JOINs adicionales si hay filtros
        join_clauses = []
        group_by_clauses = [
            "o.id_obra",
            "o.titulo_espanol",
            "o.titulo_original",
            "rp.puntuacion",
            "rp.comentarios",
            "rp.fecha_ranking",
        ]

        if filter_series_id:
            join_clauses.append("JOIN obra_serie os ON o.id_obra = os.id_obra")
            where_clauses.append("os.id_serie = %s")
            query_params.append(filter_series_id)
            group_by_clauses.append(
                "os.id_serie"
            )  # Incluir en GROUP BY si se une por serie

        if filter_author_id:
            # Aquí ya tenemos JOIN obra_autor oa y autores a
            where_clauses.append("a.id_autor = %s")
            query_params.append(filter_author_id)
            group_by_clauses.append(
                "a.id_autor"
            )  # Incluir en GROUP BY si se une por autor

        full_query = base_query
        if join_clauses:
            full_query += " " + " ".join(join_clauses)  # Añadir los JOINs condicionales

        full_query += " WHERE " + " AND ".join(where_clauses)
        full_query += " GROUP BY " + ", ".join(group_by_clauses)
        full_query += (
            " ORDER BY rp.puntuacion DESC, o.titulo_espanol"  # Ordenación por defecto
        )

        # print(f"DEBUG RANKING: Query: {full_query}")
        # print(f"DEBUG RANKING: Params: {query_params}")

        cursor.execute(full_query, query_params)
        ranked_books = cursor.fetchall()

        # Asegurar que id_obra sea int y filtrar None (similar a la ruta index)
        processed_ranked_books = []
        for book_dict in ranked_books:
            current_id_obra = None
            if (
                isinstance(book_dict, dict)
                and "id_obra" in book_dict
                and book_dict["id_obra"] is not None
            ):
                try:
                    current_id_obra = int(book_dict["id_obra"])
                except (ValueError, TypeError):
                    current_id_obra = None
            else:
                current_id_obra = None

            book_dict["id_obra"] = current_id_obra

            if book_dict["id_obra"] is not None:
                processed_ranked_books.append(book_dict)
            else:
                print(
                    f"DEBUG RANKING: Saltando libro con id_obra faltante/inválido: {book_dict}"
                )

        # Obtener listas de series y autores para los dropdowns de filtro
        cursor.execute(
            "SELECT id_serie, nombre_serie FROM series ORDER BY nombre_serie"
        )
        series_list_for_filter = cursor.fetchall()

        cursor.execute(
            "SELECT id_autor, nombre_autor, apellido_autor FROM autores ORDER BY apellido_autor, nombre_autor"
        )
        authors_list_for_filter = cursor.fetchall()

        return render_template(
            "ranking.html",
            ranked_books=processed_ranked_books,
            series_list=series_list_for_filter,
            authors_list=authors_list_for_filter,
            current_series_id=filter_series_id,
            current_author_id=filter_author_id,
        )
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
