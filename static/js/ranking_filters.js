// static/js/ranking_filters.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a elementos del DOM ---
    const clearFiltersBtn = document.getElementById('clear-filters-btn');
    const seriesIdSelect = document.getElementById('series_id');
    const authorIdSelect = document.getElementById('author_id');

    // --- Manejador para el botón "Limpiar Filtros" ---
    if (clearFiltersBtn) { // Asegurarse de que el botón existe
        clearFiltersBtn.addEventListener('click', () => {
            // Resetear los valores de los dropdowns a la opción "Todas las Series/Todos los Autores"
            seriesIdSelect.value = '';
            authorIdSelect.value = '';
            
            // Redirigir a la URL base de ranking para limpiar todos los filtros
            // Esto enviará una petición GET a /ranking sin parámetros
            window.location.href = '/ranking';
        });
    }

    // No se necesita lógica adicional para poblar/pre-seleccionar dropdowns
    // ni para manejar el submit del formulario, ya que Jinja2 y el navegador lo hacen.
});