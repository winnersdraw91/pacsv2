import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { ArrowLeft, Download, ZoomIn, ZoomOut, Move, Contrast, Maximize2, RotateCw, FlipHorizontal, Ruler, Info } from "lucide-react";

export default function DicomViewer() {
  const { studyId } = useParams();
  const navigate = useNavigate();
  const [study, setStudy] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [finalReport, setFinalReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTool, setActiveTool] = useState("pan");

  useEffect(() => {
    fetchStudyData();
  }, [studyId]);

  const fetchStudyData = async () => {
    try {
      const studyRes = await axios.get(`/studies/${studyId}`);
      setStudy(studyRes.data);

      // Fetch AI report
      try {
        const aiReportRes = await axios.get(`/studies/${studyId}/ai-report`);
        setAiReport(aiReportRes.data);
      } catch (err) {
        console.log("No AI report available");
      }

      // Fetch final report if exists
      try {
        const finalReportRes = await axios.get(`/studies/${studyId}/final-report`);
        setFinalReport(finalReportRes.data);
      } catch (err) {
        console.log("No final report available");
      }
    } catch (error) {
      console.error("Failed to fetch study:", error);
      alert("Failed to load study");
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

  if (!study) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <p className="text-xl text-slate-600 mb-4">Study not found</p>
          <Button onClick={() => navigate(-1)}>Go Back</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="text-slate-300 hover:text-white hover:bg-slate-700"
              data-testid="back-button"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back
            </Button>
            <div className="h-8 w-px bg-slate-700"></div>
            <div>
              <h1 className="text-xl font-bold text-white">Study ID: {study.study_id}</h1>
              <p className="text-sm text-slate-400">
                {study.patient_name} • {study.patient_age}Y • {study.patient_gender} • {study.modality}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Viewer */}
        <div className="flex-1 flex flex-col">
          {/* Tools */}
          <div className="bg-slate-800/80 backdrop-blur-sm p-4 border-b border-slate-700">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={activeTool === "pan" ? "default" : "outline"}
                onClick={() => setActiveTool("pan")}
                className={activeTool === "pan" ? "bg-teal-600" : "border-slate-600 text-slate-300 hover:bg-slate-700"}
              >
                <Move className="w-4 h-4 mr-2" />
                Pan
              </Button>
              <Button
                size="sm"
                variant={activeTool === "zoom" ? "default" : "outline"}
                onClick={() => setActiveTool("zoom")}
                className={activeTool === "zoom" ? "bg-teal-600" : "border-slate-600 text-slate-300 hover:bg-slate-700"}
              >
                <ZoomIn className="w-4 h-4 mr-2" />
                Zoom
              </Button>
              <Button
                size="sm"
                variant={activeTool === "window" ? "default" : "outline"}
                onClick={() => setActiveTool("window")}
                className={activeTool === "window" ? "bg-teal-600" : "border-slate-600 text-slate-300 hover:bg-slate-700"}
              >
                <Contrast className="w-4 h-4 mr-2" />
                Window/Level
              </Button>
            </div>
          </div>

          {/* Viewport */}
          <div className="flex-1 bg-black flex items-center justify-center p-8" data-testid="dicom-viewport">
            <div className="text-center">
              <div className="w-64 h-64 border-4 border-dashed border-slate-700 rounded-lg flex items-center justify-center mb-4">
                <div className="text-slate-500">
                  <p className="text-sm mb-2">DICOM Viewer Placeholder</p>
                  <p className="text-xs">Cornerstone.js integration would render medical images here</p>
                  <p className="text-xs mt-4 font-mono">Files: {study.file_ids.length}</p>
                </div>
              </div>
              <p className="text-slate-400 text-sm">
                In production, this would display the DICOM images with full viewport controls
              </p>
            </div>
          </div>
        </div>

        {/* Sidebar - Reports */}
        <div className="w-96 bg-slate-800 border-l border-slate-700 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Study Info */}
            <Card className="bg-slate-700 border-slate-600">
              <CardContent className="pt-6">
                <h3 className="font-semibold text-white mb-3">Study Information</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Study ID:</span>
                    <span className="text-white font-mono">{study.study_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Modality:</span>
                    <span className="text-white">{study.modality}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Status:</span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      study.status === 'completed' ? 'bg-emerald-600' :
                      study.status === 'assigned' ? 'bg-blue-600' : 'bg-amber-600'
                    } text-white`}>
                      {study.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Uploaded:</span>
                    <span className="text-white">{new Date(study.uploaded_at).toLocaleDateString()}</span>
                  </div>
                </div>
                {study.notes && (
                  <div className="mt-4 pt-4 border-t border-slate-600">
                    <p className="text-slate-400 text-xs mb-1">Clinical Notes:</p>
                    <p className="text-white text-sm">{study.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* AI Report */}
            {aiReport && (
              <Card className="bg-blue-950 border-blue-800">
                <CardContent className="pt-6">
                  <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                    AI Report
                    <span className="text-xs px-2 py-1 bg-blue-700 rounded text-blue-100">
                      {(aiReport.confidence_score * 100).toFixed(1)}%
                    </span>
                  </h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="text-blue-300 font-medium mb-1">Findings:</p>
                      <p className="text-blue-100 text-xs leading-relaxed">{aiReport.findings}</p>
                    </div>
                    <div>
                      <p className="text-blue-300 font-medium mb-1">Preliminary Diagnosis:</p>
                      <p className="text-blue-100 text-xs leading-relaxed">{aiReport.preliminary_diagnosis}</p>
                    </div>
                    <p className="text-blue-400 text-xs mt-2">Model: {aiReport.model_version}</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Final Report */}
            {finalReport && (
              <Card className="bg-emerald-950 border-emerald-800">
                <CardContent className="pt-6">
                  <h3 className="font-semibold text-white mb-3">Final Report</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="text-emerald-300 font-medium mb-1">Findings:</p>
                      <p className="text-emerald-100 text-xs leading-relaxed">{finalReport.findings}</p>
                    </div>
                    <div>
                      <p className="text-emerald-300 font-medium mb-1">Diagnosis:</p>
                      <p className="text-emerald-100 text-xs leading-relaxed">{finalReport.diagnosis}</p>
                    </div>
                    {finalReport.recommendations && (
                      <div>
                        <p className="text-emerald-300 font-medium mb-1">Recommendations:</p>
                        <p className="text-emerald-100 text-xs leading-relaxed">{finalReport.recommendations}</p>
                      </div>
                    )}
                    <p className="text-emerald-400 text-xs mt-2">
                      Approved: {new Date(finalReport.approved_at).toLocaleDateString()}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}