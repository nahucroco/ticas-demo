
   const DEBUG = true;
   const log = (...a)=>{ if(DEBUG) console.log(...a); };
   const group=(l)=>{ if(DEBUG) console.group(l); };
   const groupEnd=()=>{ if(DEBUG) console.groupEnd(); };
   
   const LS_CANCHA_ID='crearPartido_selectCancha';
   const LS_UBICACION='crearPartido_ubicacionCancha';
   const LS_TIPO_ID='crearPartido_selectTipoCancha';
   
   function initSelect2Single($select, parentSel, iconRotSel){
   const idSel     = $select.attr("id");
   const isCancha  = idSel === "select-cancha";
   const isFormato = idSel === "select-tipocancha";
   
   // ---- flag: reset una sola vez por apertura ----
   let didResetOnThisOpen = false;
   
   $select.on('select2:open', () => {
    if (iconRotSel) document.querySelector(iconRotSel)?.classList.add('rotar');
    // no fuerces la label a 0.5 si no hay valor
   
    if (isCancha) {
      // 👉 evitá múltiples resets dentro de la misma apertura
      if (didResetOnThisOpen) return;
      didResetOnThisOpen = true;
   
      // limpiar selección
      $select.val(null).trigger('change.select2');
   
      // limpiar ubicación (valor + class + placeholder)
      const u = document.getElementById('ubicacion-cancha');
      if (u) {
        u.value = '';
        u.classList.remove('filled');     // 👈 QUITA "filled" SOLO EN ESTE OPEN
        u.setAttribute('placeholder', 'Ubicación');
        // si tenés syncBg enganchado a 'input', disparalo:
        u.dispatchEvent(new Event('input', { bubbles:true }));
      }
   
      // labels
      if (typeof setOpacity === 'function') {
        setOpacity(document.querySelector('.ubicacion-opacity'), 0);
        setOpacity(document.querySelector('.cancha-opacity'), 0);
        setOpacity(document.querySelector('.formato-opacity'), 0);
      }
   
      // limpiar + bloquear formato
      if (typeof fillFormatoOptions === 'function') fillFormatoOptions([]);
      if (typeof $selTipo === 'function') $selTipo().val(null).trigger('change.select2');
      if (typeof lockFormato === 'function') lockFormato();
    }
   
    // bloquear tipeo en Formato
    if (isFormato) {
      const input = document.querySelector('.select2-container--open .select2-search__field');
      if (input) {
        input.setAttribute('readonly', 'readonly');
        input.style.caretColor = 'transparent';
      }
    }
   });
   
   $select.on('select2:close', () => {
    if (iconRotSel) document.querySelector(iconRotSel)?.classList.remove('rotar');
    didResetOnThisOpen = false; // 👈 habilita reset para la próxima apertura
   });
   
     // ---- Al seleccionar: forzar single-select ----
     $select.on('select2:select', (e) => {
       const id = e.params.data.id; // puede ser id ("1") o texto si es tag en Cancha
       $select.val([id]).trigger('change.select2');
       $select.select2('close');
       markFilled();
     });
   
     // ---- Si cambian/limpian por código ----
     $select.on('change select2:clear', markFilled);
   }
   
   
   
$(function(){
  log('[Init] DOM listo');

  // 1) Inicializá Select2 (SIN poblar todavía)
  initSelect2Single($('#select-cancha'), '#s2-cancha', '.custom-icons svg:last-child');
  initSelect2Single($('#select-tipocancha'), '#s2-tipo', '#custom-icon-tipocancha svg:last-child');
  initSelect2s();           // ojo: que NO agregue opciones acá

  wireCanchaChange();

  // 2) Ahora sí: traé la data y recién ahí llená el select
  loadCanchasFromAPI().catch(err=>{
    console.error("Error cargando canchas:", err);
    // si querés, poné fallback acá y luego refreshCanchasSelect();
  });
});

   

