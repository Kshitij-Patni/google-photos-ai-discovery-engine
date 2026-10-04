export default function Topbar() {
  const text = "AI Discovery Engine";
  // Using darker Material variants of Google colors for better contrast
  const colors = ["#1a73e8", "#d93025", "#f29900", "#1a73e8", "#188038", "#d93025"];
  
  let colorIndex = 0;

  return (
    <header className="topbar">
      <div className="topbar__logo">
        <img 
          src="https://www.gstatic.com/images/branding/product/1x/photos_96dp.png" 
          alt="Google Photos Logo" 
          width={32} 
          height={32} 
        />
        <span className="topbar__logo-text">Google Photos</span>
      </div>
      <div className="topbar__google-title">
        {text.split('').map((char, i) => {
          if (char === ' ') return <span key={i}>&nbsp;</span>;
          const color = colors[colorIndex % colors.length];
          colorIndex++;
          return <span key={i} style={{ color }}>{char}</span>;
        })}
      </div>
    </header>
  );
}
