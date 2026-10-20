/**
 * Hàm bọc apiFetch dùng chung cho toàn bộ Frontend:
 * - Tự động đọc access_token từ localStorage và gắn vào header Authorization: Bearer <token>.
 * - TUYỆT ĐỐI XÓA BỎ cơ chế fallback sang dữ liệu giả khi API lỗi.
 * - Ném lỗi rõ ràng kèm mã HTTP và detail từ máy chủ để UI hiển thị.
 */
export async function apiFetch(url, options = {}) {
  const opts = { ...options };
  opts.headers = { ...(opts.headers || {}) };

  const token = localStorage.getItem('app_access_token');
  if (token && !opts.headers['Authorization']) {
    opts.headers['Authorization'] = `Bearer ${token}`;
  }
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
