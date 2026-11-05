import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateBuildIdentity} from '../scripts/build-identity.mjs';

test('Windows/CRLF and Linux/LF produce the same public build identity',()=>{
  const windows=calculateBuildIdentity('<html>\r\nA</html>',[['src\\app.mjs','line1\r\nline2'],['styles\\main.css','body{}\r\n']]);
  const linux=calculateBuildIdentity('<html>\nA</html>',[['styles/main.css','body{}\n'],['src/app.mjs','line1\nline2']]);
  assert.equal(windows,linux);
});
test('A real application change creates a different identity',()=>assert.notEqual(calculateBuildIdentity('A',[['src/app.mjs','a']]),calculateBuildIdentity('A',[['src/app.mjs','b']])));
