(()=> {
  const $ = (id) => document.getElementById(id);
  const overlay = $('swa-overlay');
  const dialog  = $('swa-dialog');
  const titleEl = $('swa-title');
  const descEl  = $('swa-desc');
  const btnOk   = $('swa-btn-confirm');
  const btnCan  = $('swa-btn-cancel');
  const actions = $('swa-actions');

  const VARIANTS = ['info','success','warning','error'];
  let resolveFn = null, timerId = null;
  let defaults = {
    title: '',
    text:  '',
    html:  null,                 // si lo usás, reemplaza a text
    icon:  'info',               // info|success|warning|error
    confirmButtonText: 'Aceptar',
    cancelButtonText:  'Cancelar',
    showCancelButton:  true,
    allowOutsideClick: true,
    allowEscapeKey:    true,
    focusConfirm:      true,
    reverseButtons:    false,
    timer:             0,  
    showActions:       true,   // 👈 nuevo      // ms, 0 = sin timer
  };

  function cleanup() {
    if (timerId) { clearTimeout(timerId); timerId = null; }
    document.removeEventListener('keydown', onKey);
    overlay.removeEventListener('click', onOutside);
    btnOk.onclick = btnCan.onclick = null;
  }

  function onKey(e) {
    if (e.key === 'Escape' && currentOpts.allowEscapeKey) {
      close({isConfirmed:false, isDismissed:true, dismiss:'esc'});
    }
    if (e.key === 'Enter') {
      // enter confirma si el foco está en el diálogo
      if (document.activeElement && dialog.contains(document.activeElement)) {
        close({isConfirmed:true, isDismissed:false});
      }
    }
  }

  function onOutside(e) {
    if (e.target === overlay && currentOpts.allowOutsideClick) {
      close({isConfirmed:false, isDismissed:true, dismiss:'backdrop'});
    }
  }

  let currentOpts = {...defaults};

  function open(opts) {
    currentOpts = {...defaults, ...(opts||{})};
    actions.style.display = currentOpts.showActions === false ? 'none' : '';


    // contenido
    titleEl.textContent = currentOpts.title || '';
    if (currentOpts.html != null) {
      descEl.innerHTML = currentOpts.html;
    } else {
      descEl.textContent = currentOpts.text || '';
    }

    // variante (icon -> clase)
    dialog.classList.remove(...VARIANTS.map(v => 'swa--'+v));
    if (VARIANTS.includes(currentOpts.icon)) {
      dialog.classList.add('swa--' + currentOpts.icon);
    }

    // botones
    btnOk.querySelector('.swa__btn-text').textContent   = currentOpts.confirmButtonText;
    btnCan.querySelector('.swa__btn-text').textContent  = currentOpts.cancelButtonText;
    btnCan.style.display = currentOpts.showCancelButton ? '' : 'none';
    actions.style.display = currentOpts.showActions === false ? 'none' : '';


    // orden de botones
    btnOk.style.order  = currentOpts.reverseButtons ? 0 : 1;
    btnCan.style.order = currentOpts.reverseButtons ? 1 : 0;

    // mostrar
    overlay.classList.remove('swa--hidden');
    overlay.setAttribute('aria-hidden', 'false');
    overlay.classList.add('is-open');
    document.body.style.overflow = 'hidden';

    // listeners
    btnOk.onclick  = () => close({isConfirmed:true,  isDismissed:false});
    btnCan.onclick = () => close({isConfirmed:false, isDismissed:true, dismiss:'cancel'});
    document.addEventListener('keydown', onKey);
    overlay.addEventListener('click', onOutside, { once:false });

    // foco
    setTimeout(() => (currentOpts.focusConfirm ? btnOk : btnCan).focus(), 0);

    // timer
    if (currentOpts.timer > 0) {
      timerId = setTimeout(() => close({isConfirmed:false, isDismissed:true, dismiss:'timer'}), currentOpts.timer);
    }

    // hooks
    if (typeof currentOpts.willOpen === 'function') currentOpts.willOpen(dialog);
    setTimeout(() => { if (typeof currentOpts.didOpen === 'function') currentOpts.didOpen(dialog); }, 0);
  }

  function close(result) {
    cleanup();
    overlay.classList.add('swa--hidden');
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';

    if (typeof currentOpts.willClose === 'function') currentOpts.willClose(dialog);
    const r = result || { isConfirmed:false, isDismissed:true, dismiss:'close' };
    if (resolveFn) { const fn = resolveFn; resolveFn = null; fn(r); }
    if (typeof currentOpts.didClose === 'function') currentOpts.didClose(dialog);
  }

  function fire(opts) {
    return new Promise((resolve) => {
      resolveFn = resolve;
      open(opts);
    });
  }

  function update(partialOpts) {
    // actualizar en vivo sin cerrar
    open({...currentOpts, ...(partialOpts||{})});
  }

  function setDefaults(newDefs) { defaults = {...defaults, ...(newDefs||{})}; }

  // API pública
  window.swa = { fire, close, update, setDefaults };
})();