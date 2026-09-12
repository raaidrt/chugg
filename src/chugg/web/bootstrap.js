import {registerOffline} from './host.js';

try {
  await import('./runtime/pyodide.js');
  const {loadPyodide} = globalThis;
  const runtime = await loadPyodide({indexURL: new URL('./runtime/', import.meta.url).href});
  const response = await fetch(new URL('./app.zip', import.meta.url));
  if (!response.ok) throw new Error('Could not load Chugg.');
  runtime.unpackArchive(await response.arrayBuffer(), 'zip', {extractDir: '/app'});
  await runtime.runPythonAsync(`
import sys
assert sys.version_info[:2] == (3, 14), "Chugg requires Python 3.14"
sys.path.insert(0, '/app')
import chugg.entry
`);
  await registerOffline();
} catch (error) {
  console.error(error);
  const message = document.createElement('p');
  message.setAttribute('role', 'alert');
  message.textContent = 'Chugg couldn’t load. Please reload while online to finish downloading the app.';
  document.getElementById('root').replaceChildren(message);
}
