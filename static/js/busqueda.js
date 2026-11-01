document.addEventListener("DOMContentLoaded", () => {
  let currentTab = "jugadores";
  let datosCompletos = { jugadores: [], equipos: [], torneos: [] };
  const contenedor = document.querySelector('#resultados-api');
  const contenedorRecientes = document.querySelector('.busqueda-container-recientesx');
  const contenedorEnter = document.querySelector('.busqueda-container-enter');
  const inputBusqueda = document.querySelector('.search-input');
  const formBusqueda = document.getElementById('form-busqueda');
  const borrarhistorial = document.querySelector('.borrar-historial a');
  const filtro = inputBusqueda.value.toLowerCase().trim();


function fetchData(tab, callback) {
  fetch(`/api/busqueda/${tab}/`)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      // Si la API devuelve {results: [...]}, usá eso; si ya es array, dejalo
      datosCompletos[tab] = Array.isArray(data) ? data : (data.results || []);
      if (typeof callback === 'function') callback();
    })
    .catch(err => {
      console.error('Error cargando', tab, err);
      datosCompletos[tab] = [];
      if (typeof callback === 'function') callback();
    });
}

  formBusqueda.addEventListener('submit', (e) => {

    e.preventDefault();
    const texto = inputBusqueda.value.toLowerCase().trim();
    const errorContainer = document.querySelector('.error-busqueda');

    errorContainer.innerHTML = `<p>No se encontró ningún resultado con el nombre "<strong>${texto}</strong>".</p>`;


    if (texto.length < 4) {
      Swal.fire({
        icon: 'warning',
        title: 'Búsqueda demasiado corta',
        text: 'Por favor, escribí al menos 4 caracteres para buscar.',
        confirmButtonColor: '#7e3ff2'
      });
      return;
    }
    /*      mostrarSkeleton();
         setTimeout(() => {
      intentarRenderizar(0);
    }, 600); // Mostrar mientras busca */
    inputBusqueda.addEventListener('input', () => {
      const texto = inputBusqueda.value.trim();

      if (texto === '') {
        contenedorEnter.style.display = 'none';
        contenedorRecientes.style.display = 'block';
        borrarhistorial.style.display = 'block';

        // Quitar selección activa de tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

        // Volver a mostrar los recientes desde localStorage
        mostrarBusquedasRecientes();
      }
    });




    contenedorRecientes.style.display = 'none';
    borrarhistorial.style.display = 'none';
    contenedorEnter.style.display = 'block';

    // Buscar en todos los tabs y mostrar el primero que tenga resultados
    let encontrado = false;
    const tabs = ['jugadores', 'equipos', 'torneos'];


    function intentarRenderizar(idx) {
      if (idx >= tabs.length) {
        // Si no se encontró ningún resultado en ningún tab
        errorContainer.style.display = 'block';
        errorContainer.innerHTML = `<p>No se encontró ningún resultado.</p>`;
        contenedor.innerHTML = '';
        return;
      }

      const tab = tabs[idx];

      function continuar() {
        const datos = datosCompletos[tab] || [];
        const resultados = datos.filter(item => (item.nombre || '').toLowerCase().includes(filtro));

        if (resultados.length > 0) {
          currentTab = tab;
          document.querySelectorAll('.tab').forEach(t => {
            t.classList.remove('active');
            if (t.dataset.tab === tab) t.classList.add('active');
          });
          renderizar(tab, texto);
        } else {
          intentarRenderizar(idx + 1);
        }
      }

      if (datosCompletos[tab].length === 0) {
        fetchData(tab, continuar);
      } else {
        continuar();
      }
    }

    intentarRenderizar(0);
  });

  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const texto = inputBusqueda.value.toLowerCase().trim();

      if (texto.length >= 0 && texto.length < 4) {
        Swal.fire({
          icon: 'warning',
          title: 'Búsqueda demasiado corta',
          text: 'Por favor, escribí al menos 4 caracteres para cambiar de pestaña con búsqueda activa.',
          confirmButtonColor: '#7e3ff2'
        });
        return;
      }

      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentTab = tab.dataset.tab;

      if (datosCompletos[currentTab].length === 0) {
        fetchData(currentTab, () => renderizar(currentTab, texto));
      } else {
        renderizar(currentTab, texto);
      }
    });
  });

  fetchData("jugadores", () => renderizar("jugadores", ""));
  mostrarBusquedasRecientes();

  function renderizar(tab, filtro) {
    const datos = datosCompletos[tab] || [];
    contenedor.innerHTML = '';

    const errorContainer = document.querySelector('.error-busqueda');

    const resultados = datos.filter(item => item.nombre.toLowerCase().includes(filtro));

    if (resultados.length === 0) {
      const label = tab === "jugadores" ? "jugador" : tab === "equipos" ? "equipo" : "torneo";
      errorContainer.innerHTML = `<p>No se ha encontrado ningún ${label} con el nombre "<strong>${filtro}</strong>".</p>`;
      errorContainer.style.display = 'block'; // ✅ Solo si no hay resultados
      return;
    }

    errorContainer.style.display = 'none'; // ✅ Oculta si hay resultados

    resultados.forEach(item => {
      const link = document.createElement('a');
      if (tab === "jugadores") {
        link.href = `/perfil/${item.id}/`; // <-- ruta a perfil de jugador
      } 
      else if (tab == "equipos") {
        link.href = `/equipos/${item.id}` ;
      } 
      else if (tab == "torneos") {
        link.href = `/torneo/${item.id}` ;
      }
      else {
        link.href = '#' ;
      }

      link.classList.add("busqueda-link");

      const img_path = `${item.img_path || 'avatar_default.png'}`;
      let html = `<div class="busqueda-item">
          <img src="${img_path}" class="avatar" alt="Imagen de ${item.nombre}" onerror="this.onerror=null; this.src='/static/images/escudo-equipo/equipo-a.png'">
          <div class="info">
            <strong>${item.nombre}</strong>`;

      if (tab !== "torneos") html += `<span>${item.provincia}&nbsp;&nbsp;${item.ciudad}</span>`;
      html += `</div>`;

      if (tab === "jugadores") {
        const icono = obtenerIconoPorPosicion(item.posicion_preferida);
        if (icono) html += `<img src="${icono}" class="pos-img" alt="${item.posicion_preferida}">`;
      }

      if (tab === "equipos") {
        html += `<img src="/static/images/busqueda/equipo_cantjugadores.png" class="pos-img" alt="Cantidad de jugadores">
                 <span class="equipo-cantjugadores">${item.jugadores}</span>`;
      }

      if (tab === "torneos") {
        html += `<img src="/static/images/busqueda/torneo_cantequipos.png" class="pos-img" alt="Cantidad de equipos">
                 <span class="torneo_cantequipos">${item.participantes}</span>`;
      }

      html += `</div>`;
      link.innerHTML = html;
      link.addEventListener('click', (e) => {
        guardarBusquedaReciente(item, tab);
        return;
      });


      contenedor.appendChild(link);
    });
  }

  function guardarBusquedaReciente(item, tipo) {
    let recientes = JSON.parse(localStorage.getItem('busquedas_recientes')) || [];
    item.tipo = tipo;
    recientes = recientes.filter(i => !(i.nombre === item.nombre && i.tipo === tipo));
    recientes.unshift(item);
    if (recientes.length > 8) recientes = recientes.slice(0, 8);
    localStorage.setItem('busquedas_recientes', JSON.stringify(recientes));
  }

  function mostrarBusquedasRecientes() {
    const contenedor = document.querySelector('.busqueda-items');
    const footer = document.querySelector('.footer-busqueda');
    const recientes = JSON.parse(localStorage.getItem('busquedas_recientes')) || [];

    contenedor.innerHTML = '';

    if (recientes.length === 0) {
      contenedor.innerHTML = `
      <div class="sin-recientes">
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 24 24" style="opacity: 0.6;">
          <path d="M21.71 20.29l-3.387-3.387A7.935 7.935 0 0 0 18 11a8 8 0 1 0-3.903 6.854l3.387 3.387a1 1 0 0 0 1.414-1.414zM4 11a7 7 0 1 1 7 7 7.008 7.008 0 0 1-7-7z"/>
        </svg>
        <p>No hay búsquedas recientes todavía.</p>
      </div>`;
      footer.style.display = 'none';
      return;
    }

    contenedor.innerHTML = `<p class="recientes-label">Búsquedas recientes</p>`;

    recientes.forEach(item => {
      const link = document.createElement('a');
      link.href = "#";
      link.classList.add("busqueda-link");

      const img_path = `${item.img_path || 'avatar_default.png'}`;
      let html = `<div class="busqueda-item">
        <img src="${img_path}" class="avatar" alt="Imagen de ${item.nombre}" onerror="this.onerror=null; this.src='/static/images/escudo-equipo/equipo-a.png'">
        <div class="info">
          <strong>${item.nombre}</strong>`;

      if (item.tipo !== "torneos" && item.tipo !== "equipos") {
        html += `<span>${item.provincia}&nbsp;&nbsp;${item.ciudad}</span>`;
      }

      html += `</div>`;

      if (item.tipo === "jugadores") {
        const icono = obtenerIconoPorPosicion(item.posicion_preferida);
        if (icono) html += `<img src="${icono}" class="pos-img" alt="${item.posicion_preferida}">`;
      }

     

      html += `</div>`;
      link.innerHTML = html;

      link.addEventListener('click', (e) => {
        e.preventDefault();
        inputBusqueda.value = item.nombre;
        formBusqueda.dispatchEvent(new Event('submit'));
      });

      contenedor.appendChild(link);
    });

    footer.style.display = 'block';
  }

  function obtenerIconoPorPosicion(posicion) {
    const base = "/static/images/busqueda/";
    switch (posicion?.toLowerCase()) {
      case 'arquero': return base + "arquero.png";
      case 'defensa': return base + "defensa.png";
      case 'delantero': return base + "delantero.png";
      case 'mediocampista': return base + "mediocampista.png";
      default: return base + "delantero.png";
    }
  }
});
document.getElementById('borrarHistorial').addEventListener('click', function (e) {
  e.preventDefault();

  const contenedor = document.querySelector('.busqueda-items');
  const footer = document.querySelector('.footer-busqueda');

  // Animar salida
  contenedor.classList.add('fade-out');

  setTimeout(() => {
    // Borrar historial
    localStorage.removeItem('busquedas_recientes');

    // Reemplazar contenido por mensaje vacío
    contenedor.innerHTML = `
      <div class="sin-recientes">
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 24 24" style="opacity: 0.6;">
          <path d="M21.71 20.29l-3.387-3.387A7.935 7.935 0 0 0 18 11a8 8 0 1 0-3.903 6.854l3.387 3.387a1 1 0 0 0 1.414-1.414zM4 11a7 7 0 1 1 7 7 7.008 7.008 0 0 1-7-7z"/>
        </svg>
        <p>No hay búsquedas recientes todavía.</p>
      </div>`;

    // Ocultar botón
    footer.style.display = 'none';

    // Quitar clase para futuros usos
    contenedor.classList.remove('fade-out');
  }, 400);
});

function mostrarSkeleton() {
  const contenedor = document.getElementById('resultados-api');
  contenedor.innerHTML = `
    <div class="skeleton-loader">
      <div class="skeleton skeleton-banner"></div>
      ${[...Array(4)].map(() => `
        <div class="skeleton-row">
          <div class="skeleton skeleton-avatar"></div>
          <div class="skeleton-lines">
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
          </div>
        </div>`).join('')}
    </div>
  `;
}