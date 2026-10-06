export class Sha256 {
  update(data: Uint8Array): this;
  digest(): string;
}
