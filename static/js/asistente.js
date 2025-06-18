const chat = document.getElementById('chat');
let primerMensajeEnviado = false;
let autoScrollActivo = true;

// Detecta si el usuario está al final del chat (100px de margen)
function estaAlFinal() {
  return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 100;
}

// Scroll suave al final
function scrollSuaveAlFinal() {
  chat.scrollTo({
    top: chat.scrollHeight,
    behavior: 'smooth'
  });
}

// Escuchar cuando el usuario hace scroll manualmente
chat.addEventListener('scroll', () => {
  autoScrollActivo = estaAlFinal(); // solo activamos autoscroll si está abajo
});

// Reemplaza esto dentro de agregarMensaje o cuando el asistente responde:
function manejarScrollDespuesDeMensaje() {
  if (autoScrollActivo) {
    scrollSuaveAlFinal();
  }
}


function animarTexto(burbuja, texto) {
  let puntos = 0;
  const maxPuntos = 3;
  burbuja.textContent = 'Escribiendo';
  burbuja.classList.add('animada');

  const animacion = setInterval(() => {
    puntos = (puntos + 1) % (maxPuntos + 1);
    burbuja.textContent = 'Escribiendo' + '.'.repeat(puntos);
  }, 500);

  const procesado = texto
    .split('\n')
    .map(linea => {
      const trimmed = linea.trim();
      if (trimmed.match(/^([A-ZÁÉÍÓÚÜÑ][\w\s]+:)/)) {
        const parts = trimmed.split(':');
        return `<u><strong>${parts[0]}</strong></u>:${parts.slice(1).join(':')}`;
      }
      return trimmed;
    })
    .join('<br>');

  setTimeout(() => {
    clearInterval(animacion);
    burbuja.innerHTML = procesado;
    burbuja.classList.remove('animada');
    if (estaAlFinal()) chat.scrollTop = chat.scrollHeight;
  }, 2000);
}

function agregarMensaje(texto, clase, imagenSrc = null) {
  const mensaje = document.createElement('div');
  mensaje.className = `mensaje ${clase}`;

  const burbuja = document.createElement('div');
  burbuja.className = 'burbuja';

  if (imagenSrc && clase === 'usuario') {
    const img = document.createElement('img');
    img.src = imagenSrc;
    img.className = 'imagen-mensaje';
    mensaje.appendChild(img);
  }

  if (clase === 'asistente') {
    texto = texto.replace(/\*\*/g, '');
    animarTexto(burbuja, texto);
  } else {
    burbuja.textContent = texto;
  }

  mensaje.appendChild(burbuja);
  chat.appendChild(mensaje);
  if (estaAlFinal()) chat.scrollTop = chat.scrollHeight;
}

// Mostrar mensaje de bienvenida al cargar
window.addEventListener('DOMContentLoaded', () => {
  if (typeof NOMBRE_USUARIO !== 'undefined' && NOMBRE_USUARIO) {
    const mensajeBienvenida = `👋 Bienvenido, ${NOMBRE_USUARIO}`;
    agregarMensaje(mensajeBienvenida, 'asistente');
  }
});

document.getElementById('imagen').addEventListener('change', function (event) {
  const imagen = event.target.files[0];
  if (imagen) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const imgPreview = document.getElementById('imagenPrevio');
      imgPreview.src = e.target.result;
      document.getElementById('imagenPrevioContainer').style.display = 'block';
    };
    reader.readAsDataURL(imagen);
  }
});

document.getElementById('formulario1').addEventListener('submit', async function (e) {
  e.preventDefault();

  const consultaInput = document.getElementById('consulta');
  const consulta = consultaInput.value.trim();
  const imagenInput = document.getElementById('imagen');
  const imagen = imagenInput.files[0];

  if (!consulta) return;

  // Quitar mensaje de bienvenida solo la primera vez
  if (!primerMensajeEnviado) {
    const mensajes = document.querySelectorAll('#chat .mensaje.asistente');
    mensajes.forEach(m => {
      if (m.innerText.includes('Bienvenido')) {
        m.remove();
      }
    });
    primerMensajeEnviado = true;
  }

  let imagenSrc = null;

  if (imagen) {
    const reader = new FileReader();
    reader.onload = async function (e) {
      imagenSrc = e.target.result;
      agregarMensaje(consulta, 'usuario', imagenSrc);
    };
    reader.readAsDataURL(imagen);
  } else {
    agregarMensaje(consulta, 'usuario');
  }

  consultaInput.value = '';
  imagenInput.value = '';
  document.getElementById('imagenPrevioContainer').style.display = 'none';

  const formData = new FormData();
  formData.append('consulta', consulta);
  formData.append('imagen', imagen || '');

  try {
    const response = await fetch('/consultar', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (imagen && !imagenSrc) {
      await new Promise(resolve => {
        const check = setInterval(() => {
          if (imagenSrc) {
            clearInterval(check);
            resolve();
          }
        }, 50);
      });
    }

    agregarMensaje(data.mensaje || 'Sin respuesta.', 'asistente');
  } catch (error) {
    console.error('Error:', error);
    agregarMensaje('❌ Error al procesar la consulta.', 'asistente');
  }
});
