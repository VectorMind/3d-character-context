import { Canvas, useThree } from '@react-three/fiber';
import { Suspense, useEffect, useState } from 'react';
import {
  Dragon,
  PartOverlay,
  SkeletonOverlay,
  fitTransform,
  usePartVolume,
} from './ModelViewer';

// The same diagonal the main viewer opens on, and the same one the Blender
// hero preview renders from — so the four tiles and the live viewer all agree
// on what "the first view" means and a difference between them is a real
// difference, not a camera move.
const DIAGONAL: [number, number, number] = [4.8, 3.2, 6.5];

const EMPTY: Set<number> = new Set();

// These canvases render on demand rather than in a loop -- four continuous
// render loops on one page is a lot of GPU for four still pictures. The cost
// of `demand` is that a frame can be drawn before a suspended model or a
// fetched document has resolved, and nothing would ask for another. So each
// tile explicitly requests a redraw when its content changes, and once more
// on the next tick to cover a resolve that lands mid-commit.
function Redraw({ token }: { token: unknown }) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    invalidate();
    const timer = setTimeout(invalidate, 80);
    return () => clearTimeout(timer);
  }, [invalidate, token]);
  return null;
}

function SkeletonTile({ modelUrl, skeletonUrl, boundsMin, boundsMax }: { modelUrl: string; skeletonUrl: string; boundsMin?: number[]; boundsMax?: number[] }) {
  const [model, setModel] = useState('');
  const [skeleton, setSkeleton] = useState('');
  return <Scene url={modelUrl} token={`${model}|${skeleton}`} onModelReady={setModel} boundsMin={boundsMin} boundsMax={boundsMax}>
    <SkeletonOverlay url={skeletonUrl} visible onReady={setSkeleton} />
  </Scene>;
}

function Tile({ label, children }: { label: string; children: React.ReactNode }) {
  return <figure className="view-tile">
    <div className="view-tile-body">{children}</div>
    <figcaption>{label}</figcaption>
  </figure>;
}

function Scene({ url, token, onModelReady, boundsMin, boundsMax, children }: { url?: string; token?: unknown; onModelReady?: (value: string) => void; boundsMin?: number[]; boundsMax?: number[]; children?: React.ReactNode }) {
  const transform = fitTransform(boundsMin, boundsMax);
  return <Canvas camera={{ position: DIAGONAL, fov: 38 }} dpr={[1, 1.5]} gl={{ antialias: true }} frameloop="demand">
    <Redraw token={token} />
    <color attach="background" args={['#070b12']} />
    <ambientLight intensity={1.25} />
    <directionalLight position={[5, 8, 5]} intensity={3.2} color="#ffe0b2" />
    <directionalLight position={[-5, 2, -3]} intensity={2.0} color="#8cb8ff" />
    <group position={transform.position} scale={transform.scale}>
      {url && <Suspense fallback={null}><Dragon url={url} wireframe={false} inspectionMaterial xray={Boolean(children)} onReady={onModelReady ?? (() => undefined)} /></Suspense>}
      {children}
    </group>
  </Canvas>;
}

/**
 * One camera angle, four ways: what went in, what came out, what was fitted
 * onto it, and how it was classified. Holding the view fixed is the whole
 * point — a strip of five camera angles shows you the model from five sides,
 * which is a different question from whether the pipeline preserved the
 * character.
 *
 * The first two tiles are images that already exist; the last two are live,
 * so they cannot fall out of date with the artifacts they draw.
 */
export default function ViewStrip({ inputUrl, solidUrl, modelUrl, skeletonUrl, partUrl, boundsMin, boundsMax }: { inputUrl?: string; solidUrl?: string; modelUrl: string; skeletonUrl?: string; partUrl?: string; boundsMin?: number[]; boundsMax?: number[] }) {
  const { data } = usePartVolume(partUrl);

  return <div className="view-strip">
    <Tile label="Input reference">
      {inputUrl
        ? <img src={inputUrl} alt="Reference input at the diagonal view" loading="lazy" />
        : <p className="view-tile-empty">No input view — this asset was collected, not generated</p>}
    </Tile>

    <Tile label={inputUrl ? 'Generated solid' : 'Source solid'}>
      {solidUrl
        ? <img src={solidUrl} alt="Generated mesh rendered solid at the diagonal view" loading="lazy" />
        : <p className="view-tile-empty">No render</p>}
    </Tile>

    <Tile label="Fitted skeleton">
      {skeletonUrl
        ? <SkeletonTile modelUrl={modelUrl} skeletonUrl={skeletonUrl} boundsMin={boundsMin} boundsMax={boundsMax} />
        : <p className="view-tile-empty">Not fitted</p>}
    </Tile>

    <Tile label="Body parts">
      {partUrl
        ? <Scene token={data} boundsMin={boundsMin} boundsMax={boundsMax}>
            <PartOverlay data={data} visible hidden={EMPTY} ghost={false} />
          </Scene>
        : <p className="view-tile-empty">Not classified</p>}
    </Tile>
  </div>;
}
