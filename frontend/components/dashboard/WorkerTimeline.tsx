"use client";

export default function WorkerTimeline({
  ticks,
  maxWorkers,
}: {
  ticks: { t: number; workers: number }[];
  maxWorkers: number;
}) {
  const W = 620;
  const H = 200;
  const padL = 34;
  const padR = 14;
  const padT = 16;
  const padB = 26;

  const maxT = Math.max(ticks.length ? ticks[ticks.length - 1].t : 1, 1);
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const xy = (t: number, w: number) => {
    const x = padL + (t / maxT) * innerW;
    const y = padT + innerH - (w / maxWorkers) * innerH;
    return [x, y] as const;
  };

  const pts = ticks.map((d) => xy(d.t, d.workers));
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area =
    pts.length > 1
      ? `M ${padL},${padT + innerH} L ${pts
          .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
          .join(" L ")} L ${(pts[pts.length - 1][0]).toFixed(1)},${padT + innerH} Z`
      : "";

  const yTicks = [0, Math.ceil(maxWorkers / 2), maxWorkers];

  return (
    <div className="rounded-2xl border border-d-line bg-d-panel/60 p-5">
      <h2 className="mb-2 font-mono text-[12px] uppercase tracking-[0.2em] text-d-dim">
        Active workers over time
      </h2>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="Line graph of active GPU workers over elapsed time, spiking during the embedding burst then returning to zero"
      >
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#33E6B0" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#33E6B0" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* y gridlines + labels */}
        {yTicks.map((w) => {
          const [, y] = xy(0, w);
          return (
            <g key={w}>
              <line
                x1={padL}
                y1={y}
                x2={W - padR}
                y2={y}
                stroke={w === 0 ? "#33E6B0" : "#1E3036"}
                strokeWidth="1"
                strokeDasharray={w === 0 ? "4 4" : undefined}
                opacity={w === 0 ? 0.6 : 1}
              />
              <text
                x={padL - 8}
                y={y + 4}
                textAnchor="end"
                className="fill-d-dim font-mono"
                fontSize="10"
              >
                {w}
              </text>
            </g>
          );
        })}

        {area && <path d={area} fill="url(#areaFill)" />}
        {pts.length > 1 && (
          <polyline
            points={line}
            fill="none"
            stroke="#33E6B0"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}
        {pts.length > 0 && (
          <circle
            cx={pts[pts.length - 1][0]}
            cy={pts[pts.length - 1][1]}
            r="3.5"
            fill="#33E6B0"
            className="dash-glow"
          />
        )}

        {/* x axis label */}
        <text
          x={W - padR}
          y={H - 6}
          textAnchor="end"
          className="fill-d-dim font-mono"
          fontSize="10"
        >
          {maxT.toFixed(1)}s elapsed
        </text>
      </svg>
    </div>
  );
}
