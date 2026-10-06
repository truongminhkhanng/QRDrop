import { useEffect, useRef, useState } from 'react';
import type { MobileStatus } from '../types';
import { terminal } from '../types';
import { bytes, fileLabels } from '../utils/format';
import * as api from './api';

class HashWorker {
  private worker = new Worker(new URL('./workers/hash.worker.ts', import.meta.url), { type: 'module' });
  private sequence = 0;
  private pending = new Map<number, { resolve: (hash: string) => void; reject: (error: Error) => void }>();
  constructor() {
    this.worker.onmessage = (event: MessageEvent<{id:number;digest?:string;error?:string}>) => { const request = this.pending.get(event.data.id); if (!request) return; this.pending.delete(event.data.id); if (event.data.error) request.reject(new Error(event.data.error)); else request.resolve(event.data.digest ?? ''); };
    this.worker.onerror = () => this.close();
  }
  call(operation: 'reset' | 'chunk' | 'finish', blob?: Blob): Promise<string> { const id = ++this.sequence; return new Promise((resolve, reject) => { this.pending.set(id, {resolve,reject}); this.worker.postMessage({id,operation,blob}); }); }
  close() { this.worker.terminate(); for (const pending of this.pending.values()) pending.reject(new Error('Đã dừng kiểm tra tệp.')); this.pending.clear(); }
}
const tokenFromUrl = new URLSearchParams(location.hash.slice(1)).get('t') ?? '';
history.replaceState(null, '', location.pathname);

