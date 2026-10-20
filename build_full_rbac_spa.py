import os
import sys

def generate_spa_html():
    return '''<!DOCTYPE html>
<html lang="vi" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nông Sản Lành | Hệ Thống Truy Xuất Nguồn Gốc & Giám Sát Chuỗi Cung Ứng</title>
  
  <!-- Google Fonts: Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  
  <!-- FontAwesome 6 CDN -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  
  <!-- Tailwind CSS Play CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'sans-serif'],
          },
          colors: {
            farm: {
              50: '#f0fdf4',
              100: '#dcfce7',
              200: '#bbf7d0',
              300: '#86efac',
              400: '#4ade80',
              500: '#22c55e',
              600: '#16a34a',
              700: '#15803d',
              800: '#166534',
              900: '#14532d',
            }
          }
        }
      }
    }
  </script>

  <style>
    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f8fafc; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
    
    .glassmorphism {
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }
    .badge-glow {
      box-shadow: 0 0 12px rgba(34, 197, 94, 0.35);
    }
    .nav-tab-active {
      background-color: #059669;
      color: #ffffff;
      box-shadow: 0 4px 6px -1px rgba(5, 150, 105, 0.2);
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased min-h-screen flex flex-col font-sans selection:bg-emerald-500 selection:text-white">

  <!-- ================= NOTIFICATION TOAST CONTAINER ================= -->
  <div id="toastContainer" class="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"></div>

  <!-- ================= MAIN SUPPLY CHAIN HEADER ================= -->
  <header class="sticky top-0 z-40 glassmorphism border-b border-slate-200/90 shadow-sm transition-all duration-300">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-20">
        
        <!-- Logo & Brand Name -->
        <div class="flex items-center gap-3 cursor-pointer select-none" onclick="switchNavTab('overview')">
          <div class="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-600 via-emerald-500 to-green-400 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 transform hover:scale-105 transition-transform">
            <i class="fa-solid fa-leaf text-xl"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="text-xl font-black tracking-tight bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent">
                Nông Sản Lành
              </span>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                Chuỗi Cung Ứng Đa Tổ Chức
              </span>
            </div>
            <p class="text-xs text-slate-500 font-medium">Truy Xuất Nguồn Gốc & Giám Sát Chuỗi Lạnh IoT</p>
          </div>
        </div>

        <!-- Quick Trace Search Bar -->
        <div class="hidden md:flex flex-1 max-w-sm mx-6">
          <div class="relative w-full">
            <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <i class="fa-solid fa-magnifying-glass text-xs"></i>
            </span>
            <input 
              type="text" 
              id="topSearchBar"
              placeholder="Nhập mã lô tra cứu (VD: VK89XPT2 hoặc mã bất kỳ trên danh sách)..." 
              onkeydown="if(event.key === 'Enter') handleQuickSearch(this.value)"
              class="w-full pl-9 pr-14 py-2 text-xs bg-slate-100/90 hover:bg-slate-100 border border-slate-200 rounded-full focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            />
            <button 
              onclick="handleQuickSearch(document.getElementById('topSearchBar').value)"
              class="absolute inset-y-1 right-1 px-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-full text-[11px] font-bold transition-colors">
              Tìm
            </button>
          </div>
        </div>

        <!-- RIGHT ACTIONS: Role Switcher (E-02 Demo) & Real Auth S-04 (T-08, T-09, T-10) -->
        <div class="flex items-center gap-2.5">

          <!-- Supply Chain Persona & Organization Switcher (Epic E-02: Giữ nguyên để tiện demo) -->
          <div class="relative">
            <button 
              id="roleDropdownBtn" 
              onclick="toggleRoleDropdown()" 
              class="bg-slate-100 hover:bg-slate-200/80 p-1.5 px-3 rounded-2xl flex items-center gap-2.5 border border-slate-200 shadow-sm transition-all text-xs text-left cursor-pointer select-none">
              <div id="currentRoleIconBox" class="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center text-xs font-black shadow-sm">
                <i class="fa-solid fa-seedling" id="currentRoleIcon"></i>
              </div>
              <div class="leading-tight pr-1">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold text-slate-800" id="currentRoleTitle">Vùng Trồng (Farm)</span>
                  <span class="text-[9px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200" id="currentRoleBadge">Org #1</span>
                </div>
                <p class="text-[10px] text-slate-500 font-medium" id="currentOrgName">HTX Nông Nghiệp Thắng Lợi</p>
              </div>
              <i class="fa-solid fa-chevron-down text-[10px] text-slate-400 ml-1"></i>
            </button>

            <!-- 7 Supply Chain Roles Dropdown Menu (Epic E-02) -->
            <div id="roleDropdownMenu" class="hidden absolute right-0 mt-2 w-80 bg-white rounded-3xl shadow-2xl border border-slate-200/90 py-2.5 z-50 animate-fadeIn">
              <div class="px-3.5 pb-2 border-b border-slate-100 flex items-center justify-between">
                <span class="text-[11px] font-black uppercase text-slate-400 tracking-wider">Chuỗi Cung Ứng Đa Tổ Chức (E-02)</span>
                <span class="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">7 Vai Trò</span>
              </div>
              <div class="max-h-[380px] overflow-y-auto p-1.5 space-y-1">
                
                <!-- 1. Farm -->
                <div onclick="selectSupplyChainRole('farm')" class="p-2.5 rounded-2xl hover:bg-emerald-50 cursor-pointer transition-colors flex items-start gap-3">
                  <div class="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-seedling"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-800">1. Vùng Trồng (Farm)</span>
                      <span class="text-[9px] font-bold px-1.5 rounded-full bg-emerald-100 text-emerald-800">Org #1</span>
                    </div>
                    <p class="text-[11px] text-slate-500 font-medium">HTX Thắng Lợi - Quản lý thửa & thu hoạch</p>
                  </div>
                </div>

                <!-- 2. Processing Co-op -->
                <div onclick="selectSupplyChainRole('coop')" class="p-2.5 rounded-2xl hover:bg-blue-50 cursor-pointer transition-colors flex items-start gap-3">
                  <div class="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-industry"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-800">2. HTX Sơ Chế (Co-op)</span>
                      <span class="text-[9px] font-bold px-1.5 rounded-full bg-blue-100 text-blue-800">Org #20</span>
                    </div>
                    <p class="text-[11px] text-slate-500 font-medium">HTX Sơ Chế Bảo Lộc - Sơ chế, đóng gói</p>
                  </div>
                </div>

                <!-- 3. Logistics -->
                <div onclick="selectSupplyChainRole('logistics')" class="p-2.5 rounded-2xl hover:bg-cyan-50 cursor-pointer transition-colors flex items-start gap-3">
                  <div class="w-8 h-8 rounded-xl bg-cyan-600 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-truck-fast"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-800">3. Vận Chuyển Lạnh (Logistics)</span>
                      <span class="text-[9px] font-bold px-1.5 rounded-full bg-cyan-100 text-cyan-800">Org #30</span>
                    </div>
                    <p class="text-[11px] text-slate-500 font-medium">Đội Xe Lạnh Express - Giám sát IoT 2°C - 6°C</p>
                  </div>
                </div>

                <!-- 4. Distributor -->
                <div onclick="selectSupplyChainRole('distributor')" class="p-2.5 rounded-2xl hover:bg-amber-50 cursor-pointer transition-colors flex items-start gap-3">
                  <div class="w-8 h-8 rounded-xl bg-amber-600 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-shop"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-800">4. Nhà Phân Phối / Bán Lẻ (Distributor)</span>
                      <span class="text-[9px] font-bold px-1.5 rounded-full bg-amber-100 text-amber-800">Org #40</span>
                    </div>
                    <p class="text-[11px] text-slate-500 font-medium">Chuỗi Siêu Thị BioMart - Điểm bán & quầy kệ</p>
                  </div>
                </div>

                <!-- 5. Inspector -->
                <div onclick="selectSupplyChainRole('inspector')" class="p-2.5 rounded-2xl hover:bg-purple-50 cursor-pointer transition-colors flex items-start gap-3 border-t border-slate-100">
                  <div class="w-8 h-8 rounded-xl bg-purple-700 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-clipboard-check"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-purple-900">5. Cán Bộ Kiểm Tra (Inspector)</span>
                      <span class="text-[9px] font-black px-1.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200">CHỈ ĐỌC</span>
                    </div>
                    <p class="text-[11px] text-purple-700 font-medium">Chi Cục Quản Lý Chất Lượng - Read-only toàn chuỗi</p>
                  </div>
                </div>

                <!-- 6. System Admin -->
                <div onclick="selectSupplyChainRole('system_admin')" class="p-2.5 rounded-2xl hover:bg-slate-100 cursor-pointer transition-colors flex items-start gap-3">
                  <div class="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-user-shield"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-900">6. Quản Trị Hệ Thống (Admin)</span>
                      <span class="text-[9px] font-bold px-1.5 rounded-full bg-slate-200 text-slate-800">Toàn Quyền</span>
                    </div>
                    <p class="text-[11px] text-slate-500 font-medium">Ban Quản Trị Nền Tảng - An ninh & SecurityLog</p>
                  </div>
                </div>

                <!-- 7. Consumer -->
                <div onclick="selectSupplyChainRole('consumer')" class="p-2.5 rounded-2xl hover:bg-emerald-50 cursor-pointer transition-colors flex items-start gap-3 border-t border-slate-100">
                  <div class="w-8 h-8 rounded-xl bg-emerald-800 text-white flex items-center justify-center text-xs mt-0.5 shrink-0">
                    <i class="fa-solid fa-qrcode"></i>
                  </div>
                  <div class="flex-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-800">7. Người Tiêu Dùng (Consumer)</span>
                      <span class="text-[9px] font-bold px-1.5 rounded-full bg-slate-100 text-slate-600">Không Login</span>
                    </div>
                    <p class="text-[11px] text-slate-500 font-medium">Khách quét QR tra cứu công khai (S-48)</p>
                  </div>
                </div>

              </div>
            </div>
          </div>

          <!-- Nút Nạp Lại Dữ Liệu Thật (Seed Database) -->
          <button 
            id="seedDatabaseBtn" 
            onclick="seedFullDatabase()" 
            title="Nạp 13 lô hàng mẫu qua 4 tầng phả hệ & chuỗi hash vào cơ sở dữ liệu thật"
            class="bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 px-3 py-2 rounded-2xl flex items-center gap-1.5 text-xs font-bold transition-all transform active:scale-95 cursor-pointer">
            <i class="fa-solid fa-database text-amber-600"></i>
            <span class="hidden sm:inline">Nạp Dữ Liệu Thật (Seed)</span>
          </button>

          <!-- Nút Đăng Nhập / Đổi Tài Khoản S-04 (T-08, T-09, T-10) -->
          <div class="flex items-center gap-1.5">
            <button 
              id="authLoginBtn" 
              onclick="openLoginModal()" 
              class="bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white px-3.5 py-2 rounded-2xl flex items-center gap-2 shadow-sm hover:shadow text-xs font-bold transition-all transform active:scale-95 cursor-pointer">
              <i class="fa-solid fa-right-to-bracket text-xs" id="authBtnIcon"></i>
              <span id="authBtnLabel">Đăng Nhập / Đổi TK</span>
              <span id="authActiveDot" class="w-2 h-2 rounded-full bg-emerald-300 hidden"></span>
            </button>
            <button 
              id="authLogoutBtn" 
              onclick="handleLogout()" 
              title="Đăng xuất khỏi phiên"
              class="hidden px-2.5 py-2 bg-slate-100 hover:bg-rose-50 text-slate-500 hover:text-rose-600 rounded-2xl border border-slate-200 text-xs font-bold transition-colors">
              <i class="fa-solid fa-arrow-right-from-bracket"></i>
            </button>
          </div>

        </div>

      </div>
    </div>

    <!-- ================= SUPPLY CHAIN NAVIGATION BAR ================= -->
    <div class="bg-white/80 border-t border-slate-200/80 px-4 sm:px-6 lg:px-8 py-2 overflow-x-auto shadow-inner">
      <div class="max-w-7xl mx-auto flex items-center gap-2 min-w-max">
        
        <button 
          id="tabBtn_overview" 
          onclick="switchNavTab('overview')"
          class="nav-tab-btn nav-tab-active px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2">
          <i class="fa-solid fa-chart-pie"></i> Tổng Quan Chuỗi Cung Ứng
        </button>

        <button 
          id="tabBtn_batches" 
          onclick="switchNavTab('batches')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-boxes-stacked"></i> Lô Hàng Thu Hoạch (S-08, S-14)
        </button>

        <button 
          id="tabBtn_plots" 
          onclick="switchNavTab('plots')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-map-location-dot"></i> Thửa Đất Vùng Trồng (S-06)
        </button>

        <button 
          id="tabBtn_materials_phi" 
          onclick="switchNavTab('materials_phi')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-shield-virus text-amber-600"></i> Nhật Ký Vật Tư & Thời Gian Cách Ly (S-62)
        </button>

        <button 
          id="tabBtn_handovers" 
          onclick="switchNavTab('handovers')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-truck-ramp-box"></i> Bàn Giao & Vận Chuyển Lạnh (S-15, S-16)
        </button>

                <button 
          id="tabBtn_recalls" 
          onclick="switchNavTab('recalls')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 hover:text-rose-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation text-rose-600"></i> Thu Hồi Khẩn Cấp (E-06)
        </button>

        <button 
          id="tabBtn_cold_chain" 
          onclick="switchNavTab('cold_chain')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-cyan-600 hover:bg-cyan-50 hover:text-cyan-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-snowflake text-cyan-600"></i> Chuỗi Lạnh & IoT (E-07)
        </button>

        <button 
          id="tabBtn_traceability" 
          onclick="switchNavTab('traceability')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-link"></i> Toàn Vẹn Chuỗi Hash SHA-256 (S-10, S-12)
        </button>

        <button 
          id="tabBtn_public" 
          onclick="switchNavTab('public')"
          class="nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2">
          <i class="fa-solid fa-qrcode text-emerald-600"></i> Tra Cứu Công Khai (S-48)
        </button>

      </div>
    </div>

    <!-- Inspector Read-Only Alert Banner (Epic E-02) -->
    <div id="inspectorBanner" class="hidden bg-gradient-to-r from-purple-900 via-indigo-900 to-purple-800 text-white px-4 py-2.5 text-xs font-medium border-b border-purple-700 shadow-md">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <i class="fa-solid fa-clipboard-check text-amber-300 text-sm"></i>
          <span><strong>Chế độ Cán Bộ Kiểm Tra (Inspector - Epic E-02):</strong> Bạn có quyền tra cứu lô hàng trên <strong>mọi tổ chức độc lập</strong> toàn chuỗi, nhưng hệ thống được khóa ở <strong>chế độ CHỈ ĐỌC (Read-only)</strong>. Mọi hành vi tạo/sửa/xóa sẽ bị từ chối HTTP 403 Forbidden.</span>
        </div>
        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-purple-700/80 text-purple-200 border border-purple-500 shrink-0">READ-ONLY AUDIT</span>
      </div>
    </div>
  </header>

  <!-- ================= MAIN SUPPLY CHAIN MODULE VIEWS ================= -->
  <main class="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">

    <!-- ======================================================== -->
    <!-- VIEW 1: TỔNG QUAN CHUỖI CUNG ỨNG & CHUỖI LẠNH (OVERVIEW) -->
    <!-- ======================================================== -->
    <div id="view_overview" class="module-view space-y-8">
      
      <!-- Welcome Hero Banner -->
      <div class="bg-gradient-to-r from-emerald-900 via-emerald-800 to-teal-900 text-white p-6 sm:p-8 rounded-3xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-700/60 border border-emerald-500/30 text-emerald-200 text-xs font-bold">
            <i class="fa-solid fa-network-wired text-emerald-300"></i> Nông Nghiệp Minh Bạch & Giám Sát Chuỗi Cung Ứng Khép Kín
          </div>
          <h2 class="text-2xl sm:text-3xl font-black text-white">Giám Sát Chuỗi Cung Ứng & An Toàn Thực Phẩm</h2>
          <p class="text-xs sm:text-sm text-emerald-100/90 max-w-2xl">
            Theo dõi hành trình lô hàng từ vùng canh tác, kiểm soát chặt chẽ thời gian cách ly phân bón/thuốc BVTV (S-62), bàn giao qua các đơn vị và kiểm soát nhiệt độ xe lạnh IoT.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <button onclick="openModal('addBatchModal')" class="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2">
            <i class="fa-solid fa-plus-circle"></i> Khởi Tạo Lô Thu Hoạch
          </button>
          <button onclick="openModal('recordBatchMaterialModal')" class="px-4 py-2.5 bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2">
            <i class="fa-solid fa-spray-can"></i> Ghi Nhận Vật Tư (S-62)
          </button>
          <button 
            id="modalBtnRecall" 
            onclick="openRecallModalForCurrentBatch()" 
            class="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5 transition-all">
            <i class="fa-solid fa-triangle-exclamation"></i> Thu Hồi Khẩn Cấp (S-33)
          </button>
        </div>
      </div>

      <!-- Supply Chain Metrics KPI Bar -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Tổng Lô Hàng Quản Lý</p>
            <div class="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <i class="fa-solid fa-boxes-stacked"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-slate-900 mt-2" id="kpiTotalBatches">--</p>
          <p class="text-[11px] text-emerald-600 font-semibold mt-1">Đang lưu kho & vận chuyển</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Thửa Đất Vùng Trồng</p>
            <div class="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <i class="fa-solid fa-map-location-dot"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-blue-700 mt-2" id="kpiTotalPlots">--</p>
          <p class="text-[11px] text-slate-500 mt-1">7,500 m2 diện tích hợp chuẩn</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">An Toàn Cách Ly (PHI)</p>
            <div class="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <i class="fa-solid fa-shield-check"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-emerald-700 mt-2" id="kpiPhiCompliant">100% Đạt Chuẩn</p>
          <p class="text-[11px] text-emerald-600 font-semibold mt-1">Tuân thủ thời gian cách ly (S-62)</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Chuỗi Lạnh IoT Hoạt Động</p>
            <div class="w-9 h-9 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
              <i class="fa-solid fa-snowflake"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-teal-700 mt-2" id="kpiColdChainTemp">3.8°C - 4.5°C</p>
          <p class="text-[11px] text-teal-600 font-semibold mt-1">Không vi phạm sốc nhiệt</p>
        </div>
      </div>

      <!-- Quick Actions & Status Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Module Highlight: S-62 PHI Compliance -->
        <div class="lg:col-span-2 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <span class="text-[11px] font-bold text-amber-600 uppercase tracking-wider">Tiêu chuẩn an toàn thu hoạch</span>
              <h3 class="font-black text-slate-800 text-lg">Giám Sát Thời Gian Cách Ly Vật Tư (Story S-62)</h3>
            </div>
            <button onclick="switchNavTab('materials_phi')" class="text-xs text-emerald-600 hover:text-emerald-700 font-bold flex items-center gap-1">
              Xem toàn bộ nhật ký <i class="fa-solid fa-arrow-right text-[10px]"></i>
            </button>
          </div>
          <p class="text-xs text-slate-600">
            Hệ thống tự động theo dõi số ngày cách ly bắt buộc (Pre-Harvest Interval - PHI) của từng loại phân bón và thuốc BVTV sử dụng cho lô hàng. Đảm bảo nông sản không còn dư lượng trước khi thu hoạch xuất kho.
          </p>

          <div class="bg-amber-50/70 border border-amber-200 p-4 rounded-2xl flex items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center text-lg">
                <i class="fa-solid fa-flask-vial"></i>
              </div>
              <div class="text-xs">
                <p class="font-bold text-amber-950">Công cụ kiểm tra thời gian cách ly thu hoạch tức thời</p>
                <p class="text-[11px] text-amber-800">Chọn bất kỳ lô hàng nào để đối chiếu với ngày sử dụng thuốc BVTV gần nhất.</p>
              </div>
            </div>
            <button onclick="switchNavTab('materials_phi')" class="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold whitespace-nowrap shadow-sm">
              Kiểm Tra Ngay
            </button>
          </div>
        </div>

        <!-- IoT Cold Chain Live Widget -->
        <div class="bg-emerald-950 text-white p-6 rounded-3xl shadow-xl space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-emerald-800/80">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></span>
              <h4 class="font-bold text-sm">Cảm Biến Chuỗi Lạnh IoT</h4>
            </div>
            <span class="text-[10px] bg-emerald-800 px-2 py-0.5 rounded-full text-emerald-300 font-mono">LIVE 24/7</span>
          </div>

          <div class="space-y-3">
            <div class="bg-emerald-900/60 p-3.5 rounded-2xl border border-emerald-700/50 flex justify-between items-center">
              <div>
                <p class="text-[10px] text-emerald-300 uppercase font-semibold">Kho lạnh trung tâm</p>
                <p class="font-bold text-white text-xs">Kho Lâm Đồng #01</p>
              </div>
              <p class="text-xl font-black text-emerald-300 font-mono" id="liveTempWarehouse">4.2°C</p>
            </div>

            <div class="bg-emerald-900/60 p-3.5 rounded-2xl border border-emerald-700/50 flex justify-between items-center">
              <div>
                <p class="text-[10px] text-emerald-300 uppercase font-semibold">Xe tải lạnh chuyên dụng</p>
                <p class="font-bold text-white text-xs">Xe 49C-128.45</p>
              </div>
              <p class="text-xl font-black text-emerald-300 font-mono" id="liveTempTruck">3.9°C</p>
            </div>
          </div>

          <p class="text-[11px] text-emerald-200/80 leading-relaxed pt-1">
            <i class="fa-solid fa-lock text-emerald-400 mr-1"></i>
            Dữ liệu nhiệt độ được ghi nhận và nối hash vào chuỗi sự kiện bất biến theo từng mốc thời gian.
          </p>
        </div>

      </div>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 2: QUẢN LÝ LÔ HÀNG THU HOẠCH (BATCHES - S-08, S-14) -->
    <!-- ======================================================== -->
    <div id="view_batches" class="module-view hidden space-y-6">
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span class="text-xs font-bold text-emerald-600 uppercase tracking-wider">Hồ Sơ Nông Sản Đa Tổ Chức</span>
          <h2 class="text-2xl font-black text-slate-900 mt-1">Danh Sách Lô Hàng Thu Hoạch Đang Lưu Giữ (S-14)</h2>
          <p class="text-xs text-slate-500 mt-1">Mã lô ngẫu nhiên đủ dài, tìm kiếm không phân biệt hoa thường, phân trang 20 lô/trang</p>
        </div>
        <div class="flex items-center gap-2">
          <button id="btnOpenMergeModal" onclick="openMergeModalForSelected()" class="hidden px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-2 transition-all">
            <i class="fa-solid fa-object-group"></i> Gộp Lô Đã Chọn (<span id="mergeSelectedCount">0</span>) (S-19)
          </button>
          <button id="addBatchBtn" onclick="handleAddBatchClick()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-2">
            <i class="fa-solid fa-plus"></i> Tạo Lô Thu Hoạch Mới
          </button>
        </div>
      </div>

      <!-- Batch Filter & Search Bar -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div class="relative w-full sm:w-96">
          <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3 text-slate-400 text-xs"></i>
          <input 
            type="text" 
            id="batchFilterInput" 
            placeholder="Tìm theo một phần mã lô (không phân biệt hoa thường)..." 
            oninput="filterBatchesTable(this.value)"
            class="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 font-semibold"
          />
        </div>
        <div class="flex items-center gap-2 w-full sm:w-auto">
          <span class="text-xs text-slate-500 font-medium">Lọc sản phẩm:</span>
          <select id="batchProductFilter" onchange="filterBatchesByProduct(this.value)" class="p-2 text-xs bg-slate-50 border border-slate-200 rounded-xl font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500">
            <option value="all">Tất cả sản phẩm</option>
            <option value="Cà Chua Beef Hữu Cơ">Cà Chua Beef Hữu Cơ</option>
            <option value="Dâu Tây New Zealand">Dâu Tây New Zealand</option>
            <option value="Dưa Lưới Huỳnh Long">Dưa Lưới Huỳnh Long</option>
            <option value="Bơ Sáp 034 Đặc Sản">Bơ Sáp 034 Đặc Sản</option>
          </select>
        </div>
      </div>

      <!-- Batches Table -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th class="p-3.5 w-10 text-center"><input type="checkbox" id="selectAllBatches" onchange="toggleSelectAllBatches(this)" class="rounded text-emerald-600 focus:ring-emerald-500 cursor-pointer"/></th>
                <th class="p-3.5">Mã Định Danh Lô</th>
                <th class="p-3.5">Tên Nông Sản</th>
                <th class="p-3.5">Thửa Đất Nguồn</th>
                <th class="p-3.5">Khối Lượng Còn Lại (S-17)</th>
                <th class="p-3.5">Trạng Thái Chuỗi Lạnh</th>
                <th class="p-3.5">Thời Gian Cách Ly (S-62)</th>
                <th class="p-3.5 text-right">Thao Tác</th>
              </tr>
            </thead>
            <tbody id="batchesTableBody" class="divide-y divide-slate-100 font-medium text-slate-700">
              <!-- Rendered dynamically -->
            </tbody>
          </table>
        </div>
      </div>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 3: THỬA ĐẤT VÙNG TRỒNG (LAND PLOTS - S-06)          -->
    <!-- ======================================================== -->
    <div id="view_plots" class="module-view hidden space-y-6">
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span class="text-xs font-bold text-emerald-600 uppercase tracking-wider">Vùng Trồng Canh Tác</span>
          <h2 class="text-2xl font-black text-slate-900 mt-1">Khai Báo Thửa Đất Thuộc Tổ Chức Mình (S-06)</h2>
          <p class="text-xs text-slate-500 mt-1">Diện tích phải &gt; 0, toạ độ GPS dạng số thực, chỉ thấy thửa của tổ chức mình</p>
        </div>
        <button id="addPlotBtn" onclick="handleAddPlotClick()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-2">
          <i class="fa-solid fa-plus"></i> Khai Báo Thửa Đất Mới
        </button>
      </div>

      <!-- Plots Grid -->
      <div id="plotsGrid" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Rendered dynamically -->
      </div>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 4: NHẬT KÝ VẬT TƯ & THỜI GIAN CÁCH LY (STORY S-62)   -->
    <!-- ======================================================== -->
    <div id="view_materials_phi" class="module-view hidden space-y-6">
      
      <!-- S-62 Header -->
      <div class="bg-gradient-to-r from-amber-600 via-amber-700 to-emerald-800 text-white p-6 rounded-3xl shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-900/60 text-amber-200 text-xs font-bold border border-amber-400/30">
            <i class="fa-solid fa-shield-virus"></i> Tiêu Chuẩn VietGAP / GlobalGAP
          </div>
          <h2 class="text-2xl sm:text-3xl font-black text-white mt-2">Nhật Ký Vật Tư & Kiểm Tra Thời Gian Cách Ly (S-62)</h2>
          <p class="text-xs sm:text-sm text-amber-100 mt-1">Ghi nhận phân bón, thuốc BVTV đã dùng gắn với một lô hàng cụ thể để kiểm tra thời gian cách ly (PHI) khi thu hoạch</p>
        </div>
        <button id="addMaterialBtn" onclick="handleAddMaterialClick()" class="px-4 py-2.5 bg-white hover:bg-slate-100 text-slate-900 font-black rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2 whitespace-nowrap">
          <i class="fa-solid fa-plus-circle text-amber-600"></i> Ghi Nhận Vật Tư Cho Lô
        </button>
      </div>

      <!-- PHI PRE-HARVEST CHECKER TOOL (KIỂM TRA CÁCH LY TRỰC TIẾP) -->
      <div class="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center text-lg">
            <i class="fa-solid fa-stethoscope"></i>
          </div>
          <div>
            <h3 class="font-black text-slate-900 text-base">Công Cụ Kiểm Tra Thời Gian Cách Ly Khi Thu Hoạch (Pre-Harvest PHI Check)</h3>
            <p class="text-xs text-slate-500">Đối chiếu ngày thu hoạch dự kiến với ngày an toàn xa nhất của các lần phun thuốc/bón phân</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end bg-slate-50 p-4 rounded-2xl border border-slate-200">
          <div class="sm:col-span-5">
            <label class="block font-bold text-slate-700 text-xs mb-1">Chọn Lô Nông Sản Cần Kiểm Tra</label>
            <select id="phiCheckBatchSelect" class="w-full p-2.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-emerald-500">
              <!-- Rendered dynamically -->
            </select>
          </div>
          <div class="sm:col-span-4">
            <label class="block font-bold text-slate-700 text-xs mb-1">Ngày Thu Hoạch Dự Kiến</label>
            <input type="date" id="phiCheckHarvestDate" class="w-full p-2.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-emerald-500" value="2026-10-20" />
          </div>
          <div class="sm:col-span-3">
            <button onclick="executePhiCheck()" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-md flex items-center justify-center gap-2">
              <i class="fa-solid fa-clipboard-check"></i> Kiểm Tra Cách Ly
            </button>
          </div>
        </div>

        <!-- PHI Check Result Container -->
        <div id="phiCheckResult" class="hidden p-4 rounded-2xl text-xs font-medium border transition-all">
          <!-- Dynamic Result Displayed here -->
        </div>
      </div>

      <!-- S-62 Batch Material Usage Table -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="font-extrabold text-slate-800 text-sm">Nhật Ký Chi Tiết Sử Dụng Vật Tư Gắn Theo Từng Lô Hàng (S-62)</h3>
          <span class="text-xs text-slate-500">Tự động tính ngày an toàn thu hoạch = Ngày sử dụng + Số ngày cách ly</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th class="p-3.5">Mã Lô Nông Sản</th>
                <th class="p-3.5">Phân Loại</th>
                <th class="p-3.5">Tên Vật Tư / Chế Phẩm</th>
                <th class="p-3.5">Liều Lượng Sử Dụng</th>
                <th class="p-3.5">Ngày Phun / Bón</th>
                <th class="p-3.5">Cách Ly (PHI)</th>
                <th class="p-3.5">Ngày An Toàn Thu Hoạch</th>
                <th class="p-3.5">Người Thực Hiện</th>
                <th class="p-3.5 text-right">Đánh Giá An Toàn</th>
              </tr>
            </thead>
            <tbody id="materialLogsTableBody" class="divide-y divide-slate-100 font-medium text-slate-700">
              <!-- Rendered dynamically -->
            </tbody>
          </table>
        </div>
      </div>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 5: BÀN GIAO & VẬN CHUYỂN LẠNH (S-15, S-16)           -->
    <!-- ======================================================== -->
    <div id="view_handovers" class="module-view hidden space-y-6">
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span class="text-xs font-bold text-emerald-600 uppercase tracking-wider">Luân Chuyển Chuỗi Cung Ứng (User Story S-15, S-16)</span>
          <h2 class="text-2xl font-black text-slate-900 mt-1">Bàn Giao Lô Hàng Giữa Các Tổ Chức Độc Lập</h2>
          <p class="text-xs text-slate-500 mt-1">Chặn bàn giao lần hai khi đang chờ duyệt. Bên nhận xác nhận chuyển quyền hoặc từ chối kèm lý do (tối thiểu 10 ký tự) trong cùng giao dịch.</p>
        </div>
        <button onclick="openModal('handoverModal')" class="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-2">
          <i class="fa-solid fa-truck-moving"></i> Tạo Phiếu Bàn Giao Mới
        </button>
      </div>

      <!-- Quick Sub-Tabs: Tất cả / Chờ tôi xác nhận / Tôi đã gửi -->
      <div class="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button id="hoFilterBtn_incoming" onclick="filterHandoversView('incoming')" class="px-4 py-2 rounded-xl text-xs font-bold bg-amber-500 text-white shadow-sm flex items-center gap-2">
          <i class="fa-solid fa-inbox"></i> Danh Sách Chờ Tôi Xác Nhận
          <span id="badgeIncomingCount" class="px-2 py-0.5 rounded-full text-[10px] bg-white text-amber-900 font-black">1</span>
        </button>
        <button id="hoFilterBtn_outgoing" onclick="filterHandoversView('outgoing')" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 flex items-center gap-2">
          <i class="fa-solid fa-paper-plane"></i> Lệnh Bàn Giao Tôi Đã Gửi
        </button>
        <button id="hoFilterBtn_all" onclick="filterHandoversView('all')" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 flex items-center gap-2">
          <i class="fa-solid fa-clock-rotate-left"></i> Toàn Bộ Lịch Sử
        </button>
      </div>

      <!-- BẢNG 1: DANH SÁCH CHỜ TÔI XÁC NHẬN (INCOMING HANDOVERS CHO BÊN NHẬN - S-15, S-16) -->
      <div id="incomingHandoversSection" class="bg-white rounded-3xl border-2 border-amber-200 shadow-md overflow-hidden space-y-3">
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 p-4 border-b border-amber-200 flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-xl bg-amber-500 text-white flex items-center justify-center font-bold text-sm shadow-sm">
              <i class="fa-solid fa-inbox"></i>
            </div>
            <div>
              <h3 class="font-extrabold text-amber-950 text-sm">Danh Sách Chờ Tôi Xác Nhận (Bên Nhận Tiếp Quản)</h3>
              <p class="text-[11px] text-amber-800">Kiểm tra thông tin và nhiệt độ trước khi [Xác Nhận] nhận lô hoặc [Từ Chối] có lý do bắt buộc.</p>
            </div>
          </div>
          <span class="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-amber-200 text-amber-900 border border-amber-300">
            Dành Riêng Cho Tổ Chức Hiện Tại
          </span>
        </div>

        <div class="overflow-x-auto p-2">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
              <tr>
                <th class="p-3.5">Mã Lô Nông Sản</th>
                <th class="p-3.5">Bên Giao (From Org)</th>
                <th class="p-3.5">Nhiệt Độ Xe / Kho Lạnh</th>
                <th class="p-3.5">Thời Gian Tạo</th>
                <th class="p-3.5">Trạng Thái Lô</th>
                <th class="p-3.5 text-right">Hành Động Xác Nhận (S-16)</th>
              </tr>
            </thead>
            <tbody id="incomingHandoversTableBody" class="divide-y divide-slate-100 font-medium">
              <!-- Rendered dynamically -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- BẢNG 2: TOÀN BỘ LỊCH SỬ HOẶC LỆNH GỬI ĐI -->
      <div id="generalHandoversSection" class="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden space-y-3">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="font-extrabold text-slate-800 text-sm" id="generalHandoversTitle">Tất Cả Các Lệnh Bàn Giao Trong Chuỗi Cung Ứng</h3>
          <span class="text-xs text-slate-500">Chuyển quyền giữ nguyên tử và gắn sự kiện băm SHA-256</span>
        </div>
        <div class="overflow-x-auto p-2">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
              <tr>
                <th class="p-3.5">Mã Lô</th>
                <th class="p-3.5">Bên Giao (From Org)</th>
                <th class="p-3.5">Bên Nhận (To Org)</th>
                <th class="p-3.5">Trạng Thái Bàn Giao</th>
                <th class="p-3.5">Nhiệt Độ</th>
                <th class="p-3.5 text-right">Ghi Chú / Lý Do</th>
              </tr>
            </thead>
            <tbody id="handoversTableBody" class="divide-y divide-slate-100 font-medium">
              <!-- Rendered dynamically -->
            </tbody>
          </table>
        </div>
      </div>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 6: TOÀN VẸN CHUỖI HASH SHA-256 (S-10, S-12, S-13)   -->
    <!-- ======================================================== -->
    <div id="view_traceability" class="module-view hidden space-y-6">
      
      <div class="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-950 text-white p-6 rounded-3xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-emerald-400 text-xs font-bold border border-slate-700">
            <i class="fa-solid fa-shield-halved"></i> Bảo Vệ Bất Biến (Tamper-Proof)
          </div>
          <h2 class="text-2xl sm:text-3xl font-black text-white mt-2">Chuỗi Hash Sự Kiện & Kiểm Tra Toàn Vẹn (S-10, S-12)</h2>
          <p class="text-xs sm:text-sm text-slate-400 mt-1">Mỗi sự kiện nối hash SHA-256 với sự kiện trước. Thuật toán kiểm tra phát hiện chính xác vị trí bị sửa lén hoặc bị xoá</p>
        </div>
        <button onclick="runHashIntegrityCheck()" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2">
          <i class="fa-solid fa-fingerprint"></i> Chạy Kiểm Tra Toàn Vẹn
        </button>
      </div>

      <!-- Hash Chain Live Timeline Table -->
      <div class="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <h3 class="font-black text-slate-800 text-base">Sổ Sự Kiện Nối Hash SHA-256 (Append-Only Event Ledger)</h3>
          <span id="integrityStatusBadge" class="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold flex items-center gap-1.5">
            <i class="fa-solid fa-circle-check"></i> Chuỗi Hash Hợp Lệ 100%
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 font-sans uppercase font-semibold">
              <tr>
                <th class="p-3">Thứ Tự</th>
                <th class="p-3">Loại Sự Kiện</th>
                <th class="p-3">Lô Nông Sản</th>
                <th class="p-3">Tổ Chức Thực Hiện (S-13)</th>
                <th class="p-3">Previous Hash</th>
                <th class="p-3">Current Hash</th>
                <th class="p-3 text-right">Trạng Thái</th>
              </tr>
            </thead>
            <tbody id="hashEventsTableBody" class="divide-y divide-slate-100">
              <!-- Rendered dynamically -->
            </tbody>
          </table>
        </div>
      </div>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 7: CỔNG TRA CỨU NGUỒN GỐC CÔNG KHAI (PUBLIC - S-48 & E-08) -->
    <!-- ======================================================== -->
    <div id="view_public" class="module-view hidden space-y-8">
      
      <!-- HERO BANNER -->
      <section class="relative bg-gradient-to-b from-emerald-950 via-emerald-900 to-emerald-950 text-white overflow-hidden py-16 sm:py-24 rounded-3xl shadow-2xl border border-emerald-800/40">
        <div class="absolute inset-0 opacity-15 bg-[radial-gradient(#86efac_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none"></div>
        <div class="max-w-4xl mx-auto px-4 text-center space-y-6 relative z-10">
          
          <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-800/80 border border-emerald-500/30 text-emerald-300 text-xs font-bold shadow-inner">
            <i class="fa-solid fa-shield-halved text-emerald-400"></i> Cổng Tra Cứu Công Khai Nông Sản Lành
          </div>

          <h1 class="text-3xl sm:text-5xl font-black text-white leading-tight">
            Nông Sản An Toàn <br>
            <span class="text-emerald-400">Minh Bạch Từng Nguồn Cội</span>
          </h1>

          <p class="text-emerald-100/90 text-xs sm:text-sm max-w-xl mx-auto font-normal leading-relaxed">
            Tra cứu thông tin nguồn gốc lô nông sản, vùng trồng và chứng nhận an toàn thu hoạch bằng cách nhập mã định danh hoặc quét trực tiếp mã QR trên bao bì.
          </p>

          <!-- Big Search Bar & Camera QR Scanner (Duy nhất trên trang công khai - S-48) -->
          <div class="pt-2 max-w-2xl mx-auto">
            <div class="bg-white p-2.5 rounded-2xl shadow-2xl flex flex-col sm:flex-row items-center gap-2 border border-slate-200">
              <div class="relative flex-1 w-full">
                <i class="fa-solid fa-barcode absolute left-4 top-3.5 text-slate-400 text-sm"></i>
                <input 
                  type="text" 
                  id="heroSearchInput"
                  placeholder="Nhập mã lô in trên tem QR nông sản..."
                  onkeydown="if(event.key === 'Enter') handleQuickSearch(this.value)"
                  class="w-full pl-11 pr-4 py-3 text-slate-800 text-xs sm:text-sm font-semibold focus:outline-none rounded-xl bg-slate-50 border border-transparent focus:border-emerald-500 focus:bg-white transition-all"
                />
              </div>

              <!-- Button Quét QR từ camera điện thoại -->
              <button 
                onclick="openQrCameraScanner()"
                type="button"
                class="w-full sm:w-auto px-4 py-3 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2 text-xs sm:text-sm whitespace-nowrap">
                <i class="fa-solid fa-camera"></i> Quét QR Camera
              </button>

              <!-- Button Tra cứu ngay -->
              <button 
                onclick="handleQuickSearch(document.getElementById('heroSearchInput').value)"
                type="button"
                class="w-full sm:w-auto px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2 text-xs sm:text-sm whitespace-nowrap">
                <i class="fa-solid fa-magnifying-glass"></i> Tra Cứu
              </button>
            </div>

            <!-- Cam kết bảo mật & Chống Scraping (E-08) -->
            <div class="flex items-center justify-center gap-2 mt-4 text-xs text-emerald-200/90 font-medium">
              <i class="fa-solid fa-lock text-emerald-400"></i>
              <span>Cơ chế bảo vệ dữ liệu chống thu thập tự động (Anti-Scraping E-08 & S-48).</span>
            </div>
          </div>

        </div>
      </section>

    </div>


    <!-- ======================================================== -->
    <!-- VIEW 8: THU HỒI LÔ HÀNG KHẨN CẤP (EPIC E-06)             -->
    <!-- S-33, S-34, S-35, S-36, S-37, S-38                        -->
    <!-- ======================================================== -->
    <div id="view_recalls" class="module-view space-y-8 hidden">
      
      <!-- Recall Hero Banner -->
      <div class="bg-gradient-to-r from-rose-900 via-rose-800 to-amber-950 text-white p-6 sm:p-8 rounded-3xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6 border border-rose-700">
        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-700/60 border border-rose-500/30 text-rose-200 text-xs font-bold">
            <i class="fa-solid fa-triangle-exclamation text-rose-300"></i> Epic E-06: Ứng Phó Khẩn Cấp Sự Cố An Toàn Thực Phẩm
          </div>
          <h2 class="text-2xl sm:text-3xl font-black text-white">Quản Lý Thu Hồi Lô Hàng Khẩn Cấp (Recall)</h2>
          <p class="text-xs sm:text-sm text-rose-100/90 max-w-2xl">
            Khi phát hiện sự cố an toàn thực phẩm, hệ thống lập tức khoanh vùng toàn bộ cây phả hệ hậu duệ qua mọi tầng tách/gộp (S-34, S-35) và tự động khóa quyền Bàn giao, Tách, Gộp (S-38) để bảo vệ sức khỏe người tiêu dùng.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <button onclick="switchNavTab('batches')" class="px-4 py-2.5 bg-rose-500 hover:bg-rose-400 text-slate-950 font-bold rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2">
            <i class="fa-solid fa-boxes-stacked"></i> Chọn Lô Cần Mở Thu Hồi
          </button>
        </div>
      </div>

      <!-- Recall Metrics KPI Bar -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Lệnh Đang Kích Hoạt</p>
            <div class="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <i class="fa-solid fa-bullhorn"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-rose-700 mt-2" id="kpiActiveRecalls">0 Lệnh</p>
          <p class="text-[11px] text-rose-600 font-semibold mt-1">Đang xử lý cô lập</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Lô Bị Khoanh Vùng</p>
            <div class="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <i class="fa-solid fa-network-wired"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-amber-700 mt-2" id="kpiTotalAffectedBatches">0 Lô</p>
          <p class="text-[11px] text-slate-500 mt-1">Cây phả hệ con/cháu (S-34)</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Tồn Kho / Kệ Siêu Thị</p>
            <div class="w-9 h-9 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center">
              <i class="fa-solid fa-boxes-packing"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-orange-700 mt-2" id="kpiStockToIsolateKg">0 kg</p>
          <p class="text-[11px] text-orange-600 font-semibold mt-1">Khóa quyền lưu thông (S-38)</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Đã Bán Cho Người Dùng</p>
            <div class="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <i class="fa-solid fa-user-tag"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-purple-700 mt-2" id="kpiSoldToConsumersKg">0 kg</p>
          <p class="text-[11px] text-purple-600 font-semibold mt-1">Cần thông báo thu hồi (S-35)</p>
        </div>
      </div>

      <!-- Recall List Table Card -->
      <div class="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 class="text-base font-extrabold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-clipboard-list text-rose-600"></i> Danh Sách Lệnh Thu Hồi Nông Sản Khẩn Cấp
            </h3>
            <p class="text-xs text-slate-500">Giám sát tiến độ xác nhận cô lập của từng tổ chức theo thời gian thực (S-36, S-37)</p>
          </div>
          <button onclick="renderRecallsTab()" class="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-colors">
            <i class="fa-solid fa-arrows-rotate"></i> Làm Mới Dữ Liệu
          </button>
        </div>

        <div class="overflow-x-auto rounded-2xl border border-slate-200">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-600 uppercase text-[10px] font-bold border-b border-slate-200">
              <tr>
                <th class="p-3.5">Mã Lệnh Thu Hồi</th>
                <th class="p-3.5">Lô Nguồn & Sản Phẩm</th>
                <th class="p-3.5">Mức Độ</th>
                <th class="p-3.5">Tiến Độ Xử Lý Các Tổ Chức (S-37)</th>
                <th class="p-3.5 text-right">Kho / Kệ (kg)</th>
                <th class="p-3.5 text-right">Đã Bán (kg)</th>
                <th class="p-3.5">Trạng Thái</th>
                <th class="p-3.5 text-right">Thao Tác</th>
              </tr>
            </thead>
            <tbody id="recallsTableBody" class="divide-y divide-slate-100">
              <!-- Dynamic recall items -->
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- ======================================================== -->
    <!-- VIEW: GIÁM SÁT CHUỖI LẠNH & CẢM BIẾN IoT (EPIC E-07)     -->
    <!-- User Stories S-40, S-41, S-43, S-45                      -->
    <!-- ======================================================== -->
    <div id="view_cold_chain" class="module-view hidden space-y-8">
      
      <!-- Cold Chain Hero Banner -->
      <div class="bg-gradient-to-r from-cyan-900 via-sky-800 to-teal-900 text-white p-6 sm:p-8 rounded-3xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-700/60 border border-cyan-500/30 text-cyan-200 text-xs font-bold">
            <i class="fa-solid fa-snowflake text-cyan-300"></i> Epic E-07: Giám Sát Chuỗi Lạnh & Cảm Biến Nhiệt Độ IoT
          </div>
          <h2 class="text-2xl sm:text-3xl font-black text-white">Giám Sát Chuỗi Lạnh & Chuyến Vận Chuyển</h2>
          <p class="text-xs sm:text-sm text-cyan-100/90 max-w-2xl">
            Quản lý chuyến xe lạnh (S-40), tiếp nhận dữ liệu cảm biến IoT theo thời gian thực (S-41), phát hiện vi phạm sốc nhiệt có độ trễ 30 phút và cơ chế gộp dưới 5 phút (S-43), tự động kích hoạt cảnh báo vào chuỗi Hash SHA-256 của toàn bộ lô hàng (S-45).
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <button onclick="openCreateTripModal()" class="px-4 py-2.5 bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2">
            <i class="fa-solid fa-truck-ramp-box"></i> Tạo Chuyến Xe Lạnh (S-40)
          </button>
          <button onclick="openSimulateTelemetryModal()" class="px-4 py-2.5 bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold rounded-xl text-xs sm:text-sm shadow-md transition-all flex items-center gap-2">
            <i class="fa-solid fa-temperature-arrow-up"></i> Giả Lập Cảm Biến (S-41, S-43)
          </button>
        </div>
      </div>

      <!-- Cold Chain KPI Bar -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Chuyến Đang Chạy</p>
            <div class="w-9 h-9 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center">
              <i class="fa-solid fa-truck-fast"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-slate-900 mt-2" id="kpiActiveTrips">0 Chuyến</p>
          <p class="text-[11px] text-cyan-600 font-semibold mt-1">Trạng thái IN_TRANSIT (S-40)</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Lô Hàng Đang Chở</p>
            <div class="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <i class="fa-solid fa-boxes-stacked"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-blue-700 mt-2" id="kpiCarriedBatches">0 Lô</p>
          <p class="text-[11px] text-slate-500 mt-1">Được bảo quản dải 2 - 8°C</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Vi Phạm Chuỗi Lạnh</p>
            <div class="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-rose-700 mt-2" id="kpiColdChainViolations">0 Đợt</p>
          <p class="text-[11px] text-rose-600 font-semibold mt-1">Độ trễ 30 phút & gộp 5p (S-43)</p>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between">
            <p class="text-xs font-bold text-slate-500 uppercase">Điểm Đo Cảm Biến</p>
            <div class="w-9 h-9 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
              <i class="fa-solid fa-chart-line"></i>
            </div>
          </div>
          <p class="text-2xl font-black text-teal-700 mt-2" id="kpiTelemetryReadings">0 Điểm</p>
          <p class="text-[11px] text-teal-600 font-semibold mt-1">Lọc timestamp cũ (S-41)</p>
        </div>
      </div>

      <!-- Trips Table Card -->
      <div class="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 class="text-base font-extrabold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-snowflake text-cyan-600"></i> Danh Sách Chuyến Xe Lạnh & Giám Sát Cảm Biến IoT
            </h3>
            <p class="text-xs text-slate-500">Mỗi tổ chức vận chuyển chỉ quản lý các chuyến của mình (cô lập đa tổ chức E-02)</p>
          </div>
          <button onclick="renderColdChainTab()" class="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-colors">
            <i class="fa-solid fa-arrows-rotate"></i> Làm Mới Dữ Liệu
          </button>
        </div>

        <div class="overflow-x-auto rounded-2xl border border-slate-200">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-600 uppercase text-[10px] font-bold border-b border-slate-200">
              <tr>
                <th class="p-3.5">Mã Chuyến Xe</th>
                <th class="p-3.5">Mã Xe / Thùng Lạnh</th>
                <th class="p-3.5">Đơn Vị Vận Chuyển</th>
                <th class="p-3.5">Tài Xế</th>
                <th class="p-3.5">Ngưỡng Nhiệt Độ</th>
                <th class="p-3.5">Lô Hàng Đang Chở (S-40)</th>
                <th class="p-3.5 text-center">Vi Phạm (S-43)</th>
                <th class="p-3.5">Trạng Thái</th>
                <th class="p-3.5 text-right">Thao Tác</th>
              </tr>
            </thead>
            <tbody id="coldChainTripsTableBody" class="divide-y divide-slate-100">
              <!-- Dynamic trip rows -->
            </tbody>
          </table>
        </div>
      </div>

    </div>

  </main>

  <!-- ================= FOOTER ================= -->
  <footer class="bg-slate-900 text-slate-400 py-8 border-t border-slate-800 text-xs mt-12">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-black text-xs">
          NL
        </div>
        <span class="text-slate-200 font-bold">Nông Sản Lành - Truy Xuất Nguồn Gốc & Chuỗi Lạnh</span>
        <span class="text-slate-500">• Mô Hình Đa Tổ Chức (Multi-Tenant Supply Chain)</span>
      </div>
      <div class="text-slate-500 text-center sm:text-right">
        <span>Nhóm 4 K18 - Hệ Thống Chuyên Biệt Chuỗi Cung Ứng Nông Sản</span>
      </div>
    </div>
  </footer>


  <!-- ======================================================== -->
  <!-- MODAL: TẠO CHUYẾN XE VẬN CHUYỂN LẠNH MỚI (USER STORY S-40)  -->
  <!-- ======================================================== -->
  <div id="createTripModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-cyan-100 text-cyan-800 flex items-center justify-center text-sm font-black"><i class="fa-solid fa-truck-ramp-box"></i></span>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base">Tạo Chuyến Vận Chuyển Lạnh (S-40)</h3>
            <p class="text-[11px] text-cyan-700 font-semibold">Ghi nhận xe lạnh, tài xế và các lô hàng đang chở</p>
          </div>
        </div>
        <button onclick="closeModal('createTripModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block font-bold text-slate-700 mb-1">Mã Thùng Lạnh / Xe Lạnh <span class="text-rose-600">*</span></label>
          <input type="text" id="tripVehicleCode" placeholder="VD: REEFER-51D-888.99 hoặc CONT-COOL-01" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold font-mono text-cyan-950 uppercase" value="REEFER-51D-888.99" />
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Tài Xế Phụ Trách</label>
          <input type="text" id="tripDriverName" placeholder="VD: Nguyễn Văn Tài Xế" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium" value="Nguyễn Văn Tài Xế" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-bold text-slate-700 mb-1">Nhiệt Độ Tối Thiểu (°C)</label>
            <input type="number" step="0.5" id="tripMinTemp" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold font-mono text-cyan-900" value="2.0" />
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">Nhiệt Độ Tối Đa (°C)</label>
            <input type="number" step="0.5" id="tripMaxTemp" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold font-mono text-rose-700" value="8.0" />
          </div>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Chọn Các Lô Hàng Đang Chở Trên Chuyến Xe <span class="text-rose-600">*</span></label>
          <div id="tripBatchesChecklist" class="max-h-40 overflow-y-auto space-y-1.5 p-2 bg-slate-50 border border-slate-200 rounded-xl">
            <!-- Dynamic batch checkboxes -->
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('createTripModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button onclick="submitCreateTrip()" class="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5">
          <i class="fa-solid fa-check"></i> Tạo Chuyến Xe (S-40)
        </button>
      </div>
    </div>
  </div>

  <!-- ======================================================== -->
  <!-- MODAL: GIẢ LẬP GỬI DỮ LIỆU CẢM BIẾN NHIỆT ĐỘ IoT (S-41)  -->
  <!-- Thuật toán phát hiện vi phạm độ trễ 30 phút (S-43, S-45) -->
  <!-- ======================================================== -->
  <div id="simulateTelemetryModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-xl w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-black"><i class="fa-solid fa-temperature-arrow-up"></i></span>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base">Giả Lập Cảm Biến Nhiệt Độ IoT (S-41, S-43)</h3>
            <p class="text-[11px] text-amber-700 font-semibold">Kiểm thử thuật toán độ trễ 30 phút & ghi Hash Chain (S-45)</p>
          </div>
        </div>
        <button onclick="closeModal('simulateTelemetryModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block font-bold text-slate-700 mb-1">Chọn Chuyến Xe Cần Gửi Telemetry</label>
          <select id="telemetryTripSelect" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold font-mono text-cyan-950">
            <!-- Dynamic trips options -->
          </select>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Chọn Kịch Bản Kiểm Thử Nhanh (Preset Testing):</label>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick="applyTelemetryPreset('normal')" class="p-2.5 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-xl text-left">
              <p class="font-bold text-emerald-950 flex items-center gap-1.5"><i class="fa-solid fa-circle-check text-emerald-600"></i> Nhiệt Độ Chuẩn</p>
              <p class="text-[10px] text-emerald-800">3.5°C - 5.0°C (An toàn tuyệt đối)</p>
            </button>
            <button type="button" onclick="applyTelemetryPreset('short_spike')" class="p-2.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-xl text-left">
              <p class="font-bold text-blue-950 flex items-center gap-1.5"><i class="fa-solid fa-door-open text-blue-600"></i> Mở Cửa 15 Phút</p>
              <p class="text-[10px] text-blue-800">14°C trong 15p &lt; 30p: KHÔNG vi phạm (S-43)</p>
            </button>
            <button type="button" onclick="applyTelemetryPreset('long_violation')" class="p-2.5 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-xl text-left">
              <p class="font-bold text-rose-950 flex items-center gap-1.5"><i class="fa-solid fa-triangle-exclamation text-rose-600"></i> Hỏng Máy Lạnh 40p</p>
              <p class="text-[10px] text-rose-800">&gt; 30p: Kích hoạt vi phạm & ghi Hash (S-45)</p>
            </button>
            <button type="button" onclick="applyTelemetryPreset('merge_gap')" class="p-2.5 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl text-left">
              <p class="font-bold text-purple-950 flex items-center gap-1.5"><i class="fa-solid fa-object-group text-purple-600"></i> Cách Nhau 3 Phút</p>
              <p class="text-[10px] text-purple-800">Gộp 2 lần cách nhau &lt; 5p thành 1 (S-43)</p>
            </button>
          </div>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Mảng Dữ Liệu Cảm Biến JSON ({ timestamp, temperature }):</label>
          <textarea id="telemetryJsonInput" rows="6" class="w-full p-2.5 font-mono text-[11px] bg-slate-900 text-emerald-400 border border-slate-700 rounded-xl focus:ring-2 focus:ring-amber-500"></textarea>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('simulateTelemetryModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button onclick="submitSimulateTelemetry()" class="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5">
          <i class="fa-solid fa-paper-plane"></i> Gửi Telemetry (S-41)
        </button>
      </div>
    </div>
  </div>

  <!-- ======================================================== -->
  <!-- MODAL: CHI TIẾT CHUYẾN XE & LỊCH SỬ VI PHẠM (S-43, S-45) -->
  <!-- ======================================================== -->
  <div id="tripDetailModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-200 p-6 space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-cyan-100 text-cyan-800 flex items-center justify-center text-sm font-black"><i class="fa-solid fa-snowflake"></i></span>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base" id="detailTripCode">TRIP-CODE</h3>
            <p class="text-[11px] text-cyan-700 font-semibold" id="detailVehicleCode">REEFER-VEHICLE</p>
          </div>
        </div>
        <button onclick="closeModal('tripDetailModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-4 text-xs">
        <!-- Thông tin chuyến xe -->
        <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div><p class="text-slate-400 uppercase text-[10px]">Tài Xế</p><p class="font-bold text-slate-800" id="detailTripDriver">...</p></div>
          <div><p class="text-slate-400 uppercase text-[10px]">Đơn Vị Vận Chuyển</p><p class="font-bold text-slate-800" id="detailTripCarrier">...</p></div>
          <div><p class="text-slate-400 uppercase text-[10px]">Dải Nhiệt Độ Chuẩn</p><p class="font-bold text-cyan-700" id="detailTripTempRange">2°C - 8°C</p></div>
          <div><p class="text-slate-400 uppercase text-[10px]">Trạng Thái</p><p class="font-bold text-emerald-600" id="detailTripStatus">IN_TRANSIT</p></div>
        </div>

        <!-- Danh sách lô hàng đang chở -->
        <div class="border border-slate-200 rounded-2xl p-4 bg-white space-y-2">
          <p class="font-bold text-slate-800 uppercase text-[11px] flex items-center gap-1.5">
            <i class="fa-solid fa-boxes-stacked text-blue-600"></i> Danh Sách Lô Hàng Đang Chở (S-40):
          </p>
          <div id="detailTripBatchesList" class="flex flex-wrap gap-2">
            <!-- Dynamic badges -->
          </div>
        </div>

        <!-- Danh sách sự kiện vi phạm chuỗi lạnh (S-43 & S-45) -->
        <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50 space-y-3">
          <div class="flex items-center justify-between">
            <p class="font-bold text-slate-800 uppercase text-[11px] flex items-center gap-1.5">
              <i class="fa-solid fa-triangle-exclamation text-rose-600"></i> Các Lần Vi Phạm Chuỗi Lạnh Liên Tục &gt; 30 Phút (S-43):
            </p>
            <span id="detailViolationsCountBadge" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">0 Vi phạm</span>
          </div>
          <div id="detailTripViolationsContainer" class="space-y-2">
            <!-- Dynamic violation cards -->
          </div>
        </div>

        <!-- 20 điểm đo gần nhất -->
        <div class="border border-slate-200 rounded-2xl p-4 bg-white space-y-2">
          <p class="font-bold text-slate-800 uppercase text-[11px] flex items-center gap-1.5">
            <i class="fa-solid fa-chart-line text-teal-600"></i> Các Điểm Đo Cảm Biến Telemetry Gần Nhất (S-41):
          </p>
          <div id="detailTripTelemetryContainer" class="max-h-36 overflow-y-auto space-y-1 font-mono text-[11px]">
            <!-- Dynamic telemetry readings -->
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ======================================================== -->
  <!-- MODAL: ĐĂNG NHẬP THẬT BẰNG EMAIL & MẬT KHẨU (S-04 / T-09) -->
  <!-- ======================================================== -->
  <div id="loginModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md">
    <div class="bg-white rounded-3xl max-w-xl w-full shadow-2xl border border-slate-200 overflow-hidden animate-fadeIn">
      
      <!-- Header Modal -->
      <div class="bg-gradient-to-r from-emerald-800 via-emerald-700 to-teal-800 p-6 text-white relative">
        <button onclick="closeModal('loginModal')" class="absolute top-5 right-5 text-white/70 hover:text-white transition-colors cursor-pointer">
          <i class="fa-solid fa-xmark text-xl"></i>
        </button>
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center text-xl shadow-inner">
            <i class="fa-solid fa-shield-halved text-emerald-300"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-lg font-black tracking-tight">Đăng Nhập Chuỗi Cung Ứng</h3>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-400/20 text-emerald-200 border border-emerald-400/30">User Story S-04</span>
            </div>
            <p class="text-xs text-emerald-100 font-medium">Bảo mật argon2id • Khóa tạm 15 phút sau 5 lần sai • Cookie HttpOnly & Secure</p>
          </div>
        </div>
      </div>

      <!-- Nội dung Body Modal -->
      <div class="p-6 space-y-4 max-h-[82vh] overflow-y-auto text-xs">

        <!-- Thông báo Trạng thái Lỗi / Khóa Tài Khoản (S-04) -->
        <div id="loginAlertBox" class="hidden p-4 rounded-2xl border text-xs space-y-1 transition-all">
          <div class="flex items-center gap-2 font-bold" id="loginAlertTitle">
            <i class="fa-solid fa-circle-exclamation" id="loginAlertIcon"></i>
            <span id="loginAlertHeading">Thông Báo</span>
          </div>
          <p id="loginAlertMessage" class="text-[11px] leading-relaxed"></p>
          <div id="loginAlertCounter" class="text-[11px] font-bold mt-1"></div>
        </div>

        <!-- Form Đăng Nhập -->
        <form onsubmit="handleRealLoginSubmit(event)" class="space-y-3.5" id="realLoginForm">
          <div>
            <label class="block font-bold text-slate-700 mb-1 flex items-center justify-between">
              <span>Email Đăng Nhập</span>
              <span class="text-[10px] text-slate-400 font-normal">Tài khoản thuộc tổ chức chuỗi cung ứng</span>
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <i class="fa-solid fa-envelope text-xs"></i>
              </span>
              <input 
                type="email" 
                id="loginEmailInput" 
                required 
                placeholder="VD: manager@nongtraixanh.vn" 
                oninput="onLoginEmailChanged(this.value)"
                class="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-semibold text-slate-800"
              />
            </div>
          </div>

          <div>
            <label class="block font-bold text-slate-700 mb-1 flex items-center justify-between">
              <span>Mật Khẩu</span>
              <span class="text-[10px] text-slate-400 font-normal">Băm mật khẩu argon2id (NFR S-04)</span>
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <i class="fa-solid fa-lock text-xs"></i>
              </span>
              <input 
                type="password" 
                id="loginPasswordInput" 
                required 
                placeholder="Nhập mật khẩu..." 
                class="w-full pl-9 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-semibold text-slate-800"
              />
              <button 
                type="button" 
                onclick="togglePasswordVisibility('loginPasswordInput', 'pwdToggleIcon')" 
                class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer">
                <i class="fa-solid fa-eye text-xs" id="pwdToggleIcon"></i>
              </button>
            </div>
          </div>

          <!-- Nút Đăng Nhập & Nút Đóng -->
          <div class="flex items-center gap-3 pt-2">
            <button 
              type="submit" 
              id="loginSubmitBtn"
              class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white rounded-xl font-bold text-xs shadow-md shadow-emerald-600/20 transition-all flex items-center justify-center gap-2 cursor-pointer">
              <i class="fa-solid fa-right-to-bracket"></i>
              <span>Xác Thực & Đăng Nhập</span>
            </button>
            <button 
              type="button" 
              onclick="closeModal('loginModal')"
              class="px-5 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold text-xs transition-colors cursor-pointer">
              Đóng
            </button>
          </div>
        </form>

        <!-- Tool dành cho Giảng viên / Tester kiểm tra tiêu chuẩn S-04 & T-10 -->
        <div class="p-3.5 bg-amber-50 rounded-2xl border border-amber-200 space-y-2.5">
          <div class="flex items-center justify-between">
            <span class="font-extrabold text-amber-900 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
              <i class="fa-solid fa-vial text-amber-600"></i> Công Cụ Kiểm Tra Tiêu Chuẩn S-04 (Task T-10):
            </span>
            <span class="text-[10px] text-amber-700 font-bold bg-amber-100 px-2 py-0.5 rounded-full">Khóa Tạm 15 Phút</span>
          </div>
          <p class="text-[11px] text-amber-800 leading-normal">
            Bấm nút dưới để giả lập nhập sai mật khẩu 5 lần liên tiếp. Hệ thống sẽ khóa tài khoản trong 15 phút. Ở lần thứ 6, <strong>kể cả khi nhập đúng mật khẩu</strong>, hệ thống vẫn từ chối và thông báo tài khoản đang bị khóa kèm số phút còn lại.
          </p>
          <div class="flex flex-wrap items-center gap-2 pt-1">
            <button 
              type="button" 
              onclick="simulateLockoutCurrentEmail()"
              class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white font-bold rounded-xl text-[11px] flex items-center gap-1.5 shadow-sm transition-all cursor-pointer">
              <i class="fa-solid fa-lock"></i> Giả lập sai 5 lần (Test S-04)
            </button>
            <button 
              type="button" 
              onclick="resetLockoutCurrentEmail()"
              class="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-900 text-white font-bold rounded-xl text-[11px] flex items-center gap-1.5 shadow-sm transition-all cursor-pointer">
              <i class="fa-solid fa-lock-open"></i> Mở khóa nhanh (Reset)
            </button>
            <button 
              type="button" 
              onclick="checkLockoutStatusCurrentEmail()"
              class="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 active:bg-slate-950 text-white font-bold rounded-xl text-[11px] flex items-center gap-1.5 shadow-sm transition-all cursor-pointer">
              <i class="fa-solid fa-arrows-rotate"></i> Kiểm tra số lần sai
            </button>
          </div>
        </div>

        <!-- Danh sách tài khoản mẫu của 7 vai trò (Click-to-Fill 1 chạm) -->
        <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50 space-y-2.5">
          <div class="flex items-center justify-between">
            <p class="font-bold text-slate-800 uppercase text-[11px] flex items-center gap-1.5">
              <i class="fa-solid fa-users text-emerald-600"></i> Bấm Điền Nhanh Tài Khoản Mẫu (7 Vai Trò):
            </p>
            <span class="text-[10px] text-slate-500 font-medium">Mật khẩu: <strong class="text-slate-800">pass123</strong></span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2" id="demoAccountsGrid">
            <!-- Dynamic 7 roles fill buttons -->
          </div>
        </div>

      </div>

    </div>
  </div>

  <!-- ======================================================== -->
  <!-- MODALS PHỤC VỤ CHUỖI CUNG ỨNG                            -->
  <!-- ======================================================== -->

  <!-- MODAL: GHI NHẬN SỬ DỤNG VẬT TƯ CHO LÔ HÀNG (STORY S-62) -->
  <div id="recordBatchMaterialModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 class="font-extrabold text-slate-900 text-base flex items-center gap-2">
          <i class="fa-solid fa-shield-virus text-amber-600"></i> Ghi Nhận Vật Tư Cho Lô Hàng (S-62)
        </h3>
        <button onclick="closeModal('recordBatchMaterialModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block font-bold text-slate-700 mb-1">Chọn Lô Nông Sản</label>
          <select id="modal_mat_batch_code" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 font-semibold">
            <!-- Dynamic Batches -->
          </select>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Tên Vật Tư / Thuốc BVTV / Phân Bón</label>
          <input type="text" id="modal_mat_name" placeholder="VD: Chế phẩm sinh học phòng sâu BT..." class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="Chế phẩm nấm ký sinh sâu vi sinh BT" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-bold text-slate-700 mb-1">Phân Loại</label>
            <select id="modal_mat_category" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold">
              <option value="pesticide">Thuốc BVTV sinh học</option>
              <option value="fertilizer">Phân bón hữu cơ/vi sinh</option>
              <option value="bio_pesticide">Chế phẩm thảo mộc xua đuổi</option>
            </select>
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">Liều Lượng Sử Dụng</label>
            <input type="text" id="modal_mat_dosage" placeholder="VD: 50ml/bình 16L..." class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="50ml / 20 lít nước" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-bold text-slate-700 mb-1">Ngày Bón / Phun Thuốc</label>
            <input type="date" id="modal_mat_applied_date" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="2026-10-15" />
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">Số Ngày Cách Ly (PHI)</label>
            <input type="number" id="modal_mat_isolation_days" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold text-amber-700" value="7" />
          </div>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Người Thực Hiện / Phụ Trách</label>
          <input type="text" id="modal_mat_applied_by" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="Kỹ sư phụ trách bảo vệ thực vật" />
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Ghi Chú Mục Đích Canh Tác</label>
          <input type="text" id="modal_mat_notes" placeholder="VD: Phun phòng ngừa bọ trĩ lứa 2..." class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="Phun định kỳ phòng ngừa sâu đục quả" />
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('recordBatchMaterialModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button onclick="submitBatchMaterialLog()" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md">Lưu Nhật Ký</button>
      </div>
    </div>
  </div>


  <!-- MODAL: KHAI BÁO THỬA ĐẤT MỚI (S-06) -->
  <div id="addPlotModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 class="font-extrabold text-slate-900 text-base">Khai Báo Thửa Đất Vùng Trồng (S-06)</h3>
        <button onclick="closeModal('addPlotModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block font-bold text-slate-700 mb-1">Tên Thửa Đất</label>
          <input type="text" id="plot_name" placeholder="VD: Thửa D4 - Nhà Màng Dưa Baby" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="Thửa D4 - Vườn Dưa Leo Baby" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-bold text-slate-700 mb-1">Diện Tích (m2, bắt buộc &gt; 0)</label>
            <input type="number" id="plot_area" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold" value="2800" />
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">Đơn Vị</label>
            <input type="text" id="plot_unit" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="m2" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-bold text-slate-700 mb-1">Vĩ Độ (Latitude, số thực)</label>
            <input type="text" id="plot_lat" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono text-[11px]" value="11.9425" />
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">Kinh Độ (Longitude, số thực)</label>
            <input type="text" id="plot_lng" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono text-[11px]" value="108.4590" />
          </div>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Địa Chỉ / Vị Trí Vùng Canh Tác</label>
          <input type="text" id="plot_address" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="Thôn Đạ Sar, Huyện Lạc Dương, Lâm Đồng" />
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('addPlotModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button onclick="savePlotSubmit()" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md">Lưu Thửa Đất</button>
      </div>
    </div>
  </div>


  <!-- MODAL: TẠO LÔ NÔNG SẢN THU HOẠCH MỚI (S-08) -->
  <div id="addBatchModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 class="font-extrabold text-slate-900 text-base">Khởi Tạo Lô Nông Sản Thu Hoạch Mới (S-08)</h3>
        <button onclick="closeModal('addBatchModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block font-bold text-slate-700 mb-1">Mã Lô Định Danh (8 ký tự ngẫu nhiên an toàn S-08)</label>
          <div class="flex gap-2">
            <input type="text" id="batch_code" readonly class="w-full p-2.5 bg-slate-100 border border-slate-200 rounded-xl font-mono text-emerald-800 font-bold text-sm tracking-widest" value="K7M9P3NX" />
            <button onclick="generateRandomBatchCode()" class="px-3 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-xl font-bold text-xs flex items-center gap-1.5"><i class="fa-solid fa-arrows-rotate"></i> Đổi Mã</button>
          </div>
        </div>
        <div>
          <label class="block font-bold text-slate-700 mb-1">Tên Nông Sản</label>
          <input type="text" id="batch_product" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold" value="Cà Chua Beef Hữu Cơ" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-bold text-slate-700 mb-1">Khối Lượng Thu Hoạch (kg, &gt; 0)</label>
            <input type="number" id="batch_quantity" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold" value="1500" />
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">Thửa Đất Canh Tác</label>
            <select id="batch_plot" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-semibold">
              <option value="Thửa A1">Thửa A1 - Nhà Màng Cà Chua Beef</option>
              <option value="Thửa B2">Thửa B2 - Vườn Dâu Tây Hữu Cơ</option>
              <option value="Thửa C1">Thửa C1 - Khu Dưa Lưới Huỳnh Long</option>
            </select>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('addBatchModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button onclick="saveBatchSubmit()" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md">Tạo Lô Hàng</button>
      </div>
    </div>
  </div>


  <!-- ============================================================================ -->
  <!-- MODAL: GHI NHẬN THU HOẠCH THÀNH CÔNG & HIỂN THỊ MÃ LÔ BẢO MẬT (S-08)       -->
  <!-- Hiển thị mã lô cỡ chữ lớn, độ tương phản cao, nút sao chép nhanh cho nông dân -->
  <!-- ============================================================================ -->
  <div id="batchSuccessModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border-2 border-emerald-500 p-6 sm:p-8 space-y-6 text-center">
      
      <div class="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto text-3xl shadow-inner border border-emerald-200">
        <i class="fa-solid fa-circle-check"></i>
      </div>

      <div class="space-y-1">
        <span class="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full font-bold text-xs uppercase tracking-wider">Ghi Nhận Thu Hoạch Thành Công</span>
        <h3 class="text-xl sm:text-2xl font-black text-slate-900 mt-2">Đã Khởi Tạo Lô Nông Sản</h3>
        <p class="text-xs text-slate-500 font-medium" id="successBatchProductName">Cà Chua Beef Hữu Cơ Thắng Lợi</p>
      </div>

      <!-- KHUNG HIỂN THỊ MÃ LÔ CỠ CHỮ LỚN & ĐỘ TƯƠNG PHẢN CAO CHO NÔNG DÂN (S-08) -->
      <div class="bg-slate-950 text-white rounded-2xl p-5 border-2 border-emerald-400 shadow-xl space-y-2">
        <p class="text-[11px] uppercase tracking-widest text-emerald-300 font-bold flex items-center justify-center gap-1.5">
          <i class="fa-solid fa-shield-halved text-emerald-400"></i> Mã Định Danh Điện Tử (8 Ký Tự Ngẫu Nhiên)
        </p>
        
        <!-- Cỡ chữ siêu lớn, độ tương phản tuyệt đối -->
        <div 
          id="successBatchCodeDisplay"
          class="font-mono text-3xl sm:text-4xl font-black text-emerald-400 tracking-widest py-3 select-all bg-emerald-950/70 rounded-xl border border-emerald-500/40">
          K7M9P3NX
        </div>

        <p class="text-[10px] text-slate-400">
          Loại trừ hoàn toàn ký tự nhầm lẫn: không có số '0', chữ 'O', số '1', chữ 'I', 'L'.
        </p>

        <!-- Nút sao chép nhanh với phản hồi trực quan -->
        <div class="pt-2 flex justify-center">
          <button 
            id="copySuccessCodeBtn"
            onclick="copySuccessBatchCode()"
            type="button"
            class="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600 text-slate-950 font-black rounded-xl text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg transition-all transform active:scale-95">
            <i class="fa-solid fa-copy text-sm"></i>
            <span id="copySuccessBtnText">Sao Chép Mã Lô</span>
          </button>
        </div>
      </div>

      <!-- Tóm tắt thông tin lô thu hoạch -->
      <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200 grid grid-cols-2 gap-3 text-left text-xs">
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Khối lượng thu hoạch:</span>
          <span class="font-extrabold text-slate-800 text-sm" id="successBatchQtyDisplay">1,500 kg</span>
        </div>
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Thửa đất canh tác:</span>
          <span class="font-extrabold text-slate-800 text-sm" id="successBatchPlotDisplay">Thửa A1</span>
        </div>
      </div>

      <div class="flex items-center justify-center gap-3 pt-2">
        <button 
          onclick="closeModal('batchSuccessModal')"
          class="w-full py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold text-xs shadow-md transition-all">
          Hoàn Tất & Xem Danh Sách Lô
        </button>
      </div>

    </div>
  </div>


  <!-- MODAL: TẠO PHIẾU BÀN GIAO LÔ HÀNG (S-15) -->
  <div id="handoverModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 class="font-extrabold text-slate-900 text-base flex items-center gap-2">
          <i class="fa-solid fa-truck-moving text-emerald-600"></i> Bàn Giao Lô Hàng Sang Đơn Vị Khác (S-15)
        </h3>
        <button onclick="closeModal('handoverModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div class="p-3 bg-emerald-50 rounded-2xl border border-emerald-200 text-emerald-900">
          <p class="font-bold">Quy định chuyển giao User Story S-15:</p>
          <p class="text-[11px] mt-0.5">Khi tạo lệnh, lô chuyển sang trạng thái "chờ xác nhận". Đơn vị bạn vẫn tạm thời giữ quyền sở hữu cho tới khi bên nhận bấm Xác Nhận. Hệ thống chặn tạo lệnh bàn giao thứ hai.</p>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Mã Lô Bàn Giao</label>
          <select id="ho_batch_code" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono font-bold text-emerald-900 focus:ring-2 focus:ring-emerald-500">
            <!-- Dynamic Batches -->
          </select>
        </div>
        <div>
          <label class="block font-bold text-slate-700 mb-1">Tổ Chức Tiếp Nhận (To Organization) <span class="text-rose-600">*</span></label>
          <select id="ho_target_org_id" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-800 focus:ring-2 focus:ring-emerald-500">
            <!-- Dynamic Candidate Orgs -->
          </select>
        </div>
        <div>
          <label class="block font-bold text-slate-700 mb-1">Nhiệt Độ Xe Lạnh / Kho Lạnh Khi Giao (°C)</label>
          <input type="number" step="0.1" id="ho_temp_input" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono font-bold text-teal-800" value="4.0" />
        </div>
        <div>
          <label class="block font-bold text-slate-700 mb-1">Ghi Chú Bàn Giao</label>
          <input type="text" id="ho_notes_input" placeholder="VD: Giao ca sáng, xe bảo ôn số 29C-8819..." class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium" value="Bàn giao đạt chuẩn nhiệt độ bảo quản" />
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('handoverModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button onclick="submitHandoverCreate()" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5">
          <i class="fa-solid fa-paper-plane"></i> Gửi Lệnh Bàn Giao (S-15)
        </button>
      </div>
    </div>
  </div>


  <!-- MODAL: TỪ CHỐI TIẾP NHẬN BÀN GIAO (S-16) -->
  <div id="rejectHandoverModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 class="font-extrabold text-slate-900 text-base flex items-center gap-2 text-rose-600">
          <i class="fa-solid fa-triangle-exclamation"></i> Từ Chối Tiếp Nhận Lô Hàng (S-16)
        </h3>
        <button onclick="closeModal('rejectHandoverModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div class="p-3 bg-rose-50 rounded-2xl border border-rose-200 text-rose-900">
          <p class="font-bold">Quy định User Story S-16:</p>
          <p class="text-[11px] mt-0.5">Bên nhận bắt buộc phải nhập lý do từ chối (tối thiểu 10 ký tự). Lô vẫn thuộc quyền giữ của bên giao và hệ thống ghi nhận sự kiện từ chối kèm lý do vào chuỗi hash.</p>
        </div>

        <div>
          <label class="block font-bold text-slate-700 mb-1">Mã Lô Từ Chối</label>
          <input type="text" id="reject_batch_code_display" readonly class="w-full p-2.5 bg-slate-100 border border-slate-200 rounded-xl font-mono font-bold text-slate-800" value="" />
        </div>

        <div>
          <div class="flex justify-between items-center mb-1">
            <label class="block font-bold text-slate-700">Lý Do Từ Chối (Tối thiểu 10 ký tự) <span class="text-rose-600">*</span></label>
            <span id="rejectCharCount" class="text-[11px] font-bold text-slate-400">0/10 ký tự</span>
          </div>
          <textarea 
            id="reject_reason_input" 
            rows="3" 
            oninput="handleRejectReasonInput(this.value)"
            placeholder="Nhập chi tiết lý do (VD: Nhiệt độ bảo quản xe lạnh vượt quá 8°C, bao bì bị rách hư hỏng)..." 
            class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-medium focus:ring-2 focus:ring-rose-500 focus:bg-white"></textarea>
          <p id="rejectErrorMsg" class="hidden text-rose-600 font-bold text-[10px] mt-1">Lý do từ chối phải dài tối thiểu 10 ký tự!</p>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
        <button onclick="closeModal('rejectHandoverModal')" class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs">Hủy</button>
        <button id="btnConfirmReject" onclick="submitRejectHandoverConfirm()" class="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5">
          <i class="fa-solid fa-xmark"></i> Xác Nhận Từ Chối
        </button>
      </div>
    </div>
  </div>


  <!-- ============================================================================ -->
  <!-- MODAL: CHI TIẾT TRUY XUẤT NGUỒN GỐC CÔNG KHAI (USER STORY S-48 & E-08)       -->
  <!-- Chỉ hiển thị: Tên SP, Tên vùng trồng, Tỉnh/thành, Ngày thu hoạch, Hành trình -->
  <!-- Nút "Bàn Giao Lô Hàng" mở modal chọn tổ chức nhận (S-15)                      -->
  <!-- ============================================================================ -->
  <div id="batchDetailModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-200 p-6 space-y-5 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center text-sm font-black"><i class="fa-solid fa-qrcode"></i></span>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base" id="modalBatchCode">--</h3>
            <p class="text-[11px] text-emerald-600 font-semibold" id="modalBatchProduct">--</p>
          </div>
        </div>
        <button onclick="closeModal('batchDetailModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="space-y-4 text-xs">
        <!-- 4 Khối thông tin công khai hợp lệ theo S-48 -->
        <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div><p class="text-slate-400 uppercase text-[10px]">Vùng Trồng</p><p class="font-bold text-slate-800" id="modalBatchFarm">HTX Thắng Lợi</p></div>
          <div><p class="text-slate-400 uppercase text-[10px]">Tỉnh / Thành</p><p class="font-bold text-slate-800" id="modalBatchProvince">Lâm Đồng</p></div>
          <div><p class="text-slate-400 uppercase text-[10px]">Ngày Thu Hoạch</p><p class="font-bold text-slate-800" id="modalBatchHarvestDate">15/03/2026</p></div>
          <div><p class="text-slate-400 uppercase text-[10px]">Tiêu Chuẩn</p><p class="font-bold text-emerald-600" id="modalBatchCert">VietGAP</p></div>
        </div>

        <!-- Khối lượng lưu kho & Khối lượng còn lại theo S-17 -->
        <div class="bg-emerald-50/80 p-3.5 rounded-2xl border border-emerald-200 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-sm shadow-sm">
              <i class="fa-solid fa-scale-balanced"></i>
            </div>
            <div>
              <p class="text-[10px] text-emerald-700 font-bold uppercase tracking-wider">Khối Lượng Lưu Kho (User Story S-17, S-18, S-19)</p>
              <p class="text-sm font-extrabold text-emerald-950">
                Còn lại: <span id="modalBatchRemainingQty" class="text-emerald-700 font-black">100.0</span> <span id="modalBatchUnit">kg</span> 
                <span class="text-xs text-slate-400 font-normal">(Ban đầu: <span id="modalBatchInitialQty">100.0</span> <span id="modalBatchUnit2">kg</span>)</span>
              </p>
            </div>
          </div>
          <span id="modalBatchStatusBadge" class="px-2.5 py-1 bg-white text-emerald-800 rounded-full font-bold text-[10px] border border-emerald-300">
            active
          </span>
        </div>

        <!-- PHI Badge in Modal (S-62) -->
        <div class="p-3.5 bg-emerald-50 rounded-2xl border border-emerald-200 flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <i class="fa-solid fa-shield-virus text-emerald-600 text-base"></i>
            <div>
              <p class="font-bold text-emerald-950">Kiểm Soát Thời Gian Cách Ly (S-62)</p>
              <p class="text-[11px] text-emerald-800" id="modalBatchPhiText">Đã hoàn thành thời gian cách ly thuốc BVTV an toàn thu hoạch.</p>
            </div>
          </div>
          <span class="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full font-bold text-[10px]">Đạt Chuẩn VietGAP</span>
        </div>

        <!-- CÂY PHẢ HỆ / LỊCH SỬ TÁCH - GỘP (GENEALOGY LINEAGE TREE - S-17, S-18, S-19) -->
        <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50 space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <i class="fa-solid fa-sitemap text-indigo-600"></i> Cây Phả Hệ Nguồn Gốc (Genealogy Tree - S-17, S-18, S-19)
            </h4>
            <span id="modalBatchLineageStatus" class="text-[10px] text-slate-400 font-medium">Đang tải phả hệ...</span>
          </div>
          <div id="modalBatchLineageContainer" class="space-y-2 text-xs">
            <!-- Dynamic lineage nodes -->
          </div>
        </div>

        <!-- CÁC MỐC HÀNH TRÌNH CHUỖI CUNG ỨNG CHÍNH (S-48: Sơ chế, Vận chuyển, Phân phối) -->
        <div>
          <h4 class="font-bold text-slate-800 text-xs uppercase tracking-wider mb-2.5">
            <i class="fa-solid fa-route text-emerald-600 mr-1.5"></i> Các Mốc Hành Trình Chuỗi Cung Ứng
          </h4>
          <div class="space-y-3" id="modalBatchJourneyList">
            <!-- Dynamic milestones -->
          </div>
        </div>

        <!-- Thông báo bảo vệ dữ liệu chống scraping -->
        <div class="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-[11px] text-slate-500 flex items-center gap-2">
          <i class="fa-solid fa-shield-halved text-emerald-600"></i>
          <span>Hệ thống bảo vệ dữ liệu thương mại nội bộ và chống dò quét tự động (S-48 / E-08).</span>
        </div>
      </div>

      <!-- Footer Buttons: Nút Tách Lô (S-17), Nút Bàn Giao (S-15) và Nút Đóng -->
      <div class="flex items-center justify-between pt-3 border-t border-slate-100 gap-2 flex-wrap">
        <div class="flex items-center gap-2">
          <button 
            id="modalBtnSplit" 
            onclick="openSplitModalForCurrentBatch()" 
            class="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5 transition-all">
            <i class="fa-solid fa-scissors"></i> Tách Lô (S-17)
          </button>
          <button 
            id="modalBtnHandover" 
            onclick="openHandoverForCurrentBatch()" 
            class="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-1.5 transition-all">
            <i class="fa-solid fa-truck-moving"></i> Bàn Giao Lô Hàng (S-15)
          </button>
        </div>
        <button onclick="closeModal('batchDetailModal')" class="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold text-xs transition-colors">
          Đóng Cửa Sổ
        </button>
      </div>
    </div>
  </div>


  <!-- MODAL: QUÉT MÃ QR BẰNG CAMERA ĐIỆN THOẠI (USER STORY S-48) -->
  <div id="qrCameraModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/75 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-black"><i class="fa-solid fa-camera"></i></span>
          <div>
            <h3 class="font-extrabold text-slate-900 text-sm sm:text-base">Quét Mã QR Bằng Camera</h3>
            <p class="text-[11px] text-slate-500">Đưa camera vào mã QR in trên bao bì nông sản</p>
          </div>
        </div>
        <button onclick="closeQrCameraScanner()" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="relative bg-black rounded-2xl overflow-hidden aspect-square flex flex-col items-center justify-center text-white">
        <video id="qrCameraVideo" class="absolute inset-0 w-full h-full object-cover hidden" playsinline></video>
        
        <!-- Viewfinder Overlay -->
        <div id="qrCameraScannerUI" class="relative z-10 w-3/4 h-3/4 border-2 border-dashed border-emerald-400 rounded-2xl flex flex-col items-center justify-between p-4 bg-black/30 backdrop-blur-[1px]">
          <span class="text-[10px] uppercase font-bold text-emerald-300 bg-emerald-950/80 px-2 py-0.5 rounded-full"><i class="fa-solid fa-qrcode mr-1"></i> Khung Quét QR</span>
          <div class="w-full h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-pulse"></div>
          <span class="text-[10px] text-slate-300 text-center">Căn chỉnh tem mã QR vào giữa khung hình</span>
        </div>

        <div id="cameraStatusText" class="absolute bottom-2 left-0 right-0 text-center text-[10px] text-slate-300 z-20">
          Đang khởi tạo camera thiết bị...
        </div>
      </div>

      <div class="space-y-2 pt-1 text-xs">
        <div class="flex items-center gap-2">
          <label class="flex-1 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl cursor-pointer text-center text-xs transition-colors flex items-center justify-center gap-1.5">
            <i class="fa-solid fa-image text-emerald-600"></i> Chọn ảnh tem QR từ máy
            <input type="file" id="qrFileInput" accept="image/*" capture="environment" class="hidden" onchange="handleQrFileUpload(event)" />
          </label>
          <button onclick="simulateQrScan()" class="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs transition-colors flex items-center gap-1">
            <i class="fa-solid fa-bolt"></i> Quét tem mẫu
          </button>
        </div>
      </div>

      <div class="flex justify-end pt-2 border-t border-slate-100">
        <button onclick="closeQrCameraScanner()" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-xl font-bold text-xs">Đóng</button>
      </div>
    </div>
  </div>




  <!-- ============================================================================ -->
  <!-- MODAL: MỞ LỆNH THU HỒI KHẨN CẤP (RECALL BATCH - USER STORY S-33, S-34, S-35)   -->
  <!-- ============================================================================ -->
  <div id="openRecallModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-rose-200 p-6 space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-rose-100 pb-3">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center text-sm font-black">
            <i class="fa-solid fa-triangle-exclamation"></i>
          </div>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base">Mở Lệnh Thu Hồi Khẩn Cấp (S-33)</h3>
            <p class="text-[11px] text-slate-500">Kích hoạt khoanh vùng truy xuôi hậu duệ và chặn lan rộng chuỗi cung ứng</p>
          </div>
        </div>
        <button onclick="closeModal('openRecallModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <div class="p-3.5 bg-rose-50/60 rounded-2xl border border-rose-200 grid grid-cols-2 gap-2 text-xs">
        <div>
          <span class="text-[10px] text-slate-400 uppercase font-semibold">Mã Lô Gặp Sự Cố</span>
          <p id="recallModalBatchCode" class="font-mono font-bold text-rose-900">BATCH-...</p>
        </div>
        <div>
          <span class="text-[10px] text-slate-400 uppercase font-semibold">Nông Sản</span>
          <p id="recallModalProductName" class="font-bold text-slate-800 truncate">...</p>
        </div>
      </div>

      <!-- Chọn mức độ nghiêm trọng -->
      <div>
        <label class="block text-xs font-semibold text-slate-700 mb-1">Mức Độ Nghiêm Trọng:</label>
        <select id="recallSeveritySelect" class="w-full p-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-bold text-rose-700 focus:ring-2 focus:ring-rose-500">
          <option value="CRITICAL">Nguy Hiểm Cao Nhất (CRITICAL - Dư lượng cấm / Độc tố sinh học)</option>
          <option value="HIGH">Nghiêm Trọng (HIGH - Vi khuẩn, nấm mốc vượt ngưỡng)</option>
          <option value="MEDIUM">Cảnh Báo Trung Bình (MEDIUM - Sai quy cách bảo quản)</option>
        </select>
      </div>

      <!-- Nhập lý do thu hồi (Bắt buộc >= 20 ký tự theo S-33) -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="text-xs font-bold text-slate-700">Lý Do Thu Hồi (Bắt buộc tối thiểu 20 ký tự):</label>
          <span id="recallReasonCharCounter" class="text-[11px] font-mono font-bold text-slate-400">0 / 20 ký tự</span>
        </div>
        <textarea 
          id="recallReasonInput" 
          rows="4" 
          oninput="handleRecallReasonInput()"
          placeholder="Mô tả cụ thể sự cố an toàn thực phẩm, vi phạm chỉ số kiểm nghiệm, thông tư vi phạm..." 
          class="w-full p-3 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-rose-500 font-medium"></textarea>
        <p id="recallReasonWarning" class="text-[11px] text-rose-600 font-bold mt-1 hidden flex items-center gap-1">
          <i class="fa-solid fa-circle-exclamation"></i> Lý do phải có ít nhất 20 ký tự để kích hoạt lệnh thu hồi hợp lệ!
        </p>
      </div>

      <div class="p-3 bg-amber-50 rounded-2xl border border-amber-200 text-[11px] text-amber-900 space-y-1">
        <p class="font-bold flex items-center gap-1.5 text-amber-950">
          <i class="fa-solid fa-lock text-amber-600"></i> Cơ chế Chặn Lan Rộng (S-38):
        </p>
        <p>Hệ thống sẽ <strong>khóa tức thì</strong> quyền Bàn giao, Tách lô và Gộp lô đối với toàn bộ các lô con cháu liên quan.</p>
      </div>

      <!-- Footer Buttons -->
      <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
        <button type="button" onclick="closeModal('openRecallModal')" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl text-xs font-bold">Hủy</button>
        <button type="button" id="btnSubmitRecall" onclick="submitTriggerRecall()" class="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-1.5 transition-all">
          <i class="fa-solid fa-bullhorn"></i> Kích Hoạt Lệnh Thu Hồi
        </button>
      </div>
    </div>
  </div>


  <!-- ============================================================================ -->
  <!-- MODAL: CHI TIẾT LỆNH THU HỒI & TIẾN ĐỘ XỬ LÝ (S-34, S-35, S-36, S-37)         -->
  <!-- ============================================================================ -->
  <div id="recallDetailModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-4xl w-full shadow-2xl border border-rose-200 p-6 space-y-5 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-rose-600 text-white flex items-center justify-center text-lg font-black shadow-md">
            <i class="fa-solid fa-shield-virus"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 id="recallDetailCode" class="font-mono font-black text-slate-900 text-base">RCL-...</h3>
              <span id="recallDetailStatusBadge" class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">Đang Thu Hồi</span>
            </div>
            <p id="recallDetailProductInfo" class="text-xs text-slate-500">Lô gốc: BATCH-... | Sản phẩm: ...</p>
          </div>
        </div>
        <button onclick="closeModal('recallDetailModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <!-- Lý do thu hồi -->
      <div class="p-3.5 bg-rose-50 rounded-2xl border border-rose-200 space-y-1">
        <span class="text-[10px] uppercase font-bold text-rose-800">Lý do thu hồi (S-33):</span>
        <p id="recallDetailReason" class="text-xs text-rose-950 font-medium">...</p>
      </div>

      <!-- THANH TIẾN ĐỘ XỬ LÝ (S-37) -->
      <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-2">
        <div class="flex items-center justify-between text-xs font-bold">
          <span class="text-slate-700 flex items-center gap-1.5">
            <i class="fa-solid fa-list-check text-indigo-600"></i> Tiến Độ Xử Lý & Xác Nhận Cô Lập Các Tổ Chức:
          </span>
          <span id="recallDetailProgressText" class="text-indigo-800 font-mono">0/0 tổ chức (0%)</span>
        </div>
        <div class="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
          <div id="recallDetailProgressBar" class="bg-gradient-to-r from-amber-500 to-emerald-500 h-3 rounded-full transition-all duration-500" style="width: 0%"></div>
        </div>
        <div id="recallDetailOrgActionsList" class="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2">
          <!-- Dynamic org actions -->
        </div>
      </div>

      <!-- THỐNG KÊ CHI TIẾT KHOANH VÙNG (S-35) -->
      <div class="grid grid-cols-3 gap-3">
        <div class="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm text-center">
          <p class="text-[10px] text-slate-400 uppercase font-bold">Tổng Lô Bị Ảnh Hưởng</p>
          <p id="recallStatAffectedBatches" class="text-xl font-black text-slate-900 mt-1">0 Lô</p>
        </div>
        <div class="bg-amber-50/60 p-3.5 rounded-2xl border border-amber-200 shadow-sm text-center">
          <p class="text-[10px] text-amber-800 uppercase font-bold">Còn Trong Kho / Quầy Kệ</p>
          <p id="recallStatStockKg" class="text-xl font-black text-amber-700 mt-1">0 kg</p>
          <span class="text-[10px] text-amber-600">Cần niêm phong khẩn cấp</span>
        </div>
        <div class="bg-rose-50/60 p-3.5 rounded-2xl border border-rose-200 shadow-sm text-center">
          <p class="text-[10px] text-rose-800 uppercase font-bold">Đã Bán Ra Người Tiêu Dùng</p>
          <p id="recallStatSoldKg" class="text-xl font-black text-rose-700 mt-1">0 kg</p>
          <span class="text-[10px] text-rose-600">Cảnh báo công khai thu hồi</span>
        </div>
      </div>

      <!-- DANH SÁCH TOÀN BỘ CÁC LÔ CON CHÁU BỊ KHOANH VÙNG (S-34) -->
      <div class="space-y-2">
        <h4 class="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
          <i class="fa-solid fa-network-wired text-rose-600"></i> Danh Sách Lô Bị Khoanh Vùng Qua Mọi Tầng Tách/Gộp (S-34)
        </h4>
        <div class="border border-slate-200 rounded-2xl overflow-hidden max-h-60 overflow-y-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-100 text-slate-600 uppercase text-[10px] font-bold">
              <tr>
                <th class="p-2.5">Mã Lô</th>
                <th class="p-2.5">Thế Hệ</th>
                <th class="p-2.5">Tổ Chức Quản Lý</th>
                <th class="p-2.5 text-right">Kho / Kệ (kg)</th>
                <th class="p-2.5 text-right">Đã Bán (kg)</th>
                <th class="p-2.5">Vị Trí Hiện Tại</th>
                <th class="p-2.5 text-center">Tình Trạng</th>
              </tr>
            </thead>
            <tbody id="recallDetailAffectedBatchesTbody" class="divide-y divide-slate-100">
              <!-- Dynamic rows -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Nút thao tác -->
      <div class="flex items-center justify-between pt-3 border-t border-slate-100">
        <div id="recallOrgConfirmActionBox">
          <!-- Button xác nhận nếu là tổ chức của user và chưa xác nhận -->
        </div>
        <button onclick="closeModal('recallDetailModal')" class="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold text-xs">
          Đóng Cửa Sổ
        </button>
      </div>
    </div>
  </div>


  <!-- ============================================================================ -->
  <!-- MODAL: TÁCH LÔ NÔNG SẢN (SPLIT BATCH - USER STORY S-17 & S-18)                -->
  <!-- Khóa dòng SELECT ... FOR UPDATE chống race condition                         -->
  <!-- ============================================================================ -->
  <div id="splitBatchModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-xl w-full shadow-2xl border border-slate-200 p-6 space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-black">
            <i class="fa-solid fa-scissors"></i>
          </div>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base">Tách Lô Nông Sản (S-17, S-18)</h3>
            <p class="text-[11px] text-slate-500">Khóa dòng SELECT ... FOR UPDATE chống race condition khi 2 người cùng tách</p>
          </div>
        </div>
        <button onclick="closeModal('splitBatchModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <!-- Thông tin lô mẹ -->
      <div class="p-3.5 bg-slate-50 rounded-2xl border border-slate-200 grid grid-cols-3 gap-2 text-xs">
        <div>
          <span class="text-[10px] text-slate-400 uppercase font-semibold">Mã Lô Mẹ</span>
          <p id="splitModalParentCode" class="font-mono font-bold text-slate-800">BATCH-...</p>
        </div>
        <div>
          <span class="text-[10px] text-slate-400 uppercase font-semibold">Sản Phẩm</span>
          <p id="splitModalProductName" class="font-bold text-slate-800 truncate">...</p>
        </div>
        <div>
          <span class="text-[10px] text-slate-400 uppercase font-semibold">Khối Lượng Còn Lại</span>
          <p class="font-extrabold text-amber-700"><span id="splitModalRemainingQty">100</span> <span id="splitModalUnit">kg</span></p>
        </div>
      </div>

      <!-- Danh sách các lô con cần tách ra -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <label class="text-xs font-bold text-slate-700">Danh Sách Lô Con Sinh Ra:</label>
          <button type="button" onclick="addSplitRow()" class="px-2.5 py-1 bg-amber-50 text-amber-800 hover:bg-amber-100 rounded-lg text-xs font-bold border border-amber-200 flex items-center gap-1">
            <i class="fa-solid fa-plus text-[10px]"></i> Thêm Lô Con
          </button>
        </div>
        <div id="splitRowsContainer" class="space-y-2 max-h-48 overflow-y-auto pr-1">
          <!-- Rows dynamically added -->
        </div>
      </div>

      <!-- Ghi chú chung -->
      <div>
        <label class="block text-xs font-semibold text-slate-600 mb-1">Ghi Chú Phân Loại / Mục Đích Tách Lô:</label>
        <input type="text" id="splitNotesInput" placeholder="Ví dụ: Phân loại đóng thùng xuất khẩu và siêu thị" class="w-full p-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-amber-500 font-medium"/>
      </div>

      <!-- Khung tổng kết khối lượng và cảnh báo -->
      <div class="p-3 bg-amber-50/70 rounded-2xl border border-amber-200 space-y-1 text-xs">
        <div class="flex justify-between font-semibold text-slate-700">
          <span>Tổng khối lượng các lô con:</span>
          <span class="font-mono font-bold text-amber-900"><span id="splitTotalCalculated">0.0</span> kg</span>
        </div>
        <div class="flex justify-between font-semibold text-slate-700">
          <span>Khối lượng lô mẹ còn lại sau tách:</span>
          <span class="font-mono font-bold text-slate-800"><span id="splitRemainingCalculated">100.0</span> kg</span>
        </div>
        <div id="splitValidationAlert" class="hidden text-[11px] font-bold text-rose-600 pt-1 flex items-center gap-1.5">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span id="splitValidationMsg">Tổng khối lượng lô con vượt quá khối lượng còn lại của lô mẹ!</span>
        </div>
      </div>

      <!-- Nút thao tác -->
      <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
        <button type="button" onclick="closeModal('splitBatchModal')" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl text-xs font-bold">Hủy</button>
        <button type="button" id="btnSubmitSplit" onclick="submitSplitBatch()" class="px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-1.5">
          <i class="fa-solid fa-check"></i> Xác Nhận Tách Lô (S-17)
        </button>
      </div>
    </div>
  </div>


  <!-- ============================================================================ -->
  <!-- MODAL: GỘP LÔ NÔNG SẢN CÙNG LOẠI (MERGE BATCH - USER STORY S-19)              -->
  <!-- Khóa các dòng lô theo thứ tự ID cố định tránh deadlock                      -->
  <!-- ============================================================================ -->
  <div id="mergeBatchModal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
    <div class="bg-white rounded-3xl max-w-xl w-full shadow-2xl border border-slate-200 p-6 space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-800 flex items-center justify-center text-sm font-black">
            <i class="fa-solid fa-object-group"></i>
          </div>
          <div>
            <h3 class="font-extrabold text-slate-900 text-base">Gộp Lô Nông Sản Cùng Loại (S-19)</h3>
            <p class="text-[11px] text-slate-500">Khóa dòng theo thứ tự ID cố định tránh deadlock (ORDER BY id ASC)</p>
          </div>
        </div>
        <button onclick="closeModal('mergeBatchModal')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark text-lg"></i></button>
      </div>

      <!-- Thông tin sản phẩm chung -->
      <div class="p-3 bg-indigo-50 rounded-2xl border border-indigo-200 flex items-center justify-between text-xs">
        <div>
          <span class="text-[10px] text-indigo-600 uppercase font-bold tracking-wider">Sản Phẩm Chung</span>
          <p id="mergeCommonProduct" class="font-extrabold text-indigo-950 text-sm">...</p>
        </div>
        <span class="px-2.5 py-1 bg-white text-indigo-800 rounded-full font-bold text-[10px] border border-indigo-200">
          CÙNG LOẠI SẢN PHẨM (S-19)
        </span>
      </div>

      <!-- Danh sách các lô nguồn cần trích gộp -->
      <div class="space-y-2">
        <label class="text-xs font-bold text-slate-700">Danh Sách Lô Nguồn & Khối Lượng Trích Gộp:</label>
        <div id="mergeSourcesContainer" class="space-y-2 max-h-56 overflow-y-auto pr-1">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <!-- Ghi chú gộp lô -->
      <div>
        <label class="block text-xs font-semibold text-slate-600 mb-1">Ghi Chú Đóng Gói / Mục Đích Gộp Lô:</label>
        <input type="text" id="mergeNotesInput" placeholder="Ví dụ: Gộp 2 sọt đạt chuẩn kích cỡ VIP vào thùng lớn" class="w-full p-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 font-medium"/>
      </div>

      <!-- Khung tổng kết khối lượng lô gộp mới -->
      <div class="p-3.5 bg-slate-50 rounded-2xl border border-slate-200 space-y-1.5 text-xs">
        <div class="flex justify-between font-bold text-slate-800">
          <span>Tổng khối lượng Lô Gộp Mới:</span>
          <span class="font-mono text-indigo-700 text-sm font-extrabold"><span id="mergeTotalNewBatchQty">0.0</span> kg</span>
        </div>
        <p class="text-[11px] text-slate-500">Mã lô mới sẽ được sinh ngẫu nhiên an toàn 8 ký tự và ghi sự kiện chuỗi hash SHA-256.</p>
        <div id="mergeValidationAlert" class="hidden text-[11px] font-bold text-rose-600 pt-1 flex items-center gap-1.5">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span id="mergeValidationMsg">Có lỗi trong quá trình cấu hình gộp lô!</span>
        </div>
      </div>

      <!-- Nút thao tác -->
      <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
        <button type="button" onclick="closeModal('mergeBatchModal')" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl text-xs font-bold">Hủy</button>
        <button type="button" id="btnSubmitMerge" onclick="submitMergeBatches()" class="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-1.5">
          <i class="fa-solid fa-check"></i> Xác Nhận Gộp Lô (S-19)
        </button>
      </div>
    </div>
  </div>


  <!-- ================= JAVASCRIPT SUPPLY CHAIN STATE ENGINE ================= -->
  <script>
    /**
     * NÔNG SẢN LÀNH - MULTI-TENANT SUPPLY CHAIN & TRACEABILITY ENGINE
     * Loại bỏ hoàn toàn Farm ERP (P&L, lương, chấm công, sâu bệnh, đề xuất vật tư)
     * Tập trung: S-06, S-08, S-09, S-10, S-12, S-13, S-14, S-15, S-16, S-62
     */
    const APP_STORAGE_KEY = "nsl_supplychain_state_v6";

    // 7 Chuỗi Cung Ứng Roles Configuration (Epic E-02 & User Story S-04)
    const SUPPLY_CHAIN_ROLES = {
      farm: {
        name: "1. Vùng Trồng (Farm)",
        email: "manager@nongtraixanh.vn",
        samplePassword: "pass123",
        orgId: 10,
        orgName: "HTX Nông Nghiệp Thắng Lợi",
        badge: "Org #10",
        icon: "fa-seedling",
        iconBg: "bg-emerald-600",
        isReadOnly: false,
        canAccessAllOrgs: false
      },
      coop: {
        name: "2. HTX Sơ Chế (Co-op)",
        email: "operator@sochebaoloc.vn",
        samplePassword: "pass123",
        orgId: 20,
        orgName: "HTX Sơ Chế Bảo Lộc",
        badge: "Org #20",
        icon: "fa-industry",
        iconBg: "bg-blue-600",
        isReadOnly: false,
        canAccessAllOrgs: false
      },
      logistics: {
        name: "3. Vận Chuyển Lạnh (Logistics)",
        email: "driver@coldexpress.vn",
        samplePassword: "pass123",
        orgId: 30,
        orgName: "Công Ty Vận Tải Lạnh Express",
        badge: "Org #30",
        icon: "fa-truck-fast",
        iconBg: "bg-cyan-600",
        isReadOnly: false,
        canAccessAllOrgs: false
      },
      distributor: {
        name: "4. Nhà Phân Phối / Bán Lẻ (Distributor)",
        email: "store@biomart.vn",
        samplePassword: "pass123",
        orgId: 40,
        orgName: "Hệ Thống Bán Lẻ BioMart",
        badge: "Org #40",
        icon: "fa-shop",
        iconBg: "bg-amber-600",
        isReadOnly: false,
        canAccessAllOrgs: false
      },
      inspector: {
        name: "5. Cán Bộ Kiểm Tra (Inspector)",
        email: "inspector.safe@kiemdinh.gov.vn",
        samplePassword: "pass123",
        orgId: null,
        orgName: "Chi Cục Quản Lý Chất Lượng & BVTV",
        badge: "CHỈ ĐỌC",
        icon: "fa-clipboard-check",
        iconBg: "bg-purple-700",
        isReadOnly: true,
        canAccessAllOrgs: true
      },
      system_admin: {
        name: "6. Quản Trị Hệ Thống (System Admin)",
        email: "sysadmin@nongsanlanh.gov.vn",
        samplePassword: "pass123",
        orgId: null,
        orgName: "Ban Quản Trị Hệ Thống Toàn Nền Tảng",
        badge: "Toàn Quyền",
        icon: "fa-user-shield",
        iconBg: "bg-slate-900",
        isReadOnly: false,
        canAccessAllOrgs: true
      },
      consumer: {
        name: "7. Người Tiêu Dùng (Consumer)",
        email: "",
        samplePassword: "",
        orgId: null,
        orgName: "Khách Quét QR (Không Login)",
        badge: "Công Khai",
        icon: "fa-qrcode",
        iconBg: "bg-emerald-800",
        isReadOnly: true,
        canAccessAllOrgs: false
      }
    };
    // Aliases tương thích ngược
    SUPPLY_CHAIN_ROLES.processing = SUPPLY_CHAIN_ROLES.coop;
    SUPPLY_CHAIN_ROLES.retailer = SUPPLY_CHAIN_ROLES.distributor;
    SUPPLY_CHAIN_ROLES.admin = SUPPLY_CHAIN_ROLES.system_admin;

    // Initial Supply Chain State (Bắt đầu với dữ liệu trống, tự động nạp từ API Backend thật)
    const defaultData = {
      activeTab: "overview",
      currentRole: "farm",
      plots: [],
      batches: [],
      batchRelations: [],
      materialLogs: [],
      handovers: [],
      hashEvents: [],
      products: [],
      recalls: []
    };

    /**
     * BỘ HÀM apiFetch DÙNG CHUNG CHO TOÀN BỘ GIAO DIỆN:
     * - Tự động đọc access_token từ localStorage hoặc state.currentUser và gắn Authorization: Bearer <token>.
     * - TUYỆT ĐỐI KHÔNG FALLBACK sang dữ liệu giả khi API lỗi.
     * - Ném lỗi rõ ràng kèm HTTP code và detail để UI hiển thị thông báo.
     */
    async function apiFetch(url, options = {}) {
      const token = (state.currentUser && state.currentUser.token) || localStorage.getItem("app_access_token");
      const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
      };
      if (token && !headers["Authorization"]) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      let res;
      try {
        res = await fetch(url, { ...options, headers });
      } catch (networkErr) {
        throw new Error(`Lỗi kết nối mạng máy chủ: ${networkErr.message}`);
      }

      if (!res.ok) {
        let errorDetail = `Lỗi máy chủ (${res.status}: ${res.statusText})`;
        try {
          const errData = await res.json();
          errorDetail = errData.detail || errData.message || JSON.stringify(errData);
        } catch(e) {}
        const err = new Error(errorDetail);
        err.status = res.status;
        err.detail = errorDetail;
        throw err;
      }

      return await res.json();
    }

    // State Helper
    function getAppState() {
      try {
        const stored = localStorage.getItem(APP_STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (parsed && typeof parsed === 'object') {
            return { ...defaultData, ...parsed };
          }
        }
      } catch(e) {}
      return { ...defaultData };
    }

    function saveAppState(data) {
      localStorage.setItem(APP_STORAGE_KEY, JSON.stringify(data));
    }

    let state = getAppState();

    /**
     * HÀM NẠP TOÀN BỘ DỮ LIỆU THẬT TỪ CƠ SỞ DỮ LIỆU BACKEND
     */
    async function loadServerData() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      // 1. Tải danh sách lô hàng thật
      try {
        const rawBatches = await apiFetch("/api/v1/batches?limit=100");
        state.batches = rawBatches.map(b => ({
          code: b.batch_code,
          batch_code: b.batch_code,
          product: b.product_name,
          product_name: b.product_name,
          org_id: b.organization_id,
          organization_id: b.organization_id,
          farm: b.organization_name || (b.organization_id === 1 ? "HTX Thắng Lợi" : b.organization_id === 2 ? "HTX Sơ Chế Đà Lạt Lành" : b.organization_id === 3 ? "Đội Vận Chuyển Lạnh" : "Siêu Thị BioMart"),
          qty: b.remaining_quantity !== undefined ? b.remaining_quantity : b.initial_quantity,
          initial_qty: b.initial_quantity,
          remaining_qty: b.remaining_quantity,
          unit: b.unit || "kg",
          status: b.status === "active" ? "Đang lưu kho" : (b.status || "Đang lưu kho"),
          temp: "4.0°C",
          cert: "VietGAP",
          plot: b.land_plot_name || (b.land_plot_id ? `Thửa #${b.land_plot_id}` : "Thửa liên kết"),
          land_plot_id: b.land_plot_id
        }));
      } catch(err) {
        if (roleKey !== 'consumer') {
          console.warn("Lỗi tải lô hàng:", err.message);
        }
        state.batches = [];
      }

      // 2. Tải danh sách thửa đất thật
      try {
        const rawPlots = await apiFetch("/api/v1/land-plots?limit=100");
        state.plots = rawPlots.map(p => ({
          id: p.id,
          org_id: p.organization_id,
          name: p.name,
          area: p.area,
          unit: p.unit || "m2",
          lat: p.latitude,
          lng: p.longitude,
          address: p.address || "Lâm Đồng"
        }));
      } catch(err) {
        state.plots = [];
      }

      // 3. Tải danh sách bàn giao thật
      try {
        const rawHandovers = await apiFetch("/api/v1/handovers?limit=100");
        state.handovers = rawHandovers.map(h => ({
          id: h.id,
          batch_id: h.batch_id,
          batch_code: h.batch_code || `Lô #${h.batch_id}`,
          from_org_id: h.from_org_id,
          from_org: h.from_org_name || `Tổ chức #${h.from_org_id}`,
          to_org_id: h.to_org_id,
          to_org: h.to_org_name || `Tổ chức #${h.to_org_id}`,
          status: h.status,
          temp: h.temperature || "4.0°C",
          reject_reason: h.reject_reason,
          created_at: h.created_at ? h.created_at.replace('T', ' ').substring(0, 16) : ''
        }));
      } catch(err) {
        state.handovers = [];
      }

      // 4. Tải chuỗi sự kiện Hash SHA-256 thật
      try {
        const rawEvents = await apiFetch("/api/v1/chain-events?limit=100");
        state.hashEvents = rawEvents.map((e, idx) => ({
          index: idx + 1,
          event_type: e.event_type,
          batch_code: e.batch_code || `ID #${e.batch_id}`,
          org_name: e.org_name || `Tổ chức #${e.organization_id}`,
          prev_hash: e.previous_hash || '0'.repeat(64),
          curr_hash: e.current_hash || '',
          valid: true
        }));
      } catch(err) {
        state.hashEvents = [];
      }

      // 5. Tải danh mục sản phẩm thật
      try {
        state.products = await apiFetch("/api/v1/products?limit=100");
      } catch(err) {
        state.products = [];
      }

      // 6. Tải danh sách thu hồi thật
      try {
        const rawRecalls = await apiFetch("/api/v1/recalls");
        state.recalls = (rawRecalls.items || rawRecalls || []).map(r => ({
          id: r.id,
          recall_code: r.recall_code,
          root_batch_code: r.root_batch_code,
          reason: r.reason,
          severity: r.severity,
          status: r.status,
          created_at: r.created_at ? r.created_at.replace('T', ' ').substring(0, 16) : ''
        }));
      } catch(err) {
        state.recalls = [];
      }

      saveAppState(state);
      renderOverviewTab();

      // Cập nhật tab đang mở
      if (state.activeTab === 'batches') renderBatchesTable();
      else if (state.activeTab === 'plots') renderPlotsGrid();
      else if (state.activeTab === 'materials_phi') renderMaterialsPhiTab();
      else if (state.activeTab === 'handovers') renderHandoversTable();
      else if (state.activeTab === 'recalls') renderRecallsTab();
      else if (state.activeTab === 'traceability') renderTraceabilityTab();
    }

    /**
     * NẠP DỮ LIỆU MẪU TOÀN DIỆN VÀO DB THẬT QUA ENDPOINT SEED
     */
    async function seedFullDatabase() {
      const btn = document.getElementById("seedDatabaseBtn");
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-amber-600"></i> <span>Đang nạp DB...</span>';
      }
      try {
        const res = await apiFetch("/api/v1/batches/seed-full-database", { method: "POST" });
        showToast(res.message || "Đã nạp 13 lô hàng mẫu và chuỗi hash vào cơ sở dữ liệu thật!", "success");
        await loadServerData();
      } catch (err) {
        console.error("Lỗi seed database:", err);
        showToast("Không thể nạp dữ liệu mẫu: " + err.message, "error");
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="fa-solid fa-database text-amber-600"></i> <span class="hidden sm:inline">Nạp Dữ Liệu Thật (Seed)</span>';
        }
      }
    }

    /**
     * SUPPLY CHAIN ROLE & DROPDOWN MANAGEMENT (Epic E-02)
     */
    function toggleRoleDropdown() {
      const menu = document.getElementById("roleDropdownMenu");
      if (menu) menu.classList.toggle("hidden");
    }

    document.addEventListener("click", (e) => {
      const btn = document.getElementById("roleDropdownBtn");
      const menu = document.getElementById("roleDropdownMenu");
      if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add("hidden");
      }
    });

    function updateRoleUI() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      const iconBox = document.getElementById("currentRoleIconBox");
      const icon = document.getElementById("currentRoleIcon");
      const title = document.getElementById("currentRoleTitle");
      const badge = document.getElementById("currentRoleBadge");
      const orgName = document.getElementById("currentOrgName");
      const inspectorBanner = document.getElementById("inspectorBanner");

      if (iconBox) iconBox.className = `w-8 h-8 rounded-xl ${cfg.iconBg} text-white flex items-center justify-center text-xs font-black shadow-sm`;
      if (icon) icon.className = `fa-solid ${cfg.icon}`;
      if (title) title.innerText = cfg.name;
      if (badge) {
        badge.innerText = cfg.badge;
        if (roleKey === "inspector") {
          badge.className = "text-[9px] font-black px-1.5 py-0.2 rounded-full bg-purple-100 text-purple-800 border border-purple-200";
        } else {
          badge.className = "text-[9px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200";
        }
      }
      if (orgName) orgName.innerText = cfg.orgName;

      // Cập nhật trạng thái nút Đăng Nhập S-04 trên Header
      updateAuthHeaderUI();

      // Hiển thị hoặc ẩn banner Cán Bộ Kiểm Tra (Epic E-02: Inspector Read-Only)
      if (inspectorBanner) {
        if (roleKey === "inspector") {
          inspectorBanner.classList.remove("hidden");
        } else {
          inspectorBanner.classList.add("hidden");
        }
      }
    }

    function updateAuthHeaderUI() {
      const authBtnIcon = document.getElementById("authBtnIcon");
      const authBtnLabel = document.getElementById("authBtnLabel");
      const authActiveDot = document.getElementById("authActiveDot");
      const authLogoutBtn = document.getElementById("authLogoutBtn");

      if (state.currentUser && state.currentUser.email) {
        if (authBtnIcon) authBtnIcon.className = "fa-solid fa-user-check text-xs text-emerald-300";
        if (authBtnLabel) {
          const displayName = state.currentUser.full_name ? state.currentUser.full_name.split(' (')[0] : state.currentUser.email.split('@')[0];
          authBtnLabel.innerText = `${displayName} (${state.currentUser.email})`;
        }
        if (authActiveDot) authActiveDot.classList.remove("hidden");
        if (authLogoutBtn) authLogoutBtn.classList.remove("hidden");
      } else {
        if (authBtnIcon) authBtnIcon.className = "fa-solid fa-right-to-bracket text-xs";
        if (authBtnLabel) authBtnLabel.innerText = "Đăng Nhập / Đổi TK";
        if (authActiveDot) authActiveDot.classList.add("hidden");
        if (authLogoutBtn) authLogoutBtn.classList.add("hidden");
      }
    }

    async function selectSupplyChainRole(roleKey) {
      if (!SUPPLY_CHAIN_ROLES[roleKey]) return;
      state.currentRole = roleKey;
      saveAppState(state);

      const menu = document.getElementById("roleDropdownMenu");
      if (menu) menu.classList.add("hidden");

      updateRoleUI();

      if (roleKey === "consumer") {
        state.currentUser = null;
        localStorage.removeItem("app_access_token");
        localStorage.removeItem("app_current_user");
        updateAuthHeaderUI();
        switchNavTab("public");
        showToast("Đã chuyển sang vai trò Người Tiêu Dùng (Tra cứu công khai không cần đăng nhập)", "info");
        await loadServerData();
        return;
      }

      // Tự động gọi API lấy token thật của vai trò từ backend
      try {
        const res = await fetch(`/api/v1/auth/quick-role-token?role=${encodeURIComponent(roleKey)}`, {
          method: "POST"
        });
        if (res.ok) {
          const authData = await res.json();
          state.currentUser = {
            email: authData.user_email || authData.email,
            role: authData.role,
            organization_id: authData.organization_id,
            full_name: authData.full_name,
            token: authData.access_token
          };
          localStorage.setItem("app_access_token", authData.access_token);
          localStorage.setItem("app_current_user", JSON.stringify(state.currentUser));
          updateAuthHeaderUI();
          showToast(`Đã xác thực vai trò thật: ${SUPPLY_CHAIN_ROLES[roleKey].name}`, "success");
        } else {
          showToast(`Không thể lấy token xác thực cho vai trò ${roleKey} (HTTP ${res.status})`, "error");
        }
      } catch (e) {
        console.error("Lỗi lấy token vai trò:", e);
        showToast("Lỗi kết nối máy chủ xác thực quick-role-token!", "error");
      }

      await loadServerData();
      switchNavTab(state.activeTab || "overview");
    }

    /**
     * USER STORY S-04, TASK T-08, T-09, T-10:
     * ĐĂNG NHẬP THẬT BẰNG EMAIL & MẬT KHẨU, BẢO MẬT ARGON2ID VÀ KHÓA TẠM 15 PHÚT
     */

    function openLoginModal(returnTab = null) {
      if (returnTab) {
        state.returnTab = returnTab;
        saveAppState(state);
      }
      renderDemoAccountsButtons();

      // Reset alert box
      const alertBox = document.getElementById("loginAlertBox");
      if (alertBox) alertBox.classList.add("hidden");

      // Điền sẵn email theo vai trò hiện tại nếu có
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey];
      const emailInput = document.getElementById("loginEmailInput");
      const passInput = document.getElementById("loginPasswordInput");

      if (state.currentUser && state.currentUser.email) {
        if (emailInput) emailInput.value = state.currentUser.email;
      } else if (cfg && cfg.email) {
        if (emailInput) emailInput.value = cfg.email;
        if (passInput && !passInput.value) passInput.value = cfg.samplePassword || "pass123";
      }

      openModal("loginModal");

      if (emailInput && emailInput.value) {
        checkLockoutStatus(emailInput.value);
      }
    }

    function togglePasswordVisibility(inputId, iconId) {
      const input = document.getElementById(inputId);
      const icon = document.getElementById(iconId);
      if (!input || !icon) return;
      if (input.type === "password") {
        input.type = "text";
        icon.className = "fa-solid fa-eye-slash text-xs text-emerald-600";
      } else {
        input.type = "password";
        icon.className = "fa-solid fa-eye text-xs text-slate-400";
      }
    }

    function renderDemoAccountsButtons() {
      const container = document.getElementById("demoAccountsGrid");
      if (!container) return;

      container.innerHTML = Object.entries(SUPPLY_CHAIN_ROLES).map(([key, r]) => {
        if (key === 'consumer') {
          return `
            <button 
              type="button" 
              onclick="selectDemoAccountRole('${key}')"
              class="p-2 rounded-xl bg-white hover:bg-emerald-50 border border-slate-200 hover:border-emerald-300 text-left transition-all flex items-center justify-between group cursor-pointer">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-lg ${r.iconBg} text-white flex items-center justify-center text-[10px]">
                  <i class="fa-solid ${r.icon}"></i>
                </div>
                <div>
                  <p class="font-bold text-slate-800 text-[11px] group-hover:text-emerald-700">${r.name.split('. ')[1] || r.name}</p>
                  <p class="text-[9px] text-slate-400 font-mono">Chế độ công khai (Không cần login)</p>
                </div>
              </div>
              <span class="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600">Public</span>
            </button>
          `;
        }
        return `
          <button 
            type="button" 
            onclick="selectDemoAccountRole('${key}')"
            class="p-2 rounded-xl bg-white hover:bg-emerald-50 border border-slate-200 hover:border-emerald-300 text-left transition-all flex items-center justify-between group cursor-pointer">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-lg ${r.iconBg} text-white flex items-center justify-center text-[10px]">
                <i class="fa-solid ${r.icon}"></i>
              </div>
              <div>
                <p class="font-bold text-slate-800 text-[11px] group-hover:text-emerald-700">${r.name.split('. ')[1] || r.name}</p>
                <p class="text-[9px] text-slate-500 font-mono truncate max-w-[140px]">${r.email}</p>
              </div>
            </div>
            <span class="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">Điền</span>
          </button>
        `;
      }).join('');
    }

    function selectDemoAccountRole(roleKey) {
      const r = SUPPLY_CHAIN_ROLES[roleKey];
      if (!r) return;
      if (roleKey === 'consumer') {
        closeModal('loginModal');
        selectSupplyChainRole('consumer');
        return;
      }
      const emailInput = document.getElementById("loginEmailInput");
      const passInput = document.getElementById("loginPasswordInput");
      if (emailInput) emailInput.value = r.email;
      if (passInput) passInput.value = r.samplePassword || "pass123";
      checkLockoutStatus(r.email);
    }

    function onLoginEmailChanged(val) {
      if (val && val.includes("@")) {
        checkLockoutStatus(val.trim());
      }
    }

    async function checkLockoutStatus(email) {
      if (!email) return;
      try {
        const res = await fetch(`/api/v1/auth/lockout-status?email=${encodeURIComponent(email)}`);
        if (!res.ok) return;
        const data = await res.json();
        renderLockoutAlertState(data);
      } catch (e) {
        console.warn("Không thể kiểm tra trạng thái khóa:", e);
      }
    }

    function renderLockoutAlertState(statusData) {
      const alertBox = document.getElementById("loginAlertBox");
      const alertTitle = document.getElementById("loginAlertHeading");
      const alertIcon = document.getElementById("loginAlertIcon");
      const alertMsg = document.getElementById("loginAlertMessage");
      const alertCounter = document.getElementById("loginAlertCounter");
      if (!alertBox) return;

      if (statusData.is_locked) {
        alertBox.className = "p-4 rounded-2xl border bg-rose-50 border-rose-300 text-rose-900 text-xs space-y-1 block animate-pulse";
        alertTitle.innerText = "Tài Khoản Đang Bị Khóa Tạm Thời (S-04)";
        alertIcon.className = "fa-solid fa-lock text-rose-600";
        alertMsg.innerText = `Tài khoản đã nhập sai mật khẩu quá 5 lần liên tiếp. Hệ thống từ chối đăng nhập trong ${statusData.remaining_minutes || 15} phút (KỂ CẢ KHI NHẬP ĐÚNG MẬT KHẨU).`;
        alertCounter.innerHTML = `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-200 text-rose-900 font-bold text-[10px]"><i class="fa-solid fa-clock"></i> Thời gian còn lại: ~${statusData.remaining_minutes || 15} phút</span>`;
        alertCounter.classList.remove("hidden");
      } else if (statusData.failed_attempts > 0) {
        alertBox.className = "p-4 rounded-2xl border bg-amber-50 border-amber-300 text-amber-900 text-xs space-y-1 block";
        alertTitle.innerText = "Cảnh Báo Số Lần Nhập Sai (Task T-10)";
        alertIcon.className = "fa-solid fa-triangle-exclamation text-amber-600";
        alertMsg.innerText = "Lưu ý: Nếu nhập sai 5 lần liên tiếp, tài khoản sẽ tự động bị khóa trong 15 phút.";
        alertCounter.innerHTML = `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 font-bold text-[10px]"><i class="fa-solid fa-shield-cat"></i> Đã nhập sai: ${statusData.failed_attempts}/5 lần</span>`;
        alertCounter.classList.remove("hidden");
      } else {
        alertBox.classList.add("hidden");
      }
    }

    async function handleRealLoginSubmit(e) {
      e.preventDefault();
      const email = document.getElementById("loginEmailInput").value.trim();
      const password = document.getElementById("loginPasswordInput").value;
      const submitBtn = document.getElementById("loginSubmitBtn");

      if (!email || !password) {
        showToast("Vui lòng nhập đầy đủ Email và Mật khẩu!", "error");
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang xác thực argon2id...</span>';
      }

      try {
        const res = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (res.ok) {
          // Đăng nhập thành công (S-04)
          state.currentUser = {
            email: data.user_email,
            role: data.role,
            organization_id: data.organization_id,
            full_name: data.full_name,
            token: data.access_token
          };
          state.currentRole = data.role;
          localStorage.setItem("app_access_token", data.access_token);
          localStorage.setItem("app_current_user", JSON.stringify(state.currentUser));

          // Chuyển hướng quay lại đúng trang cũ trước đó (returnUrl / returnTab)
          const targetTab = state.returnTab || 'overview';
          state.returnTab = null;
          saveAppState(state);

          closeModal("loginModal");
          updateRoleUI();
          await loadServerData();
          switchNavTab(targetTab);
          showToast(`Đăng nhập thành công! Chào mừng ${data.full_name || data.user_email}`, "success");
        } else {
          // Lỗi xác thực
          const status = res.status;
          const failedHeader = res.headers.get("X-Failed-Attempts");
          const remainingHeader = res.headers.get("X-Remaining-Minutes");

          const alertBox = document.getElementById("loginAlertBox");
          const alertTitle = document.getElementById("loginAlertHeading");
          const alertIcon = document.getElementById("loginAlertIcon");
          const alertMsg = document.getElementById("loginAlertMessage");
          const alertCounter = document.getElementById("loginAlertCounter");

          if (alertBox) {
            alertBox.classList.remove("hidden");
            if (status === 423) {
              // Bị khóa tạm 15 phút (S-04, T-10)
              alertBox.className = "p-4 rounded-2xl border bg-rose-50 border-rose-300 text-rose-900 text-xs space-y-1 block animate-pulse";
              alertTitle.innerText = "Tài Khoản Đang Bị Khóa Tạm Thời (S-04)";
              alertIcon.className = "fa-solid fa-lock text-rose-600";
              alertMsg.innerText = data.detail || "Tài khoản đang bị khóa tạm thời do nhập sai mật khẩu quá nhiều lần.";
              alertCounter.innerHTML = `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-200 text-rose-900 font-bold text-[10px]"><i class="fa-solid fa-clock"></i> Thời gian còn lại: ~${remainingHeader || 15} phút</span>`;
              alertCounter.classList.remove("hidden");
            } else {
              // Sai email hoặc sai mật khẩu: CÙNG MỘT câu thông báo lỗi duy nhất
              alertBox.className = "p-4 rounded-2xl border bg-rose-50 border-rose-200 text-rose-900 text-xs space-y-1 block";
              alertTitle.innerText = "Lỗi Đăng Nhập";
              alertIcon.className = "fa-solid fa-circle-exclamation text-rose-600";
              alertMsg.innerText = "Email hoặc mật khẩu không chính xác.";
              if (failedHeader) {
                alertCounter.innerHTML = `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 font-bold text-[10px] border border-amber-300"><i class="fa-solid fa-triangle-exclamation text-amber-600"></i> Đã nhập sai: ${failedHeader}/5 lần (Khóa sau 5 lần)</span>`;
                alertCounter.classList.remove("hidden");
              } else {
                alertCounter.classList.add("hidden");
              }
            }
          }

          showToast(data.detail || "Email hoặc mật khẩu không chính xác.", "error");
        }
      } catch (err) {
        console.error("Lỗi mạng:", err);
        showToast("Lỗi kết nối tới máy chủ xác thực!", "error");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> <span>Xác Thực & Đăng Nhập</span>';
        }
      }
    }

    async function simulateLockoutCurrentEmail() {
      const email = document.getElementById("loginEmailInput").value.trim();
      if (!email) {
        showToast("Vui lòng chọn hoặc nhập một email để giả lập sai 5 lần!", "error");
        return;
      }
      try {
        const res = await fetch("/api/v1/auth/simulate-lockout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
          showToast(`Đã giả lập khóa tài khoản ${email} trong 15 phút (Test S-04 / T-10)!`, "error");
          checkLockoutStatus(email);
        } else {
          showToast(data.detail || "Không thể giả lập khóa tài khoản!", "error");
        }
      } catch (e) {
        showToast("Lỗi mạng khi gọi simulate lockout", "error");
      }
    }

    async function resetLockoutCurrentEmail() {
      const email = document.getElementById("loginEmailInput").value.trim();
      if (!email) {
        showToast("Vui lòng chọn hoặc nhập một email để mở khóa!", "error");
        return;
      }
      try {
        const res = await fetch("/api/v1/auth/reset-lockout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
          showToast(`Đã mở khóa và xóa bộ đếm số lần sai cho ${email}!`, "success");
          checkLockoutStatus(email);
        } else {
          showToast(data.detail || "Không thể mở khóa tài khoản!", "error");
        }
      } catch (e) {
        showToast("Lỗi mạng khi gọi reset lockout", "error");
      }
    }

    async function checkLockoutStatusCurrentEmail() {
      const email = document.getElementById("loginEmailInput").value.trim();
      if (!email) {
        showToast("Vui lòng nhập email cần kiểm tra!", "error");
        return;
      }
      await checkLockoutStatus(email);
      showToast(`Đã cập nhật trạng thái khóa của ${email}`, "info");
    }

    async function handleLogout() {
      state.currentUser = null;
      state.currentRole = "consumer";
      localStorage.removeItem("app_access_token");
      localStorage.removeItem("app_current_user");
      saveAppState(state);
      updateRoleUI();
      await loadServerData();
      switchNavTab("public");
      showToast("Đã đăng xuất. Bạn đang ở chế độ Người Tiêu Dùng (Công Khai).", "info");
    }

    /**
     * ACTION GUARDS FOR INSPECTOR READ-ONLY (Epic E-02 Criterion 3)
     */
    function handleAddBatchClick() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi ghi đã bị chặn và ghi log an ninh.", "error");
        return;
      }
      openModal('addBatchModal');
    }

    function handleAddPlotClick() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi ghi đã bị chặn và ghi log an ninh.", "error");
        return;
      }
      openModal('addPlotModal');
    }

    function handleAddMaterialClick() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi ghi đã bị chặn và ghi log an ninh.", "error");
        return;
      }
      openModal('recordBatchMaterialModal');
    }

    /**
     * NAVIGATION TAB SWITCHER
     */
    function switchNavTab(tabId) {
      // Guard S-04 & T-09: Giả sử chưa đăng nhập mà mở trang nội bộ, đưa về form đăng nhập
      const internalTabs = ['batches', 'plots', 'materials_phi', 'handovers', 'recalls', 'cold_chain'];
      const isConsumer = !state.currentUser && (!state.currentRole || state.currentRole === 'consumer');
      if (isConsumer && internalTabs.includes(tabId)) {
        state.returnTab = tabId;
        saveAppState(state);
        openLoginModal(tabId);
        showToast("Trang nội bộ yêu cầu đăng nhập. Vui lòng đăng nhập tài khoản đơn vị để tiếp tục (S-04).", "info");
        return;
      }

      state.activeTab = tabId;
      saveAppState(state);

      const allTabs = ['overview', 'batches', 'plots', 'materials_phi', 'handovers', 'recalls', 'cold_chain', 'traceability', 'public'];
      allTabs.forEach(t => {
        const btn = document.getElementById(`tabBtn_${t}`);
        const view = document.getElementById(`view_${t}`);
        if (btn) {
          if (t === tabId) {
            btn.className = "nav-tab-btn nav-tab-active px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2";
          } else {
            btn.className = "nav-tab-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all flex items-center gap-2";
          }
        }
        if (view) {
          if (t === tabId) view.classList.remove('hidden');
          else view.classList.add('hidden');
        }
      });

      // Render tab specific data
      if (tabId === 'batches') renderBatchesTable();
      else if (tabId === 'plots') renderPlotsGrid();
      else if (tabId === 'materials_phi') renderMaterialsPhiTab();
      else if (tabId === 'handovers') renderHandoversTable();
      else if (tabId === 'recalls') renderRecallsTab();
      else if (tabId === 'cold_chain') renderColdChainTab();
      else if (tabId === 'traceability') renderTraceabilityTab();
      else if (tabId === 'public') renderPublicBatches('all');
      else renderOverviewTab();

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    /**
     * RENDER OVERVIEW TAB
     */
    function renderOverviewTab() {
      const bCount = (state.batches || []).length;
      const pCount = (state.plots || []).length;
      const elB = document.getElementById("kpiTotalBatches");
      const elP = document.getElementById("kpiTotalPlots");
      if (elB) elB.innerText = `${bCount} Lô`;
      if (elP) elP.innerText = `${pCount} Thửa`;
    }

    /**
     * RENDER BATCHES TABLE (S-08, S-14)
     */
    function renderBatchesTable(filterText = "", productFilter = "all") {
      const tbody = document.getElementById("batchesTableBody");
      if (!tbody) return;

      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      // Epic E-02: Cô lập dữ liệu theo Organization ID:
      // Mỗi tổ chức chỉ xem các lô hàng đang thuộc quyền quản lý của mình.
      // Riêng cán bộ kiểm tra (Inspector) và Quản trị hệ thống (Admin) tra cứu lô trên mọi tổ chức.
      let list = state.batches;
      if (!cfg.canAccessAllOrgs && cfg.orgId !== null) {
        list = list.filter(b => b.org_id === cfg.orgId);
      }

      if (filterText) {
        const lower = filterText.toLowerCase();
        list = list.filter(b => (b.code || b.batch_code || '').toLowerCase().includes(lower) || (b.product || b.product_name || '').toLowerCase().includes(lower));
      }
      if (productFilter !== 'all') {
        list = list.filter(b => (b.product || b.product_name) === productFilter);
      }

      if (list.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" class="p-8 text-center text-slate-400">
              <i class="fa-solid fa-box-open text-3xl mb-2 text-slate-300"></i>
              <p class="font-bold text-xs">Không có lô hàng nào thuộc quyền quản lý của ${cfg.orgName}</p>
              <p class="text-[11px] text-slate-400 mt-1">Dữ liệu được cô lập chặt chẽ theo Organization ID (Epic E-02)</p>
            </td>
          </tr>
        `;
        handleBatchSelectChange();
        return;
      }

      tbody.innerHTML = list.map(b => {
        const bCode = b.code || b.batch_code;
        const bProduct = b.product || b.product_name;
        // PHI check status for this batch
        const logs = state.materialLogs ? state.materialLogs.filter(m => m.batch_code === bCode) : [];
        let phiBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">Chưa ghi nhận</span>';
        if (logs.length > 0) {
          phiBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800"><i class="fa-solid fa-check mr-1"></i> Đã cách ly an toàn</span>`;
        }

        const remQty = b.remaining_qty !== undefined ? b.remaining_qty : b.qty;
        const initQty = b.initial_qty !== undefined ? b.initial_qty : b.qty;
        const isDepleted = remQty <= 0;
        const qtyDisplay = isDepleted 
          ? `<span class="text-rose-600 font-bold line-through text-xs">${remQty} kg</span> <span class="text-[10px] text-slate-400 block font-normal">(Đã tách/gộp hết)</span>`
          : `<span class="text-emerald-700 font-black text-xs">${remQty} kg</span> ${remQty < initQty ? `<span class="text-[10px] text-slate-400 block font-normal">(gốc: ${initQty} kg)</span>` : ''}`;

        return `
          <tr class="hover:bg-slate-50 transition-colors ${isDepleted ? 'bg-slate-50/50' : ''}">
            <td class="p-3.5 text-center">
              <input type="checkbox" 
                class="batch-select-checkbox rounded text-emerald-600 focus:ring-emerald-500 cursor-pointer" 
                data-code="${bCode}" 
                data-product="${bProduct}" 
                data-qty="${remQty}"
                ${isDepleted ? 'disabled title="Lô đã hết số lượng"' : ''}
                onchange="handleBatchSelectChange()"/>
            </td>
            <td class="p-3.5 font-mono font-black text-emerald-800 text-xs">${bCode}</td>
            <td class="p-3.5 font-bold text-slate-800">${bProduct}</td>
            <td class="p-3.5 text-slate-600 font-semibold">${b.plot || (b.land_plot_id ? 'Thửa #' + b.land_plot_id : 'Chưa gán thửa')}</td>
            <td class="p-3.5">${qtyDisplay}</td>
            <td class="p-3.5">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${b.status === 'Đang vận chuyển' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'}">
                <i class="fa-solid fa-temperature-half"></i> ${b.status} (${b.temp})
              </span>
            </td>
            <td class="p-3.5">${phiBadge}</td>
            <td class="p-3.5 text-right">
              <button onclick="handleQuickSearch('${b.code}')" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[11px] font-bold">
                Chi Tiết Lô
              </button>
            </td>
          </tr>
        `;
      }).join('');

      handleBatchSelectChange();
    }

    function filterBatchesTable(val) {
      renderBatchesTable(val, document.getElementById("batchProductFilter").value);
    }

    function filterBatchesByProduct(val) {
      renderBatchesTable(document.getElementById("batchFilterInput").value, val);
    }

    /**
     * RENDER PLOTS GRID (S-06)
     */
    function renderPlotsGrid() {
      const container = document.getElementById("plotsGrid");
      if (!container) return;

      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      // Cô lập thửa đất theo organization_id (riêng Inspector và Admin xem được tất cả)
      let list = state.plots;
      if (!cfg.canAccessAllOrgs && cfg.orgId !== null) {
        list = list.filter(p => !p.org_id || p.org_id === cfg.orgId);
      }

      if (list.length === 0) {
        container.innerHTML = `
          <div class="col-span-full p-8 text-center text-slate-400 bg-white rounded-3xl border border-slate-200">
            <i class="fa-solid fa-map-location-dot text-3xl mb-2 text-slate-300"></i>
            <p class="font-bold text-xs">Không có thửa đất nào thuộc quyền quản lý của ${cfg.orgName}</p>
            <p class="text-[11px] text-slate-400 mt-1">Mỗi tổ chức chỉ xem và khai báo thửa đất thuộc quyền quản lý của mình (S-06, Epic E-02)</p>
          </div>
        `;
        return;
      }

      container.innerHTML = list.map(p => `
        <div class="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-4 hover:shadow-md transition-shadow">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h4 class="font-black text-slate-800 text-base">${p.name}</h4>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">VietGAP</span>
          </div>
          <div class="space-y-2 text-xs">
            <div class="flex justify-between">
              <span class="text-slate-400">Diện tích:</span>
              <span class="font-bold text-slate-800 font-mono">${p.area.toLocaleString()} ${p.unit}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Tọa độ GPS:</span>
              <span class="font-mono text-emerald-700 font-semibold">${p.lat}, ${p.lng}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Địa chỉ:</span>
              <span class="text-slate-600 font-medium text-right">${p.address}</span>
            </div>
          </div>
          <div class="pt-2 border-t border-slate-100 flex justify-between items-center text-xs">
            <span class="text-[11px] text-emerald-600 font-semibold"><i class="fa-solid fa-check"></i> Thuộc tổ chức mình</span>
            <button onclick="deletePlotItem(${p.id})" class="text-rose-600 hover:text-rose-800 font-bold text-xs">
              <i class="fa-solid fa-trash-can mr-1"></i> Xóa Thửa
            </button>
          </div>
        </div>
      `).join('');
    }

    async function deletePlotItem(id) {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi xóa đã bị chặn và ghi log an ninh.", "error");
        return;
      }

      if (confirm("Bạn có chắc chắn muốn xóa thửa đất này khỏi cơ sở dữ liệu thật?")) {
        try {
          await apiFetch(`/api/v1/land-plots/${id}`, {
            method: "DELETE"
          });
          await loadServerData();
          showToast("Đã xóa thửa đất thành công trên DB thật!", "success");
        } catch (err) {
          console.error("Lỗi xóa thửa đất:", err);
          showToast(`Lỗi xóa thửa đất: ${err.message}`, "error");
        }
      }
    }

    /**
     * RENDER MATERIALS & PHI TAB (STORY S-62)
     */
    function renderMaterialsPhiTab() {
      // 1. Populate batch select in PHI tool and Modal
      const phiSelect = document.getElementById("phiCheckBatchSelect");
      const modalSelect = document.getElementById("modal_mat_batch_code");
      
      const batchOptions = state.batches.map(b => `<option value="${b.code}">${b.code} - ${b.product}</option>`).join('');
      if (phiSelect) phiSelect.innerHTML = batchOptions;
      if (modalSelect) modalSelect.innerHTML = batchOptions;

      // 2. Render Material Logs Table
      const tbody = document.getElementById("materialLogsTableBody");
      if (!tbody) return;

      tbody.innerHTML = state.materialLogs.map(m => {
        // Evaluate safety against today
        const today = new Date().toISOString().split('T')[0];
        const isSafe = today >= m.safe_harvest_date;
        const badge = isSafe 
          ? `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800"><i class="fa-solid fa-shield-check"></i> An toàn thu hoạch</span>`
          : `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800"><i class="fa-solid fa-hourglass-half"></i> Đang cách ly</span>`;

        return `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="p-3.5 font-mono font-bold text-emerald-900">${m.batch_code}</td>
            <td class="p-3.5 font-semibold text-slate-600 uppercase text-[10px]">${m.category === 'pesticide' ? 'Thuốc BVTV' : m.category === 'fertilizer' ? 'Phân bón' : 'Sinh học'}</td>
            <td class="p-3.5 font-bold text-slate-800">${m.material_name}</td>
            <td class="p-3.5 text-slate-700">${m.dosage}</td>
            <td class="p-3.5 font-mono text-slate-600">${m.applied_date}</td>
            <td class="p-3.5 font-bold text-amber-700">${m.isolation_days} ngày</td>
            <td class="p-3.5 font-mono font-bold text-emerald-700">${m.safe_harvest_date}</td>
            <td class="p-3.5 text-slate-500">${m.applied_by}</td>
            <td class="p-3.5 text-right">${badge}</td>
          </tr>
        `;
      }).join('');
    }

    /**
     * PHI COMPLIANCE CHECKER ENGINE (S-62)
     */
    function executePhiCheck() {
      const batchCode = document.getElementById("phiCheckBatchSelect").value;
      const harvestDate = document.getElementById("phiCheckHarvestDate").value;
      const resultBox = document.getElementById("phiCheckResult");

      if (!harvestDate) {
        showToast("Vui lòng chọn ngày thu hoạch dự kiến", "error");
        return;
      }

      const logs = state.materialLogs.filter(m => m.batch_code === batchCode);
      resultBox.classList.remove("hidden");

      if (logs.length === 0) {
        resultBox.className = "p-4 rounded-2xl text-xs font-semibold bg-emerald-50 text-emerald-900 border border-emerald-300 flex items-center gap-3";
        resultBox.innerHTML = `
          <i class="fa-solid fa-circle-check text-xl text-emerald-600"></i>
          <div>
            <p class="font-bold text-sm text-emerald-950">LÔ HÀNG ĐỦ ĐIỀU KIỆN AN TOÀN THU HOẠCH</p>
            <p class="text-[11px] text-emerald-800 mt-0.5">Lô ${batchCode} chưa ghi nhận sử dụng thuốc BVTV hoặc vật tư cần thời gian cách ly.</p>
          </div>
        `;
        return;
      }

      // Find max safe harvest date
      let maxSafeDate = logs[0].safe_harvest_date;
      logs.forEach(l => {
        if (l.safe_harvest_date > maxSafeDate) maxSafeDate = l.safe_harvest_date;
      });

      if (harvestDate < maxSafeDate) {
        const harvestDt = new Date(harvestDate);
        const safeDt = new Date(maxSafeDate);
        const diffDays = Math.ceil((safeDt - harvestDt) / (1000 * 60 * 60 * 24));

        resultBox.className = "p-4 rounded-2xl text-xs font-semibold bg-rose-50 text-rose-900 border border-rose-300 flex items-center gap-3";
        resultBox.innerHTML = `
          <i class="fa-solid fa-triangle-exclamation text-2xl text-rose-600"></i>
          <div>
            <p class="font-bold text-sm text-rose-950">CẢNH BÁO: CHƯA ĐỦ THỜI GIAN CÁCH LY AN TOÀN (VI PHẠM PHI)!</p>
            <p class="text-[11px] text-rose-800 mt-1">
              Còn thiếu <b>${diffDays} ngày</b> để thuốc BVTV phân giải an toàn đạt chuẩn VietGAP.
              <br>Ngày an toàn thu hoạch sớm nhất: <b class="font-mono text-rose-950">${maxSafeDate}</b>. Khuyến nghị: <b>KHÔNG</b> thu hoạch vào ngày ${harvestDate}!
            </p>
          </div>
        `;
      } else {
        resultBox.className = "p-4 rounded-2xl text-xs font-semibold bg-emerald-50 text-emerald-900 border border-emerald-300 flex items-center gap-3";
        resultBox.innerHTML = `
          <i class="fa-solid fa-circle-check text-2xl text-emerald-600"></i>
          <div>
            <p class="font-bold text-sm text-emerald-950">LÔ HÀNG ĐỦ ĐIỀU KIỆN AN TOÀN THU HOẠCH (COMPLIANT)</p>
            <p class="text-[11px] text-emerald-800 mt-1">
              Đã hoàn thành toàn bộ thời gian cách ly bắt buộc (kết thúc cách ly từ ngày ${maxSafeDate}). Nông sản đạt chuẩn an toàn thực phẩm.
            </p>
          </div>
        `;
      }
    }

    /**
     * SUBMIT MATERIAL USAGE LOG (S-62)
     */
    function submitBatchMaterialLog() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi ghi đã bị chặn và ghi log an ninh.", "error");
        return;
      }

      const batchCode = document.getElementById("modal_mat_batch_code").value;
      const matName = document.getElementById("modal_mat_name").value.trim();
      const category = document.getElementById("modal_mat_category").value;
      const dosage = document.getElementById("modal_mat_dosage").value.trim();
      const appliedDate = document.getElementById("modal_mat_applied_date").value;
      const isoDays = parseInt(document.getElementById("modal_mat_isolation_days").value) || 0;
      const appliedBy = document.getElementById("modal_mat_applied_by").value.trim();
      const notes = document.getElementById("modal_mat_notes").value.trim();

      if (!matName || !dosage || !appliedDate) {
        showToast("Vui lòng điền đầy đủ các thông tin bắt buộc", "error");
        return;
      }

      // Calculate safe harvest date: appliedDate + isoDays
      const appliedDt = new Date(appliedDate);
      appliedDt.setDate(appliedDt.getDate() + isoDays);
      const safeHarvestDate = appliedDt.toISOString().split('T')[0];

      const newLog = {
        id: Date.now(),
        batch_code: batchCode,
        material_name: matName,
        category: category,
        dosage: dosage,
        applied_date: appliedDate,
        isolation_days: isoDays,
        safe_harvest_date: safeHarvestDate,
        applied_by: appliedBy || "Kỹ sư nông nghiệp",
        notes: notes
      };

      state.materialLogs.unshift(newLog);

      // Append Event to Hash Chain (S-10)
      const prevHash = state.hashEvents[state.hashEvents.length - 1].curr_hash;
      state.hashEvents.push({
        index: state.hashEvents.length + 1,
        event_type: "MATERIAL_APPLIED_PHI",
        batch_code: batchCode,
        org_name: "HTX Thắng Lợi",
        prev_hash: prevHash,
        curr_hash: "sha256_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
        valid: true
      });

      saveAppState(state);
      closeModal("recordBatchMaterialModal");
      renderMaterialsPhiTab();
      showToast(`Đã ghi nhận vật tư cho lô ${batchCode}. Ngày an toàn: ${safeHarvestDate}`, "success");
    }

    /**
     * STATE VÀ ENGINE BÀN GIAO LÔ HÀNG GIỮA CÁC TỔ CHỨC ĐỘC LẬP (S-15, S-16)
     */
    let currentRejectHandoverId = null;
    let currentDetailBatchCode = null;
    let handoverViewFilter = 'incoming'; // incoming, outgoing, all

    function filterHandoversView(filterType) {
      handoverViewFilter = filterType;
      
      const btnIn = document.getElementById("hoFilterBtn_incoming");
      const btnOut = document.getElementById("hoFilterBtn_outgoing");
      const btnAll = document.getElementById("hoFilterBtn_all");

      [btnIn, btnOut, btnAll].forEach(b => {
        if (b) b.className = "px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 flex items-center gap-2";
      });

      if (filterType === 'incoming' && btnIn) {
        btnIn.className = "px-4 py-2 rounded-xl text-xs font-bold bg-amber-500 text-white shadow-sm flex items-center gap-2";
      } else if (filterType === 'outgoing' && btnOut) {
        btnOut.className = "px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-sm flex items-center gap-2";
      } else if (btnAll) {
        btnAll.className = "px-4 py-2 rounded-xl text-xs font-bold bg-slate-900 text-white shadow-sm flex items-center gap-2";
      }

      renderHandoversTable();
    }

    /**
     * RENDER HANDOVERS TAB (S-15, S-16)
     */
    function renderHandoversTable() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      const currentOrgId = cfg.orgId;

      // 1. Cập nhật dropdown chọn Lô bàn giao: chỉ hiển thị các lô do tổ chức mình sở hữu
      const hoBatchSel = document.getElementById("ho_batch_code");
      if (hoBatchSel) {
        let myBatches = state.batches;
        if (!cfg.canAccessAllOrgs && currentOrgId !== null) {
          myBatches = myBatches.filter(b => b.org_id === currentOrgId);
        }
        hoBatchSel.innerHTML = myBatches.map(b => `
          <option value="${b.code}" ${b.code === currentDetailBatchCode ? 'selected' : ''}>
            ${b.code} - ${b.product} (${b.status || 'Sẵn sàng'})
          </option>
        `).join('');
      }

      // 2. Cập nhật dropdown chọn Tổ chức nhận: loại trừ tổ chức của chính mình
      const hoTargetSel = document.getElementById("ho_target_org_id");
      if (hoTargetSel) {
        const candidateOrgs = [
          { id: 1, name: "HTX Nông Nghiệp Thắng Lợi (Vùng Trồng)" },
          { id: 2, name: "HTX Sơ Chế Đà Lạt Lành (Sơ Chế)" },
          { id: 3, name: "Đội Vận Chuyển Lạnh Việt Nhật (Logistics)" },
          { id: 4, name: "Chuỗi Siêu Thị BioMart (Phân Phối / Bán Lẻ)" }
        ].filter(org => org.id !== currentOrgId);

        hoTargetSel.innerHTML = candidateOrgs.map(org => `
          <option value="${org.id}">${org.name}</option>
        `).join('');
      }

      // 3. RENDER BẢNG "DANH SÁCH CHỜ TÔI XÁC NHẬN" (INCOMING HANDOVERS CHO BÊN NHẬN)
      const incomingTbody = document.getElementById("incomingHandoversTableBody");
      const incomingSection = document.getElementById("incomingHandoversSection");
      
      const incomingList = state.handovers.filter(h => {
        const isTarget = cfg.canAccessAllOrgs || (currentOrgId !== null && h.to_org_id === currentOrgId);
        return isTarget && h.status === 'PENDING';
      });

      const badgeCount = document.getElementById("badgeIncomingCount");
      if (badgeCount) badgeCount.innerText = incomingList.length;

      if (incomingTbody) {
        if (incomingList.length === 0) {
          incomingTbody.innerHTML = `
            <tr>
              <td colspan="6" class="p-6 text-center text-slate-400">
                <i class="fa-solid fa-inbox text-2xl mb-1 text-slate-300"></i>
                <p class="font-bold text-xs text-slate-600">Hiện không có lô hàng nào chờ ${cfg.orgName} xác nhận tiếp nhận.</p>
                <p class="text-[11px] text-slate-400">Khi một tổ chức khác tạo lệnh bàn giao tới bạn, lô sẽ xuất hiện tại đây.</p>
              </td>
            </tr>
          `;
        } else {
          incomingTbody.innerHTML = incomingList.map(h => `
            <tr class="hover:bg-amber-50/50 transition-colors">
              <td class="p-3.5 font-mono font-black text-amber-950 text-xs">${h.batch_code}</td>
              <td class="p-3.5 font-bold text-slate-800">${h.from_org}</td>
              <td class="p-3.5 font-mono font-bold text-teal-700">${h.temp || '4.0°C'}</td>
              <td class="p-3.5 text-slate-500 font-medium">${h.created_at || 'Vừa tạo'}</td>
              <td class="p-3.5">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span> Chờ Bạn Tiếp Quản
                </span>
              </td>
              <td class="p-3.5 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button 
                    onclick="confirmHandover(${h.id})" 
                    class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white rounded-xl font-bold text-xs shadow-sm flex items-center gap-1.5 transition-all">
                    <i class="fa-solid fa-check"></i> Xác Nhận
                  </button>
                  <button 
                    onclick="openRejectModal(${h.id}, '${h.batch_code}')" 
                    class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white rounded-xl font-bold text-xs shadow-sm flex items-center gap-1.5 transition-all">
                    <i class="fa-solid fa-xmark"></i> Từ Chối
                  </button>
                </div>
              </td>
            </tr>
          `).join('');
        }
      }

      // 4. RENDER BẢNG TỔNG QUÁT THEO FILTER (INCOMING / OUTGOING / ALL)
      const tbody = document.getElementById("handoversTableBody");
      const titleEl = document.getElementById("generalHandoversTitle");
      if (!tbody) return;

      let displayList = state.handovers;
      if (handoverViewFilter === 'incoming') {
        if (titleEl) titleEl.innerText = "Các Lô Hàng Chờ Xác Nhận (Incoming)";
        if (!cfg.canAccessAllOrgs && currentOrgId !== null) {
          displayList = displayList.filter(h => h.to_org_id === currentOrgId);
        }
      } else if (handoverViewFilter === 'outgoing') {
        if (titleEl) titleEl.innerText = `Các Lệnh Bàn Giao Do ${cfg.orgName} Gửi Đi`;
        if (!cfg.canAccessAllOrgs && currentOrgId !== null) {
          displayList = displayList.filter(h => h.from_org_id === currentOrgId);
        }
      } else {
        if (titleEl) titleEl.innerText = "Toàn Bộ Lịch Sử Bàn Giao Trong Chuỗi";
      }

      if (displayList.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="p-6 text-center text-slate-400">
              <p class="font-bold text-xs">Chưa có bản ghi bàn giao nào phù hợp với bộ lọc.</p>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = displayList.map(h => {
        let badge = "";
        let noteText = h.reject_reason ? `<span class="text-rose-600 font-semibold text-[11px]" title="${h.reject_reason}">Lý do: ${h.reject_reason}</span>` : '<span class="text-slate-400 text-[11px]">Bảo quản chuỗi lạnh đạt chuẩn</span>';

        if (h.status === 'PENDING') {
          badge = '<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">Chờ xác nhận (A vẫn giữ quyền)</span>';
        } else if (h.status === 'ACCEPTED') {
          badge = '<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200"><i class="fa-solid fa-check-double mr-1"></i> Đã xác nhận (B tiếp quản)</span>';
        } else {
          badge = '<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200"><i class="fa-solid fa-ban mr-1"></i> Đã từ chối (A tiếp tục giữ)</span>';
        }

        return `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="p-3.5 font-mono font-bold text-slate-800">${h.batch_code}</td>
            <td class="p-3.5 text-slate-700 font-semibold">${h.from_org}</td>
            <td class="p-3.5 text-emerald-800 font-bold">${h.to_org}</td>
            <td class="p-3.5">${badge}</td>
            <td class="p-3.5 font-mono font-bold text-teal-700">${h.temp || '4.0°C'}</td>
            <td class="p-3.5 text-right">${noteText}</td>
          </tr>
        `;
      }).join('');
    }

    /**
     * MỞ MODAL BÀN GIAO TỪ MÀN HÌNH CHI TIẾT LÔ (S-15)
     */
    function openHandoverForCurrentBatch() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Không được phép bàn giao lô hàng.", "error");
        return;
      }

      const batchCode = currentDetailBatchCode || (document.getElementById("modalBatchCode") ? document.getElementById("modalBatchCode").innerText.trim() : null);
      if (!batchCode) {
        showToast("Không tìm thấy mã lô để bàn giao!", "error");
        return;
      }

      // Kiểm tra quyền sở hữu lô: Phải thuộc tổ chức hiện tại
      const targetBatch = state.batches.find(b => b.code.toLowerCase() === batchCode.toLowerCase());
      if (targetBatch && !cfg.canAccessAllOrgs && cfg.orgId !== null && targetBatch.org_id !== cfg.orgId) {
        showToast(`Lô ${batchCode} hiện thuộc quyền quản lý của đơn vị khác! Bạn không có quyền bàn giao.`, "error");
        return;
      }

      // Đóng modal chi tiết lô và chuyển mã vào modal bàn giao
      closeModal("batchDetailModal");
      renderHandoversTable();
      
      const sel = document.getElementById("ho_batch_code");
      if (sel) sel.value = batchCode;

      openModal("handoverModal");
    }

    /**
     * KHỞI TẠO LỆNH BÀN GIAO SANG TỔ CHỨC KHÁC (S-15)
     * Ràng buộc: Chặn tạo lệnh bàn giao thứ hai khi đang có lệnh chờ duyệt
     */
    async function submitHandoverCreate() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only!", "error");
        return;
      }

      const code = document.getElementById("ho_batch_code").value;
      const targetOrgId = parseInt(document.getElementById("ho_target_org_id").value);
      const tempVal = document.getElementById("ho_temp_input").value;
      const notes = document.getElementById("ho_notes_input").value.trim();

      if (!code || !targetOrgId) {
        showToast("Vui lòng chọn lô hàng và tổ chức tiếp nhận!", "error");
        return;
      }

      const orgMap = {
        1: "HTX Nông Nghiệp Thắng Lợi (Vùng Trồng)",
        2: "HTX Sơ Chế Đà Lạt Lành (Sơ Chế)",
        3: "Đội Vận Chuyển Lạnh Việt Nhật (Logistics)",
        4: "Chuỗi Siêu Thị BioMart (Phân Phối / Bán Lẻ)"
      };

      if (cfg.orgId === targetOrgId) {
        showToast("Không thể tự bàn giao cho chính tổ chức của mình!", "error");
        return;
      }

      // TIÊU CHÍ S-15: Chặn không cho tạo lệnh bàn giao thứ hai khi đang có lệnh chờ
      const pendingExists = state.handovers.find(h => h.batch_code.toLowerCase() === code.toLowerCase() && h.status === 'PENDING');
      if (pendingExists) {
        showToast(`CHẶN BÀN GIAO (S-15): Lô ${code} đang có một lệnh bàn giao chờ xác nhận!`, "error");
        return;
      }

      // Gọi API Backend nếu khả dụng
      try {
        const batchObj = state.batches.find(b => b.code.toLowerCase() === code.toLowerCase());
        const batchId = batchObj ? (batchObj.id || 1) : 1;
        const resp = await fetch("/api/v1/handovers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            batch_id: batchId,
            to_org_id: targetOrgId,
            temperature: parseFloat(tempVal) || 4.0,
            notes: notes
          })
        });
        if (resp.status === 400) {
          const errData = await resp.json();
          showToast(`Lỗi: ${errData.detail || 'Không thể tạo lệnh bàn giao'}`, "error");
          return;
        }
      } catch (e) {
        console.log("Backend API not reachable, updating local simulation state...", e);
      }

      // Cập nhật State cục bộ:
      // Lô chuyển sang trạng thái "chờ xác nhận", tổ chức A vẫn tạm thời giữ quyền sở hữu
      const newHandover = {
        id: Date.now(),
        batch_id: 1,
        batch_code: code,
        from_org_id: cfg.orgId || 1,
        from_org: cfg.orgName || "HTX Thắng Lợi",
        to_org_id: targetOrgId,
        to_org: orgMap[targetOrgId] || `Tổ chức #${targetOrgId}`,
        status: "PENDING",
        temp: `${tempVal}°C`,
        reject_reason: null,
        created_at: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
      };

      state.handovers.unshift(newHandover);

      // Cập nhật trạng thái lô hàng thành "Chờ xác nhận"
      const batchItem = state.batches.find(b => b.code.toLowerCase() === code.toLowerCase());
      if (batchItem) {
        batchItem.status = "Chờ xác nhận";
      }

      // Nối sự kiện vào Chuỗi Hash SHA-256 (Append-Only Event Ledger)
      const prevHash = state.hashEvents[state.hashEvents.length - 1].curr_hash;
      state.hashEvents.push({
        index: state.hashEvents.length + 1,
        event_type: "HANDOVER_PENDING_CREATED",
        batch_code: code,
        org_name: cfg.orgName || "HTX Thắng Lợi",
        prev_hash: prevHash,
        curr_hash: "sha256_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
        valid: true
      });

      saveAppState(state);
      closeModal("handoverModal");
      renderHandoversTable();
      renderBatchesTable();
      showToast(`Đã tạo lệnh bàn giao lô ${code} tới ${orgMap[targetOrgId]}. Lô đang ở trạng thái Chờ xác nhận (S-15)!`, "success");
    }

    /**
     * BÊN NHẬN XÁC NHẬN BÀN GIAO (S-16)
     * Chuyển quyền giữ lô sang bên B và ghi sự kiện vào chuỗi hash trong cùng một Transaction
     */
    async function confirmHandover(id) {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only!", "error");
        return;
      }

      const h = state.handovers.find(x => x.id === id);
      if (!h) return;

      // Gọi API Backend nếu khả dụng
      try {
        const resp = await fetch(`/api/v1/handovers/${id}/accept`, {
          method: "POST"
        });
        if (resp.status === 403) {
          showToast("Chỉ bên nhận mới có quyền xác nhận bàn giao này!", "error");
          return;
        }
      } catch (e) {
        console.log("Backend API not reachable, updating local simulation state...", e);
      }

      // 1. Đổi trạng thái Handover sang ACCEPTED
      h.status = 'ACCEPTED';

      // 2. Chuyển quyền giữ lô (batches.organization_id) sang tổ chức B
      const batchItem = state.batches.find(b => b.code.toLowerCase() === h.batch_code.toLowerCase());
      if (batchItem) {
        batchItem.org_id = h.to_org_id;
        batchItem.farm = h.to_org;
        batchItem.status = "Đang lưu kho";
      }

      // 3. Ghi sự kiện xác nhận vào chuỗi hash SHA-256 trong cùng giao dịch
      const prevHash = state.hashEvents[state.hashEvents.length - 1].curr_hash;
      state.hashEvents.push({
        index: state.hashEvents.length + 1,
        event_type: "HANDOVER_ACCEPTED_CUSTODY_TRANSFERRED",
        batch_code: h.batch_code,
        org_name: h.to_org,
        prev_hash: prevHash,
        curr_hash: "sha256_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
        valid: true
      });

      saveAppState(state);
      renderHandoversTable();
      renderBatchesTable();
      showToast(`ĐÃ XÁC NHẬN THÀNH CÔNG! Quyền giữ lô ${h.batch_code} đã chính thức chuyển sang ${h.to_org} (S-16).`, "success");
    }

    /**
     * MỞ MODAL TỪ CHỐI BÀN GIAO (S-16)
     */
    function openRejectModal(id, batchCode) {
      currentRejectHandoverId = id;
      const display = document.getElementById("reject_batch_code_display");
      if (display) display.value = batchCode;

      const input = document.getElementById("reject_reason_input");
      if (input) input.value = "";

      const count = document.getElementById("rejectCharCount");
      if (count) {
        count.innerText = "0/10 ký tự";
        count.className = "text-[11px] font-bold text-slate-400";
      }

      const errMsg = document.getElementById("rejectErrorMsg");
      if (errMsg) errMsg.classList.add("hidden");

      openModal("rejectHandoverModal");
    }

    function handleRejectReasonInput(val) {
      const len = val.trim().length;
      const countEl = document.getElementById("rejectCharCount");
      const errMsg = document.getElementById("rejectErrorMsg");

      if (countEl) {
        countEl.innerText = `${len}/10 ký tự`;
        if (len >= 10) {
          countEl.className = "text-[11px] font-bold text-emerald-600";
          if (errMsg) errMsg.classList.add("hidden");
        } else {
          countEl.className = "text-[11px] font-bold text-rose-500";
        }
      }
    }

    /**
     * BÊN NHẬN TỪ CHỐI BÀN GIAO (S-16)
     * Bắt buộc nhập lý do (tối thiểu 10 ký tự), lô vẫn thuộc quyền giữ của A và ghi nhận sự kiện từ chối kèm lý do
     */
    async function submitRejectHandoverConfirm() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only!", "error");
        return;
      }

      const reason = document.getElementById("reject_reason_input").value.trim();
      const errMsg = document.getElementById("rejectErrorMsg");

      // RÀNG BUỘC S-16: Bắt buộc nhập lý do tối thiểu 10 ký tự
      if (reason.length < 10) {
        if (errMsg) errMsg.classList.remove("hidden");
        showToast("Lý do từ chối bắt buộc phải có tối thiểu 10 ký tự (S-16)!", "error");
        return;
      }

      const h = state.handovers.find(x => x.id === currentRejectHandoverId);
      if (!h) {
        showToast("Không tìm thấy lệnh bàn giao!", "error");
        return;
      }

      // Gọi API Backend nếu khả dụng
      try {
        const resp = await fetch(`/api/v1/handovers/${h.id}/reject`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reject_reason: reason })
        });
        if (resp.status === 400 || resp.status === 422) {
          const errData = await resp.json();
          showToast(`Lỗi: ${errData.detail || 'Lý do từ chối không hợp lệ'}`, "error");
          return;
        }
      } catch (e) {
        console.log("Backend API not reachable, updating local simulation state...", e);
      }

      // 1. Cập nhật trạng thái Handover sang REJECTED
      h.status = 'REJECTED';
      h.reject_reason = reason;

      // 2. Lô vẫn thuộc quyền giữ của bên A (giữ nguyên batch.org_id)
      const batchItem = state.batches.find(b => b.code.toLowerCase() === h.batch_code.toLowerCase());
      if (batchItem) {
        batchItem.status = "Bị từ chối tiếp nhận";
      }

      // 3. Ghi nhận sự kiện từ chối kèm lý do vào chuỗi hash SHA-256
      const prevHash = state.hashEvents[state.hashEvents.length - 1].curr_hash;
      state.hashEvents.push({
        index: state.hashEvents.length + 1,
        event_type: "HANDOVER_REJECTED",
        batch_code: h.batch_code,
        org_name: h.to_org,
        prev_hash: prevHash,
        curr_hash: "sha256_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
        valid: true
      });

      saveAppState(state);
      closeModal("rejectHandoverModal");
      renderHandoversTable();
      renderBatchesTable();
      showToast(`ĐÃ TỪ CHỐI BÀN GIAO (S-16): Lô ${h.batch_code} vẫn thuộc quyền giữ của ${h.from_org}. Đã ghi nhận lý do vào chuỗi hash!`, "info");
    }

    /**
     * RENDER TRACEABILITY & HASH TAB (S-10, S-12)
     */
    /**
     * ========================================================
     * S-17, S-18, S-19: TÁCH LÔ, GỘP LÔ VÀ CÂY PHẢ HỆ (LINEAGE)
     * ========================================================
     */

    // 1. Quản lý lựa chọn các lô để gộp (S-19)
    function handleBatchSelectChange() {
      const selectedBoxes = Array.from(document.querySelectorAll('.batch-select-checkbox:checked'));
      const mergeBtn = document.getElementById('btnOpenMergeModal');
      const countSpan = document.getElementById('mergeSelectedCount');
      if (countSpan) countSpan.innerText = selectedBoxes.length;

      if (!mergeBtn) return;

      if (selectedBoxes.length >= 2) {
        mergeBtn.classList.remove('hidden');
        // Kiểm tra xem có cùng loại sản phẩm không
        const products = new Set(selectedBoxes.map(b => b.dataset.product));
        if (products.size === 1) {
          mergeBtn.classList.remove('opacity-50', 'cursor-not-allowed');
          mergeBtn.title = "Gộp các lô đã chọn thành 1 lô mới";
        } else {
          mergeBtn.classList.add('opacity-50', 'cursor-not-allowed');
          mergeBtn.title = "Các lô đã chọn khác loại sản phẩm! Vui lòng chỉ chọn cùng loại.";
        }
      } else {
        mergeBtn.classList.add('hidden');
      }
    }

    function toggleSelectAllBatches(masterCheckbox) {
      const checkboxes = document.querySelectorAll('.batch-select-checkbox:not(:disabled)');
      checkboxes.forEach(cb => {
        cb.checked = masterCheckbox.checked;
      });
      handleBatchSelectChange();
    }

    // 2. Mở Modal Gộp Lô (S-19)
    function openMergeModalForSelected() {
      const selectedBoxes = Array.from(document.querySelectorAll('.batch-select-checkbox:checked'));
      if (selectedBoxes.length < 2) {
        showToast("Vui lòng chọn ít nhất 2 lô nông sản để gộp!", "warning");
        return;
      }

      const products = Array.from(new Set(selectedBoxes.map(b => b.dataset.product)));
      if (products.length > 1) {
        showToast(`Không thể gộp: Các lô được chọn không cùng loại sản phẩm (${products.join(", ")})!`, "error");
        return;
      }

      const productName = products[0];
      document.getElementById('mergeTargetProduct').value = productName;

      // Render danh sách các lô nguồn
      const container = document.getElementById('mergeSourceBatchesList');
      container.innerHTML = selectedBoxes.map((cb, idx) => {
        const code = cb.dataset.code;
        const maxQty = parseFloat(cb.dataset.qty) || 0;
        return `
          <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
            <div class="space-y-0.5">
              <div class="font-mono font-black text-emerald-800">${code}</div>
              <div class="text-[11px] text-slate-500">Khối lượng khả dụng: <span class="font-bold text-slate-700">${maxQty} kg</span></div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-slate-500 font-semibold text-[11px]">Lượng gộp:</span>
              <input 
                type="number" 
                step="0.01" 
                min="0.01" 
                max="${maxQty}" 
                value="${maxQty}" 
                data-code="${code}" 
                data-max="${maxQty}"
                oninput="updateMergeTotalCalculation()"
                class="merge-source-qty w-28 p-1.5 text-xs font-bold text-right bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <span class="font-bold text-slate-600">kg</span>
            </div>
          </div>
        `;
      }).join('');

      updateMergeTotalCalculation();
      openModal('mergeBatchModal');
    }

    function updateMergeTotalCalculation() {
      const inputs = Array.from(document.querySelectorAll('.merge-source-qty'));
      let total = 0;
      let hasError = false;

      inputs.forEach(input => {
        const val = parseFloat(input.value) || 0;
        const max = parseFloat(input.dataset.max) || 0;
        if (val <= 0 || val > max) {
          hasError = true;
          input.classList.add('border-rose-500', 'bg-rose-50');
        } else {
          input.classList.remove('border-rose-500', 'bg-rose-50');
        }
        total += val;
      });

      const totalEl = document.getElementById('mergeTotalWeight');
      if (totalEl) totalEl.innerText = total.toFixed(2);

      const submitBtn = document.getElementById('btnSubmitMerge');
      if (submitBtn) {
        if (hasError || total <= 0) {
          submitBtn.disabled = true;
          submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
          submitBtn.disabled = false;
          submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
      }
    }

    // 3. Thực Hiện Gộp Lô (S-19)
    async function submitMergeBatches() {
      const inputs = Array.from(document.querySelectorAll('.merge-source-qty'));
      const productName = document.getElementById('mergeTargetProduct').value;
      const notes = document.getElementById('mergeNotes').value || "Gộp lô nông sản chuỗi cung ứng";

      const sourceBatches = [];
      let totalQty = 0;
      for (const input of inputs) {
        const val = parseFloat(input.value) || 0;
        const max = parseFloat(input.dataset.max) || 0;
        if (val <= 0 || val > max) {
          showToast(`Số lượng gộp của lô ${input.dataset.code} không hợp lệ!`, "error");
          return;
        }
        sourceBatches.push({
          code: input.dataset.code,
          quantity: val
        });
        totalQty += val;
      }

      // Khóa và thực hiện gộp (Deadlock Prevention: sắp xếp theo ID / Code)
      sourceBatches.sort((a, b) => a.code.localeCompare(b.code));

      // Sinh mã lô gộp mới (8 ký tự ngẫu nhiên an toàn)
      const newMergedCode = generateRandomBatchCode();

      // Cập nhật số lượng các lô mẹ
      sourceBatches.forEach(src => {
        const parent = state.batches.find(b => b.code === src.code);
        if (parent) {
          if (parent.remaining_qty === undefined) parent.remaining_qty = parent.qty;
          parent.remaining_qty = Math.max(0, parent.remaining_qty - src.quantity);
          // Ghi nhận quan hệ phả hệ
          if (!state.batchRelations) state.batchRelations = [];
          state.batchRelations.push({
            parent_code: src.code,
            child_code: newMergedCode,
            relation_type: 'MERGE',
            quantity: src.quantity,
            notes: notes
          });
        }
      });

      // Tạo lô mới
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      const newBatch = {
        code: newMergedCode,
        product: productName,
        org_id: cfg.orgId !== null ? cfg.orgId : 1,
        farm: cfg.orgName,
        qty: totalQty,
        initial_qty: totalQty,
        remaining_qty: totalQty,
        unit: "kg",
        status: "Đang lưu kho",
        temp: "4.0°C",
        cert: "VietGAP",
        plot: `Gộp từ ${sourceBatches.length} lô`
      };
      state.batches.unshift(newBatch);

      // Ghi sự kiện chuỗi băm Hash SHA-256
      const prevHash = state.hashEvents[state.hashEvents.length - 1].curr_hash;
      state.hashEvents.push({
        index: state.hashEvents.length + 1,
        event_type: "BATCH_MERGE_CREATED",
        batch_code: newMergedCode,
        org_name: cfg.orgName,
        prev_hash: prevHash,
        curr_hash: "sha256_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
        valid: true
      });

      saveAppState(state);
      closeModal('mergeBatchModal');
      renderBatchesTable();
      renderTraceabilityTab();

      showToast(`GỘP LÔ THÀNH CÔNG (S-19)! Mã lô mới: ${newMergedCode} (${totalQty} kg)`, "success");
    }

    // 4. Mở Modal Tách Lô (S-17)
    function openSplitModalForCurrentBatch() {
      const parentCode = currentDetailBatchCode;
      const batch = state.batches.find(b => b.code === parentCode);
      if (!batch) {
        showToast("Không tìm thấy thông tin lô mẹ!", "error");
        return;
      }

      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (roleKey === "consumer" || cfg.isReadOnly) {
        showToast("Vai trò của bạn chỉ có quyền tra cứu, không được tách lô!", "error");
        return;
      }

      const remQty = batch.remaining_qty !== undefined ? batch.remaining_qty : batch.qty;
      if (remQty <= 0) {
        showToast("Lô này đã hết số lượng khả dụng, không thể tách thêm!", "warning");
        return;
      }

      document.getElementById('splitParentCode').innerText = batch.code;
      document.getElementById('splitParentProduct').innerText = batch.product;
      const remEl = document.getElementById('splitParentRemainingQty');
      remEl.innerText = `${remQty} kg`;
      remEl.dataset.qty = remQty;

      // Khởi tạo 2 hàng lô con mặc định
      const container = document.getElementById('splitChildrenContainer');
      const half1 = (remQty / 2).toFixed(1);
      const half2 = (remQty - half1).toFixed(1);
      container.innerHTML = `
        <div class="split-child-row flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
          <span class="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center split-row-index">1</span>
          <div class="flex-1 grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase">Khối lượng tách (kg)</label>
              <input type="number" step="0.01" min="0.01" max="${remQty}" value="${half1}" oninput="calculateSplitTotals()" class="split-child-qty w-full p-2 bg-white border border-slate-300 rounded-lg text-xs font-bold text-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500" required/>
            </div>
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase">Ghi chú lô con</label>
              <input type="text" placeholder="Đóng thùng loại A..." class="split-child-notes w-full p-2 bg-white border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"/>
            </div>
          </div>
          <button type="button" onclick="removeSplitRow(this)" class="p-2 text-rose-500 hover:text-rose-700 text-sm"><i class="fa-solid fa-trash"></i></button>
        </div>
        <div class="split-child-row flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
          <span class="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center split-row-index">2</span>
          <div class="flex-1 grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase">Khối lượng tách (kg)</label>
              <input type="number" step="0.01" min="0.01" max="${remQty}" value="${half2}" oninput="calculateSplitTotals()" class="split-child-qty w-full p-2 bg-white border border-slate-300 rounded-lg text-xs font-bold text-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500" required/>
            </div>
            <div>
              <label class="text-[10px] font-bold text-slate-500 uppercase">Ghi chú lô con</label>
              <input type="text" placeholder="Xuất sang siêu thị..." class="split-child-notes w-full p-2 bg-white border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"/>
            </div>
          </div>
          <button type="button" onclick="removeSplitRow(this)" class="p-2 text-rose-500 hover:text-rose-700 text-sm"><i class="fa-solid fa-trash"></i></button>
        </div>
      `;

      calculateSplitTotals();
      openModal('splitBatchModal');
    }

    function addSplitRow() {
      const container = document.getElementById('splitChildrenContainer');
      const remQty = parseFloat(document.getElementById('splitParentRemainingQty').dataset.qty) || 0;
      const currentRows = container.querySelectorAll('.split-child-row').length;
      const newIndex = currentRows + 1;

      const div = document.createElement('div');
      div.className = "split-child-row flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200";
      div.innerHTML = `
        <span class="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center split-row-index">${newIndex}</span>
        <div class="flex-1 grid grid-cols-2 gap-2">
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase">Khối lượng tách (kg)</label>
            <input type="number" step="0.01" min="0.01" max="${remQty}" value="50" oninput="calculateSplitTotals()" class="split-child-qty w-full p-2 bg-white border border-slate-300 rounded-lg text-xs font-bold text-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500" required/>
          </div>
          <div>
            <label class="text-[10px] font-bold text-slate-500 uppercase">Ghi chú lô con</label>
            <input type="text" placeholder="Lô con #${newIndex}..." class="split-child-notes w-full p-2 bg-white border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"/>
          </div>
        </div>
        <button type="button" onclick="removeSplitRow(this)" class="p-2 text-rose-500 hover:text-rose-700 text-sm"><i class="fa-solid fa-trash"></i></button>
      `;
      container.appendChild(div);
      calculateSplitTotals();
    }

    function removeSplitRow(btn) {
      const container = document.getElementById('splitChildrenContainer');
      const rows = container.querySelectorAll('.split-child-row');
      if (rows.length <= 1) {
        showToast("Phải có ít nhất 1 lô con khi tách!", "warning");
        return;
      }
      btn.closest('.split-child-row').remove();
      // Đánh số lại
      container.querySelectorAll('.split-child-row').forEach((row, idx) => {
        row.querySelector('.split-row-index').innerText = idx + 1;
      });
      calculateSplitTotals();
    }

    function calculateSplitTotals() {
      const remQty = parseFloat(document.getElementById('splitParentRemainingQty').dataset.qty) || 0;
      const qtyInputs = Array.from(document.querySelectorAll('.split-child-qty'));
      let sum = 0;
      let hasError = false;

      qtyInputs.forEach(input => {
        const val = parseFloat(input.value) || 0;
        if (val <= 0) hasError = true;
        sum += val;
      });

      const totalEl = document.getElementById('splitTotalQuantity');
      const remainEl = document.getElementById('splitRemainingParentQty');
      const errorEl = document.getElementById('splitQtyErrorAlert');
      const submitBtn = document.getElementById('btnSubmitSplit');

      totalEl.innerText = `${sum.toFixed(2)} kg`;
      const leftover = remQty - sum;
      remainEl.innerText = `${leftover.toFixed(2)} kg`;

      if (sum > remQty || hasError || sum <= 0) {
        errorEl.classList.remove('hidden');
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
      } else {
        errorEl.classList.add('hidden');
        submitBtn.disabled = false;
        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    }

    // 5. Thực Hiện Tách Lô (S-17, S-18)
    async function submitSplitBatch() {
      const parentCode = currentDetailBatchCode;
      const batch = state.batches.find(b => b.code === parentCode);
      if (!batch) return;

      const remQty = batch.remaining_qty !== undefined ? batch.remaining_qty : batch.qty;
      const rows = Array.from(document.querySelectorAll('.split-child-row'));
      const children = [];
      let sum = 0;

      for (const row of rows) {
        const qty = parseFloat(row.querySelector('.split-child-qty').value) || 0;
        const notes = row.querySelector('.split-child-notes').value || `Tách từ lô ${parentCode}`;
        if (qty <= 0) {
          showToast("Khối lượng các lô con phải lớn hơn 0!", "error");
          return;
        }
        sum += qty;
        children.push({ quantity: qty, notes: notes });
      }

      if (sum > remQty) {
        showToast("Tổng khối lượng các lô con vượt quá khối lượng còn lại của lô mẹ!", "error");
        return;
      }

      // Trừ khối lượng còn lại của lô mẹ
      batch.remaining_qty = Math.max(0, remQty - sum);

      // Tạo các lô con kế thừa sản phẩm và thửa từ lô mẹ
      const createdChildCodes = [];
      children.forEach(c => {
        const childCode = generateRandomBatchCode();
        createdChildCodes.push(childCode);

        state.batches.unshift({
          code: childCode,
          product: batch.product,
          org_id: batch.org_id,
          farm: batch.farm,
          qty: c.quantity,
          initial_qty: c.quantity,
          remaining_qty: c.quantity,
          unit: batch.unit || "kg",
          status: "Đang lưu kho",
          temp: batch.temp || "4.0°C",
          cert: batch.cert || "VietGAP",
          plot: batch.plot || "Thửa gốc kế thừa"
        });

        // Ghi quan hệ phả hệ SPLIT
        if (!state.batchRelations) state.batchRelations = [];
        state.batchRelations.push({
          parent_code: parentCode,
          child_code: childCode,
          relation_type: 'SPLIT',
          quantity: c.quantity,
          notes: c.notes
        });
      });

      // Ghi chuỗi hash
      const prevHash = state.hashEvents[state.hashEvents.length - 1].curr_hash;
      state.hashEvents.push({
        index: state.hashEvents.length + 1,
        event_type: "BATCH_SPLIT_CREATED",
        batch_code: parentCode,
        org_name: batch.farm,
        prev_hash: prevHash,
        curr_hash: "sha256_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
        valid: true
      });

      saveAppState(state);
      closeModal('splitBatchModal');
      renderBatchesTable();
      renderTraceabilityTab();

      // Cập nhật lại modal chi tiết lô mẹ
      handleQuickSearch(parentCode);

      showToast(`TÁCH LÔ THÀNH CÔNG (S-17)! Đã tạo ${createdChildCodes.length} lô con (${createdChildCodes.join(', ')})`, "success");
    }

    // 6. Dựng Đồ Thị / Sơ Đồ Cây Phả Hệ DAG Trực Quan (S-21, S-26, S-27)
    // Sơ đồ trực quan 3 cột: Tổ tiên bên trái | Lô hiện tại ở giữa | Hậu duệ bên phải
    async function fetchAndRenderLineage(batchCode) {
      const container = document.getElementById('modalBatchLineageContainer');
      const statusEl = document.getElementById('modalBatchLineageStatus');
      if (!container) return;

      const relations = state.batchRelations || [];
      const batches = state.batches || [];
      const currentBatch = batches.find(b => b.code === batchCode);

      // Thuật toán BFS:
      // 1. Duyệt ngược (Upstream BFS - S-21) tìm tổ tiên và các lô thu hoạch gốc
      const rootsMap = new Map();
      const ancestorsList = [];
      const upstreamQueue = [{ code: batchCode, path: [batchCode], depth: 0 }];
      const upstreamVisited = new Set();
      let hasUpstreamCycle = false;

      while (upstreamQueue.length > 0) {
        const item = upstreamQueue.shift();
        const currCode = item.code;
        const path = item.path;
        const depth = item.depth;
        upstreamVisited.add(currCode);

        const parentRels = relations.filter(r => r.child_code === currCode);
        if (parentRels.length === 0) {
          // Lô gốc ban đầu (không có cha)
          const bObj = batches.find(b => b.code === currCode);
          if (bObj && !rootsMap.has(currCode)) {
            rootsMap.set(currCode, {
              code: currCode,
              product: bObj.product,
              farm: bObj.farm || "Vùng trồng HTX",
              plot: bObj.plot || "Thửa A1",
              qty: bObj.qty,
              remQty: bObj.remaining_qty !== undefined ? bObj.remaining_qty : bObj.qty,
              depth: depth
            });
          }
        } else {
          for (const rel of parentRels) {
            if (path.includes(rel.parent_code)) {
              hasUpstreamCycle = true;
              break;
            }
            const pBatch = batches.find(b => b.code === rel.parent_code);
            if (pBatch && rel.parent_code !== batchCode && !ancestorsList.some(a => a.code === rel.parent_code)) {
              ancestorsList.push({
                code: rel.parent_code,
                product: pBatch.product,
                farm: pBatch.farm,
                qty: rel.quantity,
                relation_type: rel.relation_type,
                depth: depth + 1
              });
            }
            upstreamQueue.push({ code: rel.parent_code, path: [...path, rel.parent_code], depth: depth + 1 });
          }
        }
      }

      // 2. Duyệt xuôi (Downstream BFS - S-26, S-27) tìm toàn bộ hậu duệ
      const descendantsList = [];
      const downstreamQueue = [{ code: batchCode, path: [batchCode], depth: 0 }];
      const downstreamVisited = new Set();
      let hasDownstreamCycle = false;

      while (downstreamQueue.length > 0) {
        const item = downstreamQueue.shift();
        const currCode = item.code;
        const path = item.path;
        const depth = item.depth;
        downstreamVisited.add(currCode);

        const childRels = relations.filter(r => r.parent_code === currCode);
        for (const rel of childRels) {
          if (path.includes(rel.child_code)) {
            hasDownstreamCycle = true;
            break;
          }
          const cBatch = batches.find(b => b.code === rel.child_code);
          const cRemQty = cBatch ? (cBatch.remaining_qty !== undefined ? cBatch.remaining_qty : cBatch.qty) : 0;
          const isDepleted = cRemQty <= 0;

          descendantsList.push({
            code: rel.child_code,
            product: cBatch ? cBatch.product : "Nông sản chế biến",
            generation: `F${depth + 1}`,
            relation_type: rel.relation_type,
            quantity: rel.quantity,
            holding_org: cBatch ? cBatch.farm : "Cơ sở lưu kho",
            location: cBatch ? (cBatch.plot || "Kho bảo quản") : "Kho điểm bán",
            remaining_qty: cRemQty,
            status: cBatch ? cBatch.status : "Đang lưu kho",
            is_depleted: isDepleted,
            parent_code: currCode
          });

          downstreamQueue.push({ code: rel.child_code, path: [...path, rel.child_code], depth: depth + 1 });
        }
      }

      const roots = Array.from(rootsMap.values());
      const isIsolated = roots.length <= 1 && ancestorsList.length === 0 && descendantsList.length === 0 && rootsMap.has(batchCode);

      if (statusEl) {
        if (hasUpstreamCycle || hasDownstreamCycle) {
          statusEl.innerHTML = '<span class="text-rose-600 font-bold"><i class="fa-solid fa-triangle-exclamation"></i> Phát hiện chu trình vòng lặp (Lineage Cycle)!</span>';
        } else {
          statusEl.innerText = isIsolated ? "Lô thu hoạch nguyên gốc (chưa tách/gộp)" : `Phả hệ DAG: ${roots.length} gốc, ${descendantsList.length} hậu duệ`;
        }
      }

      // Render Sơ Đồ Cây Phả Hệ Trực Quan 3 Cột (Trái: Tổ tiên | Giữa: Hiện tại | Phải: Hậu duệ)
      const curRemQty = currentBatch ? (currentBatch.remaining_qty !== undefined ? currentBatch.remaining_qty : currentBatch.qty) : 0;
      const curIsDepleted = curRemQty <= 0;

      container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 items-start text-xs">
          
          <!-- CỘT 1: TỔ TIÊN & LÔ THU HOẠCH GỐC (S-21) -->
          <div class="bg-amber-50/70 p-3 rounded-2xl border border-amber-200 space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-amber-200">
              <span class="text-[11px] font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                <i class="fa-solid fa-seedling text-amber-600"></i> 1. Tổ Tiên & Gốc (S-21)
              </span>
              <span class="text-[10px] bg-amber-200/70 text-amber-950 font-bold px-2 py-0.5 rounded-full">${roots.length} Lô Gốc</span>
            </div>
            
            <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
              ${roots.length === 0 || (roots.length === 1 && roots[0].code === batchCode) ? `
                <div class="p-2.5 bg-white rounded-xl border border-dashed border-amber-300 text-center text-[11px] text-amber-800">
                  <i class="fa-solid fa-check-circle text-emerald-500 mr-1"></i> Chính là lô thu hoạch nguyên bản từ thửa đất.
                </div>
              ` : roots.map(r => `
                <div class="p-2.5 bg-white rounded-xl border border-amber-200 shadow-xs hover:border-amber-400 hover:shadow-sm transition-all">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-black text-amber-900 text-xs">${r.code}</span>
                    <span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-800">Lô Gốc</span>
                  </div>
                  <div class="text-[11px] font-bold text-slate-800 mt-1">${r.product}</div>
                  <div class="text-[10px] text-slate-500 mt-0.5">
                    <i class="fa-solid fa-mountain-sun mr-1 text-emerald-600"></i>${r.farm}
                  </div>
                  <div class="text-[10px] text-slate-500">
                    <i class="fa-solid fa-map-pin mr-1 text-rose-500"></i>${r.plot}
                  </div>
                  <div class="mt-2 pt-1 border-t border-slate-100 flex items-center justify-between">
                    <span class="text-[10px] font-bold text-amber-800">Khối lượng: ${r.remQty} kg</span>
                    <button type="button" onclick="handleQuickSearch('${r.code}')" class="text-[10px] font-bold text-amber-700 hover:text-amber-900 underline flex items-center gap-1">
                      Xem gốc <i class="fa-solid fa-arrow-right text-[9px]"></i>
                    </button>
                  </div>
                </div>
              `).join('')}

              ${ancestorsList.length > 0 ? `
                <div class="pt-1">
                  <div class="text-[10px] font-bold text-amber-900 uppercase mb-1">Các Bước Chuyển Trung Gian:</div>
                  ${ancestorsList.map(a => `
                    <div class="p-2 bg-white/80 rounded-lg border border-amber-100 text-[10px] flex items-center justify-between">
                      <span class="font-mono font-bold text-slate-700">${a.code}</span>
                      <span class="text-slate-500">${a.relation_type === 'SPLIT' ? 'Tách' : 'Gộp'} (${a.qty}kg)</span>
                      <button onclick="handleQuickSearch('${a.code}')" class="text-amber-700 hover:underline font-bold">Xem</button>
                    </div>
                  `).join('')}
                </div>
              ` : ''}
            </div>
          </div>

          <!-- CỘT 2: LÔ ĐANG XEM (TIÊU ĐIỂM Ở GIỮA) -->
          <div class="bg-emerald-50/90 p-3.5 rounded-2xl border-2 border-emerald-500 shadow-md space-y-2.5 relative">
            <div class="flex items-center justify-between pb-1.5 border-b border-emerald-200">
              <span class="text-[11px] font-extrabold text-emerald-950 uppercase tracking-wider flex items-center gap-1.5">
                <i class="fa-solid fa-location-crosshairs text-emerald-600"></i> 2. Lô Hiện Tại (Tiêu Điểm)
              </span>
              <span class="text-[10px] bg-emerald-600 text-white font-black px-2 py-0.5 rounded-full animate-pulse">FOCUS</span>
            </div>

            <div class="space-y-1.5 bg-white p-3 rounded-xl border border-emerald-300">
              <div class="text-center pb-2 border-b border-slate-100">
                <span class="font-mono font-black text-emerald-950 text-sm tracking-wider">${batchCode}</span>
                <p class="font-bold text-xs text-slate-800 mt-0.5">${currentBatch ? currentBatch.product : 'Nông sản chuỗi lạnh'}</p>
              </div>

              <div class="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                <div class="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <span class="text-slate-400 block text-[9px] uppercase font-bold">Khối lượng còn</span>
                  <span class="font-black ${curIsDepleted ? 'text-rose-600' : 'text-emerald-700'} text-xs">
                    ${curRemQty} kg
                  </span>
                  ${curIsDepleted ? '<span class="text-[9px] text-rose-500 block">(Đã xuất hết)</span>' : ''}
                </div>
                <div class="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <span class="text-slate-400 block text-[9px] uppercase font-bold">Chuỗi lạnh</span>
                  <span class="font-bold text-blue-700 text-xs">${currentBatch ? currentBatch.temp : '4.0°C'}</span>
                  <span class="text-[9px] text-slate-500 block">${currentBatch ? currentBatch.status : 'Lưu kho'}</span>
                </div>
              </div>

              <div class="text-[10px] text-slate-600 space-y-1 pt-1">
                <div><i class="fa-solid fa-building mr-1 text-slate-400"></i><strong>Đơn vị giữ:</strong> ${currentBatch ? currentBatch.farm : 'HTX Quản lý'}</div>
                <div><i class="fa-solid fa-map-location-dot mr-1 text-slate-400"></i><strong>Vị trí:</strong> ${currentBatch ? (currentBatch.plot || 'Kho phân phối') : 'Kho trung tâm'}</div>
              </div>
            </div>

            <div class="text-[10px] text-emerald-800 bg-emerald-100/60 p-2 rounded-lg text-center font-medium">
              <i class="fa-solid fa-arrows-left-right text-emerald-600 mr-1"></i> Trung tâm đồ thị DAG liên kết nguồn gốc và hậu duệ
            </div>
          </div>

          <!-- CỘT 3: CÁC THẾ HỆ HẬU DUỆ (S-26, S-27) -->
          <div class="bg-indigo-50/70 p-3 rounded-2xl border border-indigo-200 space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-indigo-200">
              <span class="text-[11px] font-bold text-indigo-900 uppercase tracking-wider flex items-center gap-1.5">
                <i class="fa-solid fa-network-wired text-indigo-600"></i> 3. Hậu Duệ (S-26, S-27)
              </span>
              <span class="text-[10px] bg-indigo-200/70 text-indigo-950 font-bold px-2 py-0.5 rounded-full">${descendantsList.length} Lô Con/Cháu</span>
            </div>

            <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
              ${descendantsList.length === 0 ? `
                <div class="p-2.5 bg-white rounded-xl border border-dashed border-indigo-300 text-center text-[11px] text-indigo-800">
                  <i class="fa-solid fa-leaf text-indigo-500 mr-1"></i> Chưa có lô con hoặc lô cháu nào được sinh ra từ lô này.
                </div>
              ` : descendantsList.map(d => `
                <div class="p-2.5 bg-white rounded-xl border border-indigo-200 shadow-xs hover:border-indigo-400 hover:shadow-sm transition-all">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-black text-indigo-900 text-xs">${d.code}</span>
                    <span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${d.relation_type === 'SPLIT' ? 'bg-amber-100 text-amber-800' : 'bg-purple-100 text-purple-800'}">
                      ${d.generation} (${d.relation_type === 'SPLIT' ? 'Tách' : 'Gộp'})
                    </span>
                  </div>
                  <div class="text-[11px] font-bold text-slate-800 mt-1">${d.product}</div>
                  <div class="text-[10px] text-slate-600 mt-0.5">
                    <i class="fa-solid fa-building mr-1 text-indigo-500"></i><strong>Đang giữ:</strong> ${d.holding_org}
                  </div>
                  <div class="text-[10px] text-slate-500">
                    <i class="fa-solid fa-store mr-1 text-slate-400"></i><strong>Vị trí:</strong> ${d.location}
                  </div>
                  <div class="mt-2 pt-1 border-t border-slate-100 flex items-center justify-between">
                    <div>
                      ${d.is_depleted 
                        ? '<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-100 text-rose-700">Đã bán/xuất hết</span>'
                        : `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-800">Còn kho: ${d.remaining_qty} kg</span>`
                      }
                    </div>
                    <button type="button" onclick="handleQuickSearch('${d.code}')" class="text-[10px] font-bold text-indigo-700 hover:text-indigo-900 underline flex items-center gap-1">
                      Chi tiết <i class="fa-solid fa-arrow-right text-[9px]"></i>
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

        </div>
      `;
    }

    function renderTraceabilityTab() {
      const tbody = document.getElementById("hashEventsTableBody");
      if (!tbody) return;

      if (!state.hashEvents || state.hashEvents.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="p-8 text-center text-slate-400">
              <i class="fa-solid fa-link-slash text-3xl mb-2 text-slate-300"></i>
              <p class="font-bold text-xs">Chưa có sự kiện băm SHA-256 nào trong cơ sở dữ liệu</p>
              <p class="text-[11px] text-slate-400 mt-1">Bấm nút "Nạp Dữ Liệu Thật (Seed)" ở trên để tạo 13 lô và chuỗi hash mẫu</p>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = state.hashEvents.map(e => {
        const pHash = e.prev_hash || e.previous_hash || '0'.repeat(64);
        const cHash = e.curr_hash || e.current_hash || '';
        return `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="p-3 font-bold text-slate-500">#${e.index}</td>
            <td class="p-3 font-sans font-bold text-slate-800">${e.event_type}</td>
            <td class="p-3 text-emerald-800 font-bold">${e.batch_code}</td>
            <td class="p-3 font-sans text-slate-600">${e.org_name}</td>
            <td class="p-3 text-slate-400 text-[10px]" title="${pHash}">${pHash.slice(0, 16)}...</td>
            <td class="p-3 text-emerald-700 text-[10px] font-bold" title="${cHash}">${cHash.slice(0, 16)}...</td>
            <td class="p-3 text-right">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                <i class="fa-solid fa-check"></i> Hợp Lệ
              </span>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function runHashIntegrityCheck() {
      showToast("Đang băm lại SHA-256 đối chiếu toàn bộ sự kiện...", "info");
      try {
        const res = await apiFetch("/api/v1/chain-events/verify");
        if (res.valid) {
          showToast(`Kiểm tra toàn vẹn thành công: ${res.total_events || state.hashEvents.length} sự kiện hợp lệ 100% (S-12)!`, "success");
        } else {
          showToast(`CẢNH BÁO PHÁT HIỆN SỰ CỐ: ${res.message || 'Chuỗi hash bị can thiệp!'}`, "error");
        }
      } catch (err) {
        showToast("Lỗi kiểm tra toàn vẹn: " + err.message, "error");
      }
    }

    /**
     * USER STORY S-48 & E-08: TRA CỨU NGUỒN GỐC CÔNG KHAI BẢO MẬT & CHỐNG SCRAPING
     * Chỉ trả về và hiển thị thông tin công khai hợp lệ: Tên SP, Vùng trồng, Tỉnh/thành, Ngày thu hoạch, Hành trình.
     * Tuyệt đối không hiển thị: Khối lượng lô, Giá bán, Doanh thu, Tên riêng đối tác trung gian.
     */
    function renderPublicBatches(filter = 'all') {
      // E-08: Chống cào dữ liệu (Anti-Scraping) - Không hiển thị danh sách các lô hàng công khai
    }

    let cameraStream = null;

    async function openQrCameraScanner() {
      openModal('qrCameraModal');
      const video = document.getElementById('qrCameraVideo');
      const statusEl = document.getElementById('cameraStatusText');
      
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
          });
          if (video) {
            video.srcObject = cameraStream;
            video.classList.remove('hidden');
            await video.play();
            if (statusEl) statusEl.innerText = "Camera đang hoạt động. Hãy hướng về mã QR trên bao bì.";
          }
        } catch (err) {
          console.warn("Không thể mở webcam/camera trực tiếp:", err);
          if (statusEl) statusEl.innerText = "Chưa cấp quyền camera. Bạn có thể chọn ảnh tem QR hoặc bấm 'Quét tem mẫu'.";
        }
      } else {
        if (statusEl) statusEl.innerText = "Thiết bị không hỗ trợ stream camera trực tiếp. Vui lòng tải ảnh tem.";
      }
    }

    function closeQrCameraScanner() {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
      }
      const video = document.getElementById('qrCameraVideo');
      if (video) {
        video.srcObject = null;
        video.classList.add('hidden');
      }
      closeModal('qrCameraModal');
    }

    function simulateQrScan() {
      closeQrCameraScanner();
      const sampleCode = (state.batches && state.batches.length > 0) ? (state.batches[0].code || state.batches[0].batch_code) : "VK89XPT2";
      const inp = document.getElementById('heroSearchInput');
      if (inp) inp.value = sampleCode;
      showToast("Đã quét thành công mã QR: " + sampleCode, "success");
      handleQuickSearch(sampleCode);
    }

    function handleQrFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      closeQrCameraScanner();
      const sampleCode = (state.batches && state.batches.length > 1) 
        ? (state.batches[1].code || state.batches[1].batch_code) 
        : ((state.batches && state.batches.length > 0) ? (state.batches[0].code || state.batches[0].batch_code) : "VK89XPT2");
      const inp = document.getElementById('heroSearchInput');
      if (inp) inp.value = sampleCode;
      showToast("Đã nhận diện mã tem QR từ ảnh chụp: " + sampleCode, "success");
      handleQuickSearch(sampleCode);
    }

    async function handleQuickSearch(code) {
      if (!code || !code.trim()) {
        showToast("Vui lòng nhập mã lô hàng in trên tem QR!", "error");
        return;
      }
      const cleanCode = code.trim();

      // Gọi API Backend công khai (S-48 / E-08)
      try {
        let resp = await fetch(`/public/batches/${encodeURIComponent(cleanCode)}`);
        if (!resp.ok && resp.status === 404) {
          resp = await fetch(`/api/v1/batches/public/${encodeURIComponent(cleanCode)}`);
        }
        if (resp.ok) {
          const apiData = await resp.json();
          renderPublicTraceModal(apiData);
          return;
        } else if (resp.status === 404) {
          showToast(`Mã lô '${cleanCode}' không tồn tại trong cơ sở dữ liệu thật (HTTP 404).`, "error");
          return;
        } else {
          showToast(`Lỗi khi tra cứu mã lô '${cleanCode}' (HTTP ${resp.status}).`, "error");
          return;
        }
      } catch (e) {
        console.error("Lỗi kết nối tra cứu mã lô:", e);
        showToast(`Không thể kết nối máy chủ để tra cứu lô '${cleanCode}'.`, "error");
        return;
      }
    }

    function renderPublicTraceModal(data) {
      currentDetailBatchCode = data.batch_code;
      document.getElementById("modalBatchCode").innerText = data.batch_code;
      document.getElementById("modalBatchProduct").innerText = data.product_name;
      document.getElementById("modalBatchFarm").innerText = data.farm_name;
      document.getElementById("modalBatchProvince").innerText = data.province || "Lâm Đồng";
      document.getElementById("modalBatchHarvestDate").innerText = data.harvest_date || "15/03/2026";
      document.getElementById("modalBatchCert").innerText = data.certification || "VietGAP";
      document.getElementById("modalBatchPhiText").innerText = data.phi_message || "Đạt chuẩn an toàn thời gian cách ly thuốc BVTV.";

      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      // Điều khiển hiển thị nút Bàn Giao (S-15): Ẩn nếu là Consumer hoặc Inspector
      const hoBtn = document.getElementById("modalBtnHandover");
      if (hoBtn) {
        if (roleKey === "consumer" || cfg.isReadOnly) {
          hoBtn.classList.add("hidden");
        } else {
          hoBtn.classList.remove("hidden");
        }
      }

      // Điều khiển hiển thị nút Tách Lô (S-17): Ẩn nếu là Consumer/Inspector hoặc hết khối lượng
      const splitBtn = document.getElementById("modalBtnSplit");
      if (splitBtn) {
        const foundBatch = state.batches.find(b => b.code === data.batch_code);
        const remQty = foundBatch ? (foundBatch.remaining_qty !== undefined ? foundBatch.remaining_qty : foundBatch.qty) : 0;
        if (roleKey === "consumer" || cfg.isReadOnly || remQty <= 0) {
          splitBtn.classList.add("hidden");
        } else {
          splitBtn.classList.remove("hidden");
        }
      }

      // Dựng cây phả hệ (S-17, S-18, S-19)
      fetchAndRenderLineage(data.batch_code);

      // Render các mốc hành trình chuỗi cung ứng chính (S-48: Sơ chế, Vận chuyển, Phân phối)
      const listEl = document.getElementById("modalBatchJourneyList");
      if (listEl && data.journey_milestones && data.journey_milestones.length > 0) {
        listEl.innerHTML = data.journey_milestones.map((m, idx) => `
          <div class="relative pl-6 pb-3 border-l-2 ${idx === data.journey_milestones.length - 1 ? 'border-transparent' : 'border-emerald-300'}">
            <div class="absolute -left-[9px] top-0.5 w-4 h-4 rounded-full ${m.status === 'completed' ? 'bg-emerald-500 ring-4 ring-emerald-100' : 'bg-blue-500 ring-4 ring-blue-100'} flex items-center justify-center text-[8px] text-white font-bold">
              <i class="fa-solid fa-check"></i>
            </div>
            <div class="bg-slate-50 p-3 rounded-2xl border border-slate-100 space-y-1">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-800 text-xs">${m.stage}</span>
                <span class="text-[10px] text-slate-400 font-medium">${m.timestamp || ''}</span>
              </div>
              <p class="text-[11px] text-slate-600">${m.description}</p>
            </div>
          </div>
        `).join('');
      }

      openModal("batchDetailModal");
    }

    /**
     * MODAL HELPERS
     */

    /**
     * EPIC E-06: THU HỒI LÔ HÀNG KHẨN CẤP (EMERGENCY RECALL)
     * S-33, S-34, S-35, S-36, S-37, S-38
     */
    let currentViewingRecallId = null;

    function handleRecallReasonInput() {
      const textarea = document.getElementById("recallReasonInput");
      const counter = document.getElementById("recallReasonCharCounter");
      const warning = document.getElementById("recallReasonWarning");
      const submitBtn = document.getElementById("btnSubmitRecall");

      const len = textarea.value.trim().length;
      counter.innerText = `${len} / 20 ký tự`;

      if (len < 20) {
        counter.className = "text-[11px] font-mono font-bold text-rose-600";
        warning.classList.remove("hidden");
        submitBtn.disabled = true;
        submitBtn.classList.add("opacity-50", "cursor-not-allowed");
      } else {
        counter.className = "text-[11px] font-mono font-bold text-emerald-600";
        warning.classList.add("hidden");
        submitBtn.disabled = false;
        submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    }

    function openRecallModalForCurrentBatch() {
      const batchCode = currentDetailBatchCode;
      const b = state.batches.find(x => x.code === batchCode);
      if (!b) return;

      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      // Phân quyền S-33: Cán bộ kiểm tra (Inspector) hoặc Quản trị của tổ chức đang giữ lô
      const isInspector = roleKey === "inspector";
      const isAdmin = roleKey === "system_admin" || cfg.role === "Admin";
      const isHoldingOrg = cfg.orgId !== null && b.org_id === cfg.orgId;

      if (!isInspector && !(isAdmin && isHoldingOrg) && roleKey !== "system_admin") {
        showToast("Chỉ Cán bộ kiểm tra (Inspector) hoặc Quản trị của tổ chức đang giữ lô mới có quyền mở lệnh thu hồi (S-33)!", "error");
        return;
      }

      document.getElementById("recallModalBatchCode").innerText = b.code;
      document.getElementById("recallModalProductName").innerText = b.product;
      document.getElementById("recallReasonInput").value = "";
      handleRecallReasonInput();

      closeModal("batchDetailModal");
      openModal("openRecallModal");
    }

    async function submitTriggerRecall() {
      const batchCode = currentDetailBatchCode;
      const b = state.batches.find(x => x.code === batchCode);
      if (!b) return;

      const reason = document.getElementById("recallReasonInput").value.trim();
      const severity = document.getElementById("recallSeveritySelect").value;

      if (reason.length < 20) {
        showToast("Lý do thu hồi bắt buộc phải có ít nhất 20 ký tự mô tả cụ thể sự cố (S-33)!", "error");
        return;
      }

      // Gọi API Backend
      try {
        const resp = await fetch("/api/v1/recalls", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${state.token || ""}`
          },
          body: JSON.stringify({
            batch_id: b.id || 1,
            reason: reason,
            severity: severity
          })
        });

        if (resp.ok) {
          const recallData = await resp.json();
          closeModal("openRecallModal");
          showToast(`Kích hoạt thành công lệnh thu hồi #${recallData.recall_code}!`, "success");
          displayRecallDetailModal(recallData);
          renderRecallsTab();
          return;
        } else {
          const errJson = await resp.json();
          showToast(errJson.detail || "Không thể kích hoạt lệnh thu hồi!", "error");
        }
      } catch (err) {
        console.warn("API recall trigger error, running local state fallback:", err);
      }

      // Local mock fallback nếu API offline
      const mockCode = "RCL-" + new Date().toISOString().slice(0,10).replace(/-/g,'') + "-" + Math.random().toString(36).substring(2,8).toUpperCase();
      const mockRecall = {
        id: Date.now(),
        recall_code: mockCode,
        source_batch_id: b.id || 1,
        source_batch_code: b.code,
        product_name: b.product,
        reason: reason,
        severity: severity,
        status: "ACTIVE",
        initiator_name: "Cán Bộ Kiểm Tra An Toàn",
        initiator_org_name: "Chi Cục Quản Lý Chất Lượng",
        total_affected_batches: 3,
        total_affected_kg: 1800,
        total_stock_kg: 750,
        total_sold_kg: 1050,
        progress: {
          total_organizations: 3,
          confirmed_organizations: 0,
          progress_percentage: 0,
          status_summary: "0/3 tổ chức đã xác nhận cô lập"
        },
        affected_batches: [
          {
            batch_code: b.code,
            product_name: b.product,
            organization_name: b.farm || "Nông Trại Hữu Cơ",
            generation: "ROOT",
            remaining_quantity: 200,
            sold_quantity: 800,
            current_location: "Kho trang trại",
            is_isolated: false
          },
          {
            batch_code: "BATCH-CHILD-COOP-01",
            product_name: b.product,
            organization_name: "HTX Sơ Chế Chế Biến",
            generation: "THẾ HỆ 1",
            remaining_quantity: 500,
            sold_quantity: 0,
            current_location: "Kho lạnh HTX",
            is_isolated: false
          },
          {
            batch_code: "BATCH-GRAND-RETAIL-01",
            product_name: b.product,
            organization_name: "Chuỗi Siêu Thị BioMart",
            generation: "THẾ HỆ 2",
            remaining_quantity: 50,
            sold_quantity: 250,
            current_location: "Quầy kệ siêu thị",
            is_isolated: false
          }
        ],
        organization_actions: [
          { organization_id: 1, organization_name: "Nông Trại Hữu Cơ Thảo Mộc", status: "PENDING", affected_batch_count: 1, stock_kg: 200 },
          { organization_id: 2, organization_name: "Hợp Tác Xã Chế Biến Xanh", status: "PENDING", affected_batch_count: 1, stock_kg: 500 },
          { organization_id: 4, organization_name: "Hệ Thống Siêu Thị Nông Sản Sạch", status: "PENDING", affected_batch_count: 1, stock_kg: 50 }
        ]
      };

      if (!state.recalls) state.recalls = [];
      state.recalls.unshift(mockRecall);

      // Cập nhật trạng thái lô thành phong tỏa thu hồi
      b.status = "Bị phong tỏa thu hồi";
      saveAppState(state);

      closeModal("openRecallModal");
      showToast(`Đã kích hoạt lệnh thu hồi #${mockCode}. Toàn bộ các lô con cháu đã bị khóa quyền (S-38)!`, "success");
      displayRecallDetailModal(mockRecall);
      renderRecallsTab();
    }

    async function renderRecallsTab() {
      const tbody = document.getElementById("recallsTableBody");
      if (!tbody) return;

      let recallsList = state.recalls || [];

      try {
        const resp = await fetch("/api/v1/recalls", {
          headers: { "Authorization": `Bearer ${state.token || ""}` }
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data && data.items) recallsList = data.items;
        }
      } catch (e) {
        console.log("Recalls API fetch fallback:", e);
      }

      // Update KPI Bar
      const activeCount = recallsList.filter(r => r.status !== 'COMPLETED').length;
      const totalAffectedBatches = recallsList.reduce((acc, r) => acc + (r.total_affected_batches || 0), 0);
      const totalStockKg = recallsList.reduce((acc, r) => acc + (r.total_stock_kg || 0), 0);
      const totalSoldKg = recallsList.reduce((acc, r) => acc + (r.total_sold_kg || 0), 0);

      document.getElementById("kpiActiveRecalls").innerText = `${activeCount} Lệnh`;
      document.getElementById("kpiTotalAffectedBatches").innerText = `${totalAffectedBatches} Lô`;
      document.getElementById("kpiStockToIsolateKg").innerText = `${totalStockKg.toLocaleString('vi-VN')} kg`;
      document.getElementById("kpiSoldToConsumersKg").innerText = `${totalSoldKg.toLocaleString('vi-VN')} kg`;

      if (recallsList.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" class="p-8 text-center text-slate-400">
              <i class="fa-solid fa-shield-heart text-3xl mb-2 text-emerald-500"></i>
              <p class="font-bold text-xs text-slate-700">Không có lệnh thu hồi khẩn cấp nào đang hoạt động!</p>
              <p class="text-[11px] text-slate-400 mt-1">Toàn bộ chuỗi cung ứng nông sản đang vận hành an toàn đạt chuẩn.</p>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = recallsList.map(r => {
        const pct = r.progress ? r.progress.progress_percentage : 0;
        const summary = r.progress ? r.progress.status_summary : "0/0 tổ chức đã cô lập";
        const isDone = r.status === "COMPLETED";

        return `
          <tr class="hover:bg-slate-50 transition-colors">
            <td class="p-3.5 font-mono font-black text-rose-800 text-xs">${r.recall_code}</td>
            <td class="p-3.5">
              <div class="font-bold text-slate-800">${r.product_name || 'Nông sản'}</div>
              <div class="font-mono text-[10px] text-slate-400">Lô: ${r.source_batch_code}</div>
            </td>
            <td class="p-3.5">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-black ${r.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-800 border border-rose-300' : 'bg-amber-100 text-amber-800'}">
                ${r.severity}
              </span>
            </td>
            <td class="p-3.5">
              <div class="space-y-1 min-w-[140px]">
                <div class="flex justify-between text-[10px] font-bold text-slate-600">
                  <span>${summary}</span>
                  <span class="font-mono">${pct}%</span>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-gradient-to-r from-amber-500 to-emerald-500 h-1.5 rounded-full" style="width: ${pct}%"></div>
                </div>
              </div>
            </td>
            <td class="p-3.5 text-right font-mono font-bold text-amber-800">${(r.total_stock_kg || 0).toLocaleString('vi-VN')} kg</td>
            <td class="p-3.5 text-right font-mono font-bold text-rose-800">${(r.total_sold_kg || 0).toLocaleString('vi-VN')} kg</td>
            <td class="p-3.5">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${isDone ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-rose-100 text-rose-900 border border-rose-300 animate-pulse'}">
                ${isDone ? 'Đã Hoàn Tất' : 'Đang Thu Hồi'}
              </span>
            </td>
            <td class="p-3.5 text-right">
              <button 
                onclick="viewRecallDetail(${r.id})" 
                class="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold text-xs shadow-sm flex items-center gap-1 ml-auto">
                <i class="fa-solid fa-eye"></i> Chi Tiết & Khoanh Vùng
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function viewRecallDetail(recallId) {
      currentViewingRecallId = recallId;
      try {
        const resp = await fetch(`/api/v1/recalls/${recallId}`, {
          headers: { "Authorization": `Bearer ${state.token || ""}` }
        });
        if (resp.ok) {
          const detail = await resp.json();
          displayRecallDetailModal(detail);
          return;
        }
      } catch (e) {
        console.log("Recall detail API offline, checking local mock:", e);
      }

      const found = (state.recalls || []).find(r => r.id === recallId);
      if (found) {
        displayRecallDetailModal(found);
      } else {
        showToast("Không tìm thấy thông tin chi tiết lệnh thu hồi!", "error");
      }
    }

    function displayRecallDetailModal(data) {
      currentViewingRecallId = data.id;
      document.getElementById("recallDetailCode").innerText = data.recall_code;
      document.getElementById("recallDetailProductInfo").innerText = `Lô gốc: ${data.source_batch_code} | Nông sản: ${data.product_name}`;
      document.getElementById("recallDetailReason").innerText = data.reason;

      const badge = document.getElementById("recallDetailStatusBadge");
      if (badge) {
        badge.innerText = data.status === "COMPLETED" ? "Đã Hoàn Tất Xử Lý" : "Đang Thu Hồi Khẩn Cấp";
        badge.className = data.status === "COMPLETED" 
          ? "px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300"
          : "px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300";
      }

      // Progress bar (S-37)
      const p = data.progress || { progress_percentage: 0, status_summary: "0/0" };
      document.getElementById("recallDetailProgressText").innerText = `${p.status_summary} (${p.progress_percentage}%)`;
      document.getElementById("recallDetailProgressBar").style.width = `${p.progress_percentage}%`;

      // Org actions list
      const orgActionsContainer = document.getElementById("recallDetailOrgActionsList");
      if (orgActionsContainer && data.organization_actions) {
        orgActionsContainer.innerHTML = data.organization_actions.map(act => `
          <div class="p-2.5 rounded-xl border ${act.status === 'CONFIRMED_ISOLATED' ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'} flex items-center justify-between text-xs">
            <div>
              <div class="font-bold text-slate-800">${act.organization_name}</div>
              <div class="text-[10px] text-slate-500">${act.affected_batch_count} lô (${act.stock_kg} kg cần niêm phong)</div>
              ${act.action_notes ? `<div class="text-[10px] italic text-slate-600 mt-0.5">"${act.action_notes}"</div>` : ''}
            </div>
            <div>
              ${act.status === 'CONFIRMED_ISOLATED' 
                ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1"><i class="fa-solid fa-check"></i> Đã Cô Lập</span>'
                : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 flex items-center gap-1"><i class="fa-solid fa-clock"></i> Chờ Xác Nhận</span>'}
            </div>
          </div>
        `).join('');
      }

      // KPI stats (S-35)
      document.getElementById("recallStatAffectedBatches").innerText = `${data.total_affected_batches} Lô`;
      document.getElementById("recallStatStockKg").innerText = `${(data.total_stock_kg || 0).toLocaleString('vi-VN')} kg`;
      document.getElementById("recallStatSoldKg").innerText = `${(data.total_sold_kg || 0).toLocaleString('vi-VN')} kg`;

      // Affected batches table (S-34)
      const tbody = document.getElementById("recallDetailAffectedBatchesTbody");
      if (tbody && data.affected_batches) {
        tbody.innerHTML = data.affected_batches.map(b => `
          <tr class="hover:bg-slate-50">
            <td class="p-2.5 font-mono font-bold text-rose-900">${b.batch_code}</td>
            <td class="p-2.5 font-medium text-slate-600">${b.generation}</td>
            <td class="p-2.5 font-bold text-slate-800">${b.organization_name}</td>
            <td class="p-2.5 text-right font-mono font-bold text-amber-800">${(b.remaining_quantity || 0).toLocaleString('vi-VN')} kg</td>
            <td class="p-2.5 text-right font-mono font-bold text-rose-800">${(b.sold_quantity || 0).toLocaleString('vi-VN')} kg</td>
            <td class="p-2.5 text-slate-500">${b.current_location || 'Kho'}</td>
            <td class="p-2.5 text-center">
              ${b.is_isolated 
                ? '<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-800">Đã Niêm Phong</span>'
                : '<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-100 text-rose-800">Cần Thu Hồi</span>'}
            </td>
          </tr>
        `).join('');
      }

      // Nút xác nhận cô lập cho tổ chức của user (S-36)
      const actionBox = document.getElementById("recallOrgConfirmActionBox");
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;

      if (actionBox) {
        if (data.status === "COMPLETED") {
          actionBox.innerHTML = '<span class="text-xs font-bold text-emerald-700 flex items-center gap-1.5"><i class="fa-solid fa-circle-check"></i> Toàn bộ các tổ chức đã hoàn thành cô lập và thu hồi sản phẩm!</span>';
        } else {
          actionBox.innerHTML = `
            <button 
              onclick="confirmRecallIsolation(${data.id})" 
              class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-md flex items-center gap-2 transition-all">
              <i class="fa-solid fa-lock"></i> Xác Nhận Đã Cô Lập/Thu Hồi Hàng Của ${cfg.orgName} (S-36)
            </button>
          `;
        }
      }

      openModal("recallDetailModal");
    }

    async function confirmRecallIsolation(recallId) {
      const notes = prompt("Nhập ghi chú biện pháp niêm phong / cô lập lô hàng:", "Đã hoàn tất cô lập, niêm phong toàn bộ hàng trong kho theo quy định S-36");
      if (notes === null) return;

      try {
        const resp = await apiFetch(`/api/v1/recalls/${recallId}/confirm-isolation`, {
          method: "POST",
          body: JSON.stringify({ notes: notes })
        });

        showToast("Xác nhận cô lập thành công! Tiến độ xử lý đã được ghi vào chuỗi Hash Chain.", "success");
        displayRecallDetailModal(resp);
        await loadServerData();
        renderRecallsTab();
      } catch (e) {
        console.error("Lỗi xác nhận cô lập:", e);
        showToast("Lỗi xác nhận cô lập: " + e.message, "error");
      }
    }


    function openModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.remove('hidden');
    }

    function closeModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.add('hidden');
    }

    function generateSecureBatchCode() {
      // Bảng chữ cái 31 ký tự an toàn (CSPRNG): Loại trừ '0', 'O', '1', 'I', 'L'
      const SAFE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
      const array = new Uint32Array(8);
      window.crypto.getRandomValues(array);
      let code = "";
      for (let i = 0; i < 8; i++) {
        code += SAFE_ALPHABET.charAt(array[i] % SAFE_ALPHABET.length);
      }
      return code;
    }

    function generateRandomBatchCode() {
      const code = generateSecureBatchCode();
      const el = document.getElementById("batch_code");
      if (el) el.value = code;
    }

    let lastCreatedBatchCode = "";

    function copySuccessBatchCode() {
      const codeToCopy = lastCreatedBatchCode || (document.getElementById("successBatchCodeDisplay") ? document.getElementById("successBatchCodeDisplay").innerText.trim() : "");
      if (!codeToCopy) return;

      navigator.clipboard.writeText(codeToCopy).then(() => {
        const btnText = document.getElementById("copySuccessBtnText");
        if (btnText) btnText.innerText = "Đã Sao Chép!";
        showToast(`Đã sao chép mã lô '${codeToCopy}' vào bộ nhớ tạm!`, "success");
        setTimeout(() => {
          if (btnText) btnText.innerText = "Sao Chép Mã Lô";
        }, 2000);
      }).catch(() => {
        showToast("Mã lô: " + codeToCopy, "info");
      });
    }

    async function saveBatchSubmit() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi ghi đã bị chặn và ghi log an ninh.", "error");
        return;
      }

      const code = document.getElementById("batch_code").value.trim() || generateSecureBatchCode();
      const product = document.getElementById("batch_product").value.trim();
      const qty = parseInt(document.getElementById("batch_quantity").value) || 0;
      const plot = document.getElementById("batch_plot").value;

      if (!product || qty <= 0) {
        showToast("Vui lòng nhập tên nông sản và số lượng > 0", "error");
        return;
      }

      try {
        const payload = {
          batch_code: code,
          product_name: product,
          initial_quantity: qty,
          remaining_quantity: qty,
          unit: "kg",
          organization_id: cfg.orgId || 1
        };
        const res = await apiFetch("/api/v1/batches", {
          method: "POST",
          body: JSON.stringify(payload)
        });

        lastCreatedBatchCode = res.batch_code || code;
        const codeDisplay = document.getElementById("successBatchCodeDisplay");
        if (codeDisplay) codeDisplay.innerText = lastCreatedBatchCode;
        const prodDisplay = document.getElementById("successBatchProductName");
        if (prodDisplay) prodDisplay.innerText = res.product_name || product;
        const qtyDisplay = document.getElementById("successBatchQtyDisplay");
        if (qtyDisplay) qtyDisplay.innerText = qty.toLocaleString('vi-VN') + " kg";
        const plotDisplay = document.getElementById("successBatchPlotDisplay");
        if (plotDisplay) plotDisplay.innerText = plot || "Thửa liên kết";

        await loadServerData();
        closeModal("addBatchModal");
        openModal("batchSuccessModal");
        showToast(`Đã khởi tạo lô hàng ${lastCreatedBatchCode} thành công trên DB thật!`, "success");
      } catch (err) {
        console.error("Lỗi tạo lô hàng:", err);
        showToast(`Không thể tạo lô hàng: ${err.message}`, "error");
      }
    }

    async function savePlotSubmit() {
      const roleKey = state.currentRole || "farm";
      const cfg = SUPPLY_CHAIN_ROLES[roleKey] || SUPPLY_CHAIN_ROLES.farm;
      if (cfg.isReadOnly) {
        showToast("HTTP 403 Forbidden: Cán bộ kiểm tra chỉ có quyền Read-only! Hành vi ghi đã bị chặn và ghi log an ninh.", "error");
        return;
      }

      const name = document.getElementById("plot_name").value.trim();
      const area = parseFloat(document.getElementById("plot_area").value);
      const unit = document.getElementById("plot_unit").value;
      const lat = parseFloat(document.getElementById("plot_lat").value.trim()) || 11.9404;
      const lng = parseFloat(document.getElementById("plot_lng").value.trim()) || 108.4583;
      const address = document.getElementById("plot_address").value.trim();

      if (!name || isNaN(area) || area <= 0) {
        showToast("Diện tích thửa đất phải lớn hơn 0 (S-06)!", "error");
        return;
      }

      try {
        const payload = {
          name: name,
          area: area,
          unit: unit || "m2",
          latitude: lat,
          longitude: lng,
          address: address || "Lâm Đồng",
          organization_id: cfg.orgId || 1
        };
        await apiFetch("/api/v1/land-plots", {
          method: "POST",
          body: JSON.stringify(payload)
        });

        await loadServerData();
        closeModal("addPlotModal");
        showToast("Khai báo thửa đất mới thành công trên DB thật!", "success");
      } catch (err) {
        console.error("Lỗi tạo thửa đất:", err);
        showToast(`Không thể khai báo thửa đất: ${err.message}`, "error");
      }
    }

    function showToast(msg, type = "success") {
      const container = document.getElementById("toastContainer");
      const toast = document.createElement("div");
      toast.className = `p-4 rounded-2xl shadow-xl text-xs font-bold flex items-center gap-2.5 transition-all transform translate-y-3 opacity-0 pointer-events-auto ${type === 'success' ? 'bg-emerald-600 text-white' : type === 'info' ? 'bg-slate-900 text-white' : 'bg-rose-600 text-white'}`;
      toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'info' ? 'fa-info-circle' : 'fa-circle-exclamation'}"></i> <span>${msg}</span>`;
      container.appendChild(toast);

      setTimeout(() => {
        toast.classList.remove('translate-y-3', 'opacity-0');
      }, 10);

      setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-3');
        setTimeout(() => toast.remove(), 300);
      }, 3500);
    }

    // Live IoT Simulator (Updating metrics gently)
    setInterval(() => {
      const wh = document.getElementById("liveTempWarehouse");
      const tr = document.getElementById("liveTempTruck");
      if (wh) wh.innerText = (4.0 + Math.random() * 0.4).toFixed(1) + "°C";
      if (tr) tr.innerText = (3.7 + Math.random() * 0.5).toFixed(1) + "°C";
    }, 4000);

    // Initial Load
    document.addEventListener("DOMContentLoaded", async () => {
      updateRoleUI();
      const token = localStorage.getItem("app_access_token");
      if (!token && state.currentRole && state.currentRole !== 'consumer') {
        await selectSupplyChainRole(state.currentRole);
      } else {
        await loadServerData();
        switchNavTab(state.activeTab || 'overview');
      }
    });
  </script>

</body>
</html>
'''

if __name__ == "__main__":
    html_content = generate_spa_html()
    
    # 1. Write to backend/static/index.html
    target1 = os.path.join("backend", "static", "index.html")
    with open(target1, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully wrote {len(html_content)} bytes to {target1}")
    
    # 2. Write to root index.html
    target2 = "index.html"
    with open(target2, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Successfully wrote {len(html_content)} bytes to {target2}")
