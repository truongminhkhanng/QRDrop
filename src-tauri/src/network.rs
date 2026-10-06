use crate::errors::{AppError, Result};
use serde::Serialize;
use std::net::Ipv4Addr;

#[derive(Clone, Serialize)]
pub struct NetworkInterface { pub name: String, pub ip: Ipv4Addr, pub suggested: bool }
pub fn interfaces() -> Result<Vec<NetworkInterface>> {
    let mut result: Vec<_> = if_addrs::get_if_addrs()?.into_iter().filter_map(|interface| {
        if let if_addrs::IfAddr::V4(addr) = interface.addr {
            if addr.ip.is_private() && !addr.ip.is_loopback() {
                let virtual_name = ["docker", "veth", "virbr", "vmnet", "utun", "tun", "tap"].iter().any(|prefix| interface.name.starts_with(prefix));
                return Some(NetworkInterface { name: interface.name, ip: addr.ip, suggested: !virtual_name });
            }
        }
        None
    }).collect();
    result.sort_by_key(|i| (!i.suggested, i.name.clone(), i.ip));
    result.dedup_by_key(|i| i.ip);
    Ok(result)
}
pub fn choose(requested: Option<Ipv4Addr>) -> Result<Ipv4Addr> {
    let candidates = interfaces()?;
    if let Some(ip) = requested {
        if candidates.iter().any(|i| i.ip == ip) { return Ok(ip); }
        return Err(AppError::invalid("Địa chỉ mạng đã chọn không còn khả dụng."));
    }
    candidates.first().map(|i| i.ip).ok_or_else(|| AppError::invalid("Không tìm thấy mạng nội bộ. Kết nối điện thoại và máy tính vào cùng mạng, rồi thử lại."))
}
