import { useEffect, useRef, useState } from 'react';
import { invoke, isTauri } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { getCurrentWindow } from '@tauri-apps/api/window';
import type { NetworkInterface, Recent, Snapshot } from '../types';
import { terminal } from '../types';
import { bytes, fileLabels, sessionLabels } from '../utils/format';

export function App() {
  const [session, setSession] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [recent, setRecent] = useState<Recent[]>([]);
  const [settings, setSettings] = useState(false);
  const [destination, setDestination] = useState('');
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [ip, setIp] = useState('');
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const activeSession = useRef<string | null>(null);
  const pendingConfirmation = useRef<{promise: Promise<boolean>; resolve: (answer: boolean) => void} | null>(null);
  function ask(message: string): Promise<boolean> {
    if (pendingConfirmation.current) return pendingConfirmation.current.promise;
    let resolve!: (answer: boolean) => void;
    const promise = new Promise<boolean>(done => { resolve = done; });
    pendingConfirmation.current = { promise, resolve }; setConfirmation(message);
    return promise;
  }
  function respond(answer: boolean) {
    const pending = pendingConfirmation.current; pendingConfirmation.current = null;
    setConfirmation(null); pending?.resolve(answer);
  }
  async function perform(action: () => Promise<void>) {
    setBusy(true); setError('');
    try { await action(); } catch (cause) { setError(typeof cause === 'string' ? cause : 'Không thể thực hiện thao tác. Hãy thử lại hoặc mở lại QRDrop.'); } finally { setBusy(false); }
  }
  function showSession(snapshot: Snapshot | null) {
    activeSession.current = snapshot?.session_id ?? null;
    setSession(snapshot);
  }
  async function stopReceiving() {
    activeSession.current = null;
    try {
      await invoke('stop_receiving');
      showSession(null);
    } catch (cause) {
      showSession(await invoke<Snapshot | null>('session_snapshot').catch(() => null));
      throw cause;
    }
    setRecent(await invoke<Recent[]>('recent_transfers'));
  }
  async function toggleReceiving() {
    await perform(async () => {
      if (session && !terminal(session.state)) {
        if (session.state !== 'WAITING' && !await ask('Tắt nhận tệp? Tệp đã lưu được giữ lại, tệp chưa hoàn tất sẽ bị hủy.')) return;
        await stopReceiving();
      } else {
        showSession(await invoke<Snapshot>('create_session', { ip: ip || null }));
      }
    });
  }
  async function refresh() {
    await perform(async () => {
      if (!session || terminal(session.state)) return;
      if (session.state !== 'WAITING' && !await ask('Tạo mã QR mới? Yêu cầu hiện tại sẽ kết thúc. Tệp đã lưu được giữ lại.')) return;
      await stopReceiving();
      showSession(await invoke<Snapshot>('create_session', { ip: ip || null }));
    });
  }
  useEffect(() => {
    if (!isTauri()) { setError('Mở QRDrop bằng ứng dụng trên máy tính để nhận tệp. Trang web này không có quyền truy cập máy tính.'); return; }
    let disposed = false;
    const subscriptions: (() => void)[] = [];
    void (async () => {
      try {
        const unlisten = await listen<Snapshot>('qrdrop:session', event => { if (!disposed && activeSession.current === event.payload.session_id) setSession(event.payload); });
        if (disposed) unlisten(); else subscriptions.push(unlisten);
        const unclose = await getCurrentWindow().onCloseRequested(async event => {
          const active = await invoke<Snapshot | null>('session_snapshot');
          if (active && !terminal(active.state) && active.state !== 'WAITING') {
            event.preventDefault();
            await perform(async () => { if (await ask('Tệp chưa hoàn tất sẽ bị hủy. Bạn muốn đóng QRDrop?')) { await invoke('stop_receiving'); await getCurrentWindow().destroy(); } });
          }
        });
        if (disposed) unclose(); else subscriptions.push(unclose);
        const [config, networks, history] = await Promise.all([invoke<{destination: string}>('get_settings'), invoke<NetworkInterface[]>('network_interfaces'), invoke<Recent[]>('recent_transfers')]);
        if (disposed) return;
        setDestination(config.destination); setInterfaces(networks); setRecent(history);
        const current = await invoke<Snapshot | null>('session_snapshot');
        if (!disposed) showSession(current);
      } catch (cause) { if (!disposed) setError(typeof cause === 'string' ? cause : 'Không thể thực hiện thao tác. Hãy thử lại hoặc mở lại QRDrop.'); }
    })();
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => { disposed = true; subscriptions.forEach(unsubscribe => unsubscribe()); clearInterval(timer); pendingConfirmation.current?.resolve(false); pendingConfirmation.current = null; };
  }, []);
  useEffect(() => { if (session && terminal(session.state) && isTauri()) void invoke<Recent[]>('recent_transfers').then(setRecent).catch(cause => setError(typeof cause === 'string' ? cause : 'Không thể thực hiện thao tác. Hãy thử lại hoặc mở lại QRDrop.')); }, [session?.state]);
  const total = session?.files.reduce((sum, file) => sum + file.size, 0) ?? 0;
  const received = session?.files.reduce((sum, file) => sum + file.received, 0) ?? 0;
  const seconds = session ? Math.max(0, session.expires_at - Math.floor(now / 1000)) : 0;
  const receiving = session !== null && !terminal(session.state);
  return <main className="desktop-shell">
    <header className="brand"><span className="brand-mark">Q</span><div><h1>QRDrop</h1><p>Tệp của bạn. Đi thẳng đến máy tính.</p></div><span className="local-badge">Mạng nội bộ</span></header>
    <section className="receive-area" aria-live="polite">
      <h2>{session ? sessionLabels[session.state] : 'Đang tắt nhận tệp'}</h2>
      {session?.url && session.state === 'WAITING' ? <>
        <img className="qr" alt="Mã QR kết nối điện thoại với QRDrop" src={`data:image/svg+xml;base64,${btoa(session.qr_svg)}`} />
        <p>Quét mã bằng camera điện thoại</p><p className="muted">Mã có hiệu lực {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</p>
      </> : session?.state === 'COMPLETED' ? <div className="success-mark" aria-hidden="true">✓</div> : !session?.files.length ? <div className="empty-symbol" aria-hidden="true">↗</div> : null}
      {session && <p className="address">{session.address}</p>}
      {!session && <p className="muted">Bật nhận tệp để tạo mã QR kết nối điện thoại.</p>}
      <p className="destination">Lưu vào: {(session?.destination ?? destination) || 'Chưa chọn thư mục'}</p>
    </section>
    {(error || session?.error) && <p className="error" role="alert">{error || session?.error}</p>}
    {session && session.files.length > 0 && <section className="transfers">
      <div className="section-title"><h2>Tệp trong phiên</h2><span>{bytes(received)} / {bytes(total)}</span></div>
      <progress max={Math.max(total, 1)} value={received} />
      <ul className="file-list">{session.files.map(file => <li key={file.id}><div><strong>{file.saved_name ?? file.name}</strong><small>{bytes(file.received)} / {bytes(file.size)} · {fileLabels[file.status]}</small></div><span>{file.size ? Math.floor(file.received / file.size * 100) : file.status === 'complete' ? 100 : 0}%</span></li>)}</ul>
      {!terminal(session.state) && <button className="text-button danger" disabled={busy} onClick={() => void perform(async () => { if (await ask('Hủy phiên nhận tệp hiện tại?')) await invoke('cancel_session'); })}>Hủy nhận tệp</button>}
    </section>}
    {!session?.files.length && <section className="transfers"><h2>Đã nhận gần đây</h2>{recent.length ? <ul className="file-list">{recent.slice(0,5).map((item, i) => <li key={`${item.completed_at}-${i}`}><div><strong>{item.name}</strong><small>{bytes(item.size)} · SHA-256 khớp</small></div><span className="complete-tick">✓</span></li>)}</ul> : <p className="muted">Tệp nhận thành công sẽ xuất hiện ở đây.</p>}</section>}
    <p className="network-note">Kết nối HTTP không mã hóa. Chỉ dùng trên mạng bạn tin cậy.</p>
    <footer><button className={receiving ? 'danger' : 'primary'} aria-pressed={receiving} disabled={busy || !isTauri()} onClick={() => void toggleReceiving()}>{receiving ? 'Tắt nhận tệp' : 'Bật nhận tệp'}</button><button disabled={busy || !isTauri() || !receiving} onClick={() => void refresh()}>Làm mới QR</button><button disabled={busy || !isTauri()} onClick={() => void perform(async () => { await invoke('open_destination'); })}>Mở thư mục</button><button disabled={busy || !isTauri()} onClick={() => setSettings(true)}>Cài đặt</button></footer>
    {session?.state === 'WAITING_FOR_APPROVAL' && <div className="dialog-backdrop"><section className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="approval-title"><p className="eyebrow">Yêu cầu gửi tệp</p><h2 id="approval-title">Cho phép nhận các tệp này?</h2><p>{session.device}</p><p className="muted">Địa chỉ: {session.peer}</p><p className="approval-total">{session.files.length} tệp · {bytes(total)}</p><details><summary>Xem danh sách tệp</summary><ul className="approval-files">{session.files.map(file => <li key={file.id}>{file.name} · {bytes(file.size)}</li>)}</ul></details><p className="destination">Thư mục: {session.destination}</p><div className="dialog-actions"><button disabled={busy} onClick={() => void perform(async () => { await invoke('decide_transfer', { sessionId: session.session_id, accept: false }); })}>Từ chối</button><button className="primary" disabled={busy} onClick={() => void perform(async () => { await invoke('decide_transfer', { sessionId: session.session_id, accept: true }); })}>Cho phép</button></div></section></div>}
    {settings && <div className="dialog-backdrop"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title"><h2 id="settings-title">Cài đặt</h2><label>Thư mục nhận</label><p className="destination">{destination}</p><button disabled={busy} onClick={() => void perform(async () => { const chosen = await invoke<string | null>('choose_destination'); if (chosen) setDestination(chosen); })}>Chọn thư mục</button><p className="muted">Áp dụng cho phiên nhận tiếp theo.</p><label htmlFor="network">Kết nối mạng</label><select id="network" value={ip} onChange={event => setIp(event.target.value)}><option value="">Tự động chọn</option>{interfaces.map(item => <option key={item.ip} value={item.ip}>{item.name} · {item.ip}</option>)}</select><button className="text-button" onClick={() => void perform(async () => { setInterfaces(await invoke('network_interfaces')); })}>Kiểm tra lại mạng</button><p className="muted">Thay đổi mạng áp dụng khi tạo mã QR mới.</p><div className="dialog-actions"><button className="primary" onClick={() => setSettings(false)}>Xong</button></div></section></div>}
    {confirmation && <div className="dialog-backdrop"><section className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirmation-title"><h2 id="confirmation-title">Xác nhận</h2><p>{confirmation}</p><div className="dialog-actions"><button onClick={() => respond(false)}>Quay lại</button><button className="primary" onClick={() => respond(true)}>Tiếp tục</button></div></section></div>}
  </main>;
}
