import React, { useState } from 'react';
import ProductManagement from './pages/ProductManagement';
import ChainIntegrityCheck from './pages/ChainIntegrityCheck';

export default function App() {
  const [activeTab, setActiveTab] = useState('products'); // 'products' | 'chain'

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md font-bold text-lg">
              🌿
            </div>
            <div>
              <div className="text-base font-bold text-slate-900 leading-tight">
                Hệ Thống Truy Xuất Nguồn Gốc
              </div>
              <div className="text-xs text-slate-500 font-medium">
                Nền tảng Quản lý Chuỗi Cung ứng & Chuỗi Khối Toàn vẹn (Sprint 2)
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
            <button
              onClick={() => setActiveTab('products')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'products'
                  ? 'bg-white text-emerald-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              📦 Danh Mục Sản Phẩm (S-07)
            </button>
            <button
              onClick={() => setActiveTab('chain')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'chain'
                  ? 'bg-white text-emerald-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              ⛓️ Kiểm Tra Chuỗi Hash & T-30 (S-10, S-11, S-12)
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'products' && <ProductManagement />}
        {activeTab === 'chain' && <ChainIntegrityCheck />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        Hệ thống Truy xuất nguồn gốc nông sản © 2026 • Tuân thủ chuẩn RBAC, Multi-tenant Isolation & Append-Only SHA-256 Hash Chain
      </footer>
    </div>
  );
}
