import {writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {buildOfflineWorker} from '../lib/offline-shell.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
await writeFile(process.argv[2], await buildOfflineWorker(root));
