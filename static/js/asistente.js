const chat = document.getElementById('chat');

function animarTexto(burbuja, texto) {
  let i = 0;
  function escribir() {
    if (i < texto.length) {
      burbuja.textContent += texto.charAt(i++);
      setTimeout(escribir, 15);
    } else {
      burbuja.classList.remove('animada');
    }
  }
  burbuja.classList.add('animada');
  escribir();
}

function agregarMensaje(texto, clase, imagenSrc = null) {
  const mensaje = document.createElement('div');
  mensaje.className = `mensaje ${clase}`;

  const burbuja = document.createElement('div');
  burbuja.className = 'burbuja';

  // Si hay imagen, agrégala arriba de la burbuja
  if (imagenSrc) {
    const img = document.createElement('img');
    img.src = imagenSrc;
    img.className = 'imagen-mensaje';
    mensaje.appendChild(img);
  }

  if (clase === 'asistente') {
    animarTexto(burbuja, texto);
  } else {
    burbuja.textContent = texto;
  }

  mensaje.appendChild(burbuja);
  chat.appendChild(mensaje);
  chat.scrollTop = chat.scrollHeight;
}

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

  const consulta = document.getElementById('consulta').value.trim();
  if (!consulta) return;

  const formData = new FormData();
  const imagenInput = document.getElementById('imagen');
  const imagen = imagenInput.files[0];
  let imagenSrc = null;

  if (imagen) {
    const reader = new FileReader();
    reader.onload = function (e) {
      imagenSrc = e.target.result;
      agregarMensaje(consulta, 'usuario', imagenSrc);
    };
    reader.readAsDataURL(imagen);
  } else {
    agregarMensaje(consulta, 'usuario');
  }

  formData.append('consulta', consulta);
  formData.append('imagen', imagen || '');

  try {
    const response = await fetch('/consultar', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    // Espera la imagen si se leyó antes
    if (imagen && imagenSrc === null) {
      const waitForImg = new Promise(resolve => {
        const check = setInterval(() => {
          if (imagenSrc) {
            clearInterval(check);
            resolve();
          }
        }, 30);
      });
      await waitForImg;
    }

    agregarMensaje(data.mensaje || 'Sin respuesta.', 'asistente', imagenSrc);

  } catch (error) {
    console.error('Error:', error);
    agregarMensaje('❌ Error al procesar la consulta.', 'asistente');
  }

  document.getElementById('consulta').value = '';
  imagenInput.value = '';
  document.getElementById('imagenPrevioContainer').style.display = 'none';
});
