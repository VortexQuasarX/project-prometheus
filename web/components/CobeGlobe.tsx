"use client";
import { useEffect, useRef } from "react";
import createGlobe from "cobe";

export function CobeGlobe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let phi = 0;
    
    if (!canvasRef.current) return;
    
    const globe = createGlobe(canvasRef.current, {
      devicePixelRatio: 2,
      width: 1000,
      height: 1000,
      phi: 0,
      theta: 0.3,
      dark: 1,
      diffuse: 1.2,
      mapSamples: 24000,
      mapBrightness: 6,
      baseColor: [0.05, 0.05, 0.08],
      markerColor: [0.1, 0.8, 1],
      glowColor: [0.1, 0.1, 0.2],
      markers: [
        { location: [38.03, -78.47], size: 0.06 },
        { location: [45.83, -119.7], size: 0.06 },
        { location: [50.11, 8.68], size: 0.06 },
        { location: [35.68, 139.69], size: 0.06 },
        { location: [19.07, 72.87], size: 0.1 },
      ],
      onRender: (state) => {
        state.phi = phi;
        phi += 0.005;
      }
    });

    return () => {
      globe.destroy();
    };
  }, []);

  return (
    <div style={{ width: '100%', maxWidth: 700, aspectRatio: 1, margin: 'auto', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          contain: 'layout paint size',
          opacity: 1,
          transition: 'opacity 1s ease',
        }}
      />
    </div>
  );
}
