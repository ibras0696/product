import { readFile, readdir } from "node:fs/promises";
import { join, relative } from "node:path";

const root = new URL("../src/", import.meta.url);
const violations = [];

async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      await walk(path);
      continue;
    }
    if (!/\.(ts|tsx)$/.test(entry.name)) continue;
    const source = await readFile(path, "utf8");
    const currentModule = relative(root.pathname, path).split("/")[1];
    for (const match of source.matchAll(
      /from\s+["']@\/modules\/([^/"']+)\/([^"']+)["']/g,
    )) {
      const [, importedModule] = match;
      if (currentModule && importedModule !== currentModule) {
        violations.push(
          `${relative(root.pathname, path)} deep-imports ${match[0]}`,
        );
      }
    }
  }
}

await walk(root.pathname);
if (violations.length > 0) {
  console.error(violations.join("\n"));
  process.exit(1);
}
console.log("Frontend module-boundary check passed.");
