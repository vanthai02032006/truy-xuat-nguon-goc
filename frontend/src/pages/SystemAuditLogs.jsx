import React, { useState, useEffect } from 'react';
import { useAuthRole } from '../context/AuthRoleContext';
import { Shield, ShieldAlert, Lock, RefreshCw, AlertTriangle, CheckCircle2, Search } from 'lucide-react';

export default function SystemAuditLogs({ onRedirectHome }) {
  const { currentRole, currentUser } = useAuthRole();
  const isAdmin = ['system_admin', 'admin'].includes(currentRole) || 
                  (currentUser && ['system_admin', 'admin'].includes(currentUser?.role));

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterText, setFilterText] = useState('');

  const fetchLogs = async () => {
    if (!isAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/audit/security-logs?limit=100', {
        headers: {
          'Content-Type': 'application/json',
          ...(localStorage.getItem('token')
            ? { Authorization: `Bearer ${localStorage.getItem('token')}` }
            : {}),
        },
      });

      if (res.status === 403) {
        throw new Error('HTTP 403 Forbidden: Tài khoản không có quyền xem nhật ký bảo mật!');
      }
      if (!res.ok) {
        throw new Error(`Lỗi nạp nhật ký: ${res.statusText}`);
      }

      const data = await res.json();
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      fetchLogs();
    }
  }, [isAdmin, currentRole]);

  // Nếu người dùng không phải Quản trị viên, hiển thị màn hình thông báo không có quyền
  if (!isAdmin) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center max-w-xl mx-auto my-12">
        <div className="w-16 h-16 bg-rose-100 rounded-full flex items-center justify-center mx-auto mb-4 text-rose-600">
          <Lock className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-800 mb-2">Quyền Truy Cập Bị Hạn Chế</h3>
        <p className="text-sm text-slate-600 mb-6">
          Chức năng <strong>Nhật Ký Hệ Thống (S-31)</strong> chỉ dành riêng cho Quản trị viên hệ thống (system_admin).
          Tài khoản của bạn ({currentRole}) không có quyền truy cập thông tin bảo mật này.
        </p>
        <button
          onClick={onRedirectHome}
          className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition shadow-sm"
        >
          Quay lại Trang Chủ
        </button>
      </div>
    );
  }

  const filteredLogs = logs.filter((log) => {
    const q = filterText.toLowerCase();
    return (
      (log.attempt_type || '').toLowerCase().includes(q) ||
      (log.description || '').toLowerCase().includes(q) ||
      (log.user_email || '').toLowerCase().includes(q) ||
      (log.endpoint || '').toLowerCase().includes(q) ||
      (log.ip_address || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-5 h-5 text-indigo-400" />
            <h2 className="text-xl font-black tracking-tight">Nhật Ký An Ninh & Kiểm Toán Hệ Thống (S-31)</h2>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
              Admin Exclusive
            </span>
          </div>
          <p className="text-xs text-slate-300 font-medium">
            Ghi nhận toàn bộ sự kiện an ninh, cảnh báo truy cập chéo tổ chức và can thiệp trái phép theo tiêu chuẩn bảo mật ISO 27001 & Nghị định 13.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          disabled={loading}
          className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-md active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Làm Mới
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="flex items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Tìm theo sự kiện, email, endpoint, IP..."
            className="w-full text-xs pl-9 pr-4 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
        </div>
        <div className="text-xs font-bold text-slate-500">
          Tổng cộng: <span className="text-indigo-600 font-mono">{filteredLogs.length}</span> bản ghi
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] tracking-wider font-bold border-b border-slate-200">
              <tr>
                <th className="p-3.5">ID</th>
                <th className="p-3.5">Thời Gian</th>
                <th className="p-3.5">Loại Sự Kiện</th>
                <th className="p-3.5">Người Thao Tác</th>
                <th className="p-3.5">Phương Thức & Endpoint</th>
                <th className="p-3.5">Địa Chỉ IP</th>
                <th className="p-3.5">Chi Tiết / Mô Tả</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="p-8 text-center text-slate-400 font-medium">
                    Đang nạp dữ liệu nhật ký hệ thống...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="p-8 text-center text-slate-400 font-medium">
                    Chưa có sự kiện an ninh nào được ghi nhận.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => {
                  const isSuspicious =
                    log.attempt_type?.includes('denied') ||
                    log.attempt_type?.includes('violation') ||
                    log.attempt_type?.includes('cross_tenant');
                  return (
                    <tr key={log.id} className="hover:bg-slate-50/60 transition">
                      <td className="p-3.5 font-mono text-slate-500 font-semibold">{log.id}</td>
                      <td className="p-3.5 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                        {log.created_at ? new Date(log.created_at).toLocaleString('vi-VN') : '—'}
                      </td>
                      <td className="p-3.5">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            isSuspicious
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                          }`}
                        >
                          {isSuspicious ? (
                            <ShieldAlert className="w-3 h-3 text-rose-600" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3 text-indigo-600" />
                          )}
                          {log.attempt_type}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <div className="font-bold text-slate-800">{log.user_email || 'Hệ thống'}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          Org ID: {log.user_org_id || 'N/A'}
                        </div>
                      </td>
                      <td className="p-3.5">
                        <span className="font-mono text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded font-bold mr-1.5">
                          {log.method}
                        </span>
                        <span className="font-mono text-slate-600 text-[11px]">{log.endpoint}</span>
                      </td>
                      <td className="p-3.5 font-mono text-slate-500 text-[11px]">{log.ip_address || '127.0.0.1'}</td>
                      <td className="p-3.5 text-slate-600 max-w-xs truncate" title={log.description}>
                        {log.description}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
