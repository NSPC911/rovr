import { readFile } from "node:fs/promises";

import { optimize } from "svgo";

const optimizedSvgs = new Map<string, Promise<string>>();

async function optimizeSvgFile(path: string): Promise<string> {
  const sourceSvg = await readFile(path, "utf-8");

  try {
    return optimize(sourceSvg, {
      path,
      plugins: [
        {
          name: "preset-default",
          params: {
            overrides: {
              cleanupIds: false,
              removeUnknownsAndDefaults: false,
            },
          },
        },
      ],
    }).data;
  } catch (error) {
    const message = error instanceof Error ? error.message.split("\n", 1)[0] : String(error);
    console.warn(`[InlineSVG] Could not optimize ${path}: ${message}`);
    return sourceSvg;
  }
}

export function getOptimizedSvg(path: string): Promise<string> {
  const cachedSvg = optimizedSvgs.get(path);
  if (cachedSvg) return cachedSvg;

  const optimizedSvg = optimizeSvgFile(path);
  optimizedSvgs.set(path, optimizedSvg);
  return optimizedSvg;
}
