export function Logo({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg 
      className={className} 
      viewBox="0 0 100 100" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="100" height="100" rx="20" fill="currentColor" fillOpacity="0.1" />
      <path 
        d="M50 20L25 32.5V55C25 72.5 35 87.5 50 92.5C65 87.5 75 72.5 75 55V32.5L50 20Z" 
        fill="currentColor" 
      />
      <path 
        d="M50 45C55.5228 45 60 40.5228 60 35C60 29.4772 55.5228 25 50 25C44.4772 25 40 29.4772 40 35C40 40.5228 44.4772 45 50 45Z" 
        fill="white" 
      />
      <path 
        d="M36.19 60.19C39.46 54.49 44.53 50 50 50C55.47 50 60.54 54.49 63.81 60.19" 
        stroke="white" 
        strokeWidth="6" 
        strokeLinecap="round" 
      />
      <circle cx="68" cy="68" r="16" fill="var(--color-brand-accent)" />
      <path 
        d="M62 68L66 72L74 64" 
        stroke="white" 
        strokeWidth="4" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
      />
    </svg>
  )
}
