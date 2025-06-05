// static/js/form_handling.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Elementos del DOM ---
    const form = document.querySelector('form');

    // Editorial Autocompletado
    const editorialInput = document.getElementById('editorial-input');
    const editorialSuggestionsDiv = document.getElementById('editorial-suggestions');
    const idEditorialSelectedInput = document.getElementById('id-editorial-selected'); // Hidden input for ID
    const nombreEditorialInputHidden = document.getElementById('nombre-editorial-input-hidden'); // Hidden input for name (always send name)

    // Autores
    const authorInput = document.getElementById('author-input');
    const authorSuggestionsDiv = document.getElementById('author-suggestions');
    const selectedAuthorsDiv = document.getElementById('selected-authors');
    const autoresSelectedJsonInput = document.getElementById('autores-selected-json');
    let selectedAuthors = []; 

    // Géneros
    const genreInput = document.getElementById('genre-input');
    const genreSuggestionsDiv = document.getElementById('genre-suggestions');
    const selectedGenresDiv = document.getElementById('selected-genres');
    const generosSelectedJsonInput = document.getElementById('generos-selected-json');
    let selectedGenres = []; 

    // Imágenes
    const externalImageInputsDiv = document.getElementById('external-image-inputs');
    const addExternalImageBtn = externalImageInputsDiv.querySelector('.add-external-image-btn');
    const externalImagePreviews = document.getElementById('external-image-previews');
    const imagenesExternasJsonInput = document.getElementById('imagenes-externas-json');
    
    let externalImages = []; 

    // Variables para la edición de imágenes
    const imageUrlInput = externalImageInputsDiv.querySelector('.external-image-url');
    const imageDescInput = externalImageInputsDiv.querySelector('.external-image-desc');
    let editingImageIndex = -1; 

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
    function addSelectedItem(container, item, displayFn, removeFn, itemIdAttr) {
        const tag = document.createElement('span');
        tag.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800';
        tag.innerHTML = `
            ${displayFn(item)}
            <button type="button" class="ml-2 -mr-0.5 h-4 w-4 inline-flex items-center justify-center rounded-full bg-blue-200 text-blue-800 hover:bg-blue-300" aria-label="Remove" data-item-id="${itemIdAttr}">
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

    // --- Lógica de Autocompletado y Selección Dinámica ---

    // Editorial Autocompletado
    let editorialTimeout;
    editorialInput.addEventListener('input', () => {
        console.log("DEBUG JS EDITORIAL INPUT: Evento 'input' disparado. Valor actual:", editorialInput.value); // <-- ¡Y ESTA OTRA!

        clearTimeout(editorialTimeout);
        const query = editorialInput.value.trim();

        // Limpiar el ID seleccionado si el usuario modifica el texto
        idEditorialSelectedInput.value = ''; 

        if (query.length < 2) { 
            editorialSuggestionsDiv.innerHTML = '';
            editorialSuggestionsDiv.classList.add('hidden');
            return;
        }

        editorialTimeout = setTimeout(async () => {
            const editoriales = await fetchData('/api/editoriales', query);
            editorialSuggestionsDiv.innerHTML = '';

            if (editoriales.length > 0) {
                editorialSuggestionsDiv.classList.remove('hidden');
                editoriales.forEach(editorial => {
                    const suggestionItem = document.createElement('div');
                    suggestionItem.className = 'p-2 cursor-pointer hover:bg-gray-200';
                    suggestionItem.textContent = editorial.nombre_editorial;
                    // Almacenar el ID y el nombre completo en los dataset para fácil acceso
                    suggestionItem.dataset.id = editorial.id_editorial;
                    suggestionItem.dataset.name = editorial.nombre_editorial;
                    
                    suggestionItem.addEventListener('click', () => {
                        editorialInput.value = editorial.nombre_editorial; 
                        idEditorialSelectedInput.value = editorial.id_editorial; 
                        editorialSuggestionsDiv.classList.add('hidden'); 
                    });
                    editorialSuggestionsDiv.appendChild(suggestionItem);
                });
            } else {
                editorialSuggestionsDiv.classList.add('hidden'); 
            }
        }, 300); 
    });

    // Ocultar sugerencias de editorial, autores y géneros al hacer clic fuera
    document.addEventListener('click', (event) => {
        // Editorial
        if (!editorialInput.contains(event.target) && !editorialSuggestionsDiv.contains(event.target)) {
            editorialSuggestionsDiv.classList.add('hidden');
            const currentText = editorialInput.value.trim();
            const selectedId = idEditorialSelectedInput.value;
            
            if (selectedId) {
                const selectedOption = editorialSuggestionsDiv.querySelector(`[data-id="${selectedId}"]`);
                if (!selectedOption || selectedOption.dataset.name !== currentText) {
                    idEditorialSelectedInput.value = '';
                }
            } else if (currentText === '') {
                idEditorialSelectedInput.value = '';
            }
        }

        // Autores
        if (!authorInput.contains(event.target) && !authorSuggestionsDiv.contains(event.target)) {
            authorSuggestionsDiv.classList.add('hidden');
        }
        
        // Géneros
        if (!genreInput.contains(event.target) && !genreSuggestionsDiv.contains(event.target)) {
            genreSuggestionsDiv.classList.add('hidden');
        }
    });

    // Autores
    let authorTimeout;
    authorInput.addEventListener('input', () => {
        clearTimeout(authorTimeout);
        const query = authorInput.value.trim();
        if (query.length > 1) {
            authorTimeout = setTimeout(async () => {
                const autores = await fetchData('/api/autores', query);
                authorSuggestionsDiv.innerHTML = '';
                if (autores.length > 0) {
                    authorSuggestionsDiv.classList.remove('hidden');
                    autores.forEach(author => {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.className = 'p-2 cursor-pointer hover:bg-gray-200';
                        suggestionItem.textContent = `${author.nombre_autor} ${author.apellido_autor}`;
                        suggestionItem.dataset.id = author.id_autor;
                        suggestionItem.dataset.nombre = author.nombre_autor;
                        suggestionItem.dataset.apellido = author.apellido_autor;
                        suggestionItem.addEventListener('click', () => {
                            addAuthor({
                                id_autor: author.id_autor,
                                nombre_autor: author.nombre_autor,
                                apellido_autor: author.apellido_autor
                            });
                            authorInput.value = '';
                            authorSuggestionsDiv.classList.add('hidden');
                        });
                        authorSuggestionsDiv.appendChild(suggestionItem);
                    });
                } else {
                    authorSuggestionsDiv.classList.remove('hidden');
                    authorSuggestionsDiv.innerHTML = '<div class="p-2 text-gray-500">No hay coincidencias. Presiona Enter para añadir.</div>';
                }
            }, 300);
        } else {
            authorSuggestionsDiv.classList.add('hidden');
        }
    });

    authorInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            const fullName = authorInput.value.trim();
            if (fullName) {
                const parts = fullName.split(' ', 2);
                const nombre = parts[0];
                const apellido = parts.length > 1 ? parts[1] : '';
                addAuthor({ nombre_autor: nombre, apellido_autor: '' });
                authorInput.value = '';
                authorSuggestionsDiv.classList.add('hidden');
            }
        }
    });

    function addAuthor(author) {
        const exists = selectedAuthors.some(
            a => (a.id_autor && a.id_autor === author.id_autor) ||
                 (a.nombre_autor === author.nombre_autor && a.apellido_autor === author.apellido_autor)
        );
        if (!exists) {
            selectedAuthors.push(author);
            renderSelectedAuthors();
        }
    }

    function removeAuthor(itemId) {
        selectedAuthors = selectedAuthors.filter(
            a => (a.id_autor ? String(a.id_autor) !== itemId : `${a.nombre_autor} ${a.apellido_autor}` !== itemId)
        );
        renderSelectedAuthors();
    }

    function renderSelectedAuthors() {
        selectedAuthorsDiv.innerHTML = '';
        selectedAuthors.forEach(author => {
            const itemIdAttr = author.id_autor ? String(author.id_autor) : `${author.nombre_autor} ${author.apellido_autor}`;
            addSelectedItem(
                selectedAuthorsDiv,
                author,
                (item) => `${item.nombre_autor} ${item.apellido_autor}`,
                removeAuthor,
                itemIdAttr
            );
        });
        autoresSelectedJsonInput.value = JSON.stringify(selectedAuthors);
    }


    // Géneros
    let genreTimeout;
    genreInput.addEventListener('input', () => {
        clearTimeout(genreTimeout);
        const query = genreInput.value.trim();
        if (query.length > 1) {
            genreTimeout = setTimeout(async () => {
                const generos = await fetchData('/api/generos', query);
                genreSuggestionsDiv.innerHTML = '';
                if (generos.length > 0) {
                    genreSuggestionsDiv.classList.remove('hidden');
                    generos.forEach(genre => {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.className = 'p-2 cursor-pointer hover:bg-gray-200';
                        suggestionItem.textContent = genre.nombre_genero;
                        suggestionItem.dataset.id = genre.id_genero;
                        suggestionItem.dataset.nombre = genre.nombre_genero;
                        suggestionItem.addEventListener('click', () => {
                            addGenre({
                                id_genero: genre.id_genero,
                                nombre_genero: genre.nombre_genero
                            });
                            genreInput.value = '';
                            genreSuggestionsDiv.classList.add('hidden');
                        });
                        genreSuggestionsDiv.appendChild(suggestionItem);
                    });
                } else {
                    genreSuggestionsDiv.classList.remove('hidden');
                    genreSuggestionsDiv.innerHTML = '<div class="p-2 text-gray-500">No hay coincidencias. Presiona Enter para añadir.</div>';
                }
            }, 300);
        } else {
            genreSuggestionsDiv.classList.add('hidden');
        }
    });

    genreInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            const genreName = genreInput.value.trim();
            if (genreName) {
                addGenre({ nombre_genero: genreName });
                genreInput.value = '';
                genreSuggestionsDiv.classList.add('hidden');
            }
        }
    });

    function addGenre(genre) {
        const exists = selectedGenres.some(g => (g.id_genero && g.id_genero === genre.id_genero) || g.nombre_genero === genre.nombre_genero);
        if (!exists) {
            selectedGenres.push(genre);
            renderSelectedGenres();
        }
    }

    function removeGenre(itemId) {
        selectedGenres = selectedGenres.filter(g => (g.id_genero ? String(g.id_genero) !== itemId : g.nombre_genero !== itemId));
        renderSelectedGenres();
    }

    function renderSelectedGenres() {
        selectedGenresDiv.innerHTML = '';
        selectedGenres.forEach(genre => {
            const itemIdAttr = genre.id_genero ? String(genre.id_genero) : genre.nombre_genero;
            addSelectedItem(
                selectedGenresDiv,
                genre,
                (item) => item.nombre_genero,
                removeGenre,
                itemIdAttr
            );
        });
        generosSelectedJsonInput.value = JSON.stringify(selectedGenres);
    }


    // Imágenes (SOLO URLs EXTERNAS)
    addExternalImageBtn.addEventListener('click', () => {
        const url = imageUrlInput.value.trim();
        const description = imageDescInput.value.trim();

        if (!url) {
            alert('La URL de la imagen no puede estar vacía.');
            return;
        }

        if (editingImageIndex !== -1) {
            externalImages[editingImageIndex] = { url: url, description: description || '' };
            editingImageIndex = -1; 
            addExternalImageBtn.textContent = '+'; 
        } else {
            if (!externalImages.some(img => img.url === url)) { 
                externalImages.push({ url: url, description: description || '' });
            } else {
                alert('Esta URL ya ha sido añadida.');
            }
        }
        renderExternalImages();
        imageUrlInput.value = ''; 
        imageDescInput.value = '';
    });

    function removeExternalImage(urlToRemove) {
        if (editingImageIndex !== -1 && externalImages[editingImageIndex] && externalImages[editingImageIndex].url === urlToRemove) {
            editingImageIndex = -1;
            addExternalImageBtn.textContent = '+'; 
            imageUrlInput.value = '';
            imageDescInput.value = '';
        }
        externalImages = externalImages.filter(img => img.url !== urlToRemove);
        renderExternalImages();
    }

    function editExternalImage(urlToEdit) {
        const index = externalImages.findIndex(img => img.url === urlToEdit);
        if (index !== -1) {
            editingImageIndex = index;
            imageUrlInput.value = externalImages[index].url;
            imageDescInput.value = externalImages[index].description;
            addExternalImageBtn.textContent = 'Actualizar'; 
            imageUrlInput.focus();
        }
    }

    function createImagePreview(src, description, type, identifier) { 
        const previewCol = document.createElement('div');
        previewCol.className = 'relative group w-full h-32 overflow-hidden rounded-lg shadow-md';
        previewCol.innerHTML = `
            <img src="${src}" alt="${description}" class="w-full h-full object-cover">
            <div class="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <button type="button" class="edit-image-btn bg-blue-600 text-white p-2 rounded-full hover:bg-blue-700 mr-2" data-identifier="${identifier}" data-type="${type}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.000 2.000 0 113.536 3.536L6 21H3v-3L14.732 5.232z"></path></svg>
                </button>
                <button type="button" class="remove-image-btn bg-red-600 text-white p-2 rounded-full hover:bg-red-700" data-identifier="${identifier}" data-type="${type}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>
            <p class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 text-white text-xs text-center p-1 truncate">${description}</p>
        `;
        previewCol.querySelector('.remove-image-btn').addEventListener('click', (e) => {
            const btn = e.currentTarget;
            const itemId = btn.dataset.identifier;
            removeExternalImage(itemId);
            previewCol.remove();
        });

        previewCol.querySelector('.edit-image-btn').addEventListener('click', (e) => {
            const btn = e.currentTarget;
            const itemId = btn.dataset.identifier;
            editExternalImage(itemId);
        });
        return previewCol;
    }

    function renderExternalImages() {
        externalImagePreviews.innerHTML = '';
        externalImages.forEach(img => {
            const previewItem = createImagePreview(img.url, img.description, 'external', img.url);
            externalImagePreviews.appendChild(previewItem);
        });
        imagenesExternasJsonInput.value = JSON.stringify(externalImages);
    }


    // --- Pre-llenar formulario en modo edición ---
    // Las variables `initialAuthors`, `initialGenres`, `initialImages`, `initialEditorial`
    // ahora se pasan como propiedades de `window.` desde el script in-line en `form_libro.html`.
    if (typeof window.initialAuthors !== 'undefined' && window.initialAuthors !== null) { 
        selectedAuthors = window.initialAuthors;
        renderSelectedAuthors();
    }
    if (typeof window.initialGenres !== 'undefined' && window.initialGenres !== null) { 
        selectedGenres = window.initialGenres;
        renderSelectedGenres();
    }
    if (typeof window.initialImages !== 'undefined' && window.initialImages !== null) { 
        externalImages = window.initialImages.map(img => ({
            url: img.url_imagen,
            description: img.descripcion
        }));
        renderExternalImages();
    }
    // Pre-llenar editorial si estamos en modo edición
    if (typeof window.initialEditorial !== 'undefined' && window.initialEditorial !== null && window.initialEditorial.nombre_editorial) {
        editorialInput.value = window.initialEditorial.nombre_editorial;
        idEditorialSelectedInput.value = window.initialEditorial.id_editorial;
        console.log("DEBUG JS EDITORIAL INIT: Editorial inicializada con:", window.initialEditorial.nombre_editorial, "ID:", window.initialEditorial.id_editorial); // <-- ¡NUEVO DEBUG!
    } else {
        console.log("DEBUG JS EDITORIAL INIT: initialEditorial no definida o nombre_editorial vacío/nulo."); // <-- ¡NUEVO DEBUG!
    }
    
    // --- Antes de enviar el formulario ---
    form.addEventListener('submit', (event) => {
        event.preventDefault(); 

        const formData = new FormData(form);

        // AQUI ES DONDE AJUSTAMOS EL ENVIO DE LA EDITORIAL
        const finalEditorialName = editorialInput.value.trim();
        const finalEditorialId = idEditorialSelectedInput.value.trim(); 

        if (!finalEditorialName) {
            alert('El campo Editorial es obligatorio.');
            return;
        }

        // Eliminar el campo id_editorial (del antiguo select) si aún existiera en FormData
        formData.delete('id_editorial'); 
        
        // El nombre de la editorial siempre se enviará, sea nueva o existente
        formData.set('nombre_editorial_input', finalEditorialName); 
        
        // Si hay un ID de una editorial existente, también se envía.
        // Si el usuario escribió una nueva editorial, este campo estará vacío,
        // y el backend sabrá que debe crearla.
        formData.set('id_editorial_selected', finalEditorialId); 


        formData.set('autores_selected_json', JSON.stringify(selectedAuthors));
        formData.set('generos_selected_json', JSON.stringify(selectedGenres));
        formData.set('imagenes_externas_json', JSON.stringify(externalImages));

        // No especificar 'Content-Type' con FormData; el navegador lo establece automáticamente.
        fetch(form.action, {
            method: form.method,
            body: formData 
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.json().catch(() => response.text()).then(errorText => {
                    throw new Error(errorText);
                });
            }
        })
        .then(data => {
            if (data.message) {
                localStorage.setItem('flashMessage', data.message);
                localStorage.setItem('flashCategory', data.category || 'info');
            }

            if (data.redirect) {
                window.location.href = data.redirect;
            } else {
                // Si no hay redirección
            }
        })
        .catch(error => {
            console.error('Error al enviar el formulario:', error);
            alert('Ocurrió un error al guardar los datos: ' + (error.message || 'Error desconocido'));
        });
    });
});