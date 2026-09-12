import { useRef, useState, type ChangeEvent } from 'react';
import { Download, Upload, HardDrive } from 'lucide-react';
import { exportBackup, importBackup, MAX_BACKUP_BYTES, requestPersistence } from '../lib/progress';
import { DeviceDialog } from './DeviceDialog';

export function DataSettings({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: () => void | Promise<void>;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage('');
    setError('');
    try {
      await action();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'Device storage is unavailable. Please try again.',
      );
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    const contents = await exportBackup();
    const url = URL.createObjectURL(new Blob([contents], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `chugg-backup-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    setMessage('Backup prepared. Keep the downloaded JSON file somewhere safe.');
  }
  function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    void run(async () => {
      if (file.size > MAX_BACKUP_BYTES)
        throw new Error('This backup is too large. Choose a file smaller than 2 MB.');
      await importBackup(await file.text());
      setMessage('Backup imported. Your newest results and highest completion counts were kept.');
      try {
        await onImported();
      } catch {
        setError(
          'The backup was saved, but the view could not refresh. Close this dialog and reload Chugg.',
        );
      }
    });
  }
  return (
    <DeviceDialog title="Settings and backups" id="data-title" onClose={onClose}>
      <div className="device-dialog-icon">
        <HardDrive size={28} />
      </div>
      <p>
        Chugg saves progress and preferences on this device. There’s no account, cloud database, or
        automatic sync.
      </p>
      <section className="device-dialog-section">
        <h3>Keep a copy</h3>
        <p>
          Export a backup before switching phones or clearing browser data. You can import it into
          Chugg on another device.
        </p>
        <div className="device-dialog-actions">
          <button disabled={busy} onClick={() => void run(download)}>
            <Download size={17} /> Export backup
          </button>
          <button disabled={busy} onClick={() => fileInput.current?.click()}>
            <Upload size={17} /> Import backup
          </button>
        </div>
        <input
          hidden
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          aria-label="Choose Chugg backup"
          onChange={upload}
        />
        <p className="device-dialog-small">
          Import merges results without counting the same backup twice. Existing preferences are
          kept. JSON files up to 2 MB.
        </p>
      </section>
      <section className="device-dialog-section">
        <h3>Protect local progress</h3>
        <p>
          Ask your browser to keep Chugg’s data when device storage runs low. Backups are still
          useful if you clear data or lose your phone.
        </p>
        <button
          className="device-dialog-persist"
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const granted = await requestPersistence();
              setMessage(
                granted
                  ? 'Persistent storage is enabled for Chugg. Keep exporting backups for extra peace of mind.'
                  : 'This browser hasn’t granted persistent storage. Export a backup to protect your local progress.',
              );
            })
          }
        >
          Request persistent storage
        </button>
      </section>
      <div aria-live="polite" aria-atomic="true">
        {busy && <p className="device-dialog-small">Working…</p>}
        {message && <p className="device-dialog-notice">{message}</p>}
      </div>
      {error && (
        <p role="alert" className="device-dialog-error">
          {error}
        </p>
      )}
      <p className="device-dialog-small">
        <a
          className="device-dialog-help"
          href={`${import.meta.env.BASE_URL}credits.html`}
          target="_blank"
          rel="noreferrer"
        >
          Credits &amp; open-source licenses
        </a>
      </p>
    </DeviceDialog>
  );
}
