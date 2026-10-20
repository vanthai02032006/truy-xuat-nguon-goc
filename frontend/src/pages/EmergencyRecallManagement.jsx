import React, { useState, useEffect } from 'react';
import { useAuthRole } from '../context/AuthRoleContext';
import {
  ShieldAlert,
  AlertTriangle,
  Lock,
  CheckCircle2,
  Clock,
  Building2,
  Store,
  Warehouse,
  Boxes,
  RefreshCw,
  Search,
  Check,
  X,
  ArrowRight,
  Hash,
  ChevronDown,
  ChevronUp,
  FileText,
  Percent,
} from 'lucide-react';

export default function EmergencyRecallManagement() {
  const { currentRole, activeRoleConfig, getAuthHeaders, canOpenRecall, isAdmin, isInspector } =
    useAuthRole();

  const [recalls, setRecalls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [selectedRecallId, setSelectedRecallId] = useState(null);

  // Modal mở lệnh thu hồi (S-33)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [batches, setBatches] = useState([]);
  const [targetBatchId, setTargetBatchId] = useState('');
  const [reason, setReason] = useState('');
  const [severity, setSeverity] = useState('CRITICAL');
  const [submittingRecall, setSubmittingRecall] = useState(false);

  // Xác nhận cô lập của tổ chức (S-36, S-37)
  const [confirmingOrgId, setConfirmingOrgId] = useState(null);
  const [confirmNotes, setConfirmNotes] = useState('Đã niêm phong kho và thu hồi toàn bộ nông sản khỏi kệ hàng');

  const fetchRecalls = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/v1/recalls', {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setRecalls(data.items || []);
        if (data.items?.length > 0 && !selectedRecallId) {
          setSelectedRecallId(data.items[0].id);
        }
      } else {
        const errJson = await res.json().catch(() => ({}));
        setErrorMsg(errJson.detail || `Lỗi tải danh sách lệnh thu hồi (${res.status})`);
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách lệnh thu hồi:', err);
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchBatches = async () => {
    try {
      const res = await fetch('/api/v1/batches', {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setBatches(data);
      } else {
        const errJson = await res.json().catch(() => ({}));
        console.error('Lỗi tải danh sách lô:', res.status, errJson);
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách lô:', err);
    }
  };

  useEffect(() => {
    fetchRecalls();
    fetchBatches();
  }, [currentRole]);

  // Mở Modal Thu Hồi Mới (S-33)
  const handleOpenModal = () => {
    if (!canOpenRecall) {
      alert(
        `Vai trò hiện tại [${activeRoleConfig.name}] không có quyền mở lệnh thu hồi! Chỉ Cán bộ kiểm tra (Inspector) hoặc Quản trị viên mới được phép (S-33).`
      );
      return;
    }
    setReason('');
    setSeverity('CRITICAL');
    if (batches.length > 0) {
      // Ưu tiên chọn lô MERGE-TOM-M1 nếu có để test
      const m1 = batches.find((b) => b.batch_code === 'MERGE-TOM-M1');
      setTargetBatchId(m1 ? m1.id : batches[0].id);
    }
    setIsModalOpen(true);
  };

  // Nạp nhanh kịch bản mẫu thu hồi lô MERGE-TOM-M1
  const handleQuickFillDemo = () => {
    const m1 = batches.find((b) => b.batch_code === 'MERGE-TOM-M1');
    if (m1) {
      setTargetBatchId(m1.id);
    }
    setReason(
      'Phát hiện dư lượng kim loại nặng vượt ngưỡng quy chuẩn an toàn VietGAP tại đợt kiểm nghiệm độc lập định kỳ'
    );
    setSeverity('CRITICAL');
  };

  // Gửi Mở Lệnh Thu Hồi
  const handleSubmitRecall = async (e) => {
    e.preventDefault();
    if (!targetBatchId) {
      alert('Vui lòng chọn lô hàng phát hiện sự cố.');
      return;
    }
    if (reason.trim().length < 20) {
      alert('Lý do thu hồi bắt buộc phải có ít nhất 20 ký tự mô tả cụ thể sự cố (S-33)!');
      return;
    }

    setSubmittingRecall(true);
    try {
      const res = await fetch('/api/v1/recalls', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          batch_id: Number(targetBatchId),
          reason: reason.trim(),
          severity,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Không thể mở lệnh thu hồi');
      }

      const resData = await res.json();
      setSuccessMsg(
        `ĐÃ MỞ LỆNH THU HỒI [${resData.recall_code}] THÀNH CÔNG! Đã tự động khoanh vùng ${resData.total_affected_batches} lô hậu duệ (${resData.total_affected_kg} kg) và KHÓA TỨC THÌ mọi quyền Bàn giao, Tách, Gộp (S-38).`
      );
      setIsModalOpen(false);
      await fetchRecalls();
      setSelectedRecallId(resData.id);
    } catch (err) {
      alert(`Thất bại: ${err.message}`);
    } finally {
      setSubmittingRecall(false);
    }
  };

  // Xác nhận cô lập của tổ chức (S-36, S-37)
  const handleConfirmIsolation = async (recallId, action) => {
    try {
      const res = await fetch(`/api/v1/recalls/${recallId}/confirm-isolation`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          notes: confirmNotes || 'Đã hoàn tất cô lập, niêm phong toàn bộ hàng trong kho',
        }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Không thể xác nhận cô lập');
      }

      const updated = await res.json();
      setSuccessMsg(
        `Xác nhận cô lập thành công cho tổ chức [${action.organization_name}]! Tiến độ hiện tại: ${updated.progress.status_summary} (${updated.progress.progress_percentage}%).`
      );
      await fetchRecalls();
    } catch (err) {
      alert(`Thất bại: ${err.message}`);
    }
  };

  // Tổng hợp KPI
  const activeRecallsCount = recalls.filter((r) => r.status === 'ACTIVE' || r.status === 'IN_PROGRESS').length;
  const totalAffectedWeight = recalls.reduce((sum, r) => sum + (r.total_affected_kg || 0), 0);
  const totalStockWeight = recalls.reduce((sum, r) => sum + (r.total_stock_kg || 0), 0);
  const totalSoldWeight = recalls.reduce((sum, r) => sum + (r.total_sold_kg || 0), 0);

  const selectedRecall = recalls.find((r) => r.id === selectedRecallId) || recalls[0];

  return (
    <div className="space-y-6">
      {/* Tiêu đề & Nút Mở Lệnh Thu Hồi */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-rose-50 text-rose-600 border border-rose-100">
              <ShieldAlert className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900">
              Quản Lý Thu Hồi Nông Sản Khẩn Cấp (Emergency Recall)
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-rose-100 text-rose-800 border border-rose-200">
              Epic E-06 (S-33 ➔ S-38)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Tự động khoanh vùng mọi lô con cháu qua BFS downstream ➔ Thống kê số kg trên kệ vs đã tiêu thụ (S-29) ➔
            Khóa tức thì quyền Bàn giao, Tách, Gộp (S-38) ➔ Giám sát thanh tiến độ xử lý của các tổ chức (S-36, S-37).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenModal}
            disabled={!canOpenRecall}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition ${
              canOpenRecall
                ? 'bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-700 hover:to-red-700 shadow-rose-500/20'
                : 'bg-slate-300 cursor-not-allowed opacity-60'
            }`}
            title={canOpenRecall ? 'Mở lệnh thu hồi sự cố an toàn thực phẩm' : 'Chỉ Cán bộ kiểm tra hoặc Quản trị viên mới có quyền mở thu hồi'}
          >
            <ShieldAlert className="w-4 h-4" />
            Mở Lệnh Thu Hồi Khẩn Cấp (S-33)
          </button>
        </div>
      </div>

      {/* Thông báo Thành công / Lỗi */}
      {successMsg && (
        <div className="flex items-start justify-between gap-3 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-500 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Cụm Thẻ Thống Kê KPI (Tổng quan Epic E-06) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500">Lệnh Thu Hồi Kích Hoạt</div>
            <div className="text-2xl font-black text-rose-600 mt-1">{activeRecallsCount}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Tổng số lệnh: {recalls.length}</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500">Tổng Lượng Bị Phong Tỏa</div>
            <div className="text-2xl font-black text-slate-900 mt-1">
              {totalAffectedWeight.toLocaleString()} <span className="text-xs font-bold text-slate-500">kg</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Bao gồm toàn bộ cây hậu duệ</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Boxes className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-amber-700">Tồn Kho / Trên Kệ (Khoanh Vùng)</div>
            <div className="text-2xl font-black text-amber-700 mt-1">
              {totalStockWeight.toLocaleString()} <span className="text-xs font-bold text-slate-500">kg</span>
            </div>
            <div className="text-[11px] text-amber-600 mt-0.5">Cần niêm phong & cô lập ngay</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Warehouse className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-blue-700">Đã Bán Cho Người Tiêu Dùng</div>
            <div className="text-2xl font-black text-blue-700 mt-1">
              {totalSoldWeight.toLocaleString()} <span className="text-xs font-bold text-slate-500">kg</span>
            </div>
            <div className="text-[11px] text-blue-600 mt-0.5">Phát cảnh báo thu hồi công cộng</div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Store className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Cảnh Báo An Toàn S-38: KHÓA TỨC THÌ CÁC LÔ NẰM TRONG LỆNH THU HỒI */}
      {activeRecallsCount > 0 && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-rose-500 to-red-600 text-white shadow-lg shadow-rose-500/20 border border-rose-400">
          <div className="flex items-start gap-3">
            <span className="p-2 rounded-xl bg-white/20 backdrop-blur-md">
              <Lock className="w-6 h-6 text-white" />
            </span>
            <div>
              <h4 className="text-sm font-bold uppercase tracking-wide">
                Hệ Thống Đang Kích Hoạt Cơ Chế Khóa Tức Thì Chống Lan Rộng (S-38)
              </h4>
              <p className="text-xs text-rose-100 mt-1 leading-relaxed">
                Tất cả các lô hàng thuộc các Lệnh thu hồi đang hoạt động dưới đây đã bị <strong>TỰ ĐỘNG CHẶN HOÀN TOÀN</strong> quyền
                Bàn giao chuỗi cung ứng, Tách lô và Gộp lô. Mọi nỗ lực thao tác trên API hoặc giao diện sẽ bị từ chối
                (HTTP 400 Bad Request) để ngăn ngừa nguy cơ phân tán nông sản ô nhiễm.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* NỘI DUNG CHÍNH: DANH SÁCH LỆNH & CHI TIẾT KHOANH VÙNG TIẾN ĐỘ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Cột Trái: Danh Sách Lệnh Thu Hồi - Chiếm 5 Cột */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Danh Sách Lệnh Thu Hồi ({recalls.length})
            </h3>
            <button
              onClick={fetchRecalls}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-medium"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Làm mới
            </button>
          </div>

          {loading ? (
            <div className="py-12 text-center text-xs text-slate-500">Đang tải danh sách lệnh thu hồi...</div>
          ) : recalls.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="text-sm font-bold text-slate-800">Không Có Lệnh Thu Hồi Nào Đang Hoạt Động</div>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Toàn bộ lô hàng trên hệ thống đều đạt chuẩn an toàn vệ sinh thực phẩm và không ghi nhận sự cố.
              </p>
              {canOpenRecall && (
                <button
                  onClick={handleOpenModal}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 shadow-sm"
                >
                  Mở Lệnh Thu Hồi Thử Nghiệm (S-33)
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
              {recalls.map((r) => {
                const isSelected = r.id === selectedRecallId;
                const isCompleted = r.status === 'COMPLETED';
                return (
                  <div
                    key={r.id}
                    onClick={() => setSelectedRecallId(r.id)}
                    className={`p-4 rounded-2xl border cursor-pointer transition space-y-2.5 ${
                      isSelected
                        ? 'border-rose-500 bg-rose-50/40 shadow-sm'
                        : 'border-slate-200 bg-white hover:bg-slate-50/80'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-extrabold text-rose-900">
                        {r.recall_code}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                          isCompleted
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-rose-100 text-rose-800 border border-rose-200 animate-pulse'
                        }`}
                      >
                        {isCompleted ? 'Đã hoàn tất' : 'Đang xử lý'}
                      </span>
                    </div>

                    <div className="text-xs font-bold text-slate-900">
                      Lô sự cố: <span className="font-mono text-rose-700">{r.source_batch_code}</span> ({r.product_name})
                    </div>

                    <p className="text-xs text-slate-600 line-clamp-2 italic bg-slate-50/80 p-2 rounded-lg border border-slate-100">
                      "{r.reason}"
                    </p>

                    {/* Tiến độ cô lập của các tổ chức */}
                    <div className="space-y-1 pt-1">
                      <div className="flex justify-between text-[11px] font-semibold">
                        <span className="text-slate-500">Tiến độ cô lập:</span>
                        <span className={isCompleted ? 'text-emerald-700' : 'text-rose-700'}>
                          {r.progress?.status_summary || 'Đang cập nhật'} ({Math.round(r.progress?.progress_percentage || 0)}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            isCompleted ? 'bg-emerald-500' : 'bg-gradient-to-r from-rose-500 to-amber-500'
                          }`}
                          style={{ width: `${r.progress?.progress_percentage || 0}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                      <span>Người mở: <strong>{r.initiator_name}</strong></span>
                      <span>{new Date(r.created_at).toLocaleDateString('vi-VN')}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Cột Phải: Chi Tiết Lệnh Thu Hồi Đang Chọn - Chiếm 7 Cột */}
        <div className="lg:col-span-7 space-y-6">
          {selectedRecall ? (
            <>
              {/* Thẻ Thông Tin Chi Tiết Lệnh */}
              <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <span className="text-xs text-slate-400 font-semibold">CHI TIẾT LỆNH THU HỒI</span>
                    <h2 className="text-lg font-black text-slate-900 font-mono tracking-wide">
                      {selectedRecall.recall_code}
                    </h2>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold px-2.5 py-1 rounded-lg bg-rose-100 text-rose-800 border border-rose-200">
                      Mức độ: {selectedRecall.severity}
                    </span>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {new Date(selectedRecall.created_at).toLocaleString('vi-VN')}
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-rose-50/60 rounded-xl border border-rose-200 text-xs text-rose-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-rose-950">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    Lý do thu hồi (Vi phạm an toàn thực phẩm):
                  </div>
                  <p className="leading-relaxed pl-5">{selectedRecall.reason}</p>
                </div>

                {/* Thống kê 3 phân vùng khối lượng (S-29) */}
                <div className="grid grid-cols-3 gap-3 text-center text-xs">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="text-slate-400 text-[11px]">Tổng Ảnh Hưởng</div>
                    <div className="text-base font-extrabold text-slate-900 mt-0.5">
                      {selectedRecall.total_affected_kg} kg
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {selectedRecall.total_affected_batches} lô con cháu
                    </div>
                  </div>
                  <div className="p-3 bg-amber-50 rounded-xl border border-amber-200">
                    <div className="text-amber-700 text-[11px] font-semibold">Tồn Kho / Trên Kệ</div>
                    <div className="text-base font-extrabold text-amber-800 mt-0.5">
                      {selectedRecall.total_stock_kg} kg
                    </div>
                    <div className="text-[10px] text-amber-600 mt-0.5">Cần cô lập niêm phong</div>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-xl border border-blue-200">
                    <div className="text-blue-700 text-[11px] font-semibold">Đã Bán Ra Thị Trường</div>
                    <div className="text-base font-extrabold text-blue-800 mt-0.5">
                      {selectedRecall.total_sold_kg} kg
                    </div>
                    <div className="text-[10px] text-blue-600 mt-0.5">Cảnh báo người tiêu dùng</div>
                  </div>
                </div>
              </div>

              {/* KHU VỰC: TIẾN ĐỘ XÁC NHẬN CỦA CÁC TỔ CHỨC (S-36, S-37) */}
              <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <span className="w-7 h-7 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-xs">
                      <Percent className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                        Tiến Độ Xử Lý & Xác Nhận Của Các Tổ Chức (S-36, S-37)
                      </h3>
                      <div className="text-[11px] text-slate-500">
                        {selectedRecall.progress?.status_summary || 'Đang cập nhật'}
                      </div>
                    </div>
                  </div>
                  <span className="text-sm font-extrabold text-teal-700">
                    {Math.round(selectedRecall.progress?.progress_percentage || 0)}%
                  </span>
                </div>

                {/* Thanh tiến độ */}
                <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden p-0.5 border border-slate-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-teal-500 to-emerald-500 transition-all duration-500"
                    style={{ width: `${selectedRecall.progress?.progress_percentage || 0}%` }}
                  ></div>
                </div>

                {/* Danh sách hành động của từng tổ chức */}
                <div className="space-y-3 pt-2">
                  {selectedRecall.organization_actions && selectedRecall.organization_actions.length > 0 ? (
                    selectedRecall.organization_actions.map((act) => {
                      const isIsolated = act.status === 'CONFIRMED_ISOLATED';
                      return (
                        <div
                          key={act.id}
                          className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs transition ${
                            isIsolated
                              ? 'border-emerald-200 bg-emerald-50/40'
                              : 'border-amber-200 bg-amber-50/40'
                          }`}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Building2 className="w-4 h-4 text-slate-500" />
                              <span className="font-bold text-slate-900">{act.organization_name}</span>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  isIsolated
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {isIsolated ? 'Đã cô lập 100%' : 'Chờ xác nhận'}
                              </span>
                            </div>
                            <div className="text-slate-500 text-[11px]">
                              Số lô liên đới: <strong>{act.affected_batch_count} lô</strong> • Tồn kho:{' '}
                              <strong className="text-slate-800">{act.stock_kg} kg</strong>
                            </div>
                            {act.action_notes && (
                              <div className="text-[11px] text-slate-600 italic">
                                Ghi chú: "{act.action_notes}"
                              </div>
                            )}
                            {act.confirmed_by_name && (
                              <div className="text-[10px] text-emerald-700 font-medium">
                                Xác nhận bởi: {act.confirmed_by_name} lúc{' '}
                                {new Date(act.confirmed_at).toLocaleString('vi-VN')}
                              </div>
                            )}
                          </div>

                          {/* Nút bấm Xác nhận đã xử lý */}
                          {!isIsolated && (
                            <button
                              onClick={() => handleConfirmIsolation(selectedRecall.id, act)}
                              className="px-3.5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 shadow-sm transition whitespace-nowrap self-start sm:self-auto"
                            >
                              Xác Nhận Đã Xử Lý (S-36)
                            </button>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-xs text-slate-400 py-3 text-center">
                      Không có danh sách hành động cho tổ chức.
                    </div>
                  )}
                </div>
              </div>

              {/* KHU VỰC: DANH SÁCH CHI TIẾT TẤT CẢ LÔ HẬU DUỆ BỊ KHOANH VÙNG (S-29) */}
              <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <span className="w-7 h-7 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center font-bold text-xs">
                      <Lock className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                        Danh Sách Lô Hàng Bị Khoanh Vùng & Phong Tỏa ({selectedRecall.affected_batches?.length || 0})
                      </h3>
                      <div className="text-[11px] text-slate-500">
                        Chi tiết theo từng địa điểm & khối lượng tồn kho vs tiêu thụ (S-29)
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {selectedRecall.affected_batches && selectedRecall.affected_batches.length > 0 ? (
                    selectedRecall.affected_batches.map((item) => (
                      <div
                        key={item.id}
                        className="p-3 rounded-xl border border-slate-200 bg-slate-50/70 text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-slate-900 flex items-center gap-1">
                            <Lock className="w-3.5 h-3.5 text-rose-600" />
                            {item.batch_code}
                          </span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                            {item.generation}
                          </span>
                        </div>

                        <div className="text-slate-800 font-semibold">{item.product_name}</div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                          <div>
                            Tổ chức: <strong className="text-slate-800">{item.organization_name}</strong>
                          </div>
                          <div>
                            Địa điểm / Cửa hàng: <strong className="text-slate-800">{item.current_location || 'Kho trung tâm'}</strong>
                          </div>
                          <div>
                            Còn trên kệ / Kho:{' '}
                            <strong className="text-amber-800 font-bold">{item.remaining_quantity} kg</strong>
                          </div>
                          <div>
                            Đã bán ra cho người dân:{' '}
                            <strong className="text-blue-800 font-bold">{item.sold_quantity} kg</strong>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 py-3 text-center">
                      Không có thông tin lô bị ảnh hưởng.
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-400">
              Vui lòng chọn một lệnh thu hồi từ danh sách bên trái để xem tiến độ khoanh vùng.
            </div>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* MODAL MỞ LỆNH THU HỒI KHẨN CẤP (S-33, S-34, S-35) */}
      {/* ========================================================================= */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-rose-50 text-rose-600 font-bold">
                  <ShieldAlert className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Mở Lệnh Thu Hồi Khẩn Cấp (User Story S-33)
                  </h3>
                  <div className="text-xs text-slate-500">
                    Bắt buộc lý do tối thiểu 20 ký tự • Tự động khoanh vùng qua BFS
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Nút nạp nhanh kịch bản test */}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleQuickFillDemo}
                className="text-xs text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg border border-rose-200 font-semibold"
              >
                ⚡ Điền Nhanh Kịch Bản Mẫu (Lô MERGE-TOM-M1)
              </button>
            </div>

            <form onSubmit={handleSubmitRecall} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Chọn Lô Hàng Phát Hiện Sự Cố (*):
                </label>
                <select
                  value={targetBatchId}
                  onChange={(e) => setTargetBatchId(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 font-medium focus:outline-none focus:ring-2 focus:ring-rose-500/20"
                  required
                >
                  <option value="" disabled>-- Chọn Lô Cần Kích Hoạt Thu Hồi --</option>
                  {batches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.batch_code} - {b.product_name} ({b.remaining_quantity} {b.unit})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Mức Độ Nghiêm Trọng:
                </label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 font-medium focus:outline-none focus:ring-2 focus:ring-rose-500/20"
                >
                  <option value="CRITICAL">CRITICAL - Cực kỳ nghiêm trọng (Thu hồi khẩn cấp diện rộng)</option>
                  <option value="HIGH">HIGH - Nghiêm trọng (Thu hồi cục bộ)</option>
                  <option value="MEDIUM">MEDIUM - Trung bình (Cảnh báo giám sát)</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-bold text-slate-700">
                    Lý Do Thu Hồi Chi Tiết (Bắt buộc tối thiểu 20 ký tự) (*):
                  </label>
                  <span
                    className={`text-[11px] font-bold ${
                      reason.trim().length >= 20 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {reason.trim().length} / 20 ký tự {reason.trim().length >= 20 ? '✓ Đạt chuẩn' : '⚠️ Chưa đủ'}
                  </span>
                </div>
                <textarea
                  rows="3"
                  placeholder="Mô tả cụ thể sự cố an toàn thực phẩm, mẫu xét nghiệm vi phạm hoặc nguồn lây nhiễm (tối thiểu 20 ký tự)..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className={`w-full px-3 py-2 text-xs rounded-xl border focus:outline-none focus:ring-2 ${
                    reason.trim().length >= 20
                      ? 'border-slate-200 focus:ring-emerald-500/20'
                      : 'border-rose-300 focus:ring-rose-500/20'
                  }`}
                  required
                ></textarea>
              </div>

              <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-[11px] text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1 text-amber-950">
                  <Lock className="w-3.5 h-3.5 text-amber-700" />
                  Hiệu Lực Khóa Tức Thì Sau Khi Bấm:
                </div>
                <p>
                  Hệ thống sẽ dùng thuật toán BFS tự động truy xuôi toàn bộ các lô con cháu liên quan và khóa tức thì
                  quyền Bàn giao, Tách lô, Gộp lô đối với các lô này (S-38).
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={submittingRecall || reason.trim().length < 20}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-700 hover:to-red-700 shadow-md shadow-rose-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submittingRecall ? 'Đang Khoanh Vùng & Khóa...' : 'Kích Hoạt Lệnh Thu Hồi Khẩn Cấp'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
