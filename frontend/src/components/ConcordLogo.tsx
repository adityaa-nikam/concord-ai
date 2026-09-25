import React from 'react';

interface ConcordLogoProps {
  variant?: 'full' | 'icon' | 'horizontal';
  className?: string;
  iconSize?: number;
}

export const ConcordIcon: React.FC<{ size?: number; className?: string }> = ({ size = 28, className = "" }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 120 120"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    {/* Left Navy Bracket */}
    <path d="M 54,10 A 50,50 0 0,0 54,110 L 54,82 L 28,60 L 54,38 Z" fill="#0A192F" />
    {/* Right Blue Bracket */}
    <path d="M 66,10 A 50,50 0 0,1 66,110 L 66,82 L 92,60 L 66,38 Z" fill="#0088FF" />
  </svg>
);

export const ConcordLogo: React.FC<ConcordLogoProps> = ({
  variant = 'horizontal',
  className = '',
  iconSize = 26
}) => {
  if (variant === 'icon') {
    return <ConcordIcon size={iconSize} className={className} />;
  }

  if (variant === 'full') {
    return (
      <div className={`flex flex-col items-center select-none ${className}`}>
        <ConcordIcon size={iconSize * 1.8} />
        <div className="mt-2 text-center">
          <span className="block font-black text-slate-900 tracking-wider text-base font-sans leading-none">
            CONCORD
          </span>
          <span className="block font-bold text-[#0088FF] tracking-[0.25em] text-xs font-sans mt-0.5">
            AI
          </span>
        </div>
      </div>
    );
  }

  // Horizontal variant (Ideal for Sidebar & Header)
  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      <ConcordIcon size={iconSize} className="shrink-0" />
      <div className="flex items-baseline gap-1 font-sans">
        <span className="font-extrabold text-slate-900 text-sm tracking-tight">
          CONCORD
        </span>
        <span className="font-bold text-[#0088FF] text-xs tracking-wider">
          AI
        </span>
      </div>
    </div>
  );
};
