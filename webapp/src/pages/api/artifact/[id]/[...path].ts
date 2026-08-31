import type { APIRoute } from 'astro';
import { readFile, realpath } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { showAsset } from '../../../../server/charctx';

const types: Record<string,string> = { '.webp':'image/webp', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.glb':'model/gltf-binary', '.json':'application/json' };

export const GET: APIRoute = async ({ params }) => {
  const id = params.id ?? '';
  const relative = params.path ?? '';
  if (!/^[a-z0-9][a-z0-9-]*$/.test(id) || relative.includes('..') || relative.includes('\\')) return new Response('Not found', { status: 404 });
  try {
    const { card } = await showAsset(id);
    const allowed = new Set([...card.previews, card.cover, card.web_model, card.skeleton, card.parts, card.part_skeleton].filter(Boolean));
    if (!allowed.has(relative)) return new Response('Not found', { status: 404 });
    const packageRoot = await realpath(card.package_dir);
    const file = await realpath(resolve(packageRoot, relative));
    if (file !== packageRoot && !file.startsWith(packageRoot + sep)) return new Response('Not found', { status: 404 });
    const bytes = await readFile(file);
    return new Response(bytes, { headers: { 'Content-Type': types[extname(file).toLowerCase()] ?? 'application/octet-stream', 'Cache-Control':'private, max-age=60' } });
  } catch { return new Response('Not found', { status: 404 }); }
};
