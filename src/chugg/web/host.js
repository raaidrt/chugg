/* Browser primitives only. Application decisions and rendered content live in Python. */
let dispatch = () => {};
let registration;
let offline = {ready: false, refresh: false, error: false};
const notify = () => dispatch('offline', JSON.stringify(offline));

function database() {
  return new Promise((resolve, reject) => {
    if (!globalThis.indexedDB) return reject(new Error('Device storage is unavailable. Progress cannot be saved in this browser.'));
    const request = indexedDB.open('chugg', 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore('progress', {keyPath: ['lineId', 'side']});
      request.result.createObjectStore('settings');
    };
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      db.onversionchange = () => db.close();
      resolve(db);
    };
  });
}

async function transaction(mutation) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['progress', 'settings'], mutation ? 'readwrite' : 'readonly');
    let failure, result, pending = 2;
    const snapshot = {};
    tx.oncomplete = () => { db.close(); resolve(JSON.stringify(result)); };
    tx.onabort = () => { db.close(); reject(failure || tx.error || new Error('Device storage is unavailable.')); };
    tx.onerror = () => {};
    const loaded = () => {
      if (--pending) return;
      try {
        // Python runs synchronously inside this IDB callback, keeping the transaction active.
        result = mutation ? JSON.parse(mutation(JSON.stringify(snapshot))) : snapshot;
        if (mutation) {
          for (const row of result.progress) tx.objectStore('progress').put(row);
          if (result.preferences) tx.objectStore('settings').put(result.preferences, 'preferences');
        }
      } catch (error) { failure = error; tx.abort(); }
    };
    const rows = tx.objectStore('progress').getAll();
    rows.onsuccess = () => {snapshot.progress = rows.result; loaded();};
    const prefs = tx.objectStore('settings').get('preferences');
    prefs.onsuccess = () => {snapshot.preferences = prefs.result || null; loaded();};
  });
}

/* Morph the existing DOM toward the new markup instead of replacing it, so unchanged
   elements persist across renders: entrance animations play only on real entry, focus
   and caret survive, and only what actually changed repaints. */
function morph(current, next) {
  if (current.isEqualNode(next)) return;
  if (current.nodeType !== next.nodeType || current.nodeName !== next.nodeName) {
    current.replaceWith(next);
    return;
  }
  if (current.nodeType !== Node.ELEMENT_NODE) {
    current.data = next.data;
    return;
  }
  for (const name of current.getAttributeNames()) {
    // The browser owns a dialog's open state; showModal reconciles it after the morph.
    if (!next.hasAttribute(name) && !(name === 'open' && current.localName === 'dialog')) current.removeAttribute(name);
  }
  for (const name of next.getAttributeNames()) {
    if (current.getAttribute(name) !== next.getAttribute(name)) current.setAttribute(name, next.getAttribute(name));
  }
  morphChildren(current, next);
  if (current === document.activeElement) return;
  // Once a field has been touched its attributes stop driving the live value.
  if (current instanceof HTMLInputElement && current.type !== 'file') current.value = next.getAttribute('value') ?? '';
  if (current instanceof HTMLSelectElement) {
    const marked = current.querySelector('option[selected]');
    current.selectedIndex = marked ? marked.index : 0;
  }
}

function morphChildren(current, next) {
  const existing = [...current.childNodes];
  const desired = [...next.childNodes];
  for (let index = 0; index < desired.length; index += 1) {
    if (index < existing.length) morph(existing[index], desired[index]);
    else current.append(desired[index]);
  }
  for (const node of existing.slice(desired.length)) node.remove();
}

window.chuggHost = {
  bind(callback) { dispatch = callback; notify(); },
  render(markup, focus) {
    const root = document.getElementById('root');
    const active = document.activeElement;
    const action = active?.getAttribute('data-action');
    const value = active?.getAttribute('data-value');
    const start = active instanceof HTMLInputElement ? active.selectionStart : null;
    const end = active instanceof HTMLInputElement ? active.selectionEnd : null;
    const hadDialog = Boolean(root.querySelector('dialog[open]'));
    const template = document.createElement('template');
    template.innerHTML = markup;
    morphChildren(root, template.content);
    const dialog = root.querySelector('dialog');
    if (dialog && !dialog.open) dialog.showModal();
    if (focus) root.querySelector(focus)?.focus({preventScroll: true});
    else if (action && (!dialog || hadDialog)) {
      const candidates = [...root.querySelectorAll('[data-action]')];
      const next = candidates.find(el => el.getAttribute('data-action') === action && el.getAttribute('data-value') === value);
      next?.focus({preventScroll: true});
      if (next instanceof HTMLInputElement && start !== null) next.setSelectionRange(start, end);
    }
  },
  snapshot: () => transaction(null),
  transact: callback => transaction(callback),
  environment: () => JSON.stringify({standalone: matchMedia('(display-mode: standalone)').matches || navigator.standalone === true, android: /Android/i.test(navigator.userAgent), online: navigator.onLine}),
  date: timestamp => new Date(timestamp).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}),
  scroll: () => window.scrollTo({top: 0}),
  async persist() { return navigator.storage?.persist ? await navigator.storage.persisted() || await navigator.storage.persist() : false; },
  download(contents, filename) {
    const url = URL.createObjectURL(new Blob([contents], {type: 'application/json'}));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },
  async update() {
    if (registration?.waiting) registration.waiting.postMessage({type: 'SKIP_WAITING'});
    else await registration?.update();
  }
};
document.addEventListener('click', event => {
  const target = event.target.closest('[data-action]');
  if (!target || target.disabled || target.matches('input, select')) return;
  if (target.dataset.action === 'choose-backup') document.querySelector('input[type=file]').click();
  else dispatch(target.dataset.action, target.dataset.value || '');
});
document.addEventListener('input', event => {
  if (event.target.dataset.action === 'search') dispatch('search', event.target.value);
});
document.addEventListener('change', async event => {
  const target = event.target;
  if (target.type === 'file') {
    const file = target.files?.[0]; target.value = '';
    if (!file) return;
    try {
      if (file.size > 2 * 1024 * 1024) throw new Error('This backup is too large. Choose a file smaller than 2 MB.');
      dispatch('import', await file.text());
    } catch (error) {dispatch('file-error', error.message);}
  } else if (target.dataset.action) dispatch(target.dataset.action, target.value);
});
document.addEventListener('cancel', event => {event.preventDefault(); dispatch('close', '');}, true);
window.addEventListener('online', () => dispatch('online', 'true'));
window.addEventListener('offline', () => dispatch('online', 'false'));

export async function registerOffline() {
  if (!('serviceWorker' in navigator)) {offline.error = true; notify(); return;}
  let reloading = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!reloading) { reloading = true; location.reload(); }
  });
  try {
    registration = await navigator.serviceWorker.register(new URL('sw.js', import.meta.url), {scope: './'});
    offline.ready = Boolean(registration.active);
    offline.refresh = Boolean(registration.waiting && registration.active);
    registration.addEventListener('updatefound', () => {
      const worker = registration.installing;
      worker?.addEventListener('statechange', () => {
        if (worker.state === 'installed') {
          offline.refresh = Boolean(navigator.serviceWorker.controller);
          offline.ready = Boolean(registration.active) || !offline.refresh;
          notify();
        } else if (worker.state === 'redundant' && !registration.active) {
          offline.error = true; notify();
        }
      });
    });
    notify();
  } catch {offline.error = true; notify();}
}
