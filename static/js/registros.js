document.addEventListener("DOMContentLoaded", () => {
  const secciones = {
    ingresos: document.getElementById("seccionIngresos"),
    deudas: document.getElementById("seccionDeudas"),
    prestamos: document.getElementById("seccionPrestamos"),
  };

  const links = {
    ingresos: document.getElementById("btnIngresos"),
    deudas: document.getElementById("btnDeudas"),
    prestamos: document.getElementById("btnPrestamos"),
  };

  window.cambiarSeccion = function (nombre) {
    // Oculta todas las secciones
    Object.values(secciones).forEach(sec => sec.classList.remove("activa"));
    // Muestra la seleccionada
    if (secciones[nombre]) {
      secciones[nombre].classList.add("activa");
    }

    // Quita clase activa de todos los botones/enlaces
    Object.values(links).forEach(link => link.classList.remove("activo"));
    // Añade clase activa al actual
    if (links[nombre]) {
      links[nombre].classList.add("activo");
    }

    // También actualiza el input hidden del formulario
    const inputSeccion = document.querySelector('input[name="seccion"]');
    if (inputSeccion) {
      inputSeccion.value = nombre;
    }

    // Opcional: actualizar el parámetro en la URL sin recargar
    const params = new URLSearchParams(window.location.search);
    params.set("seccion", nombre);
    const nuevaUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', nuevaUrl);
  };
});




/*--------------------------------------
---------------Modal Imprimir--------------
----------------------------------------*/

function abrirModalImpresion(seccion) {
  document.getElementById('seccionFiltro').value = seccion;

  const tipoLabel = document.getElementById('label-tipo');
  const tipoSelect = document.getElementById('tipo');
  const estadoLabel = document.getElementById('label-estado');
  const estadoSelect = document.getElementById('estado');

  if (seccion === 'ingresos') {
    tipoLabel.style.display = tipoSelect.style.display = 'block';
    estadoLabel.style.display = estadoSelect.style.display = 'none';
  } else if (seccion === 'deudas' || seccion === 'prestamos') {
    tipoLabel.style.display = tipoSelect.style.display = 'none';
    estadoLabel.style.display = estadoSelect.style.display = 'block';
  } else {
    tipoLabel.style.display = tipoSelect.style.display =
    estadoLabel.style.display = estadoSelect.style.display = 'none';
  }

  document.getElementById('modalImpresion').style.display = 'flex';
}

function cerrarModalImpresion() {
  document.getElementById('modalImpresion').style.display = 'none';
}

// Enviar filtros y cargar PDF en iframe oculto
document.getElementById('formularioFiltroImpresion').addEventListener('submit', function (e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const params = new URLSearchParams(formData).toString();
  const iframe = document.getElementById('iframeImpresion');
  iframe.src = `/exportar_pdf?${params}`;
});

// Imprimir automáticamente desde el iframe cuando esté listo
function imprimirDesdeIframe() {
  const iframe = document.getElementById('iframeImpresion');
  if (iframe.contentWindow && iframe.contentDocument.readyState === 'complete') {
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
  }
}




/*--------------------------------------
---------------Modal abono--------------
----------------------------------------*/

// Seleccionamos el modal y los elementos del formulario
// Modal Abono
const modalAbono = document.getElementById('modalAbono');
const abonoPrestamoIdInput = document.getElementById('abonoPrestamoId');
const saldoPendienteSpan = document.getElementById('saldoPendienteModal');

// Abrir el modal con datos
function abrirModalAbono(id, saldo) {
  abonoPrestamoIdInput.value = id;
  saldoPendienteSpan.textContent = parseFloat(saldo).toFixed(2);
  modalAbono.classList.add('show');
}

// Cerrar modal
function cerrarModalAbono() {
  modalAbono.classList.remove('show');
}

// Cerrar al hacer clic fuera del contenido
window.addEventListener('click', function (e) {
  if (e.target === modalAbono) {
    cerrarModalAbono();
  }
});

// Exponer funciones
window.abrirModalAbono = abrirModalAbono;
window.cerrarModalAbono = cerrarModalAbono;


/*-------------------------------------->
<!----------Modal detalles-------------->
<!--------------------------------------*/
        document.querySelectorAll('.fila-modal-detalles').forEach(fila => {
            fila.addEventListener('click', () => {
            const modal = document.getElementById('modal-detalles');
            const contenedor = document.getElementById('modal-detalles-contenido-info');

            // Limpiar contenido anterior
            contenedor.innerHTML = '';

            // Recorremos los atributos data- para mostrar la info
            for (const attr of fila.attributes) {
                if (attr.name.startsWith('data-') && attr.value.trim() !== '') {
                // Formatear label (data-monto_inicial -> Monto inicial)
                let label = attr.name.replace('data-', '').replace(/_/g, ' ');
                label = label.charAt(0).toUpperCase() + label.slice(1);

                // Crear párrafo con label y valor
                const p = document.createElement('p');
                p.innerHTML = `<strong>${label}:</strong> ${attr.value}`;
                contenedor.appendChild(p);
                }
            }

            // Verificar si es un préstamo y mostrar botón
            const tipo = fila.getAttribute('data-tipo');
            const saldo = parseFloat(fila.getAttribute('data-saldo') || 0);
            const idMovimiento = fila.getAttribute('data-id');

            const divBotones = document.getElementById('modal-detalles-certificado');
            divBotones.innerHTML = '';

            if (tipo === 'prestamo' || tipo === 'deuda') {
              const btn = document.createElement('button');
              btn.textContent = saldo <= 0 ? 'Generar Paz y Salvo' : 'Generar Documento de Deuda';
              btn.onclick = () => {
                window.open(`/certificado_prestamo/${idMovimiento}`, '_blank');
              };
              divBotones.appendChild(btn);
            }

            // Mostrar modal
            modal.classList.add('show');
            modal.setAttribute('aria-hidden', 'false');
            });
        });

        function cerrarModalDetalles() {
            const modal = document.getElementById('modal-detalles');
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        }

        // Cerrar modal si clic fuera del contenido
        window.addEventListener('click', e => {
            const modal = document.getElementById('modal-detalles');
            if (e.target === modal) cerrarModalDetalles();
        });

        // Cerrar modal con tecla ESC
        window.addEventListener('keydown', e => {
            if (e.key === "Escape") cerrarModalDetalles();
        });


        