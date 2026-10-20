import React, { useState, useEffect } from 'react';
import { useAuthRole } from '../context/AuthRoleContext';
import {
  GitFork,
  GitMerge,
  Network,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Search,
  RefreshCw,
  Lock,
  Building2,
  Store,
  Warehouse,
  FileText,
  Check,
  X,
  Info,
  ExternalLink,
  Clock,
  Sparkles,
  ShieldAlert,
  ChevronRight,
  Hash,
  Boxes,
} from 'lucide-react';

export default function BatchLineageDAG() {
  const { currentRole, activeRoleConfig, getAuthHeaders, canSplitMerge } = useAuthRole();

  // State dữ liệu phả hệ
  const [batches, setBatches] = useState([]);
  const [selectedBatchId, setSelectedBatchId] = useState(null);
  const [dagData, setDagData] = useState(null);
  const [loadingDag, setLoadingDag] = useState(false);
  const [loadingSeed, setLoadingSeed] = useState(false);
  const [seedResult, setSeedResult] = useState(null);
  const [showAnswerKey, setShowAnswerKey] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [cycleError, setCycleError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Modals
  const [showSplitModal, setShowSplitModal] = useState(false);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [targetSplitBatch, setTargetSplitBatch] = useState(null);

  // Form Tách Lô (Split)
  const [splitChildren, setSplitChildren] = useState([
    { quantity: 200, notes: 'Lô con A - Sơ chế sỉ' },
    { quantity: 300, notes: 'Lô con B - Điểm bán lẻ' },
  ]);
  const [splitSubmitting, setSplitSubmitting] = useState(false);

  // Form Gộp Lô (Merge)
  const [mergeSelectedBatches, setMergeSelectedBatches] = useState([]);
  const [mergeNotes, setMergeNotes] = useState('Gộp nguyên liệu cùng loại sản phẩm theo S-19');
  const [mergeSubmitting, setMergeSubmitting] = useState(false);

  // Tải danh sách lô hàng
  const fetchBatches = async () => {
    try {
      const res = await fetch('/api/v1/batches', {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setBatches(data);
        if (!selectedBatchId && data.length > 0) {
          setSelectedBatchId(data[0].id);
        }
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách lô:', err);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, [currentRole]);

  // Tải Đồ thị DAG cho lô được chọn
  const fetchDagForBatch = async (batchId) => {
    if (!batchId) return;
    setLoadingDag(true);
    setCycleError(null);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/v1/batches/${batchId}/dag-graph`, {
        headers: getAuthHeaders(),
      });
      if (res.status === 400) {
        const errJson = await res.json();
        if (errJson.detail && errJson.detail.includes('chu trình')) {
          setCycleError(errJson.detail);
          setDagData(null);
          return;
        }
      }
      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Không thể tải đồ thị DAG');
      }
      const data = await res.json();
      setDagData(data);
    } catch (err) {
      setErrorMsg(err.message);
      setDagData(null);
    } finally {
      setLoadingDag(false);
    }
  };

  useEffect(() => {
    if (selectedBatchId) {
      fetchDagForBatch(selectedBatchId);
    }
  }, [selectedBatchId]);

  // 1. Thao tác Nạp Dữ Liệu Mẫu (Seed S-22 / S-39)
  const handleSeedDag = async () => {
    setLoadingSeed(true);
    setErrorMsg(null);
    setCycleError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch('/api/v1/batches/seed-lineage-dag', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Không thể nạp dữ liệu mẫu');
      }
      const data = await res.json();
      setSeedResult(data);
      setShowAnswerKey(true);
      setSuccessMsg('Đã nạp thành công bộ dữ liệu mẫu phả hệ 3-4 tầng (13 lô, 4 tổ chức)!');

      // Tải lại danh sách lô
      await fetchBatches();

      // Mặc định chọn Lô gộp MERGE-TOM-M1 để trực quan hóa
      const mergeM1 = data.sample_batches.find((b) => b.batch_code === 'MERGE-TOM-M1');
      if (mergeM1) {
        setSelectedBatchId(mergeM1.id);
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoadingSeed(false);
    }
  };

  // 2. Thao tác Tách Lô (Split - S-17)
  const handleOpenSplitModal = (batch) => {
    if (!canSplitMerge) {
      alert(
        `Vai trò hiện tại [${activeRoleConfig.name}] không có quyền Tách lô! Chỉ HTX Sơ chế và Nhà phân phối mới được phép thao tác (S-17).`
      );
      return;
    }
    if (batch.status === 'Bị phong tỏa thu hồi') {
      alert(`Lô [${batch.batch_code}] đang nằm trong Lệnh thu hồi khẩn cấp, đã bị KHÓA quyền Tách lô theo S-38!`);
      return;
    }
    setTargetSplitBatch(batch);
    const half = Math.max(10, Math.floor((batch.remaining_quantity || 100) / 2));
    setSplitChildren([
      { quantity: half, notes: 'Lô con 1 - Đóng gói bao bì mới' },
      { quantity: half, notes: 'Lô con 2 - Phân phối điểm bán' },
    ]);
    setShowSplitModal(true);
  };

  const handleAddSplitRow = () => {
    setSplitChildren([...splitChildren, { quantity: 50, notes: `Lô con ${splitChildren.length + 1}` }]);
  };

  const handleRemoveSplitRow = (idx) => {
    if (splitChildren.length <= 1) return;
    setSplitChildren(splitChildren.filter((_, i) => i !== idx));
  };

  const handleUpdateSplitQty = (idx, val) => {
    const updated = [...splitChildren];
    updated[idx].quantity = parseFloat(val) || 0;
    setSplitChildren(updated);
  };

  const handleUpdateSplitNote = (idx, val) => {
    const updated = [...splitChildren];
    updated[idx].notes = val;
    setSplitChildren(updated);
  };

  const submitSplitBatch = async (e) => {
    e.preventDefault();
    if (!targetSplitBatch) return;

    const totalSplit = splitChildren.reduce((sum, item) => sum + (parseFloat(item.quantity) || 0), 0);
    if (totalSplit <= 0) {
      alert('Tổng khối lượng tách phải lớn hơn 0!');
      return;
    }
    if (totalSplit > (targetSplitBatch.remaining_quantity || 0)) {
      alert(
        `LỖI KHỐI LƯỢNG: Tổng khối lượng tách (${totalSplit} ${targetSplitBatch.unit}) vượt quá khối lượng còn lại của lô mẹ (${targetSplitBatch.remaining_quantity} ${targetSplitBatch.unit})!`
      );
      return;
    }

    setSplitSubmitting(true);
    try {
      const res = await fetch(`/api/v1/batches/${targetSplitBatch.id}/split`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          splits: splitChildren.map((c) => ({
            quantity: c.quantity,
            notes: c.notes,
          })),
          notes: `Tách ${splitChildren.length} lô con từ lô mẹ ${targetSplitBatch.batch_code}`,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Không thể thực hiện tách lô');
      }

      const resData = await res.json();
      setSuccessMsg(
        `Tách lô thành công! Đã tạo ${resData.child_batches.length} lô con với mã 8 ký tự an toàn: [${resData.child_batches.map((c) => c.batch_code).join(', ')}] và ghi vào chuỗi hash mẹ & con.`
      );
      setShowSplitModal(false);
      await fetchBatches();
      fetchDagForBatch(targetSplitBatch.id);
    } catch (err) {
      alert(`Thất bại: ${err.message}`);
    } finally {
      setSplitSubmitting(false);
    }
  };

  // 3. Thao tác Gộp Lô (Merge - S-19)
  const handleOpenMergeModal = () => {
    if (!canSplitMerge) {
      alert(
        `Vai trò hiện tại [${activeRoleConfig.name}] không có quyền Gộp lô! Chỉ HTX Sơ chế và Nhà phân phối mới được phép thao tác (S-19).`
      );
      return;
    }
    setMergeSelectedBatches([]);
    setShowMergeModal(true);
  };

  const toggleSelectMergeBatch = (batch) => {
    if (batch.status === 'Bị phong tỏa thu hồi') {
      alert(`Lô [${batch.batch_code}] đang bị phong tỏa thu hồi, không thể gộp lô (S-38)!`);
      return;
    }
    const exists = mergeSelectedBatches.find((b) => b.batch_id === batch.id);
    if (exists) {
      setMergeSelectedBatches(mergeSelectedBatches.filter((b) => b.batch_id !== batch.id));
    } else {
      // Kiểm tra xem sản phẩm có cùng loại với các lô đã chọn trước không
      if (mergeSelectedBatches.length > 0) {
        const firstSelected = batches.find((b) => b.id === mergeSelectedBatches[0].batch_id);
        if (firstSelected && firstSelected.product_name.toLowerCase() !== batch.product_name.toLowerCase()) {
          alert(
            `QUY TẮC S-19: Chỉ được gộp các lô có CÙNG LOẠI SẢN PHẨM!\n- Lô đã chọn: ${firstSelected.product_name}\n- Lô vừa bấm: ${batch.product_name}`
          );
          return;
        }
      }
      const defaultQty = Math.min(batch.remaining_quantity || 10, 50);
      setMergeSelectedBatches([
        ...mergeSelectedBatches,
        {
          batch_id: batch.id,
          batch_code: batch.batch_code,
          product_name: batch.product_name,
          unit: batch.unit || 'kg',
          max_qty: batch.remaining_quantity || 0,
          quantity: defaultQty,
        },
      ]);
    }
  };

  const handleUpdateMergeQty = (batchId, val) => {
    setMergeSelectedBatches(
      mergeSelectedBatches.map((b) =>
        b.batch_id === batchId ? { ...b, quantity: parseFloat(val) || 0 } : b
      )
    );
  };

  const submitMergeBatches = async (e) => {
    e.preventDefault();
    if (mergeSelectedBatches.length < 2) {
      alert('Vui lòng chọn ít nhất 2 lô hàng để thực hiện gộp lô (S-19)!');
      return;
    }

    for (const b of mergeSelectedBatches) {
      if (b.quantity <= 0) {
        alert(`Khối lượng gộp của lô [${b.batch_code}] phải lớn hơn 0!`);
        return;
      }
      if (b.quantity > b.max_qty) {
        alert(
          `Khối lượng gộp từ lô [${b.batch_code}] (${b.quantity} ${b.unit}) vượt quá số lượng còn lại (${b.max_qty} ${b.unit})!`
        );
        return;
      }
    }

    setMergeSubmitting(true);
    try {
      const res = await fetch('/api/v1/batches/merge', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          sources: mergeSelectedBatches.map((b) => ({
            batch_id: b.batch_id,
            quantity: b.quantity,
          })),
          notes: mergeNotes,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Không thể thực hiện gộp lô');
      }

      const resData = await res.json();
      setSuccessMsg(
        `Gộp lô thành công! Đã tạo lô gộp mới [${resData.merged_batch.batch_code}] (${resData.total_merged_quantity} ${resData.merged_batch.unit}) khóa dòng chống deadlock & ghi nhận vào chuỗi hash mẹ - con.`
      );
      setShowMergeModal(false);
      await fetchBatches();
      setSelectedBatchId(resData.merged_batch.id);
    } catch (err) {
      alert(`Thất bại: ${err.message}`);
    } finally {
      setMergeSubmitting(false);
    }
  };

  // 4. Mô phỏng phát hiện chu trình vòng lặp (S-21, S-28)
  const handleSimulateCycleError = () => {
    setCycleError(
      '🚨 PHÁT HIỆN CHU TRÌNH VÒNG LẶP BẤT THƯỜNG TRONG PHẢ HỆ (DAG Violation): Lô #101 đã xuất hiện lặp lại trên đường đi phả hệ (101 -> 205 -> 304 -> 101). Hệ thống kích hoạt thuật toán Cycle Detection từ chối xử lý để đảm bảo đồ thị có hướng không chu trình!'
    );
  };

  // Lọc danh sách lô theo từ khóa
  const filteredBatches = batches.filter(
    (b) =>
      b.batch_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      b.product_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Tiêu đề & Nút thao tác đầu trang */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
              <Network className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900">
              Phả Hệ Lô Hàng Đa Chiều (DAG Lineage)
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              Epic E-05 (S-17 ➔ S-28)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Trực quan hóa cấu trúc đồ thị có hướng không chu trình: Truy ngược nguồn gốc gốc rễ (BFS Upstream)
            ➔ Lô trung tâm ➔ Truy xuôi hậu duệ phân phối & kiểm đếm khối lượng (BFS Downstream).
          </p>
        </div>

        {/* Cụm nút hành động chính */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Nút Nạp Dữ Liệu Mẫu Phả Hệ 3-4 Tầng */}
          <button
            onClick={handleSeedDag}
            disabled={loadingSeed}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 shadow-sm shadow-emerald-500/20 transition disabled:opacity-50"
            title="Tạo ngay mạng lưới 13 lô qua 4 tổ chức với quan hệ tách gộp và đáp án đối chiếu"
          >
            {loadingSeed ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Boxes className="w-4 h-4" />
            )}
            Nạp bộ dữ liệu mẫu phả hệ 3-4 tầng (Seed S-22 / S-39)
          </button>

          {/* Nút Tách Lô */}
          <button
            onClick={() => {
              const current = batches.find((b) => b.id === selectedBatchId) || batches[0];
              if (current) handleOpenSplitModal(current);
            }}
            disabled={!canSplitMerge}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold border transition ${
              canSplitMerge
                ? 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 shadow-sm'
                : 'bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed opacity-60'
            }`}
            title={canSplitMerge ? 'Tách 1 lô mẹ thành nhiều lô con' : 'Chỉ HTX Sơ chế và Nhà phân phối mới được tách lô'}
          >
            <GitFork className="w-4 h-4" />
            Tách Lô (S-17)
          </button>

          {/* Nút Gộp Lô */}
          <button
            onClick={handleOpenMergeModal}
            disabled={!canSplitMerge}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold border transition ${
              canSplitMerge
                ? 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 shadow-sm'
                : 'bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed opacity-60'
            }`}
            title={canSplitMerge ? 'Gộp nhiều lô cùng sản phẩm' : 'Chỉ HTX Sơ chế và Nhà phân phối mới được gộp lô'}
          >
            <GitMerge className="w-4 h-4" />
            Gộp Lô (S-19)
          </button>

          {/* Nút Mô phỏng Chu Trình */}
          <button
            onClick={handleSimulateCycleError}
            className="flex items-center gap-1 px-2.5 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition"
            title="Thử nghiệm thuật toán phát hiện chu trình vòng lặp"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            Mô phỏng Chu Trình (S-28)
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

      {errorMsg && (
        <div className="flex items-start justify-between gap-3 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span className="font-semibold">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-500 hover:text-rose-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Cảnh báo Phát hiện Chu trình (Cycle Detection Alert Banner - S-28) */}
      {cycleError && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-red-600 to-rose-700 text-white shadow-lg shadow-rose-600/20 border border-rose-500 animate-pulse">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="p-2 rounded-xl bg-white/20 backdrop-blur-md">
                <AlertTriangle className="w-6 h-6 text-white" />
              </span>
              <div>
                <h4 className="text-sm font-bold tracking-wide uppercase">
                  Cảnh báo: Phát hiện Chu Trình Vòng Lặp Phả Hệ (DAG Violation)
                </h4>
                <p className="text-xs text-rose-100 mt-1 leading-relaxed">
                  {cycleError}
                </p>
                <div className="mt-2 text-[11px] bg-black/20 px-3 py-1.5 rounded-lg inline-block text-rose-200">
                  Thuật toán BFS/DFS đã ngăn chặn tình trạng đệ quy vô hạn và tự động khóa cách ly dữ liệu hỏng.
                </div>
              </div>
            </div>
            <button
              onClick={() => setCycleError(null)}
              className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Hộp Đáp án đếm tay để đối chiếu (Hand-counted Answer Key - S-22 / S-39) */}
      {(showAnswerKey || seedResult) && (
        <div className="bg-white rounded-2xl border border-teal-200 shadow-md p-5 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-teal-50 rounded-full blur-2xl -z-0"></div>
          <div className="relative z-10">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-teal-100 text-teal-700 font-bold text-xs">
                  S-22 / S-39
                </span>
                <h3 className="text-sm font-bold text-slate-900">
                  Bảng Đáp Án Đếm Tay Đối Chiếu Bộ Dữ Liệu Mẫu (13 Lô • 4 Tổ Chức)
                </h3>
              </div>
              <button
                onClick={() => setShowAnswerKey(!showAnswerKey)}
                className="text-xs text-slate-500 hover:text-slate-800 font-medium"
              >
                {showAnswerKey ? 'Thu gọn' : 'Mở rộng đối chiếu'}
              </button>
            </div>

            {showAnswerKey && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 text-xs">
                {/* Kịch bản 1: Lô gộp MERGE-TOM-M1 */}
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between font-bold text-slate-800">
                    <span>1. Lô Gộp MERGE-TOM-M1</span>
                    <button
                      onClick={() => {
                        const b = batches.find((x) => x.batch_code === 'MERGE-TOM-M1');
                        if (b) setSelectedBatchId(b.id);
                      }}
                      className="text-[11px] text-teal-600 hover:underline font-semibold"
                    >
                      Xem ngay ➔
                    </button>
                  </div>
                  <ul className="space-y-1 text-slate-600">
                    <li>• <strong>Truy ngược gốc:</strong> 2 lô gốc (<code className="text-emerald-700">ROOT-TOM-01</code> & <code className="text-emerald-700">ROOT-CHERRY-02</code>)</li>
                    <li>• <strong>Tổ tiên trực tiếp:</strong> 2 lô (<code className="text-blue-700">CHILD-TOM-1B</code> & <code className="text-emerald-700">ROOT-CHERRY-02</code>)</li>
                    <li>• <strong>Hậu duệ trực tiếp:</strong> 3 lô (<code className="text-purple-700">RETAIL-01</code>, <code className="text-purple-700">RETAIL-02</code>, <code className="text-purple-700">STOCK-BACKUP</code>)</li>
                    <li>• <strong>Còn trên kệ / tồn kho:</strong> <span className="font-bold text-amber-700">350.0 kg</span> (150kg Cầu Giấy + 200kg Kho)</li>
                    <li>• <strong>Đã bán cho tiêu dùng:</strong> <span className="font-bold text-emerald-700">850.0 kg</span> (400kg Q1 + 450kg Cầu Giấy)</li>
                  </ul>
                </div>

                {/* Kịch bản 2: Lô gốc ROOT-TOM-01 */}
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between font-bold text-slate-800">
                    <span>2. Lô Gốc ROOT-TOM-01</span>
                    <button
                      onClick={() => {
                        const b = batches.find((x) => x.batch_code === 'ROOT-TOM-01');
                        if (b) setSelectedBatchId(b.id);
                      }}
                      className="text-[11px] text-teal-600 hover:underline font-semibold"
                    >
                      Xem ngay ➔
                    </button>
                  </div>
                  <ul className="space-y-1 text-slate-600">
                    <li>• <strong>Cấp độ:</strong> Lô thu hoạch gốc tại Thửa A1 (HTX Thắng Lợi)</li>
                    <li>• <strong>Truy ngược:</strong> 0 lô cha (Chính nó là Gốc rễ ban đầu)</li>
                    <li>• <strong>Truy xuôi hậu duệ:</strong> <span className="font-bold text-blue-700">8 lô</span> (Child 1A, 1B ➔ Merge M1, M2 ➔ Retail 1, 2, 3, Stock)</li>
                    <li>• <strong>Số tổ chức liên quan:</strong> 4 tổ chức trong chuỗi cung ứng</li>
                  </ul>
                </div>

                {/* Kịch bản 3: Thử nghiệm Thu Hồi MERGE-TOM-M1 */}
                <div className="p-3.5 rounded-xl bg-rose-50/70 border border-rose-200 space-y-2">
                  <div className="flex items-center justify-between font-bold text-rose-900">
                    <span>3. Kịch bản Thu hồi (E-06)</span>
                    <span className="text-[10px] bg-rose-100 text-rose-700 px-2 py-0.5 rounded-md font-bold">
                      S-33 ➔ S-38
                    </span>
                  </div>
                  <ul className="space-y-1 text-rose-800">
                    <li>• <strong>Lô kích hoạt sự cố:</strong> <code className="text-rose-900">MERGE-TOM-M1</code></li>
                    <li>• <strong>Số lô bị khoanh vùng:</strong> <span className="font-bold">4 lô</span> (M1 + 3 lô hậu duệ)</li>
                    <li>• <strong>Tổ chức cần xác nhận:</strong> 2 tổ chức (HTX Sơ Chế & BioMart)</li>
                    <li>• <strong>Khóa tức thì (S-38):</strong> Chặn Bàn giao, Tách, Gộp</li>
                    <li>• <strong>Số kg cần thu hồi:</strong> 350kg trên kệ, cảnh báo 850kg đã bán</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Thanh Chọn Lô & Bộ lọc */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm">
        <div className="flex items-center gap-3 flex-1 max-w-lg">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm theo mã lô hoặc tên sản phẩm..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
            />
          </div>
          <select
            value={selectedBatchId || ''}
            onChange={(e) => setSelectedBatchId(Number(e.target.value))}
            className="text-xs py-1.5 px-3 rounded-xl border border-slate-200 font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="" disabled>-- Chọn Lô Hàng Khảo Sát --</option>
            {filteredBatches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.batch_code} - {b.product_name} ({b.remaining_quantity} {b.unit}) {b.status === 'Bị phong tỏa thu hồi' ? '🔒' : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Tổng số lô: <strong>{batches.length}</strong></span>
          <span>•</span>
          <button
            onClick={() => {
              fetchBatches();
              if (selectedBatchId) fetchDagForBatch(selectedBatchId);
            }}
            className="flex items-center gap-1 text-slate-600 hover:text-emerald-700 font-medium"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Làm mới
          </button>
        </div>
      </div>

      {/* KHU VỰC HIỂN THỊ SƠ ĐỒ PHẢ HỆ DAG 3 CỘT (VISUAL 3-COLUMN DIRECTED GRAPH) */}
      {loadingDag ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center shadow-sm">
          <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto mb-3" />
          <div className="text-sm font-bold text-slate-800">Đang phân tích và dựng đồ thị phả hệ DAG...</div>
          <p className="text-xs text-slate-500 mt-1">
            Thuật toán BFS đang duyệt ngược về các lô gốc và duyệt xuôi toàn bộ cây hậu duệ.
          </p>
        </div>
      ) : dagData ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* CỘT 1: TỔ TIÊN & LÔ THU HOẠCH GỐC (UPSTREAM ROOTS - BFS S-21) - Chiếm 4 Cột */}
          <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold text-xs">
                  <ArrowLeft className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Tổ Tiên & Lô Thu Hoạch Gốc (Roots)
                  </h3>
                  <div className="text-[11px] text-slate-500">Truy ngược nguồn gốc BFS (S-21)</div>
                </div>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                {dagData.roots.length} Lô Gốc
              </span>
            </div>

            {dagData.roots.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-400">
                Lô hiện tại là Lô gốc ban đầu (không có lô mẹ phía trước).
              </div>
            ) : (
              <div className="space-y-3">
                {dagData.roots.map((root, idx) => (
                  <div
                    key={root.id}
                    className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/40 hover:bg-emerald-50 transition space-y-2 relative"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                        <Hash className="w-3.5 h-3.5 text-emerald-600" />
                        {root.batch_code}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-200/70 text-emerald-900">
                        Cấp {root.generation_depth} (Gốc rễ)
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-slate-800">{root.product_name}</div>

                    <div className="space-y-1 text-[11px] text-slate-600 border-t border-emerald-200/60 pt-2">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Vùng trồng: <strong>{root.farm_name}</strong></span>
                      </div>
                      {root.land_plot_name && (
                        <div className="flex items-center gap-1.5">
                          <Store className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Thửa đất: {root.land_plot_name}</span>
                        </div>
                      )}
                      {root.land_plot_address && (
                        <div className="text-[10px] text-slate-500 italic pl-5">
                          {root.land_plot_address}
                        </div>
                      )}
                      <div className="flex items-center justify-between text-[11px] pt-1 font-medium">
                        <span>Sản lượng gốc: {root.initial_quantity} {root.unit}</span>
                        <span className="text-slate-500">Còn lại: {root.remaining_quantity} {root.unit}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => setSelectedBatchId(root.id)}
                      className="w-full mt-2 py-1 text-[11px] text-center text-emerald-800 hover:text-emerald-950 font-semibold bg-white/70 hover:bg-white rounded-lg border border-emerald-200/80 transition"
                    >
                      Dời tâm điểm DAG sang lô này
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Các mắt xích trung gian Ancestors */}
            {dagData.ancestors && dagData.ancestors.length > 0 && (
              <div className="pt-2 border-t border-slate-100">
                <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                  Lô Trung Gian Chuyển Tiếp ({dagData.ancestors.length})
                </div>
                <div className="space-y-2">
                  {dagData.ancestors.map((anc) => (
                    <div
                      key={anc.id}
                      onClick={() => setSelectedBatchId(anc.id)}
                      className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 cursor-pointer transition flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="font-mono font-bold text-slate-800">{anc.batch_code}</div>
                        <div className="text-[11px] text-slate-500">{anc.holding_org_name}</div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* CỘT 2: LÔ HÀNG ĐANG KHẢO SÁT (FOCUS BATCH) - Chiếm 4 Cột */}
          <div className="lg:col-span-4 bg-white rounded-2xl border-2 border-emerald-500/80 shadow-md p-5 space-y-4 relative">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-sm shadow-emerald-500/30">
                  <Sparkles className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Lô Trung Tâm Đang Chọn
                  </h3>
                  <div className="text-[11px] text-slate-500">Mã định danh duy nhất CSPRNG</div>
                </div>
              </div>
              {dagData.focus_batch.status === 'Bị phong tỏa thu hồi' ? (
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-300 flex items-center gap-1">
                  <Lock className="w-3 h-3 text-rose-600" />
                  Phong tỏa (S-38)
                </span>
              ) : (
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Hoạt động
                </span>
              )}
            </div>

            {/* Chi tiết Lô Trung Tâm */}
            <div className="bg-gradient-to-b from-slate-50 to-emerald-50/20 p-4 rounded-xl border border-slate-200/80 space-y-3">
              <div className="text-center pb-2 border-b border-slate-200/60">
                <span className="text-xs text-slate-400 font-medium">MÃ LÔ TIÊU CHUẨN</span>
                <div className="font-mono text-xl font-extrabold text-slate-900 tracking-wider">
                  {dagData.focus_batch.batch_code}
                </div>
                <div className="text-xs font-semibold text-emerald-800 mt-1">
                  {dagData.focus_batch.product_name}
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Tổ chức nắm giữ:</span>
                  <span className="font-bold text-slate-800">{dagData.focus_batch.holding_org_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Khối lượng còn lại:</span>
                  <span className="font-extrabold text-slate-900 text-sm">
                    {dagData.focus_batch.remaining_quantity} {dagData.focus_batch.unit}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Trạng thái kho:</span>
                  <span className="font-medium text-slate-700">{dagData.focus_batch.status}</span>
                </div>
                {dagData.focus_batch.location && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Vị trí hiện tại:</span>
                    <span className="font-medium text-slate-700">{dagData.focus_batch.location}</span>
                  </div>
                )}
              </div>

              {/* Nút hành động nhanh cho Lô Trung Tâm */}
              <div className="pt-2 border-t border-slate-200/60 space-y-2">
                <button
                  onClick={() => {
                    const b = batches.find((x) => x.id === dagData.focus_batch.id);
                    if (b) handleOpenSplitModal(b);
                  }}
                  disabled={!canSplitMerge || dagData.focus_batch.status === 'Bị phong tỏa thu hồi'}
                  className="w-full py-2 rounded-xl text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
                >
                  <GitFork className="w-4 h-4" />
                  Tách Lô Này Thành Các Lô Con (S-17)
                </button>
              </div>
            </div>

            {/* Thông tin xác thực Hash Chain */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-[11px] text-slate-600 space-y-1">
              <div className="font-semibold text-slate-800 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Chuỗi Hash SHA-256 Hợp Lệ
              </div>
              <p>Mỗi lần Tách/Gộp đều ghi nhận mắt xích mã hóa kèm con dấu thời gian UTC không thể làm giả.</p>
            </div>
          </div>

          {/* CỘT 3: HẬU DUỆ PHÂN PHỐI & BÁN LẺ (DESCENDANTS - BFS S-26, S-27) - Chiếm 4 Cột */}
          <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-xs">
                  <ArrowRight className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Hậu Duệ Phân Phối (Descendants)
                  </h3>
                  <div className="text-[11px] text-slate-500">Truy xuôi BFS điểm bán & số lượng (S-26, S-27)</div>
                </div>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 border border-teal-200">
                {dagData.descendants.length} Hậu Duệ
              </span>
            </div>

            {dagData.descendants.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-400">
                Lô này chưa phát sinh lô con hoặc chưa phân phối tiếp xuống chuỗi bán lẻ.
              </div>
            ) : (
              <div className="space-y-3">
                {dagData.descendants.map((desc) => (
                  <div
                    key={desc.id}
                    className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition space-y-2 relative"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-900 flex items-center gap-1.5">
                        <Hash className="w-3.5 h-3.5 text-teal-600" />
                        {desc.batch_code}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                        {desc.generation} (Cấp {desc.generation_level})
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-slate-800">{desc.product_name}</div>

                    <div className="space-y-1 text-[11px] text-slate-600 border-t border-slate-200/60 pt-2">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>Đang giữ: <strong>{desc.holding_organization.name}</strong></span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Store className="w-3.5 h-3.5 text-slate-400" />
                        <span>Điểm bán / kho: {desc.current_location}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] pt-1">
                        <span className="font-bold text-slate-800">
                          Trên kệ / Kho: {desc.remaining_quantity} {desc.unit}
                        </span>
                        <span className={desc.is_depleted ? 'text-rose-600 font-semibold' : 'text-emerald-700 font-semibold'}>
                          {desc.is_depleted ? 'Đã bán hết' : 'Đang bày bán'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => setSelectedBatchId(desc.id)}
                      className="w-full mt-2 py-1 text-[11px] text-center text-teal-800 hover:text-teal-950 font-semibold bg-white hover:bg-slate-100 rounded-lg border border-slate-200 transition"
                    >
                      Dời tâm điểm DAG sang lô con này
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* ========================================================================= */}
      {/* MODAL 1: TÁCH LÔ NÔNG SẢN (SPLIT BATCH MODAL - S-17, S-18) */}
      {/* ========================================================================= */}
      {showSplitModal && targetSplitBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-blue-50 text-blue-600 font-bold">
                  <GitFork className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Tách Lô Hàng Nông Sản (User Story S-17)
                  </h3>
                  <div className="text-xs text-slate-500">Khóa dòng chống tranh chấp đồng thời (SELECT FOR UPDATE)</div>
                </div>
              </div>
              <button
                onClick={() => setShowSplitModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-blue-50/60 rounded-xl border border-blue-200 text-xs text-blue-900 space-y-1">
              <div className="flex justify-between">
                <span>Lô mẹ nguồn: <strong>{targetSplitBatch.batch_code}</strong></span>
                <span>Sản phẩm: <strong>{targetSplitBatch.product_name}</strong></span>
              </div>
              <div className="flex justify-between font-bold text-blue-950">
                <span>Khối lượng còn lại: {targetSplitBatch.remaining_quantity} {targetSplitBatch.unit}</span>
                <span>
                  Tổng lượng tách:{' '}
                  {splitChildren.reduce((sum, item) => sum + (parseFloat(item.quantity) || 0), 0)}{' '}
                  {targetSplitBatch.unit}
                </span>
              </div>
            </div>

            <form onSubmit={submitSplitBatch} className="space-y-4">
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {splitChildren.map((child, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-xs"
                  >
                    <span className="font-bold text-slate-500 w-6 text-center">#{idx + 1}</span>
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Mục đích / Ghi chú lô con..."
                        value={child.notes}
                        onChange={(e) => handleUpdateSplitNote(idx, e.target.value)}
                        className="w-full px-2.5 py-1 rounded-lg border border-slate-200 text-xs"
                      />
                    </div>
                    <div className="w-28 flex items-center gap-1">
                      <input
                        type="number"
                        step="any"
                        min="0.1"
                        placeholder="Số lượng"
                        value={child.quantity}
                        onChange={(e) => handleUpdateSplitQty(idx, e.target.value)}
                        className="w-full px-2 py-1 rounded-lg border border-slate-200 text-xs font-bold text-right"
                        required
                      />
                      <span className="text-slate-500 font-medium">{targetSplitBatch.unit}</span>
                    </div>
                    {splitChildren.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveSplitRow(idx)}
                        className="p-1 text-slate-400 hover:text-rose-600 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={handleAddSplitRow}
                  className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline"
                >
                  + Thêm Lô Con Khác
                </button>
                <div className="text-[11px] text-slate-400">
                  Mã 8 ký tự CSPRNG sẽ được tự động tạo ngẫu nhiên.
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowSplitModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={splitSubmitting}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 disabled:opacity-50"
                >
                  {splitSubmitting ? 'Đang Khóa Dòng & Tách Lô...' : 'Xác Nhận Tách Lô'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: GỘP LÔ NÔNG SẢN (MERGE BATCHES MODAL - S-19, S-20) */}
      {/* ========================================================================= */}
      {showMergeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-purple-50 text-purple-600 font-bold">
                  <GitMerge className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Gộp Nhiều Lô Nông Sản Thành Lô Mới (User Story S-19)
                  </h3>
                  <div className="text-xs text-slate-500">Khóa theo thứ tự ID cố định (ORDER BY id ASC) chống deadlock</div>
                </div>
              </div>
              <button
                onClick={() => setShowMergeModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Chọn các lô hàng của tổ chức bạn có <strong>CÙNG LOẠI SẢN PHẨM</strong> để phối trộn hoặc đóng gói thành lô thành phẩm mới.
            </p>

            {/* Danh sách các lô để chọn gộp */}
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {batches
                .filter((b) => b.remaining_quantity > 0 && b.status !== 'Bị phong tỏa thu hồi')
                .map((b) => {
                  const isSelected = mergeSelectedBatches.some((s) => s.batch_id === b.id);
                  return (
                    <div
                      key={b.id}
                      onClick={() => toggleSelectMergeBatch(b)}
                      className={`p-2.5 rounded-xl border cursor-pointer text-xs flex items-center justify-between transition ${
                        isSelected
                          ? 'border-purple-500 bg-purple-50/50'
                          : 'border-slate-200 bg-slate-50 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="rounded text-purple-600 focus:ring-purple-500"
                        />
                        <div>
                          <span className="font-mono font-bold text-slate-900">{b.batch_code}</span>
                          <span className="text-slate-500 ml-2">({b.product_name})</span>
                        </div>
                      </div>
                      <span className="font-bold text-slate-700">
                        Còn: {b.remaining_quantity} {b.unit}
                      </span>
                    </div>
                  );
                })}
            </div>

            {/* Bảng nhập khối lượng trích gộp từ từng lô */}
            {mergeSelectedBatches.length > 0 && (
              <div className="p-3 bg-purple-50 rounded-xl border border-purple-200 space-y-2">
                <div className="text-xs font-bold text-purple-900">
                  Các Lô Được Chọn Gộp ({mergeSelectedBatches.length} lô):
                </div>
                {mergeSelectedBatches.map((item) => (
                  <div key={item.batch_id} className="flex items-center justify-between gap-2 text-xs">
                    <span className="font-mono font-semibold text-purple-950">
                      {item.batch_code} (Tối đa {item.max_qty} {item.unit})
                    </span>
                    <div className="flex items-center gap-1 w-32">
                      <input
                        type="number"
                        step="any"
                        min="0.1"
                        max={item.max_qty}
                        value={item.quantity}
                        onChange={(e) => handleUpdateMergeQty(item.batch_id, e.target.value)}
                        className="w-full px-2 py-1 rounded-lg border border-purple-200 text-right font-bold text-xs"
                      />
                      <span className="text-purple-800">{item.unit}</span>
                    </div>
                  </div>
                ))}
                <div className="pt-2 border-t border-purple-200 flex justify-between font-extrabold text-xs text-purple-950">
                  <span>TỔNG KHỐI LƯỢNG LÔ MỚI:</span>
                  <span>
                    {mergeSelectedBatches.reduce((sum, b) => sum + (parseFloat(b.quantity) || 0), 0)}{' '}
                    {mergeSelectedBatches[0]?.unit}
                  </span>
                </div>
              </div>
            )}

            <form onSubmit={submitMergeBatches} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Ghi Chú Gộp Lô:</label>
                <input
                  type="text"
                  value={mergeNotes}
                  onChange={(e) => setMergeNotes(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl border border-slate-200 text-xs"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowMergeModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={mergeSubmitting || mergeSelectedBatches.length < 2}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 shadow-md shadow-purple-500/20 disabled:opacity-50"
                >
                  {mergeSubmitting ? 'Đang Gộp Lô...' : 'Xác Nhận Gộp Lô Mới'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
