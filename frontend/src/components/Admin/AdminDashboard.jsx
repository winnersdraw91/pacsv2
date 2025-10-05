import { useState, useEffect, useContext } from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { AuthContext } from "../../App";
import { Button } from "../ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Input } from "../ui/input";
import { Building2, Users, FileText, Activity, LogOut, Plus, UserCheck, DollarSign } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Label } from "../ui/label";

const Sidebar = ({ logout }) => {
  return (
    <div className="w-64 bg-gradient-to-br from-slate-800 to-slate-900 text-white min-h-screen p-6 flex flex-col">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-teal-500 flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-bold text-lg">PACS System</h2>
            <p className="text-xs text-slate-400">Admin Portal</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-2">
        <Link to="/admin" data-testid="admin-dashboard-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <Activity className="w-5 h-5" />
            <span className="font-medium">Dashboard</span>
          </div>
        </Link>
        <Link to="/admin/centres" data-testid="centres-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <Building2 className="w-5 h-5" />
            <span className="font-medium">Centres</span>
          </div>
        </Link>
        <Link to="/admin/radiologists" data-testid="radiologists-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <UserCheck className="w-5 h-5" />
            <span className="font-medium">Radiologists</span>
          </div>
        </Link>
        <Link to="/admin/studies" data-testid="studies-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <FileText className="w-5 h-5" />
            <span className="font-medium">All Studies</span>
          </div>
        </Link>
      </nav>

      <Button
        onClick={logout}
        variant="outline"
        className="w-full justify-start gap-3 border-slate-700 text-white hover:bg-white/10"
        data-testid="logout-button"
      >
        <LogOut className="w-5 h-5" />
        Logout
      </Button>
    </div>
  );
};

const DashboardHome = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get("/dashboard/stats");
      setStats(response.data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6" data-testid="admin-dashboard-home">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Dashboard Overview</h1>
        <p className="text-slate-600">System-wide statistics and metrics</p>
      </div>

      <div className="dashboard-grid">
        <Card className="border-l-4 border-l-teal-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Total Centres</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_centres || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-teal-100 flex items-center justify-center">
                <Building2 className="w-7 h-7 text-teal-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-cyan-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Total Studies</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_studies || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-cyan-100 flex items-center justify-center">
                <FileText className="w-7 h-7 text-cyan-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-blue-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Radiologists</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_radiologists || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center">
                <Users className="w-7 h-7 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Pending Studies</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.pending_studies || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center">
                <Activity className="w-7 h-7 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const CentresManagement = () => {
  const [centres, setCentres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState({ name: "", address: "", phone: "", email: "" });

  useEffect(() => {
    fetchCentres();
  }, []);

  const fetchCentres = async () => {
    try {
      const response = await axios.get("/centres");
      setCentres(response.data);
    } catch (error) {
      console.error("Failed to fetch centres:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await axios.post("/centres", formData);
      setShowCreateDialog(false);
      setFormData({ name: "", address: "", phone: "", email: "" });
      fetchCentres();
    } catch (error) {
      console.error("Failed to create centre:", error);
      alert("Failed to create centre");
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6" data-testid="centres-management">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 mb-2">Diagnostic Centres</h1>
          <p className="text-slate-600">Manage all diagnostic centres</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button className="bg-teal-600 hover:bg-teal-700" data-testid="create-centre-button">
              <Plus className="w-5 h-5 mr-2" />
              Add Centre
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Centre</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <Label>Centre Name</Label>
                <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
              </div>
              <div>
                <Label>Address</Label>
                <Input value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} required />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} required />
              </div>
              <div>
                <Label>Email</Label>
                <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required />
              </div>
              <Button type="submit" className="w-full bg-teal-600 hover:bg-teal-700">Create Centre</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Centre Name</th>
                  <th>Address</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {centres.map((centre) => (
                  <tr key={centre.id}>
                    <td className="font-medium">{centre.name}</td>
                    <td>{centre.address}</td>
                    <td>{centre.phone}</td>
                    <td>{centre.email}</td>
                    <td>
                      <span className={`status-badge ${centre.is_active ? 'status-completed' : 'status-pending'}`}>
                        {centre.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const RadiologistsManagement = () => {
  const [radiologists, setRadiologists] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRadiologists();
  }, []);

  const fetchRadiologists = async () => {
    try {
      const response = await axios.get("/users?role=radiologist");
      setRadiologists(response.data);
    } catch (error) {
      console.error("Failed to fetch radiologists:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6" data-testid="radiologists-management">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Radiologists</h1>
        <p className="text-slate-600">Manage radiologists across all centres</p>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {radiologists.map((rad) => (
                  <tr key={rad.id}>
                    <td className="font-medium">{rad.name}</td>
                    <td>{rad.email}</td>
                    <td>{rad.phone || 'N/A'}</td>
                    <td>
                      <span className={`status-badge ${rad.is_active ? 'status-completed' : 'status-pending'}`}>
                        {rad.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const StudiesView = () => {
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStudies();
  }, []);

  const fetchStudies = async () => {
    try {
      const response = await axios.get("/studies");
      setStudies(response.data);
    } catch (error) {
      console.error("Failed to fetch studies:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">All Studies</h1>
        <p className="text-slate-600">View all DICOM studies across all centres</p>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Study ID</th>
                  <th>Patient Name</th>
                  <th>Modality</th>
                  <th>Age/Gender</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {studies.map((study) => (
                  <tr key={study.id}>
                    <td className="font-mono font-medium">{study.study_id}</td>
                    <td>{study.patient_name}</td>
                    <td><span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-sm font-medium">{study.modality}</span></td>
                    <td>{study.patient_age}Y / {study.patient_gender}</td>
                    <td>
                      <span className={`status-badge status-${study.status}`}>
                        {study.status}
                      </span>
                    </td>
                    <td>{new Date(study.uploaded_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default function AdminDashboard() {
  const { user, logout } = useContext(AuthContext);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar logout={logout} />
      <div className="flex-1 overflow-y-auto">
        <div className="p-8">
          <div className="mb-6">
            <p className="text-sm text-slate-600">Welcome back,</p>
            <h2 className="text-2xl font-bold text-slate-800">{user?.name}</h2>
          </div>

          <Routes>
            <Route path="/" element={<DashboardHome />} />
            <Route path="/centres" element={<CentresManagement />} />
            <Route path="/radiologists" element={<RadiologistsManagement />} />
            <Route path="/studies" element={<StudiesView />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}