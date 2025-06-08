//Sript para abrir/cerrar menú
function toggleMenu() {
    const sidebar = document.getElementById('sidebar');
    const contenido = document.getElementById('contenido-principal');
    const overlay = document.getElementById('overlay');
    const body = document.body;
    sidebar.classList.toggle('activo');
    contenido.classList.toggle('desplazado');
    overlay.classList.toggle('activo');
    body.classList.toggle('menu-activo');
}


// Mostrar u ocultar select de deuda según tipo en formulario principal
function toggleDeudaSelect() {
    const tipo = document.getElementById('tipoSelect').value;
    const deudaSelect = document.getElementById('deudaSelect');
    if (tipo === 'abono_deuda' || tipo === 'abono_a_recibir') {
    deudaSelect.style.display = 'inline-block';
    deudaSelect.required = true;
    } else {
    deudaSelect.style.display = 'none';
    deudaSelect.required = false;
    deudaSelect.value = '';  // Limpiar selección si se oculta
    }
}



// Mostrar u ocultar select de deuda según tipo en modal editar
function toggleEditarDeudaSelect() {
    const tipo = document.getElementById('editarTipo').value;
    const deudaSelect = document.getElementById('editarDeudaSelect');
    if (tipo === 'abono_deuda' || tipo === 'abono_a_recibir') {
    deudaSelect.style.display = 'inline-block';
    deudaSelect.required = true;
    } else {
    deudaSelect.style.display = 'none';
    deudaSelect.required = false;
    deudaSelect.value = ''; // Limpiar selección si se oculta
    }
}
function capitalizePrimeraLetra(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}


function mostrarSeccion(seccion) {
    const secciones = ['ingresos', 'deudas', 'prestamos'];
    secciones.forEach(s => {
        const seccionElem = document.getElementById('seccion' + capitalizePrimeraLetra(s));
        const btnElem = document.getElementById('btn' + capitalizePrimeraLetra(s));
        if (seccionElem) seccionElem.classList.remove('activa');
        if (btnElem) btnElem.classList.remove('activo');
    });
    const seccionActiva = document.getElementById('seccion' + capitalizePrimeraLetra(seccion));
    const btnActivo = document.getElementById('btn' + capitalizePrimeraLetra(seccion));
    if (seccionActiva) seccionActiva.classList.add('activa');
    if (btnActivo) btnActivo.classList.add('activo');
}


function cambiarSeccion(seccion) {
    const url = new URL(window.location.href);
    url.searchParams.set('seccion', seccion);
    window.location.href = url.toString();
}
window.addEventListener('DOMContentLoaded', () => {
    const seccion = new URLSearchParams(window.location.search).get("seccion") || "ingresos";
    mostrarSeccion(seccion);
});


function mostrarFormulario(tipo) {
// Oculta todos
document.getElementById("form-movimiento").style.display = "none";
document.getElementById("form-prestamo").style.display = "none";
document.getElementById("form-deuda").style.display = "none";
// Muestra el seleccionado
if (tipo === "ingreso" || tipo === "gasto") {
    document.getElementById("form-movimiento").style.display = "block";
    document.getElementById("tipo").value = tipo;
} else if (tipo === "prestamo") {
    document.getElementById("form-prestamo").style.display = "block";
} else if (tipo === "deuda") {
    document.getElementById("form-deuda").style.display = "block";
}
}


 //Modal
function abrirModalAbono(prestamoId, saldoPendiente) {
document.getElementById('abonoPrestamoId').value = prestamoId;
document.getElementById('saldoPendienteModal').textContent = saldoPendiente.toFixed(2);
document.getElementById('modalAbono').classList.add('show');
}
function cerrarModalAbono() {
document.getElementById('modalAbono').classList.remove('show');
}



//botón de entrada por voz
const btnVoz = document.getElementById("btnVoz");
const entrada = document.getElementById("entradaVoz");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();

recognition.lang = 'es-ES';
btnVoz.addEventListener("click", () => {
  recognition.start();
});
recognition.onresult = (event) => {
  const texto = event.results[0][0].transcript;
  entrada.value = texto;
  procesarTexto(texto);
};

function procesarTexto(texto) {
  texto = texto.toLowerCase();
  const hoy = new Date();
  const ayer = new Date(hoy);
  ayer.setDate(hoy.getDate() - 1);
  let tipo = "";
  let fecha = "";
  let descripcion = "";
  let valor = "";
  let persona = "";
  // Fecha
  if (texto.includes("ayer")) fecha = ayer.toISOString().split("T")[0];
  else if (texto.includes("hoy")) fecha = hoy.toISOString().split("T")[0];
  else if (texto.match(/el \d+ de este mes/)) {
    const dia = texto.match(/el (\d+) de este mes/)[1];
    const mes = hoy.getMonth() + 1;
    const year = hoy.getFullYear();
    fecha = `${year}-${mes.toString().padStart(2, "0")}-${dia.padStart(2, "0")}`;
  }
  // Valor
  const montoMatch = texto.match(/(\d{4,})/);
  if (montoMatch) valor = montoMatch[1];
  // Clasificación
  if (texto.includes("me pagaron") || texto.includes("me llegó") || texto.includes("recibí")) {
    tipo = "ingreso";
    descripcion = "Pago recibido";
  } else if (texto.includes("compré") || texto.includes("gasté")) {
    tipo = "gasto";
    const descMatch = texto.match(/compré una? ([a-zñ\s]+)/);
    if (descMatch) descripcion = descMatch[1].trim();
  } else if (texto.includes("le presté") || texto.includes("pedí que le prestara")) {
    tipo = "prestamo";
    const personaMatch = texto.match(/a ([a-zñ\s]+)/);
    if (personaMatch) persona = personaMatch[1].trim();
    descripcion = "Préstamo a " + persona;
  } else if (texto.includes("compré con mi tarjeta")) {
    tipo = "deuda";
    descripcion = "Compra con tarjeta";
  }
  // Mostrar el formulario correcto
  if (tipo) {
    mostrarFormulario(tipo);
    document.getElementById("tipo").value = tipo;
  }
  // Llenar campos
  setTimeout(() => {
    if (fecha) document.querySelector("form[style*='block'] input[name='fecha']").value = fecha;
    if (valor) document.querySelector("form[style*='block'] input[name='valor']").value = valor;
    if (descripcion) document.querySelector("form[style*='block'] input[name='descripcion']").value = descripcion;
    if (persona && tipo === "prestamo") document.querySelector("#form-prestamo input[name='persona']").value = persona;
    if (persona && tipo === "deuda") document.querySelector("#form-deuda input[name='persona']").value = persona;
  }, 100);
}