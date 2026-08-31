import { Grid, OrbitControls, useGLTF } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import { Suspense, useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';

type Bone = {
  name: string;
  deform: boolean;
  head: [number, number, number];
  tail: [number, number, number];
};

type SkeletonDocument = {
  schema: 'charctx.skeleton/v1' | 'charctx.fitted-skeleton/v1' | 'charctx.derived-skeleton/v1';
  derivation?: { method?: string };
  armatures: Array<{ name: string; bones: Bone[] }>;
  summary: { bones: number; deform_bones: number };
};

type Landmark = {
  name: string;
  point: [number, number, number];
  side: 'left' | 'right' | 'center';
  confidence: 'high' | 'medium' | 'low';
};

type LandmarkDocument = {
  schema: 'charctx.landmarks/v1';
  landmarks: Landmark[];
  summary: { landmarks: number };
};

export type PartVolume = {
  schema: 'charctx.part-volume/v1';
  taxonomy: string;
  grid: { display_resolution: number; display_pitch: number; origin: [number, number, number] };
  parts: Array<{ name: string; index: number; color: string; voxels: number; parent?: string | null }>;
  voxels: { encoding: 'linear-index'; resolution: number; index: number[]; part: number[] };
  summary: { solid_voxels: number; parts_present: number; parts_total: number };
};

// Colour by side, so a left/right mix-up is visible at a glance rather than
// something you have to read out of the JSON.
const SIDE_COLOR: Record<Landmark['side'], string> = {
  center: '#ffd166',
  left: '#5ad2ff',
  right: '#ff7ad5',
};

export function fitTransform(boundsMin?: number[], boundsMax?: number[]) {
  const minimum = boundsMin?.length === 3 ? boundsMin : [-1, -1, -1];
  const maximum = boundsMax?.length === 3 ? boundsMax : [1, 1, 1];
  const center = minimum.map((value, index) => (value + maximum[index]) / 2);
  const size = minimum.map((value, index) => maximum[index] - value);
  const scale = 2.7 / Math.max(...size, .001);
  return {
    position: center.map((value) => -value * scale) as [number, number, number],
    scale,
  };
}

export function Dragon({ url, wireframe, inspectionMaterial, xray, onReady }: { url: string; wireframe: boolean; inspectionMaterial: boolean; xray: boolean; onReady: (value: string) => void }) {
  const gltf = useGLTF(url);
  const inspectionScene = useMemo(() => {
    const group = new THREE.Group();
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((node) => {
      if (!(node as THREE.Mesh).isMesh) return;
      const source = node as THREE.Mesh;
      const geometry = source.geometry.clone();
      geometry.applyMatrix4(source.matrixWorld);
      group.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
        color: '#7891b5',
        roughness: .62,
        metalness: .06,
        wireframe,
        side: THREE.DoubleSide,
        transparent: xray,
        opacity: xray ? .22 : 1,
        depthWrite: !xray,
      })));
    });
    return group;
  }, [gltf.scene, wireframe, xray]);

  useEffect(() => {
    let meshes = 0;
    gltf.scene.traverse((node) => { if ((node as THREE.Mesh).isMesh) meshes += 1; });
    onReady(`${meshes} ${meshes === 1 ? 'mesh' : 'meshes'} loaded`);
  }, [gltf.scene, onReady]);

  useEffect(() => {
    gltf.scene.traverse((node) => {
      if (!(node as THREE.Mesh).isMesh) return;
      const mesh = node as THREE.Mesh;
      if (!mesh.userData.charctxOriginalMaterial) mesh.userData.charctxOriginalMaterial = mesh.material;
      const original = mesh.userData.charctxOriginalMaterial as THREE.Material | THREE.Material[];
      const materials = Array.isArray(original) ? original : [original];
      mesh.material = materials.map((material) => {
        if (inspectionMaterial) return material;
        const clone = material.clone();
        if ('wireframe' in clone) (clone as THREE.MeshStandardMaterial).wireframe = wireframe;
        clone.transparent = xray;
        clone.opacity = xray ? .22 : 1;
        clone.depthWrite = !xray;
        return clone;
      });
    });
  }, [gltf.scene, inspectionMaterial, wireframe, xray]);

  return <primitive object={inspectionMaterial ? inspectionScene : gltf.scene} />;
}

