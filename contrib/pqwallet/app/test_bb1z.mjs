import { execFileSync } from 'node:child_process';
import { webcrypto } from 'node:crypto';
if (!globalThis.crypto) globalThis.crypto = webcrypto;
import { indirizzoBB1Z, firmaBB1Z } from './bb1z.mjs';

const CLI=['/home/ubuntu/bitcoboost-src/src/bitcoin-cli','-regtest','-datadir=/tmp/pqreg','-rpcport=38221','-rpcuser=r','-rpcpassword=r'];
function cli(...a){ return execFileSync(CLI[0],[...CLI.slice(1),...a],{encoding:'utf8'}).trim(); }
const REG = { messagePrefix:'x', bech32:'bcrt', bip32:{public:0x043587cf,private:0x04358394}, pubKeyHash:0x6f, scriptHash:0xc4, wif:0xef };
const frase = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';

const info = indirizzoBB1Z(frase, REG, 'bcrt');
console.log('indirizzo JS  :', info.address);
console.log('scriptPubKey  :', info.scriptPubKey);
const va = JSON.parse(cli('validateaddress', info.address));
console.log('nodo: isvalid=%s witver=%s spk_combacia=%s', va.isvalid, va.witness_version, va.scriptPubKey===info.scriptPubKey);

cli('sendtoaddress', info.address, '0.4');
cli('sendtoaddress', info.address, '0.25');
cli('generatetoaddress','1', cli('getnewaddress'));
const scan = JSON.parse(cli('scantxoutset','start', JSON.stringify(['raw('+info.scriptPubKey+')'])));
const utxos = scan.unspents.map(u=>({txid:u.txid, vout:u.vout, valoreSat: Math.round(u.amount*1e8)}));
const tot = utxos.reduce((s,u)=>s+u.valoreSat,0);
console.log('UTXO scoperti :', utxos.length, '| totale sat', tot);

const dest = JSON.parse(cli('getaddressinfo', cli('getnewaddress'))).scriptPubKey;
const raw = firmaBB1Z({ frase, network:REG, utxos, destScriptHex:dest, importoSat: tot-20000, feeSat:20000 });
console.log('tx firmata    :', raw.length/2, 'byte');
try {
  const txid = cli('sendrawtransaction', raw);
  console.log('>>> ACCETTATA DAL NODO! txid', txid);
  cli('generatetoaddress','1', cli('getnewaddress'));
  const speso = utxos.every(u => cli('gettxout', u.txid, String(u.vout))==='');
  console.log('>>> tutte le entrate spese:', speso);
} catch(e){
  console.log('>>> RIFIUTATA:', String(e.stderr||e.message).slice(0,300));
}
