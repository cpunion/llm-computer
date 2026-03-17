import React from 'react';
import {Composition} from 'remotion';
import {FiveImplementationOverview, FiveImplementationPoster} from './Overview';

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
    </>
  );
};