export function SkeletonOverlay({ url, visible, muted, derived, onReady }: { url: string; visible: boolean; muted?: boolean; derived?: boolean; onReady: (value: string) => void }) {
  const [data, setData] = useState<SkeletonDocument | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(url, { signal: controller.signal, cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((value: SkeletonDocument) => {
        setData(value);
        const kind = value.schema === 'charctx.fitted-skeleton/v1'
          ? 'fitted'
          : value.schema === 'charctx.derived-skeleton/v1' ? 'derived from parts' : 'extracted';
        const method = value.derivation?.method ? ` (${value.derivation.method})` : '';
        onReady(`${value.summary.bones} bones ${kind}${method}`);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') onReady('Skeleton unavailable');
      });
    return () => controller.abort();
  }, [onReady, url]);

  const group = useMemo(() => {
    if (!data) return null;
    const result = new THREE.Group();
    const deform: number[] = [];
    const other: number[] = [];
    const joints: number[] = [];
    for (const armature of data.armatures) {
      for (const bone of armature.bones) {
        const target = bone.deform ? deform : other;
        target.push(...bone.head, ...bone.tail);
        joints.push(...bone.head, ...bone.tail);
      }
    }
    const addLines = (positions: number[], color: string) => {
      if (!positions.length) return;
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: .96, depthTest: false, depthWrite: false });
      const lines = new THREE.LineSegments(geometry, material);
      lines.renderOrder = 20;
      result.add(lines);
    };
    if (muted) {
      addLines([...deform, ...other], '#7d8a9c');
      return result;
    }
    // A derived skeleton is one bone per part and every joint in it is a
    // measured region boundary, so the joints are drawn larger than on an
    // authored rig, where they are just where two of 168 bones happen to meet.
    addLines(deform, derived ? '#ff8ad0' : '#6fffd2');
    addLines(other, derived ? '#ffd2a1' : '#ffb45f');
    const jointGeometry = new THREE.BufferGeometry();
    jointGeometry.setAttribute('position', new THREE.Float32BufferAttribute(joints, 3));
    const points = new THREE.Points(jointGeometry, new THREE.PointsMaterial({ color: derived ? '#fff0fa' : '#eafff8', size: derived ? .06 : .035, sizeAttenuation: true, depthTest: false, depthWrite: false }));
    points.renderOrder = 21;
    result.add(points);
    return result;
  }, [data, derived, muted]);

  if (!group) return null;
  return <primitive object={group} visible={visible} />;
}

function LandmarkOverlay({ url, visible, scale, onReady }: { url: string; visible: boolean; scale: number; onReady: (value: string) => void }) {
  const [data, setData] = useState<LandmarkDocument | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(url, { signal: controller.signal, cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((value: LandmarkDocument) => {
        setData(value);
        onReady(`${value.summary.landmarks} landmarks proposed`);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') onReady('Landmarks unavailable');
      });
    return () => controller.abort();
  }, [onReady, url]);

  const group = useMemo(() => {
    if (!data) return null;
    const result = new THREE.Group();
    // Sized in world units so the markers stay legible whatever the model's
    // own scale is; low-confidence proposals are drawn smaller and dimmer.
    const radius = .026 / Math.max(scale, .001);
    const geometry = new THREE.SphereGeometry(radius, 14, 10);
    for (const mark of data.landmarks) {
      const weak = mark.confidence === 'low';
      const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({
        color: SIDE_COLOR[mark.side] ?? '#ffffff',
        transparent: true,
        opacity: weak ? .45 : .95,
        depthTest: false,
        depthWrite: false,
      }));
      mesh.scale.setScalar(weak ? .7 : 1);
      mesh.position.set(mark.point[0], mark.point[1], mark.point[2]);
      mesh.renderOrder = 25;
      result.add(mesh);
    }
    return result;
  }, [data, scale]);

  if (!group) return null;
  return <primitive object={group} visible={visible} />;
}

