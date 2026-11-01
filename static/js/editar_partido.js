document.addEventListener("DOMContentLoaded", function () {
  const tabs = document.querySelectorAll('.tab');
  const tabContents = document.querySelectorAll('.contenido-tab');

  // Botones internos de equipo (deben tener data-equipo="equipo-1", etc.)
  const botones = document.querySelectorAll(".boton-cambia-equipo");
  const contenedores = {
    "equipo-1": document.querySelector("#equipo-1"),
    "equipo-2": document.querySelector("#equipo-2")
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const selectedId = tab.dataset.tab;

      // Activar solo la pestaña seleccionada
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      // Mostrar contenido correspondiente
      tabContents.forEach(content => {
        content.classList.toggle('active', content.id === selectedId);
      });
    });
  });

  // Sistema de botones dentro de una pestaña
  botones.forEach(btn => {
    btn.addEventListener("click", () => {
      botones.forEach(b => b.classList.remove("activo"));
      btn.classList.add("activo");

      const equipo = btn.dataset.equipo;
      Object.entries(contenedores).forEach(([key, cont]) => {
        cont.classList.toggle("hidden", key !== equipo);
      });
    });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const tabs = document.querySelectorAll('.tab');
  const tabContents = document.querySelectorAll('.equipo-lista-jugadores');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const selectedId = tab.dataset.tab;

      // Activar pestaña
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      // Mostrar solo el equipo correspondiente
      tabContents.forEach(content => {
        content.classList.toggle('hidden', content.id !== selectedId);
      });
    });
  });
});


