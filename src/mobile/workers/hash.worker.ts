import { Sha256 } from '../../utils/sha256.mjs';
interface HashRequest { id: number; operation: 'reset' | 'chunk' | 'finish'; blob?: Blob }
let fileHash = new Sha256();
self.onmessage = async (event: MessageEvent<HashRequest>) => {
  const request = event.data;
  try {
    if (request.operation === 'reset') { fileHash = new Sha256(); self.postMessage({ id: request.id, digest: '' }); }
    else if (request.operation === 'chunk' && request.blob) {
      const data = new Uint8Array(await request.blob.arrayBuffer());
      fileHash.update(data);
      self.postMessage({ id: request.id, digest: new Sha256().update(data).digest() });
    } else if (request.operation === 'finish') self.postMessage({ id: request.id, digest: fileHash.digest() });
    else throw new Error('Yêu cầu hash không hợp lệ.');
  } catch (cause) { self.postMessage({ id: request.id, error: String(cause) }); }
};
