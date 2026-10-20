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
    id: 'coop',
    name: 'HTX Sơ chế / Chế biến',
    code: 'COOP',
    icon: '🏭',
    color: 'from-blue-600 to-cyan-600',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    desc: 'Tiếp nhận nguyên liệu, Tách lô & Gộp lô sơ chế, đóng gói',
    orgName: 'HTX Sơ Chế Bảo Lộc',
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
    id: 'distributor',
    name: 'Nhà phân phối / Bán lẻ',
    code: 'DISTRIBUTOR',
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
  const [currentRole, setCurrentRole] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSwitching, setIsSwitching] = useState(false);
  const [authError, setAuthError] = useState(null);

  // Xóa sạch token cũ khỏi localStorage nếu còn sót lại từ phiên trước
  useEffect(() => {
    localStorage.removeItem('app_access_token');
    localStorage.removeItem('app_current_role');
    localStorage.removeItem('app_current_user');
  }, []);

  // Kiểm tra phiên đăng nhập hiện tại bằng cookie HttpOnly qua /api/v1/auth/me
  const checkSession = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/v1/auth/me', {
        method: 'GET',
        credentials: 'include',
      });
      if (res.ok) {
        const user = await res.json();
        setCurrentUser(user);
        setCurrentRole(user.role);
        setIsAuthenticated(true);
        setAuthError(null);
      } else {
        setCurrentUser(null);
        setCurrentRole(null);
        setIsAuthenticated(false);
      }
    } catch (err) {
      console.warn('Chưa đăng nhập hoặc không thể xác thực phiên:', err.message);
      setCurrentUser(null);
      setCurrentRole(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkSession();
  }, []);

  // Đăng nhập an toàn qua API /api/v1/auth/login sử dụng Cookie phiên HttpOnly
  const login = async (email, password) => {
    setAuthError(null);
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        setCurrentUser(data);
        setCurrentRole(data.role);
        setToken(data.access_token);
        setIsAuthenticated(true);
        setAuthError(null);
        return { success: true, data };
      }

      const errJson = await res.json().catch(() => ({}));
      const errorMsg = errJson.detail || 'Email hoặc mật khẩu không chính xác.';
      setAuthError(errorMsg);
      return { success: false, error: errorMsg, status: res.status };
    } catch (err) {
      const msg = `Lỗi kết nối máy chủ: ${err.message}`;
      setAuthError(msg);
      return { success: false, error: msg, status: 0 };
    }
  };

  // Đăng xuất: Gọi endpoint backend xóa cookie phiên và đặt lại state
  const logout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.warn('Lỗi khi gọi API đăng xuất:', err);
    } finally {
      setCurrentUser(null);
      setCurrentRole(null);
      setToken(null);
      setIsAuthenticated(false);
      setAuthError(null);
      localStorage.removeItem('app_access_token');
      localStorage.removeItem('app_current_role');
      localStorage.removeItem('app_current_user');
    }
  };

  // Cho phép chế độ khách xem công khai dành cho Người tiêu dùng
  const loginAsConsumer = () => {
    setCurrentRole('consumer');
    setCurrentUser({
      full_name: 'Người tiêu dùng đại chúng',
      email: 'consumer@public.vn',
      role: 'consumer',
    });
    setIsAuthenticated(true);
    setAuthError(null);
  };

  // Hàm chuyển đổi vai trò demo (chỉ hoạt động khi APP_ENV=development và bật cờ)
  const switchRole = async (newRole) => {
    setIsSwitching(true);

    if (newRole === 'consumer') {
      loginAsConsumer();
      setIsSwitching(false);
      return;
    }

    try {
      const res = await fetch(`/api/v1/auth/quick-role-token?role=${newRole}`, {
        method: 'POST',
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentRole(data.role);
        setCurrentUser(data);
        setToken(data.access_token);
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`Không thể chuyển vai trò demo: ${errData.detail || 'Tính năng bị vô hiệu hóa hoặc bị từ chối.'}`);
      }
    } catch (err) {
      console.error('Lỗi kết nối auth quick-role-token:', err);
      alert('Lỗi kết nối khi gọi chuyển vai trò demo.');
    } finally {
      setIsSwitching(false);
    }
  };

  const activeRoleConfig =
    ROLES_LIST.find((r) => r.id === currentRole) ||
    ROLES_LIST.find((r) => r.id === 'consumer') ||
    ROLES_LIST[0];

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
    isAuthenticated,
    isLoading,
    isSwitching,
    authError,
    login,
    logout,
    loginAsConsumer,
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
