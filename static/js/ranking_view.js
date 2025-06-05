// static/js/ranking_view.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a elementos del DOM ---
    const cardsViewBtn = document.getElementById('view-cards-btn');
    const listViewBtn = document.getElementById('view-list-btn');
    const cardsView = document.getElementById('ranking-cards-view');
    const listView = document.getElementById('ranking-list-view');

    // --- Función para aplicar/quitar clases de estilo ---
    function applyButtonStyles(button, isActive) {
        if (isActive) {
            button.classList.add('bg-blue-600', 'text-white', 'active');
            button.classList.remove('bg-gray-200', 'text-gray-700');
        } else {
            button.classList.remove('bg-blue-600', 'text-white', 'active');
            button.classList.add('bg-gray-200', 'text-gray-700');
        }
    }

    // --- Función para cambiar la vista ---
    function setView(view) {
        if (view === 'cards') {
            cardsView.classList.remove('hidden');
            listView.classList.add('hidden');
            applyButtonStyles(cardsViewBtn, true);  // Activar vista de tarjetas
            applyButtonStyles(listViewBtn, false); // Desactivar vista de lista
            localStorage.setItem('rankingView', 'cards'); // Guardar preferencia
        } else if (view === 'list') {
            cardsView.classList.add('hidden');
            listView.classList.remove('hidden');
            applyButtonStyles(cardsViewBtn, false); // Desactivar vista de tarjetas
            applyButtonStyles(listViewBtn, true);  // Activar vista de lista
            localStorage.setItem('rankingView', 'list'); // Guardar preferencia
        }
    }

    // --- Manejadores de Eventos ---
    cardsViewBtn.addEventListener('click', () => setView('cards'));
    listViewBtn.addEventListener('click', () => setView('list'));

    // --- Inicialización: Cargar preferencia desde localStorage o usar "cards" por defecto ---
    const savedView = localStorage.getItem('rankingView');
    // Asegurarse de que al inicio se apliquen los estilos correctos según la vista cargada
    setView(savedView || 'cards');
});