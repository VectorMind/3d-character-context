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
  schema: 'charctx.skeleton/v1' | 'charctx.fitted-skeleton/v1';
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

// Colour by side, so a left/right mix-up is visible at a glance rather than
// something you have to read out of the JSON.
const SIDE_COLOR: Record<Landmark['side'], string> = {
  center: '#ffd166',
  left: '#5ad2ff',
  right: '#ff7ad5',
};

function fitTransform(boundsMin?: number[], boundsMax?: number[]) {
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

function Dragon({ url, wireframe, inspectionMaterial, xray, onReady }: { url: string; wireframe: boolean; inspectionMaterial: boolean; xray: boolean; onReady: (value: string) => void }) {
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

function SkeletonOverlay({ url, visible, onReady }: { url: string; visible: boolean; onReady: (value: string) => void }) {
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
        onReady(`${value.summary.bones} bones ${value.schema === 'charctx.fitted-skeleton/v1' ? 'fitted' : 'extracted'}`);
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
    addLines(deform, '#6fffd2');
    addLines(other, '#ffb45f');
    const jointGeometry = new THREE.BufferGeometry();
    jointGeometry.setAttribute('position', new THREE.Float32BufferAttribute(joints, 3));
    const points = new THREE.Points(jointGeometry, new THREE.PointsMaterial({ color: '#eafff8', size: .035, sizeAttenuation: true, depthTest: false, depthWrite: false }));
    points.renderOrder = 21;
    result.add(points);
    return result;
  }, [data]);

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

function Stage({ url, skeletonUrl, skeletonVisible, landmarkUrl, landmarkVisible, wireframe, inspectionMaterial, xray, boundsMin, boundsMax, onModelReady, onSkeletonReady, onLandmarkReady }: { url: string; skeletonUrl?: string; skeletonVisible: boolean; landmarkUrl?: string; landmarkVisible: boolean; wireframe: boolean; inspectionMaterial: boolean; xray: boolean; boundsMin?: number[]; boundsMax?: number[]; onModelReady: (value: string) => void; onSkeletonReady: (value: string) => void; onLandmarkReady: (value: string) => void }) {
  const transform = useMemo(() => fitTransform(boundsMin, boundsMax), [boundsMin, boundsMax]);
  return <>
    <color attach="background" args={['#070b12']} />
    <ambientLight intensity={1.25} />
    <directionalLight position={[5, 8, 5]} intensity={3.5} color="#ffe0b2" />
    <directionalLight position={[-5, 2, -3]} intensity={2.2} color="#8cb8ff" />
    <group position={transform.position} scale={transform.scale}>
      <Suspense fallback={null}><Dragon url={url} wireframe={wireframe} inspectionMaterial={inspectionMaterial} xray={xray} onReady={onModelReady} /></Suspense>
      {skeletonUrl && <SkeletonOverlay url={skeletonUrl} visible={skeletonVisible} onReady={onSkeletonReady} />}
      {landmarkUrl && <LandmarkOverlay url={landmarkUrl} visible={landmarkVisible} scale={transform.scale} onReady={onLandmarkReady} />}
    </group>
    <Grid infiniteGrid fadeDistance={80} sectionColor="#34445b" cellColor="#1b2635" position={[0, -1.5, 0]} />
    <OrbitControls makeDefault enableDamping enablePan enableRotate enableZoom />
  </>;
}

export default function ModelViewer({ url, skeletonUrl, landmarkUrl, boundsMin, boundsMax, sourceMaterialAvailable }: { url: string; skeletonUrl?: string; landmarkUrl?: string; boundsMin: number[]; boundsMax: number[]; sourceMaterialAvailable: boolean }) {
  const [wireframe, setWireframe] = useState(false);
  const [inspectionMaterial, setInspectionMaterial] = useState(true);
  const [skeletonVisible, setSkeletonVisible] = useState(Boolean(skeletonUrl));
  const [landmarkVisible, setLandmarkVisible] = useState(Boolean(landmarkUrl));
  const [xray, setXray] = useState(false);
  const [modelStatus, setModelStatus] = useState('Loading model…');
  const [skeletonStatus, setSkeletonStatus] = useState(skeletonUrl ? 'Loading skeleton…' : '');
  const [landmarkStatus, setLandmarkStatus] = useState(landmarkUrl ? 'Loading landmarks…' : '');
  return <div className="viewer">
    <div className="viewer-ui">
      <span className="viewer-status">{[modelStatus, skeletonStatus, landmarkStatus].filter(Boolean).join(' · ')}</span>
      {skeletonUrl && <button type="button" aria-pressed={skeletonVisible} onClick={() => setSkeletonVisible(!skeletonVisible)}>{skeletonVisible ? 'Hide skeleton' : 'Show skeleton'}</button>}
      {landmarkUrl && <button type="button" aria-pressed={landmarkVisible} onClick={() => setLandmarkVisible(!landmarkVisible)}>{landmarkVisible ? 'Hide landmarks' : 'Show landmarks'}</button>}
      {(skeletonUrl || landmarkUrl) && <button type="button" aria-pressed={xray} onClick={() => setXray(!xray)}>{xray ? 'Opaque model' : 'X-ray model'}</button>}
      {sourceMaterialAvailable && <button type="button" aria-pressed={inspectionMaterial} onClick={() => setInspectionMaterial(!inspectionMaterial)}>{inspectionMaterial ? 'Source material' : 'Inspection material'}</button>}
      <button type="button" aria-pressed={wireframe} onClick={() => setWireframe(!wireframe)}>{wireframe ? 'Solid' : 'Wireframe'}</button>
    </div>
    <Canvas camera={{ position: [4.8, 3.2, 6.5], fov: 38 }} dpr={[1, 2]} gl={{ antialias: true }}>
      <Stage url={url} skeletonUrl={skeletonUrl} skeletonVisible={skeletonVisible} landmarkUrl={landmarkUrl} landmarkVisible={landmarkVisible} wireframe={wireframe} inspectionMaterial={inspectionMaterial} xray={xray} boundsMin={boundsMin} boundsMax={boundsMax} onModelReady={setModelStatus} onSkeletonReady={setSkeletonStatus} onLandmarkReady={setLandmarkStatus} />
    </Canvas>
  </div>;
}
