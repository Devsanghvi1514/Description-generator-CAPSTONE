import React from 'react';

interface VisionCraftLogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
  subtitle?: string;
}

export const VisionCraftLogo: React.FC<VisionCraftLogoProps> = ({
  size = 42,
  className = '',
  showText = false,
  subtitle = 'Neural Vision',
}) => {
  return (
    <div className={`visioncraft-logo-wrapper ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '12px' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="visioncraft-svg-mark"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <linearGradient id="vc-grad-primary" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="50%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          <linearGradient id="vc-grad-core" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>
          <radialGradient id="vc-grad-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
          </radialGradient>
          <filter id="vc-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#3b82f6" floodOpacity="0.35" />
          </filter>
        </defs>

        {/* Ambient Glow */}
        <circle cx="32" cy="32" r="28" fill="url(#vc-grad-glow)" />

        {/* Outer Shield Plate */}
        <rect
          x="6"
          y="6"
          width="52"
          height="52"
          rx="16"
          className="vc-shield-bg"
          stroke="url(#vc-grad-primary)"
          strokeWidth="2"
          filter="url(#vc-shadow)"
        />

        {/* Aperture Neural Blades */}
        <g stroke="url(#vc-grad-primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M 22 14 C 28 15, 36 21, 38 27" fill="none" />
          <path d="M 44 20 C 43 27, 39 35, 33 39" fill="none" />
          <path d="M 40 46 C 33 46, 25 41, 22 35" fill="none" />
          <path d="M 17 40 C 18 33, 22 25, 29 21" fill="none" />
        </g>

        {/* Concentric Tech Lens Rings */}
        <circle cx="32" cy="32" r="18" stroke="url(#vc-grad-primary)" strokeWidth="1.6" strokeDasharray="3 3" opacity="0.8" />
        <circle cx="32" cy="32" r="12" stroke="url(#vc-grad-primary)" strokeWidth="2" />

        {/* Core Optical Iris */}
        <circle cx="32" cy="32" r="5.5" fill="url(#vc-grad-core)" />
        <circle cx="30" cy="30" r="1.8" fill="white" opacity="0.95" />

        {/* Neural Peripheral Nodes */}
        <circle cx="20" cy="18" r="2" fill="#06b6d4" />
        <circle cx="45" cy="22" r="2" fill="#3b82f6" />
        <circle cx="43" cy="44" r="2" fill="#8b5cf6" />
        <circle cx="17" cy="38" r="2" fill="#06b6d4" />
      </svg>

      {showText && (
        <div className="visioncraft-brand-text">
          <div className="brand-name-wrap">
            <span className="brand-text-main">Vision</span>
            <span className="brand-text-accent">Craft</span>
          </div>
          {subtitle && <span className="brand-badge">{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
