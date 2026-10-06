import type { FileState, SessionState } from '../types';
export function bytes(value: number): string {
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']; let n = value; let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toLocaleString('vi-VN', { maximumFractionDigits: i ? 2 : 0 })} ${units[i]}`;
}
export const fileLabels: Record<FileState, string> = { waiting: 'Đang chờ', receiving: 'Đang nhận', verifying: 'Đang kiểm tra', complete: 'Hoàn tất · SHA-256 khớp', failed: 'Thất bại', cancelled: 'Đã hủy' };
export const sessionLabels: Record<SessionState, string> = { WAITING: 'Sẵn sàng nhận tệp', WAITING_FOR_APPROVAL: 'Có yêu cầu gửi tệp', APPROVED: 'Đã cho phép · Chờ điện thoại', TRANSFERRING: 'Đang nhận tệp', VERIFYING: 'Đang kiểm tra', COMPLETED: 'Đã nhận tất cả tệp', REJECTED: 'Đã từ chối', EXPIRED: 'Phiên đã hết hạn', CANCELLED: 'Đã hủy phiên', FAILED: 'Không thể hoàn tất', PARTIALLY_COMPLETED: 'Đã nhận một phần' };
