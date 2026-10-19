// Live "Now" card. Deployed as a Vercel serverless function (GET /api/now).
// It renders the card at request time, so the clock is the real time in Poland
// whenever the README is opened. The seconds bar and the HH:MM digits keep
// ticking inside the SVG for the next 30 minutes.

const TZ = "Europe/Warsaw";
const BG = "#07080c", PANEL = "#0c0e14", LINE = "#1c2030";
const TEXT = "#e8ecf4", DIM = "#7a8399", LIME = "#d4ff3a", ORANGE = "#ff5a1f";
const FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace";

function warsawNow() {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  }).formatToParts(new Date());
  const get = (t) => Number(parts.find((p) => p.type === t).value);
  // some runtimes report midnight as 24
  return { h: get("hour") % 24, m: get("minute"), s: get("second") };
}

const pad = (n) => String(n).padStart(2, "0");

function render() {
  const { h, m, s } = warsawNow();
  const W = 1200, H = 250;
  const hh = h + m / 60;
  const part = hh < 5 || hh >= 23 ? "Night" : hh < 12 ? "Morning" : hh < 18 ? "Afternoon" : "Evening";
  const ax = 190, ay = 168, ar = 100;
  const f = Math.min(Math.max((hh - 6) / 14, 0), 1);
  const day = hh >= 6 && hh <= 20;
  const ang = Math.PI * (1 - f);
  const sx = ax + ar * Math.cos(ang), sy = ay - ar * Math.sin(ang);
  const body = day
    ? `<circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="11" fill="${LIME}" filter="url(#glow)"><animate attributeName="r" values="10;14;10" dur="3s" repeatCount="indefinite"/></circle>`
    : `<circle cx="${ax}" cy="${ay - 70}" r="12" fill="${TEXT}"/><circle cx="${ax + 6}" cy="${ay - 74}" r="11" fill="${BG}"/>`;

  // HH:MM for the next 30 minutes, switched on at the right second
  let clock = "";
  for (let i = 0; i < 30; i++) {
    const total = h * 60 + m + i;
    const label = `${pad(Math.floor(total / 60) % 24)}:${pad(total % 60)}`;
    const start = i === 0 ? 0 : i * 60 - s;
    const end = (i + 1) * 60 - s;
    const timing = i === 0
      ? `<set attributeName="opacity" to="0" begin="${end}s" fill="freeze"/>`
      : i === 29
        ? `<set attributeName="opacity" to="1" begin="${start}s" fill="freeze"/>`
        : `<set attributeName="opacity" to="1" begin="${start}s"/><set attributeName="opacity" to="0" begin="${end}s"/>`;
    clock += `<text x="${ax}" y="${ay + 40}" font-size="44" font-weight="700" text-anchor="middle" fill="${TEXT}" opacity="${i === 0 ? 1 : 0}">${label}${timing}</text>`;
  }

  const barW = 180;
  const secBar =
    `<rect x="${ax - barW / 2}" y="${ay + 70}" width="${barW}" height="3" rx="1.5" fill="${LINE}"/>` +
    `<rect x="${ax - barW / 2}" y="${ay + 70}" width="0" height="3" rx="1.5" fill="${LIME}">` +
    `<animate attributeName="width" from="0" to="${barW}" dur="60s" begin="-${s}s" repeatCount="indefinite"/></rect>`;

  const learning = ["Rust", "C++", "Kotlin", "React Native", "MongoDB", "Redis"];
  const chips = learning.map((n, i) => {
    const x = 800 + (i % 2) * 175, y = 78 + Math.floor(i / 2) * 44;
    return `<rect x="${x}" y="${y}" width="160" height="34" rx="17" fill="${PANEL}" stroke="${ORANGE}" stroke-dasharray="4 4" stroke-opacity=".8"/>` +
      `<circle cx="${x + 18}" cy="${y + 17}" r="3.5" fill="${ORANGE}"><animate attributeName="opacity" values="1;.2;1" dur="${(2 + i * 0.3).toFixed(1)}s" repeatCount="indefinite"/></circle>` +
      `<text x="${x + 32}" y="${y + 22}" font-size="14" fill="${TEXT}">${n}</text>`;
  }).join("");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="${FONT}" role="img" aria-label="Live time in Poland, current project and study list">
<defs>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#12151f" stroke-width="1"/></pattern>
<clipPath id="frame"><rect x="1" y="1" width="${W - 2}" height="${H - 2}" rx="20"/></clipPath>
</defs>
<rect x="1" y="1" width="${W - 2}" height="${H - 2}" rx="20" fill="${BG}" stroke="${LINE}"/>
<g clip-path="url(#frame)"><rect width="${W}" height="${H}" fill="url(#grid)"/>
<text x="44" y="46" font-size="12" fill="${DIM}" letter-spacing="2">RIGHT NOW · POLAND TIME</text>
<circle cx="${W - 44}" cy="42" r="4" fill="${LIME}" filter="url(#glow)" opacity="0"><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>
<path d="M${ax - ar} ${ay} A${ar} ${ar} 0 0 1 ${ax + ar} ${ay}" fill="none" stroke="${LINE}" stroke-width="2" stroke-dasharray="3 6"/>
<line x1="${ax - ar - 14}" y1="${ay}" x2="${ax + ar + 14}" y2="${ay}" stroke="${LINE}"/>${body}
${clock}${secBar}
<text x="${ax}" y="${ay + 92}" font-size="12" text-anchor="middle" fill="${DIM}">${part} in Poland · live</text>
<line x1="400" y1="30" x2="400" y2="${H - 30}" stroke="${LINE}"/><line x1="770" y1="30" x2="770" y2="${H - 30}" stroke="${LINE}"/>
<text x="440" y="46" font-size="12" fill="${DIM}" letter-spacing="2">BUILDING</text>
<text x="440" y="96" font-size="26" font-weight="700" fill="${TEXT}">A blockchain from</text>
<text x="440" y="130" font-size="26" font-weight="700" fill="${LIME}" filter="url(#glow)">scratch, in Rust.</text>
<text x="440" y="162" font-size="13" fill="${DIM}">and a coin to live on it. Consensus is next.</text>
<rect x="440" y="186" width="300" height="4" rx="2" fill="${LINE}"/>
<rect x="440" y="186" width="0" height="4" rx="2" fill="${LIME}" filter="url(#glow)"><animate attributeName="width" values="0;180;180" keyTimes="0;.8;1" dur="6s" repeatCount="indefinite"/></rect>
<text x="440" y="214" font-size="12" fill="${DIM}">3 of 7 milestones done</text>
<text x="800" y="46" font-size="12" fill="${DIM}" letter-spacing="2">LEARNING THIS MONTH</text>${chips}
</g></svg>`;
}

module.exports = (req, res) => {
  res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
  // no caching anywhere: GitHub's image proxy then refetches on each view
  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");
  res.statusCode = 200;
  res.end(render());
};
