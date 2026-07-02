// Variables globales
var categories = [];
var sizes = [];

// Función para inicializar datos
function initPortalData(cats, siz) {
    categories = cats || [];
    sizes = siz || [];
}

// Función para agregar fila
function addRow() {
    var tbody = document.getElementById("products-tbody");
    if (!tbody) {
        return;
    }

    var rowIndex = tbody.getElementsByTagName("tr").length;
    var row = document.createElement('tr');
    row.setAttribute('data-row', rowIndex);

    // Crear celdas básicas
    var cells = [
        '<input type="text" class="form-control form-control-sm" name="modelo_' + rowIndex + '" placeholder="Modelo *" required="required"/>',
        '<input type="text" class="form-control form-control-sm" name="nombre_' + rowIndex + '" placeholder="Nombre *" required="required"/>',
        '<input type="text" class="form-control form-control-sm" name="numero_' + rowIndex + '" placeholder="Número"/>',
        '<input type="text" class="form-control form-control-sm" name="otros_' + rowIndex + '" placeholder="Otros"/>',
        '<input type="number" class="form-control form-control-sm" name="cantidad_' + rowIndex + '" value="1" min="1" step="1"/>'
    ];

    // Agregar celdas básicas
    cells.forEach(function (cellHtml) {
        var cell = document.createElement('td');
        cell.innerHTML = cellHtml;
        row.appendChild(cell);
    });

    // Agregar productos y talles (5 pares)
    for (var i = 1; i <= 5; i++) {
        // Celda de producto
        var productCell = document.createElement('td');
        var productSelect = document.createElement('select');
        productSelect.className = 'form-control form-control-sm';
        productSelect.name = 'producto' + i + '_' + rowIndex;
        if (i === 1) {
            productSelect.required = true;
        }

        var defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = i === 1 ? 'Seleccionar *' : 'Seleccionar';
        productSelect.appendChild(defaultOption);

        // Agregar opciones de categorías
        if (categories && categories.length > 0) {
            categories.forEach(function (cat) {
                var option = document.createElement('option');
                option.value = cat.name;
                option.textContent = cat.name;
                productSelect.appendChild(option);
            });
        }

        productCell.appendChild(productSelect);
        row.appendChild(productCell);

        // Celda de talle
        var sizeCell = document.createElement('td');
        var sizeSelect = document.createElement('select');
        sizeSelect.className = 'form-control form-control-sm';
        sizeSelect.name = 'talle' + i + '_' + rowIndex;
        if (i === 1) {
            sizeSelect.required = true;
        }

        var defaultSizeOption = document.createElement('option');
        defaultSizeOption.value = '';
        defaultSizeOption.textContent = i === 1 ? 'Seleccionar *' : 'Seleccionar';
        sizeSelect.appendChild(defaultSizeOption);

        // Agregar opciones de talles
        if (sizes && sizes.length > 0) {
            sizes.forEach(function (size) {
                var option = document.createElement('option');
                option.value = size.name;
                option.textContent = size.name;
                sizeSelect.appendChild(option);
            });
        }

        sizeCell.appendChild(sizeSelect);
        row.appendChild(sizeCell);
    }

    // Celda de botón eliminar
    var buttonCell = document.createElement('td');
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-sm btn-danger';
    button.onclick = function () { removeRow(this); };
    button.innerHTML = '<i class="fa fa-trash"></i>';
    buttonCell.appendChild(button);
    row.appendChild(buttonCell);

    tbody.appendChild(row);
}

// Función para limpiar tabla
function clearTable() {
    if (confirm("¿Está seguro de que desea limpiar toda la tabla?")) {
        var tbody = document.getElementById("products-tbody");
        if (tbody) {
            tbody.innerHTML = "";
        }
    }
}

// Función para eliminar fila
function removeRow(button) {
    if (confirm("¿Está seguro de que desea eliminar esta fila?")) {
        button.closest("tr").remove();
    }
}

// Exponer helpers para depurar desde consola
// (Opcional: no estrictamente necesario, pero útil para verificar carga del asset)
if (typeof window !== 'undefined') {
    window.addRow = addRow;
    window.clearTable = clearTable;
    window.removeRow = removeRow;
}

function initPortalPage() {
    var form = document.getElementById("portal-details-form");
    if (form) {
        try {
            var catsAttr = form.getAttribute('data-categories');
            var sizesAttr = form.getAttribute('data-sizes');
            var cats = catsAttr ? JSON.parse(catsAttr) : [];
            var siz = sizesAttr ? JSON.parse(sizesAttr) : [];
            initPortalData(cats, siz);
        } catch (e) {
            // Error al parsear datos
        }
    }

    var addBtn = document.getElementById('add-row-btn');
    if (addBtn) {
        addBtn.addEventListener('click', function () { addRow(); });
    }
    var clearBtn = document.getElementById('clear-table-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function () { clearTable(); });
    }

    // Inicializar con una fila si la tabla está vacía
    var tbody = document.getElementById("products-tbody");
    if (tbody && tbody.getElementsByTagName('tr').length === 0) {
        addRow();
    }

    if (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();

            var rowsData = [];
            var tbodyEl = document.getElementById("products-tbody");
            var rows = tbodyEl ? tbodyEl.getElementsByTagName("tr") : [];

            for (var i = 0; i < rows.length; i++) {
                var row = rows[i];
                var rowData = {
                    modelo: row.querySelector('input[name="modelo_' + i + '"]')?.value || '',
                    nombre: row.querySelector('input[name="nombre_' + i + '"]')?.value || '',
                    numero: row.querySelector('input[name="numero_' + i + '"]')?.value || '',
                    otros: row.querySelector('input[name="otros_' + i + '"]')?.value || '',
                    cantidad: row.querySelector('input[name="cantidad_' + i + '"]')?.value || 1
                };

                for (var j = 1; j <= 5; j++) {
                    rowData["producto" + j] = row.querySelector('select[name="producto' + j + '_' + i + '"]')?.value || '';
                    rowData["talle" + j] = row.querySelector('select[name="talle' + j + '_' + i + '"]')?.value || '';
                }

                if (rowData.modelo && rowData.nombre && rowData.producto1 && rowData.talle1) {
                    rowsData.push(rowData);
                }
            }

            if (rowsData.length === 0) {
                alert("Debe agregar al menos una fila con modelo, nombre, producto 1 y talle 1.");
                return;
            }

            var jsonData = JSON.stringify(rowsData);
            var rowsDataInput = document.getElementById("rows_data");
            if (rowsDataInput) {
                rowsDataInput.value = jsonData;
            }
            this.submit();
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPortalPage);
} else {
    // DOM ya cargado y asset probablemente lazy: inicializar de inmediato
    initPortalPage();
}