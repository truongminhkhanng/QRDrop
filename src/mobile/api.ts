import type { MobileStatus, TransferFile } from '../types';
import { terminal } from '../types';
export class HttpError extends Error { constructor(message: string, public status: number) { super(message); } }
function message(data: unknown): string {
  return typeof data === 'object' && data !== null && 'message' in data && typeof data.message === 'string' ? data.message : 'Không thể xử lý yêu cầu. Hãy thử lại.';
}
async function request(path: string, token: string | null, body?: unknown, signal?: AbortSignal): Promise<Response> {
  let response: Response;
  try { response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', cache: 'no-store', signal,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body) }); }
  catch (cause) { if (signal?.aborted) throw cause; throw new HttpError('Không kết nối được với máy tính. Kiểm tra Wi-Fi và giữ QRDrop mở.', 0); }
  if (!response.ok) { const data: unknown = await response.json().catch(() => null); throw new HttpError(message(data), response.status); }
  return response;
}
export async function connect(token: string, requestId: string, files: File[], signal: AbortSignal): Promise<{ attempt_token: string; chunk_bytes: number }> {
  const ua = navigator.userAgent;
  const device = /iPhone|iPad/.test(ua) ? 'iPhone/iPad · Safari hoặc trình duyệt tương thích' : /Android/.test(ua) ? 'Android · Trình duyệt web' : 'Trình duyệt web';
  const response = await request('/api/connect', null, { token, request_id: requestId, device, files: files.map(file => ({ name: file.name, size: file.size })) }, signal);
  return response.json() as Promise<{ attempt_token: string; chunk_bytes: number }>;
}
export async function status(attempt: string, signal?: AbortSignal): Promise<MobileStatus> { return (await request('/api/status', attempt, undefined, signal)).json() as Promise<MobileStatus>; }
export async function finish(grant: string, file: TransferFile, digest: string, signal: AbortSignal) { await request(`/api/files/${file.id}/finish`, grant, { sha256: digest }, signal); }
export async function complete(grant: string, signal: AbortSignal) { await request('/api/complete', grant, {}, signal); }
export async function cancel(attempt: string) { await request('/api/cancel', attempt, {}); }
export function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(new DOMException('Đã hủy', 'AbortError')); return; }
    const onAbort = () => { clearTimeout(timer); reject(new DOMException('Đã hủy', 'AbortError')); };
    const timer = window.setTimeout(() => { signal.removeEventListener('abort', onAbort); resolve(); }, ms);
    signal.addEventListener('abort', onAbort, { once: true });
  });
}
export async function poll(attempt: string, signal: AbortSignal): Promise<MobileStatus> {
  for (let tries = 0; ; tries++) {
    try { return await status(attempt, signal); }
    catch (cause) {
      if (signal.aborted || (cause instanceof HttpError && cause.status >= 400 && cause.status < 500 && ![408,429].includes(cause.status)) || tries >= 8) throw cause;
      await sleep(Math.min(1000 * 2 ** tries, 15000), signal);
    }
  }
}
export function requireActive(current: MobileStatus) { if (terminal(current.state) && current.state !== 'COMPLETED') throw new Error(current.error ?? (current.state === 'REJECTED' ? 'Máy tính đã từ chối yêu cầu. Quét mã QR mới để thử lại.' : 'Phiên đã kết thúc. Quét mã QR mới để thử lại.')); }
export function upload(grant: string, file: TransferFile, offset: number, blob: Blob, digest: string, signal: AbortSignal, progress: (sent: number) => void): Promise<number> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    const cleanup = () => signal.removeEventListener('abort', abort);
    xhr.open('PUT', `/api/files/${file.id}/chunks`);
    xhr.timeout = 90000;
    xhr.setRequestHeader('Authorization', `Bearer ${grant}`);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.setRequestHeader('X-QRDrop-Offset', String(offset));
    xhr.setRequestHeader('X-QRDrop-Length', String(blob.size));
    xhr.setRequestHeader('X-QRDrop-SHA256', digest);
    xhr.upload.onprogress = event => progress(event.loaded);
    xhr.onload = () => { cleanup(); try { const data: unknown = JSON.parse(xhr.responseText); if (xhr.status < 200 || xhr.status >= 300) { reject(new HttpError(message(data), xhr.status)); return; } if (typeof data === 'object' && data && 'offset' in data && typeof data.offset === 'number') resolve(data.offset); else reject(new Error('Phản hồi không hợp lệ.')); } catch { reject(new Error('Không đọc được phản hồi từ máy tính.')); } };
    xhr.onerror = () => { cleanup(); reject(new HttpError('Mất kết nối với máy tính.', 0)); };
    xhr.ontimeout = () => { cleanup(); reject(new HttpError('Kết nối quá chậm hoặc bị gián đoạn.', 408)); };
    xhr.onabort = () => { cleanup(); reject(new DOMException('Đã hủy', 'AbortError')); };
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) { cleanup(); reject(new DOMException('Đã hủy', 'AbortError')); return; }
    xhr.send(blob);
  });
}
export function requestId(): string {
  const data = crypto.getRandomValues(new Uint8Array(16)); data[6] = (data[6] & 15) | 64; data[8] = (data[8] & 63) | 128;
  const hex = [...data].map(n => n.toString(16).padStart(2,'0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
