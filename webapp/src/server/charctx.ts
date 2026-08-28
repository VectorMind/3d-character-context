import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export interface AssetCard {
  id: string;
  title: string;
  kind: 'donor' | 'reference';
  status: string;
  provenance_status: string;
  family: string;
  tags: string[];
  package_dir: string;
  primary_file: string;
  source_formats: string[];
  rigged: boolean;
  animated: boolean;
  bones: number;
  actions: number;
  vertices: number;
  polygons: number;
  cover: string | null;
  web_model: string | null;
  skeleton: string | null;
  skin_weights: string | null;
  deform_bones: number;
  previews: string[];
  generations: number;
  warnings: string[];
}

export interface GenerationRecord {
  schema: 'charctx.generation-view/v1';
  character_id: string;
  backend: string;
  run: string;
  request_name: string;
  seed: number;
  started_at: string | null;
  completed_at: string | null;
  duration_s: number | null;
  model: string;
  model_sha256: string;
  measurements: string | null;
  request_file: string;
  inputs: string[];
  previews: string[];
  stages: Record<string, string>;
  warnings: string[];
  run_dir: string;
  metrics: Record<string, any> | null;
}

async function run(args: string[]): Promise<any> {
  const { stdout } = await execFileAsync('uv', ['run', 'charctx', ...args, '--json'], {
    cwd: new URL('../../..', import.meta.url),
    env: process.env,
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(stdout);
}

export async function listAssets(): Promise<AssetCard[]> {
  return (await run(['assets', 'list'])).assets;
}

export async function showAsset(id: string): Promise<{ card: AssetCard; metadata: any; inspection: any; generations: GenerationRecord[] }> {
  return run(['assets', 'show', id]);
}

export function artifactUrl(id: string, path: string): string {
  return `/api/artifact/${encodeURIComponent(id)}/${path.split('/').map(encodeURIComponent).join('/')}`;
}

export function generationArtifactUrl(id: string, generation: GenerationRecord, path: string): string {
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  return `/api/generation/${encodeURIComponent(id)}/${encodeURIComponent(generation.backend)}/${encodeURIComponent(generation.run)}/${encodedPath}`;
}
