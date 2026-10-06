use crate::errors::{AppError, Result};
use subtle::ConstantTimeEq;

pub fn random_token() -> Result<String> {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).map_err(|_| AppError::new(axum::http::StatusCode::INTERNAL_SERVER_ERROR, "random_failed", "Không thể tạo mã kết nối an toàn."))?;
    Ok(hex::encode(bytes))
}
pub fn matches(expected: &str, supplied: &str) -> bool {
    expected.len() == supplied.len() && bool::from(expected.as_bytes().ct_eq(supplied.as_bytes()))
}
pub fn valid_digest(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|c| c.is_ascii_hexdigit())
}
