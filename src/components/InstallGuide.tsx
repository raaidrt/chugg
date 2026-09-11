import { useState } from 'react';
import { Smartphone, Share, EllipsisVertical, ArrowUpRight } from 'lucide-react';
import { DeviceDialog } from './DeviceDialog';

export function isStandalone(): boolean {
  return (
    typeof window !== 'undefined' &&
    (window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true)
  );
}

export function InstallGuide({ onClose }: { onClose: () => void }) {
  const [platform, setPlatform] = useState<'iphone' | 'android'>(() =>
    /Android/i.test(navigator.userAgent) ? 'android' : 'iphone',
  );
  return (
    <DeviceDialog title="Install Chugg" id="install-title" onClose={onClose}>
      <div className="device-dialog-icon">
        <Smartphone size={28} />
      </div>
      <p>Add Chugg to your home screen.</p>
      {isStandalone() ? (
        <p className="device-dialog-notice">You’re already using Chugg as an app.</p>
      ) : (
        <>
          <div className="device-dialog-switch" aria-label="Phone type">
            <button aria-pressed={platform === 'iphone'} onClick={() => setPlatform('iphone')}>
              iPhone · Safari
            </button>
            <button aria-pressed={platform === 'android'} onClick={() => setPlatform('android')}>
              Android · Chrome
            </button>
          </div>
          {platform === 'iphone' ? (
            <ol className="device-dialog-steps">
              <li>
                <span>1</span>
                <div>
                  Open Chugg in <strong>Safari</strong>.
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  Tap <Share size={16} aria-hidden="true" /> <strong>Share</strong>. Depending on
                  your layout, open <strong>More (…)</strong> first.
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  Scroll to <strong>Add to Home Screen</strong>. If it’s missing, find it under Edit
                  Actions.
                </div>
              </li>
              <li>
                <span>4</span>
                <div>
                  Enable <strong>Open as Web App</strong> if shown, then tap <strong>Add</strong>.
                </div>
              </li>
            </ol>
          ) : (
            <ol className="device-dialog-steps">
              <li>
                <span>1</span>
                <div>
                  Open Chugg in <strong>Chrome</strong>.
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  Tap <EllipsisVertical size={16} aria-hidden="true" /> <strong>More</strong> next
                  to the address bar.
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  Choose <strong>Install and create shortcut</strong>, then <strong>Install</strong>
                  . Some versions show Install app or Add to Home screen.
                </div>
              </li>
              <li>
                <span>4</span>
                <div>Follow the prompts, then launch Chugg from your home screen.</div>
              </li>
            </ol>
          )}
          <a
            className="device-dialog-help"
            href={
              platform === 'iphone'
                ? 'https://support.apple.com/guide/iphone/open-as-web-app-iphea86e5236/ios'
                : 'https://support.google.com/chrome/answer/9658361?co=GENIE.Platform%3DAndroid&hl=en-GB'
            }
            target="_blank"
            rel="noreferrer"
          >
            {platform === 'iphone' ? 'Apple’s installation guide' : 'Google’s installation guide'}{' '}
            <ArrowUpRight size={14} />
          </a>
        </>
      )}
      <p className="device-dialog-small">
        Wait for “Ready for offline practice” before disconnecting. Your progress stays in this
        device’s browser or installed app; export a backup to move it elsewhere.
      </p>
    </DeviceDialog>
  );
}
