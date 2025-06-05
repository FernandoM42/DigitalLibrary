// static/js/rating_modal.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DEBUG RATING MODAL: DOMContentLoaded cargado. Script inicializado."); 
    // --- Referencias a elementos del DOM del Modal ---
    const ratingModal = document.getElementById('rating-modal');
    const ratingForm = document.getElementById('rating-form'); // El formulario principal para guardar/actualizar
    const ratingBookTitleSpan = document.getElementById('rating-book-title');
    const ratingBookIdInput = document.getElementById('rating-book-id');
    const puntuacionInput = document.getElementById('puntuacion');
    const comentariosInput = document.getElementById('comentarios');
    const fechaRankingInput = document.getElementById('fecha_ranking');
    const ratingClearBtn = document.getElementById('rating-clear-btn');
    const ratingDeleteBtn = document.getElementById('rating-delete-btn'); 
    const ratingSaveBtn = document.getElementById('rating-save-btn'); 
    const ratingCloseBtn = document.getElementById('rating-close-btn');

    // --- Variables de Estado del Modal ---
    let currentBookId = null;
    let currentBookTitle = '';

    // --- Funciones de Control del Modal ---

    /**
     * Abre el modal de valoración y pre-llena los campos si hay datos existentes.
     * @param {number} bookId - ID del libro a valorar.
     * @param {string} bookTitle - Título del libro.
     * @param {string|number} currentPuntuacion - Puntuación actual del libro (si existe).
     * @param {string} currentComentarios - Comentarios actuales (si existen).
     * @param {string} currentFechaRanking - Fecha de valoración actual (si existe, formatoYYYY-MM-DD).
     */
    function openRatingModal(bookId, bookTitle, currentPuntuacion, currentComentarios, currentFechaRanking) {
        currentBookId = bookId;
        currentBookTitle = bookTitle;

        ratingBookTitleSpan.textContent = bookTitle;
        ratingBookIdInput.value = bookId;
        puntuacionInput.value = currentPuntuacion || '';
        comentariosInput.value = currentComentarios || '';
        
        if (currentFechaRanking) {
            fechaRankingInput.value = currentFechaRanking;
        } else {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            fechaRankingInput.value = `${year}-${month}-${day}`;
        }

        ratingModal.classList.remove('hidden'); // Mostrar el modal
    }

    /**
     * Cierra el modal de valoración y limpia los campos.
     */
    function closeRatingModal() {
        ratingModal.classList.add('hidden'); // Ocultar el modal
        clearRatingForm(); // Limpiar campos al cerrar
        currentBookId = null;
        currentBookTitle = '';
    }

    /**
     * Limpia los campos del formulario de valoración.
     */
    function clearRatingForm() {
        puntuacionInput.value = '';
        comentariosInput.value = '';
        fechaRankingInput.value = '';
    }

    /**
     * Recarga la página actual para reflejar los cambios en el ranking.
     */
    function reloadPage() {
        window.location.reload();
    }

    // --- Manejadores de Eventos ---

    // 1. Botones "Valorar" en las tarjetas de libros (delegación de eventos)
    document.body.addEventListener('click', (event) => {
        if (event.target.classList.contains('open-rating-modal-btn')) {
            console.log("DEBUG RATING MODAL: Clic en botón 'Valorar'.");
            const button = event.target;
            const bookId = parseInt(button.dataset.bookId);
            const bookTitle = button.dataset.bookTitle;
            const puntuacion = button.dataset.puntuacion;
            const comentarios = button.dataset.comentarios;
            const fechaRanking = button.dataset.fechaRanking;

            openRatingModal(bookId, bookTitle, puntuacion, comentarios, fechaRanking);
        }
    });

    // 2. Botón "Limpiar" dentro del modal
    ratingClearBtn.addEventListener('click', () => {
        console.log("DEBUG RATING MODAL: Clic en botón 'Limpiar'.");
        clearRatingForm();
    });

    // 3. Botón "Eliminar Valoración" dentro del modal *** MODIFICACIÓN CLAVE AQUÍ ***
    ratingDeleteBtn.addEventListener('click', async () => {
        console.log("DEBUG RATING MODAL: Clic en botón 'Eliminar Valoración'.");
        if (!currentBookId) {
            alert("No hay un libro seleccionado para eliminar la valoración.");
            return;
        }
        if (confirm(`¿Estás seguro de que quieres eliminar la valoración de "${currentBookTitle}"?`)) {
            // El payload solo necesita el ID del libro, la eliminación se hace por ID en la URL
            const deleteUrl = `/api/delete_rating/${currentBookId}`; // *** NUEVA URL ***

            console.log("DEBUG RATING MODAL: Enviando DELETE request a:", deleteUrl);

            try {
                const response = await fetch(deleteUrl, {
                    method: 'POST', // Sigue siendo POST para la API de Flask
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}) // Cuerpo vacío o mínimo
                });

                const clonedResponse = response.clone();
                if (response.ok) {
                    const data = await response.json();
                    if (data.message) {
                        localStorage.setItem('flashMessage', data.message);
                        localStorage.setItem('flashCategory', data.category || 'info');
                    }
                    closeRatingModal();
                    reloadPage();
                } else {
                    const errorData = await clonedResponse.json().catch(() => clonedResponse.text());
                    let errorMessage = (typeof errorData === 'object' && errorData !== null && errorData.message) ? errorData.message : String(errorData);
                    console.error('DEBUG RATING MODAL: Error del servidor al eliminar valoración:', errorData);
                    alert(`Ocurrió un error al eliminar la valoración: ${errorMessage}. Revisa la consola.`);
                }
            } catch (error) {
                console.error('DEBUG RATING MODAL: Error de red o inesperado al eliminar valoración:', error);
                alert(`Error de red al eliminar valoración: ${error.message || 'Error desconocido'}. Revisa la consola.`);
            }
        }
    });

    // 4. Botón "Cerrar" dentro del modal
    ratingCloseBtn.addEventListener('click', () => {
        console.log("DEBUG RATING MODAL: Clic en botón 'Cerrar'.");
        closeRatingModal();
    });

    // 5. Envío del formulario de valoración
    ratingForm.addEventListener('submit', async (event) => {
        console.log("DEBUG RATING MODAL: Evento 'submit' del formulario ratingForm disparado.");
        event.preventDefault(); 

        const idObra = parseInt(ratingBookIdInput.value);
        const puntuacion = puntuacionInput.value.trim() !== '' ? parseFloat(puntuacionInput.value.trim()) : null;
        const comentarios = comentariosInput.value.trim() || null;
        const fechaRanking = fechaRankingInput.value.trim() || null;

        // Validaciones básicas: ESTAS VALIDACIONES AHORA SÓLO APLICAN PARA "GUARDAR"
        if (!idObra) {
            alert('Error: No se pudo obtener el ID del libro.');
            return;
        }
        if (puntuacion === null && comentarios === null && fechaRanking === null) {
            alert('Por favor, ingresa al menos una puntuación, comentario o fecha para valorar el libro.');
            return;
        }
        if (puntuacion !== null && (puntuacion < 1 || puntuacion > 10)) {
            alert('La puntuación debe ser entre 1 y 10.');
            return;
        }

        const payload = {
            id_obra: idObra,
            puntuacion: puntuacion,
            comentarios: comentarios,
            fecha_ranking: fechaRanking
        };

        console.log("DEBUG RATING MODAL: Enviando payload:", payload);

        try {
            const response = await fetch('/api/rate_book', {
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
                closeRatingModal(); // Cerrar modal al éxito
                reloadPage(); // Recargar la página para reflejar el cambio
            } else {
                const errorData = await clonedResponse.json().catch(() => clonedResponse.text()); 
                
                let errorMessage = 'Error desconocido al guardar valoración.';
                if (typeof errorData === 'object' && errorData !== null && errorData.message) {
                    errorMessage = errorData.message; 
                } else if (typeof errorData === 'string' && errorData.trim() !== '') {
                    errorMessage = errorData; 
                } else if (response.statusText) {
                    errorMessage = response.statusText; 
                }

                console.error('DEBUG RATING MODAL: Error del servidor:', errorData);
                alert(`Ocurrió un error al guardar la valoración: ${errorMessage}. Revisa la consola para más detalles.`);
            }
        } catch (error) {
            console.error('DEBUG RATING MODAL: Error de red o inesperado:', error);
            alert(`Error de red al guardar valoración: ${error.message || 'Error desconocido'}. Revisa la consola.`);
        }
    });
});