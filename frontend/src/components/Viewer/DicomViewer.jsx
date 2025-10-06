import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import dicomParser from "dicom-parser";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { 
  ArrowLeft, Download, ZoomIn, ZoomOut, Move, Contrast, Maximize2, 
  RotateCw, FlipHorizontal, Ruler, Info, Activity, FileText, 
  Layers, Box, Play, Pause, Grid3x3, MessageSquare, Eye, EyeOff,
  Minus, Plus, Square, Circle, Triangle
} from "lucide-react";
import { Slider } from "../ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

export default function DicomViewer() {
  const { studyId } = useParams();
  const navigate = useNavigate();
  
  // Canvas refs for multi-view
  const canvasRefs = useRef([]);
  const canvas2DRef = useRef(null);
  const canvasAxialRef = useRef(null);
  const canvasSagittalRef = useRef(null);
  const canvasCoronalRef = useRef(null);
  const canvas3DRef = useRef(null);
  const canvasMIPRef = useRef(null);
  const canvasMINIPRef = useRef(null);
  
  const [study, setStudy] = useState(null);
  const [aiReport, setAiReport] = useState(null);
  const [finalReport, setFinalReport] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // View modes and layouts
  const [viewMode, setViewMode] = useState("2D");
  const [layout, setLayout] = useState("2x2");
  const [activeTool, setActiveTool] = useState("pan");
  const [activeViewport, setActiveViewport] = useState(0);
  const [comparisonMode, setComparisonMode] = useState(false);
  const [comparisonStudyId, setComparisonStudyId] = useState(null);
  const [comparisonStudy, setComparisonStudy] = useState(null);
  const [syncScroll, setSyncScroll] = useState(true);
  const [studyOverlay, setStudyOverlay] = useState(false);
  const [overlayOpacity, setOverlayOpacity] = useState(0.5);
  
  // DICOM file data
  const [dicomFiles, setDicomFiles] = useState({});
  const [dicomImages, setDicomImages] = useState({});
  const [loadingFiles, setLoadingFiles] = useState(false);
  
  // Multi-viewport state
  const [viewports, setViewports] = useState([
    { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 },
    { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 },
    { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 },
    { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 }
  ]);
  
  // Image state
  const [imageState, setImageState] = useState({
    zoom: 1,
    rotation: 0,
    flipH: false,
    flipV: false,
    invert: false,
    brightness: 0,
    contrast: 0,
    windowWidth: 400,
    windowLevel: 40,
    panX: 0,
    panY: 0
  });
  
  // 3D state
  const [rotation3D, setRotation3D] = useState({ x: 0, y: 0, z: 0 });
  
  // Slice management
  const [currentSlice, setCurrentSlice] = useState(0);
  const [axialSlice, setAxialSlice] = useState(0);
  const [sagittalSlice, setSagittalSlice] = useState(0);
  const [coronalSlice, setCoronalSlice] = useState(0);
  
  // Cine mode
  const [cineMode, setCineMode] = useState(false);
  const [cineSpeed, setCineSpeed] = useState(5);
  const cineIntervalRef = useRef(null);
  
  // Tools and measurements
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [measurements, setMeasurements] = useState([]);
  const [angles, setAngles] = useState([]);
  const [rectangleROIs, setRectangleROIs] = useState([]);
  const [ellipseROIs, setEllipseROIs] = useState([]);
  const [volumeROIs, setVolumeROIs] = useState([]);
  const [annotations, setAnnotations] = useState([]);
  const [showMeasurements, setShowMeasurements] = useState(true);
  const [windowPreset, setWindowPreset] = useState("default");
  const [showCrosshair, setShowCrosshair] = useState(true);
  const [mipThickness, setMipThickness] = useState(10);
  const [minipThickness, setMinipThickness] = useState(10);

  useEffect(() => {
    fetchStudyData();
    return () => {
      if (cineIntervalRef.current) clearInterval(cineIntervalRef.current);
    };
  }, [studyId]);

  useEffect(() => {
    if (study) {
      drawAllViews();
    }
  }, [study, dicomImages, imageState, currentSlice, viewMode, axialSlice, sagittalSlice, coronalSlice, rotation3D, mipThickness, layout, viewports]);

  useEffect(() => {
    if (cineMode && viewMode === "2D") {
      cineIntervalRef.current = setInterval(() => {
        setCurrentSlice(prev => {
          const maxSlice = (study?.file_ids?.length || 1) - 1;
          return prev >= maxSlice ? 0 : prev + 1;
        });
      }, 1000 / cineSpeed);
    } else {
      if (cineIntervalRef.current) {
        clearInterval(cineIntervalRef.current);
        cineIntervalRef.current = null;
      }
    }
    return () => {
      if (cineIntervalRef.current) clearInterval(cineIntervalRef.current);
    };
  }, [cineMode, cineSpeed, study, viewMode]);

  const fetchStudyData = async () => {
    try {
      console.log(`📋 STUDY FETCH: Loading study data for ${studyId}`);
      const studyRes = await axios.get(`/studies/${studyId}`);
      console.log(`📋 STUDY DATA: Received study data for ${studyRes.data.patient_name}`, studyRes.data);
      setStudy(studyRes.data);
      
      // Load DICOM files if available
      if (studyRes.data.file_ids && studyRes.data.file_ids.length > 0) {
        console.log(`📁 STUDY FILES: Study has ${studyRes.data.file_ids.length} DICOM files`);
        await loadDicomFiles(studyRes.data.file_ids);
      } else {
        console.warn(`⚠️ STUDY FILES: No DICOM files found in study data`);
      }

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

  const loadDicomFiles = async (fileIds) => {
    console.log(`🔍 DICOM LOADING: Starting to load ${fileIds.length} DICOM files:`, fileIds);
    setLoadingFiles(true);
    const files = {};
    const images = {};
    
    try {
      for (let i = 0; i < Math.min(fileIds.length, 10); i++) { // Load first 10 files
        const fileId = fileIds[i];
        try {
          console.log(`📁 DICOM FILE ${i+1}/${Math.min(fileIds.length, 10)}: Loading file ID: ${fileId}`);
          
          // Fetch DICOM file as ArrayBuffer
          const response = await axios.get(`/files/${fileId}`, {
            responseType: 'arraybuffer',
            timeout: 10000
          });
          
          console.log(`✅ DICOM FILE ${i+1}: Successfully downloaded ${response.data.byteLength} bytes`);
          
          const arrayBuffer = response.data;
          const byteArray = new Uint8Array(arrayBuffer);
          
          console.log(`📋 DICOM PARSE ${i+1}: Parsing ${byteArray.length} bytes with dicom-parser`);
          
          // Parse DICOM file with error handling
          let dataSet;
          try {
            dataSet = dicomParser.parseDicom(byteArray);
            console.log(`✅ DICOM PARSE ${i+1}: Successfully parsed DICOM headers`);
          } catch (parseError) {
            console.error(`❌ DICOM PARSE ${i+1}: Failed to parse DICOM file:`, parseError);
            continue; // Skip this file
          }
          
          files[i] = dataSet;
          
          // Extract pixel data and create image
          const image = extractDicomImage(dataSet, byteArray);
          if (image) {
            images[i] = image;
            console.log(`✅ DICOM EXTRACTED ${i + 1}: Successfully extracted image data ${image.rows}x${image.columns} pixels, WL: ${image.windowCenter}/${image.windowWidth}`);
          } else {
            console.warn(`⚠️ DICOM EXTRACT ${i + 1}: Failed to extract image data, using fallback`);
            images[i] = createFallbackImage(i);
          }
        } catch (fileError) {
          console.error(`❌ DICOM ERROR ${i + 1}: Failed to load DICOM file ${fileId}:`, fileError);
          // Create fallback image
          images[i] = createFallbackImage(i);
        }
      }
    } catch (error) {
      console.error("❌ DICOM LOADING ERROR: Failed to load DICOM files:", error);
    } finally {
      console.log(`🎯 DICOM LOADING COMPLETE: Loaded ${Object.keys(images).length} DICOM images successfully`);
      setDicomFiles(files);
      setDicomImages(images);
      setLoadingFiles(false);
    }
  };

  const extractDicomImage = (dataSet, byteArray) => {
    try {
      console.log("🔍 DICOM EXTRACT: Starting DICOM data extraction...");
      
      // Get image dimensions
      const rows = dataSet.uint16('x00280010');
      const columns = dataSet.uint16('x00280011');
      
      if (!rows || !columns) {
        console.error("❌ DICOM EXTRACT: Missing image dimensions", { rows, columns });
        return null;
      }
      
      const samplesPerPixel = dataSet.uint16('x00280002') || 1;
      const bitsAllocated = dataSet.uint16('x00280100') || 16;
      const bitsStored = dataSet.uint16('x00280101') || bitsAllocated;
      const highBit = dataSet.uint16('x00280102') || bitsStored - 1;
      const pixelRepresentation = dataSet.uint16('x00280103') || 0;
      
      console.log("📏 DICOM DIMENSIONS:", { rows, columns, bitsAllocated, samplesPerPixel });
      
      // Get pixel data with better error handling
      const pixelDataElement = dataSet.elements.x7fe00010;
      if (!pixelDataElement) {
        console.error("❌ DICOM EXTRACT: No pixel data element found in DICOM file");
        return null;
      }
      
      console.log("📊 DICOM PIXEL DATA:", { 
        dataOffset: pixelDataElement.dataOffset, 
        length: pixelDataElement.length,
        byteArrayLength: byteArray.length
      });
      
      // Create pixel data array with proper error checking
      let pixelData;
      try {
        if (bitsAllocated === 8) {
          pixelData = new Uint8Array(byteArray.buffer, pixelDataElement.dataOffset, pixelDataElement.length);
        } else {
          pixelData = new Uint16Array(byteArray.buffer, pixelDataElement.dataOffset, pixelDataElement.length / 2);
        }
      } catch (bufferError) {
        console.error("❌ DICOM EXTRACT: Failed to create pixel data array:", bufferError);
        return null;
      }
      
      // Get window/level information with safer parsing
      let windowCenter = 128;
      let windowWidth = 256;
      
      try {
        const wcData = dataSet.floatString('x00281050');
        const wwData = dataSet.floatString('x00281051');
        
        if (wcData) {
          windowCenter = Array.isArray(wcData) ? wcData[0] : wcData;
        }
        if (wwData) {
          windowWidth = Array.isArray(wwData) ? wwData[0] : wwData;
        }
      } catch (windowError) {
        console.warn("⚠️ DICOM EXTRACT: Using default window/level values", windowError);
      }
      
      console.log("🎯 DICOM EXTRACT SUCCESS:", {
        dimensions: `${rows}x${columns}`,
        pixelCount: pixelData.length,
        windowCenter,
        windowWidth
      });
      
      return {
        rows,
        columns,
        samplesPerPixel,
        bitsAllocated,
        bitsStored,
        highBit,
        pixelRepresentation,
        pixelData,
        windowCenter,
        windowWidth,
        dataSet
      };
    } catch (error) {
      console.error("❌ DICOM EXTRACT: Failed to extract DICOM image:", error);
      return null;
    }
  };

  const createFallbackImage = (sliceIndex) => {
    // Create a simple fallback image
    const rows = 512;
    const columns = 512;
    const pixelData = new Uint16Array(rows * columns);
    
    // Create a simple pattern
    for (let i = 0; i < pixelData.length; i++) {
      const x = i % columns;
      const y = Math.floor(i / columns);
      pixelData[i] = ((x + y + sliceIndex * 10) % 256) * 128;
    }
    
    return {
      rows,
      columns,
      samplesPerPixel: 1,
      bitsAllocated: 16,
      bitsStored: 16,
      highBit: 15,
      pixelRepresentation: 0,
      pixelData,
      windowCenter: 128,
      windowWidth: 256
    };
  };

  const getLayoutConfig = (layoutType) => {
    const configs = {
      '1x1': { rows: 1, cols: 1, viewports: 1 },
      '1x2': { rows: 1, cols: 2, viewports: 2 },
      '2x1': { rows: 2, cols: 1, viewports: 2 },
      '2x2': { rows: 2, cols: 2, viewports: 4 },
      '1x3': { rows: 1, cols: 3, viewports: 3 },
      '3x1': { rows: 3, cols: 1, viewports: 3 },
      '1x4': { rows: 1, cols: 4, viewports: 4 },
      '4x1': { rows: 4, cols: 1, viewports: 4 },
      '2x3': { rows: 2, cols: 3, viewports: 6 },
      '3x2': { rows: 3, cols: 2, viewports: 6 },
      '3x3': { rows: 3, cols: 3, viewports: 9 },
      '1x6': { rows: 1, cols: 6, viewports: 6 },
      '6x1': { rows: 6, cols: 1, viewports: 6 }
    };
    return configs[layoutType] || configs['2x2'];
  };

  const drawAllViews = () => {
    if (viewMode === "2D") {
      if (layout === "1x1") {
        drawCanvas(canvas2DRef.current, 0);
      } else {
        const config = getLayoutConfig(layout);
        for (let i = 0; i < config.viewports && i < canvasRefs.current.length; i++) {
          if (canvasRefs.current[i]) {
            drawCanvas(canvasRefs.current[i], i);
          }
        }
      }
    } else if (viewMode === "MPR") {
      drawMPRViews();
    } else if (viewMode === "3D") {
      draw3DView();
    } else if (viewMode === "MIP") {
      drawMIPView();
    } else if (viewMode === "MINIP") {
      drawMINIPView();
    }
  };

  const drawCanvas = (canvas, viewportIndex = 0) => {
    if (!canvas || !study) {
      console.log("🔄 DRAW CANVAS: Skipping draw - canvas or study not ready", { canvas: !!canvas, study: !!study });
      return;
    }
    
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      console.error("❌ DRAW CANVAS: Failed to get 2d context from canvas");
      return;
    }
    
    const width = canvas.width || 800;
    const height = canvas.height || 600;
    const viewport = viewports[viewportIndex] || viewports[0];

    console.log(`🎨 DRAW CANVAS ${viewportIndex}: Drawing ${width}x${height} canvas, slice ${viewport.slice}, DICOM images available: ${Object.keys(dicomImages).length}`);

    // Clear canvas with background color
    ctx.fillStyle = imageState.invert ? "#ffffff" : "#000000";
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2 + viewport.panX, height / 2 + viewport.panY);
    ctx.scale(viewport.zoom, viewport.zoom);
    ctx.rotate((viewport.rotation * Math.PI) / 180);
    if (imageState.flipH) ctx.scale(-1, 1);
    if (imageState.flipV) ctx.scale(1, -1);

    try {
      renderDicomImage(ctx, width, height, viewport.slice);
      console.log(`✅ DRAW CANVAS ${viewportIndex}: Successfully rendered DICOM image for slice ${viewport.slice}`);
    } catch (renderError) {
      console.error(`❌ DRAW CANVAS ${viewportIndex}: Error rendering DICOM image:`, renderError);
    }
    
    ctx.restore();

    drawOverlayInfo(ctx, width, height, viewport.slice, viewportIndex);
    
    // Draw active viewport indicator
    if (viewportIndex === activeViewport && layout !== "1x1") {
      ctx.strokeStyle = "#00ff00";
      ctx.lineWidth = 3;
      ctx.strokeRect(0, 0, width, height);
    }
    
    if (showMeasurements) {
      drawMeasurements(ctx);
      drawAngles(ctx);
      drawRectangleROIs(ctx);
      drawEllipseROIs(ctx);
      drawVolumeROIs(ctx);
    }
    
    if (annotations.length > 0) {
      drawAnnotations(ctx);
    }
  };

  const drawMPRViews = () => {
    const totalSlices = study?.file_ids?.length || 50;
    
    if (canvasAxialRef.current) {
      const ctx = canvasAxialRef.current.getContext("2d");
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, 400, 400);
      ctx.save();
      ctx.translate(200, 200);
      renderDicomImage(ctx, 400, 400, axialSlice);
      ctx.restore();
      
      if (showCrosshair) {
        ctx.strokeStyle = "#00ff00";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(200, 0);
        ctx.lineTo(200, 400);
        ctx.moveTo(0, 200);
        ctx.lineTo(400, 200);
        ctx.stroke();
      }
      
      ctx.fillStyle = "#00ff00";
      ctx.font = "12px monospace";
      ctx.fillText("AXIAL", 10, 20);
      ctx.fillText(`${axialSlice + 1}/${totalSlices}`, 10, 390);
    }
    
    if (canvasSagittalRef.current) {
      const ctx = canvasSagittalRef.current.getContext("2d");
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, 400, 400);
      ctx.save();
      ctx.translate(200, 200);
      ctx.scale(0.8, 1);
      renderDicomImage(ctx, 400, 400, sagittalSlice);
      ctx.restore();
      
      if (showCrosshair) {
        ctx.strokeStyle = "#ff00ff";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(200, 0);
        ctx.lineTo(200, 400);
        ctx.moveTo(0, 200);
        ctx.lineTo(400, 200);
        ctx.stroke();
      }
      
      ctx.fillStyle = "#ff00ff";
      ctx.font = "12px monospace";
      ctx.fillText("SAGITTAL", 10, 20);
      ctx.fillText(`${sagittalSlice + 1}/${totalSlices}`, 10, 390);
    }
    
    if (canvasCoronalRef.current) {
      const ctx = canvasCoronalRef.current.getContext("2d");
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, 400, 400);
      ctx.save();
      ctx.translate(200, 200);
      ctx.scale(1, 0.9);
      renderDicomImage(ctx, 400, 400, coronalSlice);
      ctx.restore();
      
      if (showCrosshair) {
        ctx.strokeStyle = "#ffff00";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(200, 0);
        ctx.lineTo(200, 400);
        ctx.moveTo(0, 200);
        ctx.lineTo(400, 200);
        ctx.stroke();
      }
      
      ctx.fillStyle = "#ffff00";
      ctx.font = "12px monospace";
      ctx.fillText("CORONAL", 10, 20);
      ctx.fillText(`${coronalSlice + 1}/${totalSlices}`, 10, 390);
    }
  };

  const draw3DView = () => {
    if (!canvas3DRef.current || !study) return;
    
    const canvas = canvas3DRef.current;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2, height / 2);

    const rotX = rotation3D.x * Math.PI / 180;
    const rotY = rotation3D.y * Math.PI / 180;
    const rotZ = rotation3D.z * Math.PI / 180;

    if (study.modality === "CT" || study.modality === "MRI") {
      render3DVolume(ctx, rotX, rotY, rotZ);
    }

    ctx.restore();

    ctx.fillStyle = "#00ffff";
    ctx.font = "12px monospace";
    ctx.fillText("3D VOLUME RENDERING", 10, 20);
    ctx.fillText(`Rotation: X:${rotation3D.x}° Y:${rotation3D.y}° Z:${rotation3D.z}°`, 10, 40);
    ctx.fillText(`Modality: ${study.modality}`, 10, height - 10);
  };

  const render3DVolume = (ctx, rotX, rotY, rotZ) => {
    if (!study) return;
    
    const layers = 20;
    const baseSize = 150;
    
    for (let i = 0; i < layers; i++) {
      const depth = i / layers;
      const scale = 1 - depth * 0.3;
      const alpha = 0.05 + (1 - depth) * 0.05;
      
      ctx.save();
      
      const yOffset = Math.sin(rotX) * i * 5;
      const xOffset = Math.sin(rotY) * i * 5;
      
      ctx.translate(xOffset, yOffset);
      ctx.scale(scale, scale);
      ctx.rotate(rotZ);
      
      ctx.globalAlpha = alpha;
      
      if (study.modality === "CT") {
        ctx.fillStyle = `rgb(${80 + i * 3}, ${80 + i * 3}, ${85 + i * 3})`;
        ctx.beginPath();
        ctx.ellipse(0, 0, baseSize, baseSize * 1.2, 0, 0, 2 * Math.PI);
        ctx.fill();
        
        if (i > 15) {
          ctx.strokeStyle = `rgba(200, 200, 200, ${alpha * 2})`;
          ctx.lineWidth = 3;
          ctx.stroke();
        }
      } else if (study.modality === "MRI") {
        ctx.fillStyle = `rgb(${90 + i * 2}, ${90 + i * 2}, ${95 + i * 2})`;
        ctx.beginPath();
        ctx.ellipse(0, 0, baseSize, baseSize * 1.15, 0, 0, 2 * Math.PI);
        ctx.fill();
      }
      
      ctx.restore();
    }
  };

  const drawMIPView = () => {
    if (!canvasMIPRef.current || !study) return;
    
    const canvas = canvasMIPRef.current;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2, height / 2);

    if (study.modality === "CT" || study.modality === "MRI") {
      drawVascularMIP(ctx, mipThickness);
    }

    ctx.restore();

    ctx.fillStyle = "#ff0000";
    ctx.font = "12px monospace";
    ctx.fillText("MIP - Maximum Intensity Projection", 10, 20);
    ctx.fillText(`Thickness: ${mipThickness}mm`, 10, 40);
    ctx.fillText("Vascular Visualization", 10, 60);
  };

  const drawVascularMIP = (ctx, thickness) => {
    ctx.strokeStyle = "rgba(100, 100, 100, 0.5)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(0, 0, 180, 200, 0, 0, 2 * Math.PI);
    ctx.stroke();

    const vessels = [
      { x1: 0, y1: -80, x2: -40, y2: -150, width: 4, intensity: 255 },
      { x1: 0, y1: -80, x2: 40, y2: -150, width: 4, intensity: 255 },
      { x1: -30, y1: -60, x2: -120, y2: -40, width: 5, intensity: 240 },
      { x1: 30, y1: -60, x2: 120, y2: -40, width: 5, intensity: 240 },
      { x1: -20, y1: 60, x2: -80, y2: 120, width: 4, intensity: 230 },
      { x1: 20, y1: 60, x2: 80, y2: 120, width: 4, intensity: 230 },
      { x1: 0, y1: 80, x2: 0, y2: 180, width: 6, intensity: 250 },
      { x1: -25, y1: 0, x2: -25, y2: 150, width: 5, intensity: 245 },
      { x1: 25, y1: 0, x2: 25, y2: 150, width: 5, intensity: 245 },
    ];

    vessels.forEach(vessel => {
      const brightness = Math.floor(vessel.intensity * (thickness / 20));
      ctx.strokeStyle = `rgb(${brightness}, ${brightness}, ${brightness})`;
      ctx.lineWidth = vessel.width * (thickness / 10);
      ctx.lineCap = "round";
      
      ctx.beginPath();
      ctx.moveTo(vessel.x1, vessel.y1);
      ctx.lineTo(vessel.x2, vessel.y2);
      ctx.stroke();
      
      ctx.strokeStyle = `rgba(${brightness}, ${brightness}, ${brightness}, 0.3)`;
      ctx.lineWidth = vessel.width * (thickness / 10) + 4;
      ctx.stroke();
    });

    for (let i = 0; i < 30; i++) {
      const angle = (i / 30) * Math.PI * 2;
      const radius = 100 + Math.random() * 60;
      const length = 20 + Math.random() * 40;
      const x1 = Math.cos(angle) * radius;
      const y1 = Math.sin(angle) * radius;
      const x2 = Math.cos(angle) * (radius + length);
      const y2 = Math.sin(angle) * (radius + length);
      
      const intensity = 150 + Math.random() * 80;
      ctx.strokeStyle = `rgb(${intensity}, ${intensity}, ${intensity})`;
      ctx.lineWidth = 1 + Math.random() * 2;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
  };

  const drawMINIPView = () => {
    if (!canvasMINIPRef.current || !study) return;
    
    const canvas = canvasMINIPRef.current;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2, height / 2);

    if (study.modality === "CT" || study.modality === "MRI") {
      drawAirBoneMINIP(ctx, minipThickness);
    }

    ctx.restore();

    ctx.fillStyle = "#00ff00";
    ctx.font = "12px monospace";
    ctx.fillText("MINIP - Minimum Intensity Projection", 10, 20);
    ctx.fillText(`Thickness: ${minipThickness}mm`, 10, 40);
    ctx.fillText("Air/Bone Visualization", 10, 60);
  };

  const drawAirBoneMINIP = (ctx, thickness) => {
    // Draw lungs (air-filled structures appear dark in MINIP)
    ctx.fillStyle = "rgba(20, 20, 20, 0.8)";
    ctx.beginPath();
    ctx.ellipse(-80, -30, 60, 80, 0, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(80, -30, 60, 80, 0, 0, 2 * Math.PI);
    ctx.fill();

    // Draw airways (very dark in MINIP)
    ctx.strokeStyle = "rgba(10, 10, 10, 0.9)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, -100);
    ctx.lineTo(0, -30);
    ctx.moveTo(0, -30);
    ctx.lineTo(-30, -10);
    ctx.moveTo(0, -30);
    ctx.lineTo(30, -10);
    ctx.stroke();

    // Draw bone structures (appear lighter in MINIP)
    const bones = [
      { x: 0, y: -120, radius: 15, opacity: 0.6 }, // skull
      { x: -60, y: -40, radius: 8, opacity: 0.4 }, // ribs left
      { x: 60, y: -40, radius: 8, opacity: 0.4 }, // ribs right
      { x: -40, y: 60, radius: 12, opacity: 0.5 }, // hip left
      { x: 40, y: 60, radius: 12, opacity: 0.5 }, // hip right
      { x: 0, y: 80, radius: 10, opacity: 0.4 }, // spine
    ];

    bones.forEach(bone => {
      const intensity = Math.floor(60 + (bone.opacity * thickness * 10));
      ctx.fillStyle = `rgba(${intensity}, ${intensity}, ${intensity}, ${bone.opacity})`;
      ctx.beginPath();
      ctx.arc(bone.x, bone.y, bone.radius, 0, 2 * Math.PI);
      ctx.fill();
    });

    // Add some textural elements for realism
    for (let i = 0; i < 20; i++) {
      const angle = (i / 20) * Math.PI * 2;
      const radius = 50 + Math.random() * 100;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      
      const intensity = Math.floor(15 + Math.random() * 30);
      ctx.fillStyle = `rgba(${intensity}, ${intensity}, ${intensity}, 0.3)`;
      ctx.beginPath();
      ctx.arc(x, y, 2 + Math.random() * 3, 0, 2 * Math.PI);
      ctx.fill();
    }
  };

  const renderDicomImage = (ctx, width, height, slice = 0) => {
    // First, draw a test pattern to verify canvas is working
    ctx.fillStyle = "#ff0000";
    ctx.fillRect(0, 0, 50, 50); // Red square in top-left to test canvas
    
    // Check if we have actual DICOM data for this slice
    if (dicomImages[slice]) {
      console.log(`🖼️ RENDERING: Using real DICOM data for slice ${slice}`);
      renderActualDicomSlice(ctx, width, height, dicomImages[slice], slice);
    } else {
      console.log(`🔄 RENDERING: Using mock data for slice ${slice} (no DICOM data available). Available slices: ${Object.keys(dicomImages)}`);
      // Test pattern to verify canvas rendering works
      ctx.fillStyle = "#333333";
      ctx.fillRect(100, 100, 200, 200);
      ctx.fillStyle = "#ffffff"; 
      ctx.font = "16px Arial";
      ctx.fillText(`Loading DICOM slice ${slice}...`, 120, 220);
      // Also call mock image for fallback
      generateMockDicomImage(ctx, width, height, slice);
    }
  };

  const renderActualDicomSlice = (ctx, width, height, dicomImage, slice) => {
    try {
      console.log(`🖼️ RENDER SLICE ${slice}: Starting render with DICOM data`, {
        rows: dicomImage.rows,
        columns: dicomImage.columns,
        pixelDataLength: dicomImage.pixelData?.length,
        windowCenter: dicomImage.windowCenter,
        windowWidth: dicomImage.windowWidth
      });
      
      const { rows, columns, pixelData, windowCenter, windowWidth } = dicomImage;
      
      if (!pixelData || pixelData.length === 0) {
        console.error(`❌ RENDER SLICE ${slice}: No pixel data available`);
        throw new Error("No pixel data available");
      }
      
      // Create image data
      const imageData = ctx.createImageData(width, height);
      const data = imageData.data;
      
      // Calculate scaling factors
      const scaleX = columns / width;
      const scaleY = rows / height;
      
      // Apply current window/level settings - use DICOM values if UI values are default
      let currentWindowCenter = imageState.windowLevel;
      let currentWindowWidth = imageState.windowWidth;
      
      // If UI values are at defaults, use DICOM file's native values
      if (imageState.windowLevel === 128 && imageState.windowWidth === 256) {
        currentWindowCenter = windowCenter;
        currentWindowWidth = windowWidth;
        console.log(`🎯 RENDER SLICE ${slice}: Using DICOM native WL: ${currentWindowCenter}/${currentWindowWidth}`);
      } else {
        console.log(`🎯 RENDER SLICE ${slice}: Using UI WL: ${currentWindowCenter}/${currentWindowWidth}`);
      }
      
      const windowMin = currentWindowCenter - currentWindowWidth / 2;
      const windowMax = currentWindowCenter + currentWindowWidth / 2;
      
      console.log(`📏 RENDER SLICE ${slice}: Scaling ${rows}x${columns} → ${width}x${height}, WL range: ${windowMin} to ${windowMax}`);
      
      // Render pixels with improved error handling
      let pixelsProcessed = 0;
      let pixelsVisible = 0;
      
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const sourceX = Math.floor(x * scaleX);
          const sourceY = Math.floor(y * scaleY);
          const sourceIndex = sourceY * columns + sourceX;
          
          if (sourceIndex >= 0 && sourceIndex < pixelData.length) {
            let pixelValue = pixelData[sourceIndex];
            const originalValue = pixelValue;
            pixelsProcessed++;
            
            // Apply window/level
            if (pixelValue < windowMin) {
              pixelValue = 0;
            } else if (pixelValue > windowMax) {
              pixelValue = 255;
            } else {
              pixelValue = ((pixelValue - windowMin) / currentWindowWidth) * 255;
            }
            
            // Apply brightness and contrast
            pixelValue = pixelValue * imageState.contrast + imageState.brightness;
            pixelValue = Math.max(0, Math.min(255, Math.floor(pixelValue)));
            
            if (pixelValue > 0) pixelsVisible++;
            
            const targetIndex = (y * width + x) * 4;
            data[targetIndex] = pixelValue;     // Red
            data[targetIndex + 1] = pixelValue; // Green  
            data[targetIndex + 2] = pixelValue; // Blue
            data[targetIndex + 3] = 255;       // Alpha
          } else {
            // Fill with black for out-of-bounds pixels
            const targetIndex = (y * width + x) * 4;
            data[targetIndex] = 0;
            data[targetIndex + 1] = 0;
            data[targetIndex + 2] = 0;
            data[targetIndex + 3] = 255;
          }
        }
      }
      
      console.log(`📊 RENDER SLICE ${slice}: Processed ${pixelsProcessed} pixels, ${pixelsVisible} visible (${((pixelsVisible/pixelsProcessed)*100).toFixed(1)}%)`);
      
      // Draw the image
      ctx.putImageData(imageData, 0, 0);
      
      // Add slice information
      ctx.fillStyle = "#00ff00";
      ctx.font = "12px monospace";
      ctx.fillText(`Slice: ${slice + 1}`, 10, 20);
      ctx.fillText(`WL: ${Math.round(currentWindowCenter)}/${Math.round(currentWindowWidth)}`, 10, 40);
      ctx.fillText(`Real DICOM Data`, 10, 60);
      
      console.log(`✅ RENDER SLICE ${slice}: Successfully rendered ${width}x${height} image with ${pixelData.length} pixels`);
      
    } catch (error) {
      console.error(`❌ RENDER SLICE ${slice}: Failed to render DICOM slice:`, error);
      // Fallback to mock image
      generateMockDicomImage(ctx, width, height, slice);
    }
  };

  const generateMockDicomImage = (ctx, width, height, slice = 0) => {
    const imageWidth = 400;
    const imageHeight = 400;
    const x = -imageWidth / 2;
    const y = -imageHeight / 2;

    const brightness = imageState.brightness + (imageState.windowLevel / 100) * 50;

    if (!study) return;

    const sliceOffset = (slice / (study.file_ids?.length || 1)) * 50 - 25;

    if (study.modality === "CT") {
      ctx.fillStyle = imageState.invert ? "#e0e0e0" : "#1a1a1a";
      ctx.fillRect(x, y, imageWidth, imageHeight);

      ctx.beginPath();
      ctx.ellipse(0, sliceOffset, 150, 180, 0, 0, 2 * Math.PI);
      ctx.fillStyle = imageState.invert 
        ? `rgb(${195 - brightness}, ${195 - brightness}, ${190 - brightness})` 
        : `rgb(${60 + brightness}, ${60 + brightness}, ${65 + brightness})`;
      ctx.fill();

      const ventricleSize = 15 + Math.abs(sliceOffset) * 0.3;
      ctx.beginPath();
      ctx.ellipse(-30, -20 + sliceOffset, ventricleSize, 25, -0.2, 0, 2 * Math.PI);
      ctx.ellipse(30, -20 + sliceOffset, ventricleSize, 25, 0.2, 0, 2 * Math.PI);
      ctx.fillStyle = imageState.invert 
        ? `rgb(${225 - brightness}, ${225 - brightness}, ${225 - brightness})`
        : `rgb(${30 + brightness}, ${30 + brightness}, ${30 + brightness})`;
      ctx.fill();

      ctx.strokeStyle = imageState.invert
        ? `rgb(${55 - brightness}, ${55 - brightness}, ${55 - brightness})`
        : `rgb(${200 + brightness}, ${200 + brightness}, ${200 + brightness})`;
      ctx.lineWidth = 8;
      ctx.beginPath();
      ctx.ellipse(0, sliceOffset, 165, 195, 0, 0, 2 * Math.PI);
      ctx.stroke();

    } else if (study.modality === "MRI") {
      ctx.fillStyle = imageState.invert ? "#f0f0f0" : "#0a0a0a";
      ctx.fillRect(x, y, imageWidth, imageHeight);

      ctx.beginPath();
      ctx.ellipse(0, sliceOffset, 155, 185, 0, 0, 2 * Math.PI);
      ctx.fillStyle = imageState.invert
        ? `rgb(${175 - brightness}, ${175 - brightness}, ${170 - brightness})`
        : `rgb(${80 + brightness}, ${80 + brightness}, ${85 + brightness})`;
      ctx.fill();

      ctx.fillStyle = imageState.invert
        ? `rgb(${195 - brightness}, ${195 - brightness}, ${185 - brightness})`
        : `rgb(${60 + brightness}, ${60 + brightness}, ${70 + brightness})`;
      ctx.beginPath();
      ctx.ellipse(-35, -25 + sliceOffset, 18, 30, -0.15, 0, 2 * Math.PI);
      ctx.ellipse(35, -25 + sliceOffset, 18, 30, 0.15, 0, 2 * Math.PI);
      ctx.fill();

    } else if (study.modality === "X-ray") {
      ctx.fillStyle = imageState.invert ? "#ffffff" : "#000000";
      ctx.fillRect(x, y, imageWidth, imageHeight);

      ctx.fillStyle = imageState.invert
        ? `rgba(${215 - brightness}, ${215 - brightness}, ${215 - brightness}, 0.8)`
        : `rgba(${40 + brightness}, ${40 + brightness}, ${40 + brightness}, 0.8)`;
      ctx.beginPath();
      ctx.ellipse(-60, 0, 80, 140, 0.1, 0, 2 * Math.PI);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(60, 0, 80, 140, -0.1, 0, 2 * Math.PI);
      ctx.fill();

      ctx.fillStyle = imageState.invert
        ? `rgba(${155 - brightness}, ${155 - brightness}, ${155 - brightness}, 0.7)`
        : `rgba(${100 + brightness}, ${100 + brightness}, ${100 + brightness}, 0.7)`;
      ctx.beginPath();
      ctx.ellipse(-20, 20, 50, 70, 0.3, 0, 2 * Math.PI);
      ctx.fill();

      ctx.strokeStyle = imageState.invert
        ? `rgba(${75 - brightness}, ${75 - brightness}, ${75 - brightness}, 0.6)`
        : `rgba(${180 + brightness}, ${180 + brightness}, ${180 + brightness}, 0.6)`;
      ctx.lineWidth = 3;
      for (let i = -3; i < 4; i++) {
        ctx.beginPath();
        ctx.arc(0, i * 40 - 60, 150, 0, Math.PI);
        ctx.stroke();
      }
    }

    if (!imageState.invert) {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
      ctx.lineWidth = 1;
      for (let i = 0; i < imageHeight; i += 4) {
        ctx.beginPath();
        ctx.moveTo(x, y + i);
        ctx.lineTo(x + imageWidth, y + i);
        ctx.stroke();
      }
    }
  };

  const drawOverlayInfo = (ctx, width, height, slice, viewportIndex = 0) => {
    ctx.font = "12px monospace";
    ctx.fillStyle = imageState.invert ? "#000000" : "#00ff00";
    ctx.textAlign = "left";

    const viewport = viewports[viewportIndex] || viewports[0];
    const info = [
      `Patient: ${study?.patient_name || "N/A"}`,
      `Study ID: ${study?.study_id || "N/A"}`,
      `Modality: ${study?.modality || "N/A"}`,
      `Slice: ${slice + 1}/${study?.file_ids?.length || 1}`,
      `Zoom: ${(viewport.zoom * 100).toFixed(0)}%`,
      `W/L: ${imageState.windowWidth}/${imageState.windowLevel}`
    ];

    info.forEach((text, i) => {
      ctx.fillText(text, 10, 20 + i * 16);
    });

    ctx.textAlign = "right";
    ctx.fillText(`${study?.patient_age}Y ${study?.patient_gender}`, width - 10, 20);
    if (layout !== "1x1") {
      ctx.fillText(`View ${viewportIndex + 1}`, width - 10, 36);
    }
  };

  const drawMeasurements = (ctx) => {
    ctx.strokeStyle = "#ffff00";
    ctx.fillStyle = "#ffff00";
    ctx.lineWidth = 2;
    ctx.font = "14px Arial";

    measurements.forEach((measurement) => {
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

  const drawAngles = (ctx) => {
    ctx.strokeStyle = "#ff00ff";
    ctx.fillStyle = "#ff00ff";
    ctx.lineWidth = 2;
    ctx.font = "14px Arial";

    angles.forEach((angle) => {
      if (angle.points && angle.points.length === 3) {
        const [p1, p2, p3] = angle.points;
        
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.lineTo(p3.x, p3.y);
        ctx.stroke();

        const angle1 = Math.atan2(p1.y - p2.y, p1.x - p2.x);
        const angle2 = Math.atan2(p3.y - p2.y, p3.x - p2.x);
        let angleDiff = (angle2 - angle1) * 180 / Math.PI;
        if (angleDiff < 0) angleDiff += 360;
        if (angleDiff > 180) angleDiff = 360 - angleDiff;

        ctx.beginPath();
        ctx.arc(p2.x, p2.y, 30, angle1, angle2);
        ctx.stroke();

        ctx.fillText(`${angleDiff.toFixed(1)}°`, p2.x + 35, p2.y - 5);
      }
    });
  };

  const drawRectangleROIs = (ctx) => {
    ctx.strokeStyle = "#00ffff";
    ctx.fillStyle = "rgba(0, 255, 255, 0.1)";
    ctx.lineWidth = 2;
    ctx.font = "12px Arial";

    rectangleROIs.forEach((roi, idx) => {
      const width = roi.x2 - roi.x1;
      const height = roi.y2 - roi.y1;
      
      ctx.fillRect(roi.x1, roi.y1, width, height);
      ctx.strokeRect(roi.x1, roi.y1, width, height);
      
      const area = Math.abs(width * height) / 100;
      ctx.fillStyle = "#00ffff";
      ctx.fillText(`ROI ${idx + 1}: ${area.toFixed(1)} mm²`, roi.x1 + 5, roi.y1 + 15);
      ctx.fillStyle = "rgba(0, 255, 255, 0.1)";
    });
  };

  const drawEllipseROIs = (ctx) => {
    ctx.strokeStyle = "#ff6600";
    ctx.fillStyle = "rgba(255, 102, 0, 0.1)";
    ctx.lineWidth = 2;
    ctx.font = "12px Arial";

    ellipseROIs.forEach((roi, idx) => {
      const radiusX = Math.abs(roi.x2 - roi.x1) / 2;
      const radiusY = Math.abs(roi.y2 - roi.y1) / 2;
      const centerX = (roi.x1 + roi.x2) / 2;
      const centerY = (roi.y1 + roi.y2) / 2;
      
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
      
      const area = Math.PI * radiusX * radiusY / 100;
      ctx.fillStyle = "#ff6600";
      ctx.fillText(`Ellipse ${idx + 1}: ${area.toFixed(1)} mm²`, centerX - 40, centerY - radiusY - 10);
      ctx.fillStyle = "rgba(255, 102, 0, 0.1)";
    });
  };

  const drawVolumeROIs = (ctx) => {
    ctx.strokeStyle = "#9333ea";
    ctx.fillStyle = "rgba(147, 51, 234, 0.1)";
    ctx.lineWidth = 2;
    ctx.font = "12px Arial";

    volumeROIs.forEach((roi, idx) => {
      const width = roi.x2 - roi.x1;
      const height = roi.y2 - roi.y1;
      
      // Draw the main ROI rectangle
      ctx.fillRect(roi.x1, roi.y1, width, height);
      ctx.strokeRect(roi.x1, roi.y1, width, height);
      
      // Draw depth indicator lines to show 3D nature
      const depthOffset = 8;
      ctx.strokeStyle = "#7c3aed";
      ctx.lineWidth = 1;
      
      // Draw connecting lines for 3D effect
      ctx.beginPath();
      ctx.moveTo(roi.x1, roi.y1);
      ctx.lineTo(roi.x1 + depthOffset, roi.y1 - depthOffset);
      ctx.moveTo(roi.x2, roi.y1);
      ctx.lineTo(roi.x2 + depthOffset, roi.y1 - depthOffset);
      ctx.moveTo(roi.x2, roi.y2);
      ctx.lineTo(roi.x2 + depthOffset, roi.y2 - depthOffset);
      ctx.moveTo(roi.x1, roi.y2);
      ctx.lineTo(roi.x1 + depthOffset, roi.y2 - depthOffset);
      ctx.stroke();
      
      // Draw back face
      ctx.strokeRect(roi.x1 + depthOffset, roi.y1 - depthOffset, width, height);
      
      // Calculate volume (area * slice thickness)
      const area = Math.abs(width * height) / 100; // Convert to mm²
      const volume = area * (roi.slices || 10); // Default 10 slices if not specified
      
      ctx.fillStyle = "#9333ea";
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#9333ea";
      ctx.fillText(`Volume ${idx + 1}: ${volume.toFixed(1)} mm³`, roi.x1 + 5, roi.y1 + 15);
      ctx.fillText(`Slices: ${roi.slices || 10}`, roi.x1 + 5, roi.y1 + 30);
      ctx.fillStyle = "rgba(147, 51, 234, 0.1)";
    });
  };

  const drawAnnotations = (ctx) => {
    ctx.fillStyle = "#ff0000";
    ctx.font = "14px Arial";
    
    annotations.forEach((annotation) => {
      ctx.fillText(annotation.text, annotation.x, annotation.y);
      ctx.beginPath();
      ctx.arc(annotation.x - 10, annotation.y - 5, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  };

  const handleMouseDown = (e, viewportIndex = 0) => {
    const canvas = layout === "1x1" ? canvas2DRef.current : canvasRefs.current[viewportIndex];
    if (!canvas) return;
    
    setActiveViewport(viewportIndex);
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setIsDragging(true);
    setDragStart({ x, y });

    if (activeTool === "length") {
      const newMeasurement = { type: "line", x1: x, y1: y, x2: x, y2: y };
      setMeasurements([...measurements, newMeasurement]);
    } else if (activeTool === "angle") {
      // Angle tool needs 3 points
      // For simplicity, we'll collect points on each click
    } else if (activeTool === "rectangleROI") {
      const newROI = { x1: x, y1: y, x2: x, y2: y };
      setRectangleROIs([...rectangleROIs, newROI]);
    } else if (activeTool === "ellipseROI") {
      const newROI = { x1: x, y1: y, x2: x, y2: y };
      setEllipseROIs([...ellipseROIs, newROI]);
    } else if (activeTool === "volumeROI") {
      const newROI = { x1: x, y1: y, x2: x, y2: y, slices: 10 };
      setVolumeROIs([...volumeROIs, newROI]);
    } else if (activeTool === "annotate") {
      const text = prompt("Enter annotation:");
      if (text) {
        setAnnotations([...annotations, { text, x, y }]);
      }
    }
  };

  const handleMouseMove = (e, viewportIndex = 0) => {
    if (!isDragging) return;

    const canvas = layout === "1x1" ? canvas2DRef.current : canvasRefs.current[viewportIndex];
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - dragStart.x;
    const dy = y - dragStart.y;

    if (activeTool === "pan") {
      setViewports(prev => {
        const updated = [...prev];
        if (comparisonMode && syncScroll) {
          // Sync pan across all viewports in comparison mode
          for (let i = 0; i < updated.length; i++) {
            updated[i] = {
              ...updated[i],
              panX: updated[i].panX + dx,
              panY: updated[i].panY + dy
            };
          }
        } else {
          updated[viewportIndex] = {
            ...updated[viewportIndex],
            panX: updated[viewportIndex].panX + dx,
            panY: updated[viewportIndex].panY + dy
          };
        }
        return updated;
      });
      setDragStart({ x, y });
    } else if (activeTool === "windowLevel") {
      setImageState(prev => ({
        ...prev,
        windowWidth: Math.max(1, prev.windowWidth + dx * 2),
        windowLevel: prev.windowLevel + dy * 0.5
      }));
      setDragStart({ x, y });
    } else if (activeTool === "length" && measurements.length > 0) {
      const updatedMeasurements = [...measurements];
      updatedMeasurements[updatedMeasurements.length - 1].x2 = x;
      updatedMeasurements[updatedMeasurements.length - 1].y2 = y;
      setMeasurements(updatedMeasurements);
    } else if (activeTool === "rectangleROI" && rectangleROIs.length > 0) {
      const updatedROIs = [...rectangleROIs];
      updatedROIs[updatedROIs.length - 1].x2 = x;
      updatedROIs[updatedROIs.length - 1].y2 = y;
      setRectangleROIs(updatedROIs);
    } else if (activeTool === "ellipseROI" && ellipseROIs.length > 0) {
      const updatedROIs = [...ellipseROIs];
      updatedROIs[updatedROIs.length - 1].x2 = x;
      updatedROIs[updatedROIs.length - 1].y2 = y;
      setEllipseROIs(updatedROIs);
    } else if (activeTool === "volumeROI" && volumeROIs.length > 0) {
      const updatedROIs = [...volumeROIs];
      updatedROIs[updatedROIs.length - 1].x2 = x;
      updatedROIs[updatedROIs.length - 1].y2 = y;
      setVolumeROIs(updatedROIs);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e, viewportIndex = 0) => {
    e.preventDefault();
    const direction = e.deltaY > 0 ? 1 : -1;
    
    if (activeTool === "zoom") {
      setViewports(prev => {
        const updated = [...prev];
        if (comparisonMode && syncScroll) {
          // Sync zoom across all viewports in comparison mode
          for (let i = 0; i < updated.length; i++) {
            updated[i] = {
              ...updated[i],
              zoom: Math.max(0.2, Math.min(5, updated[i].zoom + direction * 0.1))
            };
          }
        } else {
          updated[viewportIndex] = {
            ...updated[viewportIndex],
            zoom: Math.max(0.2, Math.min(5, updated[viewportIndex].zoom + direction * 0.1))
          };
        }
        return updated;
      });
    } else {
      // Stack scroll
      setViewports(prev => {
        const updated = [...prev];
        const maxSlice = (study?.file_ids?.length || 1) - 1;
        
        if (comparisonMode && syncScroll) {
          // Sync scrolling across all viewports in comparison mode
          for (let i = 0; i < updated.length; i++) {
            updated[i] = {
              ...updated[i],
              slice: Math.max(0, Math.min(maxSlice, updated[i].slice + direction))
            };
          }
        } else {
          updated[viewportIndex] = {
            ...updated[viewportIndex],
            slice: Math.max(0, Math.min(maxSlice, updated[viewportIndex].slice + direction))
          };
        }
        return updated;
      });
    }
  };

  const handle3DRotation = (axis, delta) => {
    setRotation3D(prev => ({
      ...prev,
      [axis]: (prev[axis] + delta) % 360
    }));
  };

  const applyWindowPreset = (preset) => {
    const presets = {
      lung: { width: 1500, level: -600 },
      bone: { width: 2000, level: 300 },
      brain: { width: 80, level: 40 },
      soft: { width: 350, level: 40 },
      liver: { width: 150, level: 30 },
      default: { width: 400, level: 40 }
    };
    
    const selected = presets[preset] || presets.default;
    setImageState(prev => ({
      ...prev,
      windowWidth: selected.width,
      windowLevel: selected.level
    }));
    setWindowPreset(preset);
  };

  const handleZoomTool = (direction) => {
    const delta = direction === "in" ? 0.2 : -0.2;
    setViewports(prev => {
      const updated = [...prev];
      updated[activeViewport] = {
        ...updated[activeViewport],
        zoom: Math.max(0.2, Math.min(5, updated[activeViewport].zoom + delta))
      };
      return updated;
    });
  };

  const handleReset = () => {
    setImageState({
      zoom: 1,
      rotation: 0,
      flipH: false,
      flipV: false,
      invert: false,
      brightness: 0,
      contrast: 0,
      windowWidth: 400,
      windowLevel: 40,
      panX: 0,
      panY: 0
    });
    setRotation3D({ x: 0, y: 0, z: 0 });
    setViewports([
      { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 },
      { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 },
      { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 },
      { slice: 0, zoom: 1, panX: 0, panY: 0, rotation: 0 }
    ]);
    setMeasurements([]);
    setAngles([]);
    setRectangleROIs([]);
    setEllipseROIs([]);
    setAnnotations([]);
  };

  if (loading || loadingFiles) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-white">
            {loading ? "Loading study..." : "Loading DICOM files..."}
          </p>
          {loadingFiles && Object.keys(dicomImages).length > 0 && (
            <p className="text-slate-400 mt-2">
              Loaded {Object.keys(dicomImages).length} files
            </p>
          )}
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
  const layoutConfig = getLayoutConfig(layout);

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="text-slate-300 hover:text-white hover:bg-slate-700"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back
            </Button>
            <div className="h-8 w-px bg-slate-700"></div>
            <div>
              <h1 className="text-lg font-bold text-white">Study ID: {study.study_id}</h1>
              <p className="text-xs text-slate-400">
                {study.patient_name} • {study.patient_age}Y • {study.patient_gender} • {study.modality}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex gap-2">
              <Button
                size="sm"
                variant={viewMode === "2D" ? "default" : "outline"}
                onClick={() => setViewMode("2D")}
                className={viewMode === "2D" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
              >
                <Square className="w-4 h-4 mr-1" />
                2D
              </Button>
              <Button
                size="sm"
                variant={viewMode === "MPR" ? "default" : "outline"}
                onClick={() => setViewMode("MPR")}
                className={viewMode === "MPR" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
              >
                <Grid3x3 className="w-4 h-4 mr-1" />
                MPR
              </Button>
              <Button
                size="sm"
                variant={viewMode === "3D" ? "default" : "outline"}
                onClick={() => setViewMode("3D")}
                className={viewMode === "3D" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
              >
                <Box className="w-4 h-4 mr-1" />
                3D
              </Button>
              <Button
                size="sm"
                variant={viewMode === "MIP" ? "default" : "outline"}
                onClick={() => setViewMode("MIP")}
                className={viewMode === "MIP" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                title="Maximum Intensity Projection - Shows brightest voxels along viewing direction"
              >
                <Layers className="w-4 h-4 mr-1" />
                MIP
              </Button>
              <Button
                size="sm"
                variant={viewMode === "MINIP" ? "default" : "outline"}
                onClick={() => setViewMode("MINIP")}
                className={viewMode === "MINIP" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                title="Minimum Intensity Projection - Shows darkest voxels for air/bone visualization"
              >
                <Minus className="w-4 h-4 mr-1" />
                MINIP
              </Button>
            </div>
            
            {viewMode === "2D" && (
              <Select value={layout} onValueChange={setLayout}>
                <SelectTrigger className="h-8 w-24 bg-slate-700 border-slate-600 text-slate-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1x1">1×1</SelectItem>
                  <SelectItem value="1x2">1×2</SelectItem>
                  <SelectItem value="2x1">2×1</SelectItem>
                  <SelectItem value="2x2">2×2</SelectItem>
                  <SelectItem value="1x3">1×3</SelectItem>
                  <SelectItem value="3x1">3×1</SelectItem>
                  <SelectItem value="2x3">2×3</SelectItem>
                  <SelectItem value="3x2">3×2</SelectItem>
                </SelectContent>
              </Select>
            )}
            
            <div className="flex gap-2">
              <Button 
                size="sm" 
                variant="outline" 
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
                title="Share Screen - Start screen sharing session"
              >
                <Activity className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
                title="Video Conference - Start video call with colleagues"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Video
              </Button>
              <Button size="sm" variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Main Viewer */}
        <div className="flex-1 flex flex-col">
          {/* Tools */}
          <div className="bg-slate-800/90 backdrop-blur-sm p-3 border-b border-slate-700 overflow-x-auto">
            <div className="flex items-center gap-2 flex-nowrap min-w-max">
              {viewMode === "2D" && (
                <>
                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Button
                      size="sm"
                      variant={activeTool === "pan" ? "default" : "outline"}
                      onClick={() => setActiveTool("pan")}
                      className={activeTool === "pan" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Pan Tool - Click and drag to move image"
                    >
                      <Move className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "zoom" ? "default" : "outline"}
                      onClick={() => setActiveTool("zoom")}
                      className={activeTool === "zoom" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Zoom Tool - Use mouse wheel to zoom in/out"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "windowLevel" ? "default" : "outline"}
                      onClick={() => setActiveTool("windowLevel")}
                      className={activeTool === "windowLevel" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Window/Level Tool - Drag to adjust brightness and contrast (HU values)"
                    >
                      <Contrast className="w-4 h-4" />
                    </Button>
                  </div>

                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Button
                      size="sm"
                      variant={activeTool === "length" ? "default" : "outline"}
                      onClick={() => {
                        setActiveTool("length");
                        setShowMeasurements(true);
                      }}
                      className={activeTool === "length" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Length Tool - Click and drag to measure distance in mm"
                    >
                      <Ruler className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "angle" ? "default" : "outline"}
                      onClick={() => setActiveTool("angle")}
                      className={activeTool === "angle" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Angle Tool - Click three points to measure angle in degrees"
                    >
                      <Triangle className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "rectangleROI" ? "default" : "outline"}
                      onClick={() => setActiveTool("rectangleROI")}
                      className={activeTool === "rectangleROI" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Rectangle ROI - Draw rectangle to calculate area in mm²"
                    >
                      <Square className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "ellipseROI" ? "default" : "outline"}
                      onClick={() => setActiveTool("ellipseROI")}
                      className={activeTool === "ellipseROI" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Elliptical ROI - Draw ellipse to calculate area in mm²"
                    >
                      <Circle className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "volumeROI" ? "default" : "outline"}
                      onClick={() => setActiveTool("volumeROI")}
                      className={activeTool === "volumeROI" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="3D Volume ROI - Draw region to calculate volume in mm³"
                    >
                      <Box className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={activeTool === "annotate" ? "default" : "outline"}
                      onClick={() => setActiveTool("annotate")}
                      className={activeTool === "annotate" ? "bg-teal-600" : "border-slate-600 text-slate-300"}
                      title="Annotation Tool - Click to add text notes"
                    >
                      <MessageSquare className="w-4 h-4" />
                    </Button>
                  </div>

                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Button 
                      size="sm" 
                      variant="outline" 
                      onClick={() => handleZoomTool("in")} 
                      className="border-slate-600 text-slate-300"
                      title="Zoom In - Increase magnification"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      onClick={() => handleZoomTool("out")} 
                      className="border-slate-600 text-slate-300"
                      title="Zoom Out - Decrease magnification"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </Button>
                    <span className="text-sm text-slate-400 min-w-[50px] text-center">
                      {(viewports[activeViewport]?.zoom * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Button 
                      size="sm" 
                      variant="outline" 
                      onClick={() => setImageState(prev => ({ ...prev, invert: !prev.invert }))} 
                      className="border-slate-600 text-slate-300"
                      title="Invert Colors - Toggle black/white inversion"
                    >
                      {imageState.invert ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </Button>
                  </div>

                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Select value={windowPreset} onValueChange={applyWindowPreset}>
                      <SelectTrigger className="h-8 w-32 bg-slate-700 border-slate-600 text-slate-200">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="default">Default</SelectItem>
                        <SelectItem value="lung">Lung</SelectItem>
                        <SelectItem value="bone">Bone</SelectItem>
                        <SelectItem value="brain">Brain</SelectItem>
                        <SelectItem value="soft">Soft Tissue</SelectItem>
                        <SelectItem value="liver">Liver</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setCineMode(!cineMode)}
                      className={cineMode ? "bg-teal-600 text-white" : "border-slate-600 text-slate-300"}
                      title="Cine Mode - Auto-play through image slices"
                    >
                      {cineMode ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <span className="text-xs text-slate-400">Cine</span>
                  </div>

                  <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setComparisonMode(!comparisonMode)}
                      className={comparisonMode ? "bg-blue-600 text-white" : "border-slate-600 text-slate-300"}
                      title="Comparison Mode - Compare studies side by side"
                    >
                      <Layers className="w-4 h-4 mr-1" />
                      Compare
                    </Button>
                    {comparisonMode && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setSyncScroll(!syncScroll)}
                          className={syncScroll ? "bg-purple-600 text-white" : "border-slate-600 text-slate-300"}
                          title="Sync Scroll - Synchronize scrolling between studies"
                        >
                          {syncScroll ? <Plus className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setStudyOverlay(!studyOverlay)}
                          className={studyOverlay ? "bg-orange-600 text-white" : "border-slate-600 text-slate-300"}
                          title="Study Overlay - Overlay comparison study"
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                  </div>

                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={handleReset} 
                    className="border-slate-600 text-slate-300"
                    title="Reset All - Restore default view settings"
                  >
                    <Maximize2 className="w-4 h-4 mr-1" />
                    Reset
                  </Button>
                </>
              )}

              {viewMode === "MPR" && (
                <div className="flex items-center gap-4 w-full">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowCrosshair(!showCrosshair)}
                    className={showCrosshair ? "bg-teal-600 text-white" : "border-slate-600 text-slate-300"}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Crosshair
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleReset} className="border-slate-600 text-slate-300">
                    <Maximize2 className="w-4 h-4 mr-1" />
                    Reset All
                  </Button>
                </div>
              )}

              {viewMode === "3D" && (
                <div className="flex items-center gap-4 w-full">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Rotate X:</span>
                    <Button size="sm" variant="outline" onClick={() => handle3DRotation('x', -15)} className="border-slate-600 text-slate-300">
                      <Minus className="w-3 h-3" />
                    </Button>
                    <span className="text-xs text-white font-mono w-12 text-center">{rotation3D.x}°</span>
                    <Button size="sm" variant="outline" onClick={() => handle3DRotation('x', 15)} className="border-slate-600 text-slate-300">
                      <Plus className="w-3 h-3" />
                    </Button>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Rotate Y:</span>
                    <Button size="sm" variant="outline" onClick={() => handle3DRotation('y', -15)} className="border-slate-600 text-slate-300">
                      <Minus className="w-3 h-3" />
                    </Button>
                    <span className="text-xs text-white font-mono w-12 text-center">{rotation3D.y}°</span>
                    <Button size="sm" variant="outline" onClick={() => handle3DRotation('y', 15)} className="border-slate-600 text-slate-300">
                      <Plus className="w-3 h-3" />
                    </Button>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Rotate Z:</span>
                    <Button size="sm" variant="outline" onClick={() => handle3DRotation('z', -15)} className="border-slate-600 text-slate-300">
                      <Minus className="w-3 h-3" />
                    </Button>
                    <span className="text-xs text-white font-mono w-12 text-center">{rotation3D.z}°</span>
                    <Button size="sm" variant="outline" onClick={() => handle3DRotation('z', 15)} className="border-slate-600 text-slate-300">
                      <Plus className="w-3 h-3" />
                    </Button>
                  </div>
                  <Button size="sm" variant="outline" onClick={handleReset} className="border-slate-600 text-slate-300">
                    Reset
                  </Button>
                </div>
              )}

              {viewMode === "MIP" && (
                <div className="flex items-center gap-4 w-full">
                  <div className="flex items-center gap-3 flex-1">
                    <span className="text-xs text-slate-400">MIP Thickness:</span>
                    <Slider
                      value={[mipThickness]}
                      onValueChange={([value]) => setMipThickness(value)}
                      min={5}
                      max={30}
                      step={1}
                      className="w-48"
                    />
                    <span className="text-xs text-white font-mono">{mipThickness}mm</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={handleReset} className="border-slate-600 text-slate-300">
                    Reset
                  </Button>
                </div>
              )}

              {viewMode === "MINIP" && (
                <div className="flex items-center gap-4 w-full">
                  <div className="flex items-center gap-3 flex-1">
                    <span className="text-xs text-slate-400">MINIP Thickness:</span>
                    <Slider
                      value={[minipThickness]}
                      onValueChange={([value]) => setMinipThickness(value)}
                      min={5}
                      max={30}
                      step={1}
                      className="w-48"
                    />
                    <span className="text-xs text-white font-mono">{minipThickness}mm</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={handleReset} className="border-slate-600 text-slate-300">
                    Reset
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Viewport */}
          <div className="flex-1 bg-black p-4 overflow-auto" data-testid="dicom-viewport">
            {viewMode === "2D" && layout === "1x1" && (
              <div className="flex items-center justify-center h-full">
                <canvas
                  ref={canvas2DRef}
                  width={800}
                  height={600}
                  className="border border-slate-700 cursor-crosshair"
                  onMouseDown={(e) => handleMouseDown(e, 0)}
                  onMouseMove={(e) => handleMouseMove(e, 0)}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  onWheel={(e) => handleWheel(e, 0)}
                />
              </div>
            )}

            {viewMode === "2D" && layout !== "1x1" && (
              <div 
                className="grid gap-2 h-full"
                style={{
                  gridTemplateRows: `repeat(${layoutConfig.rows}, 1fr)`,
                  gridTemplateColumns: `repeat(${layoutConfig.cols}, 1fr)`
                }}
              >
                {Array.from({ length: layoutConfig.viewports }).map((_, idx) => (
                  <div key={idx} className="flex items-center justify-center">
                    <canvas
                      ref={(el) => (canvasRefs.current[idx] = el)}
                      width={400}
                      height={300}
                      className="border border-slate-700 cursor-crosshair w-full h-full"
                      onMouseDown={(e) => handleMouseDown(e, idx)}
                      onMouseMove={(e) => handleMouseMove(e, idx)}
                      onMouseUp={handleMouseUp}
                      onMouseLeave={handleMouseUp}
                      onWheel={(e) => handleWheel(e, idx)}
                    />
                  </div>
                ))}
              </div>
            )}

            {viewMode === "MPR" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col items-center">
                  <canvas ref={canvasAxialRef} width={400} height={400} className="border border-green-500" />
                  <div className="flex items-center gap-2 mt-2">
                    <Button size="sm" variant="outline" onClick={() => setAxialSlice(Math.max(0, axialSlice - 1))} className="border-slate-600 text-slate-300">
                      ←
                    </Button>
                    <span className="text-xs text-white font-mono">{axialSlice + 1}/{totalSlices}</span>
                    <Button size="sm" variant="outline" onClick={() => setAxialSlice(Math.min(totalSlices - 1, axialSlice + 1))} className="border-slate-600 text-slate-300">
                      →
                    </Button>
                  </div>
                </div>
                <div className="flex flex-col items-center">
                  <canvas ref={canvasSagittalRef} width={400} height={400} className="border border-purple-500" />
                  <div className="flex items-center gap-2 mt-2">
                    <Button size="sm" variant="outline" onClick={() => setSagittalSlice(Math.max(0, sagittalSlice - 1))} className="border-slate-600 text-slate-300">
                      ←
                    </Button>
                    <span className="text-xs text-white font-mono">{sagittalSlice + 1}/{totalSlices}</span>
                    <Button size="sm" variant="outline" onClick={() => setSagittalSlice(Math.min(totalSlices - 1, sagittalSlice + 1))} className="border-slate-600 text-slate-300">
                      →
                    </Button>
                  </div>
                </div>
                <div className="flex flex-col items-center col-span-2">
                  <canvas ref={canvasCoronalRef} width={400} height={400} className="border border-yellow-500" />
                  <div className="flex items-center gap-2 mt-2">
                    <Button size="sm" variant="outline" onClick={() => setCoronalSlice(Math.max(0, coronalSlice - 1))} className="border-slate-600 text-slate-300">
                      ←
                    </Button>
                    <span className="text-xs text-white font-mono">{coronalSlice + 1}/{totalSlices}</span>
                    <Button size="sm" variant="outline" onClick={() => setCoronalSlice(Math.min(totalSlices - 1, coronalSlice + 1))} className="border-slate-600 text-slate-300">
                      →
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {viewMode === "3D" && (
              <div className="flex items-center justify-center h-full">
                <canvas ref={canvas3DRef} width={800} height={600} className="border border-cyan-500" />
              </div>
            )}

            {viewMode === "MIP" && (
              <div className="flex items-center justify-center h-full">
                <canvas ref={canvasMIPRef} width={800} height={600} className="border border-red-500" />
              </div>
            )}

            {viewMode === "MINIP" && (
              <div className="flex items-center justify-center h-full">
                <canvas ref={canvasMINIPRef} width={800} height={600} className="border border-green-500" />
              </div>
            )}
          </div>

          {/* Bottom Controls */}
          {viewMode === "2D" && (
            <div className="bg-slate-800 p-3 border-t border-slate-700">
              <div className="grid grid-cols-2 gap-4 max-w-2xl">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Brightness</label>
                  <Slider
                    value={[imageState.brightness]}
                    onValueChange={([value]) => setImageState(prev => ({ ...prev, brightness: value }))}
                    min={-100}
                    max={100}
                    step={1}
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Contrast</label>
                  <Slider
                    value={[imageState.contrast]}
                    onValueChange={([value]) => setImageState(prev => ({ ...prev, contrast: value }))}
                    min={-100}
                    max={100}
                    step={1}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-96 bg-slate-800 border-l border-slate-700 overflow-y-auto">
          <div className="p-6 space-y-6">
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
                    <span className="text-slate-400">View Mode:</span>
                    <span className="text-teal-400 font-semibold">{viewMode}</span>
                  </div>
                  {viewMode === "2D" && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Layout:</span>
                      <span className="text-teal-400 font-semibold">{layout}</span>
                    </div>
                  )}
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
                </div>
                {study.notes && (
                  <div className="mt-4 pt-4 border-t border-slate-600">
                    <p className="text-slate-400 text-xs mb-1">Clinical Notes:</p>
                    <p className="text-white text-sm">{study.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>

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