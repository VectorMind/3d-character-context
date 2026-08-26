import { Grid, OrbitControls, useGLTF } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import { Suspense, useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';

function Dragon({ url, wireframe, inspectionMaterial, boundsMin, boundsMax, onReady }: { url: string; wireframe: boolean; inspectionMaterial: boolean; boundsMin?: number[]; boundsMax?: number[]; onReady: (value: string) => void }) {
  const gltf = useGLTF(url);
  const inspectionScene = useMemo(() => {
    const group = new THREE.Group();
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((node) => {
      if (!(node as THREE.Mesh).isMesh) return;
      const source = node as THREE.Mesh;
      const geometry = source.geometry.clone();
      geometry.applyMatrix4(source.matrixWorld);
      group.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: '#7891b5', roughness: .62, metalness: .06, wireframe, side: THREE.DoubleSide })));
    });
    return group;
  }, [gltf.scene, wireframe]);
  const transform = useMemo(() => {
    gltf.scene.traverse((node) => { node.visible = true; node.frustumCulled = false; });
    const measured = new THREE.Box3().setFromObject(gltf.scene);
    const minimum = boundsMin?.length === 3 ? boundsMin : measured.min.toArray();
    const maximum = boundsMax?.length === 3 ? boundsMax : measured.max.toArray();
    const center = minimum.map((value, index) => (value + maximum[index]) / 2);
    const size = minimum.map((value, index) => maximum[index] - value);
    const scale = 2.7 / Math.max(...size, .001);
    return { position: center.map((value) => -value * scale) as [number, number, number], scale };
  }, [boundsMax, boundsMin, gltf.scene]);
  useEffect(() => {
    let meshes = 0;
    gltf.scene.traverse((node) => { if ((node as THREE.Mesh).isMesh) meshes += 1; });
    onReady(`${meshes} ${meshes === 1 ? 'mesh' : 'meshes'} loaded`);
  }, [gltf.scene, onReady]);

  useEffect(() => {
    gltf.scene.traverse((node) => {
      if ((node as THREE.Mesh).isMesh) {
        const mesh = node as THREE.Mesh;
        if (!mesh.userData.charctxOriginalMaterial) mesh.userData.charctxOriginalMaterial = mesh.material;
        const original = mesh.userData.charctxOriginalMaterial as THREE.Material | THREE.Material[];
        const materials = Array.isArray(original) ? original : [original];
        mesh.material = materials.map((material) => {
          if (inspectionMaterial) return new THREE.MeshStandardMaterial({ color: '#7891b5', roughness: .62, metalness: .06, wireframe, side: THREE.DoubleSide });
          const clone = material.clone();
          if ('wireframe' in clone) (clone as THREE.MeshStandardMaterial).wireframe = wireframe;
          return clone;
        });
      }
    });
  }, [gltf.scene, inspectionMaterial, wireframe]);

  return <primitive object={inspectionMaterial ? inspectionScene : gltf.scene} position={transform.position} scale={transform.scale} />;
}

function Stage({ url, wireframe, inspectionMaterial, boundsMin, boundsMax, onReady }: { url: string; wireframe: boolean; inspectionMaterial: boolean; boundsMin?: number[]; boundsMax?: number[]; onReady: (value: string) => void }) {
  return <>
    <color attach="background" args={['#070b12']} />
    <ambientLight intensity={1.25} />
    <directionalLight position={[5, 8, 5]} intensity={3.5} color="#ffe0b2" />
    <directionalLight position={[-5, 2, -3]} intensity={2.2} color="#8cb8ff" />
    <Suspense fallback={null}><Dragon url={url} wireframe={wireframe} inspectionMaterial={inspectionMaterial} boundsMin={boundsMin} boundsMax={boundsMax} onReady={onReady} /></Suspense>
    <Grid infiniteGrid fadeDistance={80} sectionColor="#34445b" cellColor="#1b2635" position={[0, -1.5, 0]} />
    <OrbitControls makeDefault enableDamping />
  </>;
}

export default function ModelViewer({ url, boundsMin, boundsMax, sourceMaterialAvailable }: { url: string; boundsMin: number[]; boundsMax: number[]; sourceMaterialAvailable: boolean }) {
  const [wireframe, setWireframe] = useState(false);
  const [inspectionMaterial, setInspectionMaterial] = useState(true);
  const [status, setStatus] = useState('Loading model…');
  return <div className="viewer">
    <div className="viewer-ui">
      <span className="viewer-status">{status}</span>
      {sourceMaterialAvailable && <button type="button" aria-pressed={inspectionMaterial} onClick={() => setInspectionMaterial(!inspectionMaterial)}>{inspectionMaterial ? 'Source material' : 'Inspection material'}</button>}
      <button type="button" aria-pressed={wireframe} onClick={() => setWireframe(!wireframe)}>{wireframe ? 'Solid' : 'Wireframe'}</button>
    </div>
    <Canvas camera={{ position: [4.8, 3.2, 6.5], fov: 38 }} dpr={[1, 2]} gl={{ antialias: true }}>
      <Stage url={url} wireframe={wireframe} inspectionMaterial={inspectionMaterial} boundsMin={boundsMin} boundsMax={boundsMax} onReady={setStatus} />
    </Canvas>
  </div>;
}
