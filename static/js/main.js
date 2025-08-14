// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("main.js: DOMContentLoaded disparado. Buscando tarjetas de libro...");
    const bookCards = document.querySelectorAll('.group[data-images-raw]');

    if (bookCards.length === 0) {
        console.warn("main.js: No se encontraron tarjetas de libro con el atributo data-images-raw.");
    }

    bookCards.forEach((card, cardIndex) => {
        console.log(`--- main.js: Procesando tarjeta #${cardIndex} ---`);
        const rawImagesString = card.dataset.imagesRaw;
        console.log(`rawImagesString para tarjeta #<span class="math-inline">\{cardIndex\}\: "</span>{rawImagesString}"`);

        let images = [];

        if (rawImagesString) {
            // Modificación: usar split('; ') es crucial para separar las URLs
            rawImagesString.split('; ').forEach(imgData => {
                // Esta regex extrae la URL y la descripción.
                // Asegúrate de que tu formato en la DB es "URL [Descripción]"
                const parts = imgData.match(/(.*) \[(.*)\]/);
                if (parts && parts.length === 3) {
                    images.push({ url: parts[1], description: parts[2] });
                } else {
                    console.warn(`main.js: No se pudo parsear el dato de imagen para tarjeta #<span class="math-inline">\{cardIndex\}\: "</span>{imgData}"`);
                    // Si hay solo URL sin descripción, pruébalo aquí:
                    // images.push({ url: imgData.trim(), description: 'Imagen de portada' });
                }
            });
        }
        console.log(`Imágenes parseadas para tarjeta #${cardIndex}:`, images);


        const imageElement = card.querySelector('.book-image');
        const noImagePlaceholder = card.querySelector('.no-image-placeholder');
        const prevBtn = card.querySelector('.prev-image-btn');
        const nextBtn = card.querySelector('.next-image-btn');
        const indicatorsContainer = card.querySelector('.image-indicators');

        let currentImageIndex = 0;

        function showImage(index) {
            console.log(`showImage llamada para tarjeta #${cardIndex}, índice: ${index}`);
            if (images.length === 0) {
                console.log(`Tarjeta #${cardIndex}: No hay imágenes, mostrando placeholder.`);
                imageElement.style.display = 'none';
                noImagePlaceholder.classList.remove('hidden');
                prevBtn.classList.add('hidden');
                nextBtn.classList.add('hidden');
                indicatorsContainer.classList.add('hidden');
                return;
            }

            currentImageIndex = (index + images.length) % images.length;

            // *** CRÍTICO: Aquí se asigna la URL ***
            imageElement.src = images[currentImageIndex].url;
            imageElement.alt = images[currentImageIndex].description;
            imageElement.style.display = 'block'; // Asegura que la imagen sea visible
            noImagePlaceholder.classList.add('hidden'); // Oculta el placeholder
            console.log(`Tarjeta #${cardIndex} - Estableciendo imagen src a: ${imageElement.src}`);
            console.log(`Tarjeta #${cardIndex} - Estilo de display de imagen: ${imageElement.style.display}`);

            updateIndicators();

            if (images.length <= 1) {
                prevBtn.classList.add('hidden');
                nextBtn.classList.add('hidden');
                indicatorsContainer.classList.add('hidden');
            } else {
                prevBtn.classList.remove('hidden');
                nextBtn.classList.remove('hidden');
                indicatorsContainer.classList.remove('hidden');
            }
        }

        // ... (resto del código: updateIndicators, event listeners, showImage(0)) ...

        function updateIndicators() {
            indicatorsContainer.innerHTML = '';
            images.forEach((_, idx) => {
                const dot = document.createElement('div');
                dot.classList.add('w-2', 'h-2', 'rounded-full', 'bg-white', 'bg-opacity-50', 'cursor-pointer');
                if (idx === currentImageIndex) {
                    dot.classList.remove('bg-opacity-50');
                    dot.classList.add('bg-opacity-100');
                }
                dot.addEventListener('click', () => showImage(idx));
                indicatorsContainer.appendChild(dot);
            });
        }

        prevBtn.addEventListener('click', () => showImage(currentImageIndex - 1));
        nextBtn.addEventListener('click', () => showImage(currentImageIndex + 1));

        // Llamada inicial para mostrar la primera imagen
        showImage(0);
    });

    // --- NUEVA LÓGICA: Modal "Ver más" para Sinopsis ---
    const sinopsisModal = document.getElementById('sinopsis-modal');
    const sinopsisModalTitle = document.getElementById('sinopsis-modal-title');
    const fullSinopsisText = document.getElementById('full-sinopsis-text');
    const sinopsisModalCloseBtn = document.getElementById('sinopsis-modal-close-btn');

    // *** AÑADIR ESTAS LÍNEAS DE DEPURACIÓN (VERIFICAR REFERENCIAS DOM) ***
    console.log("DEBUG MAIN.JS: sinopsisModal element:", sinopsisModal);
    console.log("DEBUG MAIN.JS: sinopsisModalTitle element:", sinopsisModalTitle);
    console.log("DEBUG MAIN.JS: fullSinopsisText element:", fullSinopsisText);
    console.log("DEBUG MAIN.JS: sinopsisModalCloseBtn element:", sinopsisModalCloseBtn);
    // ***************************************************

    /**
     * Abre el modal de sinopsis con el texto completo.
     * @param {string} bookTitle - Título del libro.
     * @param {string} sinopsis - Texto completo de la sinopsis.
     */
    function openSinopsisModal(bookTitle, sinopsis) {
        sinopsisModalTitle.textContent = bookTitle;
        fullSinopsisText.textContent = sinopsis;
        sinopsisModal.classList.remove('hidden'); // Mostrar el modal
    }

    /**
     * Cierra el modal de sinopsis.
     */
    function closeSinopsisModal() {
        sinopsisModal.classList.add('hidden'); // Ocultar el modal
        sinopsisModalTitle.textContent = '';
        fullSinopsisText.textContent = '';
    }

    // Manejador para el botón "Ver más" (delegación de eventos)
    document.body.addEventListener('click', (event) => {
        if (event.target.classList.contains('ver-mas-btn')) {
            const button = event.target;
            const bookTitle = button.dataset.obraTitle;
            const fullSinopsis = button.dataset.fullSinopsis;
            openSinopsisModal(bookTitle, fullSinopsis);
        }
    });

    // Manejador para el botón de cerrar (X) del modal
    sinopsisModalCloseBtn.addEventListener('click', closeSinopsisModal);

    // Manejador para cerrar el modal al hacer clic fuera de su contenido
    sinopsisModal.addEventListener('click', (event) => {
        // Cierra el modal solo si el clic fue directamente en el fondo (overlay), no en el contenido del modal
        if (event.target === sinopsisModal) {
            closeSinopsisModal();
        }
    });
});