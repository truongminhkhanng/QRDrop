# QRDrop security

**English** · [Tiếng Việt](SECURITY.vi.md)

## Intended use

QRDrop receives files over a trusted local network. Its HTTP connection is **not encrypted**. Someone who can intercept or modify network traffic may obtain credentials or file data, or alter the phone page. A random port and a single-request QR code do not replace HTTPS with a certificate your devices trust.

## Receiving controls

Receiving starts off when the desktop app opens. Enabling receiving creates a new session and listening port. Disabling receiving revokes transfer permission, closes the listener even when an idle connection remains, and cleans up unfinished data. Completed files are kept.

Refreshing the QR code ends the previous session before creating a new one. After a session ends naturally, the listener may remain for about 30 seconds so the phone can read the result. Explicitly disabling receiving closes it immediately.

## Access and input checks

- Credentials use 256 bits of operating-system randomness and constant-time comparison. They are held in memory, not written to application logs or history.
- A QR credential expires after 10 minutes and can create one valid request with a fixed file list. It is consumed when that request is accepted. An identical retry from the same peer can recover the original response.
- Status and upload credentials are separate. The desktop must approve the file list before any file data is written. Cancellation, rejection, expiry or completion revokes upload permission.
- APIs require the selected peer IP, a valid credential and the correct session state. IP addresses are an extra restriction, not proof of identity: devices can share an address through NAT or a proxy. A phone that changes IP needs a new session.
- The receiver validates the request schema, rejects unknown fields and checks file names, sizes and counts. Request bodies, connections, concurrency and connection attempts are bounded. The phone cannot choose filesystem paths.
- Host, Origin and Sec-Fetch-Site checks restrict web requests. Local desktop approval and folder operations are not exposed through the network API.
- The listener binds only to the selected private IPv4 address, using an available port assigned by the operating system. QRDrop does not bind to all interfaces, configure port forwarding or use a cloud relay.

## File handling

Data arrives in chunks of at most 8 MiB. The receiver checks size, position and SHA-256, rolls back an invalid chunk and verifies retried data without appending it twice. A staged file becomes a completed file only after its on-disk SHA-256 is checked. Existing files are never overwritten, and received files are not automatically executed.

SHA-256 detects data differences. Over HTTP, it does not authenticate the sender or prevent an attacker from replacing both the data and its hash. Malicious local software running with the same operating-system user permissions is outside these protections.

## Verification and reporting

See [build results](docs/BUILD_STATUS.md) for automated evidence and [device testing](docs/TESTING.md) for the remaining checks. Loopback tests do not replace installation and transfers on real phones and computers. Windows installers have no publisher signature; macOS builds are ad-hoc signed and are not notarized.

When reporting a problem, include the QRDrop version, operating system, reproduction steps and error message. Do not attach credentials, a complete QR URL or private files. Replace sensitive values with `[REDACTED SECRET]`.
