import React, { useState } from 'react';
import { AuthRoleProvider, useAuthRole, ROLES_LIST } from './context/AuthRoleContext';
import LoginPage from './components/LoginPage';
import ProductManagement from './pages/ProductManagement';
import ChainIntegrityCheck from './pages/ChainIntegrityCheck';
import BatchLineageDAG from './pages/BatchLineageDAG';
import EmergencyRecallManagement from './pages/EmergencyRecallManagement';
import ColdChainMonitoring from './pages/ColdChainMonitoring';
import FarmerPrivacyManagement from './pages/FarmerPrivacyManagement';
import SystemAuditLogs from './pages/SystemAuditLogs';
import InspectionDossierModal from './components/InspectionDossierModal';
import {
  Boxes,
  Hash,
  Network,
  Shield,
  ShieldAlert,
  ChevronDown,
  Building2,
  ThermometerSnowflake,
  UserCheck,
  FileText,
  LogOut,
  Loader2,
} from 'lucide-react';

function MainApp() {
  const [activeTab, setActiveTab] = useState('dag'); // Mặc định mở tab Phả hệ lô hàng (DAG)
  const {
    currentRole,
    activeRoleConfig,
    switchRole,
    isSwitching,
    currentUser,
    isAuthenticated,
    isLoading,
    logout,
  } = useAuthRole();
  const [showGlobalDossierModal, setShowGlobalDossierModal] = useState(false);
  const [targetBatchId, setTargetBatchId] = useState(1);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center text-white">
        <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mb-3" />
        <div className="text-sm font-semibold text-slate-300">Đang kiểm tra phiên làm việc bảo mật...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm print:hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between gap-4">
            {/* Logo & Platform Name */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md font-bold text-lg">
                🌿
              </div>
              <div>
                <div className="text-base font-bold text-slate-900 leading-tight flex items-center gap-2">
                  Hệ Thống Truy Xuất Nguồn Gốc Nông Sản
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Sprint 6, 7 & 8 Hoàn Thiện
                  </span>
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  Chuỗi Lạnh 5 Kịch Bản (S-42) • Hồ Sơ PDF (S-52) • Ẩn Danh PII NĐ 13 (S-56)
                </div>
              </div>
            </div>

            {/* Quick Action: Xuất Hồ Sơ Kiểm Tra (S-52) & 7-Role Switcher Widget & Logout */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowGlobalDossierModal(true)}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold shadow-sm transition active:scale-95"
                title="Xuất Hồ Sơ Kiểm Tra Truy Xuất Nguồn Gốc (PDF / Bản In)"
              >
                <FileText className="w-3.5 h-3.5 text-emerald-400" />
                <span>Xuất Hồ Sơ (PDF)</span>
              </button>

              <div className="hidden md:flex flex-col text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400">
                  Phiên làm việc (7 Vai trò)
                </span>
                <span className="text-xs font-bold text-slate-700 flex items-center justify-end gap-1">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" />
                  {currentUser?.full_name || activeRoleConfig.orgName}
                </span>
              </div>

              {/* Dropdown 7 Vai Trò */}
              <div className="relative">
                <select
                  value={currentRole || 'consumer'}
                  onChange={(e) => switchRole(e.target.value)}
                  disabled={isSwitching}
                  className={`text-xs font-bold py-1.5 pl-3 pr-8 rounded-xl border appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-500/20 shadow-sm transition ${activeRoleConfig.badgeColor}`}
                >
                  {ROLES_LIST.map((r) => (
                    <option key={r.id} value={r.id} className="bg-white text-slate-800 font-medium py-1">
                      {r.icon} {r.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 absolute right-2.5 top-2.5 pointer-events-none text-slate-500" />
              </div>

              {/* Nút Đăng Xuất An Toàn */}
              <button
                onClick={logout}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition active:scale-95 cursor-pointer shadow-sm"
                title="Đăng xuất khỏi hệ thống"
              >
                <LogOut className="w-3.5 h-3.5 text-rose-600" />
                <span className="hidden sm:inline">Đăng xuất</span>
              </button>
            </div>
          </div>

          {/* Navigation Tabs Bar */}
          <div className="flex items-center gap-2 overflow-x-auto py-2 border-t border-slate-100 scrollbar-none">
            <button

              onClick={() => setActiveTab('dag')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'dag'
                  ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Network className="w-4 h-4" />
              🌳 Phả Hệ Lô Hàng DAG (E-05)
            </button>

            <button
              onClick={() => setActiveTab('coldchain')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'coldchain'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <ThermometerSnowflake className="w-4 h-4" />
              ❄️ Chuỗi Lạnh 5 Kịch Bản (S-40 -&gt; S-45)
            </button>

            <button
              onClick={() => setActiveTab('recall')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'recall'
                  ? 'bg-rose-600 text-white shadow-sm shadow-rose-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              🚨 Thu Hồi Khẩn Cấp (E-06)
            </button>

            <button
              onClick={() => setActiveTab('farmer_privacy')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'farmer_privacy'
                  ? 'bg-teal-600 text-white shadow-sm shadow-teal-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <UserCheck className="w-4 h-4" />
              👤 Ẩn Danh Nông Hộ NĐ 13 (S-56)
            </button>

            <button
              onClick={() => setActiveTab('products')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'products'
                  ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Boxes className="w-4 h-4" />
              📦 Danh Mục Sản Phẩm (S-07)
            </button>

            <button
              onClick={() => setActiveTab('chain')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'chain'
                  ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Hash className="w-4 h-4" />
              ⛓️ Chuỗi Hash & T-30 (S-10 - S-12)
            </button>

            {/* S-31: Nhật Ký Hệ Thống - Chỉ Quản trị viên */}
            {['system_admin', 'admin'].includes(currentRole) && (
              <button
                onClick={() => setActiveTab('audit')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                  activeTab === 'audit'
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Shield className="w-4 h-4" />
                🛡️ Nhật Ký Hệ Thống (S-31)
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 print:p-0 print:m-0 print:max-w-none">
        {activeTab === 'dag' && <BatchLineageDAG />}
        {activeTab === 'coldchain' && <ColdChainMonitoring />}
        {activeTab === 'recall' && <EmergencyRecallManagement />}
        {activeTab === 'farmer_privacy' && <FarmerPrivacyManagement />}
        {activeTab === 'products' && <ProductManagement />}
        {activeTab === 'chain' && <ChainIntegrityCheck />}
        {activeTab === 'audit' && <SystemAuditLogs onRedirectHome={() => setActiveTab('dag')} />}
      </main>

      {/* Quick Global Inspection Dossier Modal */}
      {showGlobalDossierModal && (
        <InspectionDossierModal
          batchId={targetBatchId}
          isOpen={showGlobalDossierModal}
          onClose={() => setShowGlobalDossierModal(false)}
        />
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400 print:hidden">
        Hệ thống Truy xuất nguồn gốc nông sản © 2026 • Chuỗi lạnh S-40 - S-45 • Hồ sơ kiểm tra S-52, S-53 • Bảo vệ dữ liệu cá nhân Nghị định 13/2023/NĐ-CP (S-56)
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthRoleProvider>
      <MainApp />
    </AuthRoleProvider>
  );
}
