/**
 * Hàm bọc apiFetch dùng chung cho toàn bộ Frontend:
 * - Sử dụng Cookie phiên HttpOnly (credentials: 'include'), không lưu token trong localStorage.
 * - Ném lỗi rõ ràng kèm mã HTTP và detail từ máy chủ để UI hiển thị.
 */
export async function apiFetch(url, options = {}) {
  const opts = { ...options };
  opts.headers = { ...(opts.headers || {}) };

  // Đảm bảo cookie phiên HttpOnly luôn được gửi kèm mọi request
  opts.credentials = opts.credentials || 'include';

  if (!opts.headers['Content-Type'] && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
  }


  let res;
  try {
    res = await fetch(url, opts);
  } catch (networkError) {
    const err = new Error(`Lỗi kết nối mạng tới máy chủ: ${networkError.message}`);
    err.status = 0;
    err.detail = networkError.message;
    throw err;
  }

  if (!res.ok) {
    let errorMsg = `Lỗi máy chủ (${res.status}: ${res.statusText})`;
    try {
      const errJson = await res.json();
      errorMsg = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch (e) {
      // Giữ nguyên statusText
    }

    const err = new Error(errorMsg);
    err.status = res.status;
    err.detail = errorMsg;
    throw err;
  }

  return res;
}

export default apiFetch;
