import { useState, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../../App";
import axios from "axios";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Activity, FileText, Eye, LogOut, CheckCircle, Edit, History } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Input } from "../ui/input";
import AdvancedSearch from "../Search/AdvancedSearch";

export default function RadiologistDashboard() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const [studies, setStudies] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedStudy, setSelectedStudy] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [showReportDialog, setShowReportDialog] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [existingReport, setExistingReport] = useState(null);
  const [showEditHistory, setShowEditHistory] = useState(false);
  const [reportData, setReportData] = useState({
    findings: "",
    diagnosis: "",
    recommendations: ""
  });
  const [allStudies, setAllStudies] = useState([]);

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
      setAllStudies(studiesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (searchParams) => {
    try {
      const response = await axios.post("/studies/search", searchParams);
      setStudies(response.data);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  const handleResetSearch = () => {
    setStudies(allStudies);
  };

  const handleAssignToMe = async (studyId) => {
    try {
      await axios.patch(`/studies/${studyId}/assign`);
      fetchData();
      alert("Study assigned to you successfully!");
    } catch (error) {
      console.error("Failed to assign study:", error);
      alert("Failed to assign study");
    }
  };

  const handleViewStudy = async (study) => {
    try {
      const aiReportRes = await axios.get(`/studies/${study.study_id}/ai-report`);
      setAiReport(aiReportRes.data);
      setSelectedStudy(study);
      setIsEditMode(false);
      setExistingReport(null);
      setReportData({
        findings: aiReportRes.data.findings,
        diagnosis: aiReportRes.data.preliminary_diagnosis,
        recommendations: ""
      });
      setShowReportDialog(true);
    } catch (error) {
      console.error("Failed to fetch AI report:", error);
      alert("AI report not available");
    }
  };

  const handleEditReport = async (study) => {
    try {
      const [aiReportRes, finalReportRes] = await Promise.all([
        axios.get(`/studies/${study.study_id}/ai-report`),
        axios.get(`/studies/${study.study_id}/final-report`)
      ]);
      
      setAiReport(aiReportRes.data);
      setExistingReport(finalReportRes.data);
      setSelectedStudy(study);
      setIsEditMode(true);
      setReportData({
        findings: finalReportRes.data.findings,
        diagnosis: finalReportRes.data.diagnosis,
        recommendations: finalReportRes.data.recommendations || ""
      });
      setShowReportDialog(true);
    } catch (error) {
      console.error("Failed to fetch reports:", error);
      alert("Failed to load report for editing");
    }
  };

  const handleSubmitReport = async (e) => {
    e.preventDefault();
    try {
      if (isEditMode) {
        await axios.put(`/studies/${selectedStudy.study_id}/final-report`, reportData);
        alert("Report updated successfully with edit history!");
      } else {
        await axios.post(`/studies/${selectedStudy.study_id}/final-report`, reportData);
        alert("Report submitted successfully!");
      }
      setShowReportDialog(false);
      fetchData();
    } catch (error) {
      console.error("Failed to submit report:", error);
      alert(isEditMode ? "Failed to update report" : "Failed to submit report");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="spinner"></div>
      </div>
    );
  }

  const pendingStudies = studies.filter(s => s.status === "pending");
  const myStudies = studies.filter(s => s.radiologist_id === user.id);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur">
                <Activity className="w-7 h-7" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Radiologist Portal</h1>
                <p className="text-indigo-100 text-sm">Welcome, {user?.name}</p>
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
        {/* Search */}
        <div className="mb-8">
          <AdvancedSearch onSearch={handleSearch} onReset={handleResetSearch} />
        </div>

        {/* Stats */}
        <div className="dashboard-grid mb-8">
          <Card className="border-l-4 border-l-indigo-500 shadow-md card-hover">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Assigned Studies</p>
                  <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.assigned_studies || 0}</h3>
                </div>
                <div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center">
                  <FileText className="w-7 h-7 text-indigo-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-emerald-500 shadow-md card-hover">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Completed Reports</p>
                  <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.completed_studies || 0}</h3>
                </div>
                <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center">
                  <CheckCircle className="w-7 h-7 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pending Studies */}
        <div className="mb-8">
          <div className="mb-4">
            <h2 className="text-2xl font-bold text-slate-800 mb-1">Pending Studies</h2>
            <p className="text-slate-600">Unassigned studies available for review</p>
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
                      <th>Uploaded</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingStudies.map((study) => (
                      <tr key={study.id}>
                        <td className="font-mono font-medium">{study.study_id}</td>
                        <td>{study.patient_name}</td>
                        <td>
                          <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-sm font-medium">
                            {study.modality}
                          </span>
                        </td>
                        <td>{study.patient_age}Y / {study.patient_gender}</td>
                        <td>{new Date(study.uploaded_at).toLocaleDateString()}</td>
                        <td>
                          <Button
                            size="sm"
                            onClick={() => handleAssignToMe(study.study_id)}
                            className="bg-indigo-600 hover:bg-indigo-700"
                            data-testid={`assign-study-${study.study_id}`}
                          >
                            Assign to Me
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {pendingStudies.length === 0 && (
                      <tr>
                        <td colSpan="6" className="text-center py-8 text-slate-500">
                          No pending studies available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* My Studies */}
        <div>
          <div className="mb-4">
            <h2 className="text-2xl font-bold text-slate-800 mb-1">My Studies</h2>
            <p className="text-slate-600">Studies assigned to you</p>
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
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {myStudies.map((study) => (
                      <tr key={study.id}>
                        <td className="font-mono font-medium">{study.study_id}</td>
                        <td>{study.patient_name}</td>
                        <td>
                          <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-sm font-medium">
                            {study.modality}
                          </span>
                        </td>
                        <td>
                          <span className={`status-badge status-${study.status}`}>
                            {study.status}
                          </span>
                        </td>
                        <td>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate(`/viewer/${study.study_id}`)}
                              data-testid={`view-study-${study.study_id}`}
                              title="View DICOM Images"
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              View
                            </Button>
                            {study.status === "completed" ? (
                              <Button
                                size="sm"
                                onClick={() => handleEditReport(study)}
                                className="bg-blue-600 hover:bg-blue-700"
                                data-testid={`edit-report-${study.study_id}`}
                                title="Edit Final Report"
                              >
                                <Edit className="w-4 h-4 mr-1" />
                                Edit Report
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                onClick={() => handleViewStudy(study)}
                                className="bg-emerald-600 hover:bg-emerald-700"
                                data-testid={`create-report-${study.study_id}`}
                                title="Create Final Report"
                              >
                                Create Report
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {myStudies.length === 0 && (
                      <tr>
                        <td colSpan="5" className="text-center py-8 text-slate-500">
                          No studies assigned to you
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Report Dialog */}
        <Dialog open={showReportDialog} onOpenChange={setShowReportDialog}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center justify-between">
                <span>{isEditMode ? "Edit" : "Create"} Final Report - {selectedStudy?.study_id}</span>
                {isEditMode && existingReport?.edit_history?.length > 0 && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowEditHistory(!showEditHistory)}
                    title="View Edit History"
                  >
                    <History className="w-4 h-4 mr-2" />
                    History ({existingReport.edit_history.length})
                  </Button>
                )}
              </DialogTitle>
            </DialogHeader>
            
            {showEditHistory && existingReport?.edit_history && (
              <div className="mb-4 p-4 bg-slate-50 border border-slate-200 rounded-lg max-h-48 overflow-y-auto">
                <h4 className="font-semibold text-sm mb-3 text-slate-700">Edit History</h4>
                <div className="space-y-3">
                  {existingReport.edit_history.map((entry, idx) => (
                    <div key={idx} className="text-xs border-l-2 border-blue-400 pl-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-slate-700">{entry.radiologist_name}</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-slate-500">{new Date(entry.edited_at).toLocaleString()}</span>
                      </div>
                      <p className="text-slate-600 italic">Previous findings: {entry.previous_findings?.substring(0, 100)}...</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {aiReport && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  AI-Generated Preliminary Report
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-blue-800">Model:</span>
                    <span className="text-blue-700 ml-2">{aiReport.model_version}</span>
                  </div>
                  <div>
                    <span className="font-medium text-blue-800">Confidence:</span>
                    <span className="text-blue-700 ml-2">{(aiReport.confidence_score * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmitReport} className="space-y-4">
              <div>
                <Label>Findings *</Label>
                <Textarea
                  value={reportData.findings}
                  onChange={(e) => setReportData({ ...reportData, findings: e.target.value })}
                  required
                  rows={6}
                  placeholder="Enter detailed findings..."
                  className="resize-none"
                />
              </div>

              <div>
                <Label>Diagnosis *</Label>
                <Textarea
                  value={reportData.diagnosis}
                  onChange={(e) => setReportData({ ...reportData, diagnosis: e.target.value })}
                  required
                  rows={4}
                  placeholder="Enter diagnosis..."
                  className="resize-none"
                />
              </div>

              <div>
                <Label>Recommendations</Label>
                <Textarea
                  value={reportData.recommendations}
                  onChange={(e) => setReportData({ ...reportData, recommendations: e.target.value })}
                  rows={3}
                  placeholder="Enter recommendations (optional)..."
                  className="resize-none"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setShowReportDialog(false)} className="flex-1">
                  Cancel
                </Button>
                <Button type="submit" className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                  {isEditMode ? "Update Report" : "Submit Final Report"}
                </Button>
              </div>
              
              {isEditMode && existingReport && (
                <div className="mt-4 pt-4 border-t border-slate-200">
                  <p className="text-xs text-slate-500">
                    Original report by: {existingReport.radiologist_id} on {new Date(existingReport.approved_at).toLocaleString()}
                    {existingReport.last_edited_at && (
                      <><br />Last edited: {new Date(existingReport.last_edited_at).toLocaleString()}</>
                    )}
                  </p>
                </div>
              )}
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}