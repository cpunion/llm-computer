import React from 'react';
import {AbsoluteFill} from 'remotion';
import {articleData} from './generated-data';

const palette = {
  ink: '#0f172a',
  subInk: '#334155',
  muted: '#64748b',
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

const modeColor = {
  reference: palette.teal,
  append_only_naive: palette.warm,
  append_only_hull: palette.blue,
  transformer_hull: palette.violet,
};

const modeShort = {
  reference: 'Reference',
  append_only_naive: 'Naive',
  append_only_hull: 'Hull',
  transformer_hull: 'Xfmr Hull',
};

const textFont = 'Avenir Next, Trebuchet MS, sans-serif';
const monoFont = 'JetBrains Mono, Menlo, monospace';

const formatLatency = (seconds) => {
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)} ms`;
  }

  return `${seconds.toFixed(2)} s`;
};

const cardStyle = {
  backgroundColor: 'rgba(255, 253, 248, 0.94)',
  border: `2px solid ${palette.line}`,
  borderRadius: 28,
  boxShadow: '0 18px 44px rgba(15, 23, 42, 0.08)',
  boxSizing: 'border-box',
};

const Background = () => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at top left, rgba(249, 115, 22, 0.12), transparent 28%), radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.12), transparent 34%), ${palette.cream}`,
      }}
    >
      {Array.from({length: 24}).map((_, index) => (
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
      {Array.from({length: 18}).map((_, index) => (
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

const FigureShell = ({eyebrow, title, subtitle, children}) => {
  return (
    <AbsoluteFill>
      <Background />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          padding: '64px 72px',
          boxSizing: 'border-box',
          fontFamily: textFont,
        }}
      >
        <div
          style={{
            fontSize: 18,
            letterSpacing: 4,
            textTransform: 'uppercase',
            color: palette.teal,
            fontWeight: 700,
            marginBottom: 12,
          }}
        >
          {eyebrow}
        </div>
        <div
          style={{
            fontSize: 54,
            lineHeight: 1.04,
            color: palette.ink,
            fontWeight: 700,
            maxWidth: 980,
          }}
        >
          {title}
        </div>
        <div
          style={{
            marginTop: 16,
            maxWidth: 1120,
            fontSize: 24,
            lineHeight: 1.35,
            color: palette.subInk,
          }}
        >
          {subtitle}
        </div>
        <div style={{marginTop: 38}}>{children}</div>
      </div>
    </AbsoluteFill>
  );
};

const LabelPill = ({children, color = palette.line, textColor = palette.ink}) => {
  return (
    <div
      style={{
        padding: '8px 14px',
        borderRadius: 999,
        backgroundColor: color,
        color: textColor,
        fontSize: 16,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </div>
  );
};

export const ImplementationLadderFigure = () => {
  return (
    <FigureShell
      eyebrow="Implementation Ladder"
      title="Five Ways We Moved Execution Closer to the Model"
      subtitle="Ordered by execution depth rather than by raw speed. Every layer keeps the same WASM contract, but it moves the execution boundary inward."
    >
      <div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
        {articleData.methods.map((method) => {
          const color = categoryColor[method.category];
          return (
            <div
              key={method.method_id}
              style={{
                ...cardStyle,
                padding: '24px 28px',
                borderColor: color,
                backgroundColor: 'rgba(255, 255, 255, 0.92)',
              }}
            >
              <div style={{display: 'flex', gap: 20, alignItems: 'flex-start'}}>
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 26,
                    backgroundColor: color,
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 28,
                    fontWeight: 700,
                    fontFamily: monoFont,
                    flex: '0 0 auto',
                    marginTop: 2,
                  }}
                >
                  {method.depth_rank}
                </div>
                <div style={{display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0}}>
                  <div
                    style={{
                      fontSize: 34,
                      lineHeight: 1.1,
                      fontWeight: 700,
                      color: palette.ink,
                    }}
                  >
                    {method.title}
                  </div>
                  <div
                    style={{
                      fontSize: 22,
                      lineHeight: 1.35,
                      color: palette.subInk,
                    }}
                  >
                    {method.depth_caption}
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      gap: 10,
                      alignItems: 'flex-start',
                      flexWrap: 'wrap',
                    }}
                  >
                    <LabelPill color={color} textColor="#fff">
                      Boundary
                    </LabelPill>
                    <div
                      style={{
                        fontFamily: monoFont,
                        fontSize: 18,
                        lineHeight: 1.45,
                        color: palette.ink,
                        flex: 1,
                        minWidth: 0,
                        overflowWrap: 'anywhere',
                      }}
                    >
                      {method.execution_boundary}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </FigureShell>
  );
};

export const ExecutionBoundariesFigure = () => {
  const nodes = ['Prompt', 'Model', 'Runtime', 'Executor', 'Answer'];

  return (
    <FigureShell
      eyebrow="Runtime Boundaries"
      title="Where Execution Actually Happens"
      subtitle="The same final answer can arrive through very different ownership boundaries. This view keeps the explanation in normal web layout so long labels wrap instead of spilling out."
    >
      <div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
        {articleData.methods.map((method) => {
          const color = categoryColor[method.category];
          return (
            <div
              key={method.method_id}
              style={{
                ...cardStyle,
                padding: '24px 28px',
                backgroundColor: 'rgba(255, 255, 255, 0.92)',
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '420px minmax(0, 1fr)',
                  gap: 24,
                  alignItems: 'start',
                }}
              >
                <div style={{minWidth: 0}}>
                  <div
                    style={{
                      fontSize: 32,
                      lineHeight: 1.1,
                      fontWeight: 700,
                      color: palette.ink,
                    }}
                  >
                    {method.title}
                  </div>
                  <div
                    style={{
                      marginTop: 10,
                      fontSize: 19,
                      lineHeight: 1.42,
                      color: palette.subInk,
                    }}
                  >
                    {method.execution_boundary}
                  </div>
                </div>
                <div style={{display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0}}>
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: 10,
                    }}
                  >
                    {nodes.map((label, index) => {
                      let fill = '#e2e8f0';
                      let textColor = palette.ink;
                      if (label === 'Executor') {
                        fill = color;
                        textColor = '#fff';
                      } else if (method.category === 'closed_source' && label === 'Model') {
                        fill = '#ccfbf1';
                      } else if (method.category === 'open_source' && label === 'Model') {
                        fill = '#dbeafe';
                      } else if (method.category === 'direct' && (label === 'Prompt' || label === 'Model')) {
                        fill = '#f1f5f9';
                      }
                      return (
                        <React.Fragment key={`${method.method_id}-${label}`}>
                          <div
                            style={{
                              padding: '10px 16px',
                              borderRadius: 18,
                              backgroundColor: fill,
                              color: textColor,
                              fontSize: 18,
                              fontWeight: 700,
                            }}
                          >
                            {label}
                          </div>
                          {index < nodes.length - 1 ? (
                            <div style={{fontSize: 24, color: palette.muted, marginTop: -2}}>→</div>
                          ) : null}
                        </React.Fragment>
                      );
                    })}
                  </div>
                  <div
                    style={{
                      ...cardStyle,
                      padding: '16px 18px',
                      borderRadius: 20,
                      borderColor: color,
                      backgroundColor: 'rgba(255,255,255,0.84)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 15,
                        letterSpacing: 2,
                        textTransform: 'uppercase',
                        color: color,
                        fontWeight: 700,
                        marginBottom: 8,
                      }}
                    >
                      Runtime signal
                    </div>
                    <div
                      style={{
                        fontFamily: monoFont,
                        fontSize: 17,
                        lineHeight: 1.45,
                        color: palette.ink,
                        overflowWrap: 'anywhere',
                      }}
                    >
                      {String(method.comparison.notes)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </FigureShell>
  );
};

export const LatencyFigure = () => {
  const methods = articleData.methods;
  const maxLatency = Math.max(...methods.map((method) => method.comparison.end_to_end_s));
  const minLatency = Math.min(...methods.map((method) => method.comparison.end_to_end_s));
  const maxLog = Math.log10(maxLatency);
  const minLog = Math.log10(minLatency);

  return (
    <FigureShell
      eyebrow="Latency"
      title="Latency on the Canonical 6 × 7 Scenario"
      subtitle="End-to-end time from the recorded five-way comparison. The bars are log-scaled and capped inside a fixed web-layout frame, so the slowest row cannot spill out of the image."
    >
      <div style={{display: 'flex', flexDirection: 'column', gap: 16}}>
        {methods.map((method) => {
          const elapsed = method.comparison.end_to_end_s;
          const normalized =
            maxLog === minLog ? 0 : (Math.log10(elapsed) - minLog) / (maxLog - minLog);
          const widthPercent = 18 + normalized * 82;
          const color = categoryColor[method.category];

          return (
            <div
              key={method.method_id}
              style={{
                ...cardStyle,
                padding: '20px 24px',
                backgroundColor: 'rgba(255,255,255,0.92)',
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '250px minmax(0, 1fr)',
                  gap: 22,
                  alignItems: 'center',
                }}
              >
                <div style={{minWidth: 0}}>
                  <div
                    style={{
                      fontSize: 28,
                      lineHeight: 1.1,
                      fontWeight: 700,
                      color: palette.ink,
                    }}
                  >
                    {method.short_label}
                  </div>
                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 16,
                      lineHeight: 1.4,
                      color: palette.subInk,
                    }}
                  >
                    {method.category.replace('_', ' ')}
                  </div>
                </div>
                <div style={{display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0}}>
                  <div
                    style={{
                      width: '100%',
                      height: 42,
                      borderRadius: 18,
                      backgroundColor: '#e2e8f0',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${widthPercent}%`,
                        minWidth: 140,
                        maxWidth: '100%',
                        height: '100%',
                        borderRadius: 18,
                        backgroundColor: color,
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0 16px',
                        boxSizing: 'border-box',
                        color: '#fff',
                        fontFamily: monoFont,
                        fontWeight: 700,
                        fontSize: 18,
                      }}
                    >
                      {formatLatency(elapsed)}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: 17,
                      lineHeight: 1.4,
                      color: palette.subInk,
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {String(method.comparison.notes)}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </FigureShell>
  );
};

export const ArticleExamplesFigure = () => {
  const report = articleData.articleExamples;
  const hungarianRows = report.results.filter((row) => row.example_id === 'hungarian_10x10');
  const sudokuRow = report.results.find((row) => row.example_id === 'sudoku_checksum');
  const maxElapsed = Math.max(...hungarianRows.map((row) => row.elapsed_s));

  return (
    <FigureShell
      eyebrow="Article Examples"
      title="Hungarian and Sudoku in the Same Repository"
      subtitle="The repository now validates the examples shown in the Percepta article, not just toy arithmetic and small helper modules."
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 22,
          alignItems: 'stretch',
        }}
      >
        <div style={{...cardStyle, padding: '24px 26px', backgroundColor: 'rgba(255,255,255,0.92)'}}>
          <div style={{fontSize: 34, fontWeight: 700, color: palette.ink, marginBottom: 18}}>
            Hungarian 10×10
          </div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
            {hungarianRows.map((row) => {
              const widthPercent = (row.elapsed_s / maxElapsed) * 100;
              const color = modeColor[row.mode];
              return (
                <div key={row.mode} style={{display: 'flex', flexDirection: 'column', gap: 8}}>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '170px minmax(0, 1fr)',
                      gap: 16,
                      alignItems: 'center',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 22,
                        fontWeight: 700,
                        color: palette.ink,
                      }}
                    >
                      {modeShort[row.mode]}
                    </div>
                    <div
                      style={{
                        width: '100%',
                        height: 34,
                        borderRadius: 14,
                        backgroundColor: '#e2e8f0',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${Math.max(widthPercent, 12)}%`,
                          maxWidth: '100%',
                          height: '100%',
                          backgroundColor: color,
                          borderRadius: 14,
                          color: '#fff',
                          fontSize: 16,
                          fontWeight: 700,
                          fontFamily: monoFont,
                          display: 'flex',
                          alignItems: 'center',
                          padding: '0 12px',
                          boxSizing: 'border-box',
                        }}
                      >
                        {formatLatency(row.elapsed_s)}
                      </div>
                    </div>
                  </div>
                  <div style={{fontSize: 16, color: palette.subInk, lineHeight: 1.35}}>
                    result={row.result} · steps={row.steps.toLocaleString()} · subset=
                    {row.transformer_subset ? 'yes' : 'no'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div style={{...cardStyle, padding: '24px 26px', backgroundColor: 'rgba(255,255,255,0.92)'}}>
          <div style={{fontSize: 34, fontWeight: 700, color: palette.ink, marginBottom: 18}}>
            Sudoku
          </div>
          <div style={{display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 18}}>
            <LabelPill color={palette.teal} textColor="#fff">
              checksum {sudokuRow.result}
            </LabelPill>
            <LabelPill color={palette.blue} textColor="#fff">
              {sudokuRow.steps.toLocaleString()} steps
            </LabelPill>
            <LabelPill color={palette.warm} textColor="#fff">
              {formatLatency(sudokuRow.elapsed_s)}
            </LabelPill>
          </div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 14}}>
            <div
              style={{
                ...cardStyle,
                padding: '16px 18px',
                borderRadius: 20,
                backgroundColor: 'rgba(255,255,255,0.78)',
              }}
            >
              <div style={{fontSize: 15, letterSpacing: 2, textTransform: 'uppercase', color: palette.muted, fontWeight: 700}}>
                Puzzle
              </div>
              <div
                style={{
                  marginTop: 8,
                  fontFamily: monoFont,
                  fontSize: 17,
                  lineHeight: 1.45,
                  color: palette.ink,
                  overflowWrap: 'anywhere',
                }}
              >
                {report.sudoku_puzzle}
              </div>
            </div>
            <div
              style={{
                ...cardStyle,
                padding: '16px 18px',
                borderRadius: 20,
                backgroundColor: 'rgba(255,255,255,0.78)',
              }}
            >
              <div style={{fontSize: 15, letterSpacing: 2, textTransform: 'uppercase', color: palette.muted, fontWeight: 700}}>
                Why it matters
              </div>
              <div
                style={{
                  marginTop: 8,
                  fontSize: 19,
                  lineHeight: 1.45,
                  color: palette.subInk,
                }}
              >
                The long Sudoku example exists inside the same opcode subset used by the tiny transformer-style verifier, which keeps the article comparison grounded in one executable semantics layer.
              </div>
            </div>
          </div>
        </div>
      </div>
    </FigureShell>
  );
};

export const SudokuPrefixFigure = () => {
  const report = articleData.sudokuReport;
  const rows = report.prefix_results.filter((row) => row.mode !== 'reference');
  const budgets = [...new Set(rows.map((row) => row.budget))].sort((a, b) => a - b);
  const modes = ['append_only_naive', 'append_only_hull', 'transformer_hull'];
  const maxElapsed = Math.max(...rows.map((row) => row.elapsed_s));

  return (
    <FigureShell
      eyebrow="Sudoku Validation"
      title="Sudoku Prefix Validation Frontier"
      subtitle="Before preserving a full 22M-step run for every backend, the repository records exact prefix-state agreement at increasing budgets. Short labels and a separate legend prevent bar captions from colliding."
    >
      <div style={{display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 22}}>
        {modes.map((mode) => (
          <LabelPill key={mode} color={modeColor[mode]} textColor="#fff">
            {modeShort[mode]}
          </LabelPill>
        ))}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 20,
          alignItems: 'stretch',
        }}
      >
        {budgets.map((budget) => (
          <div
            key={budget}
            style={{
              ...cardStyle,
              padding: '22px 20px 18px',
              backgroundColor: 'rgba(255,255,255,0.92)',
            }}
          >
            <div
              style={{
                textAlign: 'center',
                fontFamily: monoFont,
                fontSize: 30,
                fontWeight: 700,
                color: palette.ink,
                marginBottom: 18,
              }}
            >
              {budget.toLocaleString()} steps
            </div>
            <div
              style={{
                height: 360,
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'space-around',
                gap: 16,
                padding: '0 10px',
              }}
            >
              {modes.map((mode) => {
                const row = rows.find((entry) => entry.mode === mode && entry.budget === budget);
                if (!row) {
                  return null;
                }
                const barHeight = Math.max(28, (row.elapsed_s / maxElapsed) * 290);
                return (
                  <div
                    key={`${budget}-${mode}`}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'flex-end',
                      height: '100%',
                      flex: 1,
                      minWidth: 0,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: monoFont,
                        fontSize: 14,
                        color: palette.subInk,
                        marginBottom: 10,
                      }}
                    >
                      {formatLatency(row.elapsed_s)}
                    </div>
                    <div
                      style={{
                        width: '100%',
                        maxWidth: 88,
                        height: barHeight,
                        borderRadius: 18,
                        backgroundColor: modeColor[mode],
                      }}
                    />
                    <div
                      style={{
                        marginTop: 12,
                        fontSize: 16,
                        lineHeight: 1.25,
                        textAlign: 'center',
                        color: palette.ink,
                        fontWeight: 700,
                        minHeight: 40,
                      }}
                    >
                      {modeShort[mode]}
                    </div>
                    <div
                      style={{
                        marginTop: 6,
                        fontSize: 16,
                        color: row.matches_reference ? palette.teal : palette.warm,
                        fontWeight: 700,
                      }}
                    >
                      {row.matches_reference ? 'matches' : 'differs'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div
        style={{
          marginTop: 20,
          fontSize: 18,
          lineHeight: 1.4,
          color: palette.subInk,
        }}
      >
        All recorded rows match the reference snapshot. The default validation stage intentionally caps the append-only naive backend at 10,000 steps because it is preserved as a correctness baseline rather than a long-run path.
      </div>
    </FigureShell>
  );
};

export const ValidationMatrixFigure = () => {
  const columns = [
    ['Toy', '42'],
    ['Real', 'Model'],
    ['Article', 'Hungarian'],
    ['Sudoku', 'Full'],
    ['Sudoku', 'Prefix'],
    ['Structured', 'Capture'],
    ['Native', 'Block'],
    ['Tool', 'Call'],
  ];

  return (
    <FigureShell
      eyebrow="Validation"
      title="Validation Matrix"
      subtitle="This matrix tracks what each implementation has actually demonstrated. It uses a regular grid layout with explicit padding, so the top row no longer collides with the rounded frame."
    >
      <div
        style={{
          ...cardStyle,
          padding: '24px 24px 18px',
          backgroundColor: 'rgba(255,255,255,0.94)',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '280px repeat(8, minmax(92px, 1fr))',
            gap: 10,
            alignItems: 'stretch',
          }}
        >
          <div
            style={{
              padding: '14px 16px',
              fontSize: 22,
              fontWeight: 700,
              color: palette.ink,
              display: 'flex',
              alignItems: 'center',
            }}
          >
            Implementation
          </div>
          {columns.map(([line1, line2]) => (
            <div
              key={`${line1}-${line2}`}
              style={{
                padding: '10px 8px',
                borderRadius: 18,
                backgroundColor: '#f8fafc',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                textAlign: 'center',
                color: palette.ink,
                fontWeight: 700,
                lineHeight: 1.15,
                minHeight: 60,
              }}
            >
              <div style={{fontSize: 15}}>{line1}</div>
              <div style={{fontSize: 15}}>{line2}</div>
            </div>
          ))}
          {articleData.methods.map((method, index) => {
            const fill = index % 2 === 0 ? 'rgba(255,247,237,0.85)' : 'rgba(255,255,255,0.75)';
            const cells = [
              method.validation_flags.toy_scenario,
              method.validation_flags.real_model,
              method.validation_flags.article_hungarian,
              method.validation_flags.sudoku_full,
              method.validation_flags.sudoku_prefix,
              method.validation_flags.structured_capture,
              method.validation_flags.native_block,
              method.validation_flags.tool_call,
            ];

            return (
              <React.Fragment key={method.method_id}>
                <div
                  style={{
                    padding: '18px 16px',
                    borderRadius: 20,
                    backgroundColor: fill,
                    fontSize: 22,
                    lineHeight: 1.2,
                    fontWeight: 700,
                    color: palette.ink,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  {method.title}
                </div>
                {cells.map((enabled, cellIndex) => (
                  <div
                    key={`${method.method_id}-${cellIndex}`}
                    style={{
                      padding: '18px 8px',
                      borderRadius: 20,
                      backgroundColor: fill,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 30,
                      fontWeight: 700,
                      color: enabled ? palette.teal : '#94a3b8',
                    }}
                  >
                    {enabled ? '✓' : '–'}
                  </div>
                ))}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </FigureShell>
  );
};
