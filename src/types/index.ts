export type SessionState = 'WAITING' | 'WAITING_FOR_APPROVAL' | 'APPROVED' | 'TRANSFERRING' | 'VERIFYING' | 'COMPLETED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED' | 'FAILED' | 'PARTIALLY_COMPLETED';
export type FileState = 'waiting' | 'receiving' | 'verifying' | 'complete' | 'failed' | 'cancelled';
export interface TransferFile { id: string; name: string; saved_name: string | null; size: number; received: number; status: FileState; sha256: string | null }
export interface Snapshot { session_id: string; state: SessionState; url: string; qr_svg: string; address: string; expires_at: number; approval_expires_at: number | null; replaces_session_id: string | null; transport: 'internet' | 'lan'; trust_available: boolean; trusted_device_name: string | null; device: string | null; peer: string | null; files: TransferFile[]; error: string | null; destination: string }
export interface MobileStatus { state: SessionState; grant: string | null; files: TransferFile[]; error: string | null; paired_device_token?: string | null }
export interface TrustedDevice { id: string; name: string; created_at: number }
export interface Recent { name: string; size: number; sha256: string; destination: string; completed_at: number }
export interface NetworkInterface { name: string; ip: string; suggested: boolean }
export const terminal = (state: SessionState) => ['COMPLETED','REJECTED','EXPIRED','CANCELLED','FAILED','PARTIALLY_COMPLETED'].includes(state);
