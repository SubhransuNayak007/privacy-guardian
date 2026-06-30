const fs = require('fs');

async function test() {
  try {
    const payload = JSON.parse(fs.readFileSync('test.json', 'utf8'));
    const res = await fetch('http://localhost:3000/api/scan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    console.log(res.status);
    console.log(await res.text());
  } catch (e) {
    console.error(e);
  }
}
test();
