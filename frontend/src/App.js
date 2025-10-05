import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import "@/App.css";
import Login from "./components/Auth/Login";
import AdminDashboard from "./components/Admin/AdminDashboard";
import CentreDashboard from "./components/Centre/CentreDashboard";
import TechnicianDashboard from "./components/Technician/TechnicianDashboard";
import RadiologistDashboard from "./components/Radiologist/RadiologistDashboard";
import DicomViewer from "./components/Viewer/DicomViewer";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Configure axios defaults
axios.defaults.baseURL = API;

// Auth context
export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get("/auth/me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      localStorage.removeItem("token");
      delete axios.defaults.headers.common["Authorization"];
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post("/auth/login", { email, password });
    const { access_token, user: userData } = response.data;
    localStorage.setItem("token", access_token);
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("token");
    delete axios.defaults.headers.common["Authorization"];
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-teal-600 border-solid mx-auto mb-4"></div>
          <p className="text-slate-600 text-lg font-medium">Loading PACS System...</p>
        </div>
      </div>
    );
  }

  const ProtectedRoute = ({ children, allowedRoles }) => {
    if (!user) {
      return <Navigate to="/login" replace />;
    }
    if (allowedRoles && !allowedRoles.includes(user.role)) {
      return <Navigate to="/" replace />;
    }
    return children;
  };

  const RoleBasedRedirect = () => {
    if (!user) return <Navigate to="/login" replace />;
    
    switch (user.role) {
      case "admin":
        return <Navigate to="/admin" replace />;
      case "centre":
        return <Navigate to="/centre" replace />;
      case "technician":
        return <Navigate to="/technician" replace />;
      case "radiologist":
        return <Navigate to="/radiologist" replace />;
      default:
        return <Navigate to="/login" replace />;
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={user ? <RoleBasedRedirect /> : <Login />} />
          
          <Route
            path="/admin/*"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/centre/*"
            element={
              <ProtectedRoute allowedRoles={["centre"]}>
                <CentreDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/technician/*"
            element={
              <ProtectedRoute allowedRoles={["technician"]}>
                <TechnicianDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/radiologist/*"
            element={
              <ProtectedRoute allowedRoles={["radiologist"]}>
                <RadiologistDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/viewer/:studyId"
            element={
              <ProtectedRoute>
                <DicomViewer />
              </ProtectedRoute>
            }
          />
          
          <Route path="/" element={<RoleBasedRedirect />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;