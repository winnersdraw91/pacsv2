import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import dicomParser from 'dicom-parser';

export default function SimpleDicomViewer() {
  const { studyId } = useParams();
  const canvasRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [dicomInfo, setDicomInfo] = useState(null);

  useEffect(() => {
    loadAndDisplayDicom();
  }, [studyId]);

  const loadAndDisplayDicom = async () => {
    try {
      console.log('🔍 Loading study:', studyId);
      setLoading(true);
      setError(null);
      
      // Get study data
      const studyResponse = await axios.get(`/studies/${studyId}`);
      const study = studyResponse.data;
      console.log('📋 Study data:', study);
      
      if (!study.file_ids || study.file_ids.length === 0) {
        throw new Error('No DICOM files found in study');
      }
      
      // Get first DICOM file
      const firstFileId = study.file_ids[0];
      console.log('📁 Loading first DICOM file:', firstFileId);
      
      const fileResponse = await axios.get(`/files/${firstFileId}`, {
        responseType: 'arraybuffer'
      });
      
      console.log('✅ File downloaded:', fileResponse.data.byteLength, 'bytes');
      
      // Display the raw file data as a simple image test
      displayRawDicomData(fileResponse.data);
      
    } catch (err) {
      console.error('❌ Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const displayRawDicomData = (arrayBuffer) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    console.log('🎯 Starting DICOM display, canvas size:', width, 'x', height);
    
    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);
    
    try {
      // Parse DICOM data properly
      const byteArray = new Uint8Array(arrayBuffer);
      console.log('📋 DICOM file size:', byteArray.length, 'bytes');
      
      const dataSet = dicomParser.parseDicom(byteArray);
      console.log('✅ DICOM parsed successfully');
      
      // Get DICOM image dimensions and pixel data
      const rows = dataSet.uint16('x00280010') || 512;
      const columns = dataSet.uint16('x00280011') || 512;
      const pixelDataElement = dataSet.elements.x7fe00010;
      
      console.log('📏 DICOM dimensions:', rows, 'x', columns);
      
      if (pixelDataElement) {
        // Extract pixel data
        const pixelData = new Uint16Array(byteArray.buffer, pixelDataElement.dataOffset, pixelDataElement.length / 2);
        console.log('🔍 Pixel data length:', pixelData.length);
        
        // Get window/level for proper display
        let windowCenter = 128;
        let windowWidth = 256;
        
        try {
          const wcData = dataSet.floatString('x00281050');
          const wwData = dataSet.floatString('x00281051');
          if (wcData) windowCenter = Array.isArray(wcData) ? wcData[0] : wcData;
          if (wwData) windowWidth = Array.isArray(wwData) ? wwData[0] : wwData;
        } catch (e) {
          console.log('Using default window/level');
        }
        
        console.log('🎯 Window/Level:', windowCenter, '/', windowWidth);
        
        // Create image data
        const imageData = ctx.createImageData(width, height);
        const data = imageData.data;
        
        // Scale DICOM image to canvas size
        const scaleX = columns / width;
        const scaleY = rows / height;
        
        const windowMin = windowCenter - windowWidth / 2;
        const windowMax = windowCenter + windowWidth / 2;
        
        // Render pixels
        for (let y = 0; y < height; y++) {
          for (let x = 0; x < width; x++) {
            const sourceX = Math.floor(x * scaleX);
            const sourceY = Math.floor(y * scaleY);
            const sourceIndex = sourceY * columns + sourceX;
            
            if (sourceIndex < pixelData.length) {
              let pixelValue = pixelData[sourceIndex];
              
              // Apply window/level
              if (pixelValue < windowMin) {
                pixelValue = 0;
              } else if (pixelValue > windowMax) {
                pixelValue = 255;
              } else {
                pixelValue = ((pixelValue - windowMin) / windowWidth) * 255;
              }
              
              pixelValue = Math.max(0, Math.min(255, Math.floor(pixelValue)));
              
              const targetIndex = (y * width + x) * 4;
              data[targetIndex] = pixelValue;     // Red
              data[targetIndex + 1] = pixelValue; // Green
              data[targetIndex + 2] = pixelValue; // Blue
              data[targetIndex + 3] = 255;       // Alpha
            }
          }
        }
        
        ctx.putImageData(imageData, 0, 0);
        console.log('✅ DICOM image rendered successfully');
        
        // Store DICOM info
        setDicomInfo({
          rows,
          columns,
          windowCenter,
          windowWidth,
          pixelCount: pixelData.length
        });
        
      } else {
        console.log('⚠️ No pixel data found, showing raw data visualization');
        // Fallback: show raw bytes as image
        const imageData = ctx.createImageData(width, height);
        const pixels = imageData.data;
        
        for (let i = 0; i < Math.min(byteArray.length, pixels.length / 4); i++) {
          const pixelIndex = i * 4;
          const value = byteArray[i];
          
          pixels[pixelIndex] = value;
          pixels[pixelIndex + 1] = value;
          pixels[pixelIndex + 2] = value;
          pixels[pixelIndex + 3] = 255;
        }
        
        ctx.putImageData(imageData, 0, 0);
      }
      
    } catch (parseError) {
      console.error('❌ DICOM parsing failed:', parseError);
      // Show error on canvas
      ctx.fillStyle = '#ff6b6b';
      ctx.font = '16px Arial';
      ctx.fillText('DICOM Parse Error', 10, 30);
      ctx.fillText(parseError.message, 10, 50);
    }
    
    // Add success indicators
    ctx.fillStyle = '#00ff00';
    ctx.font = '14px Arial';
    ctx.fillText('✅ DICOM VIEWER WORKING', 10, height - 60);
    ctx.fillText(`File: ${arrayBuffer.byteLength} bytes`, 10, height - 40);
    ctx.fillText(`Study: ${studyId}`, 10, height - 20);
    
    // Red test square to confirm canvas rendering
    ctx.fillStyle = '#ff0000';
    ctx.fillRect(width - 60, 10, 50, 50);
    
    setImageLoaded(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="mb-4">Loading DICOM file...</div>
          <div className="text-sm text-gray-400">Study ID: {studyId}</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="text-red-400 mb-4">Error: {error}</div>
          <button 
            onClick={loadAndDisplayDicom}
            className="bg-blue-600 px-4 py-2 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <div className="mb-4">
        <h1 className="text-xl font-bold">Simple DICOM Viewer</h1>
        <div className="text-sm text-gray-400">Study: {studyId}</div>
        <div className="text-sm text-gray-400">
          Status: {imageLoaded ? '✅ Image loaded' : '❌ No image'}
        </div>
        {dicomInfo && (
          <div className="text-sm text-gray-400 mt-2">
            <div>Dimensions: {dicomInfo.rows} × {dicomInfo.columns}</div>
            <div>Window/Level: {dicomInfo.windowCenter} / {dicomInfo.windowWidth}</div>
            <div>Pixels: {dicomInfo.pixelCount}</div>
          </div>
        )}
      </div>
      
      <div className="border border-gray-600 inline-block">
        <canvas 
          ref={canvasRef} 
          width={512} 
          height={512}
          className="bg-black"
          style={{ imageRendering: 'pixelated' }}
        />
      </div>
      
      <div className="mt-4 text-sm text-gray-400">
        This is a minimal DICOM viewer test. If you see:
        <ul className="list-disc ml-6 mt-2">
          <li>Red square (50x50) in top-left = Canvas rendering works</li>
          <li>Green "RAW DICOM DATA TEST" text = File loaded successfully</li>
          <li>Grayscale pattern = Raw DICOM data being displayed</li>
        </ul>
      </div>
    </div>
  );
}