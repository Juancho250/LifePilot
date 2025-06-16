const chat = document.getElementById('chat');

function agregarMensaje(texto, clase) {
  const mensaje = document.createElement('div');
  mensaje.className = `mensaje ${clase}`;
  const burbuja = document.createElement('div');
  burbuja.className = 'burbuja';
  burbuja.textContent = texto;
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

document.getElementById('formulario1').addEventListener('submit', async function (e) 
{
  e.preventDefault();
  const consulta = document.getElementById('consulta').value.trim();
  
  if (!consulta) return;
  const formData = new FormData();
  const imagen = document.getElementById('imagen').files[0];
  formData.append('imagen', imagen);
  formData.append('consulta', consulta);
  agregarMensaje(consulta, 'usuario');

  try {
    const response = await fetch('/consultar', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    agregarMensaje(data.mensaje || 'Sin respuesta.', 'asistente');
  } 
  
  catch (error) {
    console.error('Error:', error);
    agregarMensaje('❌ Error al procesar la consulta.', 'asistente');
  }

  document.getElementById('consulta').value = '';
});
