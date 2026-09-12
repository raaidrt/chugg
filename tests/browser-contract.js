import './host.js';
await import('./runtime/pyodide.js');
const originalPut = IDBObjectStore.prototype.put;
const originalIndexedDB = indexedDB;
window.chuggTestControls = {
  reset() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.deleteDatabase('chugg');
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
  },
  failWrites(enabled) {
    IDBObjectStore.prototype.put = enabled ? function(...args) {
      if (this.name === 'settings') throw new DOMException('Storage full', 'QuotaExceededError');
      return originalPut.apply(this, args);
    } : originalPut;
  },
  unavailable(enabled) { Object.defineProperty(window, 'indexedDB', {configurable: true, value: enabled ? undefined : originalIndexedDB}); }
};
try {
  const runtime = await loadPyodide({indexURL: new URL('./runtime/', import.meta.url).href});
  const response = await fetch('./app.zip');
  runtime.unpackArchive(await response.arrayBuffer(), 'zip', {extractDir:'/app'});
  const result = await runtime.runPythonAsync(`
import sys
sys.path.insert(0, '/app')
from js import chuggHost, chuggTestControls
from pyodide.ffi import create_proxy
from chugg.storage import Repository
from browser_contract import run
await run(Repository(chuggHost, create_proxy), chuggTestControls)
`);
  document.querySelector('h1').textContent = 'Browser contracts passed';
  for (const check of JSON.parse(result)) {
    const item = document.createElement('li'); item.textContent = check; document.querySelector('ol').append(item);
  }
} catch (error) {
  document.querySelector('h1').textContent = 'Browser contracts failed';
  document.querySelector('pre').textContent = String(error);
  console.error(error);
}
