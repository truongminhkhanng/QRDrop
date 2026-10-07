// Explicit loopback-only fixture for native real-HTTP integration tests.
import { createRelay } from './server.mjs';
import net from 'node:net';
const reservation = net.createServer();
await new Promise(resolve => reservation.listen(0, '127.0.0.1', resolve));
const port = reservation.address().port;
await new Promise(resolve => reservation.close(resolve));
const server = createRelay({ origin: `http://127.0.0.1:${port}`, allowInsecureLoopback: true });
server.listen(port, '127.0.0.1', () => process.stdout.write(`${port}\n`));
