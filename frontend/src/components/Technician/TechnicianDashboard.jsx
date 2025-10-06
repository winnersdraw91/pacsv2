import { useState, useEffect, useContext } from "react";
import { AuthContext } from "../../App";
import axios from "axios";
import { Button } from "../ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Activity, Upload, FileText, LogOut } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import AdvancedSearch from "../Search/AdvancedSearch";

export default function TechnicianDashboard() {
  const { user, logout } = useContext(AuthContext);
  const [studies, setStudies] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [formData, setFormData] = useState({
    patient_name: "",
    patient_age: "",
    patient_gender: "Male",
    modality: "CT",
    notes: ""
  });
  const [files, setFiles] = useState([]);

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

  const handleFileSelection = async (selectedFiles) => {
    setFiles(selectedFiles);
    
    // Extract metadata from the first DICOM file
    if (selectedFiles.length > 0 && selectedFiles[0].name.toLowerCase().endsWith('.dcm')) {
      try {
        const metadataFormData = new FormData();
        metadataFormData.append('file', selectedFiles[0]);
        
        const response = await axios.post('/files/extract-metadata', metadataFormData);
        const metadata = response.data;
        
        // Auto-fill form with DICOM metadata
        setFormData(prev => ({
          ...prev,
          patient_name: metadata.patient_name || prev.patient_name,
          patient_age: metadata.calculated_age || metadata.patient_age || prev.patient_age,
          patient_gender: metadata.patient_gender === 'M' ? 'Male' : 
                          metadata.patient_gender === 'F' ? 'Female' : 
                          metadata.patient_gender === 'O' ? 'Other' : prev.patient_gender,
          modality: metadata.modality || prev.modality,
          notes: metadata.study_description || prev.notes
        }));
        
        alert(`DICOM metadata extracted! Patient: ${metadata.patient_name || 'N/A'}, Modality: ${metadata.modality || 'N/A'}`);
      } catch (error) {
        console.error("Failed to extract metadata:", error);
        // Continue without metadata extraction
      }
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      alert("Please select at least one DICOM file");
      return;
    }

    setUploading(true);
    try {
      const uploadFormData = new FormData();
      uploadFormData.append("patient_name", formData.patient_name);
      uploadFormData.append("patient_age", formData.patient_age);
      uploadFormData.append("patient_gender", formData.patient_gender);
      uploadFormData.append("modality", formData.modality);
      if (formData.notes) uploadFormData.append("notes", formData.notes);
      
      for (let file of files) {
        uploadFormData.append("files", file);
      }

      await axios.post("/studies/upload", uploadFormData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setShowUploadDialog(false);
      setFormData({ patient_name: "", patient_age: "", patient_gender: "Male", modality: "CT", notes: "" });
      setFiles([]);
      fetchData();
      alert("Study uploaded successfully!");
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Failed to upload study");
    } finally {
      setUploading(false);
    }
  };

  const handleMarkAsDraft = async (studyId) => {
    if (!confirm("Mark this study as draft? This will remove it from the active workflow.")) {
      return;
    }

    try {
      await axios.patch(`/studies/${studyId}`, {
        is_draft: true,
        status: 'draft'
      });
      
      setStudies(prev => prev.map(study => 
        study.id === studyId 
          ? { ...study, is_draft: true, status: 'draft' }
          : study
      ));
      
      alert("Study marked as draft successfully!");
    } catch (error) {
      console.error("Failed to mark as draft:", error);
      alert("Failed to mark study as draft");
    }
  };

  const handleRequestDelete = async (studyId) => {
    if (!confirm("Request deletion for this study? This will require admin approval.")) {
      return;
    }

    try {
      await axios.patch(`/studies/${studyId}`, {
        delete_requested: true,
        delete_requested_at: new Date().toISOString(),
        delete_requested_by: user.id
      });
      
      setStudies(prev => prev.map(study => 
        study.id === studyId 
          ? { 
              ...study, 
              delete_requested: true,
              delete_requested_at: new Date().toISOString(),
              delete_requested_by: user.id
            }
          : study
      ));
      
      alert("Deletion request submitted successfully! Admin approval required.");
    } catch (error) {
      console.error("Failed to request deletion:", error);
      alert("Failed to submit deletion request");
    }
  };

  const handleSearch = async (searchParams) => {
    try {
      const response = await axios.post("/studies/search", searchParams);
      setStudies(response.data);
    } catch (error) {
      console.error("Search failed:", error);
      alert("Search failed");
    }
  };

  const handleSearchReset = () => {
    fetchData();
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
      <div className="bg-gradient-to-r from-teal-600 to-cyan-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur">
                <Activity className="w-7 h-7" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Technician Portal</h1>
                <p className="text-teal-100 text-sm">Welcome, {user?.name}</p>
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
          <Card className="border-l-4 border-l-teal-500 shadow-md card-hover">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Uploaded Studies</p>
                  <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.uploaded_studies || 0}</h3>
                </div>
                <div className="w-14 h-14 rounded-full bg-teal-100 flex items-center justify-center">
                  <FileText className="w-7 h-7 text-teal-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search Section */}
        <div className="mb-6">
          <AdvancedSearch onSearch={handleSearch} onReset={handleSearchReset} />
        </div>

        {/* Upload Section */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-slate-800 mb-1">DICOM Studies</h2>
            <p className="text-slate-600">Upload and manage patient studies</p>
          </div>
          <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
            <DialogTrigger asChild>
              <Button className="bg-teal-600 hover:bg-teal-700 shadow-lg" data-testid="upload-study-button">
                <Upload className="w-5 h-5 mr-2" />
                Upload Study
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Upload DICOM Study</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleUpload} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Patient Name *</Label>
                    <Input
                      value={formData.patient_name}
                      onChange={(e) => setFormData({ ...formData, patient_name: e.target.value })}
                      required
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <Label>Age *</Label>
                    <Input
                      type="number"
                      value={formData.patient_age}
                      onChange={(e) => setFormData({ ...formData, patient_age: e.target.value })}
                      required
                      placeholder="35"
                    />
                  </div>
                  <div>
                    <Label>Gender *</Label>
                    <Select value={formData.patient_gender} onValueChange={(val) => setFormData({ ...formData, patient_gender: val })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Male">Male</SelectItem>
                        <SelectItem value="Female">Female</SelectItem>
                        <SelectItem value="Other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Modality *</Label>
                    <Select value={formData.modality} onValueChange={(val) => setFormData({ ...formData, modality: val })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CT">CT Scan</SelectItem>
                        <SelectItem value="MRI">MRI</SelectItem>
                        <SelectItem value="X-ray">X-ray</SelectItem>
                        <SelectItem value="Ultrasound">Ultrasound</SelectItem>
                        <SelectItem value="PET">PET Scan</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label>Clinical Notes</Label>
                  <textarea
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                    rows="3"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Enter any relevant clinical notes..."
                  />
                </div>
                <div>
                  <Label>DICOM Files *</Label>
                  <Input
                    type="file"
                    multiple
                    accept=".dcm,.dicom,image/*"
                    onChange={(e) => setFiles(Array.from(e.target.files))}
                    required
                  />
                  {files.length > 0 && (
                    <p className="text-sm text-slate-600 mt-2">{files.length} file(s) selected</p>
                  )}
                </div>
                <Button
                  type="submit"
                  disabled={uploading}
                  className="w-full bg-teal-600 hover:bg-teal-700"
                >
                  {uploading ? "Uploading..." : "Upload Study"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Studies Table */}
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
                    <th>Actions</th>
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
                      <td>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => window.open(`/viewer/${study.id}`, '_blank')}
                            className="text-blue-600 border-blue-200 hover:bg-blue-50"
                            title="View DICOM Study"
                          >
                            <FileText className="w-4 h-4" />
                          </Button>
                          {!study.is_draft && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleMarkAsDraft(study.id)}
                              className="text-yellow-600 border-yellow-200 hover:bg-yellow-50"
                              title="Mark as Draft"
                            >
                              Draft
                            </Button>
                          )}
                          {!study.delete_requested && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRequestDelete(study.id)}
                              className="text-red-600 border-red-200 hover:bg-red-50"
                              title="Request Deletion"
                            >
                              Delete
                            </Button>
                          )}
                          {study.delete_requested && (
                            <span className="text-xs text-red-500 font-medium">
                              Delete Pending
                            </span>
                          )}
                        </div>
                      </td>
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