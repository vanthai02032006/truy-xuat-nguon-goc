import React, { useState } from 'react';
import { useAuthRole } from '../context/AuthRoleContext';
import { Shield, Lock, Mail, Eye, EyeOff, ArrowRight, UserCheck, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const { login, loginAsConsumer, authError } = useAuthRole();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState(null);

  const demoAccounts = [
    {
      role: 'Quản trị hệ thống (System Admin)',
      email: 'sysadmin@nongsanlanh.gov.vn',
      desc: 'Toàn quyền cấu hình, bảo mật và audit log',
      badge: 'bg-purple-100 text-purple-800 border-purple-200',
    },
    {
      role: 'Vùng trồng (Farm)',
      email: 'manager@nongtraixanh.vn',
      desc: 'Khai báo lô thu hoạch, thửa đất và nhật ký canh tác',
      badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    },
    {
      role: 'HTX Sơ chế / Chế biến (Coop)',
      email: 'operator@sochebaoloc.vn',
      desc: 'Tách lô, gộp lô và đóng gói sơ chế',
      badge: 'bg-blue-100 text-blue-800 border-blue-200',
    },
    {
      role: 'Vận tải lạnh (Logistics)',
      email: 'driver@coldexpress.vn',
      desc: 'Giám sát hành trình và nhiệt độ cảm biến IoT',
      badge: 'bg-amber-100 text-amber-800 border-amber-200',
    },
    {
      role: 'Nhà phân phối / Bán lẻ (Distributor)',
      email: 'store@biomart.vn',
      desc: 'Phân phối chuỗi bán lẻ và ghi nhận bán hết',
      badge: 'bg-teal-100 text-teal-800 border-teal-200',
    },
    {
      role: 'Cán bộ kiểm tra (Inspector)',
      email: 'inspector.safe@kiemdinh.gov.vn',
      desc: 'Kiểm tra toàn chuỗi, mở lệnh thu hồi khẩn cấp',
      badge: 'bg-rose-100 text-rose-800 border-rose-200',
    },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setLocalError('Vui lòng nhập đầy đủ email và mật khẩu.');
      return;
    }
    setLocalError(null);
    setIsSubmitting(true);
    try {
      const res = await login(email.trim(), password);
      if (!res.success) {
        setLocalError(res.error);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFillDemo = (demoEmail) => {
    setEmail(demoEmail);
    setPassword('pass123');
    setLocalError(null);
  };

  const displayError = localError || authError;

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center p-4 selection:bg-emerald-500 selection:text-white">
      {/* Background Glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-100 p-8 z-10">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-lg text-2xl">
            🌿
          </div>
          <h1 className="text-xl font-black text-slate-900 tracking-tight">
            Truy Xuất Nguồn Gốc & Chuỗi Lạnh
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Đăng nhập hệ thống bảo mật bằng Cookie HttpOnly
          </p>
        </div>

        {/* Error Alert */}
        {displayError && (
          <div className="mb-6 p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-700 animate-shake">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="font-semibold leading-relaxed">{displayError}</div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Email tài khoản
            </label>
            <div className="relative">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@organization.vn"
                className="w-full pl-10 pr-3 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition font-medium"
              />
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3 pointer-events-none" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Mật khẩu
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-10 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition font-medium"
              />
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3 pointer-events-none" />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                tabIndex="-1"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] text-white rounded-xl text-sm font-bold shadow-lg shadow-emerald-600/30 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {isSubmitting ? (
              <span>Đang xác thực...</span>
            ) : (
              <>
                <span>Đăng nhập hệ thống</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Consumer Guest Trace Option */}
        <div className="mt-4 pt-4 border-t border-slate-100 text-center">
          <button
            type="button"
            onClick={loginAsConsumer}
            className="w-full py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer"
          >
            <UserCheck className="w-4 h-4 text-emerald-600" />
            <span>Chế độ Người tiêu dùng (Tra cứu công khai)</span>
          </button>
        </div>

        {/* Quick Demo Accounts Selection */}
        <div className="mt-6 pt-6 border-t border-slate-100">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
            <Shield className="w-3.5 h-3.5 text-slate-400" />
            <span>Tài khoản mẫu thử nghiệm (Mật khẩu: pass123)</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-left">
            {demoAccounts.map((acc, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleFillDemo(acc.email)}
                className="p-2 rounded-lg border border-slate-200 hover:border-emerald-500 hover:bg-emerald-50/40 text-left transition text-[11px] group cursor-pointer"
                title={`${acc.role} - Click để điền tự động`}
              >
                <div className="font-bold text-slate-800 truncate group-hover:text-emerald-700">
                  {acc.role.split('(')[0].trim()}
                </div>
                <div className="text-[10px] text-slate-500 truncate">{acc.email}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="text-center mt-6 text-xs text-slate-400 font-medium">
        Hệ thống chuẩn an toàn Nghị định 13/2023/NĐ-CP • Khóa tài khoản sau 5 lần đăng nhập sai
      </div>
    </div>
  );
}
