import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const size = { width: 32, height: 32 };
export const contentType = 'image/png';

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'transparent',
        }}
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 120 120"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M 54,10 A 50,50 0 0,0 54,110 L 54,82 L 28,60 L 54,38 Z" fill="#0A192F" />
          <path d="M 66,10 A 50,50 0 0,1 66,110 L 66,82 L 92,60 L 66,38 Z" fill="#0088FF" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
