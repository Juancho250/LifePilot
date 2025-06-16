      function mostrarImagen() {
        const imagenInput = document.querySelector("#imagen");
        const imagenPrevioContainer = document.querySelector("#imagenPrevioContainer");
        const imagenPrevio = document.querySelector("#imagenPrevio");
        const consultaTextarea = document.querySelector("#consulta");
        const resultadoPre = document.querySelector("#resultado");
  
        if (imagenInput.files && imagenInput.files[0]) {
          const reader = new FileReader();
  
          reader.onload = function (e) {
            imagenPrevio.src = e.target.result;
            // Mostrar el div de la imagen cuando se selecciona una imagen
            imagenPrevioContainer.style.display = "block";
            // Borrar el contenido del textarea y del resultado
            consultaTextarea.value = "";
            resultadoPre.innerHTML = "";
          };
  
          reader.readAsDataURL(imagenInput.files[0]);
        } else {
          // Ocultar el div de la imagen cuando no se selecciona una imagen
          imagenPrevioContainer.style.display = "none";
        }
      }
  
      const formulario1 = document.querySelector("#formulario1");
      document.querySelector("#imagen").addEventListener("change", () => {
        mostrarImagen()
      })
  
      function escaparCaracteresHTML(texto) {
        return texto.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      }
  
  
      formulario1.addEventListener("submit", evento => {
        evento.preventDefault();
  
        const consulta = document.querySelector("#consulta").value.trim();
        const imagenInput = document.querySelector("#imagen");
        const imagen = imagenInput.files[0];
  
        const botonConsultar = document.querySelector("input[type='submit']");
        botonConsultar.disabled = true;
        botonConsultar.value = "Espere, por favor...";
  
        const datosFormulario = new FormData();
        datosFormulario.append("consulta", consulta);
        datosFormulario.append("imagen", imagen);
  
        fetch("consultar", {
          method: 'POST',
          body: datosFormulario
        }).then(respuesta => respuesta.json())
          .then(respuesta => {
            document.querySelector("#resultado").innerHTML = `${escaparCaracteresHTML(respuesta.mensaje)}<br>`;
            botonConsultar.disabled = false;
            botonConsultar.value = "Consultar";
          })
          .catch(error => {
            console.error('Error en la solicitud fetch:', error);
            botonConsultar.disabled = false;
            botonConsultar.value = "Consultar";
          });
      });
    