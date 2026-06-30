'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { useTheme } from 'next-themes';

export function SpaceBackground() {
  const { theme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  
  const springX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 20 });

  useEffect(() => {
    if (!mounted) return;

    const handleMouseMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      const x = (e.clientX / innerWidth - 0.5) * 40; // Parallax intensity
      const y = (e.clientY / innerHeight - 0.5) * 40;
      mouseX.set(x);
      mouseY.set(y);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mounted, mouseX, mouseY]);

  useEffect(() => {
    if (!mounted) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;
    
    let animationFrameId: number;
    let width = 0;
    let height = 0;
    
    // Particle arrays
    const stars: { x: number; y: number; size: number; speed: number; alpha: number; twinkleSpeed: number; phase: number; layer: number }[] = [];
    const dusts: { x: number; y: number; size: number; vx: number; vy: number; alpha: number }[] = [];
    const meteors: { x: number; y: number; length: number; speed: number; angle: number; active: boolean }[] = [];
    
    const initCanvas = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      
      // Handle high DPI displays for crispness
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      
      // Initialize Stars (3 layers for depth)
      stars.length = 0;
      const numStars = Math.floor((width * height) / 1200);
      for (let i = 0; i < numStars; i++) {
        const layer = Math.random() < 0.7 ? 1 : Math.random() < 0.9 ? 2 : 3;
        stars.push({
          x: Math.random() * width,
          y: Math.random() * height,
          size: Math.random() * 0.8 * layer + 0.2,
          speed: 0.03 * layer,
          alpha: Math.random() * 0.6 + 0.2,
          twinkleSpeed: Math.random() * 0.02 + 0.005,
          phase: Math.random() * Math.PI * 2,
          layer
        });
      }
      
      // Initialize Ambient Dust
      dusts.length = 0;
      for (let i = 0; i < 30; i++) {
        dusts.push({
          x: Math.random() * width,
          y: Math.random() * height,
          size: Math.random() * 4 + 2,
          vx: (Math.random() - 0.5) * 0.2,
          vy: (Math.random() - 0.5) * 0.2 - 0.1, // Slight upward drift
          alpha: Math.random() * 0.15 + 0.05
        });
      }
      
      // Initialize Meteors (pool of 2)
      meteors.length = 0;
      for (let i = 0; i < 2; i++) {
        meteors.push(createMeteor());
      }
    };
    
    const createMeteor = () => ({
      x: Math.random() * width * 1.5 - width * 0.25,
      y: -200 - Math.random() * 800,
      length: Math.random() * 150 + 100,
      speed: Math.random() * 15 + 15,
      angle: Math.PI / 4 + (Math.random() - 0.5) * 0.1, // ~45 degrees downward
      active: Math.random() > 0.7
    });
    
    let time = 0;
    
    const render = () => {
      time += 1;
      ctx.clearRect(0, 0, width, height);
      
      // Draw Stars
      for (const star of stars) {
        star.y -= star.speed;
        if (star.y < 0) {
          star.y = height;
          star.x = Math.random() * width;
        }
        
        star.phase += star.twinkleSpeed;
        const currentAlpha = star.alpha * (0.6 + Math.sin(star.phase) * 0.4);
        
        ctx.fillStyle = `rgba(255, 255, 255, ${currentAlpha})`;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
      }
      
      // Draw Dust (soft glowing particles)
      for (const dust of dusts) {
        dust.x += dust.vx;
        dust.y += dust.vy;
        
        if (dust.x < 0) dust.x = width;
        if (dust.x > width) dust.x = 0;
        if (dust.y < 0) dust.y = height;
        if (dust.y > height) dust.y = 0;
        
        ctx.fillStyle = `rgba(200, 220, 255, ${dust.alpha})`;
        ctx.shadowBlur = dust.size * 2;
        ctx.shadowColor = 'rgba(200, 220, 255, 0.4)';
        ctx.beginPath();
        ctx.arc(dust.x, dust.y, dust.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0; // reset
      
      // Draw Meteors
      if (time % 200 === 0) {
        const inactive = meteors.find(m => !m.active);
        if (inactive && Math.random() > 0.4) {
          Object.assign(inactive, createMeteor());
          inactive.active = true;
        }
      }
      
      ctx.lineCap = 'round';
      for (const m of meteors) {
        if (!m.active) continue;
        
        m.x += Math.cos(m.angle) * m.speed;
        m.y += Math.sin(m.angle) * m.speed;
        
        const tailX = m.x - Math.cos(m.angle) * m.length;
        const tailY = m.y - Math.sin(m.angle) * m.length;
        
        const grad = ctx.createLinearGradient(m.x, m.y, tailX, tailY);
        grad.addColorStop(0, 'rgba(255, 255, 255, 0.8)');
        grad.addColorStop(0.1, 'rgba(120, 200, 255, 0.4)');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        
        ctx.strokeStyle = grad;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(m.x, m.y);
        ctx.lineTo(tailX, tailY);
        ctx.stroke();
        
        if (m.y > height + m.length || m.x > width + m.length) {
          m.active = false;
        }
      }
      
      animationFrameId = requestAnimationFrame(render);
    };
    
    initCanvas();
    render();
    
    const handleResize = () => initCanvas();
    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [mounted]);

  if (!mounted) return null;

  return (
    <div 
      className="fixed inset-0 overflow-hidden pointer-events-none -z-50 transition-colors duration-[700ms] ease-cinematic"
      style={{
        backgroundColor: resolvedTheme === 'dark' ? '#050608' : '#F6F4EF'
      }}
    >
      {/* ── PARALLAX CONTAINER ── */}
      <motion.div
        className="absolute inset-0 w-[110vw] h-[110vh] -left-[5vw] -top-[5vh]"
        style={{ x: springX, y: springY, willChange: 'transform' }}
      >
          <>
            {/* 1. Distant Galaxy (Deepest Layer) */}
            <div className={`absolute top-1/4 left-1/3 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_at_center,_rgba(40,30,80,0.15)_0%,_transparent_70%)] rounded-[100%] scale-y-50 -rotate-12 blur-[80px] transition-opacity duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'opacity-100' : 'opacity-0'}`} />

            {/* 2. 3 Nebula Layers (CSS) */}
            <div className={`absolute top-[-10%] left-[-10%] w-[60vw] h-[60vh] rounded-full blur-[100px] mix-blend-screen animate-[spin_180s_linear_infinite] transition-all duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'bg-[radial-gradient(circle_at_center,_rgba(20,50,150,0.15)_0%,_transparent_60%)] opacity-100' : 'bg-[radial-gradient(circle_at_center,_rgba(20,50,150,0.05)_0%,_transparent_60%)] opacity-50'}`} style={{ willChange: 'transform' }} />
            <div className={`absolute bottom-[-20%] right-[-10%] w-[70vw] h-[70vh] rounded-full blur-[120px] mix-blend-screen animate-[spin_240s_linear_infinite_reverse] transition-all duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'bg-[radial-gradient(circle_at_center,_rgba(120,30,150,0.1)_0%,_transparent_60%)] opacity-100' : 'bg-[radial-gradient(circle_at_center,_rgba(120,30,150,0.03)_0%,_transparent_60%)] opacity-50'}`} style={{ willChange: 'transform' }} />
            
            {/* 3. Ambient Green Glow */}
            <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] h-[90vh] rounded-full blur-[140px] mix-blend-screen transition-all duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'bg-[radial-gradient(circle_at_center,_rgba(0,255,128,0.03)_0%,_transparent_70%)] opacity-100' : 'bg-[radial-gradient(circle_at_center,_rgba(0,255,128,0.01)_0%,_transparent_70%)] opacity-50'}`} />
            
            {/* 4. Canvas Layer: Stars, Dust, Meteors */}
            <canvas ref={canvasRef} className={`absolute inset-0 z-0 mix-blend-screen transition-opacity duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'opacity-100' : 'opacity-0'}`} />
            
            {/* 5. Warp Layer */}
            <div className={`absolute inset-0 z-0 mix-blend-screen transition-opacity duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'opacity-[0.06]' : 'opacity-0'}`}>
               <div className="absolute top-[10%] left-[20%] w-[1px] h-[30vh] bg-gradient-to-b from-transparent via-white to-transparent rotate-45 animate-warp" style={{ '--warp-duration': '3.2s', '--warp-delay': '0s' } as any} />
               <div className="absolute top-[40%] left-[60%] w-[1px] h-[40vh] bg-gradient-to-b from-transparent via-white to-transparent rotate-45 animate-warp" style={{ '--warp-duration': '4.5s', '--warp-delay': '1.5s' } as any} />
               <div className="absolute top-[70%] left-[30%] w-[1px] h-[25vh] bg-gradient-to-b from-transparent via-white to-transparent rotate-45 animate-warp" style={{ '--warp-duration': '2.8s', '--warp-delay': '0.7s' } as any} />
               <div className="absolute top-[15%] left-[80%] w-[1px] h-[35vh] bg-gradient-to-b from-transparent via-white to-transparent rotate-45 animate-warp" style={{ '--warp-duration': '5s', '--warp-delay': '2.2s' } as any} />
               <div className="absolute top-[80%] left-[70%] w-[1px] h-[20vh] bg-gradient-to-b from-transparent via-white to-transparent rotate-45 animate-warp" style={{ '--warp-duration': '3.7s', '--warp-delay': '3.1s' } as any} />
            </div>

            {/* 6. Aurora Borealis Effect */}
            <div className={`absolute top-0 left-0 w-[200%] h-[30vh] mix-blend-screen transform-gpu blur-[60px] transition-opacity duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'opacity-20' : 'opacity-0'}`}
                 style={{
                   background: 'linear-gradient(90deg, transparent 0%, rgba(0, 255, 128, 0.4) 20%, rgba(50, 150, 255, 0.4) 40%, transparent 60%, rgba(0, 255, 128, 0.4) 80%, transparent 100%)',
                   animation: 'aurora-wave 60s linear infinite',
                   willChange: 'transform'
                 }}
            />

            {/* 7. Volumetric Lighting */}
            <div className={`absolute -top-[50%] -left-[50%] w-[200%] h-[200%] mix-blend-screen pointer-events-none origin-center animate-[spin_180s_linear_infinite] transition-opacity duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'opacity-[0.03]' : 'opacity-[0.01]'}`}
                 style={{
                   background: 'conic-gradient(from 0deg at 50% 50%, transparent 0deg, #ffffff 45deg, transparent 90deg, transparent 180deg, #ffffff 225deg, transparent 270deg)',
                   filter: 'blur(100px)',
                   willChange: 'transform'
                 }}
            />
          </>
      </motion.div>

      {/* 8. Subtle Vignette */}
      <div className={`absolute inset-0 pointer-events-none transition-opacity duration-[700ms] ease-cinematic ${resolvedTheme === 'dark' ? 'opacity-80' : 'opacity-10'}`}
           style={{
             boxShadow: 'inset 0 0 200px rgba(0,0,0,0.8)'
           }}
      />
      
      {/* Required CSS Animations */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes aurora-wave {
          0% { transform: translate3d(0, 0, 0) skewX(-15deg); }
          100% { transform: translate3d(-50%, 0, 0) skewX(-15deg); }
        }
      `}} />
    </div>
  );
}
