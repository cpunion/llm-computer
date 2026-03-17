import React from 'react';
import {Composition} from 'remotion';
import {FiveImplementationOverview, FiveImplementationPoster} from './Overview';
import {
  ArticleExamplesFigure,
  ExecutionBoundariesFigure,
  ImplementationLadderFigure,
  LatencyFigure,
  SudokuPrefixFigure,
  ValidationMatrixFigure,
} from './Figures';

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="five-implementations-overview"
        component={FiveImplementationOverview}
        durationInFrames={360}
        fps={30}
        width={1280}
        height={720}
      />
      <Composition
        id="five-implementations-poster"
        component={FiveImplementationPoster}
        durationInFrames={1}
        fps={30}
        width={1280}
        height={720}
      />
      <Composition
        id="five-implementation-ladder-figure"
        component={ImplementationLadderFigure}
        durationInFrames={1}
        fps={30}
        width={1500}
        height={1480}
      />
      <Composition
        id="five-implementation-paths-figure"
        component={ExecutionBoundariesFigure}
        durationInFrames={1}
        fps={30}
        width={1500}
        height={1480}
      />
      <Composition
        id="five-implementation-latency-figure"
        component={LatencyFigure}
        durationInFrames={1}
        fps={30}
        width={1500}
        height={1180}
      />
      <Composition
        id="article-example-results-figure"
        component={ArticleExamplesFigure}
        durationInFrames={1}
        fps={30}
        width={1500}
        height={1120}
      />
      <Composition
        id="sudoku-prefix-validation-figure"
        component={SudokuPrefixFigure}
        durationInFrames={1}
        fps={30}
        width={1500}
        height={1260}
      />
      <Composition
        id="five-implementation-validation-matrix-figure"
        component={ValidationMatrixFigure}
        durationInFrames={1}
        fps={30}
        width={1560}
        height={1100}
      />
    </>
  );
};
