# VADM

<p align="center">
  <img src="art/VADM.png" alt="VADM logo" width="160">
</p>

<h3 align="center">Fast, clean, open-source download manager for Windows — forked from Mister Download Manager.</h3>

<p align="center">
  <a href="https://github.com/vietanh210304/vadm/releases/latest"><img src="https://img.shields.io/badge/Download%20for-Windows%20x64-2a78d6?style=flat-square" alt="Download for Windows x64" height="34"></a>
  <a href="https://github.com/vietanh210304/vadm/releases/latest"><img src="https://img.shields.io/github/v/release/vietanh210304/vadm?logo=github&style=flat-square" alt="Latest release" height="34"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/vietanh210304/vadm?style=flat-square" alt="GPL-3.0 license" height="34"></a>
</p>

**VADM** is a lightweight, streamlined fork of [anefzaoui/misterdownloadmanager](https://github.com/anefzaoui/misterdownloadmanager) built for high-speed HTTP/HTTPS/FTP transfers, video downloads (`yt-dlp`), and seamless browser integration — without built-in BitTorrent/RSS bloat.

---

## What VADM changes from upstream MDM

- **Torrent & RSS engine removed:** Focuses purely on direct downloads, multi-connection acceleration, archives, video capture, and Link grabber.
- **`.torrent` file capture kept:** Browsers still hand `.torrent` file links over to VADM as ordinary files so you can open them in your standalone torrent client.
- **VADM branding & floating video button improvements:** Custom VADM app/tray/extension icons and a dedicated drag handle (`.grip`) separated from the click-to-download button (`.go`) on web videos.
- **Automated non-torrent upstream sync & signed in-app updates:** Daily workflow filters out torrent/RSS commits from upstream, runs tests, auto-releases clean updates, and notifies **Help → Check for updates...** inside VADM.

---

## Download & Install (Windows x64)

Download from [Releases](https://github.com/vietanh210304/vadm/releases/latest):

| File | When to choose it |
| --- | --- |
| **`VADM-<version>-setup.exe`** | Standard Windows installer: sets up app, Start Menu/Desktop shortcuts, and browser host registration. |
| `VADM-<version>-portable.zip` | Portable mode with a local `data` folder next to `vadm.exe` (no registry entries). |
| `VADM-<version>-x64.zip` | Plain x64 binaries (`AppData\Roaming\vadm` profile) — supports **Help → Check for updates → Update now** in-place updates. |
| `VADM-<version>-extension-chromium.zip` | Browser extension for Chrome, Edge, Brave, Opera, Vivaldi: unzip and click **Load unpacked** in Developer mode (`chrome://extensions` or `edge://extensions`). |

> [!NOTE]
> Uncompressed/unpacked browser integration stays pinned to extension ID `oogbclbbninliongijffeeggalppliok`. Run `vadm-nmhost.exe --register` (done automatically by the installer or setup script) so Chrome/Edge/Firefox connect to VADM.

---

## Core Features

- **Multi-connection acceleration:** Splits files into dynamic segments and keeps re-balancing until the final byte.
- **Reliable resume & site rules:** Custom headers, cookies, proxies, User-Agent, and browser-like TLS connections (`BoringSSL`).
- **Browser extension integration:** Captures downloads, finds images on web pages, and shows a floating download button on web videos.
- **Video & gallery support:** Integrates with `yt-dlp`, `ffmpeg`, and `gallery-dl` (with signed helper verification).
- **Link grabber, archive preview & extraction:** Inspects remote `.zip` files before downloading, extracts archives, unwraps `thunder://` / `flashget://` / `qqdl://` links, and supports Hugging Face / GitHub releases.
- **Queues, Scheduler, Speed Limiter & VPN binding:** Schedule overnight downloads, wake/shut down PC, restrict to a chosen network adapter, and use **Interface themes + Dark mode + 87 languages**.
- **CLI, Local Remote UI & MCP server:** Includes `vadm-cli.exe` for scripts and `vadm-mcp.exe` for AI assistants.

---

## Automated Updates (Option A)

1. **Upstream sync (`.github/workflows/sync-upstream.yml`):**
   - Runs daily at `03:00 UTC` (and via manual `workflow_dispatch`).
   - Fetches `anefzaoui/misterdownloadmanager` (`upstream/main`), filters out torrent/RSS changes via `tools/release/sync_upstream.py`, and cherry-picks clean commits.
   - **Clean sync (`0` conflicts):** Runs extension + Windows workspace tests (`verify`). When all tests pass, `auto_release` merges to `main`, bumps the version, pushes a new `vX.Y.Z` tag, and triggers `.github/workflows/release.yml`.
   - **Conflicts or test failure:** Opens a Pull Request listing the exact conflicted/failed commits for manual review instead of touching `main`.
2. **Release signing & in-app update (`.github/workflows/release.yml`):**
   - Builds Windows x64 (`setup.exe`, `portable.zip`, `x64.zip`, Chromium extension zip).
   - Signs `SHA256SUMS.txt` and `ffmpeg-builds.txt` with VADM's OpenPGP Ed25519 key (`crates/tools/keys/mdm-release.asc`, GitHub secret `MDM_RELEASE_KEY`).
   - Running **release builds** (`VADM-<version>-setup.exe`, `portable.zip`, or `x64.zip`) can update in place via **Help → Check for updates... → Update now**.

---

## Build from Source (Windows)

Requires Rust stable `1.98+` (MSVC toolchain), CMake, LLVM (`libclang`), and NASM (plus [Inno Setup 6.3+](https://jrsoftware.org/isinfo.php) if building `setup.exe`).

```powershell
# Avoid filling C: if building on a secondary drive:
$env:CARGO_TARGET_DIR = "F:\rust-target-cache"

cargo build --release --workspace
```

This produces `vadm.exe`, `vadm-cli.exe`, `vadm-mcp.exe`, and `vadm-nmhost.exe` in `target\release\` (or `$env:CARGO_TARGET_DIR\release\`).

To pack the browser extension and register the native host:

```powershell
powershell -ExecutionPolicy Bypass -File tools\extension\pack.ps1
target\release\vadm-nmhost.exe --register
```

Then open `edge://extensions` or `chrome://extensions`, enable **Developer mode**, and click **Load unpacked** → select `target\extension\chromium`.

To build the Windows x64 installer & zips into `target\dist\`:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer\build.ps1 -Arch x64
```

---

## Licence and Credits

Copyright (c) 2026 Ahmed Nefzaoui & VADM contributors.
VADM is free and open-source software under the [GNU General Public License, version 3](LICENSE) or later.

Based on [anefzaoui/misterdownloadmanager](https://github.com/anefzaoui/misterdownloadmanager). See [ATTRIBUTION.md](ATTRIBUTION.md) for third-party icon and dependency licenses.

<!-- contributors:start (python tools/contributors.py readme) -->
<p>
<a href="https://github.com/AzureKnigh7" title="AzureKnigh7"><img src="art/contributors/azureknigh7.png" width="48" height="48" alt="AzureKnigh7"></a>
<a href="https://github.com/specailm5" title="specailm5"><img src="art/contributors/specailm5.png" width="48" height="48" alt="specailm5"></a>
<a href="https://github.com/osunday" title="osunday"><img src="art/contributors/osunday.png" width="48" height="48" alt="osunday"></a>
<a href="https://github.com/SwiftyPop" title="SwiftyPop"><img src="art/contributors/swiftypop.png" width="48" height="48" alt="SwiftyPop"></a>
<a href="https://github.com/mfat" title="mfat"><img src="art/contributors/mfat.png" width="48" height="48" alt="mfat"></a>
<a href="https://github.com/praveenkumar2K06" title="praveenkumar2K06"><img src="art/contributors/praveenkumar2k06.png" width="48" height="48" alt="praveenkumar2k06"></a>
<a href="https://github.com/shreeramncity" title="shreeramncity"><img src="art/contributors/shreeramncity.png" width="48" height="48" alt="shreeramncity"></a>
<a href="https://github.com/AwesomeIronman" title="AwesomeIronman"><img src="art/contributors/awesomeironman.png" width="48" height="48" alt="AwesomeIronman"></a>
<a href="https://github.com/Maldo-0750" title="Maldo-0750"><img src="art/contributors/maldo-0750.png" width="48" height="48" alt="Maldo-0750"></a>
<a href="https://github.com/Twig6943" title="Twig6943"><img src="art/contributors/twig6943.png" width="48" height="48" alt="Twig6943"></a>
<a href="https://github.com/ADIxxDEV" title="ADIxxDEV"><img src="art/contributors/adixxdev.png" width="48" height="48" alt="ADIxxDEV"></a>
<a href="https://github.com/crse" title="crse"><img src="art/contributors/crse.png" width="48" height="48" alt="crse"></a>
<a href="https://github.com/dhrubo11" title="dhrubo11"><img src="art/contributors/dhrubo11.png" width="48" height="48" alt="dhrubo11"></a>
<a href="https://github.com/Drigva" title="Drigva"><img src="art/contributors/drigva.png" width="48" height="48" alt="Drigva"></a>
<a href="https://github.com/EnderDobra" title="EnderDobra"><img src="art/contributors/enderdobra.png" width="48" height="48" alt="EnderDobra"></a>
<a href="https://github.com/farjanatech" title="farjanatech"><img src="art/contributors/farjanatech.png" width="48" height="48" alt="farjanatech"></a>
<a href="https://github.com/gowzee" title="gowzee"><img src="art/contributors/gowzee.png" width="48" height="48" alt="gowzee"></a>
<a href="https://github.com/husnainahmedrana" title="husnainahmedrana"><img src="art/contributors/husnainahmedrana.png" width="48" height="48" alt="husnainahmedrana"></a>
<a href="https://github.com/justnxhom" title="justnxhom"><img src="art/contributors/justnxhom.png" width="48" height="48" alt="justnxhom"></a>
<a href="https://github.com/mayankmohan1992" title="mayankmohan1992"><img src="art/contributors/mayankmohan1992.png" width="48" height="48" alt="mayankmohan1992"></a>
<a href="https://github.com/Mpsp4321" title="Mpsp4321"><img src="art/contributors/mpsp4321.png" width="48" height="48" alt="Mpsp4321"></a>
<a href="https://github.com/sadatdaniel" title="sadatdaniel"><img src="art/contributors/sadatdaniel.png" width="48" height="48" alt="sadatdaniel"></a>
<a href="https://github.com/SHURmanizer" title="SHURmanizer"><img src="art/contributors/shurmanizer.png" width="48" height="48" alt="SHURmanizer"></a>
<a href="https://github.com/Uyaii" title="Uyaii"><img src="art/contributors/uyaii.png" width="48" height="48" alt="Uyaii"></a>
<a href="https://github.com/Volcanify" title="Volcanify"><img src="art/contributors/volcanify.png" width="48" height="48" alt="Volcanify"></a>
<a href="https://github.com/Zekidt" title="Zekidt"><img src="art/contributors/zekidt.png" width="48" height="48" alt="Zekidt"></a>
<a href="https://github.com/Stark-0505" title="Stark-0505"><img src="art/contributors/stark-0505.png" width="48" height="48" alt="Stark-0505"></a>
<a href="https://github.com/dr-strange15" title="dr-strange15"><img src="art/contributors/dr-strange15.png" width="48" height="48" alt="dr-strange15"></a>
</p>
<!-- contributors:end -->
