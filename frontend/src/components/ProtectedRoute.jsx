import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ role }) {
  const { isAuthenticated, role: currentRole } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />
  if (role && currentRole?.toLowerCase() !== role.toLowerCase()) return <Navigate to="/" replace />
  return <Outlet />
}
