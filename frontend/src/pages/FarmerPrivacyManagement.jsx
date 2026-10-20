import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  UserX,
  ShieldCheck,
  ShieldAlert,
  Hash,
  Lock,
  EyeOff,
  Eye,
  Plus,
  RefreshCw,
  FileCheck,
  AlertTriangle,
  Building,
  CheckCircle2,
  Trash2,
} from 'lucide-react';
import { useAuthRole } from '../context/AuthRoleContext';

export default function FarmerPrivacyManagement() {
  const { authFetch, currentRole } = useAuthRole();
  const [farmers, setFarmers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [anonymizingRef, setAnonymizingRef] = useState(null);
  const [anonymizeReason, setAnonymizeReason] = useState(
    'Yêu cầu xóa dữ liệu cá nhân theo Điều 16 Nghị định 13/2023/NĐ-CP'
  );
  const [anonymizeResult, setAnonymizeResult] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Form đăng ký nông hộ mới
  const [fullName, setFullName] = useState('Trần Văn Nông Dân');
  const [phone, setPhone] = useState('0912345678');
  const [idCard, setIdCard] = useState('049090008888');
  const [address, setAddress] = useState('Số 45 Thôn Đa Quý, Xã Xuân Thọ');
  const [province, setProvince] = useState('Lâm Đồng');
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    fetchFarmers();
  }, [currentRole]);

  const fetchFarmers = async () => {
    setLoading(true);
    try {
      const res = await authFetch('/api/v1/farmers');
      if (res.ok) {
        const data = await res.json();
        setFarmers(data);
      }
    } catch (err) {
      console.error('Lỗi tải danh sách nông hộ:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFarmer = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setFormError(null);
    try {
      const payload = {
        full_name: fullName.trim(),
        phone: phone.trim(),
        id_card: idCard.trim(),
        detail_address: address.trim(),
        province: province.trim(),
      };
      const res = await authFetch('/api/v1/farmers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Không thể tạo hồ sơ nông hộ.');
      }
      setShowAddModal(false);
      fetchFarmers();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAnonymizeFarmer = async () => {
    if (!anonymizingRef) return;
    setActionLoading(true);
    setAnonymizeResult(null);
    try {
      const res = await authFetch(`/api/v1/farmers/${anonymizingRef}/anonymize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: anonymizeReason }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Xóa dữ liệu cá nhân thất bại.');
      }
      const data = await res.json();
      setAnonymizeResult(data);
      setAnonymizingRef(null);
      fetchFarmers();
    } catch (err) {
      alert(`Lỗi: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900 via-teal-900 to-slate-900 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/30 text-emerald-200 border border-emerald-400/30">
                Nghị định 13/2023/NĐ-CP • User Story S-56
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-200 border border-cyan-400/30">
                Bảo vệ Dữ liệu Cá nhân &amp; Chuỗi Hash Bất Biến
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-black tracking-tight flex items-center gap-2.5">
              <Lock className="w-7 h-7 text-emerald-400" />
              Ẩn Danh Dữ Liệu Nông Hộ Không Vỡ Chuỗi Hash (S-56)
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl mt-1">
              Dữ liệu cá nhân (Họ tên, SĐT, CCCD, Địa chỉ) được tách biệt ra khỏi chuỗi băm SHA-256.
              Chuỗi sự kiện chỉ lưu mã tham chiếu bí danh <code className="bg-black/30 px-1 py-0.5 rounded text-emerald-300 font-mono">farmer_ref_id</code>.
              Khi thực hiện quyền xóa dữ liệu cá nhân, chuỗi hash vẫn khớp 100% hợp lệ!
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white rounded-xl font-bold text-xs shadow-lg shadow-emerald-500/25 transition"
            >
              <Plus className="w-4 h-4" />
              Thêm Nông Hộ Mới (S-56)
            </button>
            <button
              onClick={fetchFarmers}
              disabled={loading}
              className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition border border-white/10"
              title="Làm mới danh sách"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Result Demonstration Box */}
      {anonymizeResult && (
        <div className="p-5 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-950 shadow-sm animate-in fade-in">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-emerald-900">
                  XÓA DỮ LIỆU ĐỊNH DANH CÁ NHÂN THÀNH CÔNG (NĐ 13/2023/NĐ-CP)
                </h3>
                <span className="px-2 py-0.5 rounded-full text-xs font-extrabold bg-emerald-200 text-emerald-900">
                  HỢP LỆ 100%
                </span>
              </div>
              <p className="text-xs text-emerald-800 mt-1 leading-relaxed">
                {anonymizeResult.message}
              </p>
              <div className="mt-3 p-3 bg-white/80 rounded-xl border border-emerald-200 text-xs space-y-1">
                <div className="flex items-center gap-2 font-bold text-slate-800">
                  <Hash className="w-4 h-4 text-emerald-600" />
                  Chứng minh tính bất biến chuỗi khối SHA-256:
                </div>
                <div className="text-slate-700 pl-6">
                  {anonymizeResult.integrity_message}
                </div>
                <div className="text-[11px] text-slate-500 pl-6 italic">
                  * Mọi màn hình và API công khai giờ đây hiển thị vùng trồng ở chế độ ẩn danh, bảo vệ quyền riêng tư tuyệt đối theo Nghị định 13/2023/NĐ-CP.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Architecture Concept Explainer Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center mb-2 font-bold">
            1
          </div>
          <h4 className="text-xs font-bold text-slate-900 uppercase">Tách Biệt Bảng Dữ Liệu PII</h4>
          <p className="text-xs text-slate-600 mt-1">
            Bảng <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">farmer_identities</code> lưu thông tin cá nhân.
            Tuyệt đối không nhúng Họ tên, SĐT, CCCD trực tiếp vào nội dung sự kiện băm.
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mb-2 font-bold">
            2
          </div>
          <h4 className="text-xs font-bold text-slate-900 uppercase">Chuỗi Hash Chỉ Băm Bí Danh</h4>
          <p className="text-xs text-slate-600 mt-1">
            Trong <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">chain_events</code>, nội dung JSON chỉ chứa{' '}
            <code className="text-emerald-700 font-mono font-bold">farmer_ref_id</code> (vd: FMR-DL-001) làm khóa liên kết.
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center mb-2 font-bold">
            3
          </div>
          <h4 className="text-xs font-bold text-slate-900 uppercase">Quyền Xóa Theo NĐ 13/2023</h4>
          <p className="text-xs text-slate-600 mt-1">
            Khi nông hộ yêu cầu xóa PII, hệ thống xóa sạch trong bảng định danh mà không cần sửa bảng sự kiện.
            Mã SHA-256 giữ nguyên 100%.
          </p>
        </div>
      </div>

      {/* Farmers List Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-emerald-600" />
            <h3 className="font-bold text-sm text-slate-900">Danh Sách Nông Hộ Vùng Trồng ({farmers.length})</h3>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            Quản lý quyền riêng tư &amp; Nghị định 13/2023/NĐ-CP
          </span>
        </div>

        {farmers.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            Chưa có nông hộ nào trong cơ sở dữ liệu. Bấm "Thêm Nông Hộ Mới" để tạo hồ sơ kiểm thử.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
                  <th className="py-3 px-4">Mã Bí Danh (Hash Ref)</th>
                  <th className="py-3 px-4">Tên Nông Hộ Hiển Thị</th>
                  <th className="py-3 px-4">Số Điện Thoại</th>
                  <th className="py-3 px-4">Địa Chỉ Vùng Trồng</th>
                  <th className="py-3 px-4 text-center">Trạng Thái PII</th>
                  <th className="py-3 px-4 text-right">Thao Tác Quyền Riêng Tư</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {farmers.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4 font-mono font-bold text-emerald-800">
                      {f.farmer_ref_id}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900">{f.display_name}</div>
                      <div className="text-[10px] text-slate-400">{f.organization_name}</div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">
                      {f.phone || <span className="text-slate-400 italic">[Đã xóa PII]</span>}
                    </td>
                    <td className="py-3 px-4 text-slate-600 max-w-xs truncate" title={f.detail_address}>
                      {f.detail_address || <span className="text-slate-400 italic">[Đã xóa theo NĐ 13]</span>}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {f.is_anonymized ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          <EyeOff className="w-3 h-3" /> Đã Ẩn Danh (NĐ 13)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                          <Eye className="w-3 h-3" /> Đầy Đủ Định Danh
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {f.is_anonymized ? (
                        <span className="text-[11px] font-bold text-slate-400 italic">
                          Đã xóa dữ liệu cá nhân
                        </span>
                      ) : (
                        <button
                          onClick={() => setAnonymizingRef(f.farmer_ref_id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-bold transition shadow-sm"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                          Xóa Dữ Liệu PII (S-56)
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Đăng ký nông hộ mới */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 bg-slate-800 text-white flex items-center justify-between">
              <span className="font-bold text-sm">Đăng Ký Hồ Sơ Nông Hộ Mới (S-56)</span>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleCreateFarmer} className="p-6 space-y-3.5 text-xs">
              {formError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700">
                  {formError}
                </div>
              )}

              <div>
                <label className="block font-bold text-slate-700 mb-1">Họ và tên nông hộ *</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Số điện thoại *</label>
                  <input
                    type="text"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-2 border rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Số CCCD / CMND</label>
                  <input
                    type="text"
                    value={idCard}
                    onChange={(e) => setIdCard(e.target.value)}
                    className="w-full px-3 py-2 border rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Địa chỉ chi tiết (Thôn/Xóm/Số nhà) *</label>
                <input
                  type="text"
                  required
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full px-3 py-2 border rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Tỉnh / Thành phố vùng trồng</label>
                <input
                  type="text"
                  value={province}
                  onChange={(e) => setProvince(e.target.value)}
                  className="w-full px-3 py-2 border rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div className="pt-3 border-t flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border rounded-xl text-slate-600 hover:bg-slate-50 font-bold"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold shadow-sm"
                >
                  {actionLoading ? 'Đang lưu...' : 'Tạo Hồ Sơ & Sinh Mã Bí Danh'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Xác Nhận Xóa / Ẩn Danh Dữ Liệu Theo NĐ 13/2023 */}
      {anonymizingRef && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 bg-rose-800 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-rose-300" />
                <span className="font-bold text-sm">Xóa Dữ Liệu Cá Nhân Theo Nghị Định 13/2023/NĐ-CP</span>
              </div>
              <button onClick={() => setAnonymizingRef(null)} className="text-slate-300 hover:text-white">✕</button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 flex items-start gap-2.5">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">Căn cứ pháp lý: Điều 16 Nghị định 13/2023/NĐ-CP</div>
                  <div className="mt-0.5 text-slate-700 leading-relaxed">
                    Chủ thể dữ liệu có quyền yêu cầu xóa dữ liệu cá nhân của mình. Sau khi xác nhận,
                    toàn bộ thông tin định danh (Họ tên, SĐT, CCCD, Địa chỉ) của mã{' '}
                    <b className="font-mono text-slate-900">{anonymizingRef}</b> sẽ bị xóa sạch vĩnh viễn khỏi CSDL.
                  </div>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Lý do yêu cầu xóa dữ liệu:</label>
                <textarea
                  rows={3}
                  value={anonymizeReason}
                  onChange={(e) => setAnonymizeReason(e.target.value)}
                  className="w-full px-3 py-2 border rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-rose-500/20 text-xs"
                />
              </div>

              <div className="p-3 bg-slate-50 border rounded-xl text-slate-600 space-y-1">
                <div className="font-bold text-slate-800 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" /> Cam kết toàn vẹn chuỗi khối (S-56):
                </div>
                <p>
                  Thao tác này chỉ xóa trong bảng định danh <code className="font-mono">farmer_identities</code>.
                  Chuỗi Hash SHA-256 của các lô hàng nông sản liên quan không bị sửa đổi hay đứt mạch chuỗi khối!
                </p>
              </div>

              <div className="pt-3 border-t flex items-center justify-end gap-2">
                <button
                  onClick={() => setAnonymizingRef(null)}
                  className="px-4 py-2 border rounded-xl text-slate-600 hover:bg-slate-50 font-bold"
                >
                  Hủy
                </button>
                <button
                  onClick={handleAnonymizeFarmer}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-bold shadow-sm"
                >
                  {actionLoading ? 'Đang thực hiện...' : 'Xác Nhận Xóa / Ẩn Danh Vĩnh Viễn'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
