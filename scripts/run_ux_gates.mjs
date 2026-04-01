import net from 'node:net';
import { spawn } from 'node:child_process';

function reserveFreePort(host = '127.0.0.1') {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', reject);
    server.listen(0, host, () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        server.close();
        reject(new Error('Failed to resolve a free port for the UX gate.'));
        return;
      }
      const { port } = address;
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(port);
      });
    });
  });
}

function run(command, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      env,
      stdio: 'inherit',
    });

    child.once('error', reject);
    child.once('exit', (code, signal) => {
      if (signal) {
        reject(new Error(`${command} exited from signal ${signal}`));
        return;
      }
      resolve(code ?? 1);
    });
  });
}

async function main() {
  const port = await reserveFreePort();
  const baseUrl = `http://127.0.0.1:${port}/web`;
  const waitUrl = `${baseUrl}/`;
  const env = {
    ...process.env,
    STATIC_AUDIT_PORT: String(port),
    PLAYWRIGHT_BASE_URL: baseUrl,
  };

  const exitCode = await run(
    'start-server-and-test',
    [
      'npm run ux:serve',
      waitUrl,
      `npm run ux:playwright && lhci autorun --config=.lighthouserc.json --collect.url=${waitUrl}`,
    ],
    env,
  );

  process.exit(exitCode);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
