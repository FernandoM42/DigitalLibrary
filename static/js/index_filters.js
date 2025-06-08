// static/js/index_filters.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a elementos del DOM ---
    const filterModal = document.getElementById('filter-modal');
    const openFilterModalBtn = document.getElementById('open-filter-modal-btn');
    const closeFilterModalBtn = document.getElementById('close-filter-modal-btn');
    const advancedFilterForm = document.getElementById('advanced-filter-form');
    const clearFiltersBtn = document.getElementById('clear-filters-btn');

    // Campos de filtro individuales
    const qTitleInput = document.getElementById('q_title');
    const idEditorialFilterSelect = document.getElementById('id_editorial_filter'); // Select para editorial
    const idTipoObraFilterSelect = document.getElementById('id_tipo_obra_filter');
    const idTipoEncuadernacionFilterSelect = document.getElementById('id_tipo_encuadernacion_filter');
    const minAnioPublicacionInput = document.getElementById('min_anio_publicacion');
    const maxAnioPublicacionInput = document.getElementById('max_anio_publicacion');
    const adquiridoFilterSelect = document.getElementById('adquirido_filter');
    const minRankingInput = document.getElementById('min_ranking');
    const maxRankingInput = document.getElementById('max_ranking');

    // Autores (filtros)
    const authorFilterInput = document.getElementById('author-filter-input');
    const authorFilterSuggestionsDiv = document.getElementById('author-filter-suggestions');
    const selectedAuthorsFilterTags = document.getElementById('selected-authors-filter-tags');
    const authorIdsFilterInput = document.getElementById('author-ids-filter');
    let selectedAuthorsFilter = {}; // {id_autor: {id_autor, nombre_autor, apellido_autor}}

    // Géneros (filtros)
    const genreFilterInput = document.getElementById('genre-filter-input');
    const genreFilterSuggestionsDiv = document.getElementById('genre-filter-suggestions');
    const selectedGenresFilterTags = document.getElementById('selected-genres-filter-tags');
    const genreIdsFilterInput = document.getElementById('genre-ids-filter');
    let selectedGenresFilter = {}; // {id_genero: {id_genero, nombre_genero}}

        const sortBySelect = document.getElementById('sort_by');


    // --- Datos iniciales / URLSearchParams (global en este contexto de script) ---
    const currentFilters = new URLSearchParams(window.location.search);


    // --- Funciones de Utilidad ---

    // Función para obtener datos de una API
    async function fetchData(url, query) {
        try {
            const response = await fetch(`${url}?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status} from ${url}`);
                return [];
            }
            return await response.json();
        } catch (error) {
            console.error("Error fetching data:", error);
            return [];
        }
    }

    // Función para añadir un "tag" de elemento seleccionado
    function addSelectedItemToFilter(container, item, displayFn, removeFn, itemIdAttr) {
        const tag = document.createElement('span');
        tag.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-200 text-gray-800';
        tag.innerHTML = `
            ${displayFn(item)}
            <button type="button" class="ml-2 -mr-0.5 h-4 w-4 inline-flex items-center justify-center rounded-full bg-gray-300 text-gray-800 hover:bg-gray-400" aria-label="Remove" data-item-id="${itemIdAttr}">
                <svg class="h-2 w-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        `;
        container.appendChild(tag);

        const removeButton = tag.querySelector('button');
        removeButton.addEventListener('click', (e) => {
            const itemId = e.target.closest('button').dataset.itemId;
            removeFn(itemId);
            tag.remove();
        });
    }

    // --- Lógica del Modal ---

    async function openFilterModal() {
        filterModal.classList.remove('hidden');
        await populateEditorialsDropdown(); // Cargar editoriales al abrir el modal
        prefillFilterForm(); // Pre-llenar con filtros actuales de la URL
    }

    function closeFilterModal() {
        filterModal.classList.add('hidden');
    }

    // Función para poblar el dropdown de editoriales
    async function populateEditorialsDropdown() {
        const editoriales = await fetchData('/api/editoriales', ''); // Obtener todas las editoriales
        idEditorialFilterSelect.innerHTML = '<option value="">Todas</option>'; // Limpiar y añadir opción por defecto
        editoriales.forEach(editorial => {
            const option = document.createElement('option');
            option.value = editorial.id_editorial;
            option.textContent = editorial.nombre_editorial;
            idEditorialFilterSelect.appendChild(option);
        });
    }

    function prefillFilterForm() {
        // Campos de texto y número simples
        qTitleInput.value = currentFilters.get('q_title') || '';
        minAnioPublicacionInput.value = currentFilters.get('min_anio_publicacion') || '';
        maxAnioPublicacionInput.value = currentFilters.get('max_anio_publicacion') || '';
        minRankingInput.value = currentFilters.get('min_ranking') || '';
        maxRankingInput.value = currentFilters.get('max_ranking') || '';

        // Selects
        idTipoObraFilterSelect.value = currentFilters.get('id_tipo_obra_filter') || '';
        idTipoEncuadernacionFilterSelect.value = currentFilters.get('id_tipo_encuadernacion_filter') || '';
        adquiridoFilterSelect.value = currentFilters.get('adquirido_filter') || '';

        // Pre-seleccionar la editorial en el dropdown (usando el nombre del parámetro correcto)
        idEditorialFilterSelect.value = currentFilters.get('id_editorial_filter') || ''; // Corrected parameter name

        // Autores y Géneros (requieren lógica de carga y renderizado de tags)
        prefillDynamicFilter(
            currentFilters.get('author_ids_filter'),
            selectedAuthorsFilter,
            selectedAuthorsFilterTags,
            removeAuthorFilter,
            (item) => `${item.nombre_autor} ${item.apellido_autor}`,
            '/api/autores'
        );

        prefillDynamicFilter(
            currentFilters.get('genre_ids_filter'),
            selectedGenresFilter,
            selectedGenresFilterTags,
            removeGenreFilter,
            (item) => item.nombre_genero,
            '/api/generos'
        );
    }

    async function prefillDynamicFilter(idsParam, selectedFilterMap, tagsContainer, removeFn, displayFn, apiUrl) {
        if (!idsParam) {
            tagsContainer.innerHTML = '';
            return;
        }

        const ids = idsParam.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
        if (ids.length === 0) {
            tagsContainer.innerHTML = '';
            return;
        }

        // Limpiar mapa antes de prellenar con nuevos datos de la URL
        for (const key in selectedFilterMap) {
            if (selectedFilterMap.hasOwnProperty(key)) {
                delete selectedFilterMap[key];
            }
        }
        tagsContainer.innerHTML = ''; // Limpiar tags existentes en el DOM

        for (const id of ids) {
            // Se asume que fetchData(apiUrl, id) puede devolver el objeto completo por ID
            const items = await fetchData(apiUrl, id);
            if (items && items.length > 0) {
                const item = items[0];
                // Determinar la clave ID correcta ('id_autor' o 'id_genero')
                const itemIdKey = item.id_autor ? 'id_autor' : 'id_genero';
                selectedFilterMap[item[itemIdKey]] = item;
            }
        }
        renderDynamicFilterTags(selectedFilterMap, tagsContainer, removeFn, displayFn);
    }

    function renderDynamicFilterTags(selectedFilterMap, tagsContainer, removeFn, displayFn) {
        tagsContainer.innerHTML = '';
        Object.values(selectedFilterMap).forEach(item => {
            const itemIdAttr = item.id_autor ? String(item.id_autor) : String(item.id_genero); // Usar el ID numérico
            addSelectedItemToFilter(tagsContainer, item, displayFn, removeFn, itemIdAttr);
        });
    }


    // --- Lógica de Autocompletado (para el Modal) ---

    // Autores (filtros) - Autocompletado y selección
    let authorFilterTimeout;
    authorFilterInput.addEventListener('input', () => {
        clearTimeout(authorFilterTimeout);
        const query = authorFilterInput.value.trim();

        if (query.length < 2) { // Empieza a buscar después de 2 caracteres
            authorFilterSuggestionsDiv.innerHTML = '';
            authorFilterSuggestionsDiv.classList.add('hidden');
            return;
        }

        authorFilterTimeout = setTimeout(async () => {
            const authors = await fetchData('/api/autores', query);
            authorFilterSuggestionsDiv.innerHTML = '';

            if (authors.length > 0) {
                authors.forEach(author => {
                    // Evitar añadir autores ya seleccionados
                    if (!selectedAuthorsFilter[author.id_autor]) {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.className = 'p-2 cursor-pointer hover:bg-blue-100 border-b border-gray-100 last:border-b-0';
                        suggestionItem.textContent = `${author.nombre_autor} ${author.apellido_autor}`;
                        suggestionItem.addEventListener('click', () => {
                            selectedAuthorsFilter[author.id_autor] = author;
                            renderDynamicFilterTags(selectedAuthorsFilter, selectedAuthorsFilterTags, removeAuthorFilter, (item) => `${item.nombre_autor} ${item.apellido_autor}`);
                            authorFilterInput.value = ''; // Limpiar input después de seleccionar
                            authorFilterSuggestionsDiv.classList.add('hidden');
                            // Actualizar el input oculto al seleccionar un autor
                            authorIdsFilterInput.value = Object.keys(selectedAuthorsFilter).join(',');
                        });
                        authorFilterSuggestionsDiv.appendChild(suggestionItem);
                    }
                });
                authorFilterSuggestionsDiv.classList.remove('hidden');
            } else {
                authorFilterSuggestionsDiv.classList.add('hidden');
            }
        }, 300); // Pequeño retardo para evitar demasiadas peticiones
    });

    function removeAuthorFilter(authorId) {
        delete selectedAuthorsFilter[authorId];
        renderDynamicFilterTags(selectedAuthorsFilter, selectedAuthorsFilterTags, removeAuthorFilter, (item) => `${item.nombre_autor} ${item.apellido_autor}`);
        // ¡CRÍTICO! Actualizar el hidden input cuando se elimina un tag
        authorIdsFilterInput.value = Object.keys(selectedAuthorsFilter).join(',');
    }


    // Géneros (filtros) - Autocompletado y selección
    let genreFilterTimeout;
    genreFilterInput.addEventListener('input', () => {
        clearTimeout(genreFilterTimeout);
        const query = genreFilterInput.value.trim();

        if (query.length < 2) {
            genreFilterSuggestionsDiv.innerHTML = '';
            genreFilterSuggestionsDiv.classList.add('hidden');
            return;
        }

        genreFilterTimeout = setTimeout(async () => {
            const genres = await fetchData('/api/generos', query);
            genreFilterSuggestionsDiv.innerHTML = '';

            if (genres.length > 0) {
                genres.forEach(genre => {
                    if (!selectedGenresFilter[genre.id_genero]) {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.className = 'p-2 cursor-pointer hover:bg-blue-100 border-b border-gray-100 last:border-b-0';
                        suggestionItem.textContent = genre.nombre_genero;
                        suggestionItem.addEventListener('click', () => {
                            selectedGenresFilter[genre.id_genero] = genre;
                            renderDynamicFilterTags(selectedGenresFilter, selectedGenresFilterTags, removeGenreFilter, (item) => item.nombre_genero);
                            genreFilterInput.value = '';
                            genreFilterSuggestionsDiv.classList.add('hidden');
                            // Actualizar el input oculto al seleccionar un género
                            genreIdsFilterInput.value = Object.keys(selectedGenresFilter).join(',');
                        });
                        genreFilterSuggestionsDiv.appendChild(suggestionItem);
                    }
                });
                genreFilterSuggestionsDiv.classList.remove('hidden');
            } else {
                genreFilterSuggestionsDiv.classList.add('hidden');
            }
        }, 300);
    });

    function removeGenreFilter(genreId) {
        delete selectedGenresFilter[genreId];
        renderDynamicFilterTags(selectedGenresFilter, selectedGenresFilterTags, removeGenreFilter, (item) => item.nombre_genero);
        // ¡CRÍTICO! Actualizar el hidden input cuando se elimina un tag
        genreIdsFilterInput.value = Object.keys(selectedGenresFilter).join(',');
    }


    // Ocultar sugerencias al hacer clic fuera
    document.addEventListener('click', (event) => {
        if (!authorFilterInput.contains(event.target) && !authorFilterSuggestionsDiv.contains(event.target)) {
            authorFilterSuggestionsDiv.classList.add('hidden');
        }
        if (!genreFilterInput.contains(event.target) && !genreFilterSuggestionsDiv.contains(event.target)) {
            genreFilterSuggestionsDiv.classList.add('hidden');
        }
    });


    // --- Manejadores de Eventos del Modal ---

    openFilterModalBtn.addEventListener('click', openFilterModal);
    closeFilterModalBtn.addEventListener('click', closeFilterModal);

    clearFiltersBtn.addEventListener('click', () => {
        // Resetear campos simples
        qTitleInput.value = '';
        idEditorialFilterSelect.value = ''; // Resetear el select
        minAnioPublicacionInput.value = '';
        maxAnioPublicacionInput.value = '';
        idTipoObraFilterSelect.value = '';
        idTipoEncuadernacionFilterSelect.value = '';
        adquiridoFilterSelect.value = '';
        minRankingInput.value = '';
        maxRankingInput.value = '';

        // Resetear campos dinámicos
        authorFilterInput.value = '';
        genreFilterInput.value = '';
        selectedAuthorsFilter = {}; // Resetear el mapa de autores seleccionados
        selectedGenresFilter = {}; // Resetear el mapa de géneros seleccionados
        // Limpiar los tags visuales
        renderDynamicFilterTags(selectedAuthorsFilter, selectedAuthorsFilterTags, removeAuthorFilter, (item) => `${item.nombre_autor} ${item.apellido_autor}`);
        renderDynamicFilterTags(selectedGenresFilter, selectedGenresFilterTags, removeGenreFilter, (item) => item.nombre_genero);
        // Limpiar los inputs ocultos
        authorIdsFilterInput.value = '';
        genreIdsFilterInput.value = '';
    });

    // Antes de enviar el formulario del modal, actualizar los inputs hidden
    advancedFilterForm.addEventListener('submit', () => {
        authorIdsFilterInput.value = Object.keys(selectedAuthorsFilter).join(',');
        genreIdsFilterInput.value = Object.keys(selectedGenresFilter).join(',');
        // El resto de los campos de texto y select se envían automáticamente
    });

    // *** NUEVA LÓGICA: Manejar el cambio en el selector de ordenar ***
    sortBySelect.addEventListener('change', () => {
        // Obtener todos los parámetros actuales de la URL
        const params = new URLSearchParams(window.location.search);
        
        // Eliminar cualquier parámetro 'sort_by' existente
        params.delete('sort_by');

        // Añadir el nuevo parámetro 'sort_by' si se seleccionó una opción
        if (sortBySelect.value) {
            params.append('sort_by', sortBySelect.value);
        }
        
        // Redirigir a la página con los nuevos filtros y ordenación
        window.location.href = `/index?${params.toString()}`;
    });
    // ***************************************************************

    // --- Inicialización ---
    // Pre-llenar el formulario de filtros con los parámetros de la URL al cargar la página
    prefillFilterForm();

    // *** NUEVA LÓGICA: Pre-seleccionar la opción de ordenar al cargar la página ***
    const currentSortBy = currentFilters.get('sort_by');
     const firstOption = sortBySelect.options[0];
    
    if (currentSortBy) {
        sortBySelect.value = currentSortBy;
    } else {
        sortBySelect.value = firstOption.value; // Asegurarse de que la opción por defecto esté seleccionada
    }
});