# QRDrop

**English** · [Tiếng Việt](README.vi.md)

Send files from your phone to your computer by scanning a QR code. Your phone uses a web browser; no mobile app is required.

[Download QRDrop 1.0.0](https://github.com/truongminhkhanng/QRDrop/releases/tag/v1.0.0)

## Install

Choose the installer for your computer:

| Computer | Installer | Installation |
|---|---|---|
| Windows 64-bit | `QRDrop_1.0.0_x64-setup.exe` | Open the installer and follow the steps |
| Apple Silicon Mac | `QRDrop_1.0.0_aarch64.dmg` | Open the disk image and drag QRDrop into Applications |
| Ubuntu/Debian 64-bit | `QRDrop_1.0.0_amd64.deb` | Open with your software manager |
| Linux 64-bit | `QRDrop_1.0.0_amd64.AppImage` | Allow the file to run as a program, then open it |

**No Node.js, npm or Rust installation is needed.** The Mac installer is for Apple Silicon; Intel Macs are not supported. The configured minimum macOS version is 13.0.

If the repository is private, downloads require a GitHub account with repository access. A public release can be downloaded without signing in.

Windows installers do not yet have a publisher signature. macOS builds are ad-hoc signed and are not notarized, so your operating system may show a warning. Installation and phone transfers still need verification on real devices. The app interface currently uses Vietnamese; the button labels below match the app.

## Send your first files

1. Connect your phone and computer to the same Wi-Fi or local network where they can reach each other.
2. Open QRDrop on your computer. Choose a save folder in **Cài đặt** (Settings).
3. Select **Bật nhận tệp** (Enable receiving), then scan the QR code with your phone camera.
4. Choose files on your phone and select **Yêu cầu gửi tệp** (Request to send).
5. Review the file list on your computer and select **Cho phép** (Allow).
6. Keep the phone page open and its screen awake until the transfer finishes. Select **Mở thư mục** (Open folder) on your computer to find your files.

QRDrop checks the data before saving a completed file. Existing files are never overwritten; a new file with the same name gets a different name.

## Control receiving

| Control | What it does |
|---|---|
| **Bật nhận tệp** — Enable receiving | Creates a QR code and opens the receiving connection |
| **Tắt nhận tệp** — Disable receiving | Closes the connection, cancels unfinished files and keeps completed files |
| **Làm mới QR** — Refresh QR | Replaces the current QR code and invalidates the old one |

Receiving starts **off** when you open QRDrop. After a transfer ends, enable receiving again for the next transfer. Refreshing a code during a pending request or transfer asks for confirmation first.

Closing QRDrop completely stops receiving. Minimizing the window keeps the app running.

## Connection help

- Check that both devices can reach each other. Guest Wi-Fi, device isolation and VPNs can block the connection.
- Allow QRDrop to access your local network when your operating system asks. In Settings, choose the correct network connection and create a new QR code.
- If a code has expired, has already been used, or your phone changes networks, create a new code and scan it again.
- If a transfer is interrupted, keep the phone page open to retry. Reloading the page or reopening QRDrop requires a new QR code.
- If a file cannot be saved, check free disk space and folder permissions, or choose another folder.

## Privacy

Files travel directly from your phone to your computer, without a cloud relay. Your computer must approve the file list before any file data is received.

**The HTTP connection is not encrypted. Use QRDrop only on a network you trust.** A QR code and transfer permission do not replace network encryption. See the [security details](SECURITY.md).

QRDrop preserves the file data supplied by the browser. Photos and videos chosen from a phone's photo library may differ from the original library resources.
