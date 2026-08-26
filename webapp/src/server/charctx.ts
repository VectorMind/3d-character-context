import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export interface AssetCard {
  id: string;
  title: string;
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
  previews: string[];
  warnings: string[];
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

export async function showAsset(id: string): Promise<{ card: AssetCard; metadata: any; inspection: any }> {
  return run(['assets', 'show', id]);
}

export function artifactUrl(id: string, path: string): string {
  return `/api/artifact/${encodeURIComponent(id)}/${path.split('/').map(encodeURIComponent).join('/')}`;
}
