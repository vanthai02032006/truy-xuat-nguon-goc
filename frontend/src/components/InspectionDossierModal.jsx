import React, { useState, useEffect } from 'react';
import {
  FileText,
  Printer,
  ShieldCheck,
  ShieldAlert,
  Hash,
  ThermometerSnowflake,
  Network,
  AlertTriangle,
  UserCheck,
  X,
  Copy,
  Check,
  Clock,
  Building,
  Calendar,
  Layers,
} from 'lucide-react';
import { useAuthRole } from '../context/AuthRoleContext';

export default function InspectionDossierModal({ batchId, isOpen, onClose }) {
  const { authFetch } = useAuthRole();
  const [loading, setLoading] = useState(true);
  const [dossier, setDossier] = useState(null);
  const [error, setError] = useState(null);
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (isOpen && batchId) {
      fetchDossier();
    }
  }, [isOpen, batchId]);

  const fetchDossier = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/api/v1/batches/${batchId}/inspection-dossier`);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Không thể tải hồ sơ kiểm tra.');
      }
      const data = await res.json();
      setDossier(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleCopyHash = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 print:p-0 print:bg-white print:fixed-none">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh] print:max-h-none print:shadow-none print:border-none print:rounded-none">
        {/* Modal Controls (Hidden in Print) */}
        <div className="px-6 py-3.5 bg-slate-800 text-white flex items-center justify-between print:hidden">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-400" />
            <span className="font-bold text-sm">Hồ Sơ Kiểm Tra Truy Xuất Nguồn Gốc (S-52, S-53)</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
              Bản In / PDF
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              disabled={loading || !dossier}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg transition shadow-sm"
            >
              <Printer className="w-4 h-4" />
              In Hồ Sơ / Lưu PDF
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body / Printable Document */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 bg-slate-50/50 print:bg-white print:p-0 print:overflow-visible">
          {loading && (
            <div className="py-16 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-emerald-500 border-t-transparent mb-3" />
              <p className="text-sm font-medium text-slate-600">Đang tổng hợp dữ liệu hồ sơ và xác thực chuỗi Hash SHA-256...</p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-center gap-3">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!loading && dossier && (
            <div className="bg-white p-6 sm:p-10 rounded-xl border border-slate-200/80 shadow-sm print:border-none print:shadow-none print:p-0">
              {/* Header Quốc hiệu / Tiêu ngữ */}
              <div className="text-center border-b pb-5 mb-6 border-slate-200">
                <p className="text-xs font-bold tracking-widest uppercase text-slate-600">
                  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
                </p>
                <p className="text-xs font-bold text-slate-700 underline decoration-slate-400 underline-offset-4">
                  Độc lập - Tự do - Hạnh phúc
                </p>
                <div className="mt-4">
                  <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 uppercase tracking-tight">
                    HỒ SƠ KIỂM TRA TRUY XUẤT NGUỒN GỐC & CHUỖI CUNG ỨNG
                  </h1>
                  <p className="text-xs text-slate-500 font-mono mt-1">
                    Mã hồ sơ: <span className="font-bold text-slate-800">{dossier.export_metadata.official_dossier_code}</span> • 
                    Thời điểm xuất: {new Date(dossier.export_metadata.exported_at).toLocaleString('vi-VN')}
                  </p>
                </div>
              </div>

              {/* Box Toàn vẹn chuỗi Hash (S-12, S-53) */}
              <div
                className={`p-4 rounded-xl border mb-6 ${
                  dossier.integrity_verification.valid
                    ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50/80 border-rose-200 text-rose-900'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        dossier.integrity_verification.valid ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
                      }`}
                    >
                      {dossier.integrity_verification.valid ? (
                        <ShieldCheck className="w-6 h-6" />
                      ) : (
                        <ShieldAlert className="w-6 h-6" />
                      )}
                    </div>
                    <div>
                      <div className="text-sm font-bold flex items-center gap-2">
                        CHỨNG CHỈ TOÀN VẸN MÃ HÓA SHA-256
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-extrabold uppercase ${
                            dossier.integrity_verification.valid
                              ? 'bg-emerald-200 text-emerald-900'
                              : 'bg-rose-200 text-rose-900'
                          }`}
                        >
                          {dossier.integrity_verification.status_label}
                        </span>
                      </div>
                      <p className="text-xs opacity-90 mt-0.5">
                        {dossier.integrity_verification.message} • Đã xác thực tuần tự qua {dossier.integrity_verification.total_events} mắt xích sự kiện.
                      </p>
                    </div>
                  </div>

                  {/* Terminal Hash */}
                  <div className="bg-white/90 p-2.5 rounded-lg border border-slate-200 text-right print:text-left">
                    <div className="text-[10px] font-bold text-slate-500 uppercase flex items-center justify-end gap-1">
                      <Hash className="w-3 h-3" /> Mã Hash Cuối Chuỗi (Terminal Hash Đối Chiếu)
                    </div>
                    <div className="font-mono text-xs text-slate-800 font-bold flex items-center justify-end gap-1 mt-0.5">
                      <span className="truncate max-w-[200px]" title={dossier.integrity_verification.terminal_current_hash}>
                        {dossier.integrity_verification.terminal_current_hash}
                      </span>
                      <button
                        onClick={() => handleCopyHash(dossier.integrity_verification.terminal_current_hash)}
                        className="p-1 hover:bg-slate-100 rounded text-slate-500 transition print:hidden"
                        title="Sao chép toàn bộ Hash"
                      >
                        {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* 2-Column Grid: Thông tin lô & Vùng trồng */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {/* Thông tin lô hàng */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-3">
                    <Layers className="w-4 h-4 text-emerald-600" /> 1. Thông Tin Lô Hàng
                  </h3>
                  <dl className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-xs">
                    <dt className="text-slate-500">Mã lô:</dt>
                    <dd className="font-mono font-bold text-slate-900">{dossier.batch_info.batch_code}</dd>
                    <dt className="text-slate-500">Tên sản phẩm:</dt>
                    <dd className="font-bold text-slate-900">{dossier.batch_info.product_name}</dd>
                    <dt className="text-slate-500">Khối lượng ban đầu:</dt>
                    <dd className="font-medium text-slate-800">{dossier.batch_info.initial_quantity} {dossier.batch_info.unit}</dd>
                    <dt className="text-slate-500">Khối lượng còn lại:</dt>
                    <dd className="font-bold text-emerald-700">{dossier.batch_info.remaining_quantity} {dossier.batch_info.unit}</dd>
                    <dt className="text-slate-500">Trạng thái:</dt>
                    <dd className="font-medium capitalize text-slate-800">{dossier.batch_info.status}</dd>
                    <dt className="text-slate-500">Tổ chức quản lý:</dt>
                    <dd className="font-bold text-slate-900">{dossier.batch_info.organization_name}</dd>
                  </dl>
                </div>

                {/* Vùng trồng & Nông hộ (NĐ 13/2023) */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-3">
                    <UserCheck className="w-4 h-4 text-emerald-600" /> 2. Nguồn Gốc Vùng Trồng & Nông Hộ
                  </h3>
                  <dl className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-xs">
                    <dt className="text-slate-500">Tên / Bí danh:</dt>
                    <dd className="font-bold text-slate-900">{dossier.farmer_origin.display_name}</dd>
                    <dt className="text-slate-500">Mã tham chiếu:</dt>
                    <dd className="font-mono text-slate-700">{dossier.farmer_origin.farmer_ref_id || 'N/A'}</dd>
                    <dt className="text-slate-500">Tỉnh / Khu vực:</dt>
                    <dd className="font-medium text-slate-800">{dossier.farmer_origin.province}</dd>
                    <dt className="text-slate-500">Bảo vệ dữ liệu cá nhân:</dt>
                    <dd>
                      {dossier.farmer_origin.is_anonymized ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          Đã ẩn danh (NĐ 13/2023/NĐ-CP)
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
                          Đầy đủ danh tính
                        </span>
                      )}
                    </dd>
                    <dt className="text-slate-500">Địa chỉ cụ thể:</dt>
                    <dd className="text-slate-700 truncate">{dossier.farmer_origin.detail_address || 'Đã ẩn danh theo quy định'}</dd>
                  </dl>
                </div>
              </div>

              {/* 3. Lịch sử giám sát chuỗi lạnh & Vi phạm (S-40 -> S-45) */}
              <div className="mb-6 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <ThermometerSnowflake className="w-4 h-4 text-blue-600" /> 3. Giám Sát Chuỗi Lạnh & Bảo Quản (S-40 - S-45)
                  </h3>
                  {dossier.cold_chain.has_violations ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Phát hiện {dossier.cold_chain.violations_count} lần vi phạm nhiệt độ
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Chuỗi lạnh duy trì an toàn 100%
                    </span>
                  )}
                </div>

                {dossier.cold_chain.violations.length > 0 ? (
                  <div className="space-y-2 mt-2">
                    {dossier.cold_chain.violations.map((v, i) => (
                      <div key={i} className="p-3 bg-rose-50/70 border border-rose-200 rounded-lg text-xs text-rose-900 flex items-center justify-between">
                        <div>
                          <span className="font-bold">Xe {v.vehicle_code} (#{v.trip_code}):</span> Nhiệt độ đỉnh{' '}
                          <span className="font-bold text-rose-700">{v.peak_temperature}°C</span> vượt ngưỡng {v.threshold}°C liên tục{' '}
                          <span className="font-bold">{v.duration_minutes} phút</span>.
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">
                          {v.started_at ? new Date(v.started_at).toLocaleTimeString('vi-VN') : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">
                    Không ghi nhận vi phạm nhiệt độ bảo quản vượt ngưỡng 30 phút trong các chuyến vận chuyển.
                  </p>
                )}
              </div>

              {/* 4. Dòng thời gian sự kiện chuỗi khối SHA-256 (Timeline) */}
              <div className="mb-6">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-3">
                  <Hash className="w-4 h-4 text-emerald-600" /> 4. Dòng Thời Gian Sự Kiện Băm SHA-256 (Toàn Bộ Chuỗi Khối)
                </h3>
                <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-100/80 text-slate-600 font-bold border-b border-slate-200">
                        <th className="py-2.5 px-3 w-12 text-center">STT</th>
                        <th className="py-2.5 px-3 w-32">Thời Gian</th>
                        <th className="py-2.5 px-3 w-36">Loại Sự Kiện</th>
                        <th className="py-2.5 px-3">Nội Dung Chi Tiết</th>
                        <th className="py-2.5 px-3 w-44 font-mono text-[10px]">Mã Hash Hiện Tại</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {dossier.event_timeline.map((evt) => (
                        <tr key={evt.id} className="hover:bg-slate-50/70">
                          <td className="py-2 px-3 text-center font-bold text-slate-400">{evt.index}</td>
                          <td className="py-2 px-3 text-slate-600 font-mono text-[11px]">
                            {new Date(evt.created_at).toLocaleString('vi-VN')}
                          </td>
                          <td className="py-2 px-3">
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                              {evt.event_type}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-800">
                            <div>{evt.event_data}</div>
                            <div className="text-[10px] text-slate-400 mt-0.5">Thực hiện: {evt.organization_name}</div>
                          </td>
                          <td className="py-2 px-3 font-mono text-[10px] text-slate-500 truncate max-w-[150px]" title={evt.current_hash}>
                            {evt.current_hash.slice(0, 16)}...
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 5. Phả hệ tổ tiên & hậu duệ */}
              <div className="mb-6 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-2">
                  <Network className="w-4 h-4 text-emerald-600" /> 5. Phả Hệ Lô Hàng (Lineage DAG)
                </h3>
                <div className="grid grid-cols-2 gap-4 text-xs mt-2">
                  <div>
                    <span className="font-bold text-slate-700">Tổ tiên / Lô nguồn ({dossier.lineage.ancestor_count}):</span>
                    {dossier.lineage.ancestors.length > 0 ? (
                      <ul className="list-disc list-inside mt-1 space-y-0.5 text-slate-600 font-mono">
                        {dossier.lineage.ancestors.map((a, i) => (
                          <li key={i}>{a.batch_code} ({a.product_name})</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-400 italic mt-1">Lô gốc khởi nguyên (Không có cha/mẹ).</p>
                    )}
                  </div>
                  <div>
                    <span className="font-bold text-slate-700">Hậu duệ / Lô con ({dossier.lineage.descendant_count}):</span>
                    {dossier.lineage.descendants.length > 0 ? (
                      <ul className="list-disc list-inside mt-1 space-y-0.5 text-slate-600 font-mono">
                        {dossier.lineage.descendants.map((d, i) => (
                          <li key={i}>{d.batch_code} ({d.product_name}) - {d.status}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-400 italic mt-1">Chưa tách hoặc gộp thành lô con nào.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Signatures & Seal Section */}
              <div className="mt-8 pt-6 border-t border-slate-200 grid grid-cols-2 gap-8 text-center text-xs">
                <div>
                  <p className="font-bold text-slate-700 uppercase">ĐẠI DIỆN ĐƠN VỊ SẢN XUẤT / QUẢN LÝ</p>
                  <p className="text-[11px] text-slate-400 italic mt-0.5">(Ký, ghi rõ họ tên và đóng dấu)</p>
                  <div className="h-16" />
                  <p className="font-bold text-slate-800">{dossier.batch_info.organization_name}</p>
                </div>

                <div>
                  <p className="font-bold text-slate-700 uppercase">CÁN BỘ KIỂM TRA / CHỨNG THỰC HỆ THỐNG</p>
                  <p className="text-[11px] text-slate-400 italic mt-0.5">(Bảo chứng điện tử bằng hàm băm SHA-256)</p>
                  <div className="h-16 flex items-center justify-center">
                    <span className="px-3 py-1 rounded-lg border border-emerald-500/40 bg-emerald-50 text-emerald-800 font-bold font-mono text-[11px] flex items-center gap-1 shadow-sm">
                      🛡️ SHA-256 VERIFIED
                    </span>
                  </div>
                  <p className="font-bold text-slate-800">{dossier.export_metadata.inspector_name}</p>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">Chức danh: {dossier.export_metadata.inspector_role}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
