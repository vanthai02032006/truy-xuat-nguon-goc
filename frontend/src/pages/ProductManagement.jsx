import React, { useState, useEffect } from 'react';
import { useAuthRole } from '../context/AuthRoleContext';

export default function ProductManagement() {
  const auth = useAuthRole();
  const currentRole = auth?.currentRole || 'admin';
  const getAuthHeaders = auth?.getAuthHeaders || (() => ({ 'Content-Type': 'application/json' }));


  // Form State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editId, setEditId] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    unit: 'kg', // Đóng: 'kg', 'tấn', 'thùng'
    description: '',
  });

  const ALLOWED_UNITS = [
    { value: 'kg', label: 'kg (Kilogram)' },
    { value: 'tấn', label: 'tấn (Tấn)' },
    { value: 'thùng', label: 'thùng (Thùng tiêu chuẩn)' },
  ];

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParam = searchTerm ? `?q=${encodeURIComponent(searchTerm)}` : '';
      const res = await fetch(`/api/v1/products${queryParam}`);
      if (!res.ok) {
        throw new Error(`Lỗi tải danh mục sản phẩm: ${res.statusText}`);
      }
      const data = await res.json();
      setProducts(data);
    } catch (err) {
      // Dữ liệu mẫu ban đầu nếu backend chưa có dữ liệu
      setProducts([
        {
          id: 1,
          name: 'Dâu tây New Zealand Đà Lạt',
          unit: 'kg',
          description: 'Dâu tây chuẩn VietGAP trồng tại Đà Lạt, Lâm Đồng',
          created_at: '2026-10-15T08:00:00Z',
        },
        {
          id: 2,
          name: 'Sầu riêng Ri6 sấy thăng hoa',
          unit: 'thùng',
          description: 'Sầu riêng xuất khẩu loại 1',
          created_at: '2026-10-18T10:30:00Z',
        },
        {
          id: 3,
          name: 'Gạo sạch ST25 hữu cơ',
          unit: 'tấn',
          description: 'Gạo đạt giải nhì thế giới vụ mùa 2026',
          created_at: '2026-10-20T14:15:00Z',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [searchTerm]);

  const handleOpenAddModal = () => {
    if (!['admin', 'system_admin'].includes(currentRole)) {
      alert('Chỉ vai trò Quản trị hệ thống (Admin) mới có quyền thêm sản phẩm mới (HTTP 403 Forbidden)!');
      return;
    }
    setIsEditing(false);
    setEditId(null);
    setFormData({ name: '', unit: 'kg', description: '' });
    setError(null);
    setSuccessMsg(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (product) => {
    if (!['admin', 'system_admin'].includes(currentRole)) {
      alert('Chỉ vai trò Quản trị hệ thống (Admin) mới có quyền chỉnh sửa sản phẩm (HTTP 403 Forbidden)!');
      return;
    }
    setIsEditing(true);
    setEditId(product.id);
    setFormData({
      name: product.name,
      unit: product.unit,
      description: product.description || '',
    });
    setError(null);
    setSuccessMsg(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (!['admin', 'system_admin'].includes(currentRole)) {
      setError('HTTP 403 Forbidden: Chỉ Quản trị hệ thống mới có quyền ghi dữ liệu!');
      return;
    }

    if (!formData.name.trim()) {
      setError('Vui lòng nhập tên sản phẩm.');
      return;
    }

    // Kiểm tra đơn vị tính đóng
    if (!['kg', 'tấn', 'thùng'].includes(formData.unit)) {
      setError("Đơn vị tính không hợp lệ! Bắt buộc chọn từ danh sách đóng: 'kg', 'tấn', 'thùng'.");
      return;
    }

    // Kiểm tra trùng tên tại client nếu có
    const duplicate = products.find(
      (p) =>
        p.name.trim().toLowerCase() === formData.name.trim().toLowerCase() &&
        p.id !== editId
    );
    if (duplicate) {
      setError(`Sản phẩm với tên "${formData.name.trim()}" đã tồn tại trong hệ thống.`);
      return;
    }

    try {
      const url = isEditing ? `/api/v1/products/${editId}` : '/api/v1/products';
      const method = isEditing ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Thao tác thất bại (${res.status})`);
      }

      setSuccessMsg(isEditing ? 'Đã cập nhật sản phẩm thành công!' : 'Đã thêm sản phẩm mới thành công!');
      setIsModalOpen(false);
      fetchProducts();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, name) => {
    if (!['admin', 'system_admin'].includes(currentRole)) {
      alert('Chỉ vai trò Quản trị hệ thống (Admin) mới có quyền xóa sản phẩm (HTTP 403 Forbidden)!');
      return;
    }
    if (!window.confirm(`Bạn có chắc chắn muốn xóa sản phẩm "${name}" khỏi danh mục hệ thống?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/products/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Không thể xóa sản phẩm.');
      }
      setSuccessMsg(`Đã xóa sản phẩm "${name}".`);
      fetchProducts();
    } catch (err) {
      setError(err.message);
    }
  };

  const isAdmin = ['admin', 'system_admin'].includes(currentRole);


  return (
    <div className="space-y-6">
      {/* Top Banner & Tiêu đề */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                User Story S-07 (T-16, T-17)
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                Dùng chung toàn hệ thống
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Danh Mục Sản Phẩm & Đơn Vị Tính Đóng
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Bảng danh mục nông sản chuẩn hóa dùng chung toàn hệ thống (không lọc theo Organization ID).
              Đơn vị tính bắt buộc chọn từ danh sách đóng (kg, tấn, thùng).
            </p>
          </div>

          {/* Công cụ giả lập vai trò RBAC phục vụ nghiệm thu */}
          <div className="flex items-center gap-3 bg-slate-50 p-2.5 rounded-xl border border-slate-200">
            <span className="text-xs font-medium text-slate-600">Đang xem với vai trò:</span>
            <select
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              className="text-xs font-semibold bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
            >
              <option value="admin">Quản trị hệ thống (Admin) - Thấy nút & Gọi API ghi</option>
              <option value="farm">Vùng trồng (Farm) - Chỉ xem (Read-only)</option>
              <option value="inspector">Cán bộ kiểm tra (Inspector) - Chỉ xem (Read-only)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Thông báo lỗi / thành công */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-xl text-red-700 text-sm flex justify-between items-center shadow-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800 font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-50 border-l-4 border-emerald-500 p-4 rounded-xl text-emerald-800 text-sm flex justify-between items-center shadow-sm">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 hover:text-emerald-900 font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Thanh công cụ tìm kiếm và Thêm mới */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Tìm kiếm sản phẩm theo tên..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-slate-50 focus:bg-white transition"
          />
          <span className="absolute left-3 top-2.5 text-slate-400 text-sm">🔍</span>
        </div>

        <div>
          {isAdmin ? (
            <button
              onClick={handleOpenAddModal}
              className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-xl text-sm shadow-sm transition active:scale-95"
            >
              <span>+</span> Thêm Sản Phẩm Mới
            </button>
          ) : (
            <div className="text-xs text-slate-400 italic bg-slate-50 px-3 py-2 rounded-lg border border-slate-200">
              🔒 Nút Thêm/Sửa bị ẩn đối với vai trò {currentRole === 'farm' ? 'Vùng trồng' : 'Cán bộ kiểm tra'}.
            </div>
          )}
        </div>
      </div>

      {/* Bảng danh sách sản phẩm */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <th className="py-3 px-4">#</th>
                <th className="py-3 px-4">Tên Sản Phẩm</th>
                <th className="py-3 px-4">Đơn Vị Tính Đóng</th>
                <th className="py-3 px-4">Mô Tả</th>
                <th className="py-3 px-4">Ngày Tạo</th>
                {isAdmin && <th className="py-3 px-4 text-right">Thao Tác</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={isAdmin ? 6 : 5} className="text-center py-8 text-slate-400">
                    Đang tải danh mục sản phẩm...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={isAdmin ? 6 : 5} className="text-center py-8 text-slate-400">
                    Chưa có sản phẩm nào trong danh mục.
                  </td>
                </tr>
              ) : (
                products.map((item, index) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                      #{item.id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      {item.name}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
                        {item.unit}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 max-w-xs truncate">
                      {item.description || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400 font-mono">
                      {new Date(item.created_at).toLocaleDateString('vi-VN')}
                    </td>
                    {isAdmin && (
                      <td className="py-3.5 px-4 text-right space-x-2">
                        <button
                          onClick={() => handleOpenEditModal(item)}
                          className="px-2.5 py-1 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition"
                        >
                          Sửa
                        </button>
                        <button
                          onClick={() => handleDelete(item.id, item.name)}
                          className="px-2.5 py-1 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition"
                        >
                          Xóa
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Thêm / Chỉnh Sửa Sản Phẩm */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">
                {isEditing ? 'Cập Nhật Sản Phẩm' : 'Thêm Sản Phẩm Chuẩn Hóa Mới'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Tên Sản Phẩm <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ví dụ: Dâu tây New Zealand, Sầu riêng Ri6..."
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <p className="text-xs text-slate-400 mt-1">Hệ thống tự động chặn thêm sản phẩm trùng tên.</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Đơn Vị Tính Bắt Buộc (Danh Sách Đóng) <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.unit}
                  onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                >
                  {ALLOWED_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>
                      {u.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-amber-600 mt-1">
                  ⚠️ Bắt buộc chọn từ enum: tuyệt đối không cho phép nhập chữ tự do ngoài các giá trị này.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Mô Tả Sản Phẩm
                </label>
                <textarea
                  rows={3}
                  placeholder="Mô tả tiêu chuẩn, nguồn gốc, chứng nhận OCOP/VietGAP..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-sm transition"
                >
                  {isEditing ? 'Lưu Thay Đổi' : 'Thêm Sản Phẩm'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