// Alias para compatibilidad: usa la misma lógica que tu "filled"
// ✅ markFilled robusto: acepta jQuery, Event o DOM element
function markFilled(arg){
  // Normalizar a jQuery element
  const $el = (arg && arg.jquery)
    ? arg                                   // ya es jQuery
    : $(arg?.currentTarget || arg);         // Event o DOM

  if (!$el || !$el.length) return;

  const val = $el.val();
  const hasVal = Array.isArray(val) ? val.length > 0 : !!val;

  const $c = $el.siblings('.select2');      // contenedor visual de Select2
  $c.toggleClass('select2-has-value', hasVal);
  $c.toggleClass('filled', hasVal);         // coincide con tu CSS .select2.filled .select2-selection
}


   // === Enlazar JSON al Select y sincronizar datos relacionados ===
   
   // 1) Cargar canchas al select (desde canchas_activas_cargadas)
   function loadCanchasFromJSON() {
     const $sel = $('#select-cancha');
     $sel.empty().append('<option></option>'); // placeholder
   
     canchas_activas_cargadas.forEach(c => {
       const $opt = $('<option>')
         .val(String(c.id))
         .text(c.nombre)
         .attr('data-ubicacion', c.ubicacion || '')
         .attr('data-formato',  c.formato || '');
       $sel.append($opt);
     });
   
     // refresca contenedor select2 si ya estaba inicializado
     $sel.trigger('change.select2');
   }
   
   // 2) Buscar cancha por id (como string para evitar mismatch de tipos)
   function findCanchaById(id) {
     return canchas_activas_cargadas.find(c => String(c.id) === String(id));
   }
   
   // 3) Al cambiar de cancha: setear ubicación + formato
   function wireCanchaChange() {
     const $selCancha = $('#select-cancha');
     const $ubi       = $('#ubicacion-cancha');
     const $selTipo   = $('#select-tipocancha');
   
     $selCancha.on('change', function() {
       const val = $selCancha.val();
       const selectedId = Array.isArray(val) ? val[0] : val;
   
       const cancha = selectedId ? findCanchaById(selectedId) : null;
   
       // UBICACIÓN
       const lblUbi = document.querySelector('.ubicacion-opacity');
       if (cancha && cancha.ubicacion) {
         $ubi.val(cancha.ubicacion);
         if (lblUbi) lblUbi.style.opacity = 0.5;
         // si usás placeholder visible, podés limpiar: $ubi.attr('placeholder','');
       } else {
         $ubi.val('');
         if (lblUbi) lblUbi.style.opacity = 0;
       }
   
       // FORMATO
       const lblFormato = document.querySelector('.formato-opacity');
       const formatoTxt = cancha?.formato?.trim() || '';
   
       if (formatoTxt) {
         // si el formato no existe en el select, lo agrego como opción
         if ($selTipo.find(`option[value="${formatoTxt}"]`).length === 0) {
           $selTipo.append(new Option(formatoTxt, formatoTxt, false, false));
         }
         $selTipo.val([formatoTxt]).trigger('change.select2');
         if (lblFormato) lblFormato.style.opacity = 0.5;
       } else {
         $selTipo.val(null).trigger('change.select2');
         if (lblFormato) lblFormato.style.opacity = 0;
       }
   
       // LABEL DE CANCHA
       const lblCancha = document.querySelector('.cancha-opacity');
       if (lblCancha) lblCancha.style.opacity = selectedId ? 0.5 : 0;
     });
   }
   
   // 4) Inicializar carga y wiring
   $(function() {
     loadCanchasFromJSON();
     wireCanchaChange();
   
     // Si querés setear una cancha por defecto (opcional):
     // $('#select-cancha').val(['1']).trigger('change.select2');
   });

   /* ==== Datos ==== */
   const TIPOS_PREDEF = ["Fútbol 5","Fútbol 6","Fútbol 7","Fútbol 11","Fútbol Sala"];
   
let canchas_activas_cargadas = [];

function mapCanchaItem(it){
  return {
    id: it.id,
    nombre: it.nombre,
    ubicacion: it.ubicacion ?? it.direccion ?? "",
    formatos: Array.isArray(it.formatos) ? it.formatos
             : Array.isArray(it.tipo_cancha) ? it.tipo_cancha
             : []
  };
}

// Rellena <select id="select-cancha"> con las canchas cargadas
function refreshCanchasSelect(){
  const $sel = $('#select-cancha');
  $sel.empty().append('<option></option>');
  canchas_activas_cargadas.forEach(c => {
    $sel.append(new Option(c.nombre, String(c.id), false, false));
  });
  $sel.trigger('change.select2');
}

