import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { ArrowLeft, Download, ZoomIn, ZoomOut, Move, Contrast, Maximize2, RotateCw, FlipHorizontal, Ruler, Info, Activity, FileText } from "lucide-react";
import { Slider } from "../ui/slider";

export default function DicomViewer() {
  const { studyId } = useParams();
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const [study, setStudy] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [finalReport, setFinalReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTool, setActiveTool] = useState("pan");
  const [imageState, setImageState] = useState({
    zoom: 1,
    rotation: 0,
    flipH: false,
    flipV: false,
    brightness: 0,
    contrast: 0,
    windowWidth: 400,
    windowLevel: 40,
    panX: 0,
    panY: 0
  });
  const [currentSlice, setCurrentSlice] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [showMeasurements, setShowMeasurements] = useState(false);
  const [measurements, setMeasurements] = useState([]);

  useEffect(() => {
    fetchStudyData();
  }, [studyId]);

  useEffect(() => {
    if (study) {
      drawDicomImage();
    }
  }, [study, imageState, currentSlice]);

  const fetchStudyData = async () => {
    try {
      const studyRes = await axios.get(`/studies/${studyId}`);
      setStudy(studyRes.data);

      try {
        const aiReportRes = await axios.get(`/studies/${studyId}/ai-report`);
        setAiReport(aiReportRes.data);
      } catch (err) {
        console.log("No AI report available");
      }

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

  const drawDicomImage = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);

    // Save context state
    ctx.save();

    // Apply transformations
    ctx.translate(width / 2 + imageState.panX, height / 2 + imageState.panY);
    ctx.scale(imageState.zoom, imageState.zoom);
    ctx.rotate((imageState.rotation * Math.PI) / 180);
    if (imageState.flipH) ctx.scale(-1, 1);
    if (imageState.flipV) ctx.scale(1, -1);

    // Generate mock medical image based on modality
    generateMockDicomImage(ctx, width, height);

    ctx.restore();

    // Draw overlay information
    drawOverlayInfo(ctx, width, height);

    // Draw measurements if active
    if (showMeasurements && measurements.length > 0) {
      drawMeasurements(ctx);
    }
  };

  const generateMockDicomImage = (ctx, width, height) => {
    const imageWidth = 400;
    const imageHeight = 400;
    const x = -imageWidth / 2;
    const y = -imageHeight / 2;

    // Apply window/level adjustments
    const brightness = imageState.brightness + (imageState.windowLevel / 100) * 50;
    const contrast = 1 + imageState.contrast / 100 + (imageState.windowWidth / 400);

    if (!study) return;

    // Generate different mock images based on modality
    if (study.modality === "CT") {
      // CT Brain scan simulation
      ctx.fillStyle = "#1a1a1a";
      ctx.fillRect(x, y, imageWidth, imageHeight);

      // Brain outline
      ctx.beginPath();
      ctx.ellipse(0, 0, 150, 180, 0, 0, 2 * Math.PI);
      ctx.fillStyle = `rgb(${60 + brightness}, ${60 + brightness}, ${65 + brightness})`;
      ctx.fill();

      // Ventricles
      ctx.beginPath();
      ctx.ellipse(-30, -20, 15, 25, -0.2, 0, 2 * Math.PI);
      ctx.ellipse(30, -20, 15, 25, 0.2, 0, 2 * Math.PI);
      ctx.fillStyle = `rgb(${30 + brightness}, ${30 + brightness}, ${30 + brightness})`;
      ctx.fill();

      // Gray/white matter distinction
      for (let i = 0; i < 30; i++) {
        const angle = (i / 30) * Math.PI * 2;
        const radius = 120 + Math.random() * 20;
        const px = Math.cos(angle) * radius;
        const py = Math.sin(angle) * radius;
        ctx.beginPath();
        ctx.arc(px, py, 8, 0, 2 * Math.PI);
        ctx.fillStyle = `rgba(${70 + brightness}, ${70 + brightness}, ${75 + brightness}, 0.3)`;
        ctx.fill();
      }

      // Skull
      ctx.strokeStyle = `rgb(${200 + brightness}, ${200 + brightness}, ${200 + brightness})`;
      ctx.lineWidth = 8;
      ctx.beginPath();
      ctx.ellipse(0, 0, 165, 195, 0, 0, 2 * Math.PI);
      ctx.stroke();

    } else if (study.modality === "MRI") {
      // MRI Brain simulation
      ctx.fillStyle = "#0a0a0a";
      ctx.fillRect(x, y, imageWidth, imageHeight);

      // High resolution brain
      ctx.beginPath();
      ctx.ellipse(0, 0, 155, 185, 0, 0, 2 * Math.PI);
      ctx.fillStyle = `rgb(${80 + brightness}, ${80 + brightness}, ${85 + brightness})`;
      ctx.fill();

      // Detailed structures
      ctx.fillStyle = `rgb(${60 + brightness}, ${60 + brightness}, ${70 + brightness})`;
      ctx.beginPath();
      ctx.ellipse(-35, -25, 18, 30, -0.15, 0, 2 * Math.PI);
      ctx.ellipse(35, -25, 18, 30, 0.15, 0, 2 * Math.PI);
      ctx.fill();

      // White matter tracts
      ctx.strokeStyle = `rgba(${100 + brightness}, ${100 + brightness}, ${110 + brightness}, 0.6)`;
      ctx.lineWidth = 2;
      for (let i = 0; i < 15; i++) {
        ctx.beginPath();
        ctx.moveTo(-50 + i * 7, -80);
        ctx.lineTo(-50 + i * 7, 80);
        ctx.stroke();
      }

    } else if (study.modality === "X-ray") {
      // Chest X-ray simulation
      ctx.fillStyle = "#000000";
      ctx.fillRect(x, y, imageWidth, imageHeight);

      // Lung fields
      ctx.fillStyle = `rgba(${40 + brightness}, ${40 + brightness}, ${40 + brightness}, 0.8)`;
      ctx.beginPath();
      ctx.ellipse(-60, 0, 80, 140, 0.1, 0, 2 * Math.PI);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(60, 0, 80, 140, -0.1, 0, 2 * Math.PI);
      ctx.fill();

      // Heart shadow
      ctx.fillStyle = `rgba(${100 + brightness}, ${100 + brightness}, ${100 + brightness}, 0.7)`;
      ctx.beginPath();
      ctx.ellipse(-20, 20, 50, 70, 0.3, 0, 2 * Math.PI);
      ctx.fill();

      // Ribs
      ctx.strokeStyle = `rgba(${180 + brightness}, ${180 + brightness}, ${180 + brightness}, 0.6)`;
      ctx.lineWidth = 3;
      for (let i = -3; i < 4; i++) {
        ctx.beginPath();
        ctx.arc(0, i * 40 - 60, 150, 0, Math.PI);
        ctx.stroke();
      }

      // Clavicles
      ctx.strokeStyle = `rgb(${200 + brightness}, ${200 + brightness}, ${200 + brightness})`;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(-80, -150, 40, 0.5, 1.5);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(80, -150, 40, 1.6, 2.6);
      ctx.stroke();

    } else {
      // Generic medical image
      ctx.fillStyle = "#1a1a1a";
      ctx.fillRect(x, y, imageWidth, imageHeight);
      
      const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, 180);
      gradient.addColorStop(0, `rgb(${80 + brightness}, ${80 + brightness}, ${85 + brightness})`);
      gradient.addColorStop(1, `rgb(${30 + brightness}, ${30 + brightness}, ${35 + brightness})`);
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.ellipse(0, 0, 160, 180, 0, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Add scan line effect
    ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
    ctx.lineWidth = 1;
    for (let i = 0; i < imageHeight; i += 4) {
      ctx.beginPath();
      ctx.moveTo(x, y + i);
      ctx.lineTo(x + imageWidth, y + i);
      ctx.stroke();
    }
  };

  const drawOverlayInfo = (ctx, width, height) => {
    ctx.font = "12px monospace";
    ctx.fillStyle = "#00ff00";
    ctx.textAlign = "left";

    const info = [
      `Patient: ${study?.patient_name || "N/A"}`,
      `Study ID: ${study?.study_id || "N/A"}`,
      `Modality: ${study?.modality || "N/A"}`,
      `Slice: ${currentSlice + 1}/${study?.file_ids?.length || 1}`,
      `Zoom: ${(imageState.zoom * 100).toFixed(0)}%`,
      `W/L: ${imageState.windowWidth}/${imageState.windowLevel}`
    ];

    info.forEach((text, i) => {
      ctx.fillText(text, 10, 20 + i * 16);
    });

    // Top right info
    ctx.textAlign = "right";
    ctx.fillText(`${study?.patient_age}Y ${study?.patient_gender}`, width - 10, 20);
    ctx.fillText(new Date(study?.uploaded_at).toLocaleDateString(), width - 10, 36);
  };

  const drawMeasurements = (ctx) => {
    ctx.strokeStyle = "#ffff00";
    ctx.fillStyle = "#ffff00";
    ctx.lineWidth = 2;
    ctx.font = "14px Arial";

    measurements.forEach((measurement, idx) => {
      if (measurement.type === "line") {
        ctx.beginPath();
        ctx.moveTo(measurement.x1, measurement.y1);
        ctx.lineTo(measurement.x2, measurement.y2);
        ctx.stroke();

        const distance = Math.sqrt(
          Math.pow(measurement.x2 - measurement.x1, 2) +
          Math.pow(measurement.y2 - measurement.y1, 2)
        );
        const midX = (measurement.x1 + measurement.x2) / 2;
        const midY = (measurement.y1 + measurement.y2) / 2;
        ctx.fillText(`${(distance / 10).toFixed(1)} mm`, midX + 5, midY - 5);
      }
    });
  };

  const handleMouseDown = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setIsDragging(true);
    setDragStart({ x, y });

    if (activeTool === "measure") {
      const newMeasurement = { type: "line", x1: x, y1: y, x2: x, y2: y };
      setMeasurements([...measurements, newMeasurement]);
    }
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - dragStart.x;
    const dy = y - dragStart.y;

    if (activeTool === "pan") {
      setImageState(prev => ({
        ...prev,
        panX: prev.panX + dx,
        panY: prev.panY + dy
      }));
      setDragStart({ x, y });
    } else if (activeTool === "window") {
      setImageState(prev => ({
        ...prev,
        windowWidth: Math.max(1, prev.windowWidth + dx * 2),
        windowLevel: prev.windowLevel + dy * 0.5
      }));
      setDragStart({ x, y });
    } else if (activeTool === "measure" && measurements.length > 0) {
      const updatedMeasurements = [...measurements];
      updatedMeasurements[updatedMeasurements.length - 1].x2 = x;
      updatedMeasurements[updatedMeasurements.length - 1].y2 = y;
      setMeasurements(updatedMeasurements);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoomIn = () => {
    setImageState(prev => ({ ...prev, zoom: Math.min(prev.zoom + 0.2, 5) }));
  };

  const handleZoomOut = () => {
    setImageState(prev => ({ ...prev, zoom: Math.max(prev.zoom - 0.2, 0.2) }));
  };

  const handleRotate = () => {
    setImageState(prev => ({ ...prev, rotation: (prev.rotation + 90) % 360 }));
  };

  const handleFlipH = () => {
    setImageState(prev => ({ ...prev, flipH: !prev.flipH }));
  };

  const handleReset = () => {
    setImageState({
      zoom: 1,
      rotation: 0,
      flipH: false,
      flipV: false,
      brightness: 0,
      contrast: 0,
      windowWidth: 400,
      windowLevel: 40,
      panX: 0,
      panY: 0
    });
    setMeasurements([]);
  };

  const handleSliceChange = (direction) => {
    const maxSlice = (study?.file_ids?.length || 1) - 1;
    if (direction === "next") {
      setCurrentSlice(prev => Math.min(prev + 1, maxSlice));
    } else {
      setCurrentSlice(prev => Math.max(prev - 1, 0));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-white">Loading study...</p>
        </div>
      </div>
    );
  }

  if (!study) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <p className="text-xl text-slate-300 mb-4">Study not found</p>
          <Button onClick={() => navigate(-1)} className="bg-teal-600 hover:bg-teal-700">Go Back</Button>
        </div>
      </div>
    );
  }

  const totalSlices = study?.file_ids?.length || 1;

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
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Viewer */}
        <div className="flex-1 flex flex-col">
          {/* Tools */}
          <div className="bg-slate-800/90 backdrop-blur-sm p-4 border-b border-slate-700">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                <Button
                  size="sm"
                  variant={activeTool === "pan" ? "default" : "outline"}
                  onClick={() => setActiveTool("pan")}
                  className={activeTool === "pan" ? "bg-teal-600 hover:bg-teal-700" : "border-slate-600 text-slate-300 hover:bg-slate-700"}
                  data-testid="pan-tool"
                >
                  <Move className="w-4 h-4 mr-1" />
                  Pan
                </Button>
                <Button
                  size="sm"
                  variant={activeTool === "window" ? "default" : "outline"}
                  onClick={() => setActiveTool("window")}
                  className={activeTool === "window" ? "bg-teal-600 hover:bg-teal-700" : "border-slate-600 text-slate-300 hover:bg-slate-700"}
                  data-testid="window-tool"
                >
                  <Contrast className="w-4 h-4 mr-1" />
                  W/L
                </Button>
                <Button
                  size="sm"
                  variant={activeTool === "measure" ? "default" : "outline"}
                  onClick={() => {
                    setActiveTool("measure");
                    setShowMeasurements(true);
                  }}
                  className={activeTool === "measure" ? "bg-teal-600 hover:bg-teal-700" : "border-slate-600 text-slate-300 hover:bg-slate-700"}
                  data-testid="measure-tool"
                >
                  <Ruler className="w-4 h-4 mr-1" />
                  Measure
                </Button>
              </div>

              <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleZoomIn}
                  className="border-slate-600 text-slate-300 hover:bg-slate-700"
                  data-testid="zoom-in"
                >
                  <ZoomIn className="w-4 h-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleZoomOut}
                  className="border-slate-600 text-slate-300 hover:bg-slate-700"
                  data-testid="zoom-out"
                >
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <span className="text-sm text-slate-400 min-w-[50px] text-center">
                  {(imageState.zoom * 100).toFixed(0)}%
                </span>
              </div>

              <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleRotate}
                  className="border-slate-600 text-slate-300 hover:bg-slate-700"
                  data-testid="rotate"
                >
                  <RotateCw className="w-4 h-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleFlipH}
                  className="border-slate-600 text-slate-300 hover:bg-slate-700"
                  data-testid="flip"
                >
                  <FlipHorizontal className="w-4 h-4" />
                </Button>
              </div>

              <Button
                size="sm"
                variant="outline"
                onClick={handleReset}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
                data-testid="reset"
              >
                <Maximize2 className="w-4 h-4 mr-1" />
                Reset
              </Button>

              <div className="ml-auto flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-400">Slice:</span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSliceChange("prev")}
                    disabled={currentSlice === 0}
                    className="border-slate-600 text-slate-300 hover:bg-slate-700 disabled:opacity-50"
                  >
                    ←
                  </Button>
                  <span className="text-sm text-white font-mono min-w-[80px] text-center">
                    {currentSlice + 1} / {totalSlices}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSliceChange("next")}
                    disabled={currentSlice === totalSlices - 1}
                    className="border-slate-600 text-slate-300 hover:bg-slate-700 disabled:opacity-50"
                  >
                    →
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Viewport */}
          <div className="flex-1 bg-black flex items-center justify-center p-4" data-testid="dicom-viewport">
            <canvas
              ref={canvasRef}
              width={800}
              height={600}
              className="border border-slate-700 cursor-crosshair"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            />
          </div>

          {/* Bottom Controls */}
          <div className="bg-slate-800 p-4 border-t border-slate-700">
            <div className="grid grid-cols-2 gap-6 max-w-2xl">
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Brightness</label>
                <Slider
                  value={[imageState.brightness]}
                  onValueChange={([value]) => setImageState(prev => ({ ...prev, brightness: value }))}
                  min={-100}
                  max={100}
                  step={1}
                  className="w-full"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Contrast</label>
                <Slider
                  value={[imageState.contrast]}
                  onValueChange={([value]) => setImageState(prev => ({ ...prev, contrast: value }))}
                  min={-100}
                  max={100}
                  step={1}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar - Reports */}
        <div className="w-96 bg-slate-800 border-l border-slate-700 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Study Info */}
            <Card className="bg-slate-700 border-slate-600">
              <CardContent className="pt-6">
                <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                  <Info className="w-5 h-5" />
                  Study Information
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Study ID:</span>
                    <span className="text-white font-mono">{study.study_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Modality:</span>
                    <span className="text-white font-semibold">{study.modality}</span>
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
                    <span className="text-slate-400">Images:</span>
                    <span className="text-white">{totalSlices} slices</span>
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
                    <Activity className="w-5 h-5" />
                    AI Analysis Report
                    <span className="text-xs px-2 py-1 bg-blue-700 rounded text-blue-100 ml-auto">
                      {(aiReport.confidence_score * 100).toFixed(1)}% confidence
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
                    <p className="text-blue-400 text-xs mt-2 pt-2 border-t border-blue-800">
                      Model: {aiReport.model_version}<br />
                      Generated: {new Date(aiReport.generated_at).toLocaleString()}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Final Report */}
            {finalReport && (
              <Card className="bg-emerald-950 border-emerald-800">
                <CardContent className="pt-6">
                  <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Final Radiologist Report
                  </h3>
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
                    <p className="text-emerald-400 text-xs mt-2 pt-2 border-t border-emerald-800">
                      Approved: {new Date(finalReport.approved_at).toLocaleString()}
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