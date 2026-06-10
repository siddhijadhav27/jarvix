'use client'

import { useEffect, useRef } from 'react'

export default function ArcReactor3D() {
  const tickRef = useRef<SVGGElement>(null)

  useEffect(() => {
    // Generate tick marks
    const tickG = tickRef.current
    if (!tickG) return

    tickG.innerHTML = ''
    const cx = 124, cy = 124, r = 118

    for (let i = 0; i < 60; i++) {
      const angle = (i / 60) * 360
      const rad = angle * Math.PI / 180
      const len = i % 5 === 0 ? 10 : 5
      const x1 = cx + (r - len) * Math.sin(rad)
      const y1 = cy - (r - len) * Math.cos(rad)
      const x2 = cx + r * Math.sin(rad)
      const y2 = cy - r * Math.cos(rad)

      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
      line.setAttribute('x1', String(x1))
      line.setAttribute('y1', String(y1))
      line.setAttribute('x2', String(x2))
      line.setAttribute('y2', String(y2))
      line.setAttribute('stroke', i % 5 === 0 ? '#006688' : '#003344')
      line.setAttribute('stroke-width', i % 5 === 0 ? '1.5' : '0.8')
      tickG.appendChild(line)
    }
  }, [])

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '340px',
          height: '340px',
          position: 'relative',
        }}
      >
        {/* === PULSE RINGS (Emanating outward) === */}
        {[0, 1, 2].map((i) => (
          <div
            key={`pulse-${i}`}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              width: '145px',
              height: '145px',
              borderRadius: '50%',
              border: '1px solid #00d4ff',
              transform: 'translate(-50%, -50%)',
              opacity: 0,
              animation: 'pulse-expand 3s ease-out infinite',
              animationDelay: `${i}s`,
            }}
          />
        ))}

        {/* === RING 1: 330px — top+bottom solid, sides transparent === */}
        <div
          style={{
            position: 'absolute',
            top: '5px',
            left: '5px',
            width: '330px',
            height: '330px',
            borderRadius: '50%',
            borderTop: '1px solid #00d4ff',
            borderRight: '1px solid transparent',
            borderBottom: '1px solid #006688',
            borderLeft: '1px solid transparent',
            animation: 'spin 8s linear infinite',
            filter: 'drop-shadow(0 0 4px #00d4ff)',
          }}
        />

        {/* === RING 2: 308px — left+right solid === */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '16px',
            width: '308px',
            height: '308px',
            borderRadius: '50%',
            borderTop: '1px solid transparent',
            borderRight: '1px solid #00a8cc',
            borderBottom: '1px solid transparent',
            borderLeft: '1px solid #00a8cc',
            animation: 'spin 5s linear infinite reverse',
          }}
        />

        {/* === RING 3: 285px — top+bottom accent === */}
        <div
          style={{
            position: 'absolute',
            top: '27px',
            left: '27px',
            width: '285px',
            height: '285px',
            borderRadius: '50%',
            border: '1px solid #003344',
            borderTopColor: '#00d4ff',
            borderBottomColor: '#00d4ff',
            animation: 'spin 12s linear infinite',
          }}
        />

        {/* === RING 4: 265px — dashed ghost ring === */}
        <div
          style={{
            position: 'absolute',
            top: '37px',
            left: '37px',
            width: '265px',
            height: '265px',
            borderRadius: '50%',
            border: '1px dashed #003344',
            animation: 'spin 20s linear infinite reverse',
          }}
        />

        {/* === SVG TICK MARKS === */}
        <svg
          width="248"
          height="248"
          viewBox="0 0 248 248"
          style={{
            position: 'absolute',
            top: '46px',
            left: '46px',
          }}
        >
          <g ref={tickRef} />
        </svg>

        {/* === INNER RING 1: 220px — solid with inner glow === */}
        <div
          style={{
            position: 'absolute',
            top: '60px',
            left: '60px',
            width: '220px',
            height: '220px',
            borderRadius: '50%',
            border: '1px solid #006688',
            boxShadow: 'inset 0 0 20px #00d4ff11',
          }}
        />

        {/* === INNER RING 2: 185px — border + dark fill === */}
        <div
          style={{
            position: 'absolute',
            top: '77px',
            left: '77px',
            width: '185px',
            height: '185px',
            borderRadius: '50%',
            border: '1px solid #003344',
            background: 'radial-gradient(circle, #001520 0%, transparent 70%)',
          }}
        />

        {/* === GLOWING CORE === */}
        <div
          style={{
            position: 'absolute',
            top: '97px',
            left: '97px',
            width: '145px',
            height: '145px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, #003a4e 0%, #001a28 40%, #000810 70%, transparent 100%)',
            border: '1px solid #006688',
            animation: 'core-breathe 3s ease-in-out infinite',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* HEXAGON SVG */}
          <svg
            width="80"
            height="80"
            viewBox="0 0 80 80"
            style={{
              position: 'absolute',
            }}
          >
            {/* Outer hexagon */}
            <polygon
              points="40,2 74,21 74,59 40,78 6,59 6,21"
              fill="none"
              stroke="#00d4ff"
              strokeWidth="1"
              opacity="0.6"
            />
            {/* Inner hexagon */}
            <polygon
              points="40,10 66,25 66,55 40,70 14,55 14,25"
              fill="none"
              stroke="#006688"
              strokeWidth="0.5"
              opacity="0.4"
            />
          </svg>

          {/* JARVIX TEXT */}
          <div
            style={{
              position: 'absolute',
              inset: '0',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#00d4ff',
                fontSize: '18px',
                fontWeight: 900,
                letterSpacing: '4px',
                fontFamily: 'monospace',
                textShadow: '0 0 15px rgba(0,212,255,0.8)',
                transform: 'scaleX(1.6)',
                display: 'inline-block',
                transformOrigin: 'center',
                paddingLeft: '3px',
              }}
            >
              JARVIX
            </span>
            <span
              style={{
                color: 'rgba(0,212,255,0.6)',
                fontSize: '7px',
                letterSpacing: '2px',
                marginTop: '2px',
                fontFamily: 'monospace',
              }}
            >
              AI AGENT
            </span>
          </div>
        </div>

        {/* === DATA POINTS (Cardinal positions) === */}
        {/* TOP - BTC */}
        <div
          style={{
            position: 'absolute',
            top: '-35px',
            left: '50%',
            transform: 'translateX(-50%)',
            textAlign: 'center',
            fontFamily: 'monospace',
          }}
        >
          <span
            style={{
              color: '#00d4ff',
              fontSize: '11px',
              display: 'block',
              marginBottom: '2px',
              textShadow: '0 0 6px #00d4ff',
            }}
          >
            $73,085
          </span>
          <span
            style={{
              color: '#006688',
              fontSize: '9px',
              letterSpacing: '0.1em',
            }}
          >
            BTC
          </span>
        </div>

        {/* RIGHT - ETH */}
        <div
          style={{
            position: 'absolute',
            right: '-55px',
            top: '50%',
            transform: 'translateY(-50%)',
            textAlign: 'center',
            fontFamily: 'monospace',
          }}
        >
          <span
            style={{
              color: '#00d4ff',
              fontSize: '11px',
              display: 'block',
              marginBottom: '2px',
              textShadow: '0 0 6px #00d4ff',
            }}
          >
            $1,997
          </span>
          <span
            style={{
              color: '#006688',
              fontSize: '9px',
              letterSpacing: '0.1em',
            }}
          >
            ETH
          </span>
        </div>

        {/* BOTTOM - PORTFOLIO */}
        <div
          style={{
            position: 'absolute',
            bottom: '-35px',
            left: '50%',
            transform: 'translateX(-50%)',
            textAlign: 'center',
            fontFamily: 'monospace',
          }}
        >
          <span
            style={{
              color: '#00d4ff',
              fontSize: '11px',
              display: 'block',
              marginBottom: '2px',
              textShadow: '0 0 6px #00d4ff',
            }}
          >
            $311,342
          </span>
          <span
            style={{
              color: '#006688',
              fontSize: '9px',
              letterSpacing: '0.1em',
            }}
          >
            PORTFOLIO
          </span>
        </div>

        {/* LEFT - SOL */}
        <div
          style={{
            position: 'absolute',
            left: '-55px',
            top: '50%',
            transform: 'translateY(-50%)',
            textAlign: 'center',
            fontFamily: 'monospace',
          }}
        >
          <span
            style={{
              color: '#00d4ff',
              fontSize: '11px',
              display: 'block',
              marginBottom: '2px',
              textShadow: '0 0 6px #00d4ff',
            }}
          >
            $152.40
          </span>
          <span
            style={{
              color: '#006688',
              fontSize: '9px',
              letterSpacing: '0.1em',
            }}
          >
            SOL
          </span>
        </div>
      </div>
    </div>
  )
}