// Trae de la API y refresca el select
async function loadCanchasFromAPI(){
  const res = await fetch("/api/canchas/futbol", {
    headers: { "Accept": "application/json" },
    credentials: "same-origin"
  });
  const raw = await res.json();
  canchas_activas_cargadas = (Array.isArray(raw) ? raw : []).map(mapCanchaItem);
  console.log("Canchas cargadas:", canchas_activas_cargadas);
  refreshCanchasSelect();
}

// Corrige tu función previa: usa c.formatos (no c.formato)
function loadCanchasFromJSON() {
  refreshCanchasSelect(); // delega en la nueva
}


   /* ==== Helpers ==== */
   const $selCancha = () => $('#select-cancha');
   const $selTipo   = () => $('#select-tipocancha');
   const $ubi       = () => $('#ubicacion-cancha');
   
   const $lblCancha  = () => document.querySelector('.cancha-opacity');
   const $lblUbi     = () => document.querySelector('.ubicacion-opacity');
   const $lblFormato = () => document.querySelector('.formato-opacity');
   const setOpacity  = (el, v)=>{ if(el) el.style.opacity = v; };
   
   let formatoBloqueado = true;
   function lockFormato() {
     formatoBloqueado = true;
     $selTipo().data('locked', true);
     $selTipo().siblings('.select2').addClass('select2-disabled');
     setOpacity($lblFormato(), 0);
   }
   function unlockFormato() {
     formatoBloqueado = false;
     $selTipo().data('locked', false);
     $selTipo().siblings('.select2').removeClass('select2-disabled');
   }
   
   function fillFormatoOptions(list) {
     const $s = $selTipo();
     $s.empty().append('<option></option>');
     (list || []).forEach(f => $s.append(new Option(f, f, false, false)));
     $s.val(null).trigger('change.select2');
   }
   function fillFormatoFromCancha(cancha) {
     fillFormatoOptions(cancha?.formatos || []);
     if (cancha?.formatos?.length === 1) {
       $selTipo().val([cancha.formatos[0]]).trigger('change.select2');
     }
   }
   function fillFormatoPredef() {
     fillFormatoOptions(TIPOS_PREDEF);
   }
   
   function findCanchaById(id) {
     return canchas_activas_cargadas.find(c => String(c.id) === String(id));
   }
   
   /* === Gate de Formato (cancha o ubicación destraban) === */
   function reevaluateFormatoGate() {
     const val = $selCancha().val();
     const selected = Array.isArray(val) ? val[0] : val;     // puede ser "1" o "Club X" (tag)
     const canchaById = findCanchaById(selected);
     const typedUbi   = ($ubi().val() || '').trim();
   
     if (selected) {
       // Hay algo en Cancha: ¿es del JSON o es nueva?
       unlockFormato();
       if (canchaById) {
         // del JSON → autocompletar ubicación y formatos de esa cancha
         $ubi().val(canchaById.ubicacion || '');
         setOpacity($lblUbi(), canchaById.ubicacion ? 0.5 : 0);
         fillFormatoFromCancha(canchaById);
       } else {
         // NUEVA cancha escrita por el usuario → no tocar ubicación, usar TIPOS_PREDEF
         fillFormatoPredef();
         setOpacity($lblFormato(), 0); // que elija
       }
       setOpacity($lblCancha(), 0.5);
       return;
     }
   
     // Sin cancha seleccionada
     setOpacity($lblCancha(), 0);
     if (typedUbi.length > 0) {
       unlockFormato();
       fillFormatoPredef();
     } else {
       lockFormato();
       fillFormatoOptions([]);
     }
   }
   
   /* ==== Init ==== */
   function initSelect2s() {
     // Cancha con tags:true para permitir nuevas canchas
     $selCancha().select2({
       placeholder: $selCancha().data('placeholder') || 'Cancha',
       closeOnSelect: true,
       minimumResultsForSearch: 0,
       width: '100%',
       dropdownParent: $('#s2-cancha'),
       tags: true            // 👈 acepta canchas nuevas escritas
     });
   
     // Cargar opciones de canchas (JSON)
     $selCancha().empty().append('<option></option>');
     canchas_activas_cargadas.forEach(c => {
       $selCancha().append(new Option(c.nombre, String(c.id), false, false));
     });
   
     // Formato
     $selTipo().select2({
       placeholder: $selTipo().data('placeholder') || 'Formato',
       closeOnSelect: true,
       minimumResultsForSearch: 0,
       width: '100%',
       dropdownParent: $('#s2-tipo'),
       tags: false
     });
   
     // Evitar abrir Formato cuando está bloqueado
     $selTipo().on('select2:opening', (e) => {
       if ($selTipo().data('locked')) {
         e.preventDefault();
         return;
       }
       // Si abre, mostrar label
       setOpacity($lblFormato(), 0.5);
   
       // Si la opción de formato viene de una cancha del JSON, deshabilito tipeo;
       // si viene por ubicación o por cancha nueva, permito tipeo/búsqueda
       const val = $selCancha().val();
       const selected = Array.isArray(val) ? val[0] : val;
       const canchaById = findCanchaById(selected);
       const input = document.querySelector('.select2-container--open .select2-search__field');
       if (input) {
         if (canchaById) {
           input.setAttribute('readonly', 'readonly');
           input.style.caretColor = 'transparent';
         } else {
           input.removeAttribute('readonly');
           input.style.caretColor = '';
         }
       }
     });
   
     $selTipo().on('select2:close', () => {
       const hasVal = !!$selTipo().val() && $selTipo().val().length > 0;
       setOpacity($lblFormato(), hasVal ? 0.5 : 0);
     });
   
     // Forzar single-select en ambos
     $selCancha().on('select2:select', (e) => {
       const idOrText = e.params.data.id; // puede ser "1" o "Nueva Cancha"
       $selCancha().val([idOrText]).trigger('change.select2');
     });
     $selTipo().on('select2:select', (e) => {
       const id = e.params.data.id;
       $selTipo().val([id]).trigger('change.select2');
       setOpacity($lblFormato(), 0.5);
     });
   
     // Re-evaluar cuando cambien Cancha / Ubicación
     $selCancha().on('change', reevaluateFormatoGate);
     $ubi().on('input change', () => {
       // Si escribe ubicación y había una cancha del JSON, priorizamos flujo libre:
       const val = $selCancha().val();
       const selected = Array.isArray(val) ? val[0] : val;
       if (($ubi().val() || '').trim().length > 0 && findCanchaById(selected)) {
         // deseleccionar cancha del JSON para habilitar TIPOS_PREDEF
         $selCancha().val(null).trigger('change.select2');
         setOpacity($lblCancha(), 0);
       }
       setOpacity($lblUbi(), ($ubi().val()||'').trim() ? 0.5 : 0);
       reevaluateFormatoGate();
     });
   
     // Estado inicial
     lockFormato();
     setOpacity($lblCancha(), 0);
     setOpacity($lblUbi(), 0);
     setOpacity($lblFormato(), 0);
   }
   
   /* start */
   $(function(){ initSelect2s(); });
   
     // --- reset "una sola vez" por apertura ---
   let didResetOnThisOpen = false;
   
   $selCancha()
     .on('select2:open', function () {
       if (didResetOnThisOpen) return;
       didResetOnThisOpen = true;
   
       // limpiar selección previa de cancha
       $(this).val(null).trigger('change.select2');
   
       // limpiar ubicación
       $ubi().val('').trigger('input');
       setOpacity($lblUbi(), 0);
       setOpacity($lblCancha(), 0);
   
       // limpiar y bloquear formato
       fillFormatoOptions([]);
       $selTipo().val(null).trigger('change.select2');
       lockFormato();
       setOpacity($lblFormato(), 0);
     })
     .on('select2:close', function () {
       didResetOnThisOpen = false;
     });
   
   // --- al seleccionar CANCHA, rellenar al toque ubicación + formato ---
   $selCancha().on('select2:select', (e) => {
     const chosenIdOrText = e.params.data.id; // puede ser "1" (id) o texto si la escribieron
     // forzar single-select
     $selCancha().val([chosenIdOrText]).trigger('change.select2');
   
     const cancha = findCanchaById(chosenIdOrText);
   
     if (cancha) {
       // viene del JSON → autocompletar
       setUbicacion(cancha.ubicacion || '');
       setOpacity($lblUbi(), cancha.ubicacion ? 0.5 : 0);
   
       fillFormatoFromCancha(cancha); // carga cancha.formatos
       unlockFormato();
       setOpacity($lblFormato(), (cancha.formatos && cancha.formatos.length) ? 0.5 : 0);
     } else {
       // cancha escrita por el usuario → no tocamos ubicación, habilitamos TIPOS_PREDEF
       fillFormatoPredef();
       unlockFormato();
       setOpacity($lblFormato(), 0); // que elija
     }
   
     setOpacity($lblCancha(), 0.5);
   });
   
   function markSelect2Filled($el){
     const hasVal = !!$el.val() && $el.val().length > 0;
     $el.siblings('.select2').toggleClass('select2-has-value', hasVal);
   }
   
   // Llamalo después de inicializar Select2:
   markSelect2Filled($('#select-cancha'));
   markSelect2Filled($('#select-tipocancha'));
   
   $('#select-cancha').on('change select2:select select2:clear', function(){
     markSelect2Filled($(this));
   });
   $('#select-tipocancha').on('change select2:select select2:clear', function(){
     markSelect2Filled($(this));
   });
   
    const ubicacion = document.getElementById("ubicacion-cancha");
     const PH = ubicacion.getAttribute("placeholder") || "Ubicación";
   
           const tieneTexto = (t) => /\S/.test(t);  // 👈 cualquier no-espacio
   
           function syncBg() {
           const hayTexto = tieneTexto(ubicacion.value);
           if (hayTexto) {
               ubicacion.classList.add("filled");
               ubicacion.setAttribute("placeholder", "");
           } else {
               ubicacion.classList.remove("filled");
               ubicacion.setAttribute("placeholder", PH);
           }
           // (opcional) sincronizá la label flotante “Ubicacion”
           if (typeof setOpacity === "function") {
               const lblUbi = document.querySelector(".ubicacion-opacity");
               setOpacity(lblUbi, hayTexto ? 0.5 : 0);
           }
           }
   
     // Eventos de tipeo y cambios manuales
     ubicacion.addEventListener("input",  syncBg);
     ubicacion.addEventListener("change", syncBg);
   
     // Helper: usar SIEMPRE esto cuando completes la ubicación por código
     function setUbicacion(texto) {
       ubicacion.value = texto ?? "";
       syncBg(); // <<--- asegura que se pinte aunque no haya 'input' del usuario
     }
   
     // Estado inicial
     syncBg();



     // --- helpers ---