export function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [current, setCurrent] = useState<MobileStatus | null>(null);
  const [phase, setPhase] = useState('Chọn tệp để gửi đến máy tính');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<{id:string; bytes:number} | null>(null);
  const operation = useRef<AbortController | null>(null);
  const attempt = useRef<string | null>(null);
  const worker = useRef<HashWorker | null>(null);
  useEffect(() => () => { operation.current?.abort(); worker.current?.close(); }, []);
  async function send() {
    if (!tokenFromUrl || files.length === 0 || busy) return;
    const controller = new AbortController(); operation.current = controller;
    const signal = controller.signal;
    setBusy(true); setError('');
    let hash: HashWorker | null = null;
    try {
      hash = new HashWorker(); worker.current = hash;
      setPhase('Đang yêu cầu máy tính cho phép…');
      const id = api.requestId();
      let connection: Awaited<ReturnType<typeof api.connect>> | null = null;
      for (let tries = 0; !connection; tries++) {
        try { connection = await api.connect(tokenFromUrl, id, files, signal); }
        catch (cause) { if (signal.aborted || tries >= 2 || (cause instanceof api.HttpError && cause.status >= 400 && cause.status < 500)) throw cause; await api.sleep(1000 * (tries+1), signal); }
      }
      attempt.current = connection.attempt_token;
      setPhase('Đang chờ máy tính cho phép…');
      let state = await api.poll(connection.attempt_token, signal); setCurrent(state);
      while (!state.grant) {
        api.requireActive(state);
        await api.sleep(1000, signal);
        state = await api.poll(connection.attempt_token, signal); setCurrent(state);
      }
      const grant = state.grant;
      if (state.files.length !== files.length) throw new Error('Danh sách tệp không khớp. Quét mã QR mới.');
      for (const [index, file] of files.entries()) {
        const target = state.files[index];
        await hash.call('reset');
        let offset = 0;
        while (offset < file.size) {
          setPhase(`Đang gửi ${file.name}`);
          const blob = file.slice(offset, Math.min(offset + connection.chunk_bytes, file.size));
          const digest = await hash.call('chunk', blob);
          let acknowledged = false;
          for (let tries = 0; !acknowledged; tries++) {
            try {
              const next = await api.upload(grant, target, offset, blob, digest, signal, count => setSent({id:target.id,bytes:offset+count}));
              if (next !== offset + blob.size) throw new Error('Tiến trình gửi và nhận chưa khớp. Hãy thử gửi lại tệp.');
              acknowledged = true;
            } catch (cause) {
              if (signal.aborted || tries >= 8 || (cause instanceof api.HttpError && cause.status >= 400 && cause.status < 500 && ![408,409,429].includes(cause.status))) throw cause;
              setPhase('Kết nối gián đoạn · Đang thử lại…'); setSent(null);
              await api.sleep(Math.min(1000 * 2 ** tries, 15000), signal);
              const checkpoint = await api.poll(connection.attempt_token, signal); api.requireActive(checkpoint); setCurrent(checkpoint);
              // Server offset is authoritative only at ACK boundaries; retries remain idempotent.
            }
          }
          offset += blob.size;
          state = await api.poll(connection.attempt_token, signal); api.requireActive(state); setCurrent(state); setSent(null);
        }
        setPhase(`Đang kiểm tra ${file.name}`);
        const digest = await hash.call('finish');
        for (let tries = 0; ; tries++) {
          try { await api.finish(grant, target, digest, signal); break; }
          catch (cause) { if (signal.aborted || tries >= 5 || (cause instanceof api.HttpError && cause.status >= 400 && cause.status < 500 && ![408,409,429].includes(cause.status))) throw cause; await api.sleep(1000 * (tries+1), signal); }
        }
        do { await api.sleep(600, signal); state = await api.poll(connection.attempt_token, signal); api.requireActive(state); setCurrent(state); } while (state.files[index].status !== 'complete');
      }
      setPhase('Đang hoàn tất phiên gửi…');
      for (let tries = 0; ; tries++) {
        try { await api.complete(grant, signal); break; }
        catch (cause) {
          if (signal.aborted) throw cause;
          const receipt = await api.poll(connection.attempt_token, signal); setCurrent(receipt);
          if (receipt.state === 'COMPLETED') break;
          api.requireActive(receipt);
          if (tries >= 8 || (cause instanceof api.HttpError && cause.status >= 400 && cause.status < 500 && ![408,409,429].includes(cause.status))) throw cause;
          await api.sleep(Math.min(500 * 2 ** tries, 5000), signal);
        }
      }
      setCurrent(await api.poll(connection.attempt_token, signal)); setPhase('Đã gửi tất cả tệp · SHA-256 khớp');
    } catch (cause) {
      setError(signal.aborted ? 'Đã hủy gửi tệp.' : cause instanceof Error && !(cause instanceof DOMException || cause instanceof TypeError || cause instanceof RangeError || cause instanceof SyntaxError) ? cause.message : 'Không đọc hoặc gửi được tệp. Kiểm tra quyền truy cập tệp và quét mã QR mới để thử lại.');
      setPhase('Không thể hoàn tất');
      if (attempt.current && !signal.aborted) {
        try { const snapshot = await api.status(attempt.current); setCurrent(snapshot); if (!terminal(snapshot.state)) { await api.cancel(attempt.current); setCurrent(await api.status(attempt.current)); } } catch { /* Connection error is already displayed; server expires and cleans up. */ }
      }
    } finally { setBusy(false); setSent(null); hash?.close(); worker.current = null; }
  }
  async function cancel() {
    operation.current?.abort(); worker.current?.close();
    if (attempt.current) { try { await api.cancel(attempt.current); } catch { setError('Đã dừng gửi nhưng chưa kết nối được với máy tính để hủy phiên. QRDrop sẽ dọn tệp tạm khi phiên hết hạn.'); } }
  }
  const total = files.reduce((sum, file) => sum + file.size, 0);
  const received = current?.files.reduce((sum, file) => sum + file.received, 0) ?? 0;
  const used = current !== null;
  return <main className="mobile-shell">
    <header className="brand"><span className="brand-mark">Q</span><div><h1>QRDrop</h1><p>Gửi tệp đến máy tính</p></div></header>
    <h2 className="mobile-heading">{phase}</h2>
    <p className="muted">Chỉ gửi sau khi bạn cho phép trên máy tính.</p>
    {!tokenFromUrl && <p className="error" role="alert">Liên kết không có mã kết nối. Quét mã QR mới trên máy tính.</p>}
    {!used && <>
      <label className={`file-picker ${busy ? 'disabled' : ''}`}>Chọn tệp<input aria-label="Chọn tệp để gửi" type="file" multiple disabled={busy || !tokenFromUrl} onChange={event => setFiles(Array.from(event.target.files ?? []))} /></label>
      <p className="selection-summary">{files.length ? `${files.length} tệp · ${bytes(total)}` : 'Ảnh, video, tài liệu và các loại tệp khác'}</p>
      <button className="primary full-width" disabled={!files.length || busy || !tokenFromUrl} onClick={() => void send()}>Yêu cầu gửi tệp</button>
    </>}
    {current && <section className="transfers"><p>{current.files.filter(file => file.status === 'complete').length} / {current.files.length} tệp · {bytes(received)} / {bytes(total)}</p><progress max={Math.max(total, 1)} value={received} /><ul className="file-list">{current.files.map(file => <li key={file.id}><div><strong>{file.saved_name ?? file.name}</strong><small>{bytes(file.size)} · {fileLabels[file.status]}</small><progress max={Math.max(file.size,1)} value={sent?.id === file.id ? sent.bytes : file.received} /></div></li>)}</ul></section>}
    {busy && <button className="text-button danger" onClick={() => void cancel()}>Hủy gửi</button>}
    {(error || current?.error) && <p className="error" role="alert">{error || current?.error}</p>}
    {current && terminal(current.state) && current.state !== 'COMPLETED' && <p>Để gửi lại, tạo mã QR mới trên máy tính.</p>}
    <aside className="mobile-advice"><p>Giữ trang này mở và màn hình hoạt động trong lúc gửi.</p><p>QRDrop giữ nguyên dữ liệu tệp mà trình duyệt cung cấp. Tệp từ Photos có thể khác tài nguyên gốc.</p><p>Kết nối HTTP không mã hóa. Chỉ dùng trên mạng bạn tin cậy.</p></aside>
  </main>;
}
