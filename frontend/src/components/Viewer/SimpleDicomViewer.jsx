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
    
    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);
    
    // Create simple visualization of the raw data
    const uint8Array = new Uint8Array(arrayBuffer);
    console.log('🔍 Raw data length:', uint8Array.length);
    
    // Simple approach: draw first bytes as pixels
    const imageData = ctx.createImageData(width, height);
    const pixels = imageData.data;
    
    for (let i = 0; i < Math.min(uint8Array.length, pixels.length / 4); i++) {
      const pixelIndex = i * 4;
      const value = uint8Array[i];
      
      // Set RGB to same value (grayscale)
      pixels[pixelIndex] = value;     // Red
      pixels[pixelIndex + 1] = value; // Green
      pixels[pixelIndex + 2] = value; // Blue
      pixels[pixelIndex + 3] = 255;   // Alpha
    }
    
    ctx.putImageData(imageData, 0, 0);
    
    // Add test pattern to verify canvas is working
    ctx.fillStyle = '#ff0000';
    ctx.fillRect(10, 10, 50, 50);
    
    ctx.fillStyle = '#00ff00';
    ctx.font = '16px Arial';
    ctx.fillText('RAW DICOM DATA TEST', 70, 30);
    ctx.fillText(`File size: ${uint8Array.length} bytes`, 70, 50);
    
    console.log('✅ Canvas updated with raw data');
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