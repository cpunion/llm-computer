import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {articleData} from './generated-data';

const palette = {
  ink: '#0f172a',
  subInk: '#334155',
  warm: '#f97316',
  amber: '#f59e0b',
  blue: '#2563eb',
  teal: '#0f766e',
  violet: '#7c3aed',
  cream: '#f7f2e8',
  paper: '#fffdf8',
  line: '#cbd5e1',
  grid: 'rgba(15, 23, 42, 0.06)',
};

const categoryColor = {
  direct: palette.warm,
  open_source: palette.blue,
  closed_source: palette.teal,
};

const formatLatency = (seconds) => {
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)} ms`;
  }

  return `${seconds.toFixed(2)} s`;
};

const Background = () => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at top left, rgba(249, 115, 22, 0.12), transparent 28%), radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.12), transparent 34%), ${palette.cream}`,
      }}
    >
      {Array.from({length: 20}).map((_, index) => (
        <div
          key={index}
          style={{
            position: 'absolute',
            left: 56 + index * 60,
            top: 0,
            width: 1,
            height: '100%',
            backgroundColor: palette.grid,
          }}
        />
      ))}
      {Array.from({length: 12}).map((_, index) => (
        <div
          key={`h-${index}`}
          style={{
            position: 'absolute',
            left: 0,
            top: 48 + index * 56,
            width: '100%',
            height: 1,
            backgroundColor: palette.grid,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

const TitleBlock = ({frame}) => {
  const titleProgress = spring({
    fps: 30,
    frame,
    config: {
      damping: 18,
      stiffness: 140,
    },
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        top: 40,
        transform: `translateY(${interpolate(titleProgress, [0, 1], [18, 0])}px)`,
        opacity: titleProgress,
      }}
    >
      <div
        style={{
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
          fontSize: 16,
          letterSpacing: 4,
          textTransform: 'uppercase',
          color: palette.teal,
          fontWeight: 700,
          marginBottom: 10,
        }}
      >
        LLM Computer Ladder
      </div>
      <div
        style={{
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
          fontSize: 46,
          lineHeight: 1.02,
          color: palette.ink,
          fontWeight: 700,
          maxWidth: 680,
        }}
      >
        Five execution layers,
        <br />
        one shared WASM contract
      </div>
      <div
        style={{
          marginTop: 14,
          maxWidth: 700,
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
          fontSize: 18,
          lineHeight: 1.32,
          color: palette.subInk,
        }}
      >
        From a pure reference interpreter to a native open-source execution block.
      </div>
    </div>
  );
};

const LadderCard = ({method, index, frame}) => {
  const progress = spring({
    fps: 30,
    frame: frame - index * 16,
    config: {
      damping: 18,
      stiffness: 160,
      mass: 0.7,
    },
  });
  const color = categoryColor[method.category];
  const y = 210 + index * 66;
  const scale = interpolate(progress, [0, 1], [0.95, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opacity = interpolate(progress, [0, 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        top: y,
        width: 620,
        height: 58,
        borderRadius: 18,
        backgroundColor: 'rgba(255,255,255,0.88)',
        border: `2px solid ${color}`,
        boxShadow: '0 18px 44px rgba(15, 23, 42, 0.08)',
        transform: `translateY(${interpolate(progress, [0, 1], [24, 0])}px) scale(${scale})`,
        opacity,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 18,
          top: 11,
          width: 34,
          height: 34,
          borderRadius: 17,
          backgroundColor: color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: 20,
          fontWeight: 700,
          fontFamily: 'JetBrains Mono, Menlo, monospace',
        }}
      >
        {method.depth_rank}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 66,
          top: 10,
          fontSize: 22,
          fontWeight: 700,
          color: palette.ink,
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
        }}
      >
        {method.title}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 66,
          top: 34,
          right: 18,
          fontSize: 12,
          color: palette.subInk,
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
        }}
      >
        {method.depth_caption}
      </div>
    </div>
  );
};

const LatencyPanel = ({frame}) => {
  const methods = articleData.methods;
  const maxLatency = Math.max(...methods.map((method) => method.comparison.end_to_end_s));
  const panelProgress = spring({
    fps: 30,
    frame: frame - 52,
    config: {damping: 20, stiffness: 120},
  });

  return (
    <div
      style={{
        position: 'absolute',
        right: 72,
        top: 210,
        width: 486,
        height: 320,
        borderRadius: 24,
        backgroundColor: 'rgba(255,255,255,0.92)',
        border: `2px solid ${palette.line}`,
        boxShadow: '0 18px 44px rgba(15, 23, 42, 0.08)',
        opacity: panelProgress,
        transform: `translateY(${interpolate(panelProgress, [0, 1], [28, 0])}px)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 28,
          top: 22,
          fontSize: 24,
          fontWeight: 700,
          color: palette.ink,
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
        }}
      >
        Canonical latency
      </div>
      <div
        style={{
          position: 'absolute',
          left: 28,
          top: 52,
          fontSize: 14,
          color: palette.subInk,
          fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
        }}
      >
        Same final value, very different execution boundaries.
      </div>
      {methods.map((method, index) => {
        const rowY = 100 + index * 44;
        const appear = spring({
          fps: 30,
          frame: frame - 88 - index * 8,
          config: {damping: 18, stiffness: 160},
        });
        const width = interpolate(
          appear,
          [0, 1],
          [0, 280 * (method.comparison.end_to_end_s / maxLatency)],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
        );
        const color = categoryColor[method.category];

        return (
          <React.Fragment key={method.method_id}>
            <div
              style={{
                position: 'absolute',
                left: 28,
                top: rowY,
                fontSize: 16,
                color: palette.ink,
                fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
                fontWeight: 700,
              }}
            >
              {method.short_label}
            </div>
            <div
              style={{
                position: 'absolute',
                left: 180,
                top: rowY - 4,
                width,
                height: 24,
                borderRadius: 12,
                backgroundColor: color,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: 190,
                top: rowY - 1,
                fontSize: 12,
                color: 'white',
                fontFamily: 'JetBrains Mono, Menlo, monospace',
                fontWeight: 700,
                opacity: appear,
              }}
            >
              {formatLatency(method.comparison.end_to_end_s)}
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

const CoveragePanel = ({frame}) => {
  const appear = spring({
    fps: 30,
    frame: frame - 180,
    config: {damping: 16, stiffness: 110},
  });
  const badges = [
    ['Hungarian', '206 across four local backends'],
    ['Sudoku', 'Reference checksum 1276684605'],
    ['Open source', 'Wrapper and execution block both live-validated'],
  ];

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        right: 72,
        bottom: 28,
        height: 108,
        display: 'flex',
        gap: 20,
        opacity: appear,
        transform: `translateY(${interpolate(appear, [0, 1], [20, 0])}px)`,
      }}
    >
      {badges.map(([title, subtitle], index) => (
        <div
          key={title}
          style={{
            flex: 1,
            borderRadius: 24,
            minWidth: 0,
            backgroundColor: palette.paper,
            border: `2px solid ${index === 0 ? palette.warm : index === 1 ? palette.teal : palette.blue}`,
            boxShadow: '0 14px 32px rgba(15, 23, 42, 0.08)',
            padding: '18px 20px',
          }}
        >
          <div
            style={{
              fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
              fontSize: 20,
              fontWeight: 700,
              color: palette.ink,
              marginBottom: 6,
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontFamily: 'Avenir Next, Trebuchet MS, sans-serif',
              fontSize: 15,
              lineHeight: 1.3,
              color: palette.subInk,
            }}
          >
            {subtitle}
          </div>
        </div>
      ))}
    </div>
  );
};

export const FiveImplementationOverview = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const fadeOut = interpolate(frame, [durationInFrames - 30, durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{opacity: fadeOut}}>
      <Background />
      <TitleBlock frame={frame} />
      {articleData.methods.map((method, index) => (
        <LadderCard key={method.method_id} method={method} index={index} frame={frame} />
      ))}
      <LatencyPanel frame={frame} />
      <Sequence from={150}>
        <CoveragePanel frame={frame} />
      </Sequence>
    </AbsoluteFill>
  );
};

export const FiveImplementationPoster = () => {
  return <FiveImplementationOverview />;
};
