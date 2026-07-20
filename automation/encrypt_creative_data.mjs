#!/usr/bin/env node
/** Build the public encrypted creative dashboard payload without exposing raw reports. */

import { createCipheriv, pbkdf2Sync, randomBytes } from "node:crypto";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const root = process.cwd();
const privateDir = join(root, "frontend", "private-data");
const publicDir = join(root, "frontend", "public", "data");
const password = process.env.WORKBUDDY_CREATIVE_PASSWORD;

if (!password) {
  throw new Error("WORKBUDDY_CREATIVE_PASSWORD 未设置，无法加密创意看板数据。");
}

const index = JSON.parse(readFileSync(join(privateDir, "creative-index.json"), "utf8"));
const categories = Object.fromEntries(index.categories.map(category => [
  category,
  JSON.parse(readFileSync(join(privateDir, `creative-${category}.json`), "utf8")),
]));
const plaintext = Buffer.from(JSON.stringify({ index, categories }), "utf8");
const salt = randomBytes(16);
const iv = randomBytes(12);
const iterations = 600000;
const key = pbkdf2Sync(password, salt, iterations, 32, "sha256");
const cipher = createCipheriv("aes-256-gcm", key, iv);
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final(), cipher.getAuthTag()]);

mkdirSync(publicDir, { recursive: true });
for (const filename of ["creative-index.json", "creative-DT.json", "creative-手机.json"]) {
  rmSync(join(publicDir, filename), { force: true });
}
const output = join(publicDir, "creative-data.enc.json");
writeFileSync(output, JSON.stringify({
  version: 1,
  algorithm: "AES-256-GCM",
  kdf: { name: "PBKDF2", hash: "SHA-256", iterations, salt: salt.toString("base64") },
  iv: iv.toString("base64"),
  ciphertext: ciphertext.toString("base64"),
}) + "\n", "utf8");
console.log(`已生成加密创意数据: ${output} (${plaintext.length} bytes plaintext)`);
