import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardList,
  Package,
  BookOpen,
  Settings,
  LogOut,
  Shield,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { clsx } from 'clsx';

const navItems = [
  { to: '/dashboard',    icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/inspections',  icon: ClipboardList,   label: 'Inspections' },
  { to: '/products',     icon: Package,         label: 'Products' },
  { to: '/rules',        icon: BookOpen,        label: 'Rules' },
  { to: '/settings',     icon: Settings,        label: 'Settings' },
];

export function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-60 flex-shrink-0 flex flex-col h-screen glass border-r border-indigo-500/10">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-indigo-500/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Shield size={18} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white leading-tight">LM Inspect</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Legal Metrology</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx('sidebar-link', isActive && 'active')
            }
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="px-3 pb-4 space-y-2 border-t border-indigo-500/10 pt-3">
        {user && (
          <div className="px-3 py-2 rounded-lg bg-indigo-500/5 border border-indigo-500/10">
            <div className="text-xs font-semibold text-slate-300 truncate">{user.full_name}</div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] text-indigo-400 font-medium uppercase tracking-wider">
                {user.role}
              </span>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="sidebar-link w-full text-red-400 hover:text-red-300"
        >
          <LogOut size={17} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