function blurActive() {
  const a = document.activeElement;
  if (a && typeof a.blur === 'function') a.blur();
  // select2 search input (por si quedó abierto)
  document.querySelectorAll('.select2-search__field').forEach(i => i.blur());
}

function setUbicacionEditable(on) {
  const $u = $('#ubicacion-cancha');
  $u.prop('readonly', !on);
  $u.toggleClass('readonly', !on);
}

// --- en TU handler ya existente de select de CANCHA ---
$selCancha().on('select2:select', (e) => {
  const chosenIdOrText = e.params.data.id; // "1" o texto
  $selCancha().val([chosenIdOrText]).trigger('change.select2');

  const cancha = findCanchaById(chosenIdOrText);

  if (cancha) {
    // viene del JSON → autocompletamos y bloqueamos edición de Ubicación
    setUbicacion(cancha.ubicacion || '');
    setOpacity($lblUbi(), cancha.ubicacion ? 0.5 : 0);
    setUbicacionEditable(false);      // 👈 NO se puede tipear
    blurActive();                      // 👈 saca el foco
    fillFormatoFromCancha(cancha);
    unlockFormato();
    setOpacity($lblFormato(), (cancha.formatos && cancha.formatos.length) ? 0.5 : 0);
  } else {
    // cancha escrita por el usuario → Ubicación editable
    setUbicacionEditable(true);       // 👈 SÍ se puede tipear
    fillFormatoPredef();
    unlockFormato();
    setOpacity($lblFormato(), 0);
  }

  setOpacity($lblCancha(), 0.5);
});
