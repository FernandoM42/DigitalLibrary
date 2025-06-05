// static/js/dashboard_charts_and_details.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DEBUG CHART: Script dashboard_charts_and_details.js cargado e inicializado.");

    // Recupera las estadísticas pasadas desde Jinja (definida en el script inline en dashboard.html)
    const stats = typeof globalStats !== 'undefined' ? globalStats : {};
    console.log("DEBUG CHART: Stats received:", stats);

    // --- Referencias a elementos del DOM del Modal de Lista de Libros ---
    const chartBookListModal = document.getElementById('chart-book-list-modal');
    const chartBookListModalTitle = document.getElementById('chart-book-list-modal-title');
    const chartBookListFilterValueSpan = document.getElementById('chart-book-list-filter-value');
    const chartBookListModalBody = document.getElementById('chart-book-list-modal-body');
    const chartBookListCloseBtn = document.getElementById('chart-book-list-close-btn');
    const chartBookListCloseX = document.getElementById('chart-book-list-modal-close-x');

    // Depuración de referencias DOM
    console.log("DEBUG CHART: chartBookListModal element:", chartBookListModal);
    console.log("DEBUG CHART: chartBookListFilterValueSpan element:", chartBookListFilterValueSpan);
    console.log("DEBUG CHART: chartBookListModalBody element:", chartBookListModalBody);
    console.log("DEBUG CHART: chartBookListCloseBtn element:", chartBookListCloseBtn);
    console.log("DEBUG CHART: chartBookListCloseX element:", chartBookListCloseX);

    // --- Funciones de Control del Modal de Lista de Libros ---

    function openChartBookListModal(filterLabel, books) {
        console.log("DEBUG CHART: openChartBookListModal llamada para:", filterLabel);
        chartBookListFilterValueSpan.textContent = filterLabel;
        chartBookListModalBody.innerHTML = ''; // Limpiar contenido previo

        if (books && books.length > 0) {
            books.forEach(book => {
                const bookCard = document.createElement('div');
                bookCard.className = 'bg-white shadow-md rounded-lg p-3 text-sm border border-gray-200';

                let imageUrl = '';
                // Intenta obtener la primera URL de imagen del string 'imagenes_con_descripcion'
                if (book.imagenes_con_descripcion) {
                    const imagesList = book.imagenes_con_descripcion.split('; ');
                    if (imagesList.length > 0) {
                        const imageData = imagesList[0].split(' ['); // Divide "URL [Descripción]"
                        imageUrl = imageData[0]; // La URL es el primer elemento
                    }
                }

                bookCard.innerHTML = `
                    <div class="flex items-start space-x-3 mb-2">
                        <div class="flex-shrink-0 w-16 h-20 overflow-hidden rounded border border-gray-200">
                            ${imageUrl ? `<img src="${imageUrl}" alt="Portada" class="w-full h-full object-cover">` : `<div class="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100 text-xs text-center">No Image</div>`}
                        </div>
                        <div class="flex-grow">
                            <h3 class="font-semibold text-gray-900">${book.titulo_espanol} <span class="text-gray-500">(${book.anio_publicacion})</span></h3>
                            <p class="text-gray-700">Autor(es): ${book.autores || 'N/A'}</p>
                            <p class="text-gray-700">Editorial: ${book.editorial_nombre || 'N/A'}</p> 
                        </div>
                    </div>
                    <div class="flex justify-end space-x-2 mt-2">
                        <a href="/libro/form/${book.id_obra}" class="bg-yellow-500 text-white px-2 py-1 rounded-md text-xs hover:bg-yellow-600">Editar</a>
                        <button type="button" class="open-rating-modal-btn bg-purple-600 text-white px-2 py-1 rounded-md text-xs hover:bg-purple-700"
                                data-book-id="${book.id_obra}" 
                                data-book-title="${book.titulo_espanol}"
                                data-puntuacion="${book.ranking_personal_puntuacion || ''}"
                                data-comentarios="${book.ranking_personal_comentarios || ''}"
                                data-fecha-ranking="${book.ranking_personal_fecha || ''}">
                            Valorar
                        </button>
                    </div>
                `;
                chartBookListModalBody.appendChild(bookCard);
            });
        } else {
            chartBookListModalBody.innerHTML = `<p class="text-gray-500 text-center col-span-full">No se encontraron libros para este filtro.</p>`;
        }

        chartBookListModal.classList.remove('hidden');
        console.log("DEBUG CHART: Modal de lista de libros mostrado.");
    }

    function closeChartBookListModal() {
        console.log("DEBUG CHART: closeChartBookListModal llamada.");
        chartBookListModal.classList.add('hidden');
        // Limpiar el contenido del modal al cerrarlo
        chartBookListFilterValueSpan.textContent = '';
        chartBookListModalBody.innerHTML = ''; 

        // Intento de reiniciar la posición del scroll (persiste aquí aunque no siempre sea efectivo)
        // Se mantiene para el caso de que el scroll se aplique directamente a chartBookListModalBody
        if (chartBookListModalBody) {
            chartBookListModalBody.scrollTop = 0;
            console.log("DEBUG CHART: Scroll reset attempt for chartBookListModalBody.");
        }
    }

    // --- Manejadores de Eventos del Modal ---
    if (chartBookListCloseBtn) {
        chartBookListCloseBtn.addEventListener('click', closeChartBookListModal);
    }
    if (chartBookListCloseX) {
        chartBookListCloseX.addEventListener('click', closeChartBookListModal);
    }
    // Cierra el modal si se hace clic fuera del contenido principal
    if (chartBookListModal) {
        chartBookListModal.addEventListener('click', (event) => {
            if (event.target === chartBookListModal) {
                closeChartBookListModal();
            }
        });
    }

    // --- Configuración y Lógica de Creación de Gráficos ---

    const backgroundColors = [
        '#4299E1', '#F6AD55', '#48BB78', '#ED8936', '#ECC94B', '#9F7AEA', '#ED64A6', '#667EEA', '#F56565', '#38B2AC'
    ];
    const borderColors = [
        '#2B6CB0', '#DD6B20', '#2F855A', '#C05621', '#D69E2E', '#805AD5', '#D53F8C', '#4C51BF', '#C53030', '#2C7A7B'
    ];

    // Función genérica para crear gráficos de torta con interactividad de clic
    function createPieChart(ctxId, labels, data, chartTypeIdentifier) {
        const ctx = document.getElementById(ctxId);
        if (!ctx) {
            console.error(`DEBUG CHART: Canvas con ID '${ctxId}' no encontrado. No se pudo crear el gráfico.`);
            return;
        }
        new Chart(ctx.getContext('2d'), {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    borderColor: borderColors.slice(0, labels.length),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 20,
                            fontSize: 12,
                            padding: 15,
                            textAlign: 'start',
                            usePointStyle: true
                        },
                        onClick: (e, legendItem) => {
                            const index = legendItem.index;
                            const chart = this;
                            const ci = chart.chart;
                            const alreadyHidden = (ci.getDatasetMeta(0).data[index].hidden === null) ? false : ci.getDatasetMeta(0).data[index].hidden;

                            ci.data.datasets.forEach(function(e, i) {
                                const meta = ci.getDatasetMeta(i);

                                if (i === 0) {
                                    meta.data[index].hidden = !alreadyHidden;
                                }
                            });

                            ci.update();
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed !== null) {
                                    label += context.parsed + ' libros';
                                }
                                return label;
                            }
                        }
                    }
                },
                // Manejador de clic para los segmentos del gráfico
                onClick: async function(event, elements) {
                    console.log("DEBUG CHART: onClick handler disparado.", {event, elements});
                    if (elements.length > 0) {
                        const clickedElementIndex = elements[0].index;
                        const label = labels[clickedElementIndex]; // El texto del segmento clickeado (ej. "Terror", "Adquiridos")

                        let filterType = '';
                        let filterValue = '';

                        // Determinar el tipo de filtro y el valor basándose en el identificador del gráfico
                        if (chartTypeIdentifier === 'acquiredChart') {
                            filterType = 'acquired';
                            filterValue = label === 'Adquiridos' ? '1' : '0';
                        } else if (chartTypeIdentifier === 'readStatusChart') {
                            filterType = 'read_status';
                            filterValue = label === 'Leídos' ? 'leidos' : 'no_leidos';
                        } else if (chartTypeIdentifier === 'genreChart') {
                            filterType = 'genre';
                            filterValue = label; // El valor es el nombre del género (ej. "Terror")
                        } else if (chartTypeIdentifier === 'workTypeChart') {
                            filterType = 'work_type';
                            filterValue = label; // El valor es el nombre del tipo de obra (ej. "Novela")
                        } else if (chartTypeIdentifier === 'bindingTypeChart') {
                            filterType = 'binding_type';
                            filterValue = label; // El valor es el nombre del tipo de encuadernación (ej. "Tapa blanda")
                        } else {
                            console.warn(`DEBUG CHART CLICK: Tipo de gráfico desconocido o no manejado para filtrar: ${chartTypeIdentifier}`);
                            return; // Salir si el tipo de gráfico no es reconocido
                        }

                        console.log(`DEBUG CHART CLICK: Clic en segmento: "${label}". Tipo de filtro: ${filterType}, Valor de filtro: ${filterValue}`);

                        // Construir la URL para la API de filtrado de libros
                        const url = `/api/books_by_filter?filter_type=${encodeURIComponent(filterType)}&filter_value=${encodeURIComponent(filterValue)}`;
                        
                        try {
                            // Realizar la solicitud a la API
                            const response = await fetch(url);
                            if (!response.ok) {
                                const errorData = await response.text();
                                throw new Error(`Error al cargar libros filtrados: ${response.status} - ${errorData}`);
                            }
                            const books = await response.json(); // Parsear la respuesta JSON

                            console.log("DEBUG CHART CLICK: Libros recibidos para el filtro:", books);
                            // Abrir el modal y mostrar los libros
                            openChartBookListModal(label, books); 
                        } catch (error) {
                            console.error("DEBUG CHART CLICK: Fallo al obtener libros:", error);
                            alert(`Error al obtener la lista de libros: ${error.message}`); // Mostrar un mensaje de error al usuario
                        }
                    } else {
                        console.log("DEBUG CHART CLICK: Clic detectado, pero no en un sector del gráfico.");
                    }
                }
            }
        });
    }

    // --- Inicialización de Gráficos (se ejecuta cuando el DOM está completamente cargado) ---
    // Solo intenta crear los gráficos si el objeto 'stats' no está vacío
    if (Object.keys(stats).length > 0) { 
        // Gráfico: Libros Adquiridos vs No Adquiridos
        if (stats.libros_adquiridos + stats.libros_no_adquiridos > 0) {
            createPieChart('acquiredChart',
                ['Adquiridos', 'No Adquiridos'],
                [stats.libros_adquiridos, stats.libros_no_adquiridos],
                'acquiredChart' // Identificador único para este tipo de gráfico
            );
        }

        // Gráfico: Libros Leídos vs No Leídos
        if (stats.libros_leidos + stats.libros_no_leidos > 0) {
            createPieChart('readStatusChart',
                ['Leídos', 'No Leídos'],
                [stats.libros_leidos, stats.libros_no_leidos],
                'readStatusChart'
            );
        }

        // Gráfico: Libros por Género
        if (Array.isArray(stats.libros_por_genero) && stats.libros_por_genero.length > 0) {
            const genreLabels = stats.libros_por_genero.map(g => g.nombre_genero);
            const genreData = stats.libros_por_genero.map(g => g.count);
            createPieChart('genreChart', genreLabels, genreData, 'genreChart');
        }

        // Gráfico: Libros por Tipo de Obra
        if (Array.isArray(stats.libros_por_tipo_obra) && stats.libros_por_tipo_obra.length > 0) {
            const workTypeLabels = stats.libros_por_tipo_obra.map(t => t.tipo);
            const workTypeData = stats.libros_por_tipo_obra.map(t => t.count);
            createPieChart('workTypeChart', workTypeLabels, workTypeData, 'workTypeChart');
        }

        // Gráfico: Libros por Tipo de Encuadernación
        if (Array.isArray(stats.libros_por_encuadernacion) && stats.libros_por_encuadernacion.length > 0) {
            const bindingTypeLabels = stats.libros_por_encuadernacion.map(b => b.nombre_encuadernacion);
            const bindingTypeData = stats.libros_por_encuadernacion.map(b => b.count);
            createPieChart('bindingTypeChart', bindingTypeLabels, bindingTypeData, 'bindingTypeChart');
        }
    } else {
        console.warn("DEBUG CHART: No se recibieron estadísticas o el objeto 'stats' está vacío. No se crearán gráficos.");
    }

    // --- NUEVA LÓGICA: Manejadores de Eventos para los "Top" Lists ---

    // Función genérica para manejar el clic en los elementos de las listas Top 5
    async function handleTopListItemClick(event) {
        const button = event.currentTarget; // El botón clicado
        const filterType = button.dataset.filterType;
        const filterValue = button.dataset.filterValue;
        // Obtener solo el nombre del autor/editorial del texto del botón (sin "X libros")
        const filterLabel = button.textContent.split(':')[0].trim(); 

        console.log(`DEBUG TOP LIST CLICK: Clic en ${filterLabel}. Tipo de filtro: ${filterType}, Valor de filtro: ${filterValue}`);

        const url = `/api/books_by_filter?filter_type=${encodeURIComponent(filterType)}&filter_value=${encodeURIComponent(filterValue)}`;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.text();
                throw new Error(`Error al cargar libros filtrados por top list: ${response.status} - ${errorData}`);
            }
            const books = await response.json();
            console.log("DEBUG TOP LIST CLICK: Libros recibidos para el filtro:", books);
            openChartBookListModal(filterLabel, books); // Reutiliza la función existente para abrir el modal
        } catch (error) {
            console.error("DEBUG TOP LIST CLICK: Fallo al obtener libros:", error);
            alert(`Error al obtener la lista de libros: ${error.message}`);
        }
    }

    // Añadir event listeners a los botones de Top 5 Autores
    const authorDetailButtons = document.querySelectorAll('.author-detail-btn');
    authorDetailButtons.forEach(button => {
        button.addEventListener('click', handleTopListItemClick);
    });
    console.log(`DEBUG TOP LIST: ${authorDetailButtons.length} botones de autor encontrados.`);


    // Añadir event listeners a los botones de Top 5 Editoriales
    const editorialDetailButtons = document.querySelectorAll('.editorial-detail-btn');
    editorialDetailButtons.forEach(button => {
        button.addEventListener('click', handleTopListItemClick);
    });
    console.log(`DEBUG TOP LIST: ${editorialDetailButtons.length} botones de editorial encontrados.`);

});