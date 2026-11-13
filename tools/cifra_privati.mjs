// Cifra dati/scansione-privata.js in dati/scansione-cifrata.json (AES-256-GCM, chiave da PBKDF2-SHA256), decifrabile dal sito con la password.
// Uso: CIFRA_PASSWORD="..." node tools/cifra_privati.mjs      (senza CIFRA_PASSWORD ne genera una e la stampa una volta sola)
// Il file cifrato e pubblico: la password NON va scritta in nessun file del repo.
import { readFileSync, writeFileSync } from 'node:fs';
import { randomBytes, pbkdf2Sync, createCipheriv } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const radice = join(dirname(fileURLToPath(import.meta.url)), '..');
const ITER = 600000;
let password = process.env.CIFRA_PASSWORD;
if (!password) {
  const abc = 'abcdefghjkmnpqrstuvwxyz23456789';
  const gruppo = () => Array.from(randomBytes(5), b => abc[b % abc.length]).join('');
  password = [gruppo(), gruppo(), gruppo(), gruppo()].join('-');
  console.log('Password generata (salvala, non e scritta da nessuna parte):', password);
}
const testo = readFileSync(join(radice, 'dati', 'scansione-privata.js'), 'utf8');
const json = testo.slice(testo.indexOf('=') + 1).trim().replace(/;$/, '');
JSON.parse(json); // controllo che sia valido

const sale = randomBytes(16), iv = randomBytes(12);
const chiave = pbkdf2Sync(password, sale, ITER, 32, 'sha256');
const c = createCipheriv('aes-256-gcm', chiave, iv);
const cifrato = Buffer.concat([c.update(json, 'utf8'), c.final(), c.getAuthTag()]); // il browser vuole il tag in coda
writeFileSync(join(radice, 'dati', 'scansione-cifrata.json'), JSON.stringify({
  iter: ITER, sale: sale.toString('base64'), iv: iv.toString('base64'), dati: cifrato.toString('base64')
}));
console.log('scritto dati/scansione-cifrata.json');
