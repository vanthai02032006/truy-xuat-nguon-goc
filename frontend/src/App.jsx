import React, { useState } from 'react';
import { AuthRoleProvider, useAuthRole, ROLES_LIST } from './context/AuthRoleContext';
import ProductManagement from './pages/ProductManagement';
import ChainIntegrityCheck from './pages/ChainIntegrityCheck';
import BatchLineageDAG from './pages/BatchLineageDAG';
import EmergencyRecallManagement from './pages/EmergencyRecallManagement';
import {
  Boxes,
  Hash,
  Network,
  ShieldAlert,
  ChevronDown,
  UserCheck,
  Building2,
} from 'lucide-react';

function MainApp() {
  const [activeTab, setActiveTab] = useState('dag'); // Mặc định mở tab Phả hệ lô hàng (DAG)
  const { currentRole, activeRoleConfig, switchRole, isSwitching, currentUser } = useAuthRole();

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between gap-4">
            {/* Logo & Platform Name */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md font-bold text-lg">
                🌿
              </div>
              <div>
                <div className="text-base font-bold text-slate-900 leading-tight flex items-center gap-2">
                  Hệ Thống Truy Xuất Nguồn Gốc
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Sprint 2 & 3
                  </span>
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  Phả Hệ Lô Hàng (E-05) • Thu Hồi Khẩn Cấp (E-06) • RBAC 7 Vai Trò
                </div>
              </div>
            </div>

            {/* 7-Role Switcher Widget */}
            <div className="flex items-center gap-3">
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
                  value={currentRole}
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
            </div>
          </div>

          {/* Navigation Tabs Bar */}
          <div className="flex items-center gap-2 overflow-x-auto py-2 border-t border-slate-100 scrollbar-none">
            <button
              onClick={() => setActiveTab('dag')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'dag'
                  ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Network className="w-4 h-4" />
              🌳 Phả Hệ Lô Hàng DAG (E-05)
            </button>

            <button
              onClick={() => setActiveTab('recall')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'recall'
                  ? 'bg-rose-600 text-white shadow-sm shadow-rose-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              🚨 Thu Hồi Khẩn Cấp (E-06)
            </button>

            <button
              onClick={() => setActiveTab('products')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
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
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'chain'
                  ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-500/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Hash className="w-4 h-4" />
              ⛓️ Chuỗi Hash & T-30 (S-10, S-11, S-12)
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dag' && <BatchLineageDAG />}
        {activeTab === 'recall' && <EmergencyRecallManagement />}
        {activeTab === 'products' && <ProductManagement />}
        {activeTab === 'chain' && <ChainIntegrityCheck />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        Hệ thống Truy xuất nguồn gốc nông sản © 2026 • Tuân thủ chuẩn RBAC 7 Vai Trò • Thuật toán DAG Phả hệ BFS • Khóa Tức Thì Chống Lan Rộng (S-38)
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
