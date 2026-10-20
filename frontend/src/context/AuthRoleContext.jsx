import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch } from '../utils/api';

export const ROLES_LIST = [
  {
    id: 'system_admin',
    name: 'Quản trị hệ thống',
    code: 'SYSTEM_ADMIN',
    icon: '⚙️',
    color: 'from-purple-600 to-indigo-600',
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    desc: 'Toàn quyền cấu hình, quản trị người dùng & can thiệp khẩn cấp',
    orgName: 'Ban Quản Trị Hệ Thống',
    canSplitMerge: true,
    canOpenRecall: true,
  },
  {
    id: 'farm',
    name: 'Vùng trồng (Farm)',
    code: 'FARM',
    icon: '🌾',
    color: 'from-emerald-600 to-green-600',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    desc: 'Khai báo thửa đất, thu hoạch, xuất kho và bàn giao ban đầu',
    orgName: 'HTX Nông Nghiệp Thắng Lợi (Farm A)',
    canSplitMerge: false,
    canOpenRecall: false,
  },
  {
    id: 'processing',
    name: 'HTX Sơ chế / Chế biến',
    code: 'PROCESSING',
    icon: '🏭',
    color: 'from-blue-600 to-cyan-600',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    desc: 'Tiếp nhận nguyên liệu, Tách lô & Gộp lô sơ chế, đóng gói',
    orgName: 'HTX Sơ Chế Chế Biến Lành',
    canSplitMerge: true,
    canOpenRecall: true,
  },
  {
    id: 'logistics',
    name: 'Đơn vị Vận tải lạnh',
    code: 'LOGISTICS',
    icon: '🚚',
    color: 'from-amber-600 to-orange-600',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    desc: 'Vận chuyển bảo ôn, giám sát nhiệt độ chuỗi lạnh trên từng chuyến xe',
    orgName: 'Công Ty Vận Tải Lạnh Express',
    canSplitMerge: false,
    canOpenRecall: false,
  },
  {
    id: 'retailer',
    name: 'Nhà phân phối / Bán lẻ',
    code: 'RETAILER',
    icon: '🏪',
    color: 'from-teal-600 to-emerald-600',
    badgeColor: 'bg-teal-50 text-teal-700 border-teal-200',
    desc: 'Nhận lô sỉ, Tách lô theo điểm bán / siêu thị, quản lý kệ hàng',
    orgName: 'Chuỗi Siêu Thị BioMart',
    canSplitMerge: true,
    canOpenRecall: true,
  },
  {
    id: 'inspector',
    name: 'Cán bộ kiểm tra (Inspector)',
    code: 'INSPECTOR',
    icon: '🛡️',
    color: 'from-rose-600 to-red-600',
    badgeColor: 'bg-rose-50 text-rose-700 border-rose-200',
    desc: 'Chế độ chỉ đọc toàn hệ thống, Mở lệnh thu hồi khẩn cấp khi vi phạm',
    orgName: 'Chi Cục Quản Lý Chất Lượng & BVTV',
    canSplitMerge: false,
    canOpenRecall: true,
  },
  {
    id: 'consumer',
    name: 'Người tiêu dùng',
    code: 'CONSUMER',
    icon: '👤',
    color: 'from-slate-600 to-gray-600',
    badgeColor: 'bg-slate-100 text-slate-700 border-slate-200',
    desc: 'Tra cứu công khai không cần đăng nhập, bảo vệ thông tin mật nội bộ',
    orgName: 'Người Tiêu Dùng Đại Chúng',
    canSplitMerge: false,
    canOpenRecall: false,
  },
];

const AuthRoleContext = createContext(null);

export function AuthRoleProvider({ children }) {
  const [currentRole, setCurrentRole] = useState(() => {
    return localStorage.getItem('app_current_role') || 'system_admin';
  });
  const [token, setToken] = useState(() => {
    return localStorage.getItem('app_access_token') || null;
  });
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem('app_current_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isSwitching, setIsSwitching] = useState(false);

  const activeRoleConfig = ROLES_LIST.find((r) => r.id === currentRole) || ROLES_LIST[0];

  // Hàm chuyển đổi vai trò và đồng bộ Token từ backend
  const switchRole = async (newRole) => {
    setIsSwitching(true);
    setCurrentRole(newRole);
    localStorage.setItem('app_current_role', newRole);

    if (newRole === 'consumer') {
      setToken(null);
      setCurrentUser(null);
      localStorage.removeItem('app_access_token');
      localStorage.removeItem('app_current_user');
      setIsSwitching(false);
      return;
    }

    try {
      const res = await fetch(`/api/v1/auth/quick-role-token?role=${newRole}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        setCurrentUser(data);
        localStorage.setItem('app_access_token', data.access_token);
        localStorage.setItem('app_current_user', JSON.stringify(data));
      } else {
        const errData = await res.json().catch(() => ({}));
        console.error('Không thể lấy token xác thực cho vai trò:', res.status, errData);
        setToken(null);
        setCurrentUser(null);
        localStorage.removeItem('app_access_token');
        localStorage.removeItem('app_current_user');
      }
    } catch (err) {
      console.error('Lỗi kết nối auth quick-role-token:', err);
      setToken(null);
      setCurrentUser(null);
      localStorage.removeItem('app_access_token');
      localStorage.removeItem('app_current_user');
    } finally {
      setIsSwitching(false);
    }
  };

  // Tự động khởi tạo token nếu chưa có khi nạp trang
  useEffect(() => {
    if (!token && currentRole !== 'consumer') {
      switchRole(currentRole);
    }
  }, []);

  const getAuthHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  };

  const value = {
    currentRole,
    activeRoleConfig,
    token,
    currentUser,
    isSwitching,
    switchRole,
    getAuthHeaders,
    authFetch: apiFetch,
    apiFetch,
    canSplitMerge: activeRoleConfig.canSplitMerge,
    canOpenRecall: activeRoleConfig.canOpenRecall,
    isInspector: currentRole === 'inspector',
    isAdmin: ['system_admin', 'admin'].includes(currentRole),
    isConsumer: currentRole === 'consumer',
  };

  return <AuthRoleContext.Provider value={value}>{children}</AuthRoleContext.Provider>;
}

export function useAuthRole() {
  const ctx = useContext(AuthRoleContext);
  if (!ctx) {
    throw new Error('useAuthRole must be used within an AuthRoleProvider');
  }
  return ctx;
}
