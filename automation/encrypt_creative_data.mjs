#!/usr/bin/env node
/** Build the public encrypted creative dashboard payload without exposing raw reports. */

import { createCipheriv, pbkdf2Sync, randomBytes } from "node:crypto";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const privateDir = join(root, "frontend", "private-data");
const publicDir = join(root, "frontend", "public", "data");
const password = process.env.WORKBUDDY_CREATIVE_PASSWORD;

if (!password) {
  throw new Error("WORKBUDDY_CREATIVE_PASSWORD 未设置，无法加密创意看板数据。");
}

const index = JSON.parse(readFileSync(join(privateDir, "creative-index.json"), "utf8"));
const dashboard = JSON.parse(readFileSync(join(privateDir, "dashboard-data.json"), "utf8"));
const categories = Object.fromEntries(index.categories.map(category => [
  category,
  JSON.parse(readFileSync(join(privateDir, `creative-${category}.json`), "utf8")),
]));
const salt = randomBytes(16);
const iterations = 600000;
const key = pbkdf2Sync(password, salt, iterations, 32, "sha256");

function encrypt(payload) {
  const plaintext = Buffer.from(JSON.stringify(payload), "utf8");
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final(), cipher.getAuthTag()]);
  return {
    envelope: {
      version: 1,
      algorithm: "AES-256-GCM",
      kdf: { name: "PBKDF2", hash: "SHA-256", iterations, salt: salt.toString("base64") },
      iv: iv.toString("base64"),
      ciphertext: ciphertext.toString("base64"),
    },
    plaintextBytes: plaintext.length,
  };
}

mkdirSync(publicDir, { recursive: true });
for (const filename of ["creative-index.json", "creative-DT.json", "creative-手机.json", "creative-data.enc.json", "dashboard-data.enc.json"]) {
  rmSync(join(publicDir, filename), { force: true });
}
for (const [filename, payload] of [["dashboard-data.enc.json", dashboard], ["creative-data.enc.json", { index, categories }]]) {
  const { envelope, plaintextBytes } = encrypt(payload);
  const output = join(publicDir, filename);
  writeFileSync(output, JSON.stringify(envelope) + "\n", "utf8");
  console.log(`已生成加密数据: ${output} (${plaintextBytes} bytes plaintext)`);
}
