// ═══════════════════════════════════════
// JARVIX — Animation Utilities
// ═══════════════════════════════════════

/**
 * Count-up animation for portfolio/price numbers
 * @param el   - DOM element to update
 * @param target - final number (string like "100000" or "1997.95")
 * @param prefix - currency prefix e.g. "$"
 * @param duration - ms, default 1600
 */
export function countUp(
  el: HTMLElement,
  target: string,
  prefix = '$',
  duration = 1600
) {
  const num = parseFloat(target.replace(/[^0-9.]/g, ''))
  const dec = target.includes('.') ? 2 : 0
  const start = Date.now()

  const run = () => {
    const progress = Math.min((Date.now() - start) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // cubic ease-out
    el.textContent =
      prefix +
      (num * eased).toLocaleString('en-US', {
        minimumFractionDigits: dec,
        maximumFractionDigits: dec,
      })
    if (progress < 1) requestAnimationFrame(run)
  }
  requestAnimationFrame(run)
}

/**
 * Fill progress/diagnostic bars via data-w attribute
 * @param delay - ms before starting
 * @param stagger - ms between each bar
 */
export function fillBars(delay = 700, stagger = 200) {
  setTimeout(() => {
    const miniBars = document.querySelectorAll<HTMLElement>('.mini-bar-fill')
    miniBars.forEach((b) => {
      b.style.width = (b.dataset.w ?? '0') + '%'
    })

    const diagFills = document.querySelectorAll<HTMLElement>('.diag-fill')
    diagFills.forEach((b, i) => {
      setTimeout(() => {
        b.style.width = (b.dataset.w ?? '0') + '%'
      }, i * stagger)
    })
  }, delay)
}

/**
 * Flash the arc reactor core on command transmit
 */
export function arcFlash() {
  const core = document.querySelector<HTMLElement>('.arc-core')
  if (!core) return
  core.style.boxShadow =
    'inset 0 0 80px #00d4ff66, 0 0 80px #00d4ffaa, 0 0 160px #00d4ff55'
  setTimeout(() => {
    core.style.boxShadow = ''
  }, 600)
}

/**
 * Set pulse ring speed based on market volatility
 * @param volatility - 0 (calm) to 1 (extreme)
 */
export function setPulseSpeed(volatility: number) {
  const duration = 5 - volatility * 3 // 2s – 5s
  document.querySelectorAll<HTMLElement>('.pulse-ring').forEach((r) => {
    r.style.animationDuration = duration + 's'
  })
}

/**
 * Set pulse ring color based on market sentiment
 * @param sentiment - 0 (bearish) to 1 (bullish)
 */
export function setPulseColor(sentiment: number) {
  const color =
    sentiment > 0.6 ? '#00ff88' : sentiment < 0.4 ? '#ff3355' : '#00d4ff'
  document.querySelectorAll<HTMLElement>('.pulse-ring').forEach((r) => {
    r.style.borderColor = color
  })
}

/**
 * Generate tick marks for arc SVG
 * @param svgEl - the <g> element inside SVG
 */
export function generateTicks(svgEl: SVGGElement) {
  const ns = 'http://www.w3.org/2000/svg'
  for (let i = 0; i < 60; i++) {
    const angle = (i / 60) * 360
    const rad = (angle * Math.PI) / 180
    const cx = 124, cy = 124, r = 118
    const len = i % 5 === 0 ? 10 : 5
    const x1 = cx + (r - len) * Math.sin(rad)
    const y1 = cy - (r - len) * Math.cos(rad)
    const x2 = cx + r * Math.sin(rad)
    const y2 = cy - r * Math.cos(rad)
    const line = document.createElementNS(ns, 'line')
    line.setAttribute('x1', String(x1))
    line.setAttribute('y1', String(y1))
    line.setAttribute('x2', String(x2))
    line.setAttribute('y2', String(y2))
    line.setAttribute('stroke', i % 5 === 0 ? '#006688' : '#003344')
    line.setAttribute('stroke-width', i % 5 === 0 ? '1.5' : '0.8')
    svgEl.appendChild(line)
  }
}

/**
 * Spawn floating particles into container
 * @param container - DOM element to append particles to
 * @param count - number of particles (default 18)
 */
export function spawnParticles(container: HTMLElement, count = 18) {
  for (let i = 0; i < count; i++) {
    const p = document.createElement('div')
    p.className = 'particle'
    p.style.cssText = `
      left: ${Math.random() * 100}%;
      width: ${Math.random() > 0.7 ? 3 : 2}px;
      height: ${Math.random() > 0.7 ? 3 : 2}px;
      animation-duration: ${8 + Math.random() * 12}s;
      animation-delay: ${Math.random() * 10}s;
    `
    container.appendChild(p)
  }
}
