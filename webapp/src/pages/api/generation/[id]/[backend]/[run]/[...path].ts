import type { APIRoute } from 'astro';
import { readFile, realpath } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { showAsset } from '../../../../../../server/charctx';

const types: Record<string,string> = {
  '.webp':'image/webp',
  '.png':'image/png',
  '.jpg':'image/jpeg',
  '.jpeg':'image/jpeg',
  '.glb':'model/gltf-binary',
  '.json':'application/json',
};

const safePart = (value: string) => /^[a-z0-9][a-z0-9_-]*$/.test(value);

export const GET: APIRoute = async ({ params }) => {
  const id = params.id ?? '';
  const backend = params.backend ?? '';
  const run = params.run ?? '';
  const relative = params.path ?? '';
  if (!safePart(id) || !safePart(backend) || !safePart(run) || relative.includes('..') || relative.includes('\\')) {
    return new Response('Not found', { status: 404 });
  }
  try {
    const data = await showAsset(id);
    const generation = data.generations.find((item) => item.backend === backend && item.run === run);
    if (!generation) return new Response('Not found', { status: 404 });
    const allowed = new Set([generation.model, ...generation.inputs, ...generation.previews, generation.skeleton, generation.landmarks].filter(Boolean));
    if (!allowed.has(relative)) return new Response('Not found', { status: 404 });
    const runRoot = await realpath(generation.run_dir);
    const file = await realpath(resolve(runRoot, relative));
    if (file !== runRoot && !file.startsWith(runRoot + sep)) return new Response('Not found', { status: 404 });
    const bytes = await readFile(file);
    return new Response(bytes, {
      headers: {
        'Content-Type': types[extname(file).toLowerCase()] ?? 'application/octet-stream',
        'Cache-Control':'private, max-age=60',
      },
    });
  } catch {
    return new Response('Not found', { status: 404 });
  }
};
