function formatCurrency(input) {
    // Eliminar caracteres no numéricos
    let value = input.value.replace(/[^0-9]/g, '');

    // Si no hay valor, salimos de la función
    if (!value) {
        input.value = '';
        return;
    }

    // Formatear el número en pesos colombianos (sin decimales)
    value = new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0,  // Sin decimales
        maximumFractionDigits: 0
    }).format(value);

    // Asignar el valor formateado de vuelta al campo
    input.value = value;
}

function addProduct() {
    const productList = document.getElementById('product-list');
    const newProduct = document.createElement('div');
    newProduct.classList.add('form-product-item');
    newProduct.innerHTML = `
        <label for="name">Nombre del Producto</label>
        <input type="text" name="name[]" required>
        <label for="price">Precio (en pesos colombianos)</label>
        <input type="text" name="price[]" required oninput="formatCurrency(this)">
    `;
    productList.appendChild(newProduct);
}

function updateRatingValue(value) {
    document.getElementById('rating-value').innerText = value; // Actualiza el texto con el nuevo valor
}