// The part document is fetched by the parent, because the legend outside the
// canvas needs the same part list the overlay draws.
export function usePartVolume(url?: string) {
  const [data, setData] = useState<PartVolume | null>(null);
  const [status, setStatus] = useState(url ? 'Loading parts…' : '');

  useEffect(() => {
    if (!url) { setData(null); setStatus(''); return; }
    const controller = new AbortController();
    fetch(url, { signal: controller.signal, cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((value: PartVolume) => {
        setData(value);
        setStatus(`${value.voxels.index.length} voxels, ${value.summary.parts_present}/${value.summary.parts_total} parts`);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setStatus('Parts unavailable');
      });
    return () => controller.abort();
  }, [url]);

  return { data, status };
}

// Two InstancedMeshes of cubes rather than one: the parts you selected in
// full colour, and the ones you hid as a dim ghost. Hiding by deletion would
// take the body's silhouette with it, and then an isolated part floats in
// space with nothing to locate it against -- which is the opposite of what
// inspecting one part is for.
export function PartOverlay({ data, visible, hidden, ghost }: { data: PartVolume | null; visible: boolean; hidden: Set<number>; ghost: boolean }) {
  const group = useMemo(() => {
    if (!data) return null;
    const { display_resolution: size, display_pitch: pitch, origin } = data.grid;
    const colors = new Map(data.parts.map((part) => [part.index, new THREE.Color(part.color)]));
    const fallback = new THREE.Color('#888888');

    const shownRows: number[] = [];
    const ghostRows: number[] = [];
    for (let i = 0; i < data.voxels.index.length; i += 1) {
      (hidden.has(data.voxels.part[i]) ? ghostRows : shownRows).push(i);
    }

    const result = new THREE.Group();
    const matrix = new THREE.Matrix4();
    const place = (row: number) => {
      const linear = data.voxels.index[row];
      // Row-major, matching numpy's default ravel order.
      const x = Math.floor(linear / (size * size));
      const y = Math.floor(linear / size) % size;
      const z = linear % size;
      matrix.setPosition(
        origin[0] + (x + 0.5) * pitch,
        origin[1] + (y + 0.5) * pitch,
        origin[2] + (z + 0.5) * pitch,
      );
    };

    if (shownRows.length) {
      // Unlit, and cubes deliberately smaller than their cell. The scene's
      // key lights are tinted warm and cool, which would shift a part's
      // colour toward a neighbour's -- and colour identity is this overlay's
      // entire message. The gaps between undersized cubes give back the depth
      // cue that dropping the shading costs.
      //
      // No `vertexColors` on the material, deliberately: it defines USE_COLOR,
      // and the shader then runs `vColor *= color` against a per-vertex
      // attribute a BoxGeometry has not got, which reads as (0,0,0) and
      // renders every instance black. `setColorAt` alone allocates
      // instanceColor and defines USE_INSTANCING_COLOR, the branch that
      // actually applies here.
      const mesh = new THREE.InstancedMesh(
        new THREE.BoxGeometry(pitch * 0.85, pitch * 0.85, pitch * 0.85),
        new THREE.MeshBasicMaterial(),
        shownRows.length,
      );
      shownRows.forEach((row, i) => {
        place(row);
        mesh.setMatrixAt(i, matrix);
        mesh.setColorAt(i, colors.get(data.voxels.part[row]) ?? fallback);
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      result.add(mesh);
    }

    if (ghost && ghostRows.length) {
      const mesh = new THREE.InstancedMesh(
        new THREE.BoxGeometry(pitch * 0.5, pitch * 0.5, pitch * 0.5),
        new THREE.MeshBasicMaterial({ color: '#4a586d', transparent: true, opacity: .18, depthWrite: false }),
        ghostRows.length,
      );
      ghostRows.forEach((row, i) => { place(row); mesh.setMatrixAt(i, matrix); });
      mesh.instanceMatrix.needsUpdate = true;
      result.add(mesh);
    }

    return result;
  }, [data, hidden, ghost]);

  if (!group) return null;
  return <primitive object={group} visible={visible} />;
}

function Stage({ url, skeletonUrl, skeletonVisible, derivedUrl, derivedVisible, comparisonUrl, comparisonVisible, landmarkUrl, landmarkVisible, partData, partVisible, partHidden, partGhost, wireframe, inspectionMaterial, xray, boundsMin, boundsMax, onModelReady, onSkeletonReady, onDerivedReady, onComparisonReady, onLandmarkReady }: { url: string; skeletonUrl?: string; skeletonVisible: boolean; derivedUrl?: string; derivedVisible: boolean; comparisonUrl?: string; comparisonVisible: boolean; landmarkUrl?: string; landmarkVisible: boolean; partData: PartVolume | null; partVisible: boolean; partHidden: Set<number>; partGhost: boolean; wireframe: boolean; inspectionMaterial: boolean; xray: boolean; boundsMin?: number[]; boundsMax?: number[]; onModelReady: (value: string) => void; onSkeletonReady: (value: string) => void; onDerivedReady: (value: string) => void; onComparisonReady: (value: string) => void; onLandmarkReady: (value: string) => void }) {
  const transform = useMemo(() => fitTransform(boundsMin, boundsMax), [boundsMin, boundsMax]);
  return <>
    <color attach="background" args={['#070b12']} />
    <ambientLight intensity={1.25} />
    <directionalLight position={[5, 8, 5]} intensity={3.5} color="#ffe0b2" />
    <directionalLight position={[-5, 2, -3]} intensity={2.2} color="#8cb8ff" />
    <group position={transform.position} scale={transform.scale}>
      <Suspense fallback={null}><Dragon url={url} wireframe={wireframe} inspectionMaterial={inspectionMaterial} xray={xray} onReady={onModelReady} /></Suspense>
      <PartOverlay data={partData} visible={partVisible} hidden={partHidden} ghost={partGhost} />
      {comparisonUrl && comparisonVisible && <SkeletonOverlay url={comparisonUrl} visible muted onReady={onComparisonReady} />}
      {skeletonUrl && <SkeletonOverlay url={skeletonUrl} visible={skeletonVisible} onReady={onSkeletonReady} />}
      {derivedUrl && <SkeletonOverlay url={derivedUrl} visible={derivedVisible} derived onReady={onDerivedReady} />}
      {landmarkUrl && <LandmarkOverlay url={landmarkUrl} visible={landmarkVisible} scale={transform.scale} onReady={onLandmarkReady} />}
    </group>
    <Grid infiniteGrid fadeDistance={80} sectionColor="#34445b" cellColor="#1b2635" position={[0, -1.5, 0]} />
    <OrbitControls makeDefault enableDamping enablePan enableRotate enableZoom />
  </>;
}

export default function ModelViewer({ url, skeletonUrl, derivedUrl, comparisonUrl, landmarkUrl, partUrl, boundsMin, boundsMax, sourceMaterialAvailable }: { url: string; skeletonUrl?: string; derivedUrl?: string; comparisonUrl?: string; landmarkUrl?: string; partUrl?: string; boundsMin: number[]; boundsMax: number[]; sourceMaterialAvailable: boolean }) {
  const [wireframe, setWireframe] = useState(false);
  const [inspectionMaterial, setInspectionMaterial] = useState(true);
  const [skeletonVisible, setSkeletonVisible] = useState(Boolean(skeletonUrl));
  // Off by default: the comparison fit is for the review pass, not the
  // everyday picture.
  const [comparisonVisible, setComparisonVisible] = useState(false);
  const [landmarkVisible, setLandmarkVisible] = useState(Boolean(landmarkUrl));
  const [xray, setXray] = useState(false);
  const [modelStatus, setModelStatus] = useState('Loading model…');
  const [skeletonStatus, setSkeletonStatus] = useState(skeletonUrl ? 'Loading skeleton…' : '');
  const [comparisonStatus, setComparisonStatus] = useState('');
  // The part-derived skeleton starts hidden wherever an authored or fitted rig
  // is already drawn: the interesting picture is the two together, and that is
  // a comparison you ask for.
  const [derivedVisible, setDerivedVisible] = useState(Boolean(derivedUrl) && !skeletonUrl);
  const [derivedStatus, setDerivedStatus] = useState(derivedUrl ? 'Loading derived skeleton…' : '');
  // Parts start hidden: they occlude the model completely, so they are a
  // thing you switch to, not a thing you switch off.
  const [partVisible, setPartVisible] = useState(false);
  const [landmarkStatus, setLandmarkStatus] = useState(landmarkUrl ? 'Loading landmarks…' : '');

  const { data: partData, status: partStatus } = usePartVolume(partUrl);
  // Hidden rather than selected, so the default is everything visible and a
  // part added by a later run appears without being opted in.
  const [hidden, setHidden] = useState<Set<number>>(new Set());
  const [ghost, setGhost] = useState(true);
  const present = useMemo(
    () => (partData?.parts ?? []).filter((part) => part.voxels > 0),
    [partData],
  );
  const only = (index: number) => {
    const chosen = present.find((part) => part.index === index);
    const family = new Set([index]);
    if (chosen && !chosen.parent) {
      for (const part of present) if (part.parent === chosen.name) family.add(part.index);
    }
    setHidden(new Set(present.map((part) => part.index).filter((value) => !family.has(value))));
  };
  const toggle = (index: number) => setHidden((current) => {
    const next = new Set(current);
    if (next.has(index)) next.delete(index); else next.add(index);
    return next;
  });
  const shownCount = present.length - present.filter((part) => hidden.has(part.index)).length;

  return <div className="viewer">
    <div className="viewer-ui">
      <span className="viewer-status">{[modelStatus, skeletonStatus, derivedVisible ? derivedStatus : '', comparisonVisible ? comparisonStatus : '', landmarkStatus, partVisible ? partStatus : ''].filter(Boolean).join(' · ')}</span>
      {skeletonUrl && <button type="button" aria-pressed={skeletonVisible} onClick={() => setSkeletonVisible(!skeletonVisible)}>{skeletonVisible ? 'Hide skeleton' : 'Show skeleton'}</button>}
      {derivedUrl && <button type="button" aria-pressed={derivedVisible} onClick={() => setDerivedVisible(!derivedVisible)}>{derivedVisible ? 'Hide part skeleton' : 'Show part skeleton'}</button>}
      {partUrl && <button type="button" aria-pressed={partVisible} onClick={() => setPartVisible(!partVisible)}>{partVisible ? 'Hide body parts' : 'Show body parts'}</button>}
      {comparisonUrl && <button type="button" aria-pressed={comparisonVisible} onClick={() => setComparisonVisible(!comparisonVisible)}>{comparisonVisible ? 'Hide previous fit' : 'Compare previous fit'}</button>}
      {landmarkUrl && <button type="button" aria-pressed={landmarkVisible} onClick={() => setLandmarkVisible(!landmarkVisible)}>{landmarkVisible ? 'Hide landmarks' : 'Show landmarks'}</button>}
      {(skeletonUrl || derivedUrl || landmarkUrl) && <button type="button" aria-pressed={xray} onClick={() => setXray(!xray)}>{xray ? 'Opaque model' : 'X-ray model'}</button>}
      {sourceMaterialAvailable && <button type="button" aria-pressed={inspectionMaterial} onClick={() => setInspectionMaterial(!inspectionMaterial)}>{inspectionMaterial ? 'Source material' : 'Inspection material'}</button>}
      <button type="button" aria-pressed={wireframe} onClick={() => setWireframe(!wireframe)}>{wireframe ? 'Solid' : 'Wireframe'}</button>
    </div>
    {partVisible && present.length > 0 && <div className="part-legend">
      <div className="part-legend-head">
        <strong>Body parts</strong>
        <span>{shownCount}/{present.length}</span>
        <button type="button" onClick={() => setHidden(new Set())}>All</button>
        <button type="button" onClick={() => setHidden(new Set(present.map((part) => part.index)))}>None</button>
        <button type="button" aria-pressed={ghost} onClick={() => setGhost(!ghost)}>Ghost</button>
      </div>
      <ul>
        {present.map((part) => {
          const off = hidden.has(part.index);
          return <li key={part.index} className={[off ? 'off' : '', part.parent ? 'sub' : ''].filter(Boolean).join(' ') || undefined}>
            <label>
              <input type="checkbox" checked={!off} onChange={() => toggle(part.index)} />
              <span className="swatch" style={{ background: part.color }} />
              <span className="part-name">{part.name}</span>
              <span className="part-count">{part.voxels.toLocaleString()}</span>
            </label>
            <button type="button" title={`Show only ${part.name}`} onClick={() => only(part.index)}>only</button>
          </li>;
        })}
      </ul>
    </div>}
    <Canvas camera={{ position: [4.8, 3.2, 6.5], fov: 38 }} dpr={[1, 2]} gl={{ antialias: true }}>
      <Stage url={url} skeletonUrl={skeletonUrl} skeletonVisible={skeletonVisible} derivedUrl={derivedUrl} derivedVisible={derivedVisible} onDerivedReady={setDerivedStatus} comparisonUrl={comparisonUrl} comparisonVisible={comparisonVisible} onComparisonReady={setComparisonStatus} partData={partData} partVisible={partVisible} partHidden={hidden} partGhost={ghost} landmarkUrl={landmarkUrl} landmarkVisible={landmarkVisible} wireframe={wireframe} inspectionMaterial={inspectionMaterial} xray={xray} boundsMin={boundsMin} boundsMax={boundsMax} onModelReady={setModelStatus} onSkeletonReady={setSkeletonStatus} onLandmarkReady={setLandmarkStatus} />
    </Canvas>
  </div>;
}
