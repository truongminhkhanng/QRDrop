use axum::{http::StatusCode, response::{IntoResponse, Response}, Json};
use serde::Serialize;

#[derive(Debug)]
pub struct AppError {
    pub status: StatusCode,
    pub code: &'static str,
    pub message: String,
}
impl AppError {
    pub fn new(status: StatusCode, code: &'static str, message: impl Into<String>) -> Self {
        Self { status, code, message: message.into() }
    }
    pub fn invalid(message: impl Into<String>) -> Self { Self::new(StatusCode::BAD_REQUEST, "invalid_request", message) }
    pub fn denied() -> Self { Self::new(StatusCode::FORBIDDEN, "not_authorized", "Phiên chưa được cho phép hoặc quyền truy cập đã hết hạn.") }
    pub fn conflict(message: impl Into<String>) -> Self { Self::new(StatusCode::CONFLICT, "conflict", message) }
    pub fn io(error: std::io::Error) -> Self {
        let message = match error.kind() {
            std::io::ErrorKind::PermissionDenied => "QRDrop không có quyền truy cập thư mục. Hãy chọn thư mục khác hoặc kiểm tra quyền truy cập.",
            std::io::ErrorKind::NotFound => "Không tìm thấy tệp hoặc thư mục cần dùng. Kiểm tra ổ đĩa và chọn lại thư mục nhận.",
            _ => "Không thể đọc hoặc ghi dữ liệu. Kiểm tra dung lượng trống, kết nối ổ đĩa và quyền truy cập thư mục.",
        };
        Self::new(StatusCode::INSUFFICIENT_STORAGE, "storage_error", message)
    }
}
impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result { write!(f, "{}", self.message) }
}
impl std::error::Error for AppError {}
impl From<std::io::Error> for AppError { fn from(e: std::io::Error) -> Self { Self::io(e) } }
impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        #[derive(Serialize)] struct ErrorBody { code: &'static str, message: String }
        (self.status, Json(ErrorBody { code: self.code, message: self.message })).into_response()
    }
}
pub type Result<T> = std::result::Result<T, AppError>;
