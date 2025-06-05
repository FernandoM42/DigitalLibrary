// static/js/series_management.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a elementos del DOM ---
    const seriesManagementForm = document.getElementById('series-management-form');
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');

    const nombreSerieInput = document.getElementById('nombre_serie');
    const descripcionSerieInput = document.getElementById('descripcion_serie');

    const bookSearchInput = document.getElementById('book-search-input');
    const clearBookSearchBtn = document.getElementById('clear-book-search');
    const booksSelectionTableBody = document.getElementById('books-selection-table-body');

    const nextStepBtn = document.getElementById('next-step-btn');
    const prevStepBtn = document.getElementById('prev-step-btn');
    const booksOrderTableBody = document.getElementById('books-order-table-body');

    // --- Variables de Estado ---
    let currentStep = 1; 
    let selectedBooks = {}; // { id_obra: { id_obra: "...", titulo_espanol: "...", orden: N, ...todos los detalles del libro } }
    let allBooks = []; // Almacenará todos los libros cargados de la API (para la búsqueda y selección)

    // Bandera para asegurar que los libros de la serie existente se carguen solo una vez
    let initialSeriesBooksLoaded = false; 

    // --- Funciones de Utilidad ---

    /**
     * Muestra u oculta los pasos del formulario.
     * @param {number} stepNumber El número del paso a mostrar (1 o 2).
     */
    function showStep(stepNumber) {
        currentStep = stepNumber;
        if (stepNumber === 1) {
            step1.classList.remove('hidden');
            step2.classList.add('hidden');
            fetchAndRenderBookSelectionTable(); // Re-renderiza al volver al Paso 1
        } else if (stepNumber === 2) {
            step1.classList.add('hidden');
            step2.classList.remove('hidden');
            renderOrderAdjustmentTable(); // Renderiza la tabla de ajuste de orden para el Paso 2
        }
    }

    /**
     * Carga libros de la API `/api/books_for_series_selection` y renderiza la tabla de selección (Paso 1).
     * También se encarga de inicializar `selectedBooks` en modo edición.
     */
    async function fetchAndRenderBookSelectionTable() {
        console.log("DEBUG JS: fetchAndRenderBookSelectionTable llamada."); 
        const searchTerm = bookSearchInput.value.trim();
        const url = `/api/books_for_series_selection?q=${encodeURIComponent(searchTerm)}`;
        console.log("DEBUG JS: Fetching books from URL:", url); 
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.text(); 
                throw new Error(`HTTP error! status: ${response.status} - ${errorData}`);
            }
            allBooks = await response.json(); 
            console.log("DEBUG JS: Libros cargados de la API (allBooks):", allBooks); 
            
            // --- INICIALIZACIÓN CRÍTICA PARA EL MODO EDICIÓN ---
            // Solo procesa `initialBooksForSeries` si estamos en modo edición Y no se ha cargado antes.
            if (typeof initialSeries !== 'undefined' && typeof initialBooksForSeries !== 'undefined' && !initialSeriesBooksLoaded) {
                console.log("DEBUG JS INIT: Procesando initialBooksForSeries."); // DEBUG
                Object.keys(initialBooksForSeries).forEach(bookIdStr => {
                    const bookId = parseInt(bookIdStr);
                    const order = initialBooksForSeries[bookIdStr];
                    const bookDataFromAllBooks = allBooks.find(b => b.id_obra === bookId); 

                    if (bookDataFromAllBooks) {
                        // Popula `selectedBooks` con los detalles completos del libro y su orden.
                        selectedBooks[bookId] = {
                            id_obra: bookId,
                            orden: order, 
                            titulo_espanol: bookDataFromAllBooks.titulo_espanol,
                            titulo_original: bookDataFromAllBooks.titulo_original,
                            autores: bookDataFromAllBooks.autores,
                            anio_publicacion: bookDataFromAllBooks.anio_publicacion 
                        };
                    } else {
                        // Fallback: Si un libro de la serie existente no se encuentra en la lista general.
                        console.warn(`Libro con ID ${bookId} de la serie existente no encontrado en la lista general de libros.`);
                        selectedBooks[bookId] = {
                            id_obra: bookId,
                            orden: order,
                            titulo_espanol: `Libro ID ${bookId} (Desconocido)`,
                            titulo_original: '',
                            autores: 'N/A',
                            anio_publicacion: ''
                        };
                    }
                });
                initialSeriesBooksLoaded = true; 
                console.log("DEBUG JS INIT: initialSeriesBooksLoaded establecido a true."); // DEBUG
                console.log("DEBUG JS INIT: selectedBooks después de inicialización inicial:", selectedBooks); // DEBUG
            }
            // --- FIN INICIALIZACIÓN CRÍTICA ---

            // Renderizado de la tabla de selección de libros (Paso 1)
            booksSelectionTableBody.innerHTML = ''; 
            if (allBooks.length === 0) {
                booksSelectionTableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">No se encontraron libros.</td></tr>`;
            } else {
                allBooks.forEach(book => {
                    const isChecked = selectedBooks.hasOwnProperty(book.id_obra);
                    const row = document.createElement('tr');
                    row.className = 'hover:bg-gray-50';
                    row.dataset.bookId = book.id_obra;
                    row.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap"><input type="checkbox" class="book-selection-checkbox w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500" ${isChecked ? 'checked' : ''}></td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${book.titulo_espanol} <br> <span class="text-gray-500 text-xs">(${book.titulo_original || ''})</span></td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${book.autores || 'N/A'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${book.anio_publicacion || ''}</td>
                    `;
                    const checkbox = row.querySelector('.book-selection-checkbox');
                    checkbox.addEventListener('change', (e) => {
                        if (e.target.checked) {
                            selectedBooks[book.id_obra] = {
                                id_obra: book.id_obra,
                                titulo_espanol: book.titulo_espanol,
                                titulo_original: book.titulo_original,
                                autores: book.autores,
                                anio_publicacion: book.anio_publicacion,
                                orden: selectedBooks[book.id_obra] ? selectedBooks[book.id_obra].orden : 1 
                            };
                        } else {
                            delete selectedBooks[book.id_obra];
                        }
                        console.log("DEBUG JS: selectedBooks después del cambio de checkbox:", selectedBooks);
                    });
                    booksSelectionTableBody.appendChild(row);
                });
            }
        } catch (error) {
            console.error("DEBUG JS: Error al cargar y renderizar libros:", error); 
            booksSelectionTableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-4 text-center text-red-500">Error al cargar libros: ${error.message}</td></tr>`;
        }
    }

    /**
     * Renderiza la tabla de ajuste de orden (Paso 2) con Drag-and-Drop y la columna de orden visible.
     */
    function renderOrderAdjustmentTable() {
        booksOrderTableBody.innerHTML = '';
        
        // Convertir `selectedBooks` a un array y ordenar para la visualización inicial en el Paso 2
        // Se espera que `selectedBooks` ya tenga órdenes secuenciales y únicos después de `nextStepBtn` o `updateSelectedBooksOrderFromDOM`.
        const sortedSelectedBooks = Object.values(selectedBooks).sort((a, b) => {
            const orderA = a.orden || Infinity; 
            const orderB = b.orden || Infinity;

            if (orderA === orderB) {
                return a.titulo_espanol.localeCompare(b.titulo_espanol); 
            }
            return orderA - orderB;
        });

        if (sortedSelectedBooks.length === 0) {
            // Ajustado el colspan a 3, ya que ahora hay 3 columnas visibles (handle, orden, título)
            booksOrderTableBody.innerHTML = `<tr><td colspan="3" class="px-6 py-4 text-center text-gray-500">No hay libros seleccionados para ordenar.</td></tr>`; 
            return;
        }

        sortedSelectedBooks.forEach(book => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50';
            row.dataset.bookId = book.id_obra; // Es crucial para identificar el libro al reordenar
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 w-16">
                    <span class="drag-handle cursor-grab text-gray-400 hover:text-gray-600 text-lg">&#x2630;</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 w-24">${book.orden || ''}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${book.titulo_espanol} <br> <span class="text-gray-500 text-xs">(${book.titulo_original || ''})</span></td>
            `;
            booksOrderTableBody.appendChild(row);
        });

        // Inicializar SortableJS en el tbody para permitir el arrastre
        if (!Sortable.get(booksOrderTableBody)) {
            new Sortable(booksOrderTableBody, {
                animation: 150, 
                handle: '.drag-handle', 
                ghostClass: 'bg-blue-100', 
                chosenClass: 'bg-blue-200', 
                dragClass: 'bg-blue-300', 
                onEnd: function (evt) {
                    updateSelectedBooksOrderFromDOM(); 
                    console.log("DEBUG JS: Orden de libros actualizado tras Drag-and-Drop.");
                    // Opcional: Para actualizar los números de orden visibles inmediatamente después del arrastre,
                    // puedes volver a renderizar la tabla o actualizar solo las celdas de orden.
                    // Una re-renderización completa puede causar un "salto" visual.
                    // Si optas por actualizar solo la celda:
                    const rowElement = evt.item; // El elemento <tr> arrastrado
                    const orderCell = rowElement.querySelector('td:nth-child(2)'); // La segunda celda es la del orden
                    if (orderCell) {
                        const newOrder = selectedBooks[parseInt(rowElement.dataset.bookId)].orden;
                        orderCell.textContent = newOrder;
                    }
                    // Sin embargo, si quieres que *todas* las celdas se actualicen (porque el orden de todos los libros cambia),
                    // necesitas iterar y actualizar o re-renderizar. Para mantenerlo simple, la re-renderización es más fácil.
                    // renderOrderAdjustmentTable(); // Descomentar si deseas que los números de orden salten inmediatamente.
                    renderOrderAdjustmentTable(); 
                }
            });
        }
    }

    /**
     * Actualiza la propiedad `orden` en `selectedBooks` basada en la posición actual de las filas en el DOM.
     * Esta función es crucial para la lógica de Drag-and-Drop.
     */
    function updateSelectedBooksOrderFromDOM() {
        const rows = booksOrderTableBody.children;
        for (let i = 0; i < rows.length; i++) {
            const bookId = parseInt(rows[i].dataset.bookId);
            if (selectedBooks[bookId]) {
                selectedBooks[bookId].orden = i + 1; // Orden = índice en el DOM (0-basado) + 1
            }
        }
    }

    // --- Manejadores de Eventos ---

    let searchTimeout;
    bookSearchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            fetchAndRenderBookSelectionTable();
        }, 300);
    });
    clearBookSearchBtn.addEventListener('click', () => {
        bookSearchInput.value = '';
        fetchAndRenderBookSelectionTable();
    });

    /**
     * Maneja el clic en el botón "Siguiente" (Paso 1 a Paso 2).
     * Realiza validaciones y asigna órdenes provisionales a los libros.
     */
    nextStepBtn.addEventListener('click', async () => { 
        const nombreSerie = nombreSerieInput.value.trim();
        const seriesId = seriesManagementForm.dataset.seriesId ? parseInt(seriesManagementForm.dataset.seriesId) : null; 

        console.log(`DEBUG JS NEXT BUTTON: Valor de seriesId del dataset: ${seriesId}, Tipo: ${typeof seriesId}`); // DEBUG

        if (!nombreSerie) { 
            alert('El nombre de la serie es obligatorio.');
            return;
        }

        try {
            let checkUrl = `/api/series/check_name?name=${encodeURIComponent(nombreSerie)}`;
            if (seriesId !== null) { 
                checkUrl += `&exclude_id=${seriesId}`;
            }
            
            console.log("DEBUG JS NEXT BUTTON: Checking series name uniqueness URL:", checkUrl); // DEBUG
            const checkResponse = await fetch(checkUrl);
            const checkData = await checkResponse.json();

            if (checkData.exists) {
                alert(`Ya existe una serie con el nombre "${nombreSerie}". Por favor, elige un nombre diferente.`);
                return; 
            }
        } catch (error) {
            console.error("DEBUG JS NEXT BUTTON: Error al verificar la unicidad del nombre de la serie:", error); // DEBUG
            alert("Ocurrió un error al verificar el nombre de la serie. Inténtalo de nuevo.");
            return;
        }

        if (Object.keys(selectedBooks).length === 0) {
            alert('Por favor, selecciona al menos un libro para esta serie.');
            return;
        }

        const booksInOrder = Object.values(selectedBooks).sort((a,b) => {
            const orderA = a.orden || Infinity;
            const orderB = b.orden || Infinity;
            if (orderA === orderB) {
                return a.titulo_espanol.localeCompare(b.titulo_espanol);
            }
            return orderA - orderB;
        });
        
        booksInOrder.forEach((book, index) => {
            selectedBooks[book.id_obra].orden = index + 1; 
        });

        showStep(2); 
    });
    prevStepBtn.addEventListener('click', () => showStep(1));

    /**
     * Maneja el envío final del formulario (Paso 2).
     * Envía los datos de la serie y los libros asociados a Flask.
     */
    seriesManagementForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const nombreSerie = nombreSerieInput.value.trim();
        const descripcionSerie = descripcionSerieInput.value.trim();

        console.log("DEBUG JS SUBMIT: Valor de nombreSerie:", nombreSerie); // DEBUG
        console.log("DEBUG JS SUBMIT: Tipo de nombreSerie:", typeof nombreSerie); // DEBUG
        console.log("DEBUG JS SUBMIT: Longitud de nombreSerie:", nombreSerie.length); // DEBUG

        if (!nombreSerie) {
            console.error('DEBUG JS SUBMIT: ¡Alerta disparada por nombreSerie vacío/falsy!');
            console.trace('Origen de la alerta: El nombre de la serie es obligatorio.');
            alert('El nombre de la serie es obligatorio.');
            return;
        }
        if (Object.keys(selectedBooks).length === 0) {
            alert('Por favor, selecciona al menos un libro para esta serie.');
            return;
        }

        const seriesId = seriesManagementForm.dataset.seriesId; 
        const parsedSeriesId = seriesId ? parseInt(seriesId) : null; 
        console.log(`DEBUG JS SUBMIT: seriesId del dataset (original): ${seriesId}, Tipo: ${typeof seriesId}`); // DEBUG
        console.log(`DEBUG JS SUBMIT: parsedSeriesId (para payload y URL): ${parsedSeriesId}, Tipo: ${typeof parsedSeriesId}`); // DEBUG

        const selectedBooksWithOrder = Object.values(selectedBooks).map(book => ({
            id_obra: book.id_obra,
            orden: book.orden || 1 
        }));

        const seriesToAddPayload = [{
            id_serie: parsedSeriesId, 
            nombre_serie: nombreSerie,
            descripcion_serie: descripcionSerie,
            libros_a_asignar: selectedBooksWithOrder
        }];

        const payload = {
            selected_book_ids: selectedBooksWithOrder.map(b => b.id_obra), 
            series_to_add: seriesToAddPayload,
            series_to_remove: [] 
        };

        const endpointUrl = parsedSeriesId !== null ? `/series/${parsedSeriesId}/edit` : '/series/new';
        console.log(`DEBUG JS SUBMIT: Endpoint URL: ${endpointUrl}`); // DEBUG

        try {
            const response = await fetch(endpointUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const clonedResponse = response.clone(); 

            if (response.ok) {
                const data = await response.json(); 
                if (data.message) {
                    localStorage.setItem('flashMessage', data.message);
                    localStorage.setItem('flashCategory', data.category || 'info');
                }
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                const errorData = await clonedResponse.json().catch(() => clonedResponse.text()); 
                
                let errorMessage = 'Error desconocido del servidor.';
                if (response.status === 409 && typeof errorData === 'object' && errorData !== null && errorData.message) {
                    errorMessage = errorData.message;
                } else if (typeof errorData === 'object' && errorData !== null && errorData.message) {
                    errorMessage = errorData.message; 
                } else if (typeof errorData === 'string' && errorData.trim() !== '') {
                    errorMessage = errorData; 
                } else if (response.statusText) {
                    errorMessage = response.statusText; 
                }

                throw new Error(errorMessage);
            }
        } catch (error) {
            console.error('Error al guardar la serie:', error);
            alert('Ocurrió un error al guardar la serie: ' + (error.message || 'Error desconocido. Revisa la consola para más detalles.'));
        }
    });

    // --- Inicialización al cargar la página ---
    
    // Al cargar la página, inicializar `selectedBooks` con los ID y órdenes existentes si estamos en modo edición.
    if (typeof initialBooksForSeries !== 'undefined') {
        // Asignar el ID de la serie al dataset del formulario al cargar la página, si estamos en modo edición.
        if (typeof initialSeries !== 'undefined' && initialSeries.id_serie) {
            seriesManagementForm.dataset.seriesId = initialSeries.id_serie;
            console.log("DEBUG JS INIT: seriesManagementForm.dataset.seriesId inicializado con:", initialSeries.id_serie); // DEBUG
        } else {
            console.log("DEBUG JS INIT: No initialSeries o initialSeries.id_serie. Asumiendo modo 'nueva serie'."); // DEBUG
        }

        Object.keys(initialBooksForSeries).forEach(bookIdStr => {
            const bookId = parseInt(bookIdStr);
            const order = initialBooksForSeries[bookIdStr];
            selectedBooks[bookId] = { id_obra: bookId, orden: order };
        });
        console.log("DEBUG JS INIT: selectedBooks poblado con initialBooksForSeries (solo ID y orden)."); // DEBUG
    } else {
        console.log("DEBUG JS INIT: initialBooksForSeries no definido. Asumiendo que es una nueva serie."); // DEBUG
    }

    // Cargar los libros iniciales para la tabla de selección (Paso 1).
    fetchAndRenderBookSelectionTable();

    // Mostrar el primer paso del formulario al cargar la página.
    showStep(1); 
});