import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import dicomParser from 'dicom-parser';
import { 
  Play, Pause, SkipBack, SkipForward, ZoomIn, ZoomOut, RotateCw, 
  Maximize2, Move, MousePointer, Ruler, Triangle, Square, Circle,
  Eye, EyeOff, Settings, Download, ArrowLeft, Grid3x3, Layers,
  FlipHorizontal, FlipVertical, RefreshCw, Info, Search
} from 'lucide-react';

export default function AdvancedDicomViewer() {
  const { studyId } = useParams();
  const navigate = useNavigate();
  
  // Core state
  const [study, setStudy] = useState(null);
  const [dicomFiles, setDicomFiles] = useState([]);
  const [currentSlice, setCurrentSlice] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Canvas refs
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  
  // Viewport state
  const [viewport, setViewport] = useState({
    zoom: 1,
    panX: 0,
    panY: 0,
    rotation: 0,
    flipH: false,
    flipV: false,
    invert: false
  });
  
  // Image state
  const [imageState, setImageState] = useState({
    windowCenter: 128,
    windowWidth: 256,
    brightness: 0,
    contrast: 1
  });
  
  // Tools state
  const [activeTool, setActiveTool] = useState('windowLevel');
  const [measurements, setMeasurements] = useState([]);
  const [annotations, setAnnotations] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(5);
  
  // UI state
  const [showInfo, setShowInfo] = useState(true);
  const [showTools, setShowTools] = useState(true);
  const [showMeasurements, setShowMeasurements] = useState(true);
  
  // Mouse interaction state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  
  // Cine playback
  const playIntervalRef = useRef(null);

  // Load study and DICOM files
  useEffect(() => {
    loadStudy();
  }, [studyId]);

  // Cine playback effect
  useEffect(() => {
    if (isPlaying && dicomFiles.length > 1) {
      playIntervalRef.current = setInterval(() => {
        setCurrentSlice(prev => (prev + 1) % dicomFiles.length);
      }, 1000 / playSpeed);
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
    }

    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, [isPlaying, playSpeed, dicomFiles.length]);

  // Render when slice or viewport changes
  useEffect(() => {
    renderDicomImage();
  }, [currentSlice, viewport, imageState, dicomFiles]);

  const loadStudy = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🔍 Loading study:', studyId);
      
      // Get study data
      const studyResponse = await axios.get(`/studies/${studyId}`);
      const studyData = studyResponse.data;
      setStudy(studyData);
      
      console.log('📋 Study loaded:', studyData.patient_name);
      
      if (!studyData.file_ids || studyData.file_ids.length === 0) {
        throw new Error('No DICOM files found in study');
      }
      
      // Load DICOM files
      await loadDicomFiles(studyData.file_ids);
      
    } catch (err) {
      console.error('❌ Error loading study:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDicomFiles = async (fileIds) => {
    console.log(`📁 Loading ${fileIds.length} DICOM files`);
    const loadedFiles = [];
    
    for (let i = 0; i < Math.min(fileIds.length, 50); i++) { // Load first 50 files
      try {
        console.log(`Loading file ${i + 1}/${Math.min(fileIds.length, 50)}`);
        
        const response = await axios.get(`/files/${fileIds[i]}`, {
          responseType: 'arraybuffer',
          timeout: 30000
        });
        
        const byteArray = new Uint8Array(response.data);
        const dataSet = dicomParser.parseDicom(byteArray);
        
        // Extract image data
        const dicomImage = extractDicomImageData(dataSet, byteArray);
        
        if (dicomImage) {
          loadedFiles.push({
            ...dicomImage,
            fileId: fileIds[i],
            sliceIndex: i
          });
          
          // Set default window/level from first image
          if (i === 0) {
            setImageState(prev => ({
              ...prev,
              windowCenter: dicomImage.windowCenter,
              windowWidth: dicomImage.windowWidth
            }));
          }
        }
        
      } catch (fileError) {
        console.error(`Failed to load file ${i}:`, fileError);
      }
    }
    
    console.log(`✅ Loaded ${loadedFiles.length} DICOM files`);
    setDicomFiles(loadedFiles);
  };

  const extractDicomImageData = (dataSet, byteArray) => {
    try {
      // Get image dimensions
      const rows = dataSet.uint16('x00280010');
      const columns = dataSet.uint16('x00280011');
      
      if (!rows || !columns) {
        console.warn('Missing image dimensions');
        return null;
      }
      
      // Get pixel data
      const pixelDataElement = dataSet.elements.x7fe00010;
      if (!pixelDataElement) {
        console.warn('No pixel data found');
        return null;
      }
      
      const bitsAllocated = dataSet.uint16('x00280100') || 16;
      let pixelData;
      
      if (bitsAllocated === 8) {
        pixelData = new Uint8Array(byteArray.buffer, pixelDataElement.dataOffset, pixelDataElement.length);
      } else {
        pixelData = new Uint16Array(byteArray.buffer, pixelDataElement.dataOffset, pixelDataElement.length / 2);
      }
      
      // Get window/level
      let windowCenter = 128;
      let windowWidth = 256;
      
      try {
        const wcData = dataSet.floatString('x00281050');
        const wwData = dataSet.floatString('x00281051');
        if (wcData) windowCenter = Array.isArray(wcData) ? wcData[0] : wcData;
        if (wwData) windowWidth = Array.isArray(wwData) ? wwData[0] : wwData;
      } catch (e) {
        // Use defaults
      }
      
      // Get additional metadata
      const metadata = {
        patientName: dataSet.string('x00100010') || '',
        studyDate: dataSet.string('x00080020') || '',
        modality: dataSet.string('x00080060') || '',
        sliceLocation: dataSet.floatString('x00201041') || 0,
        sliceThickness: dataSet.floatString('x00180050') || 1,
        pixelSpacing: dataSet.string('x00280030') || '1\\1'
      };
      
      return {
        rows,
        columns,
        pixelData,
        windowCenter,
        windowWidth,
        bitsAllocated,
        metadata
      };
      
    } catch (error) {
      console.error('Error extracting DICOM data:', error);
      return null;
    }
  };

  const renderDicomImage = useCallback(() => {
    const canvas = canvasRef.current;
    const overlayCanvas = overlayCanvasRef.current;
    
    if (!canvas || !overlayCanvas || !dicomFiles.length || currentSlice >= dicomFiles.length) {
      return;
    }
    
    const ctx = canvas.getContext('2d');
    const overlayCtx = overlayCanvas.getContext('2d');
    const dicomFile = dicomFiles[currentSlice];
    
    // Clear canvases
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    
    // Save context for transformations
    ctx.save();
    
    // Apply transformations
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    ctx.translate(centerX + viewport.panX, centerY + viewport.panY);
    ctx.scale(viewport.zoom, viewport.zoom);
    ctx.rotate((viewport.rotation * Math.PI) / 180);
    
    if (viewport.flipH) ctx.scale(-1, 1);
    if (viewport.flipV) ctx.scale(1, -1);
    
    // Render DICOM image
    renderPixelData(ctx, dicomFile, canvas.width, canvas.height);
    
    ctx.restore();
    
    // Render overlay elements (measurements, annotations)
    renderOverlay(overlayCtx);
    
  }, [currentSlice, viewport, imageState, dicomFiles]);

  const renderPixelData = (ctx, dicomFile, canvasWidth, canvasHeight) => {
    if (!dicomFile || !dicomFile.pixelData) return;
    
    const { rows, columns, pixelData } = dicomFile;
    
    // Create image data
    const imageData = ctx.createImageData(columns, rows);
    const data = imageData.data;
    
    // Apply window/level
    const { windowCenter, windowWidth } = imageState;
    const windowMin = windowCenter - windowWidth / 2;
    const windowMax = windowCenter + windowWidth / 2;
    
    // Convert DICOM pixels to RGB
    for (let i = 0; i < pixelData.length; i++) {
      let pixelValue = pixelData[i];
      
      // Apply window/level
      if (pixelValue <= windowMin) {
        pixelValue = 0;
      } else if (pixelValue >= windowMax) {
        pixelValue = 255;
      } else {
        pixelValue = ((pixelValue - windowMin) / windowWidth) * 255;
      }
      
      // Apply brightness and contrast
      pixelValue = (pixelValue * imageState.contrast) + imageState.brightness;
      pixelValue = Math.max(0, Math.min(255, pixelValue));
      
      // Apply invert
      if (viewport.invert) {
        pixelValue = 255 - pixelValue;
      }
      
      const pixelIndex = i * 4;
      data[pixelIndex] = pixelValue;     // Red
      data[pixelIndex + 1] = pixelValue; // Green
      data[pixelIndex + 2] = pixelValue; // Blue
      data[pixelIndex + 3] = 255;       // Alpha
    }
    
    // Draw image centered
    ctx.putImageData(imageData, -columns / 2, -rows / 2);
  };

  const renderOverlay = (ctx) => {
    // Render measurements
    if (showMeasurements) {
      measurements.forEach(measurement => {
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(measurement.start.x, measurement.start.y);
        ctx.lineTo(measurement.end.x, measurement.end.y);
        ctx.stroke();
        
        // Draw measurement value
        ctx.fillStyle = '#ffff00';
        ctx.font = '14px Arial';
        ctx.fillText(`${measurement.length.toFixed(2)} mm`, measurement.end.x + 5, measurement.end.y - 5);
      });
    }
    
    // Render annotations
    annotations.forEach(annotation => {
      ctx.fillStyle = '#00ff00';
      ctx.font = '14px Arial';
      ctx.fillText(annotation.text, annotation.x, annotation.y);
    });
    
    // Render crosshairs if active
    if (activeTool === 'crosshair') {
      const centerX = ctx.canvas.width / 2;
      const centerY = ctx.canvas.height / 2;
      
      ctx.strokeStyle = '#ff0000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(ctx.canvas.width, centerY);
      ctx.moveTo(centerX, 0);
      ctx.lineTo(centerX, ctx.canvas.height);
      ctx.stroke();
    }
  };

  // Mouse event handlers
  const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setIsDragging(true);
    setDragStart({ x, y });
    
    if (activeTool === 'length') {
      // Start new measurement
      const newMeasurement = {
        id: Date.now(),
        start: { x, y },
        end: { x, y },
        length: 0
      };
      setMeasurements(prev => [...prev, newMeasurement]);
    }
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - dragStart.x;
    const dy = y - dragStart.y;
    
    if (activeTool === 'pan') {
      setViewport(prev => ({
        ...prev,
        panX: prev.panX + dx,
        panY: prev.panY + dy
      }));
      setDragStart({ x, y });
    } else if (activeTool === 'windowLevel') {
      setImageState(prev => ({
        ...prev,
        windowWidth: Math.max(1, prev.windowWidth + dx * 2),
        windowCenter: prev.windowCenter - dy * 0.5
      }));
      setDragStart({ x, y });
    } else if (activeTool === 'length' && measurements.length > 0) {
      // Update current measurement
      setMeasurements(prev => {
        const updated = [...prev];
        const current = updated[updated.length - 1];
        const distance = Math.sqrt(Math.pow(x - current.start.x, 2) + Math.pow(y - current.start.y, 2));
        current.end = { x, y };
        current.length = distance * 0.1; // Approximate mm conversion
        return updated;
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    
    if (activeTool === 'zoom') {
      setViewport(prev => ({
        ...prev,
        zoom: Math.max(0.1, Math.min(10, prev.zoom + delta))
      }));
    } else {
      // Stack scrolling
      const newSlice = Math.max(0, Math.min(dicomFiles.length - 1, currentSlice + (e.deltaY > 0 ? 1 : -1)));
      setCurrentSlice(newSlice);
    }
  };

  // Tool functions
  const resetViewport = () => {
    setViewport({
      zoom: 1,
      panX: 0,
      panY: 0,
      rotation: 0,
      flipH: false,
      flipV: false,
      invert: false
    });
  };

  const fitToWindow = () => {
    if (dicomFiles.length === 0) return;
    
    const canvas = canvasRef.current;
    const dicomFile = dicomFiles[currentSlice];
    
    if (!canvas || !dicomFile) return;
    
    const scaleX = canvas.width / dicomFile.columns;
    const scaleY = canvas.height / dicomFile.rows;
    const scale = Math.min(scaleX, scaleY) * 0.9; // 90% to leave some margin
    
    setViewport(prev => ({
      ...prev,
      zoom: scale,
      panX: 0,
      panY: 0
    }));
  };

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const clearMeasurements = () => {
    setMeasurements([]);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <div className="text-lg">Loading DICOM Study...</div>
          <div className="text-sm text-gray-400">Study ID: {studyId}</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-4">Error Loading Study</div>
          <div className="text-sm text-gray-400 mb-4">{error}</div>
          <button 
            onClick={loadStudy}
            className="bg-blue-600 px-4 py-2 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-3 py-1 bg-gray-700 rounded hover:bg-gray-600"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          
          <div>
            <h1 className="text-lg font-bold">Advanced DICOM Viewer</h1>
            {study && (
              <div className="text-sm text-gray-400">
                {study.patient_name} • {study.modality} • {study.patient_age}Y {study.patient_gender}
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            className={`p-2 rounded ${showInfo ? 'bg-blue-600' : 'bg-gray-700'}`}
          >
            <Info className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowTools(!showTools)}
            className={`p-2 rounded ${showTools ? 'bg-blue-600' : 'bg-gray-700'}`}
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex flex-1">
        {/* Left Sidebar - Tools */}
        {showTools && (
          <div className="w-64 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
            <div className="space-y-4">
              {/* Navigation Tools */}
              <div>
                <h3 className="text-sm font-semibold mb-2 text-gray-300">Navigation</h3>
                <div className="grid grid-cols-4 gap-1">
                  <button
                    onClick={() => setActiveTool('windowLevel')}
                    className={`p-2 rounded text-xs ${activeTool === 'windowLevel' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Window/Level"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTool('zoom')}
                    className={`p-2 rounded text-xs ${activeTool === 'zoom' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Zoom"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTool('pan')}
                    className={`p-2 rounded text-xs ${activeTool === 'pan' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Pan"
                  >
                    <Move className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTool('crosshair')}
                    className={`p-2 rounded text-xs ${activeTool === 'crosshair' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Crosshair"
                  >
                    <MousePointer className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Measurement Tools */}
              <div>
                <h3 className="text-sm font-semibold mb-2 text-gray-300">Measurements</h3>
                <div className="grid grid-cols-4 gap-1">
                  <button
                    onClick={() => setActiveTool('length')}
                    className={`p-2 rounded text-xs ${activeTool === 'length' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Length"
                  >
                    <Ruler className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTool('angle')}
                    className={`p-2 rounded text-xs ${activeTool === 'angle' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Angle"
                  >
                    <Triangle className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTool('rectangle')}
                    className={`p-2 rounded text-xs ${activeTool === 'rectangle' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Rectangle ROI"
                  >
                    <Square className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTool('ellipse')}
                    className={`p-2 rounded text-xs ${activeTool === 'ellipse' ? 'bg-blue-600' : 'bg-gray-700'}`}
                    title="Ellipse ROI"
                  >
                    <Circle className="w-4 h-4" />
                  </button>
                </div>
                <button
                  onClick={clearMeasurements}
                  className="w-full mt-2 px-3 py-1 bg-red-600 rounded text-xs hover:bg-red-700"
                >
                  Clear All
                </button>
              </div>

              {/* Image Controls */}
              <div>
                <h3 className="text-sm font-semibold mb-2 text-gray-300">Image Controls</h3>
                <div className="space-y-2">
                  <button
                    onClick={fitToWindow}
                    className="w-full px-3 py-2 bg-gray-700 rounded text-sm hover:bg-gray-600 flex items-center gap-2"
                  >
                    <Maximize2 className="w-4 h-4" />
                    Fit to Window
                  </button>
                  <button
                    onClick={resetViewport}
                    className="w-full px-3 py-2 bg-gray-700 rounded text-sm hover:bg-gray-600 flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reset
                  </button>
                  <button
                    onClick={() => setViewport(prev => ({ ...prev, invert: !prev.invert }))}
                    className={`w-full px-3 py-2 rounded text-sm flex items-center gap-2 ${
                      viewport.invert ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    <EyeOff className="w-4 h-4" />
                    Invert
                  </button>
                </div>
              </div>

              {/* Window/Level Presets */}
              <div>
                <h3 className="text-sm font-semibold mb-2 text-gray-300">W/L Presets</h3>
                <div className="space-y-1">
                  {[
                    { name: 'Soft Tissue', wc: 40, ww: 400 },
                    { name: 'Lung', wc: -600, ww: 1600 },
                    { name: 'Bone', wc: 300, ww: 1500 },
                    { name: 'Brain', wc: 40, ww: 80 }
                  ].map(preset => (
                    <button
                      key={preset.name}
                      onClick={() => setImageState(prev => ({
                        ...prev,
                        windowCenter: preset.wc,
                        windowWidth: preset.ww
                      }))}
                      className="w-full px-3 py-1 bg-gray-700 rounded text-xs hover:bg-gray-600 text-left"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main Viewer Area */}
        <div className="flex-1 flex flex-col">
          {/* Toolbar */}
          <div className="bg-gray-800 border-b border-gray-700 p-2">
            <div className="flex items-center justify-between">
              {/* Playback Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentSlice(Math.max(0, currentSlice - 1))}
                  disabled={currentSlice === 0}
                  className="p-2 bg-gray-700 rounded disabled:opacity-50"
                >
                  <SkipBack className="w-4 h-4" />
                </button>
                <button
                  onClick={togglePlay}
                  className="p-2 bg-blue-600 rounded hover:bg-blue-700"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => setCurrentSlice(Math.min(dicomFiles.length - 1, currentSlice + 1))}
                  disabled={currentSlice === dicomFiles.length - 1}
                  className="p-2 bg-gray-700 rounded disabled:opacity-50"
                >
                  <SkipForward className="w-4 h-4" />
                </button>
                
                <div className="text-sm text-gray-300">
                  {currentSlice + 1} / {dicomFiles.length}
                </div>
              </div>

              {/* Image Info */}
              <div className="text-sm text-gray-300">
                Zoom: {(viewport.zoom * 100).toFixed(0)}% | 
                WL: {imageState.windowCenter.toFixed(0)}/{imageState.windowWidth.toFixed(0)}
              </div>
            </div>
          </div>

          {/* Canvas Area */}
          <div className="flex-1 relative bg-black">
            <canvas
              ref={canvasRef}
              width={800}
              height={600}
              className="absolute inset-0 w-full h-full cursor-crosshair"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onWheel={handleWheel}
              style={{ imageRendering: 'pixelated' }}
            />
            <canvas
              ref={overlayCanvasRef}
              width={800}
              height={600}
              className="absolute inset-0 w-full h-full pointer-events-none"
            />
          </div>
        </div>

        {/* Right Sidebar - Info Panel */}
        {showInfo && dicomFiles.length > 0 && (
          <div className="w-64 bg-gray-800 border-l border-gray-700 p-4 overflow-y-auto">
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold mb-2 text-gray-300">Study Information</h3>
                <div className="text-xs text-gray-400 space-y-1">
                  <div><span className="text-white">Patient:</span> {study?.patient_name}</div>
                  <div><span className="text-white">Age:</span> {study?.patient_age}Y</div>
                  <div><span className="text-white">Gender:</span> {study?.patient_gender}</div>
                  <div><span className="text-white">Modality:</span> {study?.modality}</div>
                </div>
              </div>

              {dicomFiles[currentSlice] && (
                <div>
                  <h3 className="text-sm font-semibold mb-2 text-gray-300">Image Information</h3>
                  <div className="text-xs text-gray-400 space-y-1">
                    <div><span className="text-white">Dimensions:</span> {dicomFiles[currentSlice].columns} × {dicomFiles[currentSlice].rows}</div>
                    <div><span className="text-white">Slice:</span> {currentSlice + 1} of {dicomFiles.length}</div>
                    <div><span className="text-white">Bits:</span> {dicomFiles[currentSlice].bitsAllocated}</div>
                  </div>
                </div>
              )}

              {measurements.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-2 text-gray-300">Measurements</h3>
                  <div className="text-xs text-gray-400 space-y-1">
                    {measurements.map((measurement, index) => (
                      <div key={measurement.id}>
                        Length {index + 1}: {measurement.length.toFixed(2)} mm
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}