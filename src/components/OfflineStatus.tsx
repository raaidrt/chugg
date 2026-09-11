import { useEffect, useState } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';

export function OfflineStatus({ allowUpdate = true }: { allowUpdate?: boolean }) {
  const [online, setOnline] = useState(navigator.onLine);
  const [registrationError, setRegistrationError] = useState(false);
  const [previouslyReady, setPreviouslyReady] = useState(false);
  const {
    offlineReady: [offlineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisterError() {
      setRegistrationError(true);
    },
    onRegisteredSW(_url, registration) {
      if (registration?.active) setPreviouslyReady(true);
    },
  });

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  return (
    <div
      className="offline-status"
      role="status"
      style={{ fontSize: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}
    >
      <span>
        {registrationError || !('serviceWorker' in navigator)
          ? 'Offline setup unavailable — try reloading online'
          : !online
            ? 'You’re offline'
            : offlineReady || previouslyReady
              ? 'Ready for offline practice'
              : import.meta.env.DEV
                ? 'Development preview'
                : 'Preparing offline practice…'}
      </span>
      {needRefresh && allowUpdate && (
        <button
          type="button"
          className="text-button"
          onClick={() => void updateServiceWorker(true).catch(() => setRegistrationError(true))}
        >
          Update Chugg
        </button>
      )}
      {needRefresh && !allowUpdate && <span>Update ready after your drill</span>}
    </div>
  );
}

export default OfflineStatus;
