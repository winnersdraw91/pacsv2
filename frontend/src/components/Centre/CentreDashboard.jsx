import { useState, useEffect, useContext } from "react";
import { AuthContext } from "../../App";
import axios from "axios";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Activity, FileText, Users, LogOut } from "lucide-react";

export default function CentreDashboard() {
  const { user, logout } = useContext(AuthContext);
  const [studies, setStudies] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [studiesRes, statsRes] = await Promise.all([
        axios.get("/studies"),
        axios.get("/dashboard/stats")
      ]);
      setStudies(studiesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur">
                <Activity className="w-7 h-7" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Centre Portal</h1>
                <p className="text-cyan-100 text-sm">Welcome, {user?.name}</p>
              </div>
            </div>
            <Button
              onClick={logout}
              variant="outline"
              className="border-white/30 text-white hover:bg-white/10"
              data-testid="logout-button"
            >
              <LogOut className="w-5 h-5 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Stats */}
        <div className="dashboard-grid mb-8">
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

          <Card className="border-l-4 border-l-emerald-500 shadow-md card-hover">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Completed Studies</p>
                  <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.completed_studies || 0}</h3>
                </div>
                <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center">
                  <Users className="w-7 h-7 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Studies */}
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-slate-800 mb-1">Studies Overview</h2>
          <p className="text-slate-600">View and manage all studies from your centre</p>
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
                      <td>
                        <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-sm font-medium">
                          {study.modality}
                        </span>
                      </td>
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
    </div>
  );
}