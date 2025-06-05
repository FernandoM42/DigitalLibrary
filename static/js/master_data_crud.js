// static/js/master_data_crud.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Lógica para el formulario de Crear/Editar (que ya habíamos visto) ---
    const masterDataForm = document.getElementById('master-data-form');
    if (masterDataForm) { // Asegurarse de que el formulario existe en la página actual
        masterDataForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const itemId = masterDataForm.querySelector('input[name="item_id"]') ? masterDataForm.querySelector('input[name="item_id"]').value : null;
            const dataType = masterDataForm.querySelector('input[name="data_type"]').value;

            const payload = {};
            const formElements = masterDataForm.elements;

            for (let i = 0; i < formElements.length; i++) {
                const element = formElements[i];
                if (element.name && element.type !== 'submit' && element.type !== 'button') {
                    payload[element.name] = element.value.trim();
                }
            }

            delete payload.item_id;
            delete payload.data_type;

            let endpointUrl;
            if (itemId) { // Es edición
                endpointUrl = `/admin/${dataType}/${itemId}/edit`;
            } else { // Es creación
                endpointUrl = `/admin/${dataType}/new`;
            }

            console.log("DEBUG MASTER_CRUD: Enviando payload:", payload);
            console.log("DEBUG MASTER_CRUD: Hacia endpoint:", endpointUrl);

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
                    
                    let errorMessage = 'Error desconocido al guardar.';
                    if (typeof errorData === 'object' && errorData !== null && errorData.message) {
                        errorMessage = errorData.message; 
                    } else if (typeof errorData === 'string' && errorData.trim() !== '') {
                        errorMessage = errorData; 
                    } else if (response.statusText) {
                        errorMessage = response.statusText; 
                    }

                    console.error('DEBUG MASTER_CRUD: Error del servidor:', errorData);
                    alert(`Ocurrió un error: ${errorMessage}. Revisa la consola para más detalles.`);
                }
            } catch (error) {
                console.error('DEBUG MASTER_CRUD: Error de red o inesperado:', error);
                alert(`Ocurrió un error inesperado: ${error.message || 'Error desconocido'}. Revisa la consola para más detalles.`);
            }
        });
    }

    // --- Lógica para el botón de Eliminar (en master_list.html) ---
    // Usamos delegación de eventos porque los botones se renderizan en un bucle
    document.body.addEventListener('click', async (event) => {
        if (event.target.classList.contains('delete-master-btn')) {
            const deleteButton = event.target;
            const itemId = deleteButton.dataset.itemId;
            const itemName = deleteButton.dataset.itemName;
            const dataType = deleteButton.dataset.type;
            const deleteUrl = deleteButton.dataset.deleteUrl; // URL generada por Flask

            if (confirm(`¿Estás seguro de que quieres eliminar "${itemName}" de ${dataType}?`)) {
                try {
                    const response = await fetch(deleteUrl, {
                        method: 'POST', // Importante: es una petición POST
                        headers: {
                            'Content-Type': 'application/json', // Aunque no enviamos body, es buena práctica
                        },
                        body: JSON.stringify({confirm: true}) // Un pequeño body para la confirmación
                    });

                    const clonedResponse = response.clone();

                    if (response.ok) {
                        const data = await response.json();
                        if (data.message) {
                            localStorage.setItem('flashMessage', data.message);
                            localStorage.setItem('flashCategory', data.category || 'info');
                        }
                        if (data.redirect) {
                            window.location.href = data.redirect; // Redirigir a la lista actualizada
                        }
                    } else {
                        const errorData = await clonedResponse.json().catch(() => clonedResponse.text());
                        let errorMessage = 'Error desconocido al eliminar.';
                        if (typeof errorData === 'object' && errorData !== null && errorData.message) {
                            errorMessage = errorData.message;
                        } else if (typeof errorData === 'string' && errorData.trim() !== '') {
                            errorMessage = errorData;
                        } else if (response.statusText) {
                            errorMessage = response.statusText;
                        }
                        console.error('DEBUG MASTER_CRUD: Error del servidor al eliminar:', errorData);
                        alert(`Ocurrió un error al eliminar: ${errorMessage}. Revisa la consola.`);
                    }
                } catch (error) {
                    console.error('DEBUG MASTER_CRUD: Error de red o inesperado al eliminar:', error);
                    alert(`Error de red al eliminar: ${error.message || 'Error desconocido'}. Revisa la consola.`);
                }
            }
        }
    });
});