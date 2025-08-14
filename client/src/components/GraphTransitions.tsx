/**
 * Graph transition effects and animations for smooth visual updates.
 * Provides particle effects, smooth node/edge transitions, and visual feedback.
 */

import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Particle {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  color: string;
  size: number;
}

interface GraphTransitionsProps {
  isVisible?: boolean;
  particleCount?: number;
  className?: string;
}

const GraphTransitions: React.FC<GraphTransitionsProps> = ({
  isVisible = true,
  particleCount = 50,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const [particles, setParticles] = useState<Particle[]>([]);
  const [showConnectionPulse, setShowConnectionPulse] = useState(false);

  // Initialize particles
  useEffect(() => {
    if (!isVisible) return;

    const newParticles: Particle[] = [];
    for (let i = 0; i < particleCount; i++) {
      newParticles.push(createParticle(i.toString()));
    }
    setParticles(newParticles);
  }, [isVisible, particleCount]);

  // Create a new particle
  const createParticle = (id: string): Particle => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return {
        id,
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        life: 0,
        maxLife: 100,
        color: '#3b82f6',
        size: 2
      };
    }

    return {
      id,
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      life: Math.random() * 100,
      maxLife: 100 + Math.random() * 100,
      color: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'][Math.floor(Math.random() * 4)],
      size: 1 + Math.random() * 2
    };
  };

  // Animation loop
  useEffect(() => {
    if (!isVisible || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      setParticles(prevParticles => {
        return prevParticles.map(particle => {
          // Update particle position
          particle.x += particle.vx;
          particle.y += particle.vy;
          particle.life += 1;

          // Wrap around edges
          if (particle.x < 0) particle.x = canvas.width;
          if (particle.x > canvas.width) particle.x = 0;
          if (particle.y < 0) particle.y = canvas.height;
          if (particle.y > canvas.height) particle.y = 0;

          // Reset particle if life exceeded
          if (particle.life > particle.maxLife) {
            return createParticle(particle.id);
          }

          // Draw particle
          const alpha = 1 - (particle.life / particle.maxLife);
          ctx.globalAlpha = alpha * 0.3;
          ctx.fillStyle = particle.color;
          ctx.beginPath();
          ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
          ctx.fill();

          return particle;
        });
      });

      // Draw connections between nearby particles
      ctx.globalAlpha = 0.1;
      ctx.strokeStyle = '#6b7280';
      ctx.lineWidth = 1;

      particles.forEach((particle1, i) => {
        particles.slice(i + 1).forEach(particle2 => {
          const dx = particle1.x - particle2.x;
          const dy = particle1.y - particle2.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 100) {
            ctx.beginPath();
            ctx.moveTo(particle1.x, particle1.y);
            ctx.lineTo(particle2.x, particle2.y);
            ctx.stroke();
          }
        });
      });

      ctx.globalAlpha = 1;
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isVisible, particles]);

  // Connection pulse effect
  const triggerConnectionPulse = () => {
    setShowConnectionPulse(true);
    setTimeout(() => setShowConnectionPulse(false), 2000);
  };

  // Listen for graph updates to trigger effects
  useEffect(() => {
    const handleGraphUpdate = () => {
      triggerConnectionPulse();
    };

    // You can connect this to your graph update events
    window.addEventListener('graph-update', handleGraphUpdate);
    return () => window.removeEventListener('graph-update', handleGraphUpdate);
  }, []);

  if (!isVisible) return null;

  return (
    <div className={`fixed inset-0 pointer-events-none z-0 ${className}`}>
      {/* Particle canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 opacity-30"
        style={{ mixBlendMode: 'screen' }}
      />

      {/* Connection pulse overlay */}
      <AnimatePresence>
        {showConnectionPulse && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0"
          >
            {/* Radial pulse effect */}
            <motion.div
              initial={{ scale: 0, opacity: 1 }}
              animate={{ scale: 3, opacity: 0 }}
              transition={{ duration: 2, ease: "easeOut" }}
              className="absolute top-1/2 left-1/2 w-32 h-32 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-blue-400"
            />
            <motion.div
              initial={{ scale: 0, opacity: 1 }}
              animate={{ scale: 2, opacity: 0 }}
              transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
              className="absolute top-1/2 left-1/2 w-32 h-32 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-purple-400"
            />
            <motion.div
              initial={{ scale: 0, opacity: 1 }}
              animate={{ scale: 1.5, opacity: 0 }}
              transition={{ duration: 1, ease: "easeOut", delay: 0.4 }}
              className="absolute top-1/2 left-1/2 w-32 h-32 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-green-400"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ambient light effects */}
      <div className="absolute inset-0 bg-gradient-radial from-blue-900/10 via-transparent to-transparent" />
      <div className="absolute top-0 left-0 w-full h-full bg-gradient-conic from-purple-900/5 via-transparent to-blue-900/5" />
    </div>
  );
};

// Node appearance animation component
interface NodeAppearanceProps {
  isVisible: boolean;
  position: { x: number; y: number };
  onComplete?: () => void;
}

export const NodeAppearanceEffect: React.FC<NodeAppearanceProps> = ({
  isVisible,
  position,
  onComplete
}) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: [0, 1.5, 1], opacity: [0, 1, 0] }}
          exit={{ scale: 0, opacity: 0 }}
          transition={{ duration: 1, ease: "easeOut" }}
          onAnimationComplete={onComplete}
          className="fixed pointer-events-none z-30"
          style={{
            left: position.x - 25,
            top: position.y - 25,
            width: 50,
            height: 50
          }}
        >
          <div className="w-full h-full rounded-full border-2 border-blue-400 bg-blue-400/20" />
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.5, repeat: Infinity }}
            className="absolute inset-2 rounded-full bg-blue-400/40"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// Edge connection animation component
interface EdgeConnectionProps {
  isVisible: boolean;
  start: { x: number; y: number };
  end: { x: number; y: number };
  onComplete?: () => void;
}

export const EdgeConnectionEffect: React.FC<EdgeConnectionProps> = ({
  isVisible,
  start,
  end,
  onComplete
}) => {
  const length = Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2));
  const angle = Math.atan2(end.y - start.y, end.x - start.x) * (180 / Math.PI);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: [0, 1, 0] }}
          exit={{ scaleX: 0, opacity: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          onAnimationComplete={onComplete}
          className="fixed pointer-events-none z-30 origin-left"
          style={{
            left: start.x,
            top: start.y - 1,
            width: length,
            height: 2,
            transform: `rotate(${angle}deg)`,
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)'
          }}
        >
          <motion.div
            animate={{ x: [0, length] }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="w-4 h-4 -mt-1 rounded-full bg-white shadow-lg"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default GraphTransitions;