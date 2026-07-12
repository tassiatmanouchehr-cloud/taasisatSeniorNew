#!/usr/bin/env node
/**
 * Cross-platform replacement for `cp node_modules/alpinejs/dist/cdn.min.js
 * static/ui/js/alpine.min.js` (Unix `cp` doesn't exist on Windows).
 * Copies the installed Alpine.js package's own prebuilt CDN bundle
 * verbatim, byte-for-byte, into the static asset path Django serves.
 */

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const src = path.join(root, "node_modules", "alpinejs", "dist", "cdn.min.js");
const dest = path.join(root, "static", "ui", "js", "alpine.min.js");

fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.copyFileSync(src, dest);

console.log(`js:build -> ${path.relative(root, dest)}`);
